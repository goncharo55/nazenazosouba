"""
そうばノート: 記事アーカイブDB (SQLite)

スキーマ:
  editions(edition_date PK, headline, eyebrow, summary_json, tags_json,
           narrative_json, lesson_title, lesson_body, sources_note,
           artifact_url, generated_at)
  indices(edition_date, ticker, name, value_text, delta, pct)
  movers(edition_date, market, ticker, name, pct, reason, kind)

使い方(CLI):
  python db.py init
  python db.py save --json edition.json      # edition.json は build_edition() が返す形式
  python db.py list                          # 過去記事一覧(新しい順)
  python db.py get --date 2026-08-19
"""
import argparse
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
DB_PATH = BASE / "data" / "archive.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS editions (
    edition_date TEXT PRIMARY KEY,
    headline TEXT NOT NULL,
    eyebrow TEXT,
    summary_json TEXT,
    tags_json TEXT,
    narrative_json TEXT,
    lesson_title TEXT,
    lesson_body TEXT,
    sources_note TEXT,
    artifact_url TEXT,  -- 実体は公開URL(GitHub Pages: render.edition_url()の値)。列名は歴史的経緯で旧名のまま
    generated_at TEXT
);
CREATE TABLE IF NOT EXISTS indices (
    edition_date TEXT NOT NULL,
    ticker TEXT,
    name TEXT,
    value_text TEXT,
    delta REAL,
    pct REAL,
    FOREIGN KEY(edition_date) REFERENCES editions(edition_date)
);
CREATE TABLE IF NOT EXISTS movers (
    edition_date TEXT NOT NULL,
    market TEXT,       -- 'US' | 'JP' | 'GLOBAL'
    ticker TEXT,
    name TEXT,
    pct REAL,
    reason TEXT,
    kind TEXT,          -- 'equity' | 'crypto' | 'fx' | 'commodity' | 'future'
    FOREIGN KEY(edition_date) REFERENCES editions(edition_date)
);
CREATE INDEX IF NOT EXISTS idx_indices_date ON indices(edition_date);
CREATE INDEX IF NOT EXISTS idx_movers_date ON movers(edition_date);

CREATE TABLE IF NOT EXISTS glossary (
    term TEXT PRIMARY KEY,
    reading TEXT,        -- 読み仮名(五十音順ソート用)
    category TEXT,       -- '指標' | '企業行動' | '経済' | '取引の基礎' など
    definition TEXT NOT NULL,
    added_date TEXT,
    related_edition_date TEXT
);
"""


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"initialized {DB_PATH}")


def save_edition(edition: dict):
    """edition dict の想定キー:
    edition_date, headline, eyebrow, summary(list[str]), tags(list[str]),
    narrative({"us":..., "jp":..., ...}), lesson_title, lesson_body,
    sources_note, artifact_url, generated_at,
    indices(list[{ticker,name,value_text,delta,pct}]),
    movers(list[{market,ticker,name,pct,reason,kind}])
    """
    conn = get_conn()
    conn.execute("DELETE FROM editions WHERE edition_date = ?", (edition["edition_date"],))
    conn.execute("DELETE FROM indices WHERE edition_date = ?", (edition["edition_date"],))
    conn.execute("DELETE FROM movers WHERE edition_date = ?", (edition["edition_date"],))
    conn.execute(
        """INSERT INTO editions
           (edition_date, headline, eyebrow, summary_json, tags_json, narrative_json,
            lesson_title, lesson_body, sources_note, artifact_url, generated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            edition["edition_date"], edition["headline"], edition.get("eyebrow", ""),
            json.dumps(edition.get("summary", []), ensure_ascii=False),
            json.dumps(edition.get("tags", []), ensure_ascii=False),
            json.dumps(edition.get("narrative", {}), ensure_ascii=False),
            edition.get("lesson_title", ""), edition.get("lesson_body", ""),
            edition.get("sources_note", ""), edition.get("artifact_url", ""),
            edition.get("generated_at", ""),
        ),
    )
    for r in edition.get("indices", []):
        conn.execute(
            "INSERT INTO indices (edition_date, ticker, name, value_text, delta, pct) VALUES (?,?,?,?,?,?)",
            (edition["edition_date"], r.get("ticker"), r.get("name"), r.get("value_text"),
             r.get("delta"), r.get("pct")),
        )
    for r in edition.get("movers", []):
        conn.execute(
            "INSERT INTO movers (edition_date, market, ticker, name, pct, reason, kind) VALUES (?,?,?,?,?,?,?)",
            (edition["edition_date"], r.get("market"), r.get("ticker"), r.get("name"),
             r.get("pct"), r.get("reason"), r.get("kind", "equity")),
        )
    conn.commit()
    conn.close()
    print(f"saved edition {edition['edition_date']}")


