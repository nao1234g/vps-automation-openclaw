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

# P4: Read Comprehension Gate (hash-enhanced) — NORTH_STAR.md の内容ハッシュも記録
# このフラグが存在しないとEdit/Writeがブロックされる（north-star-guard.py が検証）
# ハッシュが現在のファイルと一致しない場合もブロック（staleセッション検知）
NS_FILE="$PROJECT_DIR/.claude/rules/NORTH_STAR.md"
if [ -f "$NS_FILE" ]; then
    NS_HASH=$(python -c "import hashlib; print(hashlib.sha256(open(r'$NS_FILE','rb').read()).hexdigest()[:16])" 2>/dev/null || echo "nohash")
else
    NS_HASH="missing"
fi
echo "$(date +%Y-%m-%d):${NS_HASH}" > "$STATE_DIR/north_star_loaded.flag"

# PVQE-P: セッション開始時にクリア（新セッション = 新しいP定義が必要）
rm -f "$STATE_DIR/pvqe_p.json"
# intent_confirmed.flag もクリア（前セッションの確認は引き継がない）
rm -f "$STATE_DIR/intent_confirmed.flag"
rm -f "$STATE_DIR/intent_needs_confirmation.flag"

echo "=== SESSION START: MANDATORY CONTEXT ==="
echo ""
MISSION_CONTRACT_SCRIPT="$PROJECT_DIR/scripts/mission_contract.py"
if [ -f "$MISSION_CONTRACT_SCRIPT" ]; then
    echo "--- MISSION CONTRACT (authoritative) ---"
    python "$MISSION_CONTRACT_SCRIPT" --summary 2>/dev/null || true
    echo ""
fi
BOOTSTRAP_CONTEXT_SCRIPT="$PROJECT_DIR/scripts/agent_bootstrap_context.py"
if [ -f "$BOOTSTRAP_CONTEXT_SCRIPT" ]; then
    echo "--- AGENT BOOTSTRAP CONTEXT (authoritative) ---"
    python "$BOOTSTRAP_CONTEXT_SCRIPT" --summary 2>/dev/null || true
    echo ""
fi

# ── NAOTO OS PRIMARY ANCHOR（Resume Guard — project drift 防止） ──────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏛️  NAOTO OS PRIMARY ANCHOR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  このリポジトリ = Naoto Intelligence OS のルート"
echo "  Nowpattern    = NAOTO OS 配下のプロジェクト（最重要だが最上位ではない）"
echo "  正式名称: 「NAOTO OS」または「Naoto Intelligence OS」"
echo "  ⚠️  Nowpattern を主語にして OS を語ること / vps-automation を Nowpattern 専用と言うことは禁止"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── ⛔ ECC強制の鉄則（全エージェント毎セッション必読・コードで強制表示） ────────
echo "╔══════════════════════════════════════════════════╗"
echo "║  ⛔  テキストは強制しない。コードだけが強制する  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  ❌ KNOWN_MISTAKES.md に書く  = ゼロ強制力（人間への通知のみ）"
echo "  ❌ AGENT_WISDOM.md に書く    = ゼロ強制力（人間への通知のみ）"
echo "  ❌ CLAUDE.md にルールを書く  = ゼロ強制力（コンテキスト外れたら忘れる）"
echo ""
echo "  ✅ 唯一の物理強制手段:"
echo "     mistake_patterns.json に GUARD_PATTERN 追加"
echo "     → fact-checker.py が Stop hook で exit 2 → 物理ブロック"
echo ""
PATTERN_COUNT=$(python -c "
import json, sys
try:
    d = json.load(open('$PROJECT_DIR/.claude/hooks/state/mistake_patterns.json', encoding='utf-8'))
    n = len(d) if isinstance(d, list) else len(d.get('patterns', []))
    print(n)
except Exception as e:
    print('?')
" 2>/dev/null || echo "?")
echo "  現在の物理ガード数: ${PATTERN_COUNT} パターン（mistake_patterns.json）"
echo ""
echo "  ★ ミス発見したとき の正しい手順（2段セット必須）："
echo "     Step 1: KNOWN_MISTAKES.md に記録（人間可読）"
echo "     Step 2: mistake_patterns.json に GUARD_PATTERN 追加（機械強制）"
echo "     ← この2つが揃って初めてガード完了。Step 1だけでは未完了。"
echo ""
echo "  ⚠️  違反検知: fact-checker.py が「テキスト記録=完了」主張をブロック"
echo "╔══════════════════════════════════════════════════╗"
echo "║  この原則は初めてではない。何度も言われている。  ║"
echo "╚══════════════════════════════════════════════════╝"
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
# SSH retry: 最大3回（一時的なネットワーク不安定に対応）
VPS_STATE=""
for _ssh_retry in 1 2 3; do
    VPS_STATE=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 -o BatchMode=yes \
        "$VPS" "cat /opt/shared/SHARED_STATE.md" 2>/dev/null)
    [ -n "$VPS_STATE" ] && break
    [ "$_ssh_retry" -lt 3 ] && sleep 2
