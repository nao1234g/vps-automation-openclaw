#!/usr/bin/env python3
"""Regression checks for the canonical public lexicon."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from canonical_public_lexicon import LEXICON_VERSION, get_about_copy, get_brand_copy, get_tracker_copy  # noqa: E402


def test_brand_copy() -> None:
    ja = get_brand_copy("ja")
    en = get_brand_copy("en")
    assert LEXICON_VERSION.endswith("v4")
    assert ja["platform_name"] == "検証可能な予測プラットフォーム"
    assert ja["oracle_subtitle"] == "予測オラクル"
    assert en["platform_name"] == "Verifiable Forecast Platform"


def test_tracker_copy() -> None:
    ja = get_tracker_copy("ja")
    en = get_tracker_copy("en")
    assert ja["view_in_play"] == "進行中"
    assert ja["view_awaiting"] == "判定待ち"
    assert ja["view_resolved"] == "判定済み"
    assert en["view_in_play"] == "In Play"
    assert en["view_awaiting"] == "Awaiting Verification"
    assert en["view_resolved"] == "Resolved"


def test_about_copy() -> None:
    ja = get_about_copy("ja")
    en = get_about_copy("en")
    assert "検証可能な予測プラットフォーム" in ja["hero_title"]
    assert "Verifiable Forecast Platform" in en["hero_title"]


def run() -> None:
    test_brand_copy()
    test_tracker_copy()
    test_about_copy()
    print("PASS: public lexicon regression checks")


if __name__ == "__main__":
    run()
