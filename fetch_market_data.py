"""
なぜなぞ相場: 当日の市場データ取得（記事の数値の「正」になるファイルを作る）

使い方:
    python fetch_market_data.py [--date YYYY-MM-DD] [--out data/market_YYYY-MM-DD.json] [--no-movers]

なぜこれがあるか:
  記事の数値を WebSearch の記事スニペットから拾う方式では、別の日の記事・速報値と確定値の混在・
  数字の取り違えが避けられず、指標カードの約2割が実データとズレていた(2026-11 監査)。
  そこで、指数・為替・商品・暗号資産の数値と値上がり/値下がりランキングは必ずこのスクリプトが
  yfinance から取り、記事を書く側(AI)はこのJSONの数値をそのまま使う。WebSearchは「理由・材料」を
  調べるためだけに使う。

日付の揃え方（サイトの asof ラベルと同じ規則）:
  - 日本の指標(日経平均・TOPIX ETF) : 対象日以前で最後の東証セッション → 「M/D 東証引け」
  - 米国の指標(S&P500・Nasdaq・ダウ・SOX・VIX・米10年金利) : 対象日より前で最後のNYセッション
  - 24時間資産(ドル円・金・原油・暗号資産) : 対象日以前で最後の日足（取得した時点の値）
「一度書いたファイルの値は書き換えない」: 後から取り直すと、24時間資産は値が変わり、Yahoo側の欠損で
株価が消えることもある(例: 2026-11-16の日本株が後日NaNになった)。記録した値がそのまま正になる。
このファイルが「マスタデータ」で、サイトの記事・週刊動画(market_weekly)・週次データ(build_weekly.py)は
すべてここの数字だけを使う。
  - indices : サイトの指標カード12件
  - extras  : カードには出さないが動画や本文で使う資産(イーサリアム・銀・DAX・上海・ユーロ円・注目個別株)
  - history : 上記すべての直近90セッションの終値(チャート用)。indices/extras と同じ規則で切ってある
出力JSONの indices は edition JSON の indices にそのまま貼れる形（value_text/unit/asof/delta/pct）。
streak（N日続伸/続落/ぶり反発・反落）や1年来高値/安値かどうかも計算済みなので、見出しの
「続伸」「最高値」などの表現はここの値だけを根拠にすること。
"""
import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

BASE = Path(__file__).parent
JST = timezone(timedelta(hours=9))

# (サイト上のticker, yfinanceのticker, 表示名, 単位, 区分)
INDEX_SPEC = [
    ("^N225", "^N225", "日経平均", "円", "JP"),
    ("1306.T", "1306.T", "TOPIX(ETF)", "円", "JP"),
    ("^GSPC", "^GSPC", "S&P500", "", "US"),
    ("^IXIC", "^IXIC", "Nasdaq総合", "", "US"),
    ("^DJI", "^DJI", "NYダウ", "", "US"),
    ("USDJPY=X", "JPY=X", "ドル円", "円", "24H"),
    ("^VIX", "^VIX", "VIX恐怖指数", "", "US"),
    ("^TNX", "^TNX", "米10年金利", "%", "US"),
    ("GC=F", "GC=F", "金価格(NY金)", "ドル", "24H"),
    ("^SOX", "^SOX", "SOX半導体指数", "", "US"),
    ("CL=F", "CL=F", "原油(WTI)", "ドル", "24H"),
    ("BTC-USD", "BTC-USD", "ビットコイン", "ドル", "24H"),
]

# 指標カードには出さないが、動画・週次データ・本文で使う資産（区分 EU は米国と同じ扱い、CN は日本と同じ扱い）
EXTRA_SPEC = [
    ("ETH-USD", "ETH-USD", "イーサリアム", "ドル", "24H"),
    ("SI=F", "SI=F", "銀価格(NY銀)", "ドル", "24H"),
    ("EURJPY=X", "EURJPY=X", "ユーロ円", "円", "24H"),
    ("^GDAXI", "^GDAXI", "ドイツDAX", "", "EU"),
    ("000001.SS", "000001.SS", "上海総合", "", "CN"),
    ("NVDA", "NVDA", "エヌビディア", "ドル", "US"),
    ("9984.T", "9984.T", "ソフトバンクG", "円", "JP"),
    ("6857.T", "6857.T", "アドバンテスト", "円", "JP"),
    ("8035.T", "8035.T", "東京エレクトロン", "円", "JP"),
]
HISTORY_N = 90


