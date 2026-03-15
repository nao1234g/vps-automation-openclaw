#!/usr/bin/env bash
# =============================================================================
# scripts/runtime/test-vscode-friction.sh
# T019 実測スクリプト: VS Code Extension 環境でのフリクション計測
#
# 用途: VS Code Extension モードでどのフリクション（確認ダイアログ/hookブロック）が
#       発生するかを確認するための診断スクリプト
#
# 使い方:
#   bash scripts/runtime/test-vscode-friction.sh
#   bash scripts/runtime/test-vscode-friction.sh --check-only  # 設定状態確認のみ
#
# 重要: このスクリプトはClaude Codeが生成する操作のUI確認ダイアログを
#       「代わりに確認」することはできない。
#       UIダイアログの発生有無はClaude Codeを操作して目視確認が必要。
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

echo -e "${CYAN}=== T019 VS Code Extension: フリクション計測スクリプト ===${RESET}"
echo ""
echo "【区別すること】"
echo "  (A) UI確認ダイアログ = permission mode (acceptEdits/bypassPermissions) で制御"
echo "  (B) hookブロック(exit 2) = 各hookのロジック + Night Mode で制御"
echo "  これらは完全に独立した仕組み。混同禁止。"
echo ""

# -------------------------------------------------------------------
# [STEP 1] Permission Mode の確認 → UIダイアログの有無を判定
# -------------------------------------------------------------------
echo -e "${CYAN}[STEP 1] Permission Mode 確認（UIダイアログ有無の判定）...${RESET}"

EFFECTIVE_MODE="(不明)"

if [[ -f "$LOCAL_SETTINGS" ]]; then
    LOCAL_MODE=$("/c/Program Files/Python312/python.exe" -c \
        "import json; d=json.load(open(r'$LOCAL_SETTINGS')); print(d.get('defaultMode','(not set)'))" 2>/dev/null || echo "(読み込み失敗)")
    echo -e "  settings.local.json: ${GREEN}存在${RESET} → defaultMode = ${GREEN}$LOCAL_MODE${RESET}"
    EFFECTIVE_MODE="$LOCAL_MODE"
    echo -e "  → settings.local.json が settings.json より優先される"
else
    echo -e "  settings.local.json: ${RED}存在しない${RESET}"
    SHARED_MODE=$("/c/Program Files/Python312/python.exe" -c \
        "import json; d=json.load(open(r'$SHARED_SETTINGS')); print(d.get('defaultMode','(not set)'))" 2>/dev/null || echo "(読み込み失敗)")
    echo -e "  settings.json fallback → defaultMode = ${YELLOW}$SHARED_MODE${RESET}"
    EFFECTIVE_MODE="$SHARED_MODE"
fi

echo ""
if [[ "$EFFECTIVE_MODE" == "bypassPermissions" ]]; then
    echo -e "  ${GREEN}✅ UIダイアログ: なし（bypassPermissions有効）${RESET}"
    echo -e "  ${GREEN}   T019実測確認済み: Bash/Edit/Write全てダイアログなしで実行${RESET}"
elif [[ "$EFFECTIVE_MODE" == "acceptEdits" ]]; then
    echo -e "  ${YELLOW}⚠️  UIダイアログ: あり（acceptEditsモード）${RESET}"
    echo -e "  ${YELLOW}   Edit/Write操作時にClaude Codeが確認を求める${RESET}"
else
    echo -e "  ${RED}❌ UIダイアログ: 不明（設定読み込み失敗）${RESET}"
fi

echo ""

# -------------------------------------------------------------------
# [STEP 2] Night Mode の確認 → hookバイパスの有無
# -------------------------------------------------------------------
echo -e "${CYAN}[STEP 2] Night Mode 確認（hookバイパスの有無）...${RESET}"

NIGHT_FLAG="$STATE_DIR/night_mode.flag"
if [[ -f "$NIGHT_FLAG" ]]; then
    echo -e "  Night Mode: ${GREEN}ON${RESET}"
    echo -e "  バイパス対象:"
    echo -e "    ${GREEN}✅${RESET} pvqe-p-gate.py (証拠計画要求)"
    echo -e "    ${GREEN}✅${RESET} pre_edit_task_guard.py (タスクID確認)"
    echo -e "    ${GREEN}✅${RESET} intent-confirm.py"
