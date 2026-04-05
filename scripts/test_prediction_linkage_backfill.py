#!/usr/bin/env python3
"""Tests for prediction_linkage_backfill, prediction_slug_drift_audit,
cross_language_only_audit, and ledger dedup."""

from __future__ import annotations

import json
import os
import sqlite3
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
from ghost_post_loader import (
    load_ghost_posts,
    split_by_status,
    _tag_set,
)


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


# ---------------------------------------------------------------------------
# Helper: create a minimal Ghost-compatible SQLite DB for testing
# ---------------------------------------------------------------------------


def _create_ghost_test_db(posts_data: list[dict]) -> str:
    """Create a temp SQLite file mimicking Ghost's schema.

    Each entry in posts_data should have:
        id, slug, status, title, html, updated_at, tags (list of tag slug strings)
    Returns the path to the temp DB file.
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE posts (
            id TEXT PRIMARY KEY,
            slug TEXT,
            status TEXT,
            title TEXT,
            html TEXT,
            type TEXT DEFAULT 'post',
            published_at TEXT,
            updated_at TEXT
        )
    """)
    con.execute("""
        CREATE TABLE tags (
            id TEXT PRIMARY KEY,
            slug TEXT
        )
    """)
    con.execute("""
        CREATE TABLE posts_tags (
            id TEXT PRIMARY KEY,
            post_id TEXT,
            tag_id TEXT
        )
    """)

    tag_counter = 0
    for i, post in enumerate(posts_data):
        post_id = post.get("id", f"post-{i}")
        con.execute(
            "INSERT INTO posts (id, slug, status, title, html, type, published_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'post', ?, ?)",
            (
                post_id,
                post["slug"],
                post.get("status", "published"),
                post.get("title", ""),
                post.get("html", ""),
                post.get("published_at", "2026-01-01T00:00:00Z"),
                post.get("updated_at", "2026-01-01T00:00:00Z"),
            ),
        )
        for tag_slug in post.get("tags", []):
            tag_id = f"tag-{tag_counter}"
            tag_counter += 1
            # Insert tag if not exists
            existing = con.execute("SELECT id FROM tags WHERE slug = ?", (tag_slug,)).fetchone()
            if existing:
                actual_tag_id = existing[0]
            else:
                con.execute("INSERT INTO tags (id, slug) VALUES (?, ?)", (tag_id, tag_slug))
                actual_tag_id = tag_id
            pt_id = f"pt-{post_id}-{actual_tag_id}"
            con.execute(
                "INSERT INTO posts_tags (id, post_id, tag_id) VALUES (?, ?, ?)",
                (pt_id, post_id, actual_tag_id),
            )
    con.commit()
    con.close()
    return db_path


# ---------------------------------------------------------------------------
# ghost_post_loader: html="" oracle detection regression test
# ---------------------------------------------------------------------------


def test_ghost_post_loader_always_includes_html() -> None:
    """Regression: html="" must never be passed to has_oracle_marker().

    Root cause of the VPS bug: scripts passed html="" to has_oracle_marker(),
    causing 0 oracle articles detected. The shared ghost_post_loader must always
    load the actual HTML from SQLite and pass it through to oracle detection.
    """
    oracle_html = (
        '<p>Oracle Declaration: Will AI regulation pass in 2026?</p>'
        '<div class="np-oracle">NP-2026-0500</div>'
    )
    db_path = _create_ghost_test_db([
        {
            "slug": "ai-regulation-2026",
            "status": "published",
            "title": "AI規制法案の行方",
            "html": oracle_html,
            "tags": ["lang-ja"],
        },
    ])
    try:
        posts = load_ghost_posts(db_path, compute_oracle=True)
        assert len(posts) == 1, f"Expected 1 post, got {len(posts)}"
        post = posts[0]
        # Core regression assertion: html must be non-empty
        assert post["html"] != "", "html field must not be empty — this was the root cause of the VPS oracle bug"
        assert post["html"] == oracle_html, "html field must contain the actual HTML from the DB"
        # Oracle detection must work when html is correctly loaded
        assert post["is_oracle"] is True, (
            "is_oracle must be True when HTML contains oracle markers. "
            "If False, has_oracle_marker() may be receiving html=''"
        )
    finally:
        os.unlink(db_path)