done

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

# 3c. ★ ローカル自己学習ログ（session-end.py が自動更新）
AGENT_WISDOM_FILE="$PROJECT_DIR/docs/AGENT_WISDOM.md"
if [ -f "$AGENT_WISDOM_FILE" ]; then
    echo "--- AGENT WISDOM (local self-learning log, auto-updated by session-end.py) ---"
    WISDOM_TAIL=$(grep -A 30 "## 自己学習ログ" "$AGENT_WISDOM_FILE" 2>/dev/null | tail -20)
    if [ -n "$WISDOM_TAIL" ]; then
        echo "$WISDOM_TAIL"
    else
        echo "（自己学習ログなし）"
    fi
    echo ""
else
    echo "[WARN] docs/AGENT_WISDOM.md が見つかりません (session-end.py の書き込みが無効化されています)"
    echo ""
fi

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

# ── 3d. ECC Guard Health Check（前回regression結果表示 + バックグラウンド更新） ──
REGRESSION_CACHE="$STATE_DIR/last_regression_result.txt"
REGRESSION_RUNNER="$PROJECT_DIR/.claude/hooks/regression-runner.py"
if [ -f "$REGRESSION_CACHE" ]; then
    REGRESSION_SUMMARY=$(grep -E "^結果:|❌ FAIL" "$REGRESSION_CACHE" 2>/dev/null | head -5)
    REGRESSION_TS=$(grep "\[REGRESSION RUNNER\] 開始:" "$REGRESSION_CACHE" 2>/dev/null | head -1)
    if [ -n "$REGRESSION_SUMMARY" ]; then
        echo "--- ECC GUARD HEALTH (regression-runner.py) ---"
        [ -n "$REGRESSION_TS" ] && echo "  $REGRESSION_TS"
        echo "  $REGRESSION_SUMMARY"
        echo ""
    fi
elif [ -f "$REGRESSION_RUNNER" ]; then
    echo "--- ECC GUARD HEALTH ---"
    echo "  [初回] 初期化中 — バックグラウンドで regression-runner.py を実行中"
    echo ""
fi
# バックグラウンド実行（次回セッション用にキャッシュ更新、失敗しても続行）
[ -f "$REGRESSION_RUNNER" ] && python "$REGRESSION_RUNNER" "$PROJECT_DIR" > "$REGRESSION_CACHE" 2>&1 &

# ── Coordination OS: local-claude セッション開始時の登録 ─────────────────────
# 毎セッション開始時に local-claude を coordination.db に登録（INSERT OR REPLACE）
COORD_REG=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 -o BatchMode=yes \
    "$VPS" "python3 -c \"
