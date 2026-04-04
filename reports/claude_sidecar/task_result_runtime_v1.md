# Task Result: Claude Code Runtime Layer Stability (runtime_v1)

Generated: 2026-04-04
Task ID: sidecar-20260404-runtime-layer-v1
Status: **COMPLETED**

---

## What Was Wrong

### Hook Inventory (31 hooks across 2 config files)

| Config File | Hook Count | Event Types |
|---|---|---|
| settings.json (repo) | 4 entries | SessionStart, Stop, SubagentStop, SessionEnd |
| settings.local.json (user) | 27 entries | UserPromptSubmit x3, PreToolUse x10, PostToolUse x8, PostToolUseFailure x2, SessionEnd x1, Stop x2 |

### Root Causes for "Stops After ~10 Minutes"

1. **RC-1: No mid-session sidecar save** — If Claude crashes or compacts context, session_status.json stays at 0% with stale next_exact_step
2. **RC-2: Stop gate blind to "interrupted"** — Only knew "in_progress" and "completed"; no concept of unplanned exit
3. **RC-3: SessionStart has no resume detection** — New session starts blind, doesn't know prior session was interrupted
4. **RC-4: session-start.sh is heavy** (5-6 SSH calls) — Slow startup, not the root cause of silent stop
5. **RC-5: 13-14 hooks per Edit/Write** — Adds latency per tool call, not the root cause of silent stop

---

## What Was Changed (3 Patches)

### P1: Enhanced sidecar_session_start.py
- **File**: `.claude/hooks/sidecar_session_start.py`
- **Change**: Added ~30 lines to detect prior session state from `session_status.json`
- **Behavior**: On session start, reads session_status.json:
  - `in_progress` → Injects "RESUME DETECTED" warning, forces agent to resume or mark blocked
  - `blocked` → Injects "BLOCKED SESSION" notice with blocking_reason
  - `completed` → Injects completion notice, suggests reading resume_prompt.txt for next scope
- **Fixes**: RC-3

### P2: Created sidecar_session_end.py
- **File**: `.claude/hooks/sidecar_session_end.py` (NEW, 75 lines)
- **Change**: Auto-detects if session_status.json says "in_progress" at session end
- **Behavior**: If status is "in_progress" (meaning agent didn't properly close):
  - Sets status to "interrupted"
  - Writes blocking_reason: "Session ended while scope was in_progress"
  - Preserves next_exact_step from prior state
  - Updates heartbeat.json with interrupted status
- **Fixes**: RC-1, RC-2

### P3: Updated settings.json
- **File**: `.claude/settings.json`
- **Changes**:
  - Registered P2 as `SessionEnd` command hook (powershell, 10s timeout)
  - Updated Stop gate prompt to recognize "interrupted" as valid stop state
  - Updated SubagentStop prompt to use "in_progress" wording consistently
- **Fixes**: RC-2

---

## Sidecar Lifecycle (After Patch)

```
Normal:     in_progress → completed
Planned:    in_progress → blocked (with blocking_reason + next_exact_step)
Unplanned:  in_progress → interrupted (SessionEnd hook auto-fires)
Resume:     Next SessionStart detects interrupted/blocked → injects resume context
```

---

## What Remains Imperfect

1. **Hook overhead not reduced** — 13-14 hooks per Edit/Write still fire. Not causing the 10-minute stop, but adds latency.
2. **session-start.sh still heavy** — 5-6 SSH calls on startup. Causes slow session start, not silent stop.
3. **No mid-session heartbeat** — Would require a UserPromptSubmit hook, adds overhead. Deferred.
4. **Context compaction still loses conversation history** — This is a Claude Code platform limitation, not fixable from hooks.

---

## Files Modified

| File | Action |
|---|---|
| `.claude/hooks/sidecar_session_start.py` | Enhanced (resume detection) |
| `.claude/hooks/sidecar_session_end.py` | Created (auto-interrupt marking) |
| `.claude/settings.json` | Updated (SessionEnd hook + stop gate prompts) |
| `reports/claude_sidecar/session_status.json` | Updated (scope progress) |
| `reports/claude_sidecar/heartbeat.json` | Updated (phase progress) |
| `reports/claude_sidecar/task_result_runtime_v1.json` | Created (machine-readable) |
| `reports/claude_sidecar/task_result_runtime_v1.md` | Created (human-readable) |
| `reports/claude_sidecar/resume_prompt.txt` | Updated (handoff for next session) |
