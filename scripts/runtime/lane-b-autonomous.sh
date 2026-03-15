#!/usr/bin/env bash
# =============================================================================
# scripts/runtime/lane-b-autonomous.sh
# Lane B — CLI 自律実行起動スクリプト
#
# 用途: 夜間・大量タスク・CI/CD 向けの "practically no-prompt" 実行環境
# 効果:
#   - --dangerously-skip-permissions: 全UI確認ダイアログを無効化
#   - night_mode.flag 作成: pvqe-p-gate + pre_edit_task_guard をバイパス
#
# 使い方:
#   bash scripts/runtime/lane-b-autonomous.sh
#   bash scripts/runtime/lane-b-autonomous.sh --dry-run
#
# 終了後:
#   bash scripts/night-mode-off.sh  ← Night Mode を忘れずに解除
# =============================================================================

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="$REPO_ROOT/.claude/hooks/state"
NIGHT_MODE_FLAG="$STATE_DIR/night_mode.flag"

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

echo -e "${CYAN}=== Lane B: 自律実行モード ===${RESET}"
echo ""

# -------------------------------------------------------------------
# --dry-run モード
# -------------------------------------------------------------------
if [[ "$1" == "--dry-run" ]]; then
    echo -e "${YELLOW}[DRY-RUN] 以下の操作が実行されます:${RESET}"
    echo "  1. night_mode.flag を作成 → pvqe-p-gate + pre_edit_task_guard をバイパス"
    echo "  2. claude --dangerously-skip-permissions を起動"
    echo ""
    echo -e "${YELLOW}[DRY-RUN] 現在の状態:${RESET}"
    if [[ -f "$NIGHT_MODE_FLAG" ]]; then
        echo -e "  Night Mode: ${GREEN}ON${RESET} (既にフラグが存在)"
    else
        echo -e "  Night Mode: ${RED}OFF${RESET}"
    fi
    echo ""
    echo "  残るガード（Night Mode後も有効）:"
    echo "    - research-gate.py     ← 廃止用語・未調査実装の防御"
    echo "    - north-star-guard.py  ← NORTH_STAR.md 保護"
    echo "    - vps-ssh-guard.py     ← VPS SSH前の健全性チェック"
    echo "    - llm-judge.py         ← 意味レベルの誤実装検知"
    echo ""
    echo -e "${GREEN}[DRY-RUN] 完了。実際に実行するには --dry-run なしで起動してください。${RESET}"
    exit 0
fi

# -------------------------------------------------------------------
# 前提確認
# -------------------------------------------------------------------
echo -e "${CYAN}[1/3] 前提確認...${RESET}"

# claude コマンドの存在確認
if ! command -v claude &>/dev/null; then
    echo -e "${RED}エラー: claude コマンドが見つかりません。${RESET}"
    echo "  インストール: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

# STATE_DIR の存在確認
if [[ ! -d "$STATE_DIR" ]]; then
    mkdir -p "$STATE_DIR"
    echo "  STATE_DIR を作成: $STATE_DIR"
fi

echo -e "  ${GREEN}OK${RESET}"

# -------------------------------------------------------------------
# Night Mode 有効化
# -------------------------------------------------------------------
echo -e "${CYAN}[2/3] Night Mode を有効化...${RESET}"

# pvqe_p.json / intent flags を削除（フロー制御フラグをクリア）
rm -f "$STATE_DIR/intent_confirmed.flag"
rm -f "$STATE_DIR/intent_needs_confirmation.flag"
rm -f "$STATE_DIR/pvqe_p.json"

# Night Mode フラグを作成
touch "$NIGHT_MODE_FLAG"

if [[ -f "$NIGHT_MODE_FLAG" ]]; then
    echo -e "  Night Mode: ${GREEN}ON${RESET}"
    echo "  バイパス対象:"
    echo "    ✅ pvqe-p-gate.py"
    echo "    ✅ pre_edit_task_guard.py"
    echo "    ✅ intent-confirm.py"
    echo ""
    echo -e "  ${YELLOW}⚠️  残るガード（消えない）:${RESET}"
    echo "    ❌ research-gate.py, north-star-guard.py, vps-ssh-guard.py, llm-judge.py"
else
    echo -e "${RED}エラー: night_mode.flag の作成に失敗しました。${RESET}"
    exit 1
fi

# -------------------------------------------------------------------
# claude --dangerously-skip-permissions 起動
# -------------------------------------------------------------------
echo -e "${CYAN}[3/3] Claude Code を起動します（自律実行モード）...${RESET}"
echo ""
echo -e "${YELLOW}【終了後に必ず実行】bash scripts/night-mode-off.sh${RESET}"
echo ""

# トラップ: 終了時に Night Mode を解除するか確認
cleanup() {
    echo ""
    echo -e "${CYAN}=== Lane B セッション終了 ===${RESET}"
    if [[ -f "$NIGHT_MODE_FLAG" ]]; then
        echo -n "Night Mode を解除しますか？ [Y/n]: "
        read -r answer
        if [[ "$answer" != "n" && "$answer" != "N" ]]; then
            rm -f "$NIGHT_MODE_FLAG"
            echo -e "  Night Mode: ${RED}OFF${RESET}（解除済み）"
        else
            echo -e "  Night Mode: ${YELLOW}ON のまま${RESET}（後で手動解除: bash scripts/night-mode-off.sh）"
        fi
    fi
}
trap cleanup EXIT

claude --dangerously-skip-permissions
