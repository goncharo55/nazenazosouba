"""指標カードのミニ折れ線に使う終値の履歴 data/history.json を作る(過去記事ぶんの埋め戻し用)。

新しい日付ぶんは、毎日の market_YYYY-MM-DD.json の history から自動で入る(visuals.py が両方を読む)。
このスクリプトは、market_*.json が無い古い日付のために1回流せばよい。
"""
import json
import sys
from datetime import date
from pathlib import Path

import fetch_market_data as f

OUT = Path(__file__).parent / "data" / "history.json"


def main():
    out = {}
    for site_t, yf_t, name, *_ in f.INDEX_SPEC:
        s = f.fetch_history(yf_t, date.today(), days=430)
        if len(s) == 0:
            print("取得できず:", name, file=sys.stderr)
            continue
        out[site_t] = [[str(d), round(float(v), 4)] for d, v in s.items()]
        print(name, len(s))
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
