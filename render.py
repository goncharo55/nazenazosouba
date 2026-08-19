"""
そうばノート: HTML描画モジュール

役割:
  - build_edition_html(edition: dict) -> str   … 1日分の記事ページ
  - build_archive_html(editions: list[dict], archive_url: str) -> str … バックナンバー一覧ページ

edition dict の形は README.md の「edition JSONの形」を参照。
このモジュール単体では書かない。呼び出し側(日次パイプライン)が
db.get_edition() や自分で組み立てた dict を渡す。
"""
import html as htmlmod
import json
from pathlib import Path
from urllib.parse import quote

BASE = Path(__file__).parent
FONTS = BASE / "fonts"

SITE_NAME_A = "なぜなぞ"
SITE_NAME_B = "相場"
TAGLINE = "むずかしい値動きを、やさしい言葉で。"

# GitHub Pages のプロジェクトサイトのベースパス。
# https://goncharo55.github.io/nazenazosouba/ で公開する前提。
SITE_ROOT = "/nazenazosouba"


def home_url() -> str:
    return f"{SITE_ROOT}/"


def archive_url() -> str:
    return f"{SITE_ROOT}/archive.html"


def glossary_url() -> str:
    return f"{SITE_ROOT}/glossary.html"


def edition_url(edition_date: str) -> str:
    return f"{SITE_ROOT}/editions/{edition_date}.html"


def tag_archive_url(tag: str) -> str:
    """ハッシュタグ(例: "#AI相場")をクリックした先。バックナンバーを ?tag= で絞り込んだ状態で開く。"""
    return f"{archive_url()}?tag={quote(tag.lstrip('#'))}"


def _b64(name):
    return (FONTS / name).read_text(encoding="utf-8")


FONT_CSS = f"""
  @font-face {{
    font-family: 'Newsreader';
    font-style: normal;
    font-weight: 300 700;
    font-display: swap;
    src: url(data:font/woff2;base64,{_b64('newsreader-var.b64.txt')}) format('woff2');
  }}
  @font-face {{
    font-family: 'Newsreader';
    font-style: italic;
    font-weight: 400 600;
    font-display: swap;
    src: url(data:font/woff2;base64,{_b64('newsreader-italic.b64.txt')}) format('woff2');
  }}
  @font-face {{
    font-family: 'IBM Plex Sans';
    font-style: normal;
    font-weight: 100 700;
    font-display: swap;
    src: url(data:font/woff2;base64,{_b64('ibmplexsans-var.b64.txt')}) format('woff2');
  }}
  @font-face {{
    font-family: 'IBM Plex Mono';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url(data:font/woff2;base64,{_b64('ibmplexmono-400.b64.txt')}) format('woff2');
  }}
  @font-face {{
    font-family: 'IBM Plex Mono';
    font-style: normal;
    font-weight: 500;
    font-display: swap;
    src: url(data:font/woff2;base64,{_b64('ibmplexmono-500.b64.txt')}) format('woff2');
  }}
"""

