#!/usr/bin/env python3
"""
ERROR TRACKER - PostToolUseFailure Hook
When a tool fails: log the error, increment penalty, check for repeated known mistakes.
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
ERROR_LOG = STATE_DIR / "errors.log"
MISTAKES_FILE = PROJECT_DIR / "docs" / "KNOWN_MISTAKES.md"

STATE_DIR.mkdir(parents=True, exist_ok=True)

# Read stdin
try:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}

tool_name = data.get("tool_name", "")
error = data.get("tool_output", data.get("tool_error", "unknown error"))
if isinstance(error, str):
    error = error[:200]
else:
    error = str(error)[:200]

# Log the error
date_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
date_short = datetime.now().strftime("%Y-%m-%d %H:%M")

with open(ERROR_LOG, "a", encoding="utf-8") as f:
    f.write("[%s] %s FAILED: %s\n" % (date_full, tool_name, error))

# Update state
if STATE_FILE.exists():
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        state = {"research_done": False, "search_count": 0, "errors": [], "task_started": False}

    if "errors" not in state:
        state["errors"] = []
    state["errors"].append({"tool": tool_name, "error": error})
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")

# Check if this error matches a known mistake
if MISTAKES_FILE.exists():
    import re
    # Extract keywords from error
    keywords = re.findall(r'[A-Za-z_]+Error|EBUSY|CAPTCHA|pairing|401|403|timeout', error[:100], re.IGNORECASE)
    if keywords:
        match_keyword = keywords[0]
        mistakes_content = MISTAKES_FILE.read_text(encoding="utf-8")
        if match_keyword.lower() in mistakes_content.lower():
            print("REPEATED MISTAKE DETECTED: '%s' is already in KNOWN_MISTAKES.md!" % match_keyword)
            print("You should have checked KNOWN_MISTAKES.md before starting.")
            print("Penalty: -3 points (repeated known mistake)")

            if SCORECARD.exists():
                with open(SCORECARD, "a", encoding="utf-8") as f:
                    f.write("| %s | -3 | REPEATED: %s | %s |\n" % (date_short, match_keyword, tool_name))
            sys.exit(0)

# Regular error penalty
print("Tool failed: %s. Remember to record this in KNOWN_MISTAKES.md if it takes >5 min to resolve." % tool_name)
if SCORECARD.exists():
    with open(SCORECARD, "a", encoding="utf-8") as f:
        f.write("| %s | -1 | Error: %s | %s |\n" % (date_short, tool_name, error[:40]))

sys.exit(0)
