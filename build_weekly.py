"""週次データを作る: data/weekly_YYYY-MM-DD.json（日付はその週の金曜＝動画の公開日）

使い方:
    python build_weekly.py 2026-11-13

マスタデータ(data/market_*.json)だけから作る。yfinanceには問い合わせない。
  - 週間騰落 = 前の金曜のファイルの値 → 今週の金曜のファイルの値
    （日付の規則はマスタと同じ。日本は金曜引け、米国は木曜NY引け、24時間資産は金曜朝の確定値）
  - news = その週（前の金曜の翌日〜今週の金曜）のサイト記事の見出し・3行まとめ・値動きの理由
  - history = チャート用。今週の金曜のファイルの history をそのまま入れる
週刊動画(market_weekly)はこのファイルだけを読む。サイトとYouTubeの数値がずれないようにするため。
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"

# 動画のスコアボードの並びとグループ
GROUPS = [
    ("日本株", ["^N225", "1306.T"]),
    ("米国株", ["^GSPC", "^IXIC", "^DJI", "^SOX", "^VIX"]),
    ("世界株", ["^GDAXI", "000001.SS"]),
    ("為替・金利", ["USDJPY=X", "EURJPY=X", "^TNX"]),
    ("コモディティ", ["GC=F", "SI=F", "CL=F"]),
    ("暗号資産", ["BTC-USD", "ETH-USD"]),
    ("注目銘柄", ["NVDA", "9984.T", "6857.T", "8035.T"]),
]


def load(d: date) -> dict:
    p = DATA / f"market_{d}.json"
    if not p.exists():
        sys.exit(f"ERROR: {p.name} がありません")
    return json.loads(p.read_text(encoding="utf-8"))


def num(v: str) -> float:
    return float(v.replace(",", ""))


def main(friday: str):
    fri = date.fromisoformat(friday)
    prev = fri - timedelta(days=7)
    cur_m, prev_m = load(fri), load(prev)
    cur = {i["ticker"]: i for i in cur_m["indices"] + cur_m.get("extras", [])}
    old = {i["ticker"]: i for i in prev_m["indices"] + prev_m.get("extras", [])}
    hist = cur_m.get("history", {})
    assets, missing = [], []
    for group, tickers in GROUPS:
        for t in tickers:
            if t not in cur or t not in old:
                missing.append(t); continue
            c, o = cur[t], old[t]
            last, base = num(c["value_text"]), num(o["value_text"])
            week = [(d, v) for d, v in hist.get(t, []) if o["session_date"] < d <= c["session_date"]]
            vals = [v for _, v in week] or [last]
            assets.append({
                "ticker": t, "name": c["name"], "unit": c.get("unit", ""), "group": group,
                "base": base, "base_session": o["session_date"], "base_asof": o["asof"],
                "last": last, "last_session": c["session_date"], "last_asof": c["asof"],
                "chg": round(last - base, 4), "pct": round((last / base - 1) * 100, 2),
                "week_high": max(vals), "week_low": min(vals),
                "streak_phrase": c.get("streak", {}).get("phrase"),
                "is_1y_high": c.get("is_1y_high"), "is_1y_low": c.get("is_1y_low"),
            })
    news = []
    d = prev + timedelta(days=1)
    while d <= fri:
        ep = DATA / f"edition_{d}.json"
        if ep.exists():
            ed = json.loads(ep.read_text(encoding="utf-8"))
            news.append({
                "date": str(d), "headline": ed.get("headline"), "summary": ed.get("summary", []),
                "movers": [{k: m.get(k) for k in ("market", "ticker", "name", "pct", "reason")}
                           for m in ed.get("movers", [])],
                "lesson_title": ed.get("lesson_title"),
                "url": f"https://goncharo55.github.io/nazenazosouba/editions/{d}.html",
            })
        d += timedelta(days=1)
    out = {
        "week_ending": str(fri), "base_date": str(prev),
        "note": "週間騰落は前週金曜と今週金曜の market_*.json の値の比較。数値はマスタデータのみが出典。",
        "assets": assets, "missing": missing, "news": news, "history": hist,
    }
    from fetch_market_data import dump_json
    p = DATA / f"weekly_{fri}.json"
    p.write_text(dump_json(out), encoding="utf-8")
    for a in assets:
        print(f"{a['name']:<12} {a['base']:>12,.2f} → {a['last']:>12,.2f}  {a['pct']:+6.2f}%")
    print(f"news {len(news)}日分 / missing {missing or '-'} -> {p}")


if __name__ == "__main__":
    main(sys.argv[1])
