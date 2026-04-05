#!/usr/bin/env python3
"""
coordination-pretool.py — local-claude PreToolUse coordination hook.

Fires on Edit/Write tool calls.
- Checks .coordination/*.json for LOCAL agent conflicts (exit 2 if conflict)
- Updates agent status to 'working' in coordination.db (background, non-blocking)
- Reads local session task state to track activity

v2 (2026-04-05): Added .coordination/ file-based conflict detection.
  Codex writes .coordination/codex.json with locked_files/vps_resources.
  If target file matches another agent's locks → exit 2 BLOCK.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from coordination_utils import find_conflict, resolve_self_agent_name  # noqa: E402

STATE_DIR = Path(__file__).parent / 'state'
COORD_STATE = STATE_DIR / 'coord_session_task.json'
VPS = 'root@163.44.124.123'
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _read_coord_state() -> dict:
    if COORD_STATE.exists():
        try:
            return json.loads(COORD_STATE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}


def _bg_ssh(py_oneliner: str) -> None:
    """Fire SSH command in background (non-blocking)."""
    subprocess.Popen(
        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=3',
         '-o', 'StrictHostKeyChecking=no', VPS,
         f'python3 -c \'{py_oneliner}\''],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    tool_name = data.get('tool_name', '')
    if tool_name not in ('Edit', 'Write'):
        sys.exit(0)

    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    # ── LOCAL CONFLICT CHECK (.coordination/*.json) ──────────────
    # .coordination/ 自体の編集はデッドロック防止で常に許可
    from coordination_utils import normalize_repo_relative_path  # local import to keep hook startup light

    norm_path = normalize_repo_relative_path(file_path, REPO_ROOT)
    if '.coordination/' not in norm_path:
        self_agent = resolve_self_agent_name("claude-code")
        conflict = find_conflict(file_path, root=REPO_ROOT, self_agent=self_agent)
        if conflict:
            agent_name = conflict.get('agent', 'unknown')
            task = str(conflict.get('current_task') or '不明')[:60]
            locked = conflict.get('path', '')
            print(
                '\n'
                '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
                f'⚠️  [COORDINATION] ファイル競合検出！\n'
                '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
                f'  編集対象: {file_path}\n'
                f'  競合エージェント: {agent_name}\n'
                f'  相手のタスク: {task}\n'
                f'  ロック中: {locked}\n'
                '\n'
                '  → 相手のタスク完了を待つか、.coordination/ で調整してください。\n'
                '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            )
            sys.exit(2)

    # Update agent status to 'working' + heartbeat (fire and forget)
    py = (
        "import sqlite3,time; "
        "db=sqlite3.connect('/opt/shared/coordination/coordination.db',timeout=5); "
        "db.execute('PRAGMA journal_mode=WAL'); "
        "db.execute(\"UPDATE agents SET current_status='working', "
        "last_heartbeat_at=? WHERE agent_id='local-claude'\", (time.time(),)); "
        "db.commit(); db.close()"
    )
    _bg_ssh(py)

    # Track file in local state for session-end evidence
    state = _read_coord_state()
    task_id = state.get('task_id', '')

    # Phase 2 enforcement: log violation if editing without a session task
    # Rate-limited: only fire once per session (flag in state file)
    if (not task_id or task_id == 'FAILED') and not state.get('violation_logged'):
        py_v = (
            "import sqlite3,time,uuid; "
            "db=sqlite3.connect('/opt/shared/coordination/coordination.db',timeout=5); "
            "db.execute('PRAGMA journal_mode=WAL'); "
            "db.execute(\"INSERT INTO protocol_violations "
            "(violation_id,detected_at,violation_type,actor,entity_type,entity_id,"
            "description,what_was_wrong,why_it_breaks,corrective_action,resolved) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)\","
            "(str(uuid.uuid4()),time.time(),'NO_SESSION_TASK_BEFORE_EDIT','local-claude',"
            "'agent','local-claude',"
            "'Edit/Write fired without active coordination session task',"
            "'Agent editing files without registered coordination task',"
            "'File edits are untracked in coordination DB',"
            "'Ensure session-start.sh has VPS connectivity so CoordWorkflow.start() registers',0));"
            "db.commit();db.close()"
        )
        _bg_ssh(py_v)
        state['violation_logged'] = True

    files = state.get('files_edited', [])
    if file_path and file_path not in files:
        files.append(file_path)
    state['files_edited'] = files[-50:]  # keep last 50
    state['last_edit_ts'] = time.time()
    try:
        COORD_STATE.write_text(json.dumps(state, indent=2), encoding='utf-8')
    except Exception:
        pass

    sys.exit(0)


if __name__ == '__main__':
    main()
