#!/usr/bin/env bash
# =============================================================================
# scripts/runtime/lane-b-devcontainer.sh
# Lane B — devcontainer 自律実行起動スクリプト
#
# 用途: devcontainer内でLane B（自律実行モード）を起動する前処理を行う
#
# Lane B CLIとの違い:
#   Lane B CLI:          claude --dangerously-skip-permissions (ローカルターミナル)
#   Lane B devcontainer: devcontainer内でbypassPermissions (devcontainerターミナル)
#                        → UI確認なし + deny listは有効（CLIより安全）
#
# 使い方:
#   bash scripts/runtime/lane-b-devcontainer.sh
#   bash scripts/runtime/lane-b-devcontainer.sh --dry-run
#   bash scripts/runtime/lane-b-devcontainer.sh --open-only  # Night Mode不要
#
# 終了後:
#   bash scripts/night-mode-off.sh  ← Night Mode を忘れずに解除
# =============================================================================

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEVCONTAINER_JSON="$REPO_ROOT/.devcontainer/devcontainer.json"
STATE_DIR="$REPO_ROOT/.claude/hooks/state"
NIGHT_MODE_FLAG="$STATE_DIR/night_mode.flag"

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

echo -e "${CYAN}=== Lane B (devcontainer): 自律実行モード ===${RESET}"
echo ""

# -------------------------------------------------------------------
# --dry-run モード
# -------------------------------------------------------------------
if [[ "$1" == "--dry-run" ]]; then
    echo -e "${YELLOW}[DRY-RUN] 以下の操作が実行されます:${RESET}"
    echo "  1. .devcontainer/devcontainer.json の設定確認"
    echo "  2. night_mode.flag を作成 → pvqe-p-gate + pre_edit_task_guard をバイパス"
    echo "  3. VS Code 'Dev Containers: Reopen in Container' を案内"
    echo ""
    echo -e "${YELLOW}[DRY-RUN] 現在の状態:${RESET}"
    if [[ -f "$DEVCONTAINER_JSON" ]]; then
        echo -e "  devcontainer.json: ${GREEN}存在する${RESET}"
        if grep -q "bypassPermissions\|defaultMode\|claude" "$DEVCONTAINER_JSON" 2>/dev/null; then
            echo -e "  Claude Code設定: ${GREEN}検出${RESET}"
        else
            echo -e "  Claude Code設定: ${YELLOW}未検出（bypassPermissions確認推奨）${RESET}"
        fi
    else
        echo -e "  devcontainer.json: ${RED}存在しない${RESET}"
    fi
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
# --open-only モード: Night Mode なしで devcontainer だけ開く
# -------------------------------------------------------------------
if [[ "$1" == "--open-only" ]]; then
    echo -e "${CYAN}[open-only] Night Mode なし / devcontainerを開きます...${RESET}"
    echo -e "${YELLOW}注意: Night Modeなしの場合、pvqe-p-gate等のhookは有効のままです。${RESET}"
    echo ""
    if command -v code &>/dev/null; then
        code "$REPO_ROOT"
        echo "VS Code が起動しました。"
        echo "コマンドパレット (Ctrl+Shift+P) → 'Dev Containers: Reopen in Container'"
    else
        echo "'code' コマンドが見つかりません。VS Codeを手動で起動してください。"
    fi
    exit 0
fi

# -------------------------------------------------------------------
# 前提確認
# -------------------------------------------------------------------
echo -e "${CYAN}[1/4] 前提確認...${RESET}"

# devcontainer.json の存在確認
if [[ ! -f "$DEVCONTAINER_JSON" ]]; then
    echo -e "${RED}エラー: .devcontainer/devcontainer.json が見つかりません。${RESET}"
    echo "  T019で整備されたはずです。git status を確認してください。"
    exit 1
fi

# すでにdevcontainer内にいる場合の検知
if [[ -f "/.dockerenv" ]] || [[ -n "$REMOTE_CONTAINERS" ]] || [[ -n "$CODESPACES" ]]; then
    echo -e "  ${YELLOW}⚠️  既にdevcontainer内で実行中です。${RESET}"
    echo "  このスクリプトはホスト側（VS Codeのローカルターミナル）で実行してください。"
    echo "  devcontainer内でclaude CLIを直接使用する場合: claude"
    exit 0
fi

# STATE_DIR の存在確認
if [[ ! -d "$STATE_DIR" ]]; then
    mkdir -p "$STATE_DIR"
    echo "  STATE_DIR を作成: $STATE_DIR"
