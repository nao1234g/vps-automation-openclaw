#!/usr/bin/env python3
"""
RESEARCH GATE - PreToolUse Hook
Tracks research activity and warns when editing without research.
"""
import json
import sys
import os
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
STATE_FILE = STATE_DIR / "session.json"
SCORECARD = PROJECT_DIR / ".claude" / "SCORECARD.md"

STATE_DIR.mkdir(parents=True, exist_ok=True)

# Read stdin
try:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}

tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})

# Load state
state = {"research_done": False, "search_count": 0, "errors": [], "task_started": False}
if STATE_FILE.exists():
    try:
        state = json.loads(STATE_FILE.read_text())
    except Exception:
        pass

# Track research
if tool_name in ("WebSearch", "WebFetch"):
    state["research_done"] = True
    state["search_count"] = state.get("search_count", 0) + 1
    STATE_FILE.write_text(json.dumps(state))
    sys.exit(0)

# Track KNOWN_MISTAKES reading
if tool_name == "Read":
    file_path = tool_input.get("file_path", "")
    if "KNOWN_MISTAKES" in file_path.upper():
        state["mistakes_checked"] = True
        STATE_FILE.write_text(json.dumps(state))
    sys.exit(0)

# Check research before Edit/Write
if tool_name in ("Edit", "Write"):
    if not state.get("research_done") and state.get("search_count", 0) == 0:
        state["task_started"] = True
        state["started_without_research"] = True
        STATE_FILE.write_text(json.dumps(state))

        # Warning output
        print("WARNING: Editing files WITHOUT prior research.")
        print("Did you check KNOWN_MISTAKES.md? Did you WebSearch for solutions?")
        print("Penalty: -1 point recorded.")

        # Record penalty
        if SCORECARD.exists():
            date = datetime.now().strftime("%Y-%m-%d %H:%M")
            fp = tool_input.get("file_path", "unknown")[:40]
            with open(SCORECARD, "a") as f:
                f.write("| %s | -1 | Edited without research | %s |\n" % (date, fp))
    else:
        state["task_started"] = True
        STATE_FILE.write_text(json.dumps(state))

sys.exit(0)
