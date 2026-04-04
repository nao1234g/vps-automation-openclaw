#!/usr/bin/env python3
"""Smoke tests for update_prediction_methodology_pages.py."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import update_prediction_methodology_pages as upmp  # noqa: E402


SNAPSHOT = {
    "total": 1121,
    "resolved": 58,
    "scorable": 54,
    "not_scorable": 4,
    "binary_hit": 36,
    "binary_miss": 18,
    "binary_n": 54,
    "accuracy_pct": 66.7,
    "avg_brier": 0.4608,
    "public_index": 32.1,
    "score_tier": "PROVISIONAL",
    "last_updated": "2026-04-04T10:00:00Z",
}


def test_scoring_page_has_provisional_disclosure() -> None:
    html = upmp.build_scoring_html("en", SNAPSHOT)
    assert "All current prediction scores are provisional pending blockchain timestamp confirmation." in html, html
    assert "/en/forecast-integrity-and-audit/" in html, html


def test_integrity_page_mentions_state_model_and_backfill() -> None:
    html = upmp.build_integrity_html("ja", SNAPSHOT)
    assert "2026年3月29日の後付けバックフィル" in html, html
    assert upmp.PUBLIC_STATE_MODEL_VERSION in html, html


def test_methodology_page_uses_publicly_scored_count_not_only_total() -> None:
    html = upmp.build_methodology_html("en", SNAPSHOT)
    assert "1121" in html, html
    assert "54" in html, html
    assert "The honest KPI here is not total predictions." in html, html


def test_hreflang_head_is_bilateral() -> None:
    head = upmp._hreflang_head("/en/forecasting-methodology/", "en")
    assert 'hreflang="ja" href="https://nowpattern.com/forecasting-methodology/"' in head, head
    assert 'hreflang="en" href="https://nowpattern.com/en/forecasting-methodology/"' in head, head
    assert 'rel="canonical" href="https://nowpattern.com/en/forecasting-methodology/"' in head, head


def main() -> int:
    test_scoring_page_has_provisional_disclosure()
    test_integrity_page_mentions_state_model_and_backfill()
    test_methodology_page_uses_publicly_scored_count_not_only_total()
    test_hreflang_head_is_bilateral()
    print("PASS: prediction methodology page checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
