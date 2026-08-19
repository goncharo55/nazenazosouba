"""
DBから edition / archive のHTMLを生成してファイルに書き出す(publishはこのあと手動でArtifactツールから)。
使い方: python publish_prep.py --date 2026-08-19 [--archive-url https://...]
"""
import argparse
from pathlib import Path
import db
import render

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "config.json"


def load_config():
    import json
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def save_config(cfg):
    import json
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    args = ap.parse_args()

    cfg = load_config()
    archive_url = cfg.get("archive_url")
    glossary_url = cfg.get("glossary_url")

    edition = db.get_edition(args.date)
    if not edition:
        raise SystemExit(f"edition {args.date} not found in DB")

    html = render.build_edition_html(edition, archive_url=archive_url, glossary_url=glossary_url)
    out = BASE / f"edition_{args.date}.html"
    out.write_text(html, encoding="utf-8")
    print("wrote", out)

    editions = db.list_editions()
    archive_html = render.build_archive_html(editions, self_url=archive_url, glossary_url=glossary_url)
    out2 = BASE / "archive.html"
    out2.write_text(archive_html, encoding="utf-8")
    print("wrote", out2)

    terms = db.list_glossary()
    glossary_html = render.build_glossary_html(terms, archive_url=archive_url, self_url=glossary_url)
    out3 = BASE / "glossary.html"
    out3.write_text(glossary_html, encoding="utf-8")
    print("wrote", out3)