# ---------------------------------------------------------------------------
# ghost_post_loader: tag normalization
# ---------------------------------------------------------------------------


def test_ghost_post_loader_tag_normalization() -> None:
    """tag_slugs must always be a set, never a raw string.

    If tag_slugs is a string, downstream code like `tag_slugs & SOME_SET`
    iterates character-by-character instead of matching whole slugs.
    """
    db_path = _create_ghost_test_db([
        {
            "slug": "post-with-multiple-tags",
            "status": "published",
            "title": "Multi-tag post",
            "html": "<p>content</p>",
            "tags": ["lang-en", "oracle", "geopolitics"],
        },
        {
            "slug": "post-with-no-tags",
            "status": "published",
            "title": "No tags",
            "html": "<p>content</p>",
            "tags": [],
        },
        {
            "slug": "post-with-single-tag",
            "status": "draft",
            "title": "Single tag",
            "html": "<p>content</p>",
            "tags": ["forecast"],
        },
    ])
    try:
        posts = load_ghost_posts(db_path, compute_oracle=False)
        assert len(posts) == 3, f"Expected 3 posts, got {len(posts)}"
        for post in posts:
            assert isinstance(post["tag_slugs"], set), (
                f"tag_slugs for '{post['slug']}' is {type(post['tag_slugs']).__name__}, "
                f"must be set. Raw value: {post['tag_slugs']!r}"
            )

        by_slug = {p["slug"]: p for p in posts}
        assert by_slug["post-with-multiple-tags"]["tag_slugs"] == {"lang-en", "oracle", "geopolitics"}
        assert by_slug["post-with-no-tags"]["tag_slugs"] == set()
        assert by_slug["post-with-single-tag"]["tag_slugs"] == {"forecast"}
    finally:
        os.unlink(db_path)


def test_tag_set_internal_normalization() -> None:
    """Direct test of _tag_set: edge cases for GROUP_CONCAT output."""
    # Normal space-separated tags
    assert _tag_set("lang-en oracle geopolitics") == {"lang-en", "oracle", "geopolitics"}
    # Empty string
    assert _tag_set("") == set()
    # None
    assert _tag_set(None) == set()
    # Single tag
    assert _tag_set("forecast") == {"forecast"}
    # Extra whitespace (GROUP_CONCAT shouldn't produce this, but defensive)
    assert _tag_set("  lang-ja  ") == {"lang-ja"}


# ---------------------------------------------------------------------------
# ghost_post_loader: split_by_status
# ---------------------------------------------------------------------------


def test_ghost_post_loader_split_by_status() -> None:
    """split_by_status must return dicts keyed by slug, separated by status."""
    posts = [
        {"slug": "pub-a", "status": "published", "title": "A", "html": "", "tag_slugs": set(), "is_oracle": False},
        {"slug": "pub-b", "status": "published", "title": "B", "html": "", "tag_slugs": set(), "is_oracle": False},
        {"slug": "draft-c", "status": "draft", "title": "C", "html": "", "tag_slugs": set(), "is_oracle": False},
        {"slug": "draft-d", "status": "draft", "title": "D", "html": "", "tag_slugs": set(), "is_oracle": False},
        {"slug": "draft-e", "status": "draft", "title": "E", "html": "", "tag_slugs": set(), "is_oracle": False},
    ]
    published, draft = split_by_status(posts)

    assert isinstance(published, dict)
    assert isinstance(draft, dict)
    assert set(published.keys()) == {"pub-a", "pub-b"}
    assert set(draft.keys()) == {"draft-c", "draft-d", "draft-e"}
    # Values should be the original post dicts
    assert published["pub-a"]["title"] == "A"
    assert draft["draft-e"]["title"] == "E"


def test_ghost_post_loader_split_by_status_ignores_other_statuses() -> None:
    """Posts with status other than 'published'/'draft' should not appear in either dict."""
    posts = [
        {"slug": "scheduled-f", "status": "scheduled", "title": "F", "html": "", "tag_slugs": set(), "is_oracle": False},
        {"slug": "pub-g", "status": "published", "title": "G", "html": "", "tag_slugs": set(), "is_oracle": False},
    ]
    published, draft = split_by_status(posts)
    assert "scheduled-f" not in published
    assert "scheduled-f" not in draft
    assert "pub-g" in published


