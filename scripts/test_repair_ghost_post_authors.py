#!/usr/bin/env python3
"""Regression tests for Ghost author integrity repair."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from repair_ghost_post_authors import DEFAULT_AUTHOR_SLUG, discover_default_author_id, missing_author_rows


def assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def create_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute("CREATE TABLE users (id TEXT PRIMARY KEY, slug TEXT)")
    cur.execute("CREATE TABLE posts (id TEXT PRIMARY KEY, slug TEXT, title TEXT, status TEXT, type TEXT, created_at TEXT, published_at TEXT)")
    cur.execute("CREATE TABLE posts_authors (id TEXT PRIMARY KEY, post_id TEXT, author_id TEXT, sort_order INTEGER)")
    cur.execute("INSERT INTO users (id, slug) VALUES ('1', ?)", (DEFAULT_AUTHOR_SLUG,))
    cur.executemany(
        "INSERT INTO posts (id, slug, title, status, type, created_at, published_at) VALUES (?, ?, ?, ?, ?, '2026-04-01', '2026-04-01')",
        [
            ("p1", "first-post", "First", "published", "post"),
            ("p2", "second-post", "Second", "published", "post"),
            ("p3", "draft-post", "Draft", "draft", "post"),
            ("pg1", "predictions", "Predictions", "published", "page"),
        ],
    )
    cur.execute("INSERT INTO posts_authors (id, post_id, author_id, sort_order) VALUES ('pa1', 'p2', '1', 0)")
    con.commit()
    con.close()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "ghost.db"
        create_db(db_path)
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        assert_equal(discover_default_author_id(cur, DEFAULT_AUTHOR_SLUG), "1", "fallback author lookup")
        before = missing_author_rows(cur)
        assert_equal(len(before), 2, "missing author count before repair")
        cur.execute("INSERT INTO posts_authors (id, post_id, author_id, sort_order) VALUES ('pa2', 'p1', '1', 0)")
        cur.execute("INSERT INTO posts_authors (id, post_id, author_id, sort_order) VALUES ('pa3', 'pg1', '1', 0)")
        con.commit()
        after = missing_author_rows(cur)
        assert_equal(len(after), 0, "missing author count after repair")
        con.close()
    print("PASS: repair ghost post authors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
