#!/bin/bash
# =============================================================================
# RESEARCH GATE - PreToolUse Hook
# =============================================================================
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
python3 "$PROJECT_DIR/.claude/hooks/research-gate.py" "$PROJECT_DIR" 2>/dev/null || python "$PROJECT_DIR/.claude/hooks/research-gate.py" "$PROJECT_DIR"
