#!/usr/bin/env python3
"""
coordination-pretool.py — local-claude PreToolUse coordination hook.

Fires on Edit/Write tool calls.
- Updates agent status to 'working' in coordination.db (background, non-blocking)
- Reads local session task state to track activity
- Never blocks the tool execution (exit 0 always)
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

STATE_DIR = Path(__file__).parent / 'state'
COORD_STATE = STATE_DIR / 'coord_session_task.json'
VPS = 'root@163.44.124.123'


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

    # Update agent status to 'working' + heartbeat (fire and forget)
    py = (
        'import sqlite3,time; '
        'db=sqlite3.connect("/opt/shared/coordination/coordination.db",timeout=5); '
        'db.execute("PRAGMA journal_mode=WAL"); '
        'db.execute("UPDATE agents SET current_status=\\'working\\', '
        'last_heartbeat_at=? WHERE agent_id=\\'local-claude\\'", (time.time(),)); '
        'db.commit(); db.close()'
    )
    _bg_ssh(py)

    # Track file in local state for session-end evidence
    state = _read_coord_state()
    task_id = state.get('task_id', '')

    # Phase 2 enforcement: log violation if editing without a session task
    # Rate-limited: only fire once per session (flag in state file)
    if (not task_id or task_id == 'FAILED') and not state.get('violation_logged'):
        py_v = (
            'import sqlite3,time,uuid; '
            'db=sqlite3.connect("/opt/shared/coordination/coordination.db",timeout=5); '
            'db.execute("PRAGMA journal_mode=WAL"); '
            'db.execute("INSERT INTO protocol_violations '
            '(violation_id,detected_at,violation_type,actor,entity_type,entity_id,'
            'description,what_was_wrong,why_it_breaks,corrective_action,resolved) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?)",'
            '(str(uuid.uuid4()),time.time(),"NO_SESSION_TASK_BEFORE_EDIT","local-claude",'
            '"agent","local-claude",'
            '"Edit/Write fired without active coordination session task",'
            '"Agent editing files without registered coordination task",'
            '"File edits are untracked in coordination DB",'
            '"Ensure session-start.sh has VPS connectivity so CoordWorkflow.start() registers",0));'
            'db.commit();db.close()'
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