# ---------------------------------------------------------------------------
# Slug normalization preserves prediction_id through classification
# ---------------------------------------------------------------------------


def test_slug_normalization_preserves_prediction_id() -> None:
    """prediction_id must survive through classify_missing_sibling unchanged.

    This guards against slug normalization accidentally mangling the prediction_id.
    """
    # Simulate a cross_language_only audit entry: EN article with no JA sibling
    result = classify_missing_sibling(
        slug="en-us-china-trade-war-2026",
        article_lang="en",
        prediction_id="NP-2026-0777",
        published={
            "en-us-china-trade-war-2026": {
                "slug": "en-us-china-trade-war-2026",
                "tag_slugs": "lang-en",
                "title": "US-China Trade War 2026",
                "status": "published",
            },
        },
        draft={},
        pid_to_links={},
    )
    # prediction_id must be preserved exactly
    assert result["prediction_id"] == "NP-2026-0777", (
        f"prediction_id was mangled: {result['prediction_id']!r}"
    )
    assert result["target_lang"] == "ja"
    assert result["missing_reason"] == "ja_missing_entirely"
    # expected_sibling_slug should be the clean slug (without en- prefix)
    assert result["expected_sibling_slug"] == "us-china-trade-war-2026"


# ---------------------------------------------------------------------------
# Ledger dedup chain integrity
# ---------------------------------------------------------------------------


def test_ledger_dedup_chain_integrity() -> None:
    """Append with skip_if_unchanged=True, then verify the chain hash is intact.

    This ensures that dedup-skipped entries don't corrupt the hash chain.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        ledger_path = f.name
    try:
        # Write 3 entries: first, skipped duplicate, then state change
        e1 = append_ledger_entry(
            slug="chain-test", public_url="https://example.com/chain-test/",
            prediction_id="NP-CHAIN-001", article_lang="ja",
            linkage_state="missing_sibling", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash-chain", ledger_path=ledger_path,
        )
        assert e1 is not None

        # Identical state — should be skipped
        e2 = append_ledger_entry(
            slug="chain-test", public_url="https://example.com/chain-test/",
            prediction_id="NP-CHAIN-001", article_lang="ja",
            linkage_state="missing_sibling", article_backing_state="article_backed",
            release_lane="review_required", governor_policy_version="v3",
            mission_contract_hash="hash-chain", ledger_path=ledger_path,
            skip_if_unchanged=True,
        )
        assert e2 is None, "Identical entry should have been skipped"

        # State change — should write
        e3 = append_ledger_entry(
            slug="chain-test", public_url="https://example.com/chain-test/",
            prediction_id="NP-CHAIN-001", article_lang="ja",
            linkage_state="paired_live", article_backing_state="article_backed",
            sibling_slug="en-chain-test", sibling_lang="en",
            release_lane="auto_safe", governor_policy_version="v3",
            mission_contract_hash="hash-chain", ledger_path=ledger_path,
            skip_if_unchanged=True,
        )
        assert e3 is not None

        # Another identical — should skip again
        e4 = append_ledger_entry(
            slug="chain-test", public_url="https://example.com/chain-test/",
            prediction_id="NP-CHAIN-001", article_lang="ja",
            linkage_state="paired_live", article_backing_state="article_backed",
            sibling_slug="en-chain-test", sibling_lang="en",
            release_lane="auto_safe", governor_policy_version="v3",
            mission_contract_hash="hash-chain", ledger_path=ledger_path,
            skip_if_unchanged=True,
        )
        assert e4 is None, "Identical entry should have been skipped again"

        # Verify chain integrity: exactly 2 entries, chain hashes valid
        result = verify_ledger_chain(ledger_path)
        assert result["ok"], f"Chain verification failed: {result.get('error', 'unknown')}"
        assert result["entry_count"] == 2, (
            f"Expected 2 entries (1 skipped + 1 state change), got {result['entry_count']}"
        )
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
