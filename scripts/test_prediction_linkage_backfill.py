#!/usr/bin/env python3
"""Tests for prediction_linkage_backfill, prediction_slug_drift_audit,
cross_language_only_audit, and ledger dedup."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prediction_release_contract import (
    append_ledger_entry,
    read_latest_entry_by_slug,
    verify_ledger_chain,
    _state_signature,
)
from prediction_linkage_backfill import classify_missing_sibling


# ---------------------------------------------------------------------------
# classify_missing_sibling
# ---------------------------------------------------------------------------


def test_classify_en_missing_entirely() -> None:
    result = classify_missing_sibling(
        slug="trump-tariff",
        article_lang="ja",
        prediction_id="NP-2026-0100",
        published={"trump-tariff": {"slug": "trump-tariff", "tag_slugs": "", "title": "", "status": "published"}},
        draft={},
        pid_to_links={},
    )
    assert result["missing_reason"] == "en_missing_entirely"
    assert result["expected_sibling_slug"] == "en-trump-tariff"
    assert result["action"] == "translate_and_register"
    assert result["db_link_state"] == "db_link_missing"


def test_classify_en_exists_draft() -> None:
    result = classify_missing_sibling(
        slug="trump-tariff",
        article_lang="ja",
        prediction_id="NP-2026-0100",
        published={"trump-tariff": {"slug": "trump-tariff", "tag_slugs": "", "title": "", "status": "published"}},
        draft={"en-trump-tariff": {"slug": "en-trump-tariff", "tag_slugs": "", "title": "", "status": "draft"}},
        pid_to_links={},
    )
    assert result["missing_reason"] == "en_exists_draft"
    assert result["action"] == "publish_draft"


def test_classify_en_missing_with_db_link() -> None:
    result = classify_missing_sibling(
        slug="trump-tariff",
        article_lang="ja",
        prediction_id="NP-2026-0100",
        published={"trump-tariff": {"slug": "trump-tariff", "tag_slugs": "", "title": "", "status": "published"}},
        draft={},
        pid_to_links={"NP-2026-0100": [{"lang": "en", "slug": "en-trump-tariff"}]},
    )
    assert result["missing_reason"] == "en_missing_entirely"
    assert result["db_link_state"] == "db_link_registered"
    assert result["action"] == "create_and_publish_translation"


def test_classify_ja_missing_from_en_article() -> None:
    result = classify_missing_sibling(
        slug="en-ai-news",
        article_lang="en",
        prediction_id="NP-2026-0200",
        published={"en-ai-news": {"slug": "en-ai-news", "tag_slugs": "lang-en", "title": "", "status": "published"}},
        draft={},
        pid_to_links={},
    )
    assert result["missing_reason"] == "ja_missing_entirely"
    assert result["expected_sibling_slug"] == "ai-news"
    assert result["target_lang"] == "ja"


def test_classify_en_exists_published_slug_mismatch() -> None:
    result = classify_missing_sibling(
        slug="trump-tariff",
        article_lang="ja",
        prediction_id="NP-2026-0100",
        published={
            "trump-tariff": {"slug": "trump-tariff", "tag_slugs": "", "title": "", "status": "published"},
            "en-trump-tariff": {"slug": "en-trump-tariff", "tag_slugs": "lang-en", "title": "", "status": "published"},
        },
        draft={},
        pid_to_links={},
    )
    assert result["missing_reason"] == "en_exists_published_slug_mismatch"
    assert result["action"] == "investigate_slug_mismatch"


# ---------------------------------------------------------------------------
# _state_signature
# ---------------------------------------------------------------------------


def test_state_signature_deterministic() -> None:
    sig1 = _state_signature("paired_live", "article_backed", "review_required", "en-slug", "NP-001", "v3")
    sig2 = _state_signature("paired_live", "article_backed", "review_required", "en-slug", "NP-001", "v3")
    assert sig1 == sig2


def test_state_signature_differs_on_linkage_change() -> None:
    sig1 = _state_signature("paired_live", "article_backed", "review_required", "en-slug", "NP-001", "v3")
    sig2 = _state_signature("missing_sibling", "article_backed", "review_required", "en-slug", "NP-001", "v3")
    assert sig1 != sig2


def test_state_signature_differs_on_lane_change() -> None:
    sig1 = _state_signature("paired_live", "article_backed", "review_required", "en-slug", "NP-001", "v3")
    sig2 = _state_signature("paired_live", "article_backed", "auto_safe", "en-slug", "NP-001", "v3")
    assert sig1 != sig2


# ---------------------------------------------------------------------------
# read_latest_entry_by_slug
# ---------------------------------------------------------------------------


def test_read_latest_entry_by_slug() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        ledger_path = f.name
    try:
        # Append two entries for different slugs
        append_ledger_entry(
            slug="slug-a", public_url="https://example.com/a/",
            prediction_id="NP-001", article_lang="ja",
            linkage_state="paired_live", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash1", ledger_path=ledger_path,
        )
        append_ledger_entry(
            slug="slug-b", public_url="https://example.com/b/",
            prediction_id="NP-002", article_lang="ja",
            linkage_state="missing_sibling", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash1", ledger_path=ledger_path,
        )
        append_ledger_entry(
            slug="slug-a", public_url="https://example.com/a/",
            prediction_id="NP-001", article_lang="ja",
            linkage_state="missing_sibling", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash1", ledger_path=ledger_path,
        )

        latest_a = read_latest_entry_by_slug("slug-a", ledger_path)
        assert latest_a is not None
        assert latest_a["linkage_state"] == "missing_sibling"  # Latest entry

        latest_b = read_latest_entry_by_slug("slug-b", ledger_path)
        assert latest_b is not None
        assert latest_b["prediction_id"] == "NP-002"

        latest_c = read_latest_entry_by_slug("slug-c", ledger_path)
        assert latest_c is None
    finally:
        os.unlink(ledger_path)


# ---------------------------------------------------------------------------
# Ledger dedup (skip_if_unchanged)
# ---------------------------------------------------------------------------


def test_ledger_skip_if_unchanged_skips_identical() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        ledger_path = f.name
    try:
        entry1 = append_ledger_entry(
            slug="test-slug", public_url="https://example.com/test/",
            prediction_id="NP-001", article_lang="ja",
            linkage_state="missing_sibling", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash1", ledger_path=ledger_path,
        )
        assert entry1 is not None

        # Same state, should skip
        entry2 = append_ledger_entry(
            slug="test-slug", public_url="https://example.com/test/",
            prediction_id="NP-001", article_lang="ja",
            linkage_state="missing_sibling", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash1", ledger_path=ledger_path,
            skip_if_unchanged=True,
        )
        assert entry2 is None

        # Verify only 1 entry in ledger
        result = verify_ledger_chain(ledger_path)
        assert result["ok"]
        assert result["entry_count"] == 1
    finally:
        os.unlink(ledger_path)


def test_ledger_skip_if_unchanged_writes_on_state_change() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        ledger_path = f.name
    try:
        entry1 = append_ledger_entry(
            slug="test-slug", public_url="https://example.com/test/",
            prediction_id="NP-001", article_lang="ja",
            linkage_state="missing_sibling", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash1", ledger_path=ledger_path,
        )
        assert entry1 is not None

        # Different linkage_state, should write
        entry2 = append_ledger_entry(
            slug="test-slug", public_url="https://example.com/test/",
            prediction_id="NP-001", article_lang="ja",
            linkage_state="paired_live", article_backing_state="article_backed",
            sibling_slug="en-test-slug", sibling_lang="en",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash1", ledger_path=ledger_path,
            skip_if_unchanged=True,
        )
        assert entry2 is not None
        assert entry2["linkage_state"] == "paired_live"

        result = verify_ledger_chain(ledger_path)
        assert result["ok"]
        assert result["entry_count"] == 2
    finally:
        os.unlink(ledger_path)


def test_ledger_skip_if_unchanged_different_slug_always_writes() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        ledger_path = f.name
    try:
        append_ledger_entry(
            slug="slug-a", public_url="https://example.com/a/",
            prediction_id="NP-001", article_lang="ja",
            linkage_state="missing_sibling", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash1", ledger_path=ledger_path,
        )

        # Different slug, should always write even with skip_if_unchanged
        entry2 = append_ledger_entry(
            slug="slug-b", public_url="https://example.com/b/",
            prediction_id="NP-002", article_lang="ja",
            linkage_state="missing_sibling", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash1", ledger_path=ledger_path,
            skip_if_unchanged=True,
        )
        assert entry2 is not None

        result = verify_ledger_chain(ledger_path)
        assert result["ok"]
        assert result["entry_count"] == 2
    finally:
        os.unlink(ledger_path)


def test_ledger_without_skip_always_writes() -> None:
    """Without skip_if_unchanged, same state still writes (backward compat)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        ledger_path = f.name
    try:
        append_ledger_entry(
            slug="test-slug", public_url="https://example.com/test/",
            prediction_id="NP-001", article_lang="ja",
            linkage_state="missing_sibling", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash1", ledger_path=ledger_path,
        )
        entry2 = append_ledger_entry(
            slug="test-slug", public_url="https://example.com/test/",
            prediction_id="NP-001", article_lang="ja",
            linkage_state="missing_sibling", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash1", ledger_path=ledger_path,
        )
        assert entry2 is not None

        result = verify_ledger_chain(ledger_path)
        assert result["ok"]
        assert result["entry_count"] == 2
    finally:
        os.unlink(ledger_path)


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