import sqlite3, time, uuid, sys
DB = '/opt/shared/coordination/coordination.db'
agent_id = 'local-claude'
model = 'claude-sonnet-4-6'
host = 'local-win11'
workspace = 'c:/Users/user/OneDrive/desktop/vps-automation-openclaw'
try:
    db = sqlite3.connect(DB, timeout=10)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA busy_timeout=8000')
    now = time.time()
    sid = str(uuid.uuid4())
    db.execute(
        'INSERT OR REPLACE INTO agents (agent_id, session_id, model, host, workspace, current_status, last_heartbeat_at, registered_at) VALUES (?,?,?,?,?,?,?,?)',
        (agent_id, sid, model, host, workspace, 'idle', now, now)
    )
    db.execute(
        'INSERT OR IGNORE INTO events (event_id, event_type, timestamp, actor, entity_type, entity_id, previous_state, new_state, payload) VALUES (?,?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()), 'agent.registered', now, agent_id, 'agent', agent_id, 'dead', 'idle', '{\"source\":\"session-start.sh\"}')
    )
    db.commit()
    db.close()
    print('OK')
except Exception as e:
    print(f'FAIL: {e}')
\"" 2>/dev/null)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤝 COORDINATION OS — エージェント状態"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$COORD_REG" = "OK" ]; then
    echo "  ✅ local-claude を coordination.db に登録しました"
else
    echo "  ⚠️  local-claude 登録失敗: $COORD_REG（VPS接続を確認してください）"
fi

# ── Coordination タスク作成（セッション開始時） ────────────────────────
COORD_STATE_FILE="$PROJECT_DIR/.claude/hooks/state/coord_session_task.json"
COORD_TASK_ID=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 -o BatchMode=yes \
    "$VPS" "python3 -c \"
import sys, json
sys.path.insert(0, '/opt/shared/scripts')
from coordination_workflow import CoordWorkflow
wf = CoordWorkflow('local-claude')
ctx = wf.start(
    title='local-claude-session',
    description='Claude Code session on Windows',
    scope='local-session',
    tags=['local-claude', 'session'],
)
if ctx:
    print(ctx.task_id)
else:
    print('FAILED')
\"" 2>/dev/null || echo "FAILED")

if [ "$COORD_TASK_ID" != "FAILED" ] && [ -n "$COORD_TASK_ID" ]; then
    echo "  ✅ セッションタスク登録: $COORD_TASK_ID"
    echo "{\"task_id\": \"$COORD_TASK_ID\", \"files_edited\": []}" > "$COORD_STATE_FILE" 2>/dev/null || true
else
    echo "  ⚠️  セッションタスク登録失敗 (VPS接続確認)"
fi

COORD_STATUS=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
    "$VPS" "python3 /opt/shared/scripts/coordination_cli.py agents 2>/dev/null" 2>/dev/null)
if [ -n "$COORD_STATUS" ]; then
    echo "$COORD_STATUS"
else
    echo "  [WARN] coordination_cli.py agents 取得失敗"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

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

