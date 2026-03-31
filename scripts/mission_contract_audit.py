#!/usr/bin/env python3
"""Fail if active agent entrypoints are not wired to the shared mission contract."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TOKENS = {
    "scripts/release_governor.py": ["assert_mission_handshake", "MISSION_HANDSHAKE", "mission_contract_version"],
    "scripts/ecosystem_governance_audit.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/ghost_webhook_server.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/qa_sentinel.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/site_guard_runner.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/nowpattern_publisher.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/nowpattern-deep-pattern-generate.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/breaking-news-watcher.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/breaking_pipeline_helper.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/ghost_content_gate.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/ghost_to_tweet_queue.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/auto_tweet.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/x_swarm_dispatcher.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/substack_notes_poster.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    "scripts/neo_queue_dispatcher.py": ["assert_mission_handshake", "MISSION_HANDSHAKE"],
    ".claude/hooks/session-start.sh": ["mission_contract.py", "--summary", "agent_bootstrap_context.py", "--summary"],
}
OPTIONAL_PATHS = {
    ".claude/hooks/session-start.sh",
}


def main() -> int:
    failures: list[dict[str, object]] = []
    for rel_path, tokens in EXPECTED_TOKENS.items():
        path = REPO_ROOT / rel_path
        if not path.exists():
            if rel_path in OPTIONAL_PATHS:
                continue
            failures.append({"path": rel_path, "error": "missing_file"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        missing = [token for token in tokens if token not in text]
        if missing:
            failures.append({"path": rel_path, "missing_tokens": missing})

    report = {
        "checked": len(EXPECTED_TOKENS),
        "failures": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