def list_editions(limit=365):
    conn = get_conn()
    rows = conn.execute(
        "SELECT edition_date, headline, artifact_url, generated_at FROM editions "
        "ORDER BY edition_date DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_edition(edition_date: str):
    conn = get_conn()
    e = conn.execute("SELECT * FROM editions WHERE edition_date = ?", (edition_date,)).fetchone()
    if not e:
        conn.close()
        return None
    e = dict(e)
    e["summary"] = json.loads(e.pop("summary_json") or "[]")
    e["tags"] = json.loads(e.pop("tags_json") or "[]")
    e["narrative"] = json.loads(e.pop("narrative_json") or "{}")
    e["indices"] = [dict(r) for r in conn.execute(
        "SELECT ticker, name, value_text, delta, pct FROM indices WHERE edition_date = ?", (edition_date,))]
    e["movers"] = [dict(r) for r in conn.execute(
        "SELECT market, ticker, name, pct, reason, kind FROM movers WHERE edition_date = ?", (edition_date,))]
    conn.close()
    return e


def update_artifact_url(edition_date: str, url: str):
    conn = get_conn()
    conn.execute("UPDATE editions SET artifact_url = ? WHERE edition_date = ?", (url, edition_date))
    conn.commit()
    conn.close()


def upsert_glossary_terms(terms: list[dict]):
    """terms: [{term, reading, category, definition, added_date, related_edition_date}]
    既存の term は上書きしない(初出の説明を尊重する)。新しい term だけ追加する。"""
    conn = get_conn()
    added = []
    for t in terms:
        exists = conn.execute("SELECT 1 FROM glossary WHERE term = ?", (t["term"],)).fetchone()
        if exists:
            continue
        conn.execute(
            "INSERT INTO glossary (term, reading, category, definition, added_date, related_edition_date) "
            "VALUES (?,?,?,?,?,?)",
            (t["term"], t.get("reading", ""), t.get("category", ""), t["definition"],
             t.get("added_date", ""), t.get("related_edition_date", "")),
        )
        added.append(t["term"])
    conn.commit()
    conn.close()
    return added


def list_glossary():
    conn = get_conn()
    rows = conn.execute(
        "SELECT term, reading, category, definition, added_date FROM glossary ORDER BY reading, term"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    p_save = sub.add_parser("save")
    p_save.add_argument("--json", required=True)
    sub.add_parser("list")
    p_get = sub.add_parser("get")
    p_get.add_argument("--date", required=True)
    p_url = sub.add_parser("set-url")
    p_url.add_argument("--date", required=True)
    p_url.add_argument("--url", required=True)
    p_gloss = sub.add_parser("add-glossary")
    p_gloss.add_argument("--json", required=True, help="glossary terms JSON配列ファイル")
    sub.add_parser("list-glossary")

    args = ap.parse_args()
    if args.cmd == "init":
        init_db()
    elif args.cmd == "save":
        save_edition(json.loads(Path(args.json).read_text(encoding="utf-8")))
    elif args.cmd == "list":
        for e in list_editions():
            print(e["edition_date"], "-", e["headline"], "-", e["artifact_url"])
    elif args.cmd == "get":
        e = get_edition(args.date)
        print(json.dumps(e, ensure_ascii=False, indent=2) if e else "not found")
    elif args.cmd == "set-url":
        update_artifact_url(args.date, args.url)
        print("ok")
    elif args.cmd == "add-glossary":
        terms = json.loads(Path(args.json).read_text(encoding="utf-8"))
        added = upsert_glossary_terms(terms)
        print(f"added {len(added)} new terms: {added}")
    elif args.cmd == "list-glossary":
        for g in list_glossary():
            print(g["term"], "-", g["definition"][:40])