# ── MAILBOX + BOARD + RESUME: Codex統合設計に基づく必読ファイル ──────────────
# 読み込み順: global truth → cross-agent handoff → self-resume（Codex推奨順序）
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📬 CROSS-AGENT MAILBOX & RESUME STATE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. task_ledger.json（global truth: タスク台帳）
TASK_LEDGER="$PROJECT_DIR/.claude/state/task_ledger.json"
if [ -f "$TASK_LEDGER" ]; then
    LEDGER_SUMMARY=$(python -c "
import json
try:
    d = json.load(open('$TASK_LEDGER', encoding='utf-8'))
    tasks = d.get('tasks', [])
    active = [t for t in tasks if t.get('status') in ('active', 'in_progress')]
    blocked = [t for t in tasks if t.get('status') == 'blocked']
    done = [t for t in tasks if t.get('status') == 'done']
    print(f'  タスク台帳: active={len(active)}, blocked={len(blocked)}, done={len(done)}')
    for t in active[:3]:
        tid = t.get('task_id', t.get('id', '?'))
        title = t.get('title', t.get('description', ''))[:60]
        print(f'    🔄 {tid}: {title}')
    for t in blocked[:2]:
        tid = t.get('task_id', t.get('id', '?'))
        reason = t.get('blocking_reason', '')[:50]
        print(f'    ⛔ {tid}: {reason}')
except Exception as e:
    print(f'  [WARN] task_ledger.json 読み込み失敗: {e}')
" 2>/dev/null)
    [ -n "$LEDGER_SUMMARY" ] && echo "$LEDGER_SUMMARY"
fi

# 2. PREDICTION_EXECUTION_BOARD.md（global truth: 全体進捗）
EXEC_BOARD="$PROJECT_DIR/docs/PREDICTION_EXECUTION_BOARD.md"
if [ -f "$EXEC_BOARD" ]; then
    BOARD_SUMMARY=$(head -30 "$EXEC_BOARD" 2>/dev/null | grep -E "^(##|Progress|Status|Done|Phase|Current)" | head -5)
    if [ -n "$BOARD_SUMMARY" ]; then
        echo "  📊 Execution Board:"
        echo "$BOARD_SUMMARY" | sed 's/^/    /'
    fi
fi

# 3. codex-to-claude.md（cross-agent: Codexからの最新メッセージ）
# まずVPSから最新版をpull（Codex dispatcherが書いた回答を取得）
scp -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
    root@163.44.124.123:/opt/shared/agent-mailbox/codex-to-claude.md \
    "$PROJECT_DIR/.agent-mailbox/codex-to-claude.md" 2>/dev/null && \
    echo "  📥 Codex回答をVPSからpull完了"
CODEX_MSG="$PROJECT_DIR/.agent-mailbox/codex-to-claude.md"
if [ -f "$CODEX_MSG" ]; then
    CODEX_DATE=$(head -3 "$CODEX_MSG" 2>/dev/null | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}" | head -1)
    CODEX_TITLE=$(head -5 "$CODEX_MSG" 2>/dev/null | grep "^##" | head -1)
    echo "  📩 Codex → Claude (${CODEX_DATE:-unknown}):"
    echo "    ${CODEX_TITLE:-（タイトルなし）}"
    # 最初の要点だけ表示（長すぎるメッセージは省略）
    CODEX_SUMMARY=$(sed -n '1,30p' "$CODEX_MSG" 2>/dev/null | grep -E "^(###|- )" | head -5)
    [ -n "$CODEX_SUMMARY" ] && echo "$CODEX_SUMMARY" | sed 's/^/    /'
    echo "    → 全文: .agent-mailbox/codex-to-claude.md"
fi

# 4. claude-to-codex.md（cross-agent: 前回Claudeが送った内容）
CLAUDE_MSG="$PROJECT_DIR/.agent-mailbox/claude-to-codex.md"
if [ -f "$CLAUDE_MSG" ]; then
    CLAUDE_DATE=$(head -3 "$CLAUDE_MSG" 2>/dev/null | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}" | head -1)
    CLAUDE_TITLE=$(head -5 "$CLAUDE_MSG" 2>/dev/null | grep "^##" | head -1)
    echo "  📤 Claude → Codex (${CLAUDE_DATE:-unknown}):"
    echo "    ${CLAUDE_TITLE:-（タイトルなし）}"
fi

# 5. resume_prompt.txt（self-resume: 前回の再開ポイント）
RESUME_FILE="$PROJECT_DIR/reports/claude_sidecar/resume_prompt.txt"
if [ -f "$RESUME_FILE" ]; then
    RESUME_TASK=$(grep "^TASK:" "$RESUME_FILE" 2>/dev/null | head -1)
    RESUME_NOW=$(grep "^NOW DOING:" "$RESUME_FILE" 2>/dev/null | head -1)
    RESUME_NEXT=$(grep "^NEXT EXACT STEP:" "$RESUME_FILE" 2>/dev/null | head -1)
    RESUME_BLOCKER=$(grep "^BLOCKER:" "$RESUME_FILE" 2>/dev/null | head -1)
    if [ -n "$RESUME_TASK" ] || [ -n "$RESUME_NOW" ]; then
        echo "  🔄 Resume State:"
        [ -n "$RESUME_TASK" ] && echo "    $RESUME_TASK"
        [ -n "$RESUME_NOW" ] && echo "    $RESUME_NOW"
        [ -n "$RESUME_NEXT" ] && echo "    $RESUME_NEXT"
        [ -n "$RESUME_BLOCKER" ] && [ "$RESUME_BLOCKER" != "BLOCKER:" ] && [ "$RESUME_BLOCKER" != "BLOCKER: none" ] && echo "    $RESUME_BLOCKER"
    fi
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

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
