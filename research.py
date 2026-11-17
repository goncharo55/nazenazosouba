"""データ検証（週刊動画の「データ検証コーナー」とサイトで共通に使う）

結果は data/research/<id>.json に保存し、動画もサイトもこのファイルだけを読む（数字をずらさないため）。
やった検証は data/research/index.json に記録し、直近 RECENT_WEEKS 週に「同じ種類×同じ資産」の
検証があれば止める（毎週テーマがかぶらないようにするため。どうしても必要なら --allow-dup）。
テーマ選びは research_ideas.py が候補を出す。

検証の種類（--kind）:
  event   : 資産Aが1日で X% 以上動いた日の後、N営業日後にどうなったか
            --target B を付けると「Aが動いた後のB」（資産をまたぐ検証）
  streak  : 資産Aが N日連続で上がった/下がった後、どうなったか（--streak 5 / --streak -5）
  corr    : 資産AとBの日々の値動きの相関（60営業日）。今は過去と比べて高いか低いか
  season  : 資産Aの月ごとの成績（何月に上がりやすいか）

ティッカーは yfinance の表記。"HG=F/GC=F" のように書くと比率（例: 銅÷金）を1つの指標として扱う。

例:
  python research.py --id 2026-11-20_btc_nasdaq_corr --kind corr --ticker BTC-USD --name ビットコイン \\
      --target ^IXIC --target-name ナスダック --until 2026-11-19
  python research.py --id 2026-11-20_usdjpy_up_nikkei --kind event --ticker JPY=X --name ドル円 \\
      --threshold 1.5 --target ^N225 --target-name 日経平均 --until 2026-11-19
※ 過去の結果であり、将来の値動きを保証するものではない。売買の推奨ではない。
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

BASE = Path(__file__).parent
RDIR = BASE / "data" / "research"
INDEX = RDIR / "index.json"
JST = timezone(timedelta(hours=9))
HORIZONS = [("翌日", 1), ("1週間後", 5), ("1か月後", 21), ("3か月後", 63)]
RECENT_WEEKS = 6
MONTHS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]


# ---------------- データ ----------------

def _one(ticker: str, start: str, until: str) -> pd.Series:
    # start を指定すると、データ開始より前の日付のとき直近しか返さない資産がある（BTCなど）ので、全期間を取ってから切る
    h = yf.Ticker(ticker).history(period="max", auto_adjust=False)
    s = h["Close"].dropna()
    s.index = [d.date() for d in s.index]
    s = s[~pd.Index(s.index).duplicated()]
    lo, hi = date.fromisoformat(start), date.fromisoformat(until)
    return s[[lo <= d <= hi for d in s.index]]


def load_closes(ticker: str, start: str, until: str) -> pd.Series:
    """'A/B' なら比率。日付は両方にある日だけ。"""
    if "/" in ticker:
        a, b = ticker.split("/")
        x, y = _one(a, start, until), _one(b, start, until)
        common = x.index.intersection(y.index)
        return (x[common] / y[common]).dropna()
    return _one(ticker, start, until)


# ---------------- 集計 ----------------

def forward_stats(target: pd.Series, dates: list) -> tuple[list, dict]:
    """dates の各日（以降で最初の target の取引日）から N 営業日後の騰落率。"""
    idx = list(target.index)
    rows = []
    for d in dates:
        pos = int(np.searchsorted(np.array(idx, dtype=object), d))
        if pos >= len(idx):
            continue
        row = {"date": str(d), "base_date": str(idx[pos])}
        for label, n in HORIZONS:
            row[label] = round(float(target.iloc[pos + n] / target.iloc[pos] * 100 - 100), 2) if pos + n < len(idx) else None
        rows.append(row)
    summary = {}
    for label, _ in HORIZONS:
        v = np.array([r[label] for r in rows if r[label] is not None])
        if len(v):
            summary[label] = {"n": int(len(v)), "mean": round(float(v.mean()), 2), "median": round(float(np.median(v)), 2),
                              "win_rate": round(float((v > 0).mean() * 100), 1),
                              "best": round(float(v.max()), 2), "worst": round(float(v.min()), 2)}
    return rows, summary


def baseline(target: pd.Series) -> dict:
    out = {}
    for label, n in HORIZONS:
        f = (target.shift(-n) / target * 100 - 100).dropna()
        out[label] = {"mean": round(float(f.mean()), 2), "win_rate": round(float((f > 0).mean() * 100), 1)}
    return out


def pick_dates(mask: pd.Series, gap: int) -> list:
    """条件を満たす日。同じ局面を何度も数えないよう、前の該当日から gap 営業日以内は飛ばす。"""
    out, last = [], -10**9
    for pos, (d, ok) in enumerate(mask.items()):
        if ok and pos - last > gap:
            out.append(d); last = pos
    return out


def run_event(a: pd.Series, b: pd.Series, threshold: float, gap: int) -> dict:
    ret = a.pct_change() * 100
    mask = (ret <= threshold) if threshold < 0 else (ret >= threshold)
    dates = pick_dates(mask.fillna(False), gap)
    rows, summary = forward_stats(b, dates)
    for r in rows:
        r["move"] = round(float(ret.get(date.fromisoformat(r["date"]), np.nan)), 2)
    return {"events": rows, "summary": summary, "baseline": baseline(b)}


def run_streak(a: pd.Series, b: pd.Series, n: int, gap: int) -> dict:
    sign = np.sign(a.diff())
    want = 1 if n > 0 else -1
    run = sign.groupby((sign != sign.shift()).cumsum()).cumcount() + 1
    mask = (sign == want) & (run == abs(n))   # ちょうど N 日目に到達した日
    dates = pick_dates(mask.fillna(False), gap)
    rows, summary = forward_stats(b, dates)
    for r in rows:
        d = date.fromisoformat(r["date"]); i = list(a.index).index(d)
        r["move"] = round(float(a.iloc[i] / a.iloc[max(0, i - abs(n))] * 100 - 100), 2)  # N日間の騰落
    return {"events": rows, "summary": summary, "baseline": baseline(b)}


def run_corr(a: pd.Series, b: pd.Series, window: int) -> dict:
    common = a.index.intersection(b.index)
    ra, rb = a[common].pct_change(), b[common].pct_change()
    c = ra.rolling(window).corr(rb).dropna()
    weekly = c.iloc[::5]
    now = float(c.iloc[-1])
    pct = float((c < now).mean() * 100)
    yearly = c.groupby([d.year for d in c.index]).mean()
    return {"series": [[str(d), round(float(v), 3)] for d, v in weekly.items()] + [[str(c.index[-1]), round(now, 3)]],
            "now": round(now, 3), "now_date": str(c.index[-1]), "percentile": round(pct, 1),
            "mean": round(float(c.mean()), 3), "max": round(float(c.max()), 3), "min": round(float(c.min()), 3),
            "max_date": str(c.idxmax()), "min_date": str(c.idxmin()),
            "by_year": {str(k): round(float(v), 3) for k, v in yearly.items()}, "window": window}


def run_season(a: pd.Series) -> dict:
    m = a.groupby(pd.Index([f"{d.year:04d}-{d.month:02d}" for d in a.index])).last()
    ret = (m.pct_change() * 100).dropna()
    by = {}
    for mi in range(1, 13):
        v = np.array([x for k, x in ret.items() if int(k[5:]) == mi])
        if len(v):
            by[MONTHS[mi - 1]] = {"n": int(len(v)), "mean": round(float(v.mean()), 2), "median": round(float(np.median(v)), 2),
                                  "win_rate": round(float((v > 0).mean() * 100), 1)}
    return {"months": by, "overall_mean": round(float(ret.mean()), 2), "overall_win_rate": round(float((ret > 0).mean() * 100), 1)}


# ---------------- 記録（かぶり防止） ----------------

def load_index() -> list:
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else []


def recent_dups(kind: str, tickers: list, until: str, weeks: int = RECENT_WEEKS, loose: bool = False) -> list:
    """直近 weeks 週の、かぶっている検証。
    loose=False: 同じ種類で、きっかけの資産（tickers[0]）も同じ → 止める
    loose=True : 種類を問わず、どれかの資産が重なる → 注意だけ出す"""
    lim = date.fromisoformat(until) - timedelta(weeks=weeks)
    out = []
    for e in load_index():
        if date.fromisoformat(e["until"]) < lim:
            continue
        if loose:
            if set(e["tickers"]) & set(tickers):
                out.append(e)
        elif e["kind"] == kind and e["tickers"][0] == tickers[0]:
            out.append(e)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--kind", choices=["event", "streak", "corr", "season"], default="event")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--target"); ap.add_argument("--target-name")
    ap.add_argument("--threshold", type=float)
    ap.add_argument("--streak", type=int)
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--until", required=True)
    ap.add_argument("--start", default="1970-01-01")
    ap.add_argument("--gap", type=int, default=20)
    ap.add_argument("--allow-dup", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="結果を表示するだけで、ファイルにも記録にも残さない")
    ap.add_argument("--out", help="（確認用）結果をこのパスにだけ書き出す。data/research と記録には残さない")
    a = ap.parse_args()

    tickers = [a.ticker] + ([a.target] if a.target else [])
    dups = recent_dups(a.kind, tickers, a.until)
    if dups and not a.allow_dup:
        print(f"[research] 直近{RECENT_WEEKS}週に似た検証があります（同じ種類×同じ資産）:", file=sys.stderr)
        for e in dups:
            print(f"   {e['until']} {e['id']} {e['headline']}", file=sys.stderr)
        print("[research] 別のテーマにするか、どうしても必要なら --allow-dup", file=sys.stderr)
        sys.exit(3)
    near = [e for e in recent_dups(a.kind, tickers, a.until, weeks=3, loose=True) if e["id"] != a.id]
    for e in near:
        print(f"[research] 注意: 直近3週に同じ資産を扱った検証があります（{e['until']} {e['headline']}）。続けて見えないか確認を", file=sys.stderr)

    A = load_closes(a.ticker, a.start, a.until)
    B = load_closes(a.target, a.start, a.until) if a.target else A
    tname = a.target_name or a.name
    if a.kind == "event":
        if a.threshold is None:
            sys.exit("--threshold が必要です")
        res = run_event(A, B, a.threshold, a.gap)
        cond = f"1日で{abs(a.threshold):g}%以上{'下落' if a.threshold < 0 else '上昇'}"
        headline = f"{a.name}が{cond}した日に、{tname}を買っていたら？" if a.target else f"{a.name}が{cond}した日に買っていたら？"
    elif a.kind == "streak":
        if not a.streak:
            sys.exit("--streak が必要です")
        res = run_streak(A, B, a.streak, a.gap)
        cond = f"{abs(a.streak)}日連続で{'上昇' if a.streak > 0 else '下落'}"
        headline = f"{a.name}が{cond}した後、{tname}は？" if a.target else f"{a.name}が{cond}した後は？"
    elif a.kind == "corr":
        if not a.target:
            sys.exit("--target が必要です")
        res = run_corr(A, B, a.window)
        cond = f"{a.window}営業日の相関"
        headline = f"{a.name}と{tname}、いま連動している？"
    else:
        res = run_season(A)
        cond = "月ごとの成績"
        headline = f"{a.name}は何月に上がりやすい？"
    n_events = len(res.get("events", [])) if "events" in res else None
    out = {
        "id": a.id, "kind": a.kind, "ticker": a.ticker, "name": a.name, "target": a.target, "target_name": tname,
        "condition": cond, "headline": headline, "threshold": a.threshold, "streak": a.streak,
        "data_from": str(A.index[0]), "data_until": str(A.index[-1]), "gap_days": a.gap,
        "generated_at_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "note": "終値ベース。過去の結果であり将来を保証しない。売買の推奨ではない。",
        **res,
    }
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        a.dry_run = True
    elif not a.dry_run:
        save(out, a, tickers, headline)
    print(f"[{a.kind}] {headline}（{out['data_from']}〜{out['data_until']}）" + ("  ※dry-run（保存なし）" if a.dry_run else ""))
    report(res, a)


def save(out, a, tickers, headline):
    RDIR.mkdir(parents=True, exist_ok=True)
    (RDIR / f"{a.id}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    idx = [e for e in load_index() if e["id"] != a.id]
    idx.append({"id": a.id, "kind": a.kind, "tickers": tickers, "headline": headline, "until": a.until})
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")



def report(res, a):
    if "summary" in res:
        print(f"  該当 {len(res['events'])}回")
        for label, _ in HORIZONS:
            s, bl = res["summary"].get(label), res["baseline"][label]
            if s:
                print(f"  {label:<6} 平均{s['mean']:+6.2f}% 上がった確率{s['win_rate']:5.1f}% (n={s['n']}) | 平常時 {bl['mean']:+5.2f}% {bl['win_rate']:.1f}%")
    elif a.kind == "corr":
        print(f"  いま {res['now']:+.2f}（過去の{res['percentile']:.0f}%点） 平均 {res['mean']:+.2f} 最高 {res['max']:+.2f}({res['max_date']}) 最低 {res['min']:+.2f}({res['min_date']})")
    else:
        for mname, s in res["months"].items():
            print(f"  {mname:<4} 平均{s['mean']:+5.2f}% 上がった確率{s['win_rate']:5.1f}% (n={s['n']})")
    if not a.dry_run:
        print("->", RDIR / f"{a.id}.json")


if __name__ == "__main__":
    main()
