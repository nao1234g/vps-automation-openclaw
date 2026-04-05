#!/usr/bin/env python3
"""
COORDINATION SESSION SYNC — PostToolUse Hook (Read)
====================================================
セッション中に .coordination/*.json を読んだ際、自分の状態を自動更新する。
また、session-start.sh から呼ばれて、他エージェントの状態を表示する。

Usage (standalone):
  python .claude/hooks/coordination-session-sync.py --show
  python .claude/hooks/coordination-session-sync.py --update-self "task description"
  python .claude/hooks/coordination-session-sync.py --lock "file1.py,file2.py"
  python .claude/hooks/coordination-session-sync.py --unlock
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from coordination_utils import (  # noqa: E402
    active_lock_entries,
    is_state_stale,
    load_agent_states,
    now_iso,
    resolve_self_agent_name,
    update_agent_state,
)
import update_operations_board as operations_board  # noqa: E402

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
COORD_DIR = PROJECT_DIR / ".coordination"
SELF_AGENT = resolve_self_agent_name("claude-code")


def sync_outputs() -> None:
    operations_board.sync_board(PROJECT_DIR.resolve())


def show_coordination_status():
    """全エージェントの状態を表示"""
    if not COORD_DIR.exists():
        print("  [COORD] .coordination/ not found")
        return

    agent_states = load_agent_states(PROJECT_DIR.resolve())

    if not agent_states:
        print("  [COORD] No agent state files found")
        return

    print("  ┌─── Agent Coordination Status ───┐")
    for state in sorted(agent_states, key=lambda row: str(row.get("agent", ""))):
        name = state.get("agent", state.get("_state_file", "?"))
        status = state.get("status", "unknown")
        task = state.get("current_task", "")[:60]
        locked = state.get("locked_files", [])
        vps = state.get("vps_resources", [])
        stale = is_state_stale(state, PROJECT_DIR.resolve())

        icon = "💀" if stale else ("🟢" if status == "active" else "⚪")
        stale_mark = " (stale)" if stale else ""
        print(f"  │ {icon} {name:<14} {status}{stale_mark}")
        if task:
            print(f"  │   Task: {task}")
        if locked:
            print(f"  │   Locked: {', '.join(locked)}")
        if vps:
            print(f"  │   VPS: {', '.join(vps)}")
    print("  └──────────────────────────────────┘")


def update_self(task: str, locked: list = None, vps: list = None):
    """自分の状態を更新"""
    update_agent_state(
        agent_name=SELF_AGENT,
        status="active" if task else "idle",
        current_task=task,
        locked_files=locked or [],
        vps_resources=vps or [],
        root=PROJECT_DIR.resolve(),
    )
    sync_outputs()


def mark_idle():
    """セッション終了時にidle化"""
    update_agent_state(
        agent_name=SELF_AGENT,
        status="idle",
        current_task="",
        next_step="",
        locked_files=[],
        vps_resources=[],
        root=PROJECT_DIR.resolve(),
    )
    sync_outputs()


if __name__ == "__main__":
    if "--show" in sys.argv:
        show_coordination_status()
    elif "--update-self" in sys.argv:
        idx = sys.argv.index("--update-self")
        task = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        update_self(task)
        print(f"  [COORD] Self updated: {task[:50]}")
    elif "--heartbeat" in sys.argv:
        state = update_agent_state(
            agent_name=SELF_AGENT,
            root=PROJECT_DIR.resolve(),
        )
        sync_outputs()
        print(f"  [COORD] Heartbeat: {state.get('updated_at', now_iso())}")
    elif "--lock" in sys.argv:
        idx = sys.argv.index("--lock")
        files = sys.argv[idx + 1].split(",") if idx + 1 < len(sys.argv) else []
        update_agent_state(
            agent_name=SELF_AGENT,
            status="active",
            locked_files=files,
            root=PROJECT_DIR.resolve(),
        )
        sync_outputs()
        print(f"  [COORD] Locked: {files}")
    elif "--unlock" in sys.argv:
        update_agent_state(
            agent_name=SELF_AGENT,
            locked_files=[],
            root=PROJECT_DIR.resolve(),
        )
        sync_outputs()
        print("  [COORD] All locks released")
    elif "--idle" in sys.argv:
        mark_idle()
        print("  [COORD] Marked idle")
    else:
        # Hook mode (stdin)
        try:
            raw = sys.stdin.read().strip()
            data = json.loads(raw) if raw else {}
        except Exception:
            sys.exit(0)
        # No-op in hook mode for now (precheck handles blocking)
        sys.exit(0)
