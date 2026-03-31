#!/usr/bin/env python3
"""Regression tests for tracker/article-link integrity mistakes."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import prediction_page_builder as ppb  # noqa: E402


def test_anchor_href_lowercases_prediction_id() -> None:
    href = ppb._prediction_anchor_href("NP-2026-0042", "ja")
    assert href == "/predictions/#np-2026-0042", href


def test_tracker_ui_gate_blocks_tracker_back_links() -> None:
    html = """
    <div class="np-card">
      <a href="/predictions/#np-2026-0042">View in tracker</a>
    </div>
    """
    try:
        ppb.check_tracker_public_ui_integrity(html)
    except AssertionError as exc:
        assert "tracker" in str(exc).lower()
        return
    raise AssertionError("tracker UI integrity gate failed to block tracker-back link")


def test_build_rows_keeps_prediction_without_scenarios_if_same_lang_article_exists() -> None:
    pred_db = {
        "predictions": [
            {
                "prediction_id": "NP-2026-0042",
                "title": "Test prediction",
                "title_ja": "テスト予測",
                "article_slug": "test-article",
                "ghost_url": "https://nowpattern.com/test-article/",
                "status": "OPEN",
                "scenarios": [],
                "our_pick_prob": 55,
                "question_type": "binary",
            }
        ]
    }
    ghost_posts = [
        {
            "slug": "test-article",
            "title": "テスト記事",
            "url": "https://nowpattern.com/test-article/",
            "html": "<article><div class='np-oracle'></div></article>",
        }
    ]
    rows = ppb.build_rows(pred_db, ghost_posts, embed_data=[], lang="ja")
    assert len(rows) == 1, rows
    assert rows[0]["prediction_id"] == "NP-2026-0042", rows[0]
    assert rows[0]["url"] == "https://nowpattern.com/test-article/", rows[0]


def run() -> None:
    test_anchor_href_lowercases_prediction_id()
    test_tracker_ui_gate_blocks_tracker_back_links()
    test_build_rows_keeps_prediction_without_scenarios_if_same_lang_article_exists()
    print("PASS: prediction tracker regression checks")


if __name__ == "__main__":
    run()
