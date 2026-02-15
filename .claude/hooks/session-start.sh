#!/bin/bash
# =============================================================================
# SESSION START HOOK
# =============================================================================
# Every session start: force-read KNOWN_MISTAKES.md + show SCORECARD
# This ensures Claude NEVER starts without context of past failures.
# =============================================================================

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
MISTAKES_FILE="$PROJECT_DIR/docs/KNOWN_MISTAKES.md"
SCORECARD_FILE="$PROJECT_DIR/.claude/SCORECARD.md"
STATE_DIR="$PROJECT_DIR/.claude/hooks/state"

mkdir -p "$STATE_DIR"

# Reset session state
cat > "$STATE_DIR/session.json" << 'STATEJSON'
{"research_done":false,"search_count":0,"errors":[],"task_started":false}
STATEJSON

# Output context for Claude to read
echo "=== SESSION START: MANDATORY CONTEXT ==="
echo ""

# 1. Show scorecard (reward/penalty history)
if [ -f "$SCORECARD_FILE" ]; then
    echo "--- YOUR PERFORMANCE SCORECARD ---"
    cat "$SCORECARD_FILE"
    echo ""
fi

# 2. Show recent mistakes summary (last 5)
if [ -f "$MISTAKES_FILE" ]; then
    echo "--- RECENT MISTAKES (DO NOT REPEAT) ---"
    # Extract last 5 mistake headers with their lessons
    grep -A 2 "^### " "$MISTAKES_FILE" | tail -25
    echo ""
fi

echo "--- RULES ---"
echo "1. RESEARCH FIRST: WebSearch/WebFetch BEFORE any implementation"
echo "2. CHECK KNOWN_MISTAKES.md BEFORE starting any new task"
echo "3. After errors: RECORD in KNOWN_MISTAKES.md immediately"
echo "4. Your score is tracked. Research = +points. Repeated mistakes = -points."
echo "=== END MANDATORY CONTEXT ==="
