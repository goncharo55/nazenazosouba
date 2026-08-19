"""
なぜなぞ相場: GitHub Pages用の静的サイト一式(docs/)をDBから生成する。

使い方:
  python build_site.py

出力:
  docs/index.html            … 最新記事のミラー(トップページ)
  docs/archive.html          … バックナンバー一覧
  docs/glossary.html         … 用語辞典
  docs/editions/YYYY-MM-DD.html … 各日の記事の固定リンク
  docs/sitemap.xml           … 検索エンジン向けサイトマップ
  docs/robots.txt            … クロール許可 + サイトマップの場所

Artifactツールは使わない。生成後は git add / commit / push するだけで
GitHub Pages(mainブランチのdocs/を配信するよう設定済み)が自動的に反映する。
"""
import db
import render
from datetime import date as _date
from pathlib import Path

BASE = Path(__file__).parent
DOCS = BASE / "docs"
SITE = render.SITE_PUBLIC_URL + render.SITE_ROOT


def main():
    DOCS.mkdir(exist_ok=True)
    (DOCS / "editions").mkdir(exist_ok=True)
    (DOCS / ".nojekyll").touch()  # GitHub PagesにJekyll処理をスキップさせる(素のHTMLをそのまま配信)

    editions_meta = db.list_editions()
    if not editions_meta:
        print("no editions in DB yet, nothing to build")
        return

    latest_date = editions_meta[0]["edition_date"]  # list_editions は新しい順

    for meta in editions_meta:
        d = meta["edition_date"]
        edition = db.get_edition(d)
        html = render.build_edition_html(edition)
        out = DOCS / "editions" / f"{d}.html"
        out.write_text(html, encoding="utf-8")
        print("wrote", out)

    latest_edition = db.get_edition(latest_date)
    index_html = render.build_edition_html(latest_edition)
    (DOCS / "index.html").write_text(index_html, encoding="utf-8")
    print("wrote", DOCS / "index.html", f"(mirrors {latest_date})")

    archive_html = render.build_archive_html(editions_meta)
    (DOCS / "archive.html").write_text(archive_html, encoding="utf-8")
    print("wrote", DOCS / "archive.html")

    terms = db.list_glossary()
    glossary_html = render.build_glossary_html(terms)
    (DOCS / "glossary.html").write_text(glossary_html, encoding="utf-8")
    print("wrote", DOCS / "glossary.html")

    # editions/ の永続URLもDBに記録しておく(将来の参照・整合性チェック用)
    for meta in editions_meta:
        d = meta["edition_date"]
        db.update_artifact_url(d, render.edition_url(d))

    build_sitemap(editions_meta, latest_date)
    build_robots()


def build_sitemap(editions_meta, latest_date):
    today = _date.today().isoformat()
    urls = [
        (f"{SITE}/", today, "daily", "1.0"),
        (f"{SITE}/archive.html", today, "daily", "0.6"),
        (f"{SITE}/glossary.html", today, "weekly", "0.5"),
    ]
    for meta in editions_meta:
        d = meta["edition_date"]
        urls.append((render.SITE_PUBLIC_URL + render.edition_url(d), d, "monthly", "0.8"))

    entries = "\n".join(
        f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod>"
        f"<changefreq>{freq}</changefreq><priority>{pri}</priority></url>"
        for loc, lastmod, freq, pri in urls
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )
    out = DOCS / "sitemap.xml"
    out.write_text(xml, encoding="utf-8")
    print("wrote", out)


def build_robots():
    text = f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n"
    out = DOCS / "robots.txt"
    out.write_text(text, encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
