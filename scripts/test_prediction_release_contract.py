#!/usr/bin/env python3
"""Regression tests for prediction release contract and JA/EN linkage."""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prediction_release_contract import (
    clean_slug,
    detect_article_lang,
    build_sibling_maps,
    evaluate_prediction_linkage,
    append_ledger_entry,
    read_last_ledger_entry,
    verify_ledger_chain,
    build_slug_to_prediction_index,
    build_prediction_article_links_index,
    LINKAGE_STATES,
    BACKING_STATES,
)
from article_release_guard import classify_release_lane


# ---------------------------------------------------------------------------
# clean_slug
# ---------------------------------------------------------------------------


def test_clean_slug_strips_en_prefix() -> None:
    assert clean_slug("en-trump-tariff") == "trump-tariff"


def test_clean_slug_noop_for_ja() -> None:
    assert clean_slug("trump-tariff") == "trump-tariff"


def test_clean_slug_short_en() -> None:
    assert clean_slug("en-") == ""


# ---------------------------------------------------------------------------
# detect_article_lang
# ---------------------------------------------------------------------------


def test_detect_lang_from_tag() -> None:
    assert detect_article_lang("some-slug", {"lang-en", "news"}) == "en"


def test_detect_lang_from_slug_prefix() -> None:
    assert detect_article_lang("en-some-slug", set()) == "en"


def test_detect_lang_default_ja() -> None:
    assert detect_article_lang("some-slug", {"news"}) == "ja"


# ---------------------------------------------------------------------------
# build_sibling_maps
# ---------------------------------------------------------------------------


def test_build_sibling_maps_basic() -> None:
    posts = [
        {"slug": "trump-tariff", "tag_slugs": {"news"}, "status": "published"},
        {"slug": "en-trump-tariff", "tag_slugs": {"lang-en", "news"}, "status": "published"},
        {"slug": "draft-article", "tag_slugs": set(), "status": "draft"},
    ]
    ja, en = build_sibling_maps(posts)
    assert "trump-tariff" in ja
    assert "trump-tariff" in en
    assert ja["trump-tariff"] == "trump-tariff"
    assert en["trump-tariff"] == "en-trump-tariff"
    # Draft should not appear
    assert "draft-article" not in ja


def test_build_sibling_maps_string_tags() -> None:
    """Tag slugs passed as space-separated string (as from Ghost SQL query)."""
    posts = [
        {"slug": "en-ai-news", "tag_slugs": "lang-en news", "status": "published"},
    ]
    ja, en = build_sibling_maps(posts)
    assert "ai-news" in en


# ---------------------------------------------------------------------------
# evaluate_prediction_linkage
# ---------------------------------------------------------------------------


def test_linkage_paired_live() -> None:
    ja_by_clean = {"trump-tariff": "trump-tariff"}
    en_by_clean = {"trump-tariff": "en-trump-tariff"}
    result = evaluate_prediction_linkage(
        slug="trump-tariff",
        tag_slugs=set(),
        prediction_id="NP-2026-0100",
        ja_by_clean=ja_by_clean,
        en_by_clean=en_by_clean,
    )
    assert result["linkage_state"] == "paired_live"
    assert result["article_backing_state"] == "article_backed"
    assert result["same_prediction_sibling_lang"] == "en"
    assert result["same_prediction_sibling_slug"] == "en-trump-tariff"
    assert not result["errors"]


def test_linkage_missing_sibling_ja_only() -> None:
    ja_by_clean = {"trump-tariff": "trump-tariff"}
    en_by_clean = {}
    result = evaluate_prediction_linkage(
        slug="trump-tariff",
        tag_slugs=set(),
        prediction_id="NP-2026-0100",
        ja_by_clean=ja_by_clean,
        en_by_clean=en_by_clean,
    )
    assert result["linkage_state"] == "missing_sibling"
    assert result["article_lang"] == "ja"
    assert any("PREDICTION_SIBLING_MISSING:en" in e for e in result["errors"])


def test_linkage_missing_sibling_en_only() -> None:
    ja_by_clean = {}
    en_by_clean = {"trump-tariff": "en-trump-tariff"}
    result = evaluate_prediction_linkage(
        slug="en-trump-tariff",
        tag_slugs={"lang-en"},
        prediction_id="NP-2026-0100",
        ja_by_clean=ja_by_clean,
        en_by_clean=en_by_clean,
    )
    assert result["linkage_state"] == "missing_sibling"
    assert result["article_lang"] == "en"
    assert any("PREDICTION_SIBLING_MISSING:ja" in e for e in result["errors"])


