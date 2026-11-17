"""データ検証（週刊動画の「データ検証コーナー」とサイトで共通に使う）

「ある資産が1日で X% 以上動いた日の後、N営業日後にどうなっていたか」を過去データで数える。
結果は data/research/<id>.json に保存し、動画もサイトもこのファイルだけを読む（数字をずらさないため）。

使い方:
    python research.py --id 2026-11-13_sox_drop --ticker ^SOX --name 半導体指数SOX \
        --threshold -10 --until 2026-11-04 --start 1995-01-01

  --threshold  : 1日の騰落率(%)の条件。負なら「以下」（急落）、正なら「以上」（急騰）
  --until      : この日までのデータだけを使う（検証したい今週の出来事は含めない）
  --gap        : 同じ急落局面を何度も数えないよう、前の該当日からこの営業日数以内は数えない（既定20）
比較用に「どの日に買っても」の平常時の平均（同じ期間・同じ日数後）も出す。
※ 過去の結果であり、将来の値動きを保証するものではない。売買の推奨ではない。
"""
import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

BASE = Path(__file__).parent
JST = timezone(timedelta(hours=9))
HORIZONS = [("翌日", 1), ("1週間後", 5), ("1か月後", 21), ("3か月後", 63)]


def load_closes(ticker: str, start: str, until: str) -> pd.Series:
    h = yf.Ticker(ticker).history(start=start, end=str(date.fromisoformat(until) + timedelta(days=1)), auto_adjust=False)
    s = h["Close"].dropna()
    s.index = [d.date() for d in s.index]
    return s


def study(closes: pd.Series, threshold: float, gap: int) -> dict:
    ret = closes.pct_change() * 100
    hit = ret <= threshold if threshold < 0 else ret >= threshold
    idx = list(closes.index)
    events, last_pos = [], -10**9
    for pos, d in enumerate(idx):
        if not hit.iloc[pos] or pos - last_pos <= gap:
            continue
        last_pos = pos
        ev = {"date": str(d), "move": round(float(ret.iloc[pos]), 2), "close": round(float(closes.iloc[pos]), 2)}
        for label, n in HORIZONS:
            ev[label] = round(float(closes.iloc[pos + n] / closes.iloc[pos] * 100 - 100), 2) if pos + n < len(idx) else None
        events.append(ev)
    summary, baseline = {}, {}
    for label, n in HORIZONS:
        vals = np.array([e[label] for e in events if e[label] is not None])
        if len(vals):
            summary[label] = {"n": int(len(vals)), "mean": round(float(vals.mean()), 2), "median": round(float(np.median(vals)), 2),
                              "win_rate": round(float((vals > 0).mean() * 100), 1),
                              "best": round(float(vals.max()), 2), "worst": round(float(vals.min()), 2)}
        fwd = (closes.shift(-n) / closes * 100 - 100).dropna()
        baseline[label] = {"mean": round(float(fwd.mean()), 2), "win_rate": round(float((fwd > 0).mean() * 100), 1)}
    return {"events": events, "summary": summary, "baseline": baseline}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--threshold", type=float, required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--start", default="1990-01-01")
    ap.add_argument("--gap", type=int, default=20)
    a = ap.parse_args()
    closes = load_closes(a.ticker, a.start, a.until)
    res = study(closes, a.threshold, a.gap)
    cond = f"1日で{abs(a.threshold):g}%以上{'下落' if a.threshold < 0 else '上昇'}"
    out = {
        "id": a.id, "ticker": a.ticker, "name": a.name, "condition": cond, "threshold": a.threshold,
        "data_from": str(closes.index[0]), "data_until": str(closes.index[-1]), "gap_days": a.gap,
        "generated_at_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "note": "終値ベース。過去の結果であり将来を保証しない。売買の推奨ではない。",
        **res,
    }
    p = BASE / "data" / "research" / f"{a.id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{a.name} {cond}: {len(res['events'])}回（{out['data_from']}〜{out['data_until']}）")
    for label, _ in HORIZONS:
        s, b = res["summary"].get(label), res["baseline"][label]
        if s:
            print(f"  {label:<6} 平均{s['mean']:+6.2f}% 中央値{s['median']:+6.2f}% 上がった確率{s['win_rate']:5.1f}% "
                  f"(n={s['n']})  | 平常時 平均{b['mean']:+5.2f}% 確率{b['win_rate']:.1f}%")
    print("->", p)


if __name__ == "__main__":
    main()
