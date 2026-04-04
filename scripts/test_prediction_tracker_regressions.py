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


def test_build_rows_canonicalizes_lang_en_root_urls_for_en_tracker() -> None:
    pred_db = {
        "predictions": [
            {
                "prediction_id": "NP-2026-0043",
                "title": "English prediction",
                "article_slug": "english-root-article",
                "ghost_url": "https://nowpattern.com/english-root-article/",
                "status": "OPEN",
                "scenarios": [],
                "our_pick_prob": 60,
                "question_type": "binary",
            }
        ]
    }
    ghost_posts = [
        {
            "slug": "english-root-article",
            "title": "English root article",
            "url": "https://nowpattern.com/english-root-article/",
            "html": "<article><div class='np-oracle'></div></article>",
            "tags": [{"slug": "lang-en"}],
        }
    ]
    rows = ppb.build_rows(pred_db, ghost_posts, embed_data=[], lang="en")
    assert len(rows) == 1, rows
    assert rows[0]["url"] == "https://nowpattern.com/en/english-root-article/", rows[0]
    assert rows[0]["same_lang_url"] == "https://nowpattern.com/en/english-root-article/", rows[0]


def test_resolving_near_deadline_promotes_to_in_play() -> None:
    row = {
        "status": "RESOLVING",
        "trigger_date": "2026-05-06",
    }
    assert ppb._is_tracker_in_play(row, ppb.date(2026, 4, 4)) is True


def test_resolving_far_past_deadline_stays_awaiting() -> None:
    row = {
        "status": "RESOLVING",
        "trigger_date": "2026-02-15",
    }
    assert ppb._is_tracker_in_play(row, ppb.date(2026, 4, 4)) is False


def test_resolving_q2_deadline_promotes_to_in_play() -> None:
    row = {
        "status": "RESOLVING",
        "trigger_date": "Q2 2026",
    }
    assert ppb._is_tracker_in_play(row, ppb.date(2026, 4, 4)) is True


def run() -> None:
    test_anchor_href_lowercases_prediction_id()
    test_tracker_ui_gate_blocks_tracker_back_links()
    test_build_rows_keeps_prediction_without_scenarios_if_same_lang_article_exists()
    test_build_rows_canonicalizes_lang_en_root_urls_for_en_tracker()
    test_resolving_near_deadline_promotes_to_in_play()
    test_resolving_far_past_deadline_stays_awaiting()
    test_resolving_q2_deadline_promotes_to_in_play()
    print("PASS: prediction tracker regression checks")


if __name__ == "__main__":
    run()