def test_linkage_cross_language_only() -> None:
    """Prediction DB knows about sibling but it's not published in Ghost."""
    ja_by_clean = {"trump-tariff": "trump-tariff"}
    en_by_clean = {}
    links = [{"lang": "en", "slug": "en-trump-tariff", "url": "https://nowpattern.com/en/trump-tariff/"}]
    result = evaluate_prediction_linkage(
        slug="trump-tariff",
        tag_slugs=set(),
        prediction_id="NP-2026-0100",
        ja_by_clean=ja_by_clean,
        en_by_clean=en_by_clean,
        prediction_article_links=links,
    )
    assert result["linkage_state"] == "cross_language_only"


def test_linkage_tracker_only() -> None:
    """Article slug not found in any published post map."""
    result = evaluate_prediction_linkage(
        slug="nonexistent-slug",
        tag_slugs=set(),
        prediction_id="NP-2026-0100",
        ja_by_clean={},
        en_by_clean={},
    )
    assert result["linkage_state"] == "tracker_only"
    assert result["article_backing_state"] == "tracker_only"


def test_linkage_states_exhaustive() -> None:
    """All defined linkage states are valid."""
    assert LINKAGE_STATES == {"paired_live", "missing_sibling", "cross_language_only", "tracker_only"}
    assert BACKING_STATES == {"article_backed", "tracker_only"}


# ---------------------------------------------------------------------------
# slug → prediction_id index
# ---------------------------------------------------------------------------

MOCK_PREDICTION_DB = {
    "predictions": [
        {
            "prediction_id": "NP-2026-0100",
            "article_slug": "trump-tariff",
            "article_links": [
                {"slug": "trump-tariff", "lang": "ja", "url": "https://nowpattern.com/trump-tariff/"},
                {"slug": "en-trump-tariff", "lang": "en", "url": "https://nowpattern.com/en/trump-tariff/"},
            ],
        },
        {
            "prediction_id": "NP-2026-0200",
            "article_slug": "ai-regulation",
            "article_links": [
                {"slug": "ai-regulation", "lang": "ja"},
            ],
        },
        {
            "prediction_id": "NP-2026-0300",
            "article_slug": "",
            "article_links": [],
        },
    ]
}


def test_slug_to_prediction_index_primary() -> None:
    idx = build_slug_to_prediction_index(MOCK_PREDICTION_DB)
    assert idx["trump-tariff"] == "NP-2026-0100"
    assert idx["en-trump-tariff"] == "NP-2026-0100"
    assert idx["ai-regulation"] == "NP-2026-0200"


def test_slug_to_prediction_index_missing() -> None:
    idx = build_slug_to_prediction_index(MOCK_PREDICTION_DB)
    assert "nonexistent" not in idx


def test_slug_to_prediction_index_empty_slug_skipped() -> None:
    idx = build_slug_to_prediction_index(MOCK_PREDICTION_DB)
    assert "" not in idx


def test_prediction_article_links_index() -> None:
    idx = build_prediction_article_links_index(MOCK_PREDICTION_DB)
    assert "NP-2026-0100" in idx
    assert len(idx["NP-2026-0100"]) == 2
    assert idx["NP-2026-0100"][0]["lang"] == "ja"
    assert "NP-2026-0200" in idx
    assert "NP-2026-0300" not in idx  # empty article_links


def test_slug_to_prediction_first_writer_wins() -> None:
    """If two predictions claim the same slug, first one wins."""
    db = {
        "predictions": [
            {"prediction_id": "NP-A", "article_slug": "shared-slug", "article_links": []},
            {"prediction_id": "NP-B", "article_slug": "shared-slug", "article_links": []},
        ]
    }
    idx = build_slug_to_prediction_index(db)
    assert idx["shared-slug"] == "NP-A"


# ---------------------------------------------------------------------------
# classify_release_lane integration
# ---------------------------------------------------------------------------


def test_classify_lane_oracle_missing_sibling_blocks() -> None:
    """Oracle article with missing sibling should NOT be distribution_ready."""
    lane = classify_release_lane(
        truth_errors=[],
        risk_flags=[],
        approval_present=False,
        external_url_count=3,
        verified_external_source_count=3,
        oracle_marker_present=True,
        prediction_linkage_state="missing_sibling",
    )
    assert lane == "review_required"


def test_classify_lane_oracle_paired_live_normal() -> None:
    """Oracle article with paired sibling follows normal classification."""
    lane = classify_release_lane(
        truth_errors=[],
        risk_flags=[],
        approval_present=False,
        external_url_count=3,
        verified_external_source_count=3,
        oracle_marker_present=True,
        prediction_linkage_state="paired_live",
    )
    # Normal oracle path: review_required (oracle marker present, no approval)
    assert lane == "review_required"


