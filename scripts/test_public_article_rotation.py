#!/usr/bin/env python3
"""Regression tests for shared public article rotation helpers."""

from __future__ import annotations

from public_article_rotation import normalize_article_path, pick_batch


def test_normalize_article_path_filters_non_article_routes() -> None:
    base = "https://nowpattern.com/"
    assert normalize_article_path(base, "/assets/app.css") is None
    assert normalize_article_path(base, "/predictions/") is None
    assert normalize_article_path(base, "/page/4/") is None
    assert normalize_article_path(base, "/en/") is None
    assert normalize_article_path(base, "/en/about/") is None
    assert normalize_article_path(base, "/taxonomy-guide/") is None
    assert normalize_article_path(base, "/en/taxonomy-guide/") is None
    assert normalize_article_path(base, "/taxonomy-ja/") is None
    assert normalize_article_path(base, "/taxonomy-en/") is None
    assert normalize_article_path(base, "/en/taxonomy/") is None
    assert normalize_article_path(base, "/genre-geopolitics-10/us-sinks-iranian-warship-the-escalation-spiral-nobody-can-exit/") is None
    assert normalize_article_path(base, "/an-article/") == "/an-article/"
    assert normalize_article_path(base, "/en/an-article/") == "/en/an-article/"


def test_pick_batch_rotates_through_known_paths() -> None:
    paths = ["/a/", "/b/", "/c/", "/d/"]
    batch, next_cursor = pick_batch(paths, 3, 3)
    assert batch == ["/d/", "/a/", "/b/"], batch
    assert next_cursor == 2, next_cursor


def run() -> None:
    test_normalize_article_path_filters_non_article_routes()
    test_pick_batch_rotates_through_known_paths()
    print("PASS: public article rotation regression checks")


if __name__ == "__main__":
    run()
