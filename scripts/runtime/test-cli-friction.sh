#!/usr/bin/env bash
# =============================================================================
# scripts/runtime/test-cli-friction.sh
# T019 実測スクリプト: CLI 環境でのフリクション計測
#
# 用途: CLI モード（claude / claude --dangerously-skip-permissions）での
#       フリクション（確認要求/hookブロック）状態を診断する
#
# 使い方:
#   bash scripts/runtime/test-cli-friction.sh
#   bash scripts/runtime/test-cli-friction.sh --mode dangerously
#     # --dangerously-skip-permissions での違いを確認
#
# VS Code版との違い:
#   VS Code → settings.local.json の defaultMode が効く
#   CLI     → --dangerously-skip-permissions フラグが使える（deny listも無効化）
# =============================================================================

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="$REPO_ROOT/.claude/hooks/state"
HOOKS_DIR="$REPO_ROOT/.claude/hooks"
LOCAL_SETTINGS="$REPO_ROOT/.claude/settings.local.json"
SHARED_SETTINGS="$REPO_ROOT/.claude/settings.json"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

# --mode dangerously オプション
DANGEROUSLY_MODE=false
if [[ "$1" == "--mode" && "$2" == "dangerously" ]]; then
    DANGEROUSLY_MODE=true
fi

echo -e "${CYAN}=== T019 CLI: フリクション計測スクリプト ===${RESET}"
echo ""
echo "【CLIモードの特徴】"
echo "  通常起動: claude  → settings.local.json の defaultMode が適用"
echo "  自律起動: claude --dangerously-skip-permissions"
echo "           → UIダイアログ完全なし + deny listも無効化（VSCodeより強力）"
echo "  Lane B CLI: bash scripts/runtime/lane-b-autonomous.sh"
echo "           → Night Mode ONにしてから --dangerously-skip-permissions を起動"
echo ""

# -------------------------------------------------------------------
# [STEP 1] claude コマンドの確認
# -------------------------------------------------------------------
echo -e "${CYAN}[STEP 1] claude コマンド確認...${RESET}"

if command -v claude &>/dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "(バージョン取得失敗)")
    echo -e "  claude コマンド: ${GREEN}存在${RESET} ($CLAUDE_VERSION)"
else
    echo -e "  claude コマンド: ${RED}存在しない${RESET}"
    echo "  インストール: npm install -g @anthropic-ai/claude-code"
fi

echo ""

# -------------------------------------------------------------------
# [STEP 2] 起動モード別のフリクション分類
# -------------------------------------------------------------------
echo -e "${CYAN}[STEP 2] CLIモード別フリクション分類...${RESET}"
echo ""

echo "  ┌────────────────────────────────────────────────────────┐"
echo "  │ モード                  │ UIダイアログ │ deny list │"
echo "  ├────────────────────────────────────────────────────────┤"
echo "  │ claude（通常）          │ 設定依存    │ 有効      │"
echo "  │  bypassPermissions設定  │ なし        │ 有効      │"
echo "  │  acceptEdits設定        │ あり        │ 有効      │"
echo "  ├────────────────────────────────────────────────────────┤"
echo "  │ claude --dangerously... │ なし        │ 無効化    │"
echo "  └────────────────────────────────────────────────────────┘"
echo ""

if $DANGEROUSLY_MODE; then
    echo -e "  ${YELLOW}[--mode dangerously] この設定でのフリクションを確認中...${RESET}"
    echo -e "  UIダイアログ: ${GREEN}なし（--dangerously-skip-permissions）${RESET}"
    echo -e "  deny list: ${RED}無効化${RESET}（VS Codeより危険）"
    echo -e "  hookブロック: 依存（Night Mode + 常時有効ガード）"
    echo ""
fi

# -------------------------------------------------------------------
# [STEP 3] 現在の設定状態
# -------------------------------------------------------------------
echo -e "${CYAN}[STEP 3] 現在の設定状態...${RESET}"

