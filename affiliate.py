"""A8.netのアフィリエイト広告。記事の内容に合うものを、1ページに1つだけ出す。

広告の中身は assets/a8_ads.json だけで管理する（リンクの差し替え・追加はそのファイルを直す）。
- 動画（週刊なぜなぞ相場）には使わない。サイトの記事ページだけ。
- 必ず「PR」を付ける。売買をすすめる書き方・断定的な言い回しはしない。
"""
import json
import re
import zlib
from datetime import date
from html import escape
from pathlib import Path

ADS_FILE = Path(__file__).parent / "assets" / "a8_ads.json"
_CACHE = None


def _load():
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(ADS_FILE.read_text(encoding="utf-8")) if ADS_FILE.exists() else {"topics": {}, "programs": []}
    return _CACHE


def active_programs() -> list[dict]:
    return [p for p in _load()["programs"] if p.get("a8mat") and p.get("text") and p.get("pixel")]


def _count(text: str, words) -> int:
    """キーワードの出現数。「3007円安」「784円高」のような値幅の「円安・円高」は数えない"""
    n = 0
    for k in words:
        pat = re.escape(k)
        if k in ("円安", "円高"):
            pat = r"(?<![0-9０-９,，.万億])" + pat
        n += len(re.findall(pat, text))
    return n


def _in_season(day: str, seasons) -> bool:
    md = day[5:10]
    for a, b in seasons or []:
        if (a <= md <= b) if a <= b else (md >= a or md <= b):
            return True
    return False


def _texts(edition: dict) -> tuple[str, str]:
    """（見出し・タグ）と（3行まとめ・本文）。広告の話題は見出しかタグに出たものだけ（まとめや本文の「ドル円」程度では出さない）"""
    head = " ".join([edition.get("headline", ""), " ".join(edition.get("tags", []))])
    body = [" ".join(edition.get("summary", []))]
    for sec in edition.get("narrative", []):
        if isinstance(sec, dict):
            body.append(sec.get("title", ""))
            body.extend(sec.get("paragraphs", []))
    body.append(edition.get("lesson_title", ""))
    return head, " ".join(body)


def pick(edition: dict) -> dict | None:
    """記事に合う案件を1つ選ぶ（無ければ None）。見出し・タグに出る話題を優先し、無ければ証券口座。"""
    progs = active_programs()
    if not progs:
        return None
    topics = _load()["topics"]
    head, body = _texts(edition)
    day = edition.get("edition_date", date.today().isoformat())
    best, best_score = None, 0
    for name, t in topics.items():
        if not any(p["topic"] == name for p in progs):
            continue
        h = _count(head, t.get("strong", []))
        b = min(_count(body, t.get("strong", [])), 3)
        score = 3 * h + b + (5 if _in_season(day, t.get("seasons")) else 0)
        if t.get("need_strong", True) and h == 0 and not _in_season(day, t.get("seasons")):
            continue
        if not t.get("need_strong", True):
            score = max(score, 1)  # 何も当たらないときの受け皿
        if score > best_score:
            best, best_score = name, score
    if not best:
        return None
    pool = [p for p in progs if p["topic"] == best]
    prog = pool[zlib.crc32(day.encode()) % len(pool)]
    return {**prog, "lead": topics[best]["lead"]}


def ad_html(edition: dict) -> str:
    p = pick(edition)
    if not p:
        return ""
    m = escape(p["a8mat"])
    return f"""<aside class="pr-box" aria-label="広告">
    <p class="pr-head"><span class="pr">PR</span>{escape(p['lead'])}</p>
    <p class="pr-link"><a href="https://px.a8.net/svt/ejp?a8mat={m}" rel="sponsored nofollow noopener" target="_blank">{escape(p['text'])}</a><img src="https://{escape(p['pixel'])}.a8.net/0.gif?a8mat={m}" width="1" height="1" alt="" loading="lazy"></p>
    <p class="pr-note">アフィリエイト広告です。リンク先の商品・サービスを当サイトがすすめるものではありません。申し込む前に、内容・手数料・リスクをご自身でご確認ください。</p>
  </aside>"""
