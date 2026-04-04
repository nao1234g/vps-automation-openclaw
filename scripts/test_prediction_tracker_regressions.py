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


def test_build_rows_keeps_cross_lang_only_prediction_visible_without_public_url() -> None:
    pred_db = {
        "predictions": [
            {
                "prediction_id": "NP-2026-0044",
                "title": "Cross-language only prediction",
                "title_ja": "英語記事のみの予測",
                "article_slug": "english-only-article",
                "ghost_url": "https://nowpattern.com/en/english-only-article/",
                "status": "OPEN",
                "scenarios": [],
                "our_pick_prob": 61,
                "question_type": "binary",
            }
        ]
    }
    ghost_posts = [
        {
            "slug": "english-only-article",
            "title": "English only article",
            "url": "https://nowpattern.com/en/english-only-article/",
            "html": "<article><div class='np-oracle'></div></article>",
            "tags": [{"slug": "lang-en"}],
        }
    ]
    rows = ppb.build_rows(pred_db, ghost_posts, embed_data=[], lang="ja")
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["prediction_id"] == "NP-2026-0044", row
    assert row["url"] == "", row
    assert row["same_lang_url"] == "", row
    assert row["fallback_url"] == "https://nowpattern.com/en/english-only-article/", row
    assert row["analysis_is_fallback"] is False, row
    ppb.assert_prediction_language_article_integrity(rows, "ja")


def test_build_rows_keeps_prediction_without_live_article() -> None:
    pred_db = {
        "predictions": [
            {
                "prediction_id": "NP-2026-0045",
                "title": "No article yet",
                "title_ja": "まだ記事がない予測",
                "article_slug": "missing-article",
                "ghost_url": "https://nowpattern.com/missing-article/",
                "status": "OPEN",
                "scenarios": [],
                "our_pick_prob": 58,
                "question_type": "binary",
            }
        ]
    }
    rows = ppb.build_rows(pred_db, ghost_posts=[], embed_data=[], lang="ja")
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["prediction_id"] == "NP-2026-0045", row
    assert row["url"] == "", row
    assert row["same_lang_url"] == "", row
    assert row["fallback_url"] == "", row
    ppb.assert_prediction_language_article_integrity(rows, "ja")


def test_build_compact_row_shows_tracker_only_copy_when_article_is_missing() -> None:
    row = {
        "prediction_id": "NP-2026-0046",
        "title": "Tracker-only prediction",
        "status": "RESOLVING",
        "oracle_deadline": "2026-12-31",
        "our_pick": "YES",
        "our_pick_prob": 64,
        "same_lang_url": "",
        "fallback_url": "",
        "analysis_is_fallback": False,
    }
    html = ppb._build_compact_row(row, "ja")
    assert "トラッカー上でのみ表示しています" in html, html
    assert "記事を読む" not in html, html


def test_build_page_html_counts_all_formal_rows_even_without_articles() -> None:
    rows = [
        {
            "source": "prediction_db",
            "prediction_id": "NP-2026-1001",
            "title": "Open forecast",
            "status": "OPEN",
            "url": "",
            "same_lang_url": "",
            "fallback_url": "",
            "analysis_is_fallback": False,
            "genres": [],
            "our_pick": "YES",
            "our_pick_prob": 60,
            "question_type": "binary",
            "hit_condition_ja": "条件A",
            "trigger_date": "2026-12-31",
            "scenarios_labeled": [{"label": "基本", "prob": 60, "content": "根拠A"}],
        },
        {
            "source": "prediction_db",
            "prediction_id": "NP-2026-1002",
            "title": "Resolving forecast",
            "status": "RESOLVING",
            "url": "",
            "same_lang_url": "",
            "fallback_url": "",
            "analysis_is_fallback": False,
            "genres": [],
            "our_pick": "NO",
            "our_pick_prob": 55,
            "question_type": "binary",
            "hit_condition_ja": "条件B",
            "trigger_date": "2026-02-15",
            "oracle_deadline": "2026-02-15",
            "scenarios_labeled": [{"label": "基本", "prob": 55, "content": "根拠B"}],
        },
        {
            "source": "prediction_db",
            "prediction_id": "NP-2026-1003",
            "title": "Resolved forecast",
            "status": "RESOLVED",
            "url": "",
            "same_lang_url": "",
            "fallback_url": "",
            "analysis_is_fallback": False,
            "genres": [],
            "our_pick": "YES",
            "our_pick_prob": 70,
            "question_type": "binary",
            "hit_condition_ja": "条件C",
            "trigger_date": "2026-01-01",
            "scenarios_labeled": [{"label": "基本", "prob": 70, "content": "根拠C"}],
            "brier": 0.1,
            "outcome": "楽観",
            "resolved_at": "2026-01-02",
            "official_score_tier": "PROVISIONAL",
        },
    ]
    html = ppb.build_page_html(rows, {}, "ja")
    assert 'data-view="all">すべて <span>3</span>' in html, html
    assert 'data-view="inplay">進行中 <span>1</span>' in html, html
    assert 'data-view="awaiting">判定待ち <span>1</span>' in html, html
    assert 'data-view="resolved">判定済み <span>1</span>' in html, html


