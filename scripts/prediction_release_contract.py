#!/usr/bin/env python3
"""Prediction-linked article release contract: JA/EN linkage + append-only ledger.

Purpose:
  - Evaluate whether a prediction-linked article has a cross-language sibling.
  - Classify linkage_state and article_backing_state for release decisions.
  - Append release events to an immutable JSONL ledger with hash chaining.

Integration:
  - Called from article_release_guard.evaluate_release_blockers() for oracle articles.
  - Results flow through release_governor → build_article_release_manifest.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from runtime_boundary import shared_or_local_path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_REPORT_DIR = shared_or_local_path(
    script_file=__file__,
    shared_path="/opt/shared/reports",
    local_path=_REPO_ROOT / "reports",
)
LEDGER_PATH = str(_REPORT_DIR / "article_release_ledger.jsonl")

GHOST_DB_DEFAULT = "/var/www/nowpattern/content/data/ghost.db"

PREDICTION_DB_DEFAULT = str(
    shared_or_local_path(
        script_file=__file__,
        shared_path="/opt/shared/scripts/prediction_db.json",
        local_path=_SCRIPT_DIR / "prediction_db.json",
    )
)


# ---------------------------------------------------------------------------
# Prediction ID mapping (slug → prediction_id)
# ---------------------------------------------------------------------------


def load_prediction_db(path: str = PREDICTION_DB_DEFAULT) -> dict[str, Any]:
    """Load prediction_db.json and return the parsed dict."""
    if not os.path.exists(path):
        return {"predictions": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_slug_to_prediction_index(
    prediction_db: dict[str, Any] | None = None,
    prediction_db_path: str = PREDICTION_DB_DEFAULT,
) -> dict[str, str]:
    """Build deterministic Ghost slug → prediction_id index.

    Sources (checked in order for each prediction):
      1. article_slug field (primary article)
      2. article_links[].slug (all language variants)

    First writer wins: if a slug maps to multiple predictions, the first
    prediction encountered keeps the mapping.
    """
    if prediction_db is None:
        prediction_db = load_prediction_db(prediction_db_path)

    index: dict[str, str] = {}
    for pred in prediction_db.get("predictions", []):
        pid = str(pred.get("prediction_id", "")).strip()
        if not pid:
            continue

        # Primary article_slug
        primary = str(pred.get("article_slug") or "").strip()
        if primary and primary not in index:
            index[primary] = pid

        # All article_links slugs
        for link in pred.get("article_links") or []:
            if not isinstance(link, dict):
                continue
            slug = str(link.get("slug") or "").strip()
            if slug and slug not in index:
                index[slug] = pid

    return index


def build_prediction_article_links_index(
    prediction_db: dict[str, Any] | None = None,
    prediction_db_path: str = PREDICTION_DB_DEFAULT,
) -> dict[str, list[dict[str, Any]]]:
    """Build prediction_id → article_links index for sibling lookup."""
    if prediction_db is None:
        prediction_db = load_prediction_db(prediction_db_path)

    index: dict[str, list[dict[str, Any]]] = {}
    for pred in prediction_db.get("predictions", []):
        pid = str(pred.get("prediction_id", "")).strip()
        if not pid:
            continue
        links = pred.get("article_links") or []
        if links:
            index[pid] = links

    return index


# ---------------------------------------------------------------------------
# Linkage state definitions
# ---------------------------------------------------------------------------
#   paired_live        – Both JA and EN articles exist and are published.
#   missing_sibling    – Only one language version exists (other is missing).
#   cross_language_only – Article exists only in one language with no matching
#                        prediction_db article_links entry for the other.
#   tracker_only       – Prediction exists in prediction_db but has no
#                        published Ghost article at all.
LINKAGE_STATES = {
    "paired_live",
    "missing_sibling",
    "cross_language_only",
    "tracker_only",
}

# Article backing state definitions
#   article_backed  – At least one published Ghost article backs this prediction.
#   tracker_only    – Prediction is in prediction_db only; no published article.
BACKING_STATES = {"article_backed", "tracker_only"}


# ---------------------------------------------------------------------------
# Cross-language sibling detection (aligned with repair_cross_language_article_links.py)
# ---------------------------------------------------------------------------


def detect_article_lang(slug: str, tag_slugs: set[str] | frozenset[str]) -> str:
    """Determine article language from tag or slug prefix."""
    if "lang-en" in tag_slugs or str(slug).startswith("en-"):
        return "en"
    return "ja"


def clean_slug(slug: str) -> str:
    """Strip 'en-' prefix to get the base slug shared by JA/EN siblings."""
    s = str(slug)
    return s[3:] if s.startswith("en-") else s


def build_sibling_maps(
    posts: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, str]]:
    """Build clean_slug → slug maps for JA and EN published posts.

    Args:
        posts: list of dicts with keys: slug, tag_slugs (set or space-separated str), status

    Returns:
        (ja_by_clean, en_by_clean) – each maps clean_slug to the actual post slug.
    """
    ja_by_clean: dict[str, str] = {}
    en_by_clean: dict[str, str] = {}
    for post in posts:
        slug = str(post.get("slug", ""))
        status = str(post.get("status", ""))
        if not slug or status != "published":
            continue
        raw_tags = post.get("tag_slugs")
        if isinstance(raw_tags, (set, frozenset)):
            tags = raw_tags
        else:
            tags = set(str(raw_tags or "").split())
        lang = detect_article_lang(slug, tags)
        cs = clean_slug(slug)
        if lang == "en":
            en_by_clean.setdefault(cs, slug)
        else:
            ja_by_clean.setdefault(cs, slug)
    return ja_by_clean, en_by_clean


def build_sibling_maps_from_db(
    ghost_db_path: str = GHOST_DB_DEFAULT,
) -> tuple[dict[str, str], dict[str, str]]:
    """Build sibling maps directly from Ghost SQLite DB."""
    con = sqlite3.connect(ghost_db_path)
    rows = con.execute(
        """
        SELECT p.slug,
               COALESCE(GROUP_CONCAT(t.slug, ' '), '') AS tag_slugs,
               p.status
        FROM posts p
        LEFT JOIN posts_tags pt ON pt.post_id = p.id
        LEFT JOIN tags t ON t.id = pt.tag_id
        WHERE p.type = 'post' AND p.status = 'published'
        GROUP BY p.id, p.slug, p.status
        """
    ).fetchall()
    con.close()
    posts = [
        {"slug": r[0], "tag_slugs": set((r[1] or "").split()), "status": r[2]}
        for r in rows
    ]
    return build_sibling_maps(posts)


# ---------------------------------------------------------------------------
# Linkage evaluation
# ---------------------------------------------------------------------------


def evaluate_prediction_linkage(
    *,
    slug: str,
    tag_slugs: set[str] | frozenset[str],
    prediction_id: str = "",
    ja_by_clean: dict[str, str] | None = None,
    en_by_clean: dict[str, str] | None = None,
    prediction_article_links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate cross-language linkage for a prediction-linked article.

    Args:
        slug: Ghost article slug.
        tag_slugs: Set of tag slugs for the article.
        prediction_id: The NP-YYYY-XXXX prediction identifier (if known).
        ja_by_clean: clean_slug → JA slug map (pre-built for batch use).
        en_by_clean: clean_slug → EN slug map (pre-built for batch use).
        prediction_article_links: article_links array from prediction_db entry.

    Returns:
        dict with keys:
          - prediction_id: str
          - article_lang: str ("ja" or "en")
          - linkage_state: str (one of LINKAGE_STATES)
          - article_backing_state: str (one of BACKING_STATES)
          - same_prediction_sibling_lang: str | None
          - same_prediction_sibling_slug: str | None
          - clean_slug: str
          - errors: list[str]
    """
    ja_by_clean = ja_by_clean or {}
    en_by_clean = en_by_clean or {}

    article_lang = detect_article_lang(slug, tag_slugs)
    cs = clean_slug(slug)

    # Determine if this article is backed (published in Ghost)
    self_map = en_by_clean if article_lang == "en" else ja_by_clean
    is_self_live = cs in self_map

    # Look for sibling in the other language
    sibling_map = ja_by_clean if article_lang == "en" else en_by_clean
    sibling_slug = sibling_map.get(cs)

    # Also check prediction_db article_links for the sibling
    sibling_from_db = None
    if prediction_article_links:
        target_lang = "ja" if article_lang == "en" else "en"
        for link in prediction_article_links:
            if link.get("lang") == target_lang:
                sibling_from_db = link.get("slug", "")
                break

    # Determine linkage_state
    if not is_self_live:
        linkage_state = "tracker_only"
        article_backing_state = "tracker_only"
    elif sibling_slug:
        linkage_state = "paired_live"
        article_backing_state = "article_backed"
    elif sibling_from_db:
        # prediction_db knows about a sibling but it's not published
        linkage_state = "cross_language_only"
        article_backing_state = "article_backed"
    else:
        linkage_state = "missing_sibling"
        article_backing_state = "article_backed"

    # Build errors
    errors: list[str] = []
    if linkage_state == "missing_sibling":
        target_lang = "ja" if article_lang == "en" else "en"
        errors.append(
            f"PREDICTION_SIBLING_MISSING:{target_lang}:{prediction_id or 'unknown'}"
        )
    if linkage_state == "tracker_only":
        errors.append(
            f"PREDICTION_NO_PUBLISHED_ARTICLE:{prediction_id or 'unknown'}"
        )

    sibling_lang = None
    if sibling_slug:
        sibling_lang = "ja" if article_lang == "en" else "en"

    return {
        "prediction_id": prediction_id,
        "article_lang": article_lang,
        "linkage_state": linkage_state,
        "article_backing_state": article_backing_state,
        "same_prediction_sibling_lang": sibling_lang,
        "same_prediction_sibling_slug": sibling_slug,
        "clean_slug": cs,
        "errors": errors,
    }


