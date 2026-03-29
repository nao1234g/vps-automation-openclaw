#!/bin/bash
# =============================================================================
# SESSION END HOOK - Score summary (Python wrapper)
# =============================================================================
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
python "$PROJECT_DIR/.claude/hooks/session-end.py" "$PROJECT_DIR"