def test_build_card_renders_reader_vote_widget_for_unresolved_prediction() -> None:
    row = {
        "source": "prediction_db",
        "prediction_id": "NP-2026-1004",
        "title": "Vote-enabled forecast",
        "status": "OPEN",
        "url": "",
        "same_lang_url": "",
        "fallback_url": "",
        "analysis_is_fallback": False,
        "genres": [],
        "our_pick": "YES",
        "our_pick_prob": 62,
        "question_type": "binary",
        "hit_condition_ja": "条件D",
        "trigger_date": "2026-12-31",
        "oracle_deadline": "2026-12-31",
        "resolution_question_ja": "条件Dは満たされるか",
        "scenarios_labeled": [
            {"label": "基本", "prob": 62, "content": "根拠D"},
            {"label": "悲観", "prob": 38, "content": "反証D"},
        ],
    }
    html = ppb._build_card(row, "ja")
    assert 'class="np-reader-vote"' in html, html
    assert 'data-pred="NP-2026-1004"' in html, html
    assert 'class="np-vote-btn" data-vote="YES"' in html, html
    assert 'class="np-vote-btn" data-vote="NO"' in html, html
    assert 'id="np-vote-label-NP-2026-1004"' in html, html
    assert 'id="np-vote-stats-NP-2026-1004"' in html, html


def test_build_card_wraps_long_english_deadline_badge() -> None:
    row = {
        "source": "prediction_db",
        "prediction_id": "NP-2026-1004B",
        "title": "English overflow check",
        "status": "OPEN",
        "url": "",
        "same_lang_url": "",
        "fallback_url": "",
        "analysis_is_fallback": False,
        "genres": [],
        "our_pick": "YES",
        "our_pick_prob": 62,
        "question_type": "binary",
        "trigger_date_display": "Ongoing risk — highest probability if cross-border regulatory coordination remains delayed into late 2026",
        "scenarios_labeled": [
            {"label": "Base", "prob": 62, "content": "Reason D"},
            {"label": "Bear", "prob": 38, "content": "Counter D"},
        ],
    }
    html = ppb._build_card(row, "en")
    assert "overflow-wrap:anywhere" in html, html
    assert "max-width:100%" in html, html
    assert "white-space:normal" in html, html


def test_build_reader_vote_widget_foot_localizes_english_copy() -> None:
    foot = ppb._build_reader_vote_widget_foot("en")
    assert ppb.READER_WIDGET_MARKER_START in foot, foot
    assert "Lean YES selected" in foot, foot
    assert "Bullish" in foot, foot
    assert "Bearish" in foot, foot
    assert "楽観" not in foot, foot


def test_merge_reader_vote_widget_foot_replaces_legacy_widget_script() -> None:
    legacy = """
    <script>console.log('keep me');</script>
    <script>
    /* Nowpattern Community Prediction Widget v2.0 */
    (function(){
      window.npVote = function(){};
      localStorage.getItem('np-voter-uuid');
      fetch('/reader-predict/stats-bulk');
    })();
    </script>
    """
    merged = ppb._merge_reader_vote_widget_foot(legacy, "en")
    assert "keep me" in merged, merged
    assert "v2.0" not in merged, merged
    assert merged.count(ppb.READER_WIDGET_MARKER_START) == 1, merged
    assert "Lean YES selected" in merged, merged


