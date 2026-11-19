"""「今週の実践」ページ：なぜなぞ相場の口座で実際に売買した記録（週1回、売買した週だけ）。

  データ: data/practice/<公開日>.json（週刊動画を作るときに集めた注文履歴と感想から作る）
  画像:   docs/practice/img/<公開日>_*.png
  出力:   docs/practice/index.html（一覧）と docs/practice/<公開日>.html
build_site.py から呼ばれる。売買の記録であり、推奨ではない（ページにも明記する）。
"""
import json
from pathlib import Path

import render
from render import esc, masthead, page_shell, SITE_NAME_A, SITE_NAME_B

BASE = Path(__file__).parent
DATA = BASE / "data" / "practice"

CSS = """
<style>
  .pr-lead { color: var(--ink-soft); max-width: 66ch; }
  .pr-figure { margin: 22px 0 28px; }
  .pr-figure img { max-width: 100%; height: auto; border: 1px solid var(--line); border-radius: 8px; background: #fff; }
  .pr-figure figcaption { font-size: 13px; color: var(--ink-faint); margin-top: 6px; }
  .pr-trades { display: grid; gap: 14px; margin: 10px 0 30px; }
  .pr-trade { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; box-shadow: var(--shadow); }
  .pr-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 12px; }
  .pr-side { font-weight: 700; font-size: 13px; color: #fff; border-radius: 4px; padding: 1px 8px; }
  .pr-side.buy { background: var(--up); } .pr-side.sell { background: var(--down); }
  .pr-name { font-weight: 700; }
  .pr-meta { font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: var(--ink-soft); }
  .pr-note { margin: 8px 0 0; }
  .pr-after { background: var(--surface-2); border-radius: 8px; padding: 16px 18px; margin: 10px 0 30px; }
  .pr-after h2 { font-size: 18px; margin: 0 0 8px; }
</style>
"""


def practice_url(date: str | None = None) -> str:
    return f"{render.SITE_ROOT}/practice/{date}.html" if date else f"{render.SITE_ROOT}/practice/"


def load_all() -> list[dict]:
    if not DATA.exists():
        return []
    items = [json.loads(p.read_text(encoding="utf-8")) for p in DATA.glob("*.json")]
    return sorted(items, key=lambda x: x["date"], reverse=True)


def _md(iso: str) -> str:
    return f"{int(iso[5:7])}/{int(iso[8:10])}"


def _footer() -> str:
    return f"""<footer class="footer">
    <p>このページは{SITE_NAME_A}{SITE_NAME_B}の口座で実際に行った売買の記録です。特定の銘柄の売買を推奨するものではありません。投資判断はご自身の責任で行ってください。</p>
    <p>{SITE_NAME_A}{SITE_NAME_B}
      ／ <a href="{esc(practice_url())}">今週の実践 一覧</a>
      ／ <a href="{esc(render.archive_url())}">過去の記事一覧</a>
      ／ <a href="{esc(render.glossary_url())}">金融用語辞典</a>
      ／ <a href="{esc(render.privacy_url())}">プライバシーポリシー</a></p>
  </footer>"""


def _figure(src: str, note: str) -> str:
    # スマホでは表が小さいので、画像をタップすると原寸で開く
    return (f'<figure class="pr-figure"><a href="{esc(src)}" target="_blank" rel="noopener">'
            f'<img src="{esc(src)}" alt="{esc(note)}" loading="lazy"></a>'
            f'<figcaption>{esc(note)}（タップで拡大）</figcaption></figure>')