fi

echo -e "  ${GREEN}OK${RESET}"

# -------------------------------------------------------------------
# devcontainer.json の Claude Code 設定チェック
# -------------------------------------------------------------------
echo -e "${CYAN}[2/4] devcontainer.json の設定確認...${RESET}"

if grep -q "bypassPermissions\|defaultMode" "$DEVCONTAINER_JSON" 2>/dev/null; then
    echo -e "  Claude bypassPermissions設定: ${GREEN}検出${RESET}"
elif grep -q "claude\|anthropic" "$DEVCONTAINER_JSON" 2>/dev/null; then
    echo -e "  Claude関連設定: ${YELLOW}部分的に検出（bypassPermissions設定を確認してください）${RESET}"
else
    echo -e "  Claude Code設定: ${YELLOW}未検出${RESET}"
    echo "  devcontainer内でUIダイアログが出る可能性があります。"
    echo "  .devcontainer/devcontainer.json を確認してください。"
    echo ""
fi

# .claude/settings.json の確認（devcontainer内でもこのファイルが参照される）
SETTINGS_JSON="$REPO_ROOT/.claude/settings.json"
if [[ -f "$SETTINGS_JSON" ]]; then
    if grep -q "bypassPermissions" "$SETTINGS_JSON" 2>/dev/null; then
        echo -e "  .claude/settings.json: ${GREEN}bypassPermissions設定あり${RESET}"
    else
        echo -e "  .claude/settings.json: ${YELLOW}bypassPermissions設定なし（acceptEditsが有効）${RESET}"
        echo "  → devcontainer内ではsettings.local.jsonが存在しないため、settings.jsonが使われる"
    fi
fi

echo -e "  ${GREEN}OK${RESET}"

# -------------------------------------------------------------------
# Night Mode 有効化
# -------------------------------------------------------------------
echo -e "${CYAN}[3/4] Night Mode を有効化...${RESET}"

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
    echo -e "  ${YELLOW}⚠️  残るガード（Night Modeでも消えない）:${RESET}"
    echo "    ❌ research-gate.py"
    echo "    ❌ north-star-guard.py"
    echo "    ❌ vps-ssh-guard.py"
    echo "    ❌ llm-judge.py"
else
    echo -e "${RED}エラー: night_mode.flag の作成に失敗しました。${RESET}"
    exit 1
fi

# -------------------------------------------------------------------
# devcontainer 起動案内
# -------------------------------------------------------------------
echo -e "${CYAN}[4/4] devcontainer を開きます...${RESET}"
echo ""
echo -e "${YELLOW}【重要】devcontainerでの作業完了後に必ず実行:${RESET}"
echo "  bash scripts/night-mode-off.sh"
echo ""
echo -e "${YELLOW}【devcontainer内での注意】${RESET}"
echo "  - devcontainerではsettings.local.jsonが存在しない場合がある"
echo "  - settings.json のdefaultModeを確認: $(grep -o '"bypassPermissions"\|"acceptEdits"' "$REPO_ROOT/.claude/settings.json" 2>/dev/null | head -1 || echo '未確認')"
echo ""

if command -v code &>/dev/null; then
    echo -e "${CYAN}VS Code でリポジトリを開いています...${RESET}"
    code "$REPO_ROOT"
    echo ""
    echo -e "${YELLOW}次のステップ:${RESET}"
    echo "  1. VS Code の右下に 'Reopen in Container' 通知が出る場合はクリック"
    echo "  2. または: コマンドパレット (Ctrl+Shift+P) → 'Dev Containers: Reopen in Container'"
    echo "  3. devcontainer内で claude コマンドを実行"
else
    echo -e "${YELLOW}'code' コマンドが見つかりません。${RESET}"
    echo "手動で行ってください:"
    echo "  1. VS Code でこのリポジトリを開く"
    echo "  2. コマンドパレット → 'Dev Containers: Reopen in Container'"
    echo "  3. devcontainer内で claude コマンドを実行"
fi

echo ""
echo -e "${YELLOW}⚠️  Night Mode は devcontainer での作業が完了するまで ON です。${RESET}"
echo "   忘れた場合: bash scripts/night-mode-off.sh"

# トラップ: スクリプト終了時に Night Mode を解除するか確認
cleanup() {
    echo ""
    echo -e "${CYAN}=== Lane B (devcontainer) セッション終了 ===${RESET}"
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
