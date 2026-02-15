#!/bin/bash
# =============================================================================
# RESEARCH REWARD - PostToolUse Hook (Python wrapper)
# =============================================================================
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
python3 "$PROJECT_DIR/.claude/hooks/research-reward.py" "$PROJECT_DIR" 2>/dev/null || python "$PROJECT_DIR/.claude/hooks/research-reward.py" "$PROJECT_DIR"
