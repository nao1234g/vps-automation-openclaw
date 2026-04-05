#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> int:
    try:
        payload = json.loads(input() or "{}")
    except Exception:
        payload = {}

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    reports_dir = project_dir / "reports" / "claude_sidecar"
    reports_dir.mkdir(parents=True, exist_ok=True)

    context_lines = [
        "NAOTO OS is the founder OS. Nowpattern is a verifiable forecast platform under NAOTO OS.",
        "Read docs/OPERATIONS_BOARD.md first. It is the single human-readable operations board for platform truth, agent coordination, and restart readiness.",
        "If you are doing sidecar work, you must maintain reports/claude_sidecar/session_status.json, heartbeat.json, task_result_v*.json, task_result_v*.md, and resume_prompt.txt.",
        "Do not stop silently. Before stopping, mark the scope completed or blocked with blocking_reason and next_exact_step.",
        "Read CLAUDE.md, .claude/rules/NORTH_STAR.md, scripts/mission_contract.py, scripts/agent_bootstrap_context.py, and the latest reports before acting.",
        "The chat UI is not the source of truth. File outputs are the source of truth.",
    ]

    # Detect interrupted sidecar session and inject resume context
    session_file = reports_dir / "session_status.json"
    resume_file = reports_dir / "resume_prompt.txt"
    if session_file.exists():
        try:
            ss = json.loads(session_file.read_text(encoding="utf-8"))
            status = ss.get("status", "")
            task_id = ss.get("task_id", "")
            scope_pct = ss.get("scope_completion_pct", 0)
            blocking = ss.get("blocking_reason", "")
            next_step = ss.get("next_exact_step", "")
            reached = ss.get("reached_100_pct_for_this_scope", False)

            if status == "in_progress":
                context_lines.append(
                    f"RESUME DETECTED: Prior sidecar session '{task_id}' was interrupted at {scope_pct}% scope. "
                    f"Status=in_progress. You MUST either resume this scope or mark it blocked with blocking_reason before starting new work."
                )
                if next_step:
                    context_lines.append(f"Last next_exact_step: {next_step}")
                if resume_file.exists():
                    context_lines.append("Read reports/claude_sidecar/resume_prompt.txt for full resume context.")
            elif status == "blocked" and blocking:
                context_lines.append(
                    f"BLOCKED SESSION: Prior sidecar session '{task_id}' is blocked. Reason: {blocking}. "
                    f"Next step: {next_step or 'unspecified'}. Resume or escalate."
                )
            elif status == "completed" and reached:
                context_lines.append(
                    f"Prior sidecar scope '{task_id}' completed (100%). Ready for new scope."
                )
                if resume_file.exists():
                    context_lines.append("Read reports/claude_sidecar/resume_prompt.txt for suggested next scopes.")
        except Exception:
            pass  # Malformed session_status.json — proceed without resume context

    source = str(payload.get("source") or "startup")
    context_lines.append(f"Session source: {source}. Prefer resume-safe work and keep progress machine-readable.")

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": "\n".join(context_lines),
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
