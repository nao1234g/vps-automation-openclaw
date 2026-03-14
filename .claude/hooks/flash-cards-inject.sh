#!/bin/bash
# =============================================================================
# FLASH CARDS INJECT — UserPromptSubmit Hook
# =============================================================================
# 毎ターン開始時にFLASH_CARDS.mdを注入する。
# LLMは学習データより「今このコンテキストにある情報」を優先するため、
# 毎ターン注入することでセッション開始時だけでなく常に参照可能にする。
# NIGHT MODE: night_mode.flag が存在する場合、自律運転指示を追加注入する。
# =============================================================================

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
FLASH_FILE="$PROJECT_DIR/.claude/FLASH_CARDS.md"
NIGHT_MODE_FLAG="$PROJECT_DIR/.claude/hooks/state/night_mode.flag"

if [ -f "$FLASH_FILE" ]; then
    cat "$FLASH_FILE"
fi

# NIGHT MODE: 自律運転中の場合は強制指示を注入
if [ -f "$NIGHT_MODE_FLAG" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌙 【NIGHT MODE / 自律運転モード】— ユーザーは不在です"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  MANDATORY RULES（守らないとタスクが止まる）:"
    echo "  ★ AskUserQuestion = 完全禁止。代わりに安全な選択を取って続行する。"
    echo "  ★ EnterPlanMode = 完全禁止。計画は内部で立て、即実行する。"
    echo "  ★「〜でよいですか？」「進めますか？」等の確認テキスト = 禁止。"
    echo "  ★ 判断に迷ったら → リスクの低い安全な選択を取り、自律実行する。"
    echo "  ★ エラーが出ても止まらない → ログして次のタスクへスキップする。"
    echo "  ★ 全タスク完了後 → 結果サマリーを出力して終了する。"
    echo "  解除: bash scripts/night-mode-off.sh"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
