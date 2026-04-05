#!/usr/bin/env python3
"""Regression tests for coordination_guard CLI and derived lock sync."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import coordination_guard as cg  # noqa: E402
import coordination_utils as cu  # noqa: E402


BOARD_TEMPLATE = """# Operations Board — Nowpattern Platform

> x
> Last updated: 2026-04-05 JST

## Cross-Agent Coordination

### Current Agent Snapshot

| Agent | Current Status | Current Scope | Next Exact Step | Source |
|------|----------------|---------------|-----------------|--------|
| old | old | old | old | old |

### Shared Open Queue

1. a
"""


def _seed_root(root: Path) -> None:
    (root / ".coordination").mkdir()
    (root / "docs").mkdir()
    (root / "reports" / "claude_sidecar").mkdir(parents=True)
    (root / ".coordination" / "protocol.json").write_text(
        '{"rules":{"stale_threshold_seconds":600}}',
        encoding="utf-8",
    )
    (root / "docs" / "OPERATIONS_BOARD.md").write_text(BOARD_TEMPLATE, encoding="utf-8")
    (root / ".coordination" / "claude-code.json").write_text(
        '{"agent":"claude-code","status":"idle","current_task":"","next_step":"","locked_files":[],"vps_resources":[],"updated_at":"2026-04-05T11:00:00+09:00"}',
        encoding="utf-8",
    )
    (root / "reports" / "claude_sidecar" / "session_status.json").write_text("{}", encoding="utf-8")


def run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _seed_root(root)

        result = cg.cmd_heartbeat(
            type(
                "Args",
                (),
                {
                    "root": str(root),
                    "agent": "codex",
                    "status": "active",
                    "task": "coord task",
                    "next_step": "next",
                    "locked_files": "scripts/a.py,docs/OPERATIONS_BOARD.md",
                    "vps_resources": "",
                    "session_id": "",
                },
            )()
        )
        assert result == 0

        codex_state = cu.read_json(root / ".coordination" / "codex.json")
        assert codex_state["locked_files"] == ["scripts/a.py", "docs/OPERATIONS_BOARD.md"]

        registry = cu.read_json(root / ".coordination" / "lock-registry.json")
        assert registry["generated_from"] == ".coordination/*.json"
        assert any(item["path"] == "scripts/a.py" for item in registry["locks"])

        ok = cg.cmd_check(
            type("Args", (), {"root": str(root), "agent": "codex", "path": "scripts/a.py"})()
        )
        assert ok == 0

        blocked = cg.cmd_check(
            type("Args", (), {"root": str(root), "agent": "claude-code", "path": "scripts/a.py"})()
        )
        assert blocked == 2

        board_text = (root / "docs" / "OPERATIONS_BOARD.md").read_text(encoding="utf-8")
        assert "coord task" in board_text

        keepalive_result = cg.cmd_keepalive(
            type(
                "Args",
                (),
                {
                    "root": str(root),
                    "agent": "codex",
                    "status": "active",
                    "task": "coord task keepalive",
                    "next_step": "still running",
                    "locked_files": "scripts/a.py",
                    "vps_resources": "",
                    "session_id": "",
                    "interval": "1",
                    "iterations": "2",
                },
            )()
        )
        assert keepalive_result == 0
        refreshed_state = cu.read_json(root / ".coordination" / "codex.json")
        assert refreshed_state["current_task"] == "coord task keepalive"

    print("PASS: coordination guard regression checks")


if __name__ == "__main__":
    run()