BASE_CSS = """
  :root {
    --ink: #14181B; --ink-soft: #4A5560; --ink-faint: #7C8790;
    --paper: #F5F6F2; --surface: #FFFFFF; --surface-2: #EEF0EA; --line: #DADFD9;
    --brand: #1F3A5F; --brand-strong: #16283F; --brand-soft: #E7ECF2;
    --up: #C23B33; --down: #2B6CB0;
    --shadow: 0 1px 2px rgba(20,24,27,0.04), 0 8px 24px rgba(20,24,27,0.06);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --ink: #E9ECEE; --ink-soft: #9BA7B0; --ink-faint: #6B7680;
      --paper: #10161B; --surface: #171F26; --surface-2: #1C252D; --line: #29333B;
      --brand: #6FA0D6; --brand-strong: #8FB6E0; --brand-soft: #1B2C3D;
      --up: #E8635A; --down: #4A8AC4;
      --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 24px rgba(0,0,0,0.35);
    }
  }
  :root[data-theme="dark"] {
    --ink: #E9ECEE; --ink-soft: #9BA7B0; --ink-faint: #6B7680;
    --paper: #10161B; --surface: #171F26; --surface-2: #1C252D; --line: #29333B;
    --brand: #6FA0D6; --brand-strong: #8FB6E0; --brand-soft: #1B2C3D;
    --up: #E8635A; --down: #4A8AC4;
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 24px rgba(0,0,0,0.35);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--paper); color: var(--ink);
    font-family: 'IBM Plex Sans','Yu Gothic','Hiragino Kaku Gothic ProN','Meiryo',sans-serif;
    font-size: 16px; line-height: 1.75; -webkit-font-smoothing: antialiased;
  }
  ::selection { background: var(--brand-soft); }
  a { color: var(--brand); }
  .wrap { max-width: 920px; margin: 0 auto; padding: 0 20px 64px; }

  .masthead { border-bottom: 1px solid var(--line); padding: 28px 0 18px; margin-bottom: 28px; }
  .masthead-row { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .nameplate { font-family:'Newsreader','Yu Mincho','Hiragino Mincho ProN',serif; font-weight:600;
    font-size: clamp(28px,5vw,38px); letter-spacing:0.01em; margin:0; color: var(--ink); }
  .nameplate span { color: var(--brand); }
  .nameplate a { color: inherit; text-decoration: none; }
  .tagline { font-size:13.5px; color: var(--ink-soft); margin:6px 0 0; }
  .masthead-meta { text-align:right; font-family:'IBM Plex Mono',monospace; font-size:13px; color: var(--ink-faint); line-height:1.6; }
  .archive-link { font-size: 12.5px; margin-top: 6px; }

  .hero { margin-bottom: 36px; }
  .eyebrow { font-family:'IBM Plex Mono',monospace; font-size:12px; letter-spacing:0.08em; color: var(--down);
    text-transform: uppercase; margin:0 0 10px; }
  .headline { font-family:'Newsreader','Yu Mincho','Hiragino Mincho ProN',serif; font-weight:600;
    font-size: clamp(26px,4.2vw,38px); line-height:1.35; margin:0 0 18px; text-wrap: balance; color: var(--ink); }
  .tags { display:flex; flex-wrap:wrap; gap:8px; margin:0 0 22px; }
  .tag { font-family:'IBM Plex Mono',monospace; font-size:12px; color: var(--ink-soft); background: var(--surface-2);
    border:1px solid var(--line); border-radius:999px; padding:4px 11px; text-decoration:none; transition:border-color .15s,color .15s; }
  .tag:hover { color: var(--brand); border-color: var(--brand); }
  .summary-box { background: var(--surface); border:1px solid var(--line); border-left:3px solid var(--brand);
    border-radius:6px; padding:18px 22px; box-shadow: var(--shadow); }
  .summary-box h2 { font-family:'IBM Plex Sans',sans-serif; font-size:12.5px; letter-spacing:0.08em; text-transform:uppercase;
    color: var(--brand); margin:0 0 10px; }
  .summary-box ul { margin:0; padding-left:1.15em; }
  .summary-box li { margin-bottom:8px; color: var(--ink); }
  .summary-box li:last-child { margin-bottom:0; }

  .ticker-section { margin: 40px 0; }
  .section-label { font-family:'IBM Plex Mono',monospace; font-size:12px; letter-spacing:0.08em; text-transform:uppercase;
    color: var(--ink-faint); margin:0 0 12px; }
  .ticker-strip { display:grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap:10px; }
  .ticker-card { background: var(--surface); border:1px solid var(--line);
    border-radius:8px; padding:12px 14px; }
  .ticker-card .t-name { font-size:15px; font-weight:600; color: var(--ink); margin-bottom:2px; }
  .ticker-card .t-asof { font-size:10.5px; color: var(--ink-faint); margin-bottom:6px; }
  .ticker-card .t-value { font-family:'IBM Plex Mono',monospace; font-variant-numeric: tabular-nums; font-size:22px;
    font-weight:600; color: var(--ink); margin-bottom:4px; }
  .ticker-card .t-value .t-unit { font-family:'IBM Plex Sans',sans-serif; font-size:12.5px; font-weight:400;
    color: var(--ink-soft); margin-left:3px; white-space:nowrap; }
  .ticker-card .t-change { font-family:'IBM Plex Mono',monospace; font-variant-numeric: tabular-nums; font-size:12.5px;
    display:flex; align-items:center; gap:4px; flex-wrap:wrap; }
  .ticker-card .t-change-label { font-family:'IBM Plex Sans',sans-serif; font-size:11px; color: var(--ink-faint);
    margin-right:2px; }
  .t-change.up { color: var(--up); } .t-change.down { color: var(--down); }

  .article { margin: 44px 0; }
  .article h3 { font-family:'Newsreader','Yu Mincho','Hiragino Mincho ProN',serif; font-size:22px; font-weight:600;
    color: var(--ink); margin:34px 0 12px; padding-bottom:8px; border-bottom:1px solid var(--line); }
  .article h3 .flag { display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:12px; font-weight:500;
    color: var(--brand); background: var(--brand-soft); border-radius:3px; padding:2px 8px; margin-right:10px;
    vertical-align:middle; transform: translateY(-2px); }
  .article p { margin:0 0 16px; max-width:66ch; color: var(--ink); }
  .num { font-family:'IBM Plex Mono',monospace; font-variant-numeric: tabular-nums; }

  .movers-section { margin: 44px 0; }
  .movers-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(280px,1fr)); gap:20px; }
  .movers-panel { background: var(--surface); border:1px solid var(--line); border-radius:8px;
    padding:18px 20px 8px; box-shadow: var(--shadow); }
  .movers-panel h4 { font-family:'IBM Plex Sans',sans-serif; font-size:13px; letter-spacing:0.04em; color: var(--ink-soft);
    margin:0 0 14px; display:flex; justify-content:space-between; gap: 8px; }
  .mover-row { padding:12px 0; border-top:1px solid var(--line); }
  .mover-row:first-of-type { border-top:none; }
  .mover-top { display:flex; align-items:baseline; justify-content:space-between; gap:10px; margin-bottom:6px; }
  .mover-id { display:flex; align-items:baseline; gap:8px; min-width:0; }
  .mover-ticker { font-family:'IBM Plex Mono',monospace; font-size:12px; color: var(--ink-faint); white-space:nowrap; }
  .mover-name { font-size:14.5px; font-weight:500; color: var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .mover-pct { font-family:'IBM Plex Mono',monospace; font-variant-numeric: tabular-nums; font-size:14.5px; font-weight:500; white-space:nowrap; }
  .mover-pct.up { color: var(--up); } .mover-pct.down { color: var(--down); }
  .mover-bar-track { height:5px; background: var(--surface-2); border-radius:3px; overflow:hidden; margin-bottom:8px; }
  .mover-bar { height:100%; border-radius:3px; }
  .mover-bar.up { background: var(--up); } .mover-bar.down { background: var(--down); }
  .mover-why { font-size:13.5px; color: var(--ink-soft); line-height:1.6; margin:0; }

  .lesson { margin:48px 0; background: var(--brand-soft); border:1px solid var(--line); border-radius:10px; padding:26px 28px; }
  .lesson-label { font-family:'IBM Plex Mono',monospace; font-size:12px; letter-spacing:0.08em; text-transform:uppercase;
    color: var(--brand); margin:0 0 10px; }
  .lesson h3 { font-family:'Newsreader','Yu Mincho','Hiragino Mincho ProN',serif; font-weight:600; font-style:italic;
    font-size:22px; margin:0 0 14px; color: var(--ink); }
  .lesson p { margin:0 0 12px; max-width:66ch; color: var(--ink); }
  .lesson p:last-child { margin-bottom:0; }

  .quiz { margin:32px 0 48px; background: var(--surface); border:1px dashed var(--line); border-radius:10px; padding:26px 28px; }
  .quiz-label { font-family:'IBM Plex Mono',monospace; font-size:12px; letter-spacing:0.08em; text-transform:uppercase;
    color: var(--brand); margin:0 0 10px; }
  .quiz h3 { font-family:'Newsreader','Yu Mincho','Hiragino Mincho ProN',serif; font-weight:600; font-style:italic;
    font-size:20px; margin:0 0 16px; color: var(--ink); }
  .quiz-choices { display:flex; flex-direction:column; gap:8px; margin:0 0 14px; padding:0; list-style:none; }
  .quiz-choice { text-align:left; width:100%; padding:12px 16px; border:1px solid var(--line); border-radius:8px;
    background: var(--surface); color: var(--ink); font-size:15px; font-family:inherit; cursor:pointer; transition:border-color .15s,background .15s; }
  .quiz-choice:hover { border-color: var(--brand); }
  .quiz-choice.is-correct { border-color: var(--up); background: color-mix(in srgb, var(--up) 12%, var(--surface)); font-weight:600; }
  .quiz-choice.is-wrong { border-color: var(--down); background: color-mix(in srgb, var(--down) 10%, var(--surface)); }
  .quiz-choice:disabled { cursor:default; }
  .quiz-result { display:none; font-size:14px; color: var(--ink-soft); border-top:1px solid var(--line); padding-top:14px; margin-top:4px; }
  .quiz-result p { margin:0 0 6px; max-width:66ch; }
  .quiz-result .quiz-verdict { font-weight:600; color: var(--ink); }

  .footer { margin-top:56px; padding-top:22px; border-top:1px solid var(--line); font-size:12.5px; color: var(--ink-faint); line-height:1.8; }
  .footer p { margin:0 0 8px; max-width:70ch; }
  .footer .sources { color: var(--ink-soft); }

  /* Archive page */
  .archive-list { margin: 20px 0; display: flex; flex-direction: column; }
  .archive-item { display:flex; gap:18px; padding:18px 0; border-top:1px solid var(--line); align-items: baseline; }
  .archive-item:first-child { border-top: none; }
  .archive-date { font-family:'IBM Plex Mono',monospace; font-size:13px; color: var(--ink-faint); white-space:nowrap; min-width: 92px; }
  .archive-title { font-size:15px; color: var(--ink); }
  .archive-title a { color: var(--ink); text-decoration:none; }
  .archive-title a:hover { color: var(--brand); text-decoration:underline; }
  .archive-empty { color: var(--ink-soft); padding: 24px 0; }
  .archive-filter-banner { background: var(--brand-soft); border:1px solid var(--line); border-radius:8px;
    padding:12px 16px; margin: 0 0 8px; font-size:14px; color: var(--ink); }
  .archive-filter-banner p { margin:0; }
  .archive-filter-banner a { margin-left:10px; }

  /* Glossary page */
  .glossary-search-wrap { position: sticky; top: 0; background: var(--paper); padding: 6px 0 16px; z-index: 5; }
  .glossary-search {
    width: 100%; font-family: 'IBM Plex Sans', sans-serif; font-size: 16px; color: var(--ink);
    background: var(--surface); border: 1px solid var(--line); border-radius: 8px;
    padding: 12px 16px; outline: none; box-shadow: var(--shadow);
  }
  .glossary-search:focus { border-color: var(--brand); }
  .glossary-count { font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; color: var(--ink-faint); margin: 10px 0 0; }
  .glossary-list { display: flex; flex-direction: column; }
  .glossary-item { padding: 18px 0; border-top: 1px solid var(--line); }
  .glossary-item:first-child { border-top: none; }
  .glossary-item-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
  .glossary-term { font-family:'Newsreader','Yu Mincho','Hiragino Mincho ProN',serif; font-weight: 600; font-size: 19px; color: var(--ink); }
  .glossary-reading { font-size: 12px; color: var(--ink-faint); }
  .glossary-category { font-family:'IBM Plex Mono',monospace; font-size: 11px; color: var(--brand); background: var(--brand-soft);
    border-radius: 999px; padding: 2px 10px; }
  .glossary-def { font-size: 14.5px; color: var(--ink-soft); line-height: 1.75; max-width: 66ch; margin: 0; }
  .glossary-empty { display: none; color: var(--ink-soft); padding: 40px 0; text-align: center; }

  @media (max-width:560px) {
    .wrap { padding:0 16px 48px; }
    .masthead-meta { text-align:left; }
    .archive-item { flex-direction: column; gap: 4px; }
  }
"""


