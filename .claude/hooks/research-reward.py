#!/usr/bin/env python3
"""
RESEARCH REWARD - PostToolUse Hook for WebSearch/WebFetch
When research is done BEFORE implementation: +2 reward
"""
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
STATE_FILE = STATE_DIR / "session.json"
SCORECARD = PROJECT_DIR / ".claude" / "SCORECARD.md"

STATE_DIR.mkdir(parents=True, exist_ok=True)

# Atomic write utility
try:
    sys.path.insert(0, str(PROJECT_DIR / ".claude" / "hooks"))
    from _state_utils import safe_read_json, safe_write_json
except ImportError:
    def safe_read_json(path, default=None):
        try:
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else (default or {})
        except Exception:
            return default or {}
    def safe_write_json(path, data, indent=None):
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

# Read stdin
try:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}

tool_name = data.get("tool_name", "")

# Only track WebSearch and WebFetch
if tool_name not in ("WebSearch", "WebFetch"):
    sys.exit(0)

# Update research state
state = safe_read_json(STATE_FILE, default={"research_done": False, "search_count": 0, "errors": [], "task_started": False})
task_started = state.get("task_started", False)
already_rewarded = state.get("research_rewarded", False)

# Reward if research happens BEFORE task started (before any Edit/Write)
if not task_started and not already_rewarded:
    state["research_done"] = True
    state["search_count"] = state.get("search_count", 0) + 1
    state["research_rewarded"] = True
    safe_write_json(STATE_FILE, state)

    date_short = datetime.now().strftime("%Y-%m-%d %H:%M")
    if SCORECARD.exists():
        with open(SCORECARD, "a", encoding="utf-8") as f:
            f.write("| %s | +2 | Research before implementation | %s |\n" % (date_short, tool_name))
    print("Good: Research done before implementation. +2 points.")
else:
    # Research after starting is still tracked but less rewarded
    state["research_done"] = True
    state["search_count"] = state.get("search_count", 0) + 1
    safe_write_json(STATE_FILE, state)

sys.exit(0)