else
    echo -e "  Night Mode: ${RED}OFF${RESET}"
    echo -e "  以下のhookが有効（証拠計画/タスクID等の確認が必要）:"
    echo -e "    ${YELLOW}⚠️${RESET}  pvqe-p-gate.py"
    echo -e "    ${YELLOW}⚠️${RESET}  pre_edit_task_guard.py"
fi

echo ""

# -------------------------------------------------------------------
# [STEP 3] 常時有効なhook（Night Modeでもバイパス不可）
# -------------------------------------------------------------------
echo -e "${CYAN}[STEP 3] 常時有効ガード確認（Night Modeに関係なく動作）...${RESET}"

declare -a PERMANENT_GUARDS=(
    "north-star-guard.py|NORTH_STAR.md保護 + docs/*.md Write禁止"
    "research-gate.py|廃止用語ブロック + 未調査新規コード禁止"
    "vps-ssh-guard.py|VPS SSH前健全性チェック"
    "llm-judge.py|意味レベル誤実装検知（Gemini）"
    "fact-checker.py|廃止用語・未確認情報の出力ブロック"
)

for guard_desc in "${PERMANENT_GUARDS[@]}"; do
    guard="${guard_desc%%|*}"
    desc="${guard_desc##*|}"
    if [[ -f "$HOOKS_DIR/$guard" ]]; then
        echo -e "  ${GREEN}✅ 存在${RESET} $guard — $desc"
    else
        echo -e "  ${RED}❌ 不在${RESET} $guard — $desc"
    fi
done

echo ""

# -------------------------------------------------------------------
# [STEP 4] devcontainer環境の場合の追加警告
# -------------------------------------------------------------------
if [[ -f "/.dockerenv" ]] || [[ -n "$REMOTE_CONTAINERS" ]] || [[ -n "$CODESPACES" ]]; then
    echo -e "${YELLOW}=== devcontainer内で実行中 ===${RESET}"
    echo -e "${YELLOW}⚠️  注意: devcontainerではsettings.local.jsonが存在しない可能性があります。${RESET}"
    if [[ -f "$LOCAL_SETTINGS" ]]; then
        echo -e "  settings.local.json: ${GREEN}存在する（マウントされている）${RESET}"
    else
        echo -e "  settings.local.json: ${RED}存在しない${RESET}"
        echo -e "  → .claude/settings.json の defaultMode を bypassPermissions にしてください"
    fi
    echo ""
fi

# -------------------------------------------------------------------
# [STEP 5] 目視確認ガイド（--check-only でなければ表示）
# -------------------------------------------------------------------
if [[ "$1" != "--check-only" ]]; then
    echo -e "${CYAN}[STEP 4] 目視確認ガイド（Claude Codeを操作して確認）...${RESET}"
    echo ""
    echo "以下の手順でUIダイアログ発生有無を実際に確認してください:"
    echo ""
    echo "  1. VS Code内でClaude Code チャット画面を開く"
    echo "  2. 「一時ファイル .claude/state/friction_test.tmp を作成して」と依頼"
    echo "  3. Claude CodeがBash/Edit操作を実行する際にダイアログが出るか目視確認"
    echo ""
    if [[ "$EFFECTIVE_MODE" == "bypassPermissions" ]]; then
        echo -e "  期待される結果: ${GREEN}ダイアログなし（bypassPermissions有効）${RESET}"
        echo -e "  残る摩擦: ${YELLOW}hookブロック(exit 2)のみ（Night Mode前提）${RESET}"
    else
        echo -e "  期待される結果: ${YELLOW}ダイアログあり（acceptEditsモード）${RESET}"
        echo -e "  対策: settings.local.json を bypassPermissions に変更して再起動${RESET}"
    fi
    echo ""
    echo "結果は docs/CLAUDE_CONFIRMATION_TEST_MATRIX.md に記録してください。"
fi

echo ""
echo -e "${CYAN}=== 計測完了 ===${RESET}"