def esc(s):
    return htmlmod.escape(str(s), quote=False)


def format_jp_date(iso_date: str) -> str:
    """"2026-08-19" -> "2026年8月19日"。マストヘッドの日付表記用(ISO表記に和文の接尾辞を直接足すと読みにくいため)。"""
    y, m, d = (int(x) for x in iso_date.split("-"))
    return f"{y}年{m}月{d}日"


SITE_PUBLIC_URL = "https://goncharo55.github.io"  # SITE_ROOT("/nazenazosouba")と連結してcanonical URLを作る


def page_shell(title: str, body: str, description: str = "", standalone: bool = False,
                canonical_path: str | None = None, page_type: str = "website",
                published_date: str | None = None) -> str:
    """standalone=True で完全なHTMLドキュメント(<!doctype html>から)を出力する。
    GitHub Pagesなど、Artifactラッパーを経由しない配信先ではこちらを使う。
    canonical_path はSITE_ROOTからの絶対パス(例: "/", "/archive.html", "/editions/2026-08-19.html")。
    指定するとcanonical link・OGP・JSON-LDを出力する(SEO用)。"""
    head_extra = f'<meta name="description" content="{esc(description)}">\n  ' if description else ""
    if not standalone:
        return f"""<title>{esc(title)}</title>
<style>
{FONT_CSS}
{BASE_CSS}
</style>
<div class="wrap">
{body}
</div>
"""
    seo_tags = ""
    if canonical_path:
        canonical_url = SITE_PUBLIC_URL + canonical_path
        seo_tags = f"""<link rel="canonical" href="{esc(canonical_url)}">
  <meta property="og:type" content="{'article' if page_type == 'article' else 'website'}">
  <meta property="og:site_name" content="{esc(SITE_NAME_A + SITE_NAME_B)}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical_url)}">
  <meta property="og:locale" content="ja_JP">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">
"""
        if page_type == "article" and published_date:
            json_ld = (
                '{"@context":"https://schema.org","@type":"NewsArticle",'
                f'"headline":{json.dumps(title, ensure_ascii=False)},'
                f'"description":{json.dumps(description, ensure_ascii=False)},'
                f'"datePublished":{json.dumps(published_date, ensure_ascii=False)},'
                f'"url":{json.dumps(canonical_url, ensure_ascii=False)},'
                '"author":{"@type":"Organization","name":' + json.dumps(SITE_NAME_A + SITE_NAME_B, ensure_ascii=False) + '},'
                '"publisher":{"@type":"Organization","name":' + json.dumps(SITE_NAME_A + SITE_NAME_B, ensure_ascii=False) + '}}'
            )
            seo_tags += f'  <script type="application/ld+json">{json_ld}</script>\n'
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  {head_extra}{seo_tags}<style>
{FONT_CSS}
{BASE_CSS}
  </style>
