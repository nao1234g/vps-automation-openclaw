#!/usr/bin/env python3
"""
sidecar_session_end.py — SessionEnd Hook: Auto-save sidecar state on exit.

If a sidecar session is in_progress when the session ends (crash, compaction,
user exit), this hook marks it as "interrupted" with enough metadata for the
next session to resume cleanly.

This is the fix for the "stops after ~10 minutes with no resume state" gap.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    reports_dir = project_dir / "reports" / "claude_sidecar"
    session_file = reports_dir / "session_status.json"
    heartbeat_file = reports_dir / "heartbeat.json"

    if not session_file.exists():
        return 0

    try:
        ss = json.loads(session_file.read_text(encoding="utf-8"))
    except Exception:
        return 0

    status = ss.get("status", "")

    # Only act if session is still in_progress (meaning it wasn't properly closed)
    if status != "in_progress":
        return 0

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    task_id = ss.get("task_id", "unknown")
    scope_pct = ss.get("scope_completion_pct", 0)
    phase = ss.get("current_phase", "unknown")

    # Mark as interrupted (not blocked — interrupted means unplanned exit)
    ss["status"] = "interrupted"
    ss["blocking_reason"] = "Session ended while scope was in_progress (unplanned exit or context compaction)"
    ss["next_exact_step"] = ss.get("next_exact_step", "") or "Resume from current phase"
    ss["interrupted_at"] = now
    ss["interrupted_scope_pct"] = scope_pct

    try:
        session_file.write_text(
            json.dumps(ss, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        return 0

    # Also update heartbeat
    try:
        hb = {
            "generated_at": now,
            "phase": phase,
            "phase_status": "interrupted",
            "progress_note": f"Session ended unexpectedly at {scope_pct}% scope. Task: {task_id}.",
            "next_step": "Next session should read resume_prompt.txt and continue.",
        }
        heartbeat_file.write_text(
            json.dumps(hb, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    print(f"[sidecar] Session '{task_id}' marked as interrupted at {scope_pct}% scope.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
