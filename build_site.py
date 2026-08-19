"""
なぜなぞ相場: GitHub Pages用の静的サイト一式(docs/)をDBから生成する。

使い方:
  python build_site.py

出力:
  docs/index.html            … 最新記事のミラー(トップページ)
  docs/archive.html          … バックナンバー一覧
  docs/glossary.html         … 用語辞典
  docs/editions/YYYY-MM-DD.html … 各日の記事の固定リンク

Artifactツールは使わない。生成後は git add / commit / push するだけで
GitHub Pages(mainブランチのdocs/を配信するよう設定済み)が自動的に反映する。
"""
import db
import render
from pathlib import Path

BASE = Path(__file__).parent
DOCS = BASE / "docs"


def main():
    DOCS.mkdir(exist_ok=True)
    (DOCS / "editions").mkdir(exist_ok=True)

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


if __name__ == "__main__":
    main()