</head>
<body>
<div class="wrap">
{body}
</div>
</body>
</html>
"""


def masthead(date_label: str, archive_url: str | None = None, glossary_url: str | None = None,
             page: str = "edition") -> str:
    """page: 'edition' | 'archive' | 'glossary' — 現在表示中のページ種別(archive/glossaryへの自分自身へのリンクは出さない)。
    サイト名(なぜなぞ相場)自体は常に home_url()、つまり最新記事にリンクする。"""
    home = f'<a href="{esc(home_url())}">{SITE_NAME_A}<span>{SITE_NAME_B}</span></a>'
    nav_links = []
    if archive_url and page != "archive":
        nav_links.append(f'<a href="{esc(archive_url)}">過去の記事一覧</a>')
    if glossary_url and page != "glossary":
        nav_links.append(f'<a href="{esc(glossary_url)}">金融用語辞典</a>')
    nav_line = f'<div class="archive-link">{" ／ ".join(nav_links)}</div>' if nav_links else ""
    return f"""<header class="masthead">
    <div class="masthead-row">
      <div>
        <p class="nameplate">{home}</p>
        <p class="tagline">{esc(TAGLINE)}</p>
      </div>
      <div class="masthead-meta">
        {esc(date_label)}
        {nav_line}
      </div>
    </div>
  </header>"""


def render_ticker_cards(indices: list[dict]) -> str:
    cards = []
    for r in indices:
        delta = r.get("delta") or 0
        pct = r.get("pct") or 0
        direction = "up" if delta >= 0 else "down"
        arrow = "▲" if delta >= 0 else "▼"
        sign = "+" if delta >= 0 else ""
        psign = "+" if pct >= 0 else ""
        unit = r.get("unit", "")
        asof = r.get("asof", "")
        cards.append(f"""<div class="ticker-card">
        <div class="t-name">{esc(r['name'])}</div>
        {f'<div class="t-asof">{esc(asof)}時点</div>' if asof else ''}
        <div class="t-value">{esc(r['value_text'])}<span class="t-unit">{esc(unit)}</span></div>
        <div class="t-change {direction}"><span class="t-change-label">前日比</span>{arrow} {sign}{delta:,.2f}{esc(unit)} ({psign}{pct:.2f}%)</div>
      </div>""")
    return "\n      ".join(cards)


def render_narrative(sections: list[dict]) -> str:
    out = []
    for s in sections:
        flag = f'<span class="flag">{esc(s["flag"])}</span>' if s.get("flag") else ""
        out.append(f'<h3>{flag}{esc(s["title"])}</h3>')
        for p in s.get("paragraphs", []):
            out.append(f'<p>{p}</p>')  # allow inline <span class="num"> markup, not escaped
    return "\n    ".join(out)


MARKET_LABELS = {
    "JP": ("日本", "日経225構成銘柄より"),
    "US": ("米国", "S&P500構成銘柄より"),
    "GLOBAL": ("為替・商品・暗号資産", "24時間動く主要資産より"),
}


def group_movers(flat_movers: list[dict]) -> dict:
    """DB由来のフラットなmoversリスト([{market,ticker,name,pct,reason,kind}, ...])を
    market別のパネル辞書にまとめる。market の出現順を保つ。"""
    panels = {}
    for m in flat_movers:
        mkt = m.get("market", "GLOBAL")
        if mkt not in panels:
            label, sub = MARKET_LABELS.get(mkt, (mkt, ""))
            panels[mkt] = {"label": label, "sub": sub, "rows": []}
        panels[mkt]["rows"].append(m)
    return panels


def render_movers_panel(panel: dict) -> str:
    rows = panel.get("rows", [])
    if not rows:
        return f"""<div class="movers-panel">
        <h4>{esc(panel['label'])} <span>{esc(panel.get('sub',''))}</span></h4>
        <p class="mover-why">この日は目立った値動きが確認できませんでした。</p>
      </div>"""
    max_abs = max(abs(r["pct"]) for r in rows) or 1
    row_html = []
    for r in rows:
        pct = r["pct"]
        direction = "up" if pct >= 0 else "down"
        width = max(6, round(abs(pct) / max_abs * 100))
        psign = "+" if pct >= 0 else ""
        reason = r.get("reason") or "明確な材料は確認できず"
        row_html.append(f"""<div class="mover-row">
          <div class="mover-top">
            <div class="mover-id">
              <span class="mover-ticker">{esc(r['ticker'])}</span>
              <span class="mover-name">{esc(r['name'])}</span>
            </div>
            <span class="mover-pct {direction}">{psign}{pct:.2f}%</span>
          </div>
          <div class="mover-bar-track"><div class="mover-bar {direction}" style="width:{width}%"></div></div>
          <p class="mover-why">{esc(reason)}</p>
        </div>""")
    return f"""<div class="movers-panel">
        <h4>{esc(panel['label'])} <span>{esc(panel.get('sub',''))}</span></h4>
        {''.join(row_html)}
      </div>"""


def render_quiz(quiz: dict | None) -> str:
    """quiz: {"question": str, "choices": list[str|{"text","explanation"}], "answer_index": int}
    未設定(None)なら空文字を返し、記事にクイズコーナー自体を出さない。
    選択肢は文字列でもよいが、{"text","explanation"}形式にすると
    「不正解の選択肢が実際は何の説明か」もその場で表示できる(誤答も学びになる設計)。"""
    if not quiz or not quiz.get("question") or not quiz.get("choices"):
        return ""
    question = esc(quiz["question"])
    answer_index = quiz.get("answer_index", 0)
    norm_choices = []
    for c in quiz["choices"]:
        if isinstance(c, dict):
            norm_choices.append({"text": c.get("text", ""), "explanation": c.get("explanation", "")})
        else:
            norm_choices.append({"text": c, "explanation": ""})
    choices_html = "\n        ".join(
        f'<li><button type="button" class="quiz-choice" data-index="{i}" '
        f'data-explanation="{esc(c["explanation"])}">{esc(c["text"])}</button></li>'
        for i, c in enumerate(norm_choices)
    )
    return f"""
  <section class="quiz" id="quiz">
    <p class="quiz-label">きょうのなぞなぞクイズ</p>
    <h3>{question}</h3>
    <ul class="quiz-choices" id="quizChoices">
        {choices_html}
    </ul>
    <div class="quiz-result" id="quizResult">
      <p class="quiz-verdict" id="quizVerdict"></p>
      <p id="quizPickedExplain"></p>
      <p id="quizCorrectExplain"></p>
    </div>
  </section>
  <script>
    (function() {{
      var answerIndex = {answer_index};
      var buttons = Array.prototype.slice.call(document.querySelectorAll('#quizChoices .quiz-choice'));
      var result = document.getElementById('quizResult');
      var verdict = document.getElementById('quizVerdict');
      var pickedExplain = document.getElementById('quizPickedExplain');
      var correctExplain = document.getElementById('quizCorrectExplain');
      buttons.forEach(function(btn) {{
        btn.addEventListener('click', function() {{
          var picked = parseInt(btn.getAttribute('data-index'), 10);
          buttons.forEach(function(b, i) {{
            b.disabled = true;
            if (i === answerIndex) b.classList.add('is-correct');
            else if (i === picked) b.classList.add('is-wrong');
          }});
          var isCorrect = picked === answerIndex;
          verdict.textContent = isCorrect ? '正解！' : '不正解…';
          var pickedExp = btn.getAttribute('data-explanation') || '';
          pickedExplain.textContent = pickedExp ? ('選んだ「' + btn.textContent + '」：' + pickedExp) : '';
          if (!isCorrect) {{
            var correctBtn = buttons[answerIndex];
            var correctExp = correctBtn.getAttribute('data-explanation') || '';
            correctExplain.textContent = '正解「' + correctBtn.textContent + '」：' + correctExp;
          }} else {{
            correctExplain.textContent = '';
          }}
          result.style.display = 'block';
        }});
      }});
    }})();
  </script>
