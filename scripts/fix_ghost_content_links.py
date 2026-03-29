#!/usr/bin/env python3
"""Normalize stale EN link variants inside Ghost sqlite content fields."""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path


DEFAULT_GHOST_DB = Path("/var/www/nowpattern/content/data/ghost.db")
CONTENT_FIELDS = [
    "html",
    "lexical",
    "mobiledoc",
    "custom_excerpt",
    "canonical_url",
    "codeinjection_head",
    "codeinjection_foot",
]

REPLACEMENTS = [
    (
        re.compile(r"(https?://(?:www\.)?nowpattern\.com)/en/en-", flags=re.IGNORECASE),
        r"\1/en/",
    ),
    (
        re.compile(r'((?:href|src|content)=["\'])/en/en-', flags=re.IGNORECASE),
        r"\1/en/",
    ),
    (
        re.compile(r"(?<![A-Za-z0-9_-])/en/en-"),
        "/en/",
    ),
    (
        re.compile(r"(https?://(?:www\.)?nowpattern\.com)/en-predictions/", flags=re.IGNORECASE),
        r"\1/en/predictions/",
    ),
    (
        re.compile(r"(?<![A-Za-z0-9_-])/en-predictions/"),
        "/en/predictions/",
    ),
]


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def replace_text(value: str) -> tuple[str, int]:
    total = 0
    updated = value
    for pattern, replacement in REPLACEMENTS:
        updated, count = pattern.subn(replacement, updated)
        total += count
    return updated, total


def existing_content_fields(cur: sqlite3.Cursor, table_name: str) -> list[str]:
    rows = list(cur.execute(f"PRAGMA table_info({table_name})"))
    columns = {row[1] for row in rows}
    return [field for field in CONTENT_FIELDS if field in columns]


def fix_content_table(cur: sqlite3.Cursor, table_name: str, dry_run: bool) -> dict:
    fields = existing_content_fields(cur, table_name)
    if not fields:
        return {"rows_changed": 0, "replacement_hits": 0, "field_counts": {}}

    slug_column = "slug" if "slug" in {row[1] for row in cur.execute(f"PRAGMA table_info({table_name})")} else "id"
    select_sql = "SELECT id, " + slug_column + ", " + ", ".join(fields) + f" FROM {table_name}"
    field_counts = {field: 0 for field in fields}
    rows_changed = 0
    replacement_hits = 0

    for row in cur.execute(select_sql):
        post_id = row[0]
        values = list(row[2:])
        updates: dict[str, str] = {}
        row_hits = 0
        for index, field in enumerate(fields):
            current = values[index]
            if not isinstance(current, str) or not current:
                continue
            updated, hits = replace_text(current)
            if hits <= 0 or updated == current:
                continue
            updates[field] = updated
            field_counts[field] += hits
            row_hits += hits

        if not updates:
            continue

        rows_changed += 1
        replacement_hits += row_hits
        if dry_run:
            continue

        assignments = ", ".join(f"{field} = ?" for field in updates)
        payload = list(updates.values()) + [post_id]
        cur.execute(f"UPDATE {table_name} SET {assignments} WHERE id = ?", payload)

    return {
        "rows_changed": rows_changed,
        "replacement_hits": replacement_hits,
        "field_counts": field_counts,
    }


def fix_settings(cur: sqlite3.Cursor, dry_run: bool) -> dict:
    rows_changed = 0
    replacement_hits = 0
    field_counts: dict[str, int] = {}

    rows = list(
        cur.execute(
            """
            SELECT key, value
            FROM settings
            WHERE key IN ('codeinjection_head', 'codeinjection_foot')
            """
        )
    )
    for key, current in rows:
        if not isinstance(current, str) or not current:
            continue
        updated, hits = replace_text(current)
        if hits <= 0 or updated == current:
            continue
        rows_changed += 1
        replacement_hits += hits
        field_counts[key] = hits
        if dry_run:
            continue
        cur.execute("UPDATE settings SET value = ? WHERE key = ?", (updated, key))

    return {
        "rows_changed": rows_changed,
        "replacement_hits": replacement_hits,
        "field_counts": field_counts,
    }


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Fix stale EN Ghost content links in ghost.db.")
    parser.add_argument("--db", default=str(DEFAULT_GHOST_DB), help="Path to ghost.db")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    parser.add_argument("--quiet", action="store_true", help="Suppress no-op output")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise FileNotFoundError(f"ghost db not found: {db_path}")

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    post_stats = fix_content_table(cur, "posts", args.dry_run)
    page_stats = fix_content_table(cur, "pages", args.dry_run)
    settings_stats = fix_settings(cur, args.dry_run)
    total_rows = post_stats["rows_changed"] + page_stats["rows_changed"] + settings_stats["rows_changed"]
    total_hits = post_stats["replacement_hits"] + page_stats["replacement_hits"] + settings_stats["replacement_hits"]

    if not args.dry_run and total_rows:
        con.commit()
    con.close()

    if not total_rows and args.quiet:
        return 0

    mode = "DRY RUN" if args.dry_run else "OK"
    print(f"{mode}: normalized Ghost content links in {db_path}")
    print(f"  rows_changed={total_rows} replacement_hits={total_hits}")
    if post_stats["field_counts"]:
        print(f"  posts={post_stats['field_counts']}")
    if page_stats["field_counts"]:
        print(f"  pages={page_stats['field_counts']}")
    if settings_stats["field_counts"]:
        print(f"  settings={settings_stats['field_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
