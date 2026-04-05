#!/usr/bin/env python3
"""Unit tests for prediction_maturity_audit.py."""

from __future__ import annotations

import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prediction_maturity_audit as pma  # noqa: E402


def test_parse_tracker_counts_extracts_toolbar_numbers() -> None:
    html = """
    <button class="np-view-btn active" data-view="all">All <span>1121</span></button>
    <button class="np-view-btn" data-view="inplay">In Play <span>976</span></button>
    <button class="np-view-btn" data-view="awaiting">Awaiting Verification <span>87</span></button>
    <button class="np-view-btn" data-view="resolved">Resolved <span>58</span></button>
    """
    counts = pma.parse_tracker_counts(html)
    assert counts == {"all": 1121, "in_play": 976, "awaiting": 87, "resolved": 58}, counts


def test_count_phrase_hits_and_sum_hits() -> None:
    text = "A fallback. A fallback. Another fallback."
    hits = pma.count_phrase_hits(text, ("A fallback.", "Another fallback."))
    assert hits["A fallback."] == 2, hits
    assert hits["Another fallback."] == 1, hits
    assert pma.sum_hits(hits) == 3, hits


def test_progress_helpers_are_capped_and_scaled() -> None:
    assert pma.pct_progress(54, 150) == 36.0
    assert pma.pct_progress(300, 150) == 100.0
    assert pma.ratio_progress(1.5, 0.5) == 33.3
    assert pma.ratio_progress(0.4, 0.5) == 100.0
    assert pma.fallback_progress(0) == 100.0
    assert pma.fallback_progress(25, soft_cap=50) == 50.0


def test_markdown_summary_contains_recommendations() -> None:
    report = {
        "generated_at_epoch": 123,
        "base_url": "https://nowpattern.com",
        "canonical_local": {"total": 1121, "resolved": 58, "scorable": 54},
        "maturity": {
            "m1_scored_sample_and_backlog": {"progress_pct": 34.9},
            "m2_human_baseline": {"progress_pct": 15.2},
            "m3_en_card_completeness": {"progress_pct": 82.0},
        },
        "recommendations": ["Do X", "Do Y"],
    }
    md = pma.markdown_summary(report)
    assert "Prediction Maturity Audit" in md, md
    assert "`1121 total / 58 resolved / 54 publicly scored`" in md, md
    assert "- Do X" in md and "- Do Y" in md, md


def test_fetch_text_retries_transient_urlerror() -> None:
    original_urlopen = pma.urllib.request.urlopen
    original_sleep = pma.time.sleep

    class _FakeResponse:
        status = 200

        def __init__(self, body: str) -> None:
            self._body = body
            self.headers = {"content-type": "text/plain; charset=utf-8"}

        def read(self) -> bytes:
            return self._body.encode("utf-8")

        def geturl(self) -> str:
            return "https://example.com/final"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    calls = {"count": 0}

    def fake_urlopen(request, context=None, timeout=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise urllib.error.URLError("temporary dns failure")
        return _FakeResponse("ok")

    try:
        pma.urllib.request.urlopen = fake_urlopen
        pma.time.sleep = lambda _seconds: None
        result = pma.fetch_text("https://example.com/test", retries=2)
    finally:
        pma.urllib.request.urlopen = original_urlopen
        pma.time.sleep = original_sleep

    assert result.status == 200, result
    assert result.body == "ok", result
    assert calls["count"] == 2, calls


def main() -> int:
    test_parse_tracker_counts_extracts_toolbar_numbers()
    test_count_phrase_hits_and_sum_hits()
    test_progress_helpers_are_capped_and_scaled()
    test_markdown_summary_contains_recommendations()
    test_fetch_text_retries_transient_urlerror()
    print("PASS: prediction maturity audit tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
