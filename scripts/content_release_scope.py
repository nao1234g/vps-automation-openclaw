#!/usr/bin/env python3
"""Shared scope rules for canonical public content reporting."""

from __future__ import annotations

from collections.abc import Iterable

SKIP_SLUGS = {
    "about",
    "en-about",
    "predictions",
    "en-predictions",
    "members",
    "en-members",
    "taxonomy",
    "en-taxonomy",
    "taxonomy-guide",
    "en-taxonomy-guide",
    "taxonomy-ja",
}


def is_release_scope_slug(slug: str) -> bool:
    value = (slug or "").strip()
    return bool(value) and value not in SKIP_SLUGS


def filter_release_scope_posts(posts: Iterable[dict]) -> list[dict]:
    return [post for post in posts if is_release_scope_slug(str(post.get("slug", "")).strip())]


def count_release_scope_posts(posts: Iterable[dict]) -> int:
    return len(filter_release_scope_posts(posts))
