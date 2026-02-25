#!/bin/bash
# =============================================================================
# SESSION START HOOK — MANDATORY CONTEXT INJECTION
# =============================================================================
# 毎セッション開始時に必ず実行。VPSの最新状態を取得してコンテキストに注入する。
# CLAUDE.mdより VPS の SYSTEM_BRIEFING.md が正しい（常に最新）。
# =============================================================================

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
MISTAKES_FILE="$PROJECT_DIR/docs/KNOWN_MISTAKES.md"
SCORECARD_FILE="$PROJECT_DIR/.claude/SCORECARD.md"
STATE_DIR="$PROJECT_DIR/.claude/hooks/state"
VPS="root@163.44.124.123"

mkdir -p "$STATE_DIR"

# Reset session state
cat > "$STATE_DIR/session.json" << 'STATEJSON'
{"research_done":false,"search_count":0,"errors":[],"task_started":false}
STATEJSON

echo "=== SESSION START: MANDATORY CONTEXT ==="
echo ""

# 1. Show scorecard
if [ -f "$SCORECARD_FILE" ]; then
    echo "--- YOUR PERFORMANCE SCORECARD ---"
    cat "$SCORECARD_FILE"
    echo ""
fi

# 2. Show recent mistakes
if [ -f "$MISTAKES_FILE" ]; then
    echo "--- RECENT MISTAKES (DO NOT REPEAT) ---"
    grep -A 2 "^### " "$MISTAKES_FILE" | tail -25
    echo ""
fi

# 3. ★ CRITICAL: VPSの最新状態を取得（CLAUDE.mdより優先）
echo "--- VPS LIVE STATE (authoritative — overrides CLAUDE.md) ---"
VPS_STATE=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
    "$VPS" "cat /opt/shared/SHARED_STATE.md" 2>/dev/null)

if [ -n "$VPS_STATE" ]; then
    echo "$VPS_STATE"
else
    echo "[WARN] VPS接続失敗 — CLAUDE.mdのCurrent Stateセクションを参照（古い可能性あり）"
fi
echo ""

# 3b. ★ 全エージェント共有知識ベース（リアルタイム同期）
echo "--- AGENT SHARED KNOWLEDGE (all agents read/write this) ---"
AGENT_KNOWLEDGE=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
    "$VPS" "cat /opt/shared/AGENT_KNOWLEDGE.md" 2>/dev/null)
if [ -n "$AGENT_KNOWLEDGE" ]; then
    echo "$AGENT_KNOWLEDGE"
else
    echo "[WARN] AGENT_KNOWLEDGE.md取得失敗"
fi
echo ""

# 4. ★ 長期記憶から関連コンテキストを注入
MEMORY_DIR="$PROJECT_DIR/.claude/memory"
if [ -d "$MEMORY_DIR/entries" ]; then
    MEMORY_COUNT=$(ls "$MEMORY_DIR/entries/"*.md 2>/dev/null | wc -l)
    if [ "$MEMORY_COUNT" -gt 0 ]; then
        echo "--- LONG-TERM MEMORY ($MEMORY_COUNT entries) ---"
        # 最近の記憶10件を表示
        RECENT_MEMORIES=$(python3 "$PROJECT_DIR/scripts/memory_search.py" --base-dir "$MEMORY_DIR" --recent 10 2>/dev/null)
        if [ -n "$RECENT_MEMORIES" ]; then
            echo "$RECENT_MEMORIES"
        else
            echo "（最近の記憶なし）"
        fi
        echo ""
        echo "💡 記憶検索: 'python3 scripts/memory_search.py \"検索ワード\"'"
        echo ""
    fi
fi

echo "--- RULES ---"
echo "1. RESEARCH FIRST: WebSearch/WebFetch BEFORE any implementation"
echo "2. CHECK KNOWN_MISTAKES.md BEFORE starting any new task"
echo "3. After errors: RECORD in KNOWN_MISTAKES.md immediately"
echo "4. Your score is tracked. Research = +points. Repeated mistakes = -points."
echo "5. ★ @aisaintel は存在しない(廃止)。NowpatternのXは @nowpattern。AISAパイプラインはSUSPENDED。"
echo "6. 長期記憶: memory_search.py で過去の知識を検索可能"
echo "7. 新規コード作成前に TodoWrite でタスク計画を書くこと（書かないと物理ブロック）"
echo "=== END MANDATORY CONTEXT ==="

# ── タスクダッシュボードの状態を表示 ──────────────────────────────────────
DASHBOARD_HTML="$HOME/.claude/tasks/dashboard.html"
CURRENT_STATE="$HOME/.claude/tasks/current_state.json"
echo ""
echo "📋 タスクボード: file://$DASHBOARD_HTML（ブラウザで開くと10秒ごと自動更新）"
if [ -f "$CURRENT_STATE" ]; then
    IN_PROGRESS=$(python3 -c "
import json, sys
try:
    s = json.load(open('$CURRENT_STATE', encoding='utf-8'))
    ip = s.get('in_progress', [])
    pd = s.get('pending', [])
    done = s.get('completed', [])
    if ip: print('  実行中: ' + ' / '.join(ip[:2]))
    if pd: print('  未着手: ' + str(len(pd)) + '件')
    if done: print('  完了: ' + str(len(done)) + '件（本日）')
except: pass
" 2>/dev/null)
    if [ -n "$IN_PROGRESS" ]; then
        echo "$IN_PROGRESS"
    fi
fi

# 5. ★ MEMORY.mdをVPS状態で更新（次セッション用 — バックグラウンド実行）
python "$PROJECT_DIR/scripts/update_local_memory.py" > /dev/null 2>&1 &
