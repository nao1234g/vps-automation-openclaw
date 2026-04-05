#!/usr/bin/env python3
"""Smoke tests for update_leaderboard_pages.py."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import update_leaderboard_pages as ulp  # noqa: E402


def test_build_leaderboard_page_html_replaces_legacy_threshold_copy() -> None:
    html = ulp.build_leaderboard_page_html("en")
    assert "No human forecasters yet. Need 5+ resolved." not in html, html
    assert "AI benchmark only (beta)" in html, html
    assert "Build the Human Baseline" in html, html
    assert "baseline-building mode" in html, html
    assert "/reader-predict/top-forecasters" in html, html
    assert "/en/forecasting-methodology/" in html, html
    assert "/en/forecast-scoring-and-resolution/" in html, html
    assert "/en/forecast-integrity-and-audit/" in html, html


def test_build_leaderboard_page_html_localizes_japanese_beta_copy() -> None:
    html = ulp.build_leaderboard_page_html("ja")
    assert "AI benchmark only (beta)" in html, html
    assert "人間ランキング" in html, html
    assert "人間ベースラインを育てる" in html, html
    assert "ベースライン" in html, html
    assert "解決済予測が5件以上でランキングに表示されます。" not in html, html


def test_leaderboard_page_metadata_avoids_overclaiming_challenge_title() -> None:
    meta = ulp._page_metadata("ja")
    assert meta["title"] == "AI Benchmark Leaderboard | Nowpattern", meta
    assert "AIを倒せるか" not in meta["title"], meta
    assert "ベースライン構築" in meta["meta_description"], meta


def main() -> int:
    test_build_leaderboard_page_html_replaces_legacy_threshold_copy()
    test_build_leaderboard_page_html_localizes_japanese_beta_copy()
    test_leaderboard_page_metadata_avoids_overclaiming_challenge_title()
    print("PASS: leaderboard page update checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
