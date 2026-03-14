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

# Reset session state — research_done=true: CLAUDE.mdとMEMORY.mdを読んだ=リサーチ済み
cat > "$STATE_DIR/session.json" << 'STATEJSON'
{"research_done":true,"search_count":0,"errors":[],"task_started":false}
STATEJSON

# PVQE-P: セッション開始時にクリア（新セッション = 新しいP定義が必要）
rm -f "$STATE_DIR/pvqe_p.json"
# intent_confirmed.flag もクリア（前セッションの確認は引き継がない）
rm -f "$STATE_DIR/intent_confirmed.flag"
rm -f "$STATE_DIR/intent_needs_confirmation.flag"

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

# H1: 前回セッションからのVPS変更を差分検知
VPS_SNAPSHOT="$STATE_DIR/last_vps_snapshot.json"
if [ -n "$VPS_STATE" ]; then
    echo "$VPS_STATE" > "$STATE_DIR/vps_current.tmp"
    if [ -f "$VPS_SNAPSHOT" ]; then
        H1_DIFF=$(python "$PROJECT_DIR/.claude/hooks/h1-vps-diff.py" \
            "$VPS_SNAPSHOT" "$STATE_DIR/vps_current.tmp" 2>/dev/null)
        if [ -n "$H1_DIFF" ]; then
            echo "--- H1: 前回セッションからのVPS変更 ---"
            echo "$H1_DIFF"
            echo ""
        fi
    fi
    # 現在状態をスナップショットとして保存（次回セッション用）
    python -c "
import json, datetime
try:
    c = open('$STATE_DIR/vps_current.tmp', encoding='utf-8').read()
    json.dump({'timestamp': datetime.datetime.now().isoformat(), 'content': c},
              open('$VPS_SNAPSHOT', 'w', encoding='utf-8'), ensure_ascii=False)
except: pass
" 2>/dev/null
fi

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
        RECENT_MEMORIES=$(python "$PROJECT_DIR/scripts/memory_search.py" --base-dir "$MEMORY_DIR" --recent 10 2>/dev/null)
        if [ -n "$RECENT_MEMORIES" ]; then
            echo "$RECENT_MEMORIES"
        else
            echo "（最近の記憶なし）"
        fi
        echo ""
        echo "💡 記憶検索: 'python scripts/memory_search.py \"検索ワード\"'"
        echo ""
    fi
fi