def test_canonical_public_stats_ignore_stale_stats_block() -> None:
    pred_db = {
        "stats": {
            "total": 999,
            "resolved": 6,
            "avg_brier_score": 0.1828,
            "last_updated": "2026-03-30T00:02:10.106796",
        },
        "meta": {
            "total_predictions": 3,
            "scored_predictions": 2,
            "official_brier_avg": 0.0520,
            "accuracy_hit": 1,
            "accuracy_miss": 1,
            "accuracy_pct": 50.0,
            "accuracy_updated_at": "2026-04-04T01:23:45Z",
            "status_counts": {"RESOLVED": 3, "OPEN": 0},
        },
        "predictions": [
            {
                "prediction_id": "NP-1",
                "status": "RESOLVED",
                "verdict": "HIT",
                "hit_miss": "correct",
                "brier_score": 0.04,
                "official_score_tier": "PROVISIONAL",
            },
            {
                "prediction_id": "NP-2",
                "status": "RESOLVED",
                "verdict": "MISS",
                "hit_miss": "incorrect",
                "brier_score": 0.064,
                "official_score_tier": "PROVISIONAL",
            },
            {
                "prediction_id": "NP-3",
                "status": "RESOLVED",
                "verdict": "NOT_SCORED",
                "brier_score": 0.10,
                "official_score_tier": "NOT_SCORABLE",
            },
        ],
    }
    stats = ppb._canonical_public_stats(pred_db)
    assert stats["total"] == 3, stats
    assert stats["resolved"] == 3, stats
    assert stats["scorable"] == 2, stats
    assert stats["not_scorable"] == 1, stats
    assert stats["avg_brier_score"] == 0.052, stats
    ld = ppb._build_dataset_ld(stats, "en")
    assert '"size": "3 predictions (3 resolved, 2 publicly scorable)"' in ld, ld


def test_scoreboard_block_separates_binary_and_brier_metrics() -> None:
    stats = {
        "total": 1121,
        "resolved": 58,
        "accuracy_binary_hit": 36,
        "accuracy_binary_miss": 18,
        "accuracy_binary_n": 54,
        "accuracy_pct": 66.7,
        "public_brier_n": 54,
        "public_brier_avg": 0.4608,
        "public_score_tier": "PROVISIONAL",
        "not_scorable": 4,
    }
    html = ppb._scoreboard_block([], "en", stats)
    assert "Binary Judged Accuracy" in html, html
    assert "Public Brier Index" in html, html
    assert "HIT/MISS sample n=54" in html, html
    assert "Brier Index / n=54 / avg raw Brier 0.4608" in html, html
    assert "66.7%" in html, html
    assert "32.1%" in html, html
    assert "/en/forecasting-methodology/" in html, html
    assert "/en/forecast-scoring-and-resolution/" in html, html
    assert "/en/forecast-integrity-and-audit/" in html, html


def test_build_rows_attaches_state_snapshot_fields() -> None:
    pred_db = {
        "predictions": [
            {
                "prediction_id": "NP-2026-7777",
                "title": "State snapshot forecast",
                "title_ja": "状態スナップショット予測",
                "article_slug": "state-snapshot-forecast",
                "ghost_url": "https://nowpattern.com/en/state-snapshot-forecast/",
                "status": "RESOLVING",
                "scenarios": [],
                "our_pick_prob": 61,
                "question_type": "binary",
                "oracle_deadline": "2026-02-15",
            }
        ]
    }
    ghost_posts = [
        {
            "slug": "state-snapshot-forecast",
            "title": "State snapshot forecast",
            "url": "https://nowpattern.com/en/state-snapshot-forecast/",
            "html": "<article><div class='np-oracle'></div></article>",
            "tags": [{"slug": "lang-en"}],
        }
    ]
    rows = ppb.build_rows(pred_db, ghost_posts, embed_data=[], lang="ja")
    row = rows[0]
    assert row["forecast_state"] == "CLOSED_FOR_FORECASTING", row
    assert row["resolution_state"] == "AWAITING_EVIDENCE", row
    assert row["content_state"] == "CROSS_LANG_FALLBACK", row
    assert row["render_bucket"] == "awaiting", row