def fetch_history(yf_ticker: str, end: date, days: int = 400, retries: int = 3) -> pd.Series:
    """日足終値(調整なし)。index は date。取れなければ空Seriesを返す。"""
    for i in range(retries):
        try:
            h = yf.Ticker(yf_ticker).history(start=str(end - timedelta(days=days)),
                                             end=str(end + timedelta(days=2)), auto_adjust=False)
            s = h["Close"].dropna()
            if len(s):
                s.index = [d.date() for d in s.index]
                return s
        except Exception as e:  # noqa: BLE001
            print(f"[fetch] {yf_ticker} attempt {i + 1} failed: {e}", file=sys.stderr)
        time.sleep(2 * (i + 1))
    return pd.Series(dtype=float)


def streak_info(closes: pd.Series) -> dict:
    """終値列の末尾から、連続上昇/下落日数と「N日ぶり反発/反落」を計算する。"""
    d = closes.diff().dropna()
    signs = [1 if x > 0 else (-1 if x < 0 else 0) for x in d]
    if not signs or signs[-1] == 0:
        return {"streak_days": 0, "streak_dir": "flat", "phrase": "横ばい"}
    cur = signs[-1]
    n = 0
    for s in reversed(signs):
        if s == cur:
            n += 1
        else:
            break
    prev_run = 0
    if n < len(signs):
        prev = signs[len(signs) - n - 1]
        for s in reversed(signs[:len(signs) - n]):
            if s == prev and prev != 0:
                prev_run += 1
            else:
                break
    up = cur > 0
    if n >= 2:
        phrase = f"{n}日続伸" if up else f"{n}日続落"
    elif prev_run >= 2:
        phrase = f"{prev_run + 1}日ぶり反発" if up else f"{prev_run + 1}日ぶり反落"
    else:
        phrase = "反発" if up else "反落"
    return {"streak_days": n, "streak_dir": "up" if up else "down", "prev_run_days": prev_run, "phrase": phrase}


def pick_session(s: pd.Series, target: date, kind: str):
    """区分ごとの規則で、対象日の記事が使うべき最終セッション(date)を返す。"""
    # 当日分を含めない: 米欧（日本時間16時はまだ取引前/取引中）。それ以外は当日分まで含める
    cand = s[s.index < target] if kind in ("US", "EU") else s[s.index <= target]
    return cand


def fmt(v: float) -> str:
    return f"{v:,.2f}"


def build_indices(target: date, live: bool, hist: dict, now: datetime, errors: list,
                  spec: list = INDEX_SPEC, history_out: dict | None = None) -> list:
    out = []
    for site_t, yf_t, name, unit, kind in spec:
        s = hist.get(yf_t)
        if s is None:
            s = hist[yf_t] = fetch_history(yf_t, target)
        cand = pick_session(s, target, kind) if len(s) else s
        if len(cand) < 2:
            errors.append(f"{site_t}: データ取得失敗")
            continue
        last_d, last = cand.index[-1], float(cand.iloc[-1])
        prev = float(cand.iloc[-2])
        delta = last - prev
        pct = delta / prev * 100
        md = f"{last_d.month}/{last_d.day}"
        if kind == "JP":
            asof = f"{md} 東証引け"
        elif kind == "CN":
            asof = f"{md} 上海引け"
        elif kind == "US":
            asof = f"{md} NY市場引け"
        elif kind == "EU":
            asof = f"{md} 欧州引け"
        else:
            asof = f"{md} {now.hour:02d}:00" if (live and last_d == target) else f"{md} 終値"
        if history_out is not None:
            history_out[site_t] = [[str(d), round(float(v), 4)] for d, v in cand.iloc[-HISTORY_N:].items()]
        year = cand.iloc[-252:] if len(cand) >= 2 else cand
        out.append({
            "ticker": site_t, "name": name, "value_text": fmt(last), "unit": unit, "asof": asof,
            "delta": round(delta, 2), "pct": round(pct, 2),
            "session_date": str(last_d),
            "streak": streak_info(cand.iloc[-30:]),
            "is_1y_high": bool(last >= year.max() - 1e-9), "is_1y_low": bool(last <= year.min() + 1e-9),
            "high_1y": round(float(year.max()), 2), "low_1y": round(float(year.min()), 2),
        })
    return out