if [[ -f "$LOCAL_SETTINGS" ]]; then
    LOCAL_MODE=$("/c/Program Files/Python312/python.exe" -c \
        "import json; d=json.load(open(r'$LOCAL_SETTINGS')); print(d.get('defaultMode','(not set)'))" 2>/dev/null || echo "(読み込み失敗)")
    echo -e "  settings.local.json: ${GREEN}存在${RESET} → defaultMode = ${GREEN}$LOCAL_MODE${RESET}"
else
    SHARED_MODE=$("/c/Program Files/Python312/python.exe" -c \
        "import json; d=json.load(open(r'$SHARED_SETTINGS')); print(d.get('defaultMode','(not set)'))" 2>/dev/null || echo "(読み込み失敗)")
    echo -e "  settings.local.json: ${RED}存在しない${RESET}"
    echo -e "  settings.json fallback → defaultMode = ${YELLOW}$SHARED_MODE${RESET}"
fi

# Night Mode
NIGHT_FLAG="$STATE_DIR/night_mode.flag"
if [[ -f "$NIGHT_FLAG" ]]; then
    echo -e "  Night Mode: ${GREEN}ON${RESET} (pvqe-p-gate等バイパス済み)"
else
    echo -e "  Night Mode: ${RED}OFF${RESET} (pvqe-p-gate等は有効)"
fi

echo ""

# -------------------------------------------------------------------
# [STEP 4] hookガード状態
# -------------------------------------------------------------------
echo -e "${CYAN}[STEP 4] hookガード状態...${RESET}"
echo ""
echo "  --- Night Mode でバイパス可能なガード ---"

declare -a BYPASSABLE_GUARDS=(
    "pvqe-p-gate.py|証拠計画要求"
    "pre_edit_task_guard.py|タスクID確認"
)

for guard_desc in "${BYPASSABLE_GUARDS[@]}"; do
    guard="${guard_desc%%|*}"
    desc="${guard_desc##*|}"
    if [[ -f "$HOOKS_DIR/$guard" ]]; then
        if [[ -f "$NIGHT_FLAG" ]]; then
            echo -e "  ${GREEN}✅ バイパス中${RESET} $guard — $desc"
        else
            echo -e "  ${YELLOW}⚠️  有効${RESET}     $guard — $desc (Night Modeでバイパス可)"
        fi
    fi
done

echo ""
echo "  --- 常時有効なガード（CLIモード/Night Modeに関係なく有効）---"

declare -a PERMANENT_GUARDS=(
    "north-star-guard.py|NORTH_STAR.md保護"
    "research-gate.py|廃止用語ブロック"
    "vps-ssh-guard.py|VPS SSH前健全性チェック"
    "llm-judge.py|意味レベル誤実装検知"
    "fact-checker.py|廃止情報出力ブロック"
)

for guard_desc in "${PERMANENT_GUARDS[@]}"; do
    guard="${guard_desc%%|*}"
    desc="${guard_desc##*|}"
    if [[ -f "$HOOKS_DIR/$guard" ]]; then
        echo -e "  ${RED}❌ 常時有効${RESET} $guard — $desc"
    fi
done

echo ""

# -------------------------------------------------------------------
# [STEP 5] Lane B CLI 推奨フロー
# -------------------------------------------------------------------
echo -e "${CYAN}[STEP 5] Lane B CLI で自律実行する場合の推奨フロー...${RESET}"
echo ""
echo "  # 推奨: lane-b-autonomous.sh を使う（Night Mode管理を自動化）"
echo "  bash scripts/runtime/lane-b-autonomous.sh"
echo ""
echo "  # 手動でやる場合:"
echo "  bash scripts/night-mode-on.sh"
echo "  claude --dangerously-skip-permissions"
echo "  bash scripts/night-mode-off.sh  ← 必ず解除！"
echo ""

echo -e "${CYAN}=== 計測完了 ===${RESET}"
echo "結果は docs/CLAUDE_CONFIRMATION_TEST_MATRIX.md に記録してください。"
