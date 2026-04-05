#!/usr/bin/env python3
"""Regression tests for operations-board synchronization."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import update_operations_board as uob  # noqa: E402


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


def test_build_agent_rows_uses_coordination_and_sidecar_state() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".coordination").mkdir()
        (root / "reports" / "claude_sidecar").mkdir(parents=True)
        (root / ".coordination" / "codex.json").write_text(
            '{"status":"active","current_task":"codex-task","next_step":"do codex"}',
            encoding="utf-8",
        )
        (root / ".coordination" / "claude-code.json").write_text(
            '{"status":"active","current_task":"claude-task","next_step":"fallback next"}',
            encoding="utf-8",
        )
        (root / "reports" / "claude_sidecar" / "session_status.json").write_text(
            '{"status":"in_progress","task_id":"sidecar-1","current_phase":"phase-a","next_exact_step":"do sidecar"}',
            encoding="utf-8",
        )

        rows = uob.build_agent_rows(root)
        assert rows[0]["agent"] == "Codex"
        assert rows[0]["status"] == "IN_PROGRESS"
        assert rows[0]["scope"] == "codex-task"
        assert rows[0]["next_step"] == "do codex"
        assert rows[1]["agent"] == "Claude Code sidecar"
        assert rows[1]["scope"] == "`sidecar-1` / `phase-a`"
        assert rows[1]["next_step"] == "do sidecar"


def test_build_agent_rows_discovers_additional_agents() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".coordination").mkdir()
        (root / "reports" / "claude_sidecar").mkdir(parents=True)
        (root / ".coordination" / "codex.json").write_text(
            '{"agent":"codex","status":"active","current_task":"codex-task","next_step":"do codex"}',
            encoding="utf-8",
        )
        (root / ".coordination" / "review-bot.json").write_text(
            '{"agent":"review-bot","status":"blocked","current_task":"review scope","next_step":"wait for code"}',
            encoding="utf-8",
        )
        (root / "reports" / "claude_sidecar" / "session_status.json").write_text("{}", encoding="utf-8")

        rows = uob.build_agent_rows(root)
        assert any(row["agent"] == "Review Bot" for row in rows)
        extra = next(row for row in rows if row["agent"] == "Review Bot")
        assert extra["status"] == "BLOCKED"
        assert extra["scope"] == "review scope"
        assert extra["source"] == "`.coordination/review-bot.json`"


def test_sync_board_replaces_snapshot_table() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "docs").mkdir()
        (root / ".coordination").mkdir()
        (root / "reports" / "claude_sidecar").mkdir(parents=True)
        (root / "docs" / "OPERATIONS_BOARD.md").write_text(BOARD_TEMPLATE, encoding="utf-8")
        (root / ".coordination" / "codex.json").write_text(
            '{"status":"active","current_task":"codex-task","next_step":"step-c"}',
            encoding="utf-8",
        )
        (root / ".coordination" / "claude-code.json").write_text(
            '{"status":"idle","current_task":"","next_step":""}',
            encoding="utf-8",
        )
        (root / "reports" / "claude_sidecar" / "session_status.json").write_text(
            '{"status":"completed","task_id":"sidecar-2","current_phase":"phase-b","next_exact_step":"step-s"}',
            encoding="utf-8",
        )

        updated = uob.sync_board(root)
        assert "codex-task" in updated
        assert "step-c" in updated
        assert "`DONE`" in updated
        assert "`sidecar-2` / `phase-b`" in updated
        assert "### Shared Open Queue" in updated


def test_completed_sidecar_does_not_fall_back_to_stale_coord_next_step() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".coordination").mkdir()
        (root / "reports" / "claude_sidecar").mkdir(parents=True)
        (root / ".coordination" / "codex.json").write_text(
            '{"status":"idle","current_task":"","next_step":""}',
            encoding="utf-8",
        )
        (root / ".coordination" / "claude-code.json").write_text(
            '{"status":"active","current_task":"stale-task","next_step":"stale next"}',
            encoding="utf-8",
        )
        (root / "reports" / "claude_sidecar" / "session_status.json").write_text(
            '{"status":"completed","task_id":"sidecar-3","current_phase":"all-phases-done","next_exact_step":""}',
            encoding="utf-8",
        )

        rows = uob.build_agent_rows(root)
        assert rows[1]["status"] == "DONE"
        assert rows[1]["next_step"] == "completed; choose next scope from Shared Open Queue"
        assert rows[1]["source"] == "`reports/claude_sidecar/session_status.json`"


def run() -> None:
    test_build_agent_rows_uses_coordination_and_sidecar_state()
    test_build_agent_rows_discovers_additional_agents()
    test_sync_board_replaces_snapshot_table()
    test_completed_sidecar_does_not_fall_back_to_stale_coord_next_step()
    print("PASS: update operations board regression checks")


if __name__ == "__main__":
    run()
