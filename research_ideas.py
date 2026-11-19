"""データ検証のテーマ候補を出す（毎週テーマがかぶらないように）。

使い方:
    python research_ideas.py 2026-11-26          # 動画の公開日（木曜）
  - その週の weekly_*.json で大きく動いた資産に関係するテーマほど上に出す
  - 直近6週に「同じ種類×同じ資産」をやっていれば ×（research.py も止める）
  - 種類（event/streak/corr/season）も、直近でやった種類は少し下げる（同じ形式が続かないように）
  - 出てきたコマンドをそのまま実行すれば検証できる（--id の日付と --until は自動で入る）
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from research import RECENT_WEEKS, load_index, recent_dups

BASE = Path(__file__).parent
# サイト(マスタ)のticker → yfinanceのticker
SITE2YF = {"USDJPY=X": "JPY=X"}

# (種類, 資産A, 名前A, 資産B, 名前B, 条件, 見どころ)  条件: event=threshold, streak=日数, corr=window
CATALOG = [
    ("event", "^N225", "日経平均", None, None, 5, "大きく上げた翌日以降は、さらに上がる？利益確定で下がる？"),
    ("event", "BTC-USD", "ビットコイン", None, None, -10, "1日で1割下げたビットコイン、その後は？"),
    ("event", "BTC-USD", "ビットコイン", None, None, 10, "1日で1割上げたビットコイン、飛びつくとどうなる？"),
    ("event", "^GSPC", "S&P500", "^N225", "日経平均", -4, "米国株が急落した翌日から、日経平均はどう動く？"),
    ("event", "JPY=X", "ドル円", "^N225", "日経平均", 1.5, "急な円安の日のあと、日経平均は上がりやすい？"),
    ("event", "JPY=X", "ドル円", "^N225", "日経平均", -1.5, "急な円高の日のあと、日経平均は？"),
    ("event", "^VIX", "VIX恐怖指数", "^GSPC", "S&P500", 40, "恐怖指数が1日で4割跳ねた日に買うと？"),
    ("event", "GC=F", "金", None, None, -4, "安全資産の金が急落した後は？"),
    ("event", "CL=F", "原油WTI", "^GSPC", "S&P500", -8, "原油が暴落した日のあと、米国株は？"),
    ("event", "^SOX", "半導体指数SOX", "8035.T", "東京エレクトロン", -7, "米半導体が急落した翌日、日本の半導体株は？"),
    ("event", "^TNX", "米10年金利", "^IXIC", "ナスダック", 5, "金利が急に上がった日のあと、ハイテク株は？"),
    ("event", "HG=F", "銅", "^GSPC", "S&P500", -5, "景気の先行指標と言われる銅が急落したら？"),
    ("event", "^KS11", "韓国KOSPI", "^N225", "日経平均", -4, "お隣の韓国株が急落した日、日経平均は？"),
    ("event", "NG=F", "天然ガス", None, None, 10, "値動きの激しい天然ガス、急騰の後は？"),
    ("streak", "^N225", "日経平均", None, None, 6, "日経平均が6連騰した後も上がり続ける？"),
    ("streak", "^N225", "日経平均", None, None, -6, "6連敗した日経平均、その後は？"),
    ("streak", "^GSPC", "S&P500", None, None, 7, "S&P500の7連騰、その後は？"),
    ("streak", "BTC-USD", "ビットコイン", None, None, -5, "ビットコインが5日続落した後は？"),
    ("streak", "JPY=X", "ドル円", None, None, 6, "ドル円が6日連続で円安に動いた後は？"),
    ("streak", "GC=F", "金", None, None, 5, "金の5連騰の後は？"),
    ("corr", "BTC-USD", "ビットコイン", "^IXIC", "ナスダック", 60, "ビットコインは「ハイテク株の仲間」になった？"),
    ("corr", "GC=F", "金", "BTC-USD", "ビットコイン", 60, "「デジタルゴールド」は本当に金と連動している？"),
    ("corr", "^N225", "日経平均", "JPY=X", "ドル円", 60, "円安なら日本株高、はいまも成り立つ？"),
    ("corr", "^TNX", "米10年金利", "GC=F", "金", 60, "金利が上がると金は下がる、は本当？"),
    ("corr", "CL=F", "原油WTI", "^GSPC", "S&P500", 60, "原油と株は同じ方向？逆？"),
    ("corr", "HG=F/GC=F", "銅÷金レシオ", "^TNX", "米10年金利", 60, "知る人ぞ知る景気の温度計「銅金レシオ」と金利"),
    ("corr", "^TWII", "台湾加権指数", "^SOX", "半導体指数SOX", 60, "台湾株はほぼ半導体株？"),
    ("corr", "HYG", "米ハイイールド債", "^GSPC", "S&P500", 60, "ジャンク債と株、どちらが先に崩れる？"),
    ("season", "^N225", "日経平均", None, None, None, "日経平均は何月に強い？"),
    ("season", "^GSPC", "S&P500", None, None, None, "「5月に売れ」は本当？"),
    ("season", "BTC-USD", "ビットコイン", None, None, None, "ビットコインの得意な月・苦手な月"),
    ("season", "GC=F", "金", None, None, None, "金は何月に上がりやすい？"),
    ("season", "JPY=X", "ドル円", None, None, None, "ドル円の季節性（年末の円安は本当？）"),
    ("season", "^RUT", "米小型株ラッセル2000", None, None, None, "小型株の「1月効果」は今もある？"),
    ("season", "^NSEI", "インドNifty50", None, None, None, "成長市場インド株の季節性"),
    ("season", "NG=F", "天然ガス", None, None, None, "冬に向けて天然ガスは上がる？"),
]
KIND_PARAM = {"event": "--threshold", "streak": "--streak", "corr": "--window"}
SLUG = str.maketrans({"^": "", "=": "", "/": "_", "-": "", ".": ""})


def weekly_moves(friday: str) -> dict:
    p = BASE / "data" / f"weekly_{friday}.json"
    if not p.exists():
        return {}
    w = json.loads(p.read_text(encoding="utf-8"))
    return {SITE2YF.get(a["ticker"], a["ticker"]): abs(a["pct"]) for a in w["assets"]}


def main(friday: str):
    until = friday  # 公開日（木曜）までのデータで検証
    moves = weekly_moves(friday)
    recent_kinds = [e["kind"] for e in load_index()
                    if date.fromisoformat(e["until"]) >= date.fromisoformat(until) - timedelta(weeks=3)]
    rows = []
    for kind, a, an, b, bn, prm, why in CATALOG:
        tick = [a] + ([b] if b else [])
        dup = bool(recent_dups(kind, tick, until))
        rel = max([moves.get(t.split("/")[0], 0) for t in tick] + [0])
        score = rel - 3 * recent_kinds.count(kind) + (2 if b else 0) - (100 if dup else 0)
        if kind == "season":
            score += 1
        rows.append((score, dup, kind, a, an, b, bn, prm, why, rel))
    rows.sort(key=lambda r: -r[0])
    print(f"テーマ候補（{friday}の週。今週の値動き・まだやっていない・種類の偏りで並べています）")
    for score, dup, kind, a, an, b, bn, prm, why, rel in rows[:12]:
        mark = "×" if dup else "○"
        title = f"{an}×{bn}" if bn else an
        sgn = "" if prm is None or kind == "corr" else (f"_p{abs(prm):g}" if prm > 0 else f"_m{abs(prm):g}")
        rid = f"{friday}_{kind}_{a.translate(SLUG)}" + (f"_{b.translate(SLUG)}" if b else "") + sgn.replace(".", "")
        cmd = f'python research.py --id {rid} --kind {kind} --ticker "{a}" --name "{an}" --until {until}'
        if b:
            cmd += f' --target "{b}" --target-name "{bn}"'
        if kind in KIND_PARAM:
            cmd += f" {KIND_PARAM[kind]} {prm}"
        print(f"{mark} [{kind:<6}] {title}  今週の動き{rel:4.1f}%  … {why}")
        print(f"     {cmd}")
    print(f"（×は直近{RECENT_WEEKS}週に同じ種類×同じ資産をやったもの）")


if __name__ == "__main__":
    main(sys.argv[1])