def test_build_card_emits_state_attributes() -> None:
    row = {
        "source": "prediction_db",
        "prediction_id": "NP-2026-1004C",
        "title": "State attrs forecast",
        "status": "OPEN",
        "url": "",
        "same_lang_url": "",
        "fallback_url": "",
        "analysis_is_fallback": False,
        "genres": [],
        "forecast_state": "OPEN_FOR_FORECASTING",
        "resolution_state": "PENDING_EVENT",
        "content_state": "TRACKER_ONLY",
        "render_bucket": "in_play",
        "our_pick": "YES",
        "our_pick_prob": 62,
        "question_type": "binary",
        "hit_condition_ja": "条件D",
        "trigger_date": "2026-12-31",
        "oracle_deadline": "2026-12-31",
        "resolution_question_ja": "条件Dは満たされるか",
        "scenarios_labeled": [
            {"label": "基本", "prob": 62, "content": "根拠D"},
            {"label": "悲観", "prob": 38, "content": "反証D"},
        ],
    }
    html = ppb._build_card(row, "ja")
    assert 'data-forecast-state="OPEN_FOR_FORECASTING"' in html, html
    assert 'data-resolution-state="PENDING_EVENT"' in html, html
    assert 'data-content-state="TRACKER_ONLY"' in html, html


def test_build_card_suppresses_japanese_resolution_evidence_on_en_page() -> None:
    row = {
        "source": "prediction_db",
        "prediction_id": "NP-2026-1005",
        "title": "Resolved English card",
        "status": "RESOLVED",
        "url": "",
        "same_lang_url": "",
        "fallback_url": "",
        "analysis_is_fallback": False,
        "genres": [],
        "our_pick": "YES",
        "our_pick_prob": 72,
        "question_type": "binary",
        "trigger_date": "2026-12-31",
        "resolution_question_en": "Will example happen?",
        "hit_condition_en": "Example happens.",
        "oracle_question": "Will example happen by 2026-12-31?",
        "scenarios_labeled": [
            {"label": "基本", "prob": 72, "content": "日本語の説明です。"},
            {"label": "悲観", "prob": 28, "content": "別の日本語説明です。"},
        ],
        "outcome": "base",
        "base_content": "日本語の解決サマリー",
        "brier": 0.09,
        "official_score_tier": "PROVISIONAL",
        "resolution_evidence": {"key_evidence_text": "日本語の判定根拠"},
        "integrity_hash": "abc1234567890",
    }
    html = ppb._build_card(row, "en")
    assert "TRANSLATION MISSING" not in html, html
    assert "English resolution summary pending." in html, html
    assert "English evidence summary pending." in html, html
    assert "Base" in html, html
    assert "Bearish" in html, html


def test_claimreview_ld_excludes_not_scored_predictions() -> None:
    predictions = [
        {
            "prediction_id": "NP-2026-2001",
            "status": "RESOLVED",
            "resolved_at": "2026-04-04T00:00:00Z",
            "verdict": "HIT",
            "hit_miss": "correct",
            "brier_score": 0.04,
            "official_score_tier": "PROVISIONAL",
            "our_pick_prob": 70,
            "resolution_question": "Will example A happen?",
        },
        {
            "prediction_id": "NP-2026-2002",
            "status": "RESOLVED",
            "resolved_at": "2026-04-03T00:00:00Z",
            "verdict": "NOT_SCORED",
            "brier_score": 0.10,
            "official_score_tier": "NOT_SCORABLE",
            "our_pick_prob": 65,
            "resolution_question": "Will example B happen?",
        },
    ]
    ld = ppb._build_claimreview_ld(predictions, "en")
    assert "NP-2026-2001".lower() in ld, ld
    assert "NP-2026-2002".lower() not in ld, ld


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
    test_build_rows_keeps_cross_lang_only_prediction_visible_without_public_url()
    test_build_rows_keeps_prediction_without_live_article()
    test_build_compact_row_shows_tracker_only_copy_when_article_is_missing()
    test_build_page_html_counts_all_formal_rows_even_without_articles()
    test_build_card_renders_reader_vote_widget_for_unresolved_prediction()
    test_canonical_public_stats_ignore_stale_stats_block()
    test_scoreboard_block_separates_binary_and_brier_metrics()
    test_build_rows_attaches_state_snapshot_fields()
    test_build_card_emits_state_attributes()
    test_build_card_suppresses_japanese_resolution_evidence_on_en_page()
    test_claimreview_ld_excludes_not_scored_predictions()
    test_resolving_near_deadline_promotes_to_in_play()
    test_resolving_far_past_deadline_stays_awaiting()
    test_resolving_q2_deadline_promotes_to_in_play()
    print("PASS: prediction tracker regression checks")


if __name__ == "__main__":
    run()