def load_universe():
    sp500 = pd.read_csv(BASE / "sp500_list.csv", encoding="utf-8-sig")
    sp500["yf_ticker"] = sp500["Symbol"].str.replace(".", "-", regex=False)
    nikkei = pd.read_csv(BASE / "nikkei225_list.csv", encoding="utf-8-sig", dtype={"code": str})
    nikkei["yf_ticker"] = nikkei["code"] + ".T"
    return sp500, nikkei


def rank_movers(tickers: list[str], session: date, top_n: int) -> pd.DataFrame:
    """session の終値と、その直前の終値から騰落率を出して上位/下位を返す。"""
    data = yf.download(tickers, period="30d", progress=False, auto_adjust=False,
                       group_by="ticker", threads=True)
    rows = []
    for t in tickers:
        try:
            sub = data[t]
            close = sub["Close"].dropna()
            close.index = [d.date() for d in close.index]
            if session not in close.index:
                continue
            pos = list(close.index).index(session)
            if pos < 1:
                continue
            last, prev = float(close.iloc[pos]), float(close.iloc[pos - 1])
            vol = sub["Volume"].dropna()
            rows.append({"ticker": t, "pct": (last / prev - 1) * 100, "close": last,
                         "volume": float(vol.iloc[-1]) if len(vol) else None})
        except Exception:  # noqa: BLE001
            continue
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values("pct", ascending=False)
    return pd.concat([df.head(top_n), df.tail(top_n)]).drop_duplicates("ticker")


def build_movers(sessions: dict, top_n: int, errors: list) -> dict:
    sp500, nikkei = load_universe()
    out = {"JP": [], "US": []}
    if sessions.get("jp"):
        df = rank_movers(nikkei["yf_ticker"].tolist(), date.fromisoformat(sessions["jp"]), top_n)
        m = df.merge(nikkei, left_on="ticker", right_on="yf_ticker", how="left") if len(df) else df
        for _, r in m.iterrows():
            out["JP"].append({"ticker": r["code"], "name": r["name"], "pct": round(r["pct"], 2),
                              "close": round(r["close"], 2), "volume": r["volume"]})
        if not out["JP"]:
            errors.append("JP movers: 取得0件")
    if sessions.get("us"):
        df = rank_movers(sp500["yf_ticker"].tolist(), date.fromisoformat(sessions["us"]), top_n)
        m = df.merge(sp500, left_on="ticker", right_on="yf_ticker", how="left") if len(df) else df
        for _, r in m.iterrows():
            out["US"].append({"ticker": r["Symbol"], "name": r["Security"], "pct": round(r["pct"], 2),
                              "close": round(r["close"], 2), "volume": r["volume"]})
        if not out["US"]:
            errors.append("US movers: 取得0件")
    return out


def dump_json(data: dict) -> str:
    """indent付きで書くが、history は1資産1行にまとめる（ファイルが膨らまないように）。"""
    hist = data.get("history")
    body = dict(data)
    if hist is not None:
        body["history"] = "__HISTORY__"
    text = json.dumps(body, ensure_ascii=False, indent=2)
    if hist is not None:
        nl = "\n"
        lines = ("," + nl).join(f"    {json.dumps(k)}: {json.dumps(v, separators=(',', ':'))}" for k, v in hist.items())
        text = text.replace('"__HISTORY__"', "{" + nl + lines + nl + "  }")
    return text


