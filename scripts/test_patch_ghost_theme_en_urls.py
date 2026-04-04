#!/usr/bin/env python3
"""Regression tests for Ghost theme EN URL patcher."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from patch_ghost_theme_en_urls import (
    CARD_NEW,
    CARD_OLD,
    JSONLD_NEW,
    JSONLD_OLD,
    PAGE_EN_EXTENDS,
    PAGE_TEMPLATE_PATH,
    ensure_prediction_methodology_routes,
    ensure_en_page_template,
    normalize_en_canonical_urls,
    patch_theme_file,
    patch_routes_for_en_pages,
)


def assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def build_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE posts (
            id TEXT PRIMARY KEY,
            slug TEXT,
            status TEXT,
            canonical_url TEXT
        )
        """
    )
    cur.executemany(
        "INSERT INTO posts (id, slug, status, canonical_url) VALUES (?, ?, ?, ?)",
        [
            ("1", "en-example-story", "published", None),
            ("2", "en-already-good", "published", "https://nowpattern.com/en/already-good/"),
            ("3", "ja-story", "published", None),
            ("4", "en-draft-story", "draft", None),
        ],
    )
    con.commit()
    con.close()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        db_path = root / "ghost.db"
        build_db(db_path)

        theme_root = root / "theme"
        (theme_root / "partials").mkdir(parents=True)
        page_hbs = theme_root / PAGE_TEMPLATE_PATH
        post_card = theme_root / "partials" / "post-card.hbs"
        post_hbs = theme_root / "post.hbs"
        routes_yaml = root / "routes.yaml"
        page_hbs.write_text(
            "{{!< default}}\n<main><article>{{content}}</article></main>\n",
            encoding="utf-8",
        )
        post_card.write_text(CARD_OLD + "\n", encoding="utf-8")
        post_hbs.write_text(JSONLD_OLD + "\n", encoding="utf-8")
        routes_yaml.write_text(
            "\n".join(
                [
                    "routes:",
                    "  /about/:",
                    "    data: page.about",
                    "    template: page",
                    "  /en/about/:",
                    "    data: page.en-about",
                    "    template: page",
                    "  /en/predictions/:",
                    "    data: page.en-predictions",
                    "    template: page",
                    "  /en/leaderboard/:",
                    "    data: page.en-leaderboard",
                    "    template: page",
                    "collections:",
                    "  /en/:",
                    "    permalink: /en/{slug}/",
                    "    filter: tag:lang-en",
                    "    template: index-en",
                    "taxonomies:",
                    "  tag: /tag/{slug}/",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        db_changes = normalize_en_canonical_urls(db_path, "https://nowpattern.com", dry_run=False)
        assert_equal(db_changes["published_en_posts"], 2, "published EN post count")
        assert_equal(db_changes["canonical_urls_changed"], 1, "canonical_url changed count")

        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        cur.execute("SELECT canonical_url FROM posts WHERE id='1'")
        assert_equal(cur.fetchone()[0], "https://nowpattern.com/en/example-story/", "canonical url normalized")
        cur.execute("SELECT canonical_url FROM posts WHERE id='2'")
        assert_equal(cur.fetchone()[0], "https://nowpattern.com/en/already-good/", "existing canonical preserved")
        cur.execute("SELECT canonical_url FROM posts WHERE id='4'")
        assert_equal(cur.fetchone()[0], None, "draft post untouched")
        con.close()

        card_result = patch_theme_file(post_card, [(CARD_OLD, CARD_NEW)], dry_run=False)
        post_result = patch_theme_file(post_hbs, [(JSONLD_OLD, JSONLD_NEW)], dry_run=False)
        page_en_result = ensure_en_page_template(theme_root, dry_run=False)
        methodology_routes_result = ensure_prediction_methodology_routes(routes_yaml, dry_run=False)
        routes_result = patch_routes_for_en_pages(routes_yaml, dry_run=False)
        assert_equal(card_result.changed, True, "post-card patched")
        assert_equal(post_result.changed, True, "post.hbs patched")
        assert_equal(page_en_result.changed, True, "page-en created")
        assert_equal(methodology_routes_result.changed, True, "methodology routes inserted")
        assert_equal(routes_result.changed, True, "routes patched for EN pages")
        if CARD_NEW not in post_card.read_text(encoding="utf-8"):
            raise AssertionError("post-card missing canonical_url fallback")
        if JSONLD_NEW not in post_hbs.read_text(encoding="utf-8"):
            raise AssertionError("post.hbs missing canonical_url fallback")
        page_en_hbs = theme_root / "page-en.hbs"
        if PAGE_EN_EXTENDS not in page_en_hbs.read_text(encoding="utf-8"):
            raise AssertionError("page-en.hbs missing default-en layout")
        routes_after = routes_yaml.read_text(encoding="utf-8")
        if "data: page.en-about\n    template: page-en" not in routes_after:
            raise AssertionError("en-about route not switched to page-en")
        if "data: page.en-predictions\n    template: page-en" not in routes_after:
            raise AssertionError("en-predictions route not switched to page-en")
        if "data: page.en-leaderboard\n    template: page-en" not in routes_after:
            raise AssertionError("en-leaderboard route not switched to page-en")
        if "data: page.en-forecasting-methodology\n    template: page-en" not in routes_after:
            raise AssertionError("en-forecasting-methodology route not switched to page-en")
        if "data: page.en-forecast-scoring-and-resolution\n    template: page-en" not in routes_after:
            raise AssertionError("en-forecast-scoring-and-resolution route not switched to page-en")
        if "data: page.en-forecast-integrity-and-audit\n    template: page-en" not in routes_after:
            raise AssertionError("en-forecast-integrity-and-audit route not switched to page-en")
        if "data: page.about\n    template: page-en" in routes_after:
            raise AssertionError("ja page route should not switch to page-en")

        card_result_second = patch_theme_file(post_card, [(CARD_OLD, CARD_NEW)], dry_run=False)
        post_result_second = patch_theme_file(post_hbs, [(JSONLD_OLD, JSONLD_NEW)], dry_run=False)
        page_en_result_second = ensure_en_page_template(theme_root, dry_run=False)
        methodology_routes_result_second = ensure_prediction_methodology_routes(routes_yaml, dry_run=False)
        routes_result_second = patch_routes_for_en_pages(routes_yaml, dry_run=False)
        assert_equal(card_result_second.changed, False, "post-card patch idempotent")
        assert_equal(post_result_second.changed, False, "post.hbs patch idempotent")
        assert_equal(page_en_result_second.changed, False, "page-en patch idempotent")
        assert_equal(methodology_routes_result_second.changed, False, "methodology route patch idempotent")
        assert_equal(routes_result_second.changed, False, "routes patch idempotent")

    print("PASS: patch_ghost_theme_en_urls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