def test_classify_lane_oracle_approved_overrides_linkage() -> None:
    """Human approval overrides linkage state."""
    lane = classify_release_lane(
        truth_errors=[],
        risk_flags=[],
        approval_present=True,
        external_url_count=3,
        verified_external_source_count=3,
        oracle_marker_present=True,
        prediction_linkage_state="missing_sibling",
    )
    assert lane == "distribution_ready"


def test_classify_lane_non_oracle_ignores_linkage() -> None:
    """Non-oracle articles are unaffected by linkage state."""
    lane = classify_release_lane(
        truth_errors=[],
        risk_flags=[],
        approval_present=False,
        external_url_count=3,
        verified_external_source_count=3,
        oracle_marker_present=False,
        prediction_linkage_state="missing_sibling",
    )
    # No oracle marker + no risk flags → auto_safe (empty risk_flags is subset of AUTO_SAFE)
    assert lane == "auto_safe"


def test_classify_lane_backward_compatible_no_linkage() -> None:
    """Without linkage param, behaves identically to pre-contract code."""
    lane = classify_release_lane(
        truth_errors=[],
        risk_flags=[],
        approval_present=False,
        external_url_count=3,
        verified_external_source_count=3,
        oracle_marker_present=True,
    )
    assert lane == "review_required"


# ---------------------------------------------------------------------------
# Append-only ledger
# ---------------------------------------------------------------------------


def test_ledger_append_and_read() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        ledger_path = f.name
    try:
        # First entry
        entry1 = append_ledger_entry(
            slug="trump-tariff",
            public_url="https://nowpattern.com/trump-tariff/",
            prediction_id="NP-2026-0100",
            article_lang="ja",
            linkage_state="paired_live",
            article_backing_state="article_backed",
            sibling_lang="en",
            sibling_slug="en-trump-tariff",
            release_lane="review_required",
            governor_policy_version="2026-04-05-governor-v3",
            mission_contract_hash="abc123",
            ledger_path=ledger_path,
        )
        assert entry1["previous_entry_hash"] == ""
        assert entry1["entry_hash"]

        # Second entry chains to first
        entry2 = append_ledger_entry(
            slug="en-trump-tariff",
            public_url="https://nowpattern.com/en/trump-tariff/",
            prediction_id="NP-2026-0100",
            article_lang="en",
            linkage_state="paired_live",
            article_backing_state="article_backed",
            sibling_lang="ja",
            sibling_slug="trump-tariff",
            release_lane="review_required",
            governor_policy_version="2026-04-05-governor-v3",
            mission_contract_hash="abc123",
            ledger_path=ledger_path,
        )
        assert entry2["previous_entry_hash"] == entry1["entry_hash"]

        # Read last
        last = read_last_ledger_entry(ledger_path)
        assert last is not None
        assert last["slug"] == "en-trump-tariff"

        # Verify chain
        result = verify_ledger_chain(ledger_path)
        assert result["ok"]
        assert result["entry_count"] == 2
    finally:
        os.unlink(ledger_path)


def test_ledger_chain_tamper_detected() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        ledger_path = f.name
    try:
        append_ledger_entry(
            slug="test",
            public_url="https://example.com/test/",
            prediction_id="NP-2026-0001",
            article_lang="ja",
            linkage_state="paired_live",
            article_backing_state="article_backed",
            release_lane="auto_safe",
            governor_policy_version="v1",
            mission_contract_hash="hash1",
            ledger_path=ledger_path,
        )
        # Tamper with the file
        with open(ledger_path, "r", encoding="utf-8") as f:
            line = f.read()
        tampered = line.replace('"paired_live"', '"TAMPERED"')
        with open(ledger_path, "w", encoding="utf-8") as f:
            f.write(tampered)

        result = verify_ledger_chain(ledger_path)
        assert not result["ok"]
        assert result["errors"]
    finally:
        os.unlink(ledger_path)


def test_ledger_empty_file_ok() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        ledger_path = f.name
    try:
        result = verify_ledger_chain(ledger_path)
        assert result["ok"]
        assert result["entry_count"] == 0
    finally:
        os.unlink(ledger_path)


def test_ledger_nonexistent_ok() -> None:
    result = verify_ledger_chain("/tmp/nonexistent_ledger.jsonl")
    assert result["ok"]
    assert result["entry_count"] == 0


if __name__ == "__main__":
    failed = 0
    passed = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  PASS  {name}")
                passed += 1
            except Exception as exc:
                print(f"  FAIL  {name}: {exc}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