def build_market_data(target: date, with_movers: bool = True, hist: dict | None = None,
                      top_n: int = 10) -> dict:
    now = datetime.now(JST)
    live = target == now.date()
    hist = hist if hist is not None else {}
    errors: list[str] = []
    history: dict = {}
    indices = build_indices(target, live, hist, now, errors, INDEX_SPEC, history)
    extras = build_indices(target, live, hist, now, errors, EXTRA_SPEC, history)
    by = {i["ticker"]: i for i in indices}
    sessions = {
        "jp": by["^N225"]["session_date"] if "^N225" in by else None,
        "us": by["^GSPC"]["session_date"] if "^GSPC" in by else None,
    }
    # 休場判定: JPの最終セッションが対象日と違えば、東証は(対象日時点で)休場または未確定
    sessions["jp_open_on_target"] = sessions["jp"] == str(target)
    if not sessions["jp_open_on_target"] and target.weekday() < 5:
        # 平日なのに当日の東証データが無い: 祝日か、Yahoo側の未反映/欠損。休場と決めつけない
        errors.append(f"JP: {target} の東証データが取得できず（祝日でなければ再取得が必要）")
    movers = {"JP": [], "US": []}
    if with_movers:
        # 日本は対象日の当日セッションがあるときだけ。米国は直近セッション(対象日の前日扱い)
        mv_sessions = {"jp": sessions["jp"] if sessions["jp_open_on_target"] else None, "us": sessions["us"]}
        movers = build_movers(mv_sessions, top_n, errors)
    return {
        "edition_date": str(target),
        "generated_at_jst": now.strftime("%Y-%m-%d %H:%M JST"),
        "live": live,
        "sessions": sessions,
        "indices": indices,
        "extras": extras,
        "movers": movers,
        "history": history,
        "fetch_errors": errors,
        "usage_note": ("indices は edition JSON の indices にそのまま使う。値上がり/値下がりの騰落率(pct)も"
                       "この movers の数値をそのまま使う。streak.phrase/1年来高値フラグを見出しの根拠にする。"
                       "ここに無い数字を書くときは必ず別ソースで裏取りする。"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="対象日 YYYY-MM-DD (省略時は今日のJST)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-movers", action="store_true")
    ap.add_argument("--top-n", type=int, default=10)
    ap.add_argument("--force", action="store_true", help="既存ファイルを上書きする（通常は使わない）")
    args = ap.parse_args()

    target = date.fromisoformat(args.date) if args.date else datetime.now(JST).date()
    data = build_market_data(target, with_movers=not args.no_movers, top_n=args.top_n)
    out = Path(args.out) if args.out else BASE / "data" / f"market_{target}.json"
    # マスタは一度書いたら書き換えない（取り直すと値が変わる/欠けることがあるため）
    if out.exists() and not args.force:
        print(f"[market] {out} は既にあるので上書きしません（作り直すなら --force）", file=sys.stderr)
        return
    # 指標が1つも取れていなければファイルを書かずに失敗扱い(Actionsで検知してリトライ/通知できるように)
    if not data["indices"]:
        print("[market] 指標を1つも取得できませんでした", data["fetch_errors"], file=sys.stderr)
        sys.exit(2)
    out.parent.mkdir(exist_ok=True)
    out.write_text(dump_json(data), encoding="utf-8")
    print(f"[market] wrote {out}  indices={len(data['indices'])}/{len(INDEX_SPEC)} "
          f"movers JP={len(data['movers']['JP'])} US={len(data['movers']['US'])} errors={len(data['fetch_errors'])}",
          file=sys.stderr)
    if data["fetch_errors"]:
        print("[market] fetch_errors:", data["fetch_errors"], file=sys.stderr)


if __name__ == "__main__":
    main()
