#!/bin/bash
# =============================================================================
# RESEARCH REWARD - PostToolUse Hook (Python wrapper)
# =============================================================================
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
python "$PROJECT_DIR/.claude/hooks/research-reward.py" "$PROJECT_DIR"
