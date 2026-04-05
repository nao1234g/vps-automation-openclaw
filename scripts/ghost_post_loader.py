#!/usr/bin/env python3
"""Shared Ghost DB loader.

Single source of truth for loading Ghost posts from SQLite.
All scripts that read Ghost posts should use this module instead
of writing their own SQL queries.

This prevents html="" bugs and field inconsistencies across scripts.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from article_release_guard import has_oracle_marker
from content_release_scope import SKIP_SLUGS

GHOST_DB_DEFAULT = "/var/www/nowpattern/content/data/ghost.db"

# ---------------------------------------------------------------------------
# Core data structure
# ---------------------------------------------------------------------------

# Each GhostPost dict has:
#   slug: str
#   status: str ("published" | "draft")
#   title: str
#   html: str
#   tag_slugs: set[str]  (normalized to set, never raw string)
#   post_id: str  (Ghost internal UUID)
#   updated_at: str
#   is_oracle: bool  (computed from has_oracle_marker)


def _tag_set(raw_tag_slugs: str | None) -> set[str]:
    """Normalize tag_slugs from GROUP_CONCAT string to set."""
    return set((raw_tag_slugs or "").split()) - {""}


def load_ghost_posts(
    ghost_db_path: str = GHOST_DB_DEFAULT,
    *,
    include_draft: bool = True,
    published_only: bool = False,
    compute_oracle: bool = True,
    skip_scope_slugs: bool = False,
) -> list[dict[str, Any]]:
    """Load Ghost posts with all fields needed by release/linkage scripts.

    Args:
        ghost_db_path: Path to Ghost SQLite database.
        include_draft: If False, exclude draft posts entirely.
        published_only: If True, only load published posts (same as include_draft=False).
        compute_oracle: If True, compute is_oracle via has_oracle_marker.
        skip_scope_slugs: If True, exclude SKIP_SLUGS (about, taxonomy, etc).

    Returns:
        List of GhostPost dicts with normalized fields.
    """
    con = sqlite3.connect(ghost_db_path)
    con.row_factory = sqlite3.Row

    status_filter = ""
    if published_only or not include_draft:
        status_filter = "AND p.status = 'published'"

    rows = con.execute(
        f"""
        SELECT p.id AS post_id, p.slug, p.status, p.title, p.html,
               p.updated_at,
               COALESCE(GROUP_CONCAT(t.slug, ' '), '') AS tag_slugs
        FROM posts p
        LEFT JOIN posts_tags pt ON pt.post_id = p.id
        LEFT JOIN tags t ON t.id = pt.tag_id
        WHERE p.type = 'post' {status_filter}
        GROUP BY p.id, p.slug, p.status, p.title, p.html, p.updated_at
        ORDER BY p.published_at DESC
        """
    ).fetchall()
    con.close()

    posts: list[dict[str, Any]] = []
    for r in rows:
        slug = r["slug"]
        if skip_scope_slugs and slug in SKIP_SLUGS:
            continue

        tag_slugs = _tag_set(r["tag_slugs"])
        title = r["title"] or ""
        html = r["html"] or ""

        is_oracle = False
        if compute_oracle:
            is_oracle = has_oracle_marker(title=title, html=html, tags=tag_slugs)

        posts.append({
            "slug": slug,
            "status": r["status"],
            "title": title,
            "html": html,
            "tag_slugs": tag_slugs,
            "post_id": str(r["post_id"]),
            "updated_at": str(r["updated_at"] or ""),
            "is_oracle": is_oracle,
        })

    return posts


# ---------------------------------------------------------------------------
# Convenience splits (published / draft)
# ---------------------------------------------------------------------------


def split_by_status(
    posts: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Split posts into published and draft dicts keyed by slug.

    Returns:
        (published_by_slug, draft_by_slug)
    """
    published: dict[str, dict[str, Any]] = {}
    draft: dict[str, dict[str, Any]] = {}
    for post in posts:
        if post["status"] == "published":
            published[post["slug"]] = post
        elif post["status"] == "draft":
            draft[post["slug"]] = post
    return published, draft


def published_slugs_set(posts: list[dict[str, Any]]) -> set[str]:
    """Return set of published post slugs."""
    return {p["slug"] for p in posts if p["status"] == "published"}


def draft_slugs_set(posts: list[dict[str, Any]]) -> set[str]:
    """Return set of draft post slugs."""
    return {p["slug"] for p in posts if p["status"] == "draft"}


def oracle_posts(posts: list[dict[str, Any]], status: str = "published") -> list[dict[str, Any]]:
    """Return oracle-marked posts filtered by status."""
    return [p for p in posts if p["is_oracle"] and p["status"] == status]
