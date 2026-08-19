"""
そうばノート: 当日の値動きスキャナー

使い方:
    python scan_movers.py [--date YYYY-MM-DD] [--out scan_result.json]

やること:
  1. 米国(S&P500)・日本(日経225)の全銘柄の当日騰落率・出来高を取得
  2. 24時間動く資産(暗号資産・為替・商品・株価指数先物)も取得
  3. 各市場が休場かどうかを、指標的な銘柄の最終データ日付で判定
  4. 値動きが大きい銘柄の候補(米国・日本それぞれ上位10)と、
     24時間資産の当日の動きを JSON で出力する

出力JSONは記事本文を書くAI(このスクリプトを呼ぶ側)が読み込んで、
WebSearchで値動きの理由を調べたうえで記事化する前提。
このスクリプト自体は「理由付け」はしない(数値の収集・ランキングのみ)。
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

BASE = Path(__file__).parent

ALWAYS_ON = [
    ("BTC-USD", "ビットコイン", "crypto"),
    ("ETH-USD", "イーサリアム", "crypto"),
    ("JPY=X", "ドル円", "fx"),
    ("EURUSD=X", "ユーロドル", "fx"),
    ("CL=F", "WTI原油先物", "commodity"),
    ("GC=F", "金先物", "commodity"),
    ("ES=F", "S&P500先物", "future"),
    ("NQ=F", "Nasdaq100先物", "future"),
]

INDEX_TICKERS = [
    ("^GSPC", "S&P500"),
    ("^IXIC", "Nasdaq総合"),
    ("^DJI", "NYダウ"),
    ("^SOX", "SOX(半導体)"),
    ("^N225", "日経平均"),
    ("1306.T", "TOPIX(ETF)"),
    ("^VIX", "VIX(恐怖指数)"),
    ("^TNX", "米10年金利"),
]


def load_universe():
    sp500 = pd.read_csv(BASE / "sp500_list.csv", encoding="utf-8-sig")
    sp500["yf_ticker"] = sp500["Symbol"].str.replace(".", "-", regex=False)
    nikkei = pd.read_csv(BASE / "nikkei225_list.csv", encoding="utf-8-sig", dtype={"code": str})
    nikkei["yf_ticker"] = nikkei["code"] + ".T"
    return sp500, nikkei


def batch_change(tickers: list[str], period="10d") -> pd.DataFrame:
    """全ticker分の直近2営業日分の終値・出来高・騰落率をまとめて取得"""
    data = yf.download(tickers, period=period, progress=False, auto_adjust=True,
                        group_by="ticker", threads=True)
    rows = []
    for t in tickers:
        try:
            sub = data[t] if len(tickers) > 1 else data
            close = sub["Close"].dropna()
            vol = sub["Volume"].dropna()
            if len(close) < 2:
                continue
            last, prev = close.iloc[-1], close.iloc[-2]
            rows.append({
                "ticker": t,
                "last_close": float(last),
                "prev_close": float(prev),
                "pct_change": float((last / prev - 1) * 100),
                "last_date": str(close.index[-1].date()),
                "volume": float(vol.iloc[-1]) if len(vol) else None,
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


def market_open_today(index_ticker: str, target_date: str) -> bool:
    d = yf.download(index_ticker, period="10d", progress=False, auto_adjust=True)
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    if d.empty:
        return False
    last_date = str(d.index[-1].date())
    return last_date == target_date


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="対象日 YYYY-MM-DD (省略時は今日)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--top-n", type=int, default=10)
    args = ap.parse_args()

    target_date = args.date or datetime.now().strftime("%Y-%m-%d")

    print(f"[scan] target_date={target_date}", file=sys.stderr)

    us_open = market_open_today("SPY", target_date)
    jp_open = market_open_today("1306.T", target_date)
    print(f"[scan] us_open={us_open} jp_open={jp_open}", file=sys.stderr)

    result = {
        "target_date": target_date,
        "us_market_open": us_open,
        "jp_market_open": jp_open,
        "indices": [],
        "us_movers": [],
        "jp_movers": [],
        "always_on": [],
    }

    # 主要指標
    idx_tickers = [t for t, _ in INDEX_TICKERS]
    idx_df = batch_change(idx_tickers)
    idx_map = {r["ticker"]: r for r in idx_df.to_dict("records")}
    for t, name in INDEX_TICKERS:
        r = idx_map.get(t)
        if r:
            result["indices"].append({"ticker": t, "name": name, **r})

    # 24時間資産
    ao_tickers = [t for t, _, _ in ALWAYS_ON]
    ao_df = batch_change(ao_tickers)
    ao_map = {r["ticker"]: r for r in ao_df.to_dict("records")}
    for t, name, kind in ALWAYS_ON:
        r = ao_map.get(t)
        if r:
            result["always_on"].append({"ticker": t, "name": name, "kind": kind, **r})

    # 米国個別 (S&P500)
    if us_open:
        sp500, nikkei = load_universe()
        us_df = batch_change(sp500["yf_ticker"].tolist(), period="10d")
        us_df = us_df[us_df["last_date"] == target_date]
        us_df = us_df.merge(sp500, left_on="ticker", right_on="yf_ticker", how="left")
        us_df = us_df.sort_values("pct_change", ascending=False)
        top_gain = us_df.head(args.top_n)
        top_loss = us_df.tail(args.top_n).sort_values("pct_change")
        movers = pd.concat([top_gain, top_loss]).drop_duplicates("ticker")
        for _, r in movers.iterrows():
            result["us_movers"].append({
                "ticker": r["Symbol"], "name": r["Security"],
                "pct_change": round(r["pct_change"], 2),
                "last_close": round(r["last_close"], 2),
                "volume": r["volume"],
            })
    else:
        print("[scan] US market closed today, skipping equity scan", file=sys.stderr)

    # 日本個別 (日経225)
    if jp_open:
        sp500, nikkei = load_universe()
        jp_df = batch_change(nikkei["yf_ticker"].tolist(), period="10d")
        jp_df = jp_df[jp_df["last_date"] == target_date]
        jp_df = jp_df.merge(nikkei, left_on="ticker", right_on="yf_ticker", how="left")
        jp_df = jp_df.sort_values("pct_change", ascending=False)
        top_gain = jp_df.head(args.top_n)
        top_loss = jp_df.tail(args.top_n).sort_values("pct_change")
        movers = pd.concat([top_gain, top_loss]).drop_duplicates("ticker")
        for _, r in movers.iterrows():
            result["jp_movers"].append({
                "ticker": r["code"], "name": r["name"],
                "pct_change": round(r["pct_change"], 2),
                "last_close": round(r["last_close"], 2),
                "volume": r["volume"],
            })
    else:
        print("[scan] JP market closed today, skipping equity scan", file=sys.stderr)

    out_path = Path(args.out) if args.out else BASE / "data" / f"scan_{target_date}.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[scan] wrote {out_path}", file=sys.stderr)
    print(str(out_path))


if __name__ == "__main__":
    main()