def build_page(p: dict) -> str:
    trades = []
    for t in p["trades"]:
        cls = "buy" if t["side"] == "買" else "sell"
        trades.append(f"""<div class="pr-trade">
      <div class="pr-head">
        <span class="pr-side {cls}">{esc(t['side'])}</span>
        <span class="pr-name">{esc(t['name'])}</span>
        <span class="pr-meta">{esc(_md(t['date']))}　{esc(t['qty'])} @ {esc(t['price'])}　{esc(t['account'])}口座</span>
      </div>
      <p class="pr-note">{esc(t['note'])}</p>
    </div>""")
    after = ""
    if p.get("after"):
        a = p["after"]
        img = _figure(a["image"], a.get("image_note", "")) if a.get("image") else ""
        after = f"""<section class="pr-after">
      <h2>{esc(a['heading'])}</h2>
      {''.join(f'<p>{esc(x)}</p>' for x in a['paragraphs'])}
      {img}
    </section>"""
    links = [f'<a href="{esc(render.edition_url(l["edition"]))}">{esc(l["label"])}</a>' for l in p.get("links", [])]
    if p.get("short_url"):
        links.insert(0, f'<a href="{esc(p["short_url"])}" target="_blank" rel="noopener">{esc(p.get("short_label", "この週のショート"))}（YouTube）</a>')
    if p.get("video_url"):
        links.insert(0, f'<a href="{esc(p["video_url"])}" target="_blank" rel="noopener">この週の「週刊なぜなぞ相場」（YouTube）</a>')
    links_html = f'<p>関連：{" ／ ".join(links)}</p>' if links else ""
    body = f"""{CSS}
  {masthead(f"{render.format_jp_date(p['date'])}の実践", render.archive_url(), render.glossary_url(), page="practice")}

  <section class="hero">
    <p class="eyebrow">Practice — 今週の実践（{esc(p.get('period', ''))}）</p>
    <h1 class="headline">{esc(p['title'])}</h1>
    <p class="pr-lead">{esc(p['lead'])}</p>
  </section>

  {_figure(p['image'], p.get('image_note', '注文履歴'))}

  <section class="pr-trades">
    {''.join(trades)}
  </section>
  {after}
  {links_html}
  {_footer()}
"""
    return page_shell(f"今週の実践：{p['title']} — {SITE_NAME_A}{SITE_NAME_B}", body, description=p["lead"][:110],
                      standalone=True, canonical_path=practice_url(p["date"]), page_type="article",
                      published_date=p["date"])


def build_index(items: list[dict]) -> str:
    rows = "\n      ".join(f"""<div class="archive-item">
        <span class="archive-date">{esc(p['date'])}</span>
        <span class="archive-title"><a href="{esc(practice_url(p['date']))}">{esc(p['title'])}</a></span>
      </div>""" for p in items) or '<p class="archive-empty">まだありません。</p>'
    body = f"""{CSS}
  {masthead("今週の実践", render.archive_url(), render.glossary_url(), page="practice")}

  <section class="hero">
    <p class="eyebrow">Practice</p>
    <h1 class="headline">今週の実践</h1>
    <p class="pr-lead">{SITE_NAME_A}{SITE_NAME_B}の口座で、実際に売買した記録です。注文履歴と、そのとき考えたことをそのまま載せています（売買した週だけ更新）。</p>
  </section>

  <section class="archive-list">
    {rows}
  </section>
  {_footer()}
"""
    return page_shell(f"今週の実践 — {SITE_NAME_A}{SITE_NAME_B}", body,
                      description=f"{SITE_NAME_A}{SITE_NAME_B}の口座で実際に売買した記録（注文履歴と売買の理由）。",
                      standalone=True, canonical_path=practice_url())


def build_all(docs: Path) -> list[tuple[str, str]]:
    """ページを書き出して、サイトマップ用の (URL, 日付) を返す。"""
    items = load_all()
    out = docs / "practice"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(build_index(items), encoding="utf-8")
    urls = [(render.SITE_PUBLIC_URL + practice_url(), items[0]["date"] if items else None)]
    for p in items:
        (out / f"{p['date']}.html").write_text(build_page(p), encoding="utf-8")
        urls.append((render.SITE_PUBLIC_URL + practice_url(p["date"]), p["date"]))
    print("wrote", out, f"({len(items)}週分)")
    return urls
