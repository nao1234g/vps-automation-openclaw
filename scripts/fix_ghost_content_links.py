#!/usr/bin/env python3
"""Normalize stale EN link variants across Ghost sqlite text content."""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path


DEFAULT_GHOST_DB = Path("/var/www/nowpattern/content/data/ghost.db")
TEXT_TYPE_MARKERS = ("CHAR", "CLOB", "TEXT", "VARCHAR", "JSON")
CONTENT_FIELD_HINTS = {
    "html",
    "lexical",
    "mobiledoc",
    "custom_excerpt",
    "canonical_url",
    "meta_title",
    "meta_description",
    "og_title",
    "og_description",
    "twitter_title",
    "twitter_description",
    "codeinjection_head",
    "codeinjection_foot",
    "value",
}

REPLACEMENTS = [
    (
        re.compile(r"(__GHOST_URL__)/en/en-", flags=re.IGNORECASE),
        r"\1/en/",
    ),
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
        re.compile(r"(__GHOST_URL__)/en-predictions/", flags=re.IGNORECASE),
        r"\1/en/predictions/",
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


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def replace_text(value: str) -> tuple[str, int]:
    total = 0
    updated = value
    for pattern, replacement in REPLACEMENTS:
        updated, count = pattern.subn(replacement, updated)
        total += count
    return updated, total


def list_user_tables(cur: sqlite3.Cursor) -> list[str]:
    rows = cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows if isinstance(row[0], str)]


def discover_text_columns(cur: sqlite3.Cursor, table_name: str) -> tuple[list[str], list[str]]:
    pragma = list(cur.execute(f"PRAGMA table_info({quote_ident(table_name)})"))
    text_columns: list[str] = []
    primary_key_columns: list[tuple[int, str]] = []

    for row in pragma:
        column_name = row[1]
        column_type = str(row[2] or "").upper()
        pk_order = int(row[5] or 0)
        is_text_like = any(marker in column_type for marker in TEXT_TYPE_MARKERS) or column_name in CONTENT_FIELD_HINTS
        if is_text_like:
            text_columns.append(column_name)
        if pk_order:
            primary_key_columns.append((pk_order, column_name))

    primary_keys = [column_name for _, column_name in sorted(primary_key_columns)]
    return text_columns, primary_keys


def scan_and_fix_table(cur: sqlite3.Cursor, table_name: str, dry_run: bool) -> dict:
    text_columns, primary_keys = discover_text_columns(cur, table_name)
    if not text_columns:
        return {
            "table": table_name,
            "rows_changed": 0,
            "replacement_hits": 0,
            "field_counts": {},
        }

    key_columns = primary_keys or ["rowid"]
    if primary_keys:
        select_columns = [quote_ident(column) for column in key_columns] + [quote_ident(column) for column in text_columns]
    else:
        select_columns = ['rowid AS "__rowid__"'] + [quote_ident(column) for column in text_columns]

    select_sql = f"SELECT {', '.join(select_columns)} FROM {quote_ident(table_name)}"
    rows = list(cur.execute(select_sql))
    field_counts = {column: 0 for column in text_columns}
    rows_changed = 0
    replacement_hits = 0

    key_count = len(primary_keys) if primary_keys else 1
    quoted_keys = [quote_ident(column) for column in primary_keys] if primary_keys else ["rowid"]

    for row in rows:
        key_values = list(row[:key_count])
        values = list(row[key_count:])
        updates: dict[str, str] = {}
        row_hits = 0

        for index, column in enumerate(text_columns):
            current = values[index]
            if not isinstance(current, str) or not current:
                continue
            updated, hits = replace_text(current)
            if hits <= 0 or updated == current:
                continue
            updates[column] = updated
            field_counts[column] += hits
            row_hits += hits

        if not updates:
            continue

        rows_changed += 1
        replacement_hits += row_hits
        if dry_run:
            continue

        assignments = ", ".join(f"{quote_ident(column)} = ?" for column in updates)
        where_clause = " AND ".join(f"{column} = ?" for column in quoted_keys)
        payload = list(updates.values()) + key_values
        cur.execute(
            f"UPDATE {quote_ident(table_name)} SET {assignments} WHERE {where_clause}",
            payload,
        )

    return {
        "table": table_name,
        "rows_changed": rows_changed,
        "replacement_hits": replacement_hits,
        "field_counts": {key: value for key, value in field_counts.items() if value},
    }


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Fix stale EN Ghost content links in ghost.db.")
    parser.add_argument("--db", default=str(DEFAULT_GHOST_DB), help="Path to ghost.db")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    parser.add_argument("--quiet", action="store_true", help="Suppress no-op output")
    parser.add_argument(
        "--table",
        action="append",
        help="Only scan the named table. Can be passed multiple times.",
    )
    parser.add_argument(
        "--exclude-table",
        action="append",
        help="Skip the named table. Can be passed multiple times.",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise FileNotFoundError(f"ghost db not found: {db_path}")

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    include_tables = set(args.table or [])
    exclude_tables = set(args.exclude_table or [])
    table_names = [
        table_name
        for table_name in list_user_tables(cur)
        if (not include_tables or table_name in include_tables) and table_name not in exclude_tables
    ]
    table_stats = [scan_and_fix_table(cur, table_name, args.dry_run) for table_name in table_names]
    total_rows = sum(int(item["rows_changed"]) for item in table_stats)
    total_hits = sum(int(item["replacement_hits"]) for item in table_stats)

    if not args.dry_run and total_rows:
        con.commit()
    con.close()

    if not total_rows and args.quiet:
        return 0

    mode = "DRY RUN" if args.dry_run else "OK"
    print(f"{mode}: normalized Ghost content links in {db_path}")
    print(f"  rows_changed={total_rows} replacement_hits={total_hits}")
    for item in table_stats:
        if item["field_counts"]:
            print(f"  {item['table']}={item['field_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
