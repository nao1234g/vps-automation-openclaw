#!/usr/bin/env python3
"""Audit and repair published Ghost posts that are missing a primary author."""

from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
import sys
from pathlib import Path


DEFAULT_GHOST_DB = Path("/var/www/nowpattern/content/data/ghost.db")
DEFAULT_AUTHOR_SLUG = "naoto"


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def discover_default_author_id(cur: sqlite3.Cursor, author_slug: str) -> str:
    row = cur.execute("SELECT id FROM users WHERE slug = ? LIMIT 1", (author_slug,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"default author slug not found: {author_slug}")
    return str(row[0])


def missing_author_rows(cur: sqlite3.Cursor) -> list[tuple[str, str, str]]:
    return list(
        cur.execute(
            """
            SELECT p.id, p.slug, p.title
            FROM posts p
            LEFT JOIN posts_authors pa ON p.id = pa.post_id
            LEFT JOIN users u ON pa.author_id = u.id
            WHERE p.status = 'published'
              AND p.type IN ('post', 'page')
            GROUP BY p.id, p.slug, p.title
            HAVING COUNT(u.id) = 0
            ORDER BY p.published_at DESC, p.created_at DESC
            """
        )
    )


def attach_default_author(cur: sqlite3.Cursor, post_id: str, author_id: str) -> None:
    relation_id = secrets.token_hex(12)
    cur.execute(
        """
        INSERT INTO posts_authors (id, post_id, author_id, sort_order)
        VALUES (?, ?, ?, 0)
        """,
        (relation_id, post_id, author_id),
    )


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Repair published Ghost posts that are missing authors.")
    parser.add_argument("--db", default=str(DEFAULT_GHOST_DB), help="Path to ghost.db")
    parser.add_argument("--author-slug", default=DEFAULT_AUTHOR_SLUG, help="Fallback Ghost author slug")
    parser.add_argument("--audit-only", action="store_true", help="Only report missing authors and exit non-zero if any remain")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise FileNotFoundError(f"ghost db not found: {db_path}")

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    fallback_author_id = discover_default_author_id(cur, args.author_slug)
    before = missing_author_rows(cur)
    repaired = 0
    if not args.audit_only:
        for post_id, _, _ in before:
            attach_default_author(cur, post_id, fallback_author_id)
            repaired += 1
        if repaired:
            con.commit()
    after = missing_author_rows(cur)
    con.close()

    report = {
        "db": str(db_path),
        "author_slug": args.author_slug,
        "fallback_author_id": fallback_author_id,
        "missing_before": len(before),
        "repaired": repaired,
        "missing_after": len(after),
        "samples_before": [{"id": row[0], "slug": row[1], "title": row[2]} for row in before[:10]],
        "samples_after": [{"id": row[0], "slug": row[1], "title": row[2]} for row in after[:10]],
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if len(after) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