"""


def build_edition_html(edition: dict, standalone: bool = True) -> str:
    a_url, g_url = archive_url(), glossary_url()
    date_label = format_jp_date(edition["edition_date"]) + "号"
    tags_html = "\n      ".join(
        f'<a class="tag" href="{esc(tag_archive_url(t))}">{esc(t)}</a>' for t in edition.get("tags", [])
    )
    summary_html = "\n        ".join(f'<li>{esc(s)}</li>' for s in edition.get("summary", []))
    ticker_html = render_ticker_cards(edition.get("indices", []))
    narrative_html = render_narrative(edition.get("narrative", []))
    movers_panels = group_movers(edition.get("movers", []))
    movers_html = "\n      ".join(render_movers_panel(p) for p in movers_panels.values())
    quiz_html = render_quiz(edition.get("quiz"))

    body = f"""
  {masthead(date_label, a_url, g_url, page="edition")}

  <section class="hero">
    <p class="eyebrow">{esc(edition.get('eyebrow', "Today's Market"))}</p>
    <h1 class="headline">{esc(edition['headline'])}</h1>
    <div class="tags">
      {tags_html}
    </div>
    <div class="summary-box">
      <h2>3行まとめ</h2>
      <ul>
        {summary_html}
      </ul>
    </div>
  </section>

  <section class="ticker-section">
    <p class="section-label">Market Snapshot — 主要指標</p>
    <div class="ticker-strip">
      {ticker_html}
    </div>
  </section>

  <section class="article">
    {narrative_html}
  </section>

  <section class="movers-section">
    <p class="section-label">Movers — きょう大きく動いた銘柄・資産</p>
    <div class="movers-grid">
      {movers_html}
    </div>
  </section>

  <section class="lesson">
    <p class="lesson-label">きょうの用語解説</p>
    <h3>{esc(edition.get('lesson_title',''))}</h3>
    {"".join(f'<p>{p}</p>' for p in edition.get('lesson_body_paragraphs', [edition.get('lesson_body','')]))}
  </section>
  {quiz_html}
  <footer class="footer">
    <p class="sources">{edition.get('sources_note','')}</p>
    <p>本ページは公開データと報道をもとに自動でまとめた市場概況であり、特定の銘柄の売買を推奨するものではありません。内容の正確性には配慮していますが誤りを含む可能性があります。投資判断はご自身の責任で行ってください。</p>
    <p>{SITE_NAME_A}{SITE_NAME_B} ／ 生成日時: {esc(edition.get('generated_at',''))}
      ／ <a href="{esc(a_url)}">過去の記事一覧</a>
      ／ <a href="{esc(g_url)}">金融用語辞典</a></p>
  </footer>