# H3: 前回セッションの引き継ぎタスクを表示
HANDOFF_FILE="$STATE_DIR/handoff.json"
if [ -f "$HANDOFF_FILE" ]; then
    H3_OUT=$(python -c "
import json
try:
    h = json.load(open('$HANDOFF_FILE', encoding='utf-8'))
    ts = h.get('timestamp', '')[:16].replace('T', ' ')
    ip = h.get('in_progress', [])
    pd = h.get('pending', [])
    if ip or pd:
        print(f'前回セッション ({ts}) の引き継ぎ:')
        for t in ip[:3]:
            name = t.get('content', str(t)) if isinstance(t, dict) else str(t)
            print(f'  🔄 進行中: {name}')
        for t in pd[:3]:
            name = t.get('content', str(t)) if isinstance(t, dict) else str(t)
            print(f'  ⏳ 未着手: {name}')
except: pass
" 2>/dev/null)
    if [ -n "$H3_OUT" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🤝 H3: 前回セッション引き継ぎ"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "$H3_OUT"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
    fi
fi

# ── Hive Mind v2.0: VPS知識をローカルにマージ（バックグラウンド、失敗しても続行）─────
MERGE_SCRIPT="$PROJECT_DIR/scripts/merge_wisdom.py"
if [ -f "$MERGE_SCRIPT" ]; then
    MERGE_RESULT=$(python "$MERGE_SCRIPT" 2>/dev/null)
    if echo "$MERGE_RESULT" | grep -q "\[NEW\]"; then
        echo "🧠 [Hive Mind] VPSから新規知識をマージしました:"
        echo "$MERGE_RESULT" | grep -E "\[NEW\]|\[DONE\]|\+" | head -10
        echo ""
    fi
fi

# ── バックログ表示（未完了タスクをセッション開始時に必ず見せる） ─────────────
BACKLOG_FILE="$PROJECT_DIR/docs/BACKLOG.md"
if [ -f "$BACKLOG_FILE" ]; then
    PENDING_COUNT=$(grep -c "^- \[ \]" "$BACKLOG_FILE" 2>/dev/null || echo 0)
    if [ "$PENDING_COUNT" -gt 0 ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📋 BACKLOG — 約束済み未完了タスク: ${PENDING_COUNT}件"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        grep "^- \[ \]" "$BACKLOG_FILE"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
    fi
fi

# ── Dev-Time Approval Queue — VPS承認待ちキューを取得して表示 ─────────────────
APPROVALS_RESULT=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
    "$VPS" "python3 -c \"
import sys; sys.path.insert(0, '/opt/shared/scripts')
try:
    from approval_utils import get_pending_summary, get_pending_count
    cnt = get_pending_count()
    if cnt > 0:
        print(get_pending_summary())
    else:
        print('')
except Exception as e:
    print(f'[WARN] approval_utils: {e}')
\"" 2>/dev/null)

if [ -n "$APPROVALS_RESULT" ] && echo "$APPROVALS_RESULT" | grep -q "AIからの提案"; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$APPROVALS_RESULT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi

# ── 🧬 Evolutionary Ecosystem Audit — 自己進化サマリー ─────────────────────
EVO_AUDIT=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
    "$VPS" "python3 -c \"
import json, os
from datetime import datetime, timezone, timedelta

log_path = '/opt/shared/logs/evolution_log.json'
if not os.path.exists(log_path):
    exit()

try:
    log = json.load(open(log_path, encoding='utf-8'))
except Exception:
    exit()

if not log:
    exit()

# 直近7日以内のエントリ
cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
recent = [e for e in log if e.get('timestamp', '') >= cutoff]

if not recent:
    # 7日以内がなければ最新1件を表示
    recent = [log[-1]]

print('=== 🧬 EVOLUTIONARY ECOSYSTEM AUDIT ===')
print(f'直近の自己進化: {len(recent)}回（過去7日）')
print()
for e in recent[-3:]:  # 最大3件表示
    date = e.get('date', '?')
    brier = e.get('avg_brier', '?')
    hits  = e.get('hit_count', 0)
    misses= e.get('miss_count', 0)
    n_analyzed = e.get('analyzed_count', 0)
    summary = e.get('insights_summary', '')[:200]
    print(f'📅 {date} | 分析: {n_analyzed}件 | 的中: {hits} / 外れ: {misses} | 平均Brier: {brier}')
    print(f'   AIの学習: {summary[:150]}')
    print()

print('→ 詳細: /opt/shared/logs/evolution_log.json')
print('→ 原則: 第3原則（自律的進化）+ 原則11 Evolutionary Ecosystem')
\" " 2>/dev/null)

if [ -n "$EVO_AUDIT" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$EVO_AUDIT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi

echo "--- RULES ---"
echo "1. RESEARCH FIRST: WebSearch/WebFetch BEFORE any implementation"
echo "2. CHECK KNOWN_MISTAKES.md BEFORE starting any new task"
echo "3. After errors: RECORD in KNOWN_MISTAKES.md immediately"
echo "4. Your score is tracked. Research = +points. Repeated mistakes = -points."
echo "5. ★ @aisaintel は存在しない(廃止)。NowpatternのXは @nowpattern。AISAパイプラインはSUSPENDED。"
echo "6. 長期記憶: memory_search.py で過去の知識を検索可能"
echo "7. 新規コード作成前に TodoWrite でタスク計画を書くこと（書かないと物理ブロック）"
echo "8. ★ 新しいタスクを約束したら docs/BACKLOG.md に追加すること（完了まで追跡）"
echo "=== END MANDATORY CONTEXT ==="

# ── タスクダッシュボードの状態を表示 ──────────────────────────────────────
DASHBOARD_HTML="$HOME/.claude/tasks/dashboard.html"
CURRENT_STATE="$HOME/.claude/tasks/current_state.json"
echo ""
echo "📋 タスクボード: file://$DASHBOARD_HTML（ブラウザで開くと10秒ごと自動更新）"
if [ -f "$CURRENT_STATE" ]; then
    IN_PROGRESS=$(python -c "
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

# 6. ★ 週次リサーチチェック（7日以上未実施なら警告）
RESEARCH_STATE="$STATE_DIR/last_research.json"
RESEARCH_DUE=0
if [ -f "$RESEARCH_STATE" ]; then
    DAYS_AGO=$(python -c "
import json, datetime, sys
try:
    d = json.load(open('$RESEARCH_STATE', encoding='utf-8'))
    last = datetime.datetime.fromisoformat(d.get('last_run', '2000-01-01'))
    delta = (datetime.datetime.now() - last).days
    print(delta)
except:
    print(999)
" 2>/dev/null)
    if [ "${DAYS_AGO:-999}" -ge 7 ]; then
        RESEARCH_DUE=1
    fi
else
    RESEARCH_DUE=1
fi

if [ "$RESEARCH_DUE" -eq 1 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔬 [週次リサーチ] 7日以上未実施 — 未知ミス防止のため実行推奨"
    echo "  タスク: WebSearchで世界のAIエージェントミスパターンを検索"
    echo "  対象: 'AI agent mistakes 2026', 'Claude Code pitfalls', 'LLM agent failure modes'"
    echo "  更新先: docs/KNOWN_MISTAKES.md"
    echo "  完了後: python \"$PROJECT_DIR/.claude/hooks/vps-ssh-guard.py\" は自動的にlast_research.jsonを更新"
    echo "  （このセッションで実行したら: python -c \"import json,datetime; open('$RESEARCH_STATE','w').write(json.dumps({'last_run': datetime.datetime.now().isoformat()}))\" ）"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
