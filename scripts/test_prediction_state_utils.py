#!/usr/bin/env python3
"""Regression tests for the public prediction state contract."""

from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prediction_state_utils as psu  # noqa: E402


def test_open_prediction_maps_to_in_play_bucket() -> None:
    prediction = {
        "status": "OPEN",
        "trigger_date": "2026-05-01",
        "same_lang_url": "",
        "fallback_url": "",
    }
    snap = psu.public_state_snapshot(prediction, lang="ja", today=date(2026, 4, 4))
    assert snap["forecast_state"] == psu.FORECAST_STATE_OPEN, snap
    assert snap["resolution_state"] == psu.RESOLUTION_STATE_PENDING, snap
    assert snap["content_state"] == psu.CONTENT_STATE_TRACKER_ONLY, snap
    assert snap["render_bucket"] == psu.PUBLIC_RENDER_BUCKET_IN_PLAY, snap


def test_closed_unresolved_prediction_maps_to_awaiting_bucket() -> None:
    prediction = {
        "status": "RESOLVING",
        "trigger_date": "2026-02-15",
        "same_lang_url": "",
        "fallback_url": "https://nowpattern.com/en/example/",
    }
    snap = psu.public_state_snapshot(prediction, lang="ja", today=date(2026, 4, 4))
    assert snap["forecast_state"] == psu.FORECAST_STATE_CLOSED, snap
    assert snap["resolution_state"] == psu.RESOLUTION_STATE_AWAITING, snap
    assert snap["content_state"] == psu.CONTENT_STATE_CROSS_LANG, snap
    assert snap["render_bucket"] == psu.PUBLIC_RENDER_BUCKET_AWAITING, snap


def test_resolved_not_scored_prediction_maps_to_resolved_bucket() -> None:
    prediction = {
        "status": "RESOLVING",
        "resolved_at": "2026-04-03T00:00:00Z",
        "verdict": "NOT_SCORED",
        "official_score_tier": "NOT_SCORABLE",
        "brier_score": 0.10,
        "same_lang_url": "https://nowpattern.com/example/",
    }
    snap = psu.public_state_snapshot(prediction, lang="ja", today=date(2026, 4, 4))
    assert snap["forecast_state"] == psu.FORECAST_STATE_CLOSED, snap
    assert snap["resolution_state"] == psu.RESOLUTION_STATE_NOT_SCORED, snap
    assert snap["content_state"] == psu.CONTENT_STATE_ARTICLE_LIVE, snap
    assert snap["render_bucket"] == psu.PUBLIC_RENDER_BUCKET_RESOLVED, snap


def test_invalid_trigger_date_falls_back_without_crashing() -> None:
    prediction = {
        "status": "RESOLVING",
        "trigger_date": "2026-13",
        "same_lang_url": "",
        "fallback_url": "",
    }
    snap = psu.public_state_snapshot(prediction, lang="ja", today=date(2026, 4, 4))
    assert snap["forecast_state"] == psu.FORECAST_STATE_CLOSED, snap
    assert snap["resolution_state"] == psu.RESOLUTION_STATE_AWAITING, snap
    assert snap["render_bucket"] == psu.PUBLIC_RENDER_BUCKET_AWAITING, snap


def main() -> int:
    test_open_prediction_maps_to_in_play_bucket()
    test_closed_unresolved_prediction_maps_to_awaiting_bucket()
    test_resolved_not_scored_prediction_maps_to_resolved_bucket()
    test_invalid_trigger_date_falls_back_without_crashing()
    print("PASS: prediction state utils")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