"""
    description = edition.get("summary", [""])[0] if edition.get("summary") else edition.get("headline", "")
    return page_shell(f"{edition['headline']} — {SITE_NAME_A}{SITE_NAME_B}", body,
                       description=description, standalone=standalone,
                       canonical_path=edition_url(edition["edition_date"]), page_type="article",
                       published_date=edition.get("generated_at", edition["edition_date"]))


def build_archive_html(editions: list[dict], standalone: bool = True) -> str:
    g_url = glossary_url()
    items = []
    for e in editions:
        d = e["edition_date"]
        headline = e["headline"]
        url = edition_url(d)
        data_tags = esc(",".join(t.lstrip("#") for t in e.get("tags", [])))
        items.append(f"""<div class="archive-item" data-tags="{data_tags}">
        <span class="archive-date">{esc(d)}</span>
        <span class="archive-title"><a href="{esc(url)}">{esc(headline)}</a></span>
      </div>""")
    list_html = "\n      ".join(items) if items else '<p class="archive-empty">まだ記事がありません。</p>'

    body = f"""
  {masthead("バックナンバー", archive_url(), g_url, page="archive")}

  <section class="hero">
    <p class="eyebrow">Archive</p>
    <h1 class="headline">過去の記事一覧</h1>
    <p style="color:var(--ink-soft); max-width:66ch;">これまでに配信した「{SITE_NAME_A}{SITE_NAME_B}」の一覧です。日々の値動きを振り返って、金融の勉強に役立ててください。</p>
  </section>

  <div class="archive-filter-banner" id="archiveFilterBanner" style="display:none;">
    <p><span id="archiveFilterLabel"></span><a href="{esc(archive_url())}">すべて表示に戻す</a></p>
  </div>

  <section class="archive-list" id="archiveList">
    {list_html}
    <p class="archive-empty" id="archiveFilterEmpty" style="display:none;">このタグの記事はまだありません。</p>
  </section>

  <script>
    (function() {{
      var params = new URLSearchParams(window.location.search);
      var tag = params.get('tag');
      if (!tag) return;
      var items = Array.prototype.slice.call(document.querySelectorAll('#archiveList .archive-item'));
      var visible = 0;
      items.forEach(function(el) {{
        var tags = (el.getAttribute('data-tags') || '').split(',');
        var match = tags.indexOf(tag) !== -1;
        el.style.display = match ? '' : 'none';
        if (match) visible++;
      }});
      document.getElementById('archiveFilterLabel').textContent = '「#' + tag + '」の関連記事（' + visible + '件）　';
      document.getElementById('archiveFilterBanner').style.display = 'block';
      document.getElementById('archiveFilterEmpty').style.display = visible === 0 ? 'block' : 'none';
    }})();
  </script>

  <footer class="footer">
    <p>{SITE_NAME_A}{SITE_NAME_B}は、公開データと報道をもとに毎営業日自動でまとめている市場概況です。特定の銘柄の売買を推奨するものではありません。
      ／ <a href="{esc(g_url)}">金融用語辞典</a></p>
  </footer>
