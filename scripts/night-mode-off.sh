#!/bin/bash
# =============================================================================
# NIGHT MODE OFF — Claude Code自律運転を解除する
# =============================================================================
# 使い方: bash scripts/night-mode-off.sh
# =============================================================================

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE_DIR="$PROJECT_DIR/.claude/hooks/state"

if [ -f "$STATE_DIR/night_mode.flag" ]; then
    rm -f "$STATE_DIR/night_mode.flag"
    echo "☀️ NIGHT MODE OFF — 通常モードに戻りました"
    echo "  Claude Code は確認フローを再び使います。"
else
    echo "  Night Mode は既にOFFです。"
fi
