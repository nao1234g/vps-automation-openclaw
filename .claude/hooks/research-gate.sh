#!/bin/bash
# =============================================================================
# RESEARCH GATE - PreToolUse Hook
# =============================================================================
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
python "$PROJECT_DIR/.claude/hooks/research-gate.py" "$PROJECT_DIR"