"""
    return page_shell(f"{SITE_NAME_A}{SITE_NAME_B} — バックナンバー", body,
                       description=f"{SITE_NAME_A}{SITE_NAME_B}のこれまでの配信一覧。日々の市場の動きをやさしい言葉で振り返れます。",
                       standalone=standalone, canonical_path=archive_url())


def build_glossary_html(terms: list[dict], standalone: bool = True) -> str:
    """terms: [{term, reading, category, definition}, ...] （db.list_glossary()の出力そのまま渡せる）
    クライアントサイドJSで検索フィルタする(サーバー不要、Artifact上で完結)。"""
    items = []
    for t in terms:
        term = esc(t["term"])
        reading = esc(t.get("reading", ""))
        category = esc(t.get("category", ""))
        definition = esc(t["definition"])
        haystack = esc(f"{t['term']} {t.get('reading','')} {t['definition']}".lower())
        items.append(f"""<div class="glossary-item" data-search="{haystack}">
        <div class="glossary-item-head">
          <span class="glossary-term">{term}</span>
          {f'<span class="glossary-reading">{reading}</span>' if reading else ''}
          {f'<span class="glossary-category">{category}</span>' if category else ''}
        </div>
        <p class="glossary-def">{definition}</p>
      </div>""")
    list_html = "\n      ".join(items)

    body = f"""
  {masthead("金融用語辞典", archive_url(), glossary_url(), page="glossary")}

  <section class="hero">
    <p class="eyebrow">Glossary</p>
    <h1 class="headline">金融用語辞典</h1>
    <p style="color:var(--ink-soft); max-width:66ch;">{SITE_NAME_A}{SITE_NAME_B}の記事に出てくる用語や、投資の基礎知識をまとめています。気になる言葉を検索してみてください。</p>
  </section>

  <div class="glossary-search-wrap">
    <input type="text" class="glossary-search" id="gsearch" placeholder="用語を検索（例：金利、決算、PER）" autocomplete="off">
    <p class="glossary-count" id="gcount">{len(terms)}件の用語</p>
  </div>

  <section class="glossary-list" id="glist">
    {list_html}
    <p class="glossary-empty" id="gempty">該当する用語が見つかりませんでした。</p>
  </section>

  <footer class="footer">
    <p>{SITE_NAME_A}{SITE_NAME_B}は、公開データと報道をもとに毎営業日自動でまとめている市場概況です。用語辞典は日々の記事をきっかけに少しずつ追加しています。</p>
  </footer>

  <script>
    (function() {{
      var input = document.getElementById('gsearch');
      var items = Array.prototype.slice.call(document.querySelectorAll('.glossary-item'));
      var count = document.getElementById('gcount');
      var empty = document.getElementById('gempty');
      input.addEventListener('input', function() {{
        var q = input.value.trim().toLowerCase();
        var visible = 0;
        items.forEach(function(el) {{
          var match = !q || el.getAttribute('data-search').indexOf(q) !== -1;
          el.style.display = match ? '' : 'none';
          if (match) visible++;
        }});
        count.textContent = visible + '件の用語';
        empty.style.display = visible === 0 ? 'block' : 'none';
      }});
    }})();
  </script>
"""
    return page_shell(f"{SITE_NAME_A}{SITE_NAME_B} — 金融用語辞典", body,
                       description=f"{SITE_NAME_A}{SITE_NAME_B}の記事に出てくる金融用語や投資の基礎知識をまとめた検索可能な用語辞典。",
                       standalone=standalone, canonical_path=glossary_url())
