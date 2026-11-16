"""既存の data/market_*.json を、今の fetch_market_data.py の規則で作り直す。

使い方:
    python rebuild_market_files.py                 # すべて
    python rebuild_market_files.py 2026-11-01      # この日以降だけ

- 記録済みの値（indices / sessions / movers）は一切書き換えない。マスタの値は「記録した時点の値」が正
  （取り直すと24時間資産は値が変わり、Yahoo側の欠損で値が消えることもあるため）
- 足すのは extras（追加資産）と history（チャート用の履歴）だけ
- yfinance の履歴は全日付で使い回すので、1回のダウンロードで済む
"""
import json
import sys
from datetime import date, datetime
from pathlib import Path

from fetch_market_data import EXTRA_SPEC, INDEX_SPEC, JST, build_market_data, dump_json, fetch_history

BASE = Path(__file__).parent


def main():
    since = sys.argv[1] if len(sys.argv) > 1 else "0000-00-00"
    files = sorted(p for p in (BASE / "data").glob("market_*.json") if p.stem[7:] >= since)
    last = max(date.fromisoformat(p.stem[7:]) for p in files)
    hist = {}
    for _, yf_t, *_ in INDEX_SPEC + EXTRA_SPEC:
        hist[yf_t] = fetch_history(yf_t, last, days=600)
    for p in files:
        old = json.loads(p.read_text(encoding="utf-8"))
        target = date.fromisoformat(old["edition_date"])
        new = build_market_data(target, with_movers=False, hist=hist)
        new["movers"] = old.get("movers", {"JP": [], "US": []})
        # 記録済みの値は書き換えない: indices と sessions は元のファイルのものをそのまま使い、
        # extras と history だけを足す。history の末尾も記録済みの値に合わせる
        if old.get("indices"):
            new["indices"] = old["indices"]
            new["sessions"] = old.get("sessions", new["sessions"])
            for i in old["indices"]:
                h = [x for x in new["history"].get(i["ticker"], []) if x[0] < i["session_date"]]
                h.append([i["session_date"], float(i["value_text"].replace(",", ""))])
                new["history"][i["ticker"]] = h[-90:]
            new["fetch_errors"] = old.get("fetch_errors", []) + [e for e in new["fetch_errors"] if e.split(":")[0] in {t[0] for t in EXTRA_SPEC}]
        new["live"] = False
        new["rebuilt_at_jst"] = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
        new["generated_at_jst"] = old.get("generated_at_jst", new["generated_at_jst"])
        p.write_text(dump_json(new), encoding="utf-8")
        print(p.name, "indices", len(new["indices"]), "extras", len(new["extras"]),
              "errors", new["fetch_errors"] or "-")


if __name__ == "__main__":
    main()