def evaluate_prediction_publish_intent(
    *,
    prediction_id: str,
    article_lang: str,
    prediction_article_links: list[dict[str, Any]] | None = None,
    ja_by_clean: dict[str, str] | None = None,
    en_by_clean: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Evaluate pre-publish sibling readiness for a prediction-linked article.

    Unlike evaluate_prediction_linkage(), this helper is for the article that is
    about to be published, so the current article does not need to be live yet.
    The gating question is: does the opposite-language sibling already exist and
    is it published?
    """
    lang = "en" if str(article_lang).strip().lower() == "en" else "ja"
    target_lang = "ja" if lang == "en" else "en"
    ja_by_clean = ja_by_clean or {}
    en_by_clean = en_by_clean or {}

    current_link: dict[str, Any] | None = None
    sibling_link: dict[str, Any] | None = None
    for link in prediction_article_links or []:
        if not isinstance(link, dict):
            continue
        link_lang = str(link.get("lang") or "").strip().lower()
        if link_lang == lang and current_link is None:
            current_link = link
        elif link_lang == target_lang and sibling_link is None:
            sibling_link = link

    sibling_slug = str((sibling_link or {}).get("slug") or "").strip()
    sibling_url = str((sibling_link or {}).get("url") or "").strip()
    sibling_map = ja_by_clean if target_lang == "ja" else en_by_clean

    sibling_live_slug = ""
    if sibling_slug:
        sibling_live_slug = sibling_map.get(clean_slug(sibling_slug), "")

    if sibling_live_slug:
        linkage_state = "paired_live"
    elif sibling_slug:
        linkage_state = "cross_language_only"
    else:
        linkage_state = "missing_sibling"

    # For pre-publish intent, the current article is not live yet. The backing
    # state is still useful as a coarse indicator of whether the prediction has
    # article metadata at all.
    article_backing_state = (
        "article_backed" if current_link or sibling_link else "tracker_only"
    )

    errors: list[str] = []
    if linkage_state == "missing_sibling":
        errors.append(
            f"PREDICTION_SIBLING_MISSING:{target_lang}:{prediction_id or 'unknown'}"
        )

    return {
        "prediction_id": prediction_id,
        "article_lang": lang,
        "linkage_state": linkage_state,
        "article_backing_state": article_backing_state,
        "same_prediction_sibling_lang": target_lang if (sibling_slug or sibling_live_slug) else None,
        "same_prediction_sibling_slug": sibling_live_slug or sibling_slug or None,
        "same_prediction_sibling_url": sibling_url,
        "clean_slug": clean_slug(str((current_link or {}).get("slug") or "")),
        "errors": errors,
        "intent_basis": "prepublish",
    }


def coerce_prediction_linkage_publish_status(
    requested_status: str,
    prediction_linkage: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    """Force draft for published oracle work until the sibling is live."""
    normalized = str(requested_status or "published").strip().lower()
    if normalized != "published" or not prediction_linkage:
        return normalized, []

    linkage_state = str(prediction_linkage.get("linkage_state") or "").strip()
    if not linkage_state or linkage_state == "paired_live":
        return normalized, []

    prediction_id = str(prediction_linkage.get("prediction_id") or "unknown").strip() or "unknown"
    article_lang = str(prediction_linkage.get("article_lang") or "ja").strip() or "ja"
    return "draft", [
        f"PREDICTION_LINKAGE_DRAFT:{prediction_id}:{article_lang}:{linkage_state}"
    ]


# ---------------------------------------------------------------------------
# Append-only release ledger
# ---------------------------------------------------------------------------


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _entry_hash(entry: dict[str, Any]) -> str:
    raw = json.dumps(entry, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_last_ledger_entry(ledger_path: str = LEDGER_PATH) -> dict[str, Any] | None:
    """Read the last entry from the JSONL ledger."""
    if not os.path.exists(ledger_path):
        return None
    last_line = ""
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                last_line = stripped
    if not last_line:
        return None
    return json.loads(last_line)


def read_latest_entry_by_slug(slug: str, ledger_path: str = LEDGER_PATH) -> dict[str, Any] | None:
    """Read the most recent ledger entry for a specific slug."""
    if not os.path.exists(ledger_path):
        return None
    latest = None
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            entry = json.loads(stripped)
            if entry.get("slug") == slug:
                latest = entry
    return latest


def _state_signature(
    linkage_state: str,
    article_backing_state: str,
    release_lane: str,
    sibling_slug: str | None,
    prediction_id: str,
    governor_policy_version: str,
) -> str:
    """Deterministic signature of the state-bearing fields for dedup."""
    parts = [
        linkage_state,
        article_backing_state,
        release_lane,
        sibling_slug or "",
        prediction_id,
        governor_policy_version,
    ]
    return "|".join(parts)


def append_ledger_entry(
    *,
    slug: str,
    public_url: str,
    prediction_id: str,
    article_lang: str,
    linkage_state: str,
    article_backing_state: str,
    sibling_lang: str | None = None,
    sibling_slug: str | None = None,
    sibling_url: str | None = None,
    release_lane: str,
    governor_policy_version: str,
    mission_contract_hash: str,
    content_hash: str = "",
    ledger_path: str = LEDGER_PATH,
    skip_if_unchanged: bool = False,
) -> dict[str, Any] | None:
    """Append one entry to the release ledger with hash chaining.

    When skip_if_unchanged=True, checks whether the most recent entry for this
    slug has identical state-bearing fields (linkage_state, article_backing_state,
    release_lane, sibling_slug, prediction_id, governor_policy_version).
    If unchanged, returns None without appending (preserving hash chain integrity).

    Returns the appended entry dict, or None if skipped.
    """
    # State-change dedup: skip if identical state already recorded
    if skip_if_unchanged:
        existing = read_latest_entry_by_slug(slug, ledger_path)
        if existing:
            old_sig = _state_signature(
                linkage_state=existing.get("linkage_state", ""),
                article_backing_state=existing.get("article_backing_state", ""),
                release_lane=existing.get("release_lane", ""),
                sibling_slug=existing.get("same_prediction_sibling_slug"),
                prediction_id=existing.get("prediction_id", ""),
                governor_policy_version=existing.get("governor_policy_version", ""),
            )
            new_sig = _state_signature(
                linkage_state=linkage_state,
                article_backing_state=article_backing_state,
                release_lane=release_lane,
                sibling_slug=sibling_slug,
                prediction_id=prediction_id,
                governor_policy_version=governor_policy_version,
            )
            if old_sig == new_sig:
                return None

    # Read previous entry for chain
    prev = read_last_ledger_entry(ledger_path)
    previous_entry_hash = prev["entry_hash"] if prev else ""

    entry: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "slug": slug,
        "public_url": public_url,
        "prediction_id": prediction_id,
        "article_lang": article_lang,
        "linkage_state": linkage_state,
        "article_backing_state": article_backing_state,
        "same_prediction_sibling_lang": sibling_lang,
        "same_prediction_sibling_slug": sibling_slug,
        "same_prediction_sibling_url": sibling_url or "",
        "release_lane": release_lane,
        "governor_policy_version": governor_policy_version,
        "mission_contract_hash": mission_contract_hash,
        "content_hash": content_hash,
        "previous_entry_hash": previous_entry_hash,
    }
    entry["entry_hash"] = _entry_hash(entry)

    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def verify_ledger_chain(ledger_path: str = LEDGER_PATH) -> dict[str, Any]:
    """Verify hash chain integrity of the ledger.

    Returns dict with ok, entry_count, broken_at (index or None), errors.
    """
    if not os.path.exists(ledger_path):
        return {"ok": True, "entry_count": 0, "broken_at": None, "errors": []}

    entries: list[dict[str, Any]] = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                entries.append(json.loads(stripped))

    errors: list[str] = []
    for i, entry in enumerate(entries):
        # Verify entry_hash
        stored_hash = entry.get("entry_hash", "")
        check_entry = {k: v for k, v in entry.items() if k != "entry_hash"}
        expected_hash = _entry_hash(check_entry)
        if stored_hash != expected_hash:
            errors.append(f"entry[{i}]: entry_hash mismatch")

        # Verify chain link
        expected_prev = entries[i - 1]["entry_hash"] if i > 0 else ""
        actual_prev = entry.get("previous_entry_hash", "")
        if actual_prev != expected_prev:
            errors.append(f"entry[{i}]: previous_entry_hash mismatch")

    return {
        "ok": not errors,
        "entry_count": len(entries),
        "broken_at": None if not errors else int(errors[0].split("[")[1].split("]")[0]),
        "errors": errors,
    }
