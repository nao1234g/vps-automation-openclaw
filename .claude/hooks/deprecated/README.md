# Deprecated Hooks

These hooks have been removed from `.claude/settings.local.json` and are no longer active.
They are preserved here for reference only.

| File | Reason | Archived |
|------|--------|---------|
| `debug-hook.py` | No references in settings or any .sh wrapper | 2026-03-26 |
| `intent-confirm.py` | Removed from PreToolUse chain (task_ledger confirms dead code) | 2026-03-26 |
| `pvqe-p-gate.py` | Removed from PreToolUse chain (task_ledger confirms dead code) | 2026-03-26 |

**DO NOT re-add these to settings.local.json without a plan review.**
The PVQE-P evidence enforcement is now handled by `pvqe-p-stop.py` (Stop hook only).
