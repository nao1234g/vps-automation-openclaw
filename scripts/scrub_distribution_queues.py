#!/usr/bin/env python3
"""Block stale distribution queue items that no longer pass release policy."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

SCRIPTS_DIR = Path("/opt/shared/scripts")
MANIFEST_PATH = Path("/opt/shared/reports/article_release_manifest.json")
TWEET_QUEUE = SCRIPTS_DIR / "tweet_queue.json"
BREAKING_QUEUE = SCRIPTS_DIR / "breaking_queue.json"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def slug_from_url(url: str) -> str:
    path = urlparse(url or "").path.strip("/")
    if not path:
        return ""
    parts = [p for p in path.split("/") if p]
    if not parts:
        return ""
    if parts[0] == "en" and len(parts) > 1:
        return "en-" + parts[-1]
    return parts[-1]


def main() -> int:
    manifest_data = load_json(MANIFEST_PATH, {"posts": []})
    manifest = {row.get("slug", ""): row for row in manifest_data.get("posts", [])}

    tweet_queue = load_json(TWEET_QUEUE, {"tweets": []})
    breaking_queue = load_json(BREAKING_QUEUE, [])

    tweet_blocked = 0
    for item in tweet_queue.get("tweets", []):
        if item.get("status") != "pending":
            continue
        slug = item.get("source_slug") or item.get("name") or slug_from_url(item.get("link", ""))
        row = manifest.get(slug, {})
        if not item.get("distribution_approved") or not row.get("distribution_allowed"):
            item["status"] = "blocked"
            item["error"] = "release_policy_blocked"
            tweet_blocked += 1

    breaking_blocked = 0
    for item in breaking_queue:
        if item.get("status") != "article_ready":
            continue
        slug = slug_from_url(item.get("ghost_url", ""))
        row = manifest.get(slug, {})
        if not row.get("distribution_allowed"):
            item["status"] = "distribution_blocked"
            breaking_blocked += 1

    save_json(TWEET_QUEUE, tweet_queue)
    save_json(BREAKING_QUEUE, breaking_queue)

    print(json.dumps({
        "tweet_blocked": tweet_blocked,
        "breaking_blocked": breaking_blocked,
        "tweet_total": len(tweet_queue.get("tweets", [])),
        "breaking_total": len(breaking_queue),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
