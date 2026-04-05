#!/usr/bin/env python3
"""Sync the shared operations board from coordination state files."""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

from coordination_utils import load_agent_states, read_json, sync_lock_registry

BOARD_PATH = Path("docs/OPERATIONS_BOARD.md")
COORD_DIR = Path(".coordination")
SIDECAR_STATUS_PATH = Path("reports/claude_sidecar/session_status.json")

SNAPSHOT_START = "### Current Agent Snapshot"
SNAPSHOT_END = "### Shared Open Queue"
UPDATED_PREFIX = "> Last updated: "

def _normalize_status(raw: str) -> str:
    value = str(raw or "").strip().lower()
    mapping = {
        "active": "IN_PROGRESS",
        "in_progress": "IN_PROGRESS",
        "idle": "IDLE",
        "completed": "DONE",
        "done": "DONE",
        "blocked": "BLOCKED",
        "interrupted": "BLOCKED",
    }
    return mapping.get(value, (str(raw or "").strip().upper() or "UNKNOWN"))


def _fmt(value: str, fallback: str = "(not set)") -> str:
    text = str(value or "").strip()
    return text or fallback


def _claude_next_step(sidecar_state: dict, claude_state: dict) -> tuple[str, str]:
    sidecar_status = str(sidecar_state.get("status") or "").strip().lower()
    sidecar_next = str(sidecar_state.get("next_exact_step") or "").strip()
    coord_next = str(claude_state.get("next_step") or "").strip()

    if sidecar_next:
        return sidecar_next, "`reports/claude_sidecar/session_status.json`"
    if sidecar_status == "completed":
        return (
            "completed; choose next scope from Shared Open Queue",
            "`reports/claude_sidecar/session_status.json`",
        )
    if coord_next:
        return coord_next, "`.coordination/claude-code.json`"
    return "(not set)", "`reports/claude_sidecar/session_status.json`"


def _display_agent_name(agent_name: str, *, sidecar: bool = False) -> str:
    normalized = str(agent_name or "").strip()
    if normalized == "codex":
        return "Codex"
    if normalized == "claude-code":
        return "Claude Code sidecar" if sidecar else "Claude Code"
    words = [part for part in normalized.replace("_", "-").split("-") if part]
    return " ".join(word[:1].upper() + word[1:] for word in words) or normalized or "Unknown Agent"


def _sort_key(state: dict) -> tuple[int, str]:
    agent = str(state.get("agent") or "").strip()
    priority = {"codex": 0, "claude-code": 1}
    return (priority.get(agent, 10), agent)


def build_agent_rows(root: Path) -> list[dict[str, str]]:
    agent_states = load_agent_states(root)
    state_by_agent = {
        str(state.get("agent") or state.get("_state_file") or "").strip(): state
        for state in agent_states
    }
    claude_state = state_by_agent.get("claude-code", {})
    sidecar_state = read_json(root / SIDECAR_STATUS_PATH)

    rows: list[dict[str, str]] = []

    seen_agents: set[str] = set()
    for state in sorted(agent_states, key=_sort_key):
        agent_name = str(state.get("agent") or "").strip()
        if not agent_name:
            continue
        seen_agents.add(agent_name)

        if agent_name == "claude-code":
            sidecar_task = str(sidecar_state.get("task_id") or "").strip()
            sidecar_phase = str(sidecar_state.get("current_phase") or "").strip()
            if sidecar_task and sidecar_phase:
                scope = f"`{sidecar_task}` / `{sidecar_phase}`"
            elif sidecar_task:
                scope = f"`{sidecar_task}`"
            else:
                scope = _fmt(state.get("current_task"))

            status = sidecar_state.get("status") or state.get("status")
            next_step, next_source = _claude_next_step(sidecar_state, state)
            if sidecar_state and next_source == "`.coordination/claude-code.json`":
                source = "`reports/claude_sidecar/session_status.json` + `.coordination/claude-code.json`"
            elif sidecar_state:
                source = next_source
            else:
                source = f"`.coordination/{agent_name}.json`"

            rows.append(
                {
                    "agent": _display_agent_name(agent_name, sidecar=bool(sidecar_state)),
                    "status": _normalize_status(status),
                    "scope": scope,
                    "next_step": _fmt(next_step),
                    "source": source,
                }
            )
            continue

        rows.append(
            {
                "agent": _display_agent_name(agent_name),
                "status": _normalize_status(state.get("status")),
                "scope": _fmt(state.get("current_task")),
                "next_step": _fmt(state.get("next_step")),
                "source": f"`.coordination/{agent_name}.json`",
            }
        )

    if sidecar_state and "claude-code" not in seen_agents:
        sidecar_task = str(sidecar_state.get("task_id") or "").strip()
        sidecar_phase = str(sidecar_state.get("current_phase") or "").strip()
        scope = f"`{sidecar_task}` / `{sidecar_phase}`" if sidecar_task and sidecar_phase else _fmt(sidecar_task)
        next_step, _ = _claude_next_step(sidecar_state, {})
        rows.append(
            {
                "agent": _display_agent_name("claude-code", sidecar=True),
                "status": _normalize_status(sidecar_state.get("status")),
                "scope": scope,
                "next_step": _fmt(next_step),
                "source": "`reports/claude_sidecar/session_status.json`",
            }
        )

    return rows


def render_agent_snapshot(rows: list[dict[str, str]]) -> str:
    lines = [
        "| Agent | Current Status | Current Scope | Next Exact Step | Source |",
        "|------|----------------|---------------|-----------------|--------|",
    ]
    for row in rows:
        lines.append(
            f"| {row['agent']} | `{row['status']}` | {row['scope']} | {row['next_step']} | {row['source']} |"
        )
    return "\n".join(lines) + "\n"


def sync_agent_snapshot(board_text: str, rows: list[dict[str, str]]) -> str:
    pattern = re.compile(
        rf"({re.escape(SNAPSHOT_START)}\n\n)(.*?)(\n{re.escape(SNAPSHOT_END)})",
        re.DOTALL,
    )
    replacement = r"\1" + render_agent_snapshot(rows) + r"\3"
    updated, count = pattern.subn(replacement, board_text, count=1)
    if count != 1:
        raise ValueError("Could not locate Current Agent Snapshot section in operations board")
    return updated


def update_last_updated(board_text: str, stamp: str) -> str:
    pattern = re.compile(rf"^{re.escape(UPDATED_PREFIX)}.*$", re.MULTILINE)
    updated, count = pattern.subn(f"{UPDATED_PREFIX}{stamp}", board_text, count=1)
    if count != 1:
        raise ValueError("Could not locate last-updated line in operations board")
    return updated


def sync_board(root: Path) -> str:
    board_path = root / BOARD_PATH
    board_text = board_path.read_text(encoding="utf-8")
    rows = build_agent_rows(root)
    board_text = sync_agent_snapshot(board_text, rows)
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    board_text = update_last_updated(board_text, stamp)
    board_path.write_text(board_text, encoding="utf-8")
    sync_lock_registry(root)
    return board_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync docs/OPERATIONS_BOARD.md from coordination state.")
    parser.add_argument("--root", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    sync_board(root)
    print("OK: operations board synced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
