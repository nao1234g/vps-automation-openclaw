#!/bin/bash
# =============================================================================
# ERROR TRACKER - PostToolUseFailure Hook (Python wrapper)
# =============================================================================
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
python3 "$PROJECT_DIR/.claude/hooks/error-tracker.py" "$PROJECT_DIR" 2>/dev/null || python "$PROJECT_DIR/.claude/hooks/error-tracker.py" "$PROJECT_DIR"
