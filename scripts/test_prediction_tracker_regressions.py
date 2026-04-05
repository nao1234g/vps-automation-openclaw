#!/usr/bin/env python3
"""Regression tests for tracker/article-link integrity mistakes."""

from __future__ import annotations

import http.client
import tempfile
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


def test_build_page_html_limits_initial_tracking_dom_and_embeds_tracking_payload() -> None:
    import json
    import re

    rows = []
    for idx in range(40):
        rows.append(
            {
                "source": "prediction_db",
                "prediction_id": f"NP-2026-{2000 + idx}",
                "title": f"Open forecast {idx}",
                "status": "OPEN",
                "url": "",
                "same_lang_url": "",
                "fallback_url": "",
                "analysis_is_fallback": False,
                "genres": [],
                "our_pick": "YES",
                "our_pick_prob": 60,
                "question_type": "binary",
                "hit_condition_ja": f"条件{idx}",
                "trigger_date": "2026-12-31",
                "oracle_deadline": "2026-12-31",
                "resolution_question_ja": f"質問{idx}",
                "scenarios_labeled": [
                    {"label": "基本", "prob": 60, "content": f"根拠{idx}"},
                    {"label": "悲観", "prob": 40, "content": f"反証{idx}"},
                ],
            }
        )

    html = ppb.build_page_html(rows, {}, "ja")
    assert html.count('class="np-reader-vote"') == ppb.TRACKING_INITIAL_RENDER_LIMIT, html

    config_match = re.search(
        rf'<script id="{ppb.TRACKING_PAYLOAD_SCRIPT_ID}" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert config_match, html
    config = json.loads(config_match.group(1))
    assert config["payload_url"] == "/reader-predict/tracking-payload/ja", config
    assert config["seed_limit"] == ppb.TRACKING_INITIAL_RENDER_LIMIT, config
    assert config["tracking_total"] == 40, config

    payload = ppb._build_tracking_payload(rows, [], "ja")
    assert len(payload) == 40, payload
    assert payload[0]["bucket"] == "inplay", payload[0]
    assert payload[0]["html_b64"], payload[0]
    assert "The rest load on demand." not in html, html


def test_write_tracker_payload_report_writes_local_artifact() -> None:
    rows = [
        {
            "source": "prediction_db",
            "prediction_id": "NP-2026-3001",
            "title": "Open forecast",
            "status": "OPEN",
            "render_bucket": "in_play",
            "same_lang_url": "",
            "fallback_url": "",
            "analysis_is_fallback": False,
            "genres": ["macro"],
            "our_pick": "YES",
            "our_pick_prob": 60,
            "question_type": "binary",
            "hit_condition_ja": "条件A",
            "oracle_deadline": "2026-12-31",
            "resolution_question_ja": "質問A",
            "scenarios_labeled": [{"label": "基本", "prob": 60, "content": "根拠A"}],
        },
        {
            "source": "prediction_db",
            "prediction_id": "NP-2026-3002",
            "title": "Awaiting forecast",
            "status": "RESOLVING",
            "render_bucket": "awaiting",
            "same_lang_url": "",
            "fallback_url": "",
            "analysis_is_fallback": False,
            "genres": ["policy"],
            "our_pick": "NO",
            "our_pick_prob": 45,
            "question_type": "binary",
            "hit_condition_ja": "条件B",
            "oracle_deadline": "2026-12-31",
            "resolution_question_ja": "質問B",
            "scenarios_labeled": [{"label": "基本", "prob": 45, "content": "根拠B"}],
        },
        {
            "source": "prediction_db",
            "prediction_id": "NP-2026-3003",
            "title": "Resolved forecast",
            "status": "RESOLVED",
            "render_bucket": "resolved",
            "same_lang_url": "",
            "fallback_url": "",
            "analysis_is_fallback": False,
            "genres": ["all"],
            "our_pick": "YES",
            "our_pick_prob": 75,
            "question_type": "binary",
            "hit_condition_ja": "条件C",
            "oracle_deadline": "2026-12-31",
            "resolution_question_ja": "質問C",
            "scenarios_labeled": [{"label": "基本", "prob": 75, "content": "根拠C"}],
        },
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        original_template = ppb.TRACKER_PAYLOAD_OUTPUT_TEMPLATE
        try:
            ppb.TRACKER_PAYLOAD_OUTPUT_TEMPLATE = str(Path(tmpdir) / "tracker_payload_{lang}.json")
            ppb._write_tracker_payload_report("ja", rows)
            payload_path = Path(tmpdir) / "tracker_payload_ja.json"
            assert payload_path.exists(), payload_path
            payload = __import__("json").loads(payload_path.read_text(encoding="utf-8"))
        finally:
            ppb.TRACKER_PAYLOAD_OUTPUT_TEMPLATE = original_template

    assert payload["lang"] == "ja", payload
    assert len(payload["items"]) == 2, payload
    assert {item["bucket"] for item in payload["items"]} == {"inplay", "awaiting"}, payload
    assert all(item["html_b64"] for item in payload["items"]), payload


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
    assert "window.npReaderWidgetRefresh" in foot, foot
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
    assert "54/1121 (4.8%)" in html, html
    assert "Next milestone: 150 publicly scored cases." in html, html
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


def test_build_rows_treats_verdict_backed_resolution_as_resolved_without_resolved_at() -> None:
    pred_db = {
        "predictions": [
            {
                "prediction_id": "NP-2026-8888",
                "title": "Resolved without timestamp",
                "title_ja": "解決日時なしの解決予測",
                "status": "RESOLVED",
                "verdict": "MISS",
                "brier_score": 0.8281,
                "official_score_tier": "PROVISIONAL",
                "scenarios": [
                    {"label": "基本", "probability": 0.91, "content": "根拠"}
                ],
                "our_pick_prob": 91,
                "question_type": "binary",
                "hit_condition_ja": "条件E",
                "oracle_deadline": "2026-03-01",
            }
        ]
    }
    rows = ppb.build_rows(pred_db, ghost_posts=[], embed_data=[], lang="ja")
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["verdict"] == "MISS", row
    assert row["brier_score"] == 0.8281, row
    assert row["resolution_state"] == "RESOLVED_MISS", row
    assert row["render_bucket"] == "resolved", row


def test_build_rows_uses_canonical_trigger_date_for_state_in_both_languages() -> None:
    pred_db = {
        "predictions": [
            {
                "prediction_id": "NP-2026-8889",
                "title": "Cross-language deadline parsing",
                "title_ja": "多言語期限パース確認",
                "status": "RESOLVING",
                "triggers": [{"date": "2026年Q4", "date_en": "Q4 2026"}],
                "scenarios": [{"label": "基本", "probability": 0.6, "content": "根拠"}],
                "our_pick_prob": 60,
                "question_type": "binary",
                "oracle_deadline": "2026年Q4",
            }
        ]
    }
    row_ja = ppb.build_rows(pred_db, ghost_posts=[], embed_data=[], lang="ja")[0]
    row_en = ppb.build_rows(pred_db, ghost_posts=[], embed_data=[], lang="en")[0]
    assert row_ja["trigger_date"] == "2026年Q4", row_ja
    assert row_en["trigger_date"] == "2026年Q4", row_en
    assert row_ja["render_bucket"] == row_en["render_bucket"], (row_ja, row_en)


def test_build_rows_accepts_list_genre_tags() -> None:
    pred_db = {
        "predictions": [
            {
                "prediction_id": "NP-2026-8890",
                "title": "List genre tags",
                "title_ja": "genre_tags が配列の予測",
                "status": "OPEN",
                "genre_tags": ["Macro", "Policy"],
                "scenarios": [{"label": "基本", "probability": 0.6, "content": "根拠"}],
                "our_pick_prob": 60,
                "question_type": "binary",
                "oracle_deadline": "2026-12-31",
            }
        ]
    }
    row = ppb.build_rows(pred_db, ghost_posts=[], embed_data=[], lang="ja")[0]
    assert row["genres"] == ["macro", "policy"], row


def test_tracker_page_metadata_softens_old_transparency_claims() -> None:
    meta = ppb._tracker_page_metadata(
        {
            "total": 1121,
            "resolved": 58,
            "scorable": 54,
            "not_scorable": 4,
            "accuracy_pct": 66.7,
            "public_brier_index": 32.1,
        },
        "en",
    )
    assert "Full Accuracy Transparency" not in meta["title"], meta
    assert "auto-calculated Brier Scores" not in meta["meta_description"], meta
    assert "Provisional" in meta["meta_description"], meta


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
    assert "English resolution summary pending." not in html, html
    assert "English evidence summary pending." not in html, html
    assert "English scenario summary pending." not in html, html
    assert "This forecast resolved as accurate against its published YES/NO rule." in html, html
    assert "The supporting evidence bundle for this resolution is recorded and fingerprinted below." in html, html
    assert "Base case in the published scenario split (72%)." in html, html
    assert "Bearish case in the published scenario split (28%)." in html, html
    assert "Base" in html, html
    assert "Bearish" in html, html


def test_tracker_ui_gate_rejects_legacy_english_pending_copy() -> None:
    html = "<div>English resolution summary pending.</div>"
    try:
        ppb.check_tracker_public_ui_integrity(html)
    except AssertionError as exc:
        assert "legacy placeholder copy" in str(exc)
        return
    raise AssertionError("tracker UI integrity gate failed to block legacy EN placeholder copy")


def test_ghost_request_treats_incomplete_write_body_as_success() -> None:
    original_urlopen = ppb.urllib.request.urlopen
    original_jwt = ppb.ghost_jwt

    class _DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            raise http.client.IncompleteRead(b'{"ok":true}', 32)

    try:
        ppb.ghost_jwt = lambda api_key: "dummy-token"
        ppb.urllib.request.urlopen = lambda *args, **kwargs: _DummyResponse()
        result = ppb.ghost_request("PUT", "/pages/1/", "kid:deadbeef", {"pages": []})
    finally:
        ppb.urllib.request.urlopen = original_urlopen
        ppb.ghost_jwt = original_jwt

    assert result["_warning"] == "incomplete_read_after_write", result
    assert result["_partial_bytes"] > 0, result


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
    test_build_rows_treats_verdict_backed_resolution_as_resolved_without_resolved_at()
    test_build_rows_uses_canonical_trigger_date_for_state_in_both_languages()
    test_build_rows_accepts_list_genre_tags()
    test_tracker_page_metadata_softens_old_transparency_claims()
    test_build_card_emits_state_attributes()
    test_build_card_suppresses_japanese_resolution_evidence_on_en_page()
    test_tracker_ui_gate_rejects_legacy_english_pending_copy()
    test_ghost_request_treats_incomplete_write_body_as_success()
    test_claimreview_ld_excludes_not_scored_predictions()
    test_resolving_near_deadline_promotes_to_in_play()
    test_resolving_far_past_deadline_stays_awaiting()
    test_resolving_q2_deadline_promotes_to_in_play()
    print("PASS: prediction tracker regression checks")


if __name__ == "__main__":
    run()
