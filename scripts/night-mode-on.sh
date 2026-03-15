#!/bin/bash
# =============================================================================
# NIGHT MODE ON — Claude Code自律運転を有効化する
# =============================================================================
# 使い方: bash scripts/night-mode-on.sh
# 解除:   bash scripts/night-mode-off.sh
#
# 効果:
#   - flash-cards-inject.sh が毎ターン AUTONOMOUS MODE 指示を注入
#   - pvqe-p-gate.py の証拠計画要件をバイパス
#   - Claude は AskUserQuestion / EnterPlanMode を使わず自律実行
# =============================================================================

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE_DIR="$PROJECT_DIR/.claude/hooks/state"

mkdir -p "$STATE_DIR"

# Night Mode フラグを作成
touch "$STATE_DIR/night_mode.flag"

# 邪魔になる可能性のあるフラグをクリア
rm -f "$STATE_DIR/intent_confirmed.flag"
rm -f "$STATE_DIR/intent_needs_confirmation.flag"
rm -f "$STATE_DIR/pvqe_p.json"

echo "🌙 NIGHT MODE ON — 自律運転を開始します"
echo "  Claude Code は確認を求めず自律実行します。"
echo "  解除: bash scripts/night-mode-off.sh"
echo "  フラグ: $STATE_DIR/night_mode.flag"
