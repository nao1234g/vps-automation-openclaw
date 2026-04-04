#!/usr/bin/env python3
"""Regression tests for repair_internal_draft_links.py."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from repair_internal_draft_links import apply_repairs, discover_issues


def create_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE posts (
            id TEXT PRIMARY KEY,
            slug TEXT,
            title TEXT,
            type TEXT,
            status TEXT,
            html TEXT,
            codeinjection_head TEXT,
            codeinjection_foot TEXT,
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
    cur.executemany(
        """
        INSERT INTO posts (id, slug, title, type, status, html, codeinjection_head, codeinjection_foot, published_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, '', '', '2026-04-01', '2026-04-01')
        """,
        [
            (
                "1",
                "source-post",
                "Source",
                "post",
                "published",
                '<p><a href="https://nowpattern.com/en/us-china-paris-trade-talks-tariffs-and-rare-earth-2/">bad</a></p>',
            ),
            (
                "2",
                "us-china-paris-trade-talks-tariffs-and-rare-earth-2",
                "Draft target",
                "post",
                "draft",
                "<p>draft</p>",
            ),
            (
                "3",
                "us-china-paris-trade-talks-tariffs-and-rare-earth",
                "Published target",
                "post",
                "published",
                "<p>ok</p>",
            ),
            (
                "4",
                "source-page",
                "Source page",
                "page",
                "published",
                '<p><a href="__GHOST_URL__/en/the-deeper-meaning-behind-the-feds/">bad2</a></p>',
            ),
            (
                "5",
                "the-deeper-meaning-behind-the-feds",
                "Draft prefix target",
                "post",
                "draft",
                "<p>draft</p>",
            ),
            (
                "6",
                "the-deeper-meaning-behind-the-feds-rate-cut-freeze",
                "Published longer target",
                "post",
                "published",
                "<p>ok</p>",
            ),
            (
                "7",
                "unresolved-source",
                "Unresolved source",
                "post",
                "published",
                '<p><a href="https://nowpattern.com/en/no-replacement-draft/">bad3</a></p>',
            ),
            (
                "8",
                "no-replacement-draft",
                "No replacement draft",
                "post",
                "draft",
                "<p>draft</p>",
            ),
            (
                "9",
                "old-style-en-source",
                "Old style EN source",
                "post",
                "published",
                '<p><a href="__GHOST_URL__/en-yemen-port-siege-iran-saudi-proxy-war-threatens-global-oil-chokepoint/">bad4</a></p>',
            ),
            (
                "10",
                "en-yemen-port-siege-iran-saudi-proxy-war-threatens-global-oil-chokepoint",
                "Old style EN draft",
                "post",
                "draft",
                "<p>draft</p>",
            ),
            (
                "11",
                "en-yemen-port-siege-iran-saudi-proxy-war-threatens-global-oil-chokepoint-2",
                "Old style EN published replacement",
                "post",
                "published",
                "<p>ok</p>",
            ),
            (
                "12",
                "missing-slug-source",
                "Missing slug source",
                "post",
                "published",
                '<p><a href="__GHOST_URL__/en-bei-zhao-xian-xin-xing-misairuri-ben-shang-kong-tong-guo-dui-li-noluo-xuan-gasheng-mudong-aziajun-kuo-nolin-jie-dian/">North Korean New Missile Overflies Japan — East Asia Arms Race</a></p>',
            ),
            (
                "13",
                "north-korean-new-missile-overflies-japan-east-asia-arms-race",
                "North Korean New Missile Overflies Japan — East Asia Arms Race",
                "post",
                "published",
                "<p>ok</p>",
            ),
            (
                "14",
                "missing-unresolved-source",
                "Missing unresolved source",
                "post",
                "published",
                '<p><a href="https://nowpattern.com/en/dragonfly-650mdiao-da-jue-mie-nozhong-deni-zhang-risuruvcnogou-zao/">Dragonfly Raises $650M — The Structure of VCs Contrarian in the Midst of \"Extinction\"</a></p>',
            ),
            (
                "15",
                "tag-link-source",
                "Tag link source",
                "post",
                "published",
                '<p><a href="__GHOST_URL__/tag/">Tag</a></p>',
            ),
            (
                "16",
                "genre-link-source",
                "Genre link source",
                "post",
                "published",
                '<p><a href="__GHOST_URL__/genre-geopolitics-10/">Genre</a></p>',
            ),
            (
                "17",
                "english-source",
                "English source",
                "post",
                "published",
                '<p><a href="https://nowpattern.com/english-target/">wrong-root</a> '
                '<a href="https://nowpattern.com/en/english-target/">already-right</a></p>',
            ),
            (
                "18",
                "english-target",
                "English target",
                "post",
                "published",
                "<p>ok</p>",
            ),
            (
                "19",
                "templated-en-source",
                "Templated EN source",
                "post",
                "published",
                '<p><a href="__GHOST_URL__/en/english-target/">templated-right</a></p>',
            ),
            (
                "20",
                "legacy-genre-article-link-source",
                "Legacy genre article link source",
                "post",
                "published",
                '<p><a href="__GHOST_URL__/genre-geopolitics-10/us-sinks-iranian-warship-the-escalation-spiral-nobody-can-exit/">legacy</a></p>',
            ),
            (
                "21",
                "us-sinks-iranian-warship-the-escalation-spiral-nobody-can-exit",
                "Legacy target draft",
                "post",
                "draft",
                "<p>draft</p>",
            ),
            (
                "22",
                "us-sinks-iranian-warship-the-escalation-spiral-nobody-can-exit-2",
                "Legacy target published replacement",
                "post",
                "published",
                "<p>ok</p>",
            ),
        ],
    )
    cur.executemany(
        "INSERT INTO tags (id, slug) VALUES (?, ?)",
        [
            ("t-en", "lang-en"),
        ],
    )
    cur.executemany(
        "INSERT INTO posts_tags (post_id, tag_id, sort_order) VALUES (?, ?, ?)",
        [
            ("17", "t-en", 0),
            ("18", "t-en", 0),
            ("19", "t-en", 0),
        ],
    )
    con.commit()
    con.close()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ghost.db"
        create_db(db_path)
        con = sqlite3.connect(str(db_path))
        try:
            cur = con.cursor()
            before = discover_issues(cur)
            assert len(before) == 8, before
            repaired = apply_repairs(cur, before)
            assert repaired == 8, repaired
            con.commit()
            after = discover_issues(cur)
            assert len(after) == 0, after

            html_source = cur.execute("SELECT html FROM posts WHERE id='1'").fetchone()[0]
            assert "rare-earth-2" not in html_source, html_source
            assert "rare-earth/" in html_source, html_source

            html_page = cur.execute("SELECT html FROM posts WHERE id='4'").fetchone()[0]
            assert "the-deeper-meaning-behind-the-feds/" not in html_page, html_page
            assert "the-deeper-meaning-behind-the-feds-rate-cut-freeze/" in html_page, html_page

            unresolved_html = cur.execute("SELECT html FROM posts WHERE id='7'").fetchone()[0]
            assert "no-replacement-draft" not in unresolved_html, unresolved_html
            assert "data-removed-draft-link" in unresolved_html, unresolved_html

            old_style_en_html = cur.execute("SELECT html FROM posts WHERE id='9'").fetchone()[0]
            assert "/en-yemen-port-siege-iran-saudi-proxy-war-threatens-global-oil-chokepoint/" not in old_style_en_html, old_style_en_html
            assert "/en/yemen-port-siege-iran-saudi-proxy-war-threatens-global-oil-chokepoint-2/" in old_style_en_html, old_style_en_html

            missing_slug_html = cur.execute("SELECT html FROM posts WHERE id='12'").fetchone()[0]
            assert "/en-bei-zhao-xian-xin-xing-misairuri-ben-shang-kong-tong-guo-dui-li-noluo-xuan-gasheng-mudong-aziajun-kuo-nolin-jie-dian/" not in missing_slug_html, missing_slug_html
            assert "/north-korean-new-missile-overflies-japan-east-asia-arms-race/" in missing_slug_html, missing_slug_html

            unresolved_missing_html = cur.execute("SELECT html FROM posts WHERE id='14'").fetchone()[0]
            assert "dragonfly-650mdiao-da-jue-mie-nozhong-deni-zhang-risuruvcnogou-zao" not in unresolved_missing_html, unresolved_missing_html
            assert "data-removed-draft-link" in unresolved_missing_html, unresolved_missing_html

            english_source_html = cur.execute("SELECT html FROM posts WHERE id='17'").fetchone()[0]
            assert 'https://nowpattern.com/en/english-target/' in english_source_html, english_source_html
            assert 'https://nowpattern.com/english-target/' not in english_source_html, english_source_html

            templated_en_html = cur.execute("SELECT html FROM posts WHERE id='19'").fetchone()[0]
            assert '__GHOST_URL__/en/english-target/' in templated_en_html, templated_en_html

            legacy_genre_html = cur.execute("SELECT html FROM posts WHERE id='20'").fetchone()[0]
            assert "/genre-geopolitics-10/us-sinks-iranian-warship-the-escalation-spiral-nobody-can-exit/" not in legacy_genre_html, legacy_genre_html
            assert "/us-sinks-iranian-warship-the-escalation-spiral-nobody-can-exit-2/" in legacy_genre_html, legacy_genre_html
        finally:
            con.close()

    print("PASS: repair_internal_draft_links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
