#!/usr/bin/env python3
"""
SESSION END HOOK - Score summary
Summarize session performance and update cumulative score.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
STATE_FILE = STATE_DIR / "session.json"
SCORECARD = PROJECT_DIR / ".claude" / "SCORECARD.md"

if not STATE_FILE.exists():
    sys.exit(0)

# Load state
try:
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
except Exception:
    sys.exit(0)

search_count = state.get("search_count", 0)
error_count = len(state.get("errors", []))
research_done = state.get("research_done", False)
started_without = state.get("started_without_research", False)

date_short = datetime.now().strftime("%Y-%m-%d %H:%M")
summary = "Session: searches=%d, errors=%d, researched_first=%s" % (search_count, error_count, research_done)

# Write session summary to scorecard
if SCORECARD.exists():
    if search_count >= 3 and error_count == 0:
        with open(SCORECARD, "a", encoding="utf-8") as f:
            f.write("| %s | +3 | Thorough research, zero errors | %s |\n" % (date_short, summary))
    elif search_count >= 1 and error_count <= 1:
        with open(SCORECARD, "a", encoding="utf-8") as f:
            f.write("| %s | +1 | Researched with minimal errors | %s |\n" % (date_short, summary))
    elif started_without and error_count >= 2:
        with open(SCORECARD, "a", encoding="utf-8") as f:
            f.write("| %s | -2 | No research, multiple errors | %s |\n" % (date_short, summary))

    # Update cumulative score in header
    try:
        content = SCORECARD.read_text(encoding="utf-8")
        # Find all score entries like "| +2 |" or "| -1 |"
        scores = re.findall(r'\|\s*([+-]\d+)\s*\|', content)
        total = sum(int(s) for s in scores)
        content = re.sub(
            r'^## Cumulative Score: .*$',
            '## Cumulative Score: %d' % total,
            content,
            flags=re.MULTILINE
        )
        SCORECARD.write_text(content, encoding="utf-8")
    except Exception:
        pass

sys.exit(0)
