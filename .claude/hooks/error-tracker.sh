#!/bin/bash
# =============================================================================
# ERROR TRACKER - PostToolUseFailure Hook (Python wrapper)
# =============================================================================
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
python "$PROJECT_DIR/.claude/hooks/error-tracker.py" "$PROJECT_DIR"
