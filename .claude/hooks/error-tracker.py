#!/usr/bin/env python3
"""
ERROR TRACKER - PostToolUseFailure Hook
When a tool fails:
1. Log to errors.log
2. AUTO-WRITE draft entry to KNOWN_MISTAKES.md (no more "remember to...")
3. Update scorecard
4. Detect repeated known mistakes
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
    error_short = error[:200]
else:
    error_short = str(error)[:200]

# ── ノイズフィルター: 権限ブロック・空エラーはスキップ ──
if not tool_name:
    sys.exit(0)  # ツール名が空 = hookシステム自体の問題
NOISE_SIGNALS = [
    "permission denied", "not allowed", "blocked by settings",
    "tool_use_error", "unknown error"
]
if any(sig in error_short.lower() for sig in NOISE_SIGNALS) and len(error_short) < 50:
    sys.exit(0)  # 権限ブロック系は実際のミスではない

date_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
date_short = datetime.now().strftime("%Y-%m-%d %H:%M")
date_header = datetime.now().strftime("%Y-%m-%d")

# 1. Log the error
with open(ERROR_LOG, "a", encoding="utf-8") as f:
    f.write("[%s] %s FAILED: %s\n" % (date_full, tool_name, error_short))

# 2. Update state
if STATE_FILE.exists():
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        state = {"research_done": False, "search_count": 0, "errors": [], "task_started": False}
    if "errors" not in state:
        state["errors"] = []
    state["errors"].append({"tool": tool_name, "error": error_short})
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")

# 3. Check for repeated known mistake
is_repeated = False
if MISTAKES_FILE.exists():
    import re
    keywords = re.findall(r'[A-Za-z_]+Error|EBUSY|CAPTCHA|pairing|401|403|timeout|SSL|404|lexical', error_short[:100], re.IGNORECASE)
    if keywords:
        match_keyword = keywords[0]
        mistakes_content = MISTAKES_FILE.read_text(encoding="utf-8")
        if match_keyword.lower() in mistakes_content.lower():
            is_repeated = True
            print("⚠️  REPEATED MISTAKE: '%s' is already in KNOWN_MISTAKES.md!" % match_keyword)
            print("Score: -3 (repeated known mistake)")
            if SCORECARD.exists():
                with open(SCORECARD, "a", encoding="utf-8") as f:
                    f.write("| %s | -3 | Repeated known mistake: %s | %s |\n" % (date_short, match_keyword, tool_name))

# 4. AUTO-WRITE draft to KNOWN_MISTAKES.md (regardless of whether repeated)
# Only for significant errors (not trivial ones)
trivial_errors = ["unknown error", "cancelled", "timeout reading", "permission denied to"]
is_trivial = any(t in error_short.lower() for t in trivial_errors) and len(error_short) < 30

if not is_trivial and MISTAKES_FILE.exists():
    draft_marker = f"AUTO-DRAFT-{date_header}-{tool_name}"
    existing = MISTAKES_FILE.read_text(encoding="utf-8")
    if draft_marker not in existing:
        draft = f"""
### {date_header} AUTO-DRAFT: {tool_name} エラー ← Claudeが詳細を記入すること
- **症状**: ツール `{tool_name}` が失敗した
- **エラー内容**: `{error_short[:150]}`
- **根本原因**: TODO — Claudeが記入すること
- **誤ったアプローチ**: TODO — 何を試して失敗したか
- **正しい解決策**: TODO — どう解決したか
- **教訓**: TODO — 次回どうすべきか
<!-- {draft_marker} -->
"""
        with open(MISTAKES_FILE, "a", encoding="utf-8") as f:
            f.write(draft)
        print("📝 AUTO-RECORDED draft in KNOWN_MISTAKES.md — please fill in root cause and solution.")

# 5. Regular score penalty
if not is_repeated:
    print("Tool failed: %s | Error: %s" % (tool_name, error_short[:80]))
    if SCORECARD.exists():
        with open(SCORECARD, "a", encoding="utf-8") as f:
            f.write("| %s | -1 | Error: %s | %s |\n" % (date_short, tool_name, error_short[:40]))

sys.exit(0)
