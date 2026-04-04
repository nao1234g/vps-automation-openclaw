#!/usr/bin/env python3
"""Regression checks for cross-language internal article-link repairs."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import repair_cross_language_article_links as rcl  # noqa: E402


def init_db(db_path: Path) -> None:
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE posts (
          id TEXT PRIMARY KEY,
          slug TEXT,
          type TEXT,
          status TEXT,
          html TEXT,
          published_at TEXT,
          created_at TEXT
        );
        CREATE TABLE tags (
          id TEXT PRIMARY KEY,
          slug TEXT
        );
        CREATE TABLE posts_tags (
          post_id TEXT,
          tag_id TEXT,
          sort_order INTEGER DEFAULT 0
        );
        """
    )
    con.commit()
    con.close()


def add_post(cur: sqlite3.Cursor, post_id: str, slug: str, lang: str, html: str) -> None:
    cur.execute(
        "INSERT INTO posts (id, slug, type, status, html, published_at, created_at) VALUES (?, ?, 'post', 'published', ?, '2026-04-01', '2026-04-01')",
        (post_id, slug, html),
    )
    tag_id = f"tag-{slug}"
    cur.execute("INSERT INTO tags (id, slug) VALUES (?, ?)", (tag_id, f"lang-{lang}"))
    cur.execute("INSERT INTO posts_tags (post_id, tag_id, sort_order) VALUES (?, ?, 0)", (post_id, tag_id))


def test_repair_cross_language_internal_links() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "ghost.db"
        init_db(db_path)
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()

        add_post(
            cur,
            "ja-source",
            "ja-source",
            "ja",
            (
                '<p>関連記事</p><ul>'
                '<li><a href="https://nowpattern.com/en/shared-story/">Shared story</a></li>'
                '<li><a href="https://nowpattern.com/en/en-only-story/">EN only story</a></li>'
                '</ul>'
            ),
        )
        add_post(cur, "ja-shared", "shared-story", "ja", "<p>JA sibling</p>")
        add_post(cur, "en-shared", "en-shared-story", "en", "<p>EN sibling</p>")
        add_post(cur, "en-only", "en-only-story", "en", "<p>EN only</p>")
        add_post(
            cur,
            "en-source",
            "en-source",
            "en",
            '<p>Related patterns: <a href="https://nowpattern.com/shared-story/">Shared story</a></p>',
        )
        con.commit()

        before = rcl.discover_issues(cur)
        assert len(before) == 3, before
        repaired = rcl.apply_issues(cur, before)
        assert repaired == 2, repaired
        con.commit()
        after = rcl.discover_issues(cur)
        assert len(after) == 0, after

        ja_html = cur.execute("SELECT html FROM posts WHERE id = 'ja-source'").fetchone()[0]
        assert 'href="https://nowpattern.com/shared-story/"' in ja_html, ja_html
        assert 'href="https://nowpattern.com/en/only-story/"' in ja_html, ja_html
        assert 'data-cross-lang-link="true"' in ja_html, ja_html
        assert "(EN)" in ja_html, ja_html

        en_html = cur.execute("SELECT html FROM posts WHERE id = 'en-source'").fetchone()[0]
        assert 'href="https://nowpattern.com/en/shared-story/"' in en_html, en_html
        assert 'data-cross-lang-link="true"' not in en_html, en_html
        con.close()


def run() -> None:
    test_repair_cross_language_internal_links()
    print("PASS: repair_cross_language_article_links checks")


if __name__ == "__main__":
    run()
