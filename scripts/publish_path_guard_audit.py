#!/usr/bin/env python3
"""Fail if any active publish/distribution path lacks a release blocker."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

ACTIVE_PATHS = {
    "prediction_page_builder.py": ["prediction_deploy_gate.py", "--skip-deploy-gate"],
    "nowpattern_publisher.py": ["assert_release_ready", "article_release_guard"],
    "nowpattern-deep-pattern-generate.py": ["evaluate_release_blockers", "article_release_guard"],
    "breaking-news-watcher.py": ["evaluate_release_blockers", "article_release_guard"],
    "breaking_pipeline_helper.py": ["evaluate_release_blockers", "article_release_guard"],
    "ghost_webhook_server.py": ["evaluate_release_blockers", "article_release_guard"],
    "ghost_content_gate.py": ["evaluate_release_blockers", "article_release_guard"],
    "qa_sentinel.py": ["evaluate_release_blockers", "article_release_guard"],
    "ghost_to_tweet_queue.py": ["evaluate_release_blockers", "article_release_guard"],
    "auto_tweet.py": ["distribution_approved"],
    "substack_notes_poster.py": ["distribution_allowed", "distribution_approved"],
    "x_swarm_dispatcher.py": ["distribution_allowed", "RELEASE_MANIFEST"],
}


def main() -> int:
    failures: list[dict[str, object]] = []
    for rel_path, required_tokens in ACTIVE_PATHS.items():
        path = ROOT / rel_path
        if not path.exists():
            failures.append({"path": rel_path, "error": "missing_file"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        missing = [token for token in required_tokens if token not in text]
        if missing:
            failures.append({"path": rel_path, "missing_tokens": missing})

    report = {"checked": len(ACTIVE_PATHS), "failures": failures}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
