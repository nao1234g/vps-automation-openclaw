#!/bin/bash
# =============================================================================
# SESSION END HOOK - Score summary (Python wrapper)
# =============================================================================
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
python3 "$PROJECT_DIR/.claude/hooks/session-end.py" "$PROJECT_DIR" 2>/dev/null || python "$PROJECT_DIR/.claude/hooks/session-end.py" "$PROJECT_DIR"
