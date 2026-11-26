"""
なぜなぞ相場: edition JSON の数値を実データ(yfinance)と突き合わせる検証スクリプト

使い方:
    python verify_edition.py data/edition_YYYY-MM-DD.json            # 検証だけ。ERRORがあれば終了コード1
    python verify_edition.py data/edition_YYYY-MM-DD.json --fix      # indices と movers の騰落率を実データで上書き

事前に `python fetch_market_data.py --date YYYY-MM-DD` で data/market_YYYY-MM-DD.json を作っておくこと
（--market で別パスを指定可）。DBに保存する前に必ず実行し、ERRORが出たら直してから `db.py save` する。

検査する内容:
  1. indices : 12指標がそろっているか、value_text / delta / pct が実データと一致するか
  2. movers  : 各銘柄の騰落率が実データと一致するか（ランキング外の銘柄はその場でyfinanceに問い合わせる）
  3. 見出し・本文の「N日続伸/続落/ぶり反発/反落」が、実データから計算した連続日数と合っているか
  4. 本文中の日経平均の水準（○万○円）が終値から大きく外れていないか(WARN)
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import yfinance as yf

from fetch_market_data import INDEX_SPEC, fetch_history, streak_info

BASE = Path(__file__).parent
VAL_TOL = 0.0005   # 値の相対許容誤差(0.05%)
PCT_TOL = 0.06     # 指標カードの騰落率の許容誤差(ポイント)
MOVER_TOL = 0.30   # 個別銘柄の騰落率の許容誤差(ポイント)

# 本文中のキーワード → 指標ticker（連続日数の検査用）
KEYWORDS = [("日経平均", "^N225"), ("日経225", "^N225"), ("TOPIX", "1306.T"), ("S&P500", "^GSPC"), ("S&amp;P500", "^GSPC"),
            ("ナスダック", "^IXIC"), ("Nasdaq", "^IXIC"), ("NYダウ", "^DJI"), ("ダウ平均", "^DJI"), ("ダウ", "^DJI")]
STREAK_RE = re.compile(r"(\d+)(?:営業)?日(続伸|続落|ぶり反発|ぶり反落)")


def all_text_chunks(ed: dict):
    yield "headline", ed.get("headline", "")
    for s in ed.get("summary", []) or []:
        yield "summary", s
    for sec in ed.get("narrative", []) or []:
        yield "narrative", sec.get("title", "")
        for p in sec.get("paragraphs", []) or []:
            yield "narrative", p


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def _kw_index(ctx: str, m_idx: dict):
    idx, best = None, -1
    for kw, tk in KEYWORDS:
        pos = ctx.rfind(kw)
        if pos > best:
            best, idx = pos, tk
    return idx if idx in m_idx else None


def fix_streak_text(ed: dict, mk: dict) -> list[str]:
    """本文中の「N日続伸/続落/ぶり反発/反落」を実データの表現に置き換える。
    向き(上昇/下落)が同じ場合だけ自動で直し、向きが逆の場合は文章の意味が変わってしまうので触らない
    (その場合は verify の ERROR として残るので手で書き直す)。"""
    m_idx = {i["ticker"]: i for i in mk["indices"]}
    changed = []

    def repl_factory(ctx_holder):
        def repl(m):
            kind = m.group(2)
            idx = _kw_index(ctx_holder["text"][max(0, m.start() - 40):m.start()], m_idx)
            if idx is None:
                return m.group(0)
            st = m_idx[idx]["streak"]
            want_up = kind in ("続伸", "ぶり反発")
            if st["streak_dir"] != ("up" if want_up else "down"):
                return m.group(0)
            new = st["phrase"]
            if "営業" in m.group(0) and re.match(r"\d+日", new):
                new = re.sub(r"^(\d+)日", lambda mm: mm.group(1) + "営業日", new)
            if new != m.group(0):
                changed.append(f"{m.group(0)} -> {new}")
            return new
        return repl

    def fix(text: str) -> str:
        holder = {"text": text}
        return STREAK_RE.sub(repl_factory(holder), text)

    ed["headline"] = fix(ed.get("headline", ""))
    ed["summary"] = [fix(x) for x in ed.get("summary", []) or []]
    for sec in ed.get("narrative", []) or []:
        sec["title"] = fix(sec.get("title", ""))
        sec["paragraphs"] = [fix(x) for x in sec.get("paragraphs", []) or []]
    return changed


def lookup_move(ticker: str, market: str, session: str):
    """ランキング外の銘柄の騰落率をその場で取得。取れなければNone。"""
    yt = f"{ticker}.T" if market == "JP" else ticker.replace(".", "-")
    try:
        h = yf.Ticker(yt).history(start=str(date.fromisoformat(session) - timedelta(days=12)),
                                  end=str(date.fromisoformat(session) + timedelta(days=2)), auto_adjust=False)["Close"].dropna()
        h.index = [d.date() for d in h.index]
        sd = date.fromisoformat(session)
        if sd not in h.index:
            return None
        pos = list(h.index).index(sd)
        if pos < 1:
            return None
        return (float(h.iloc[pos]) / float(h.iloc[pos - 1]) - 1) * 100
    except Exception:  # noqa: BLE001
        return None


def verify(ed: dict, mk: dict, fix: bool = False, check_unlisted: bool = True):
    errors, warns, fixed = [], [], []
    m_idx = {i["ticker"]: i for i in mk["indices"]}

    # 1. indices
    have = {}
    for i in ed.get("indices", []) or []:
        have[i["ticker"]] = i
    for site_t, _, name, _, _ in INDEX_SPEC:
        if site_t not in m_idx:
            warns.append(f"[indices] {name}: 実データが取得できていないため検証不可")
            continue
        m = m_idx[site_t]
        e = have.get(site_t)
        if e is None:
            errors.append(f"[indices] {name}({site_t}) のカードがありません")
            continue
        try:
            ev = float(str(e["value_text"]).replace(",", ""))
        except Exception:  # noqa: BLE001
            errors.append(f"[indices] {name}: value_text が数値ではありません: {e.get('value_text')}")
            continue
        mv = float(m["value_text"].replace(",", ""))
        bad = []
        if abs(ev - mv) > abs(mv) * VAL_TOL:
            bad.append(f"値 記事={e['value_text']} 実データ={m['value_text']}")
        if abs(float(e.get("pct", 0)) - m["pct"]) > PCT_TOL:
            bad.append(f"騰落率 記事={e.get('pct')} 実データ={m['pct']}")
        if bad:
            errors.append(f"[indices] {name}: " + " / ".join(bad))
    extra = set(have) - {t for t, *_ in INDEX_SPEC}
    for t in extra:
        warns.append(f"[indices] 想定外の指標カード: {t}")

    # 2. movers
    jp_map = {m["ticker"]: m for m in mk["movers"]["JP"]}
    us_map = {m["ticker"]: m for m in mk["movers"]["US"]}
    for mv in ed.get("movers", []) or []:
        mkt = mv.get("market")
        t = str(mv.get("ticker"))
        if mkt not in ("JP", "US"):
            continue  # GLOBAL(24時間資産)は指標カード側で検証
        actual = (jp_map if mkt == "JP" else us_map).get(t, {}).get("pct")
        session = mk["sessions"]["jp"] if mkt == "JP" else mk["sessions"]["us"]
        if actual is None and check_unlisted and session:
            actual = lookup_move(t, mkt, session)
        if actual is None:
            level = errors if abs(float(mv.get("pct", 0))) >= 8 else warns
            level.append(f"[movers] {mv.get('name')}({t}) {mv.get('pct'):+}%: 実データで確認できません"
                         + ("（±8%超の大きな値動き。別ソースで必ず裏取りするか記事から外す）" if abs(float(mv.get('pct', 0))) >= 8 else ""))
            continue
        if abs(float(mv.get("pct", 0)) - actual) > MOVER_TOL:
            errors.append(f"[movers] {mv.get('name')}({t}): 記事={mv.get('pct'):+}% 実データ={actual:+.2f}%")
            if fix:
                mv["pct"] = round(actual, 2)
                fixed.append(f"movers {t} -> {actual:+.2f}%")

    # 3. 連続日数・「ぶり反発/反落」
    for where, text in all_text_chunks(ed):
        text = strip_tags(text)
        for m in STREAK_RE.finditer(text):
            n, kind = int(m.group(1)), m.group(2)
            ctx = text[max(0, m.start() - 40):m.start()]
            idx = None
            best = -1
            for kw, tk in KEYWORDS:
                p = ctx.rfind(kw)
                if p > best:
                    best, idx = p, tk
            if idx is None or idx not in m_idx:
                continue
            st = m_idx[idx]["streak"]
            nm = m_idx[idx]["name"]
            ok = True
            if kind in ("続伸", "続落"):
                ok = st["streak_days"] == n and st["streak_dir"] == ("up" if kind == "続伸" else "down")
            else:
                want = "up" if kind == "ぶり反発" else "down"
                ok = st["streak_dir"] == want and st["streak_days"] == 1 and st.get("prev_run_days", 0) + 1 == n
            if not ok:
                errors.append(f"[streak] {where}: 「{m.group(0)}」({nm}) → 実データでは「{st['phrase']}」"
                              f"（{m_idx[idx]['asof']}）")

    # 4. 日経平均の水準
    n225 = m_idx.get("^N225")
    if n225:
        close = float(n225["value_text"].replace(",", ""))
        for where, text in all_text_chunks(ed):
            text = strip_tags(text)
            if "日経平均" not in text:
                continue
            for m in re.finditer(r"(\d)万(\d[\d,]*)円", text):
                v = int(m.group(1)) * 10000 + int(m.group(2).replace(",", ""))
                if 30000 < v < 150000 and abs(v - close) / close > 0.004:
                    warns.append(f"[level] {where}: 「{m.group(0)}」は日経平均の終値{close:,.0f}円と離れています"
                                 "（前引け・高値などの言及なら問題なし）")

    if fix:
        fixed += [f"streak {c}" for c in fix_streak_text(ed, mk)]
        ed["indices"] = [
            {k: i[k] for k in ("ticker", "name", "value_text", "unit", "asof", "delta", "pct")}
            for i in mk["indices"]
        ]
        fixed.append("indices を実データで置き換え")

    # 読者に見せる文章に、データ取得の事情（裏側の話）を書かない。
    # 取れなかった数字は「書かない」だけにして、取れなかったこと自体には触れない
    for where, s in meta_text_chunks(ed):
        for w in META_WORDS:
            if w in s:
                errors.append(f"[meta] {where} に裏側の話（「{w}」）が入っています。読者向けの文章から消してください: {strip_tags(s)[:60]}…")
                break
    return errors, warns, fixed


META_WORDS = ("yfinance", "WebSearch", "実データ", "取得エラー", "データ取得", "自動取得", "データが取得でき", "値が取得でき",
              "取得に失敗", "取得失敗", "market_", ".json", "データの欠落", "データ側の欠落", "データ取得側",
              "推定値も含めて", "数値の正確性を優先", "本サイトの数値", "概算を含み", "編集部推計",
              "確認できず", "確認できない", "確認できません", "確認できなかった", "確認できていない", "確認できていません",
              "確認できたわけ", "確認が取れ", "確認できた範囲", "確認できた値", "確認できた報道", "材料が見当たら",
              "書き直し", "【お知らせ】", "訂正済みです", "誤った数値", "検索実施", "日付の一致")


def meta_text_chunks(ed: dict):
    yield from all_text_chunks(ed)
    for k in ("lesson_title", "lesson_body", "sources_note", "quiz_question", "quiz_explanation"):
        if ed.get(k):
            yield k, str(ed[k])
    for p in ed.get("lesson_body_paragraphs", []) or []:
        yield "lesson_body", p
    for m in ed.get("movers", []) or []:
        if m.get("reason"):
            yield f"movers {m.get('name', '')}", m["reason"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edition_json")
    ap.add_argument("--market", default=None)
    ap.add_argument("--fix", action="store_true", help="indices と movers騰落率を実データで上書きして保存")
    ap.add_argument("--no-lookup", action="store_true", help="ランキング外銘柄のyfinance問い合わせをしない")
    args = ap.parse_args()

    p = Path(args.edition_json)
    ed = json.loads(p.read_text(encoding="utf-8"))
    mp = Path(args.market) if args.market else p.parent / f"market_{ed['edition_date']}.json"
    if not mp.exists():
        print(f"ERROR: 市場データ {mp} がありません。先に python fetch_market_data.py --date {ed['edition_date']}")
        sys.exit(2)
    mk = json.loads(mp.read_text(encoding="utf-8"))

    errors, warns, fixed = verify(ed, mk, fix=args.fix, check_unlisted=not args.no_lookup)
    for w in warns:
        print("WARN :", w)
    for e in errors:
        print("ERROR:", e)
    if args.fix:
        p.write_text(json.dumps(ed, ensure_ascii=False, indent=2), encoding="utf-8")
        print("FIXED:", "; ".join(fixed) if fixed else "(変更なし)")
        print("※ 見出し・本文の数字は自動では直りません。上のERRORのうち [streak]/[level] は文章を手で直してください。")
    print(f"結果: ERROR {len(errors)}件 / WARN {len(warns)}件")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
