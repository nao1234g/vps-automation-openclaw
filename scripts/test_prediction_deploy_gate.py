#!/usr/bin/env python3
"""Regression tests for canonical release snapshot gating."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import prediction_deploy_gate as gate  # noqa: E402


def test_parse_report_timestamp_accepts_iso_and_jst() -> None:
    assert gate._parse_report_timestamp("2026-03-31T01:23:45Z") is not None
    assert gate._parse_report_timestamp("2026-03-31 10:23 JST") is not None


def test_build_snapshot_uses_release_scope_counts() -> None:
    manifest = {
        "generated_at": "2026-03-31T01:23:45Z",
        "counts": {
            "published_total": 10,
            "distribution_allowed": 2,
            "high_risk_unapproved": 8,
        },
    }
    tracker = {
        "generated_at": "2026-03-31 10:23 JST",
        "ghost_published_posts_total": 14,
        "ghost_published_posts_release_scope": 10,
        "formal_prediction_total": 20,
        "orphan_oracle_articles": {"count": 3},
        "langs": {
            "ja": {"public_rows": 5, "hidden_no_live_article": 15},
            "en": {"public_rows": 6, "hidden_no_live_article": 14},
        },
    }
    snapshot = gate._build_snapshot(manifest, tracker, [], [])
    assert snapshot["tracker_summary"]["ghost_published_posts_release_scope"] == 10
    assert snapshot["operational_metrics"]["distribution_allowed_ratio_pct"] == 20.0


def test_mojibake_detection_trips_on_multiple_tokens() -> None:
    token = gate.MOJIBAKE_TOKENS[0]
    payload = {"title": token * 3}
    assert gate._count_suspicious_mojibake(payload) == 1


def run() -> None:
    test_parse_report_timestamp_accepts_iso_and_jst()
    test_build_snapshot_uses_release_scope_counts()
    test_mojibake_detection_trips_on_multiple_tokens()
    print("PASS: prediction deploy gate regression checks")


if __name__ == "__main__":
    run()
