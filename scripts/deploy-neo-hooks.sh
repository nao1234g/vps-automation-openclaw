#!/bin/bash
# deploy-neo-hooks.sh
# NEO-ONE / NEO-TWO の Claude Code に SessionStart hook を追加する
# 効果: セッション開始時に AGENT_WISDOM.md + CLAUDE.md を強制読み込み
# 実行: bash scripts/deploy-neo-hooks.sh [--dry-run]

set -e

VPS="root@163.44.124.123"
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
err()  { echo -e "${RED}⛔ $*${NC}"; exit 1; }

$DRY_RUN && warn "DRY-RUN モード（実際には変更しません）"

echo "=== NEO VPS Hook デプロイ ==="

# ── Step1: VPS上にhookスクリプトを作成 ────────────────────────────────────────
log "Step1: NEO SessionStart hook を作成..."

HOOK_CONTENT='#!/bin/bash
# NEO SessionStart hook — 毎セッション開始時に必須ドキュメントを読み込む
# 場所: /opt/claude-code-telegram/.claude/hooks/neo-session-start.sh

echo "=== NEO セッション開始 ==="

# AGENT_WISDOM.md を注入（全エージェント共有の知識ベース）
if [ -f /opt/shared/AGENT_WISDOM.md ]; then
    echo "--- AGENT_WISDOM.md ---"
    cat /opt/shared/AGENT_WISDOM.md
else
    echo "[WARNING] /opt/shared/AGENT_WISDOM.md が見つかりません"
fi

# 現在の実行中サービス状態を注入
if [ -f /opt/shared/SHARED_STATE.md ]; then
    echo "--- SHARED_STATE (現在の状態) ---"
    cat /opt/shared/SHARED_STATE.md
fi

# KNOWN_MISTAKES サマリーを注入（VPSローカルコピー）
if [ -f /opt/KNOWN_MISTAKES_SUMMARY.md ]; then
    echo "--- KNOWN_MISTAKES サマリー ---"
    cat /opt/KNOWN_MISTAKES_SUMMARY.md
fi

echo "=== セッション開始完了 ==="
exit 0
'

if ! $DRY_RUN; then
    # NEO-ONE のhookディレクトリ
    ssh "$VPS" "mkdir -p /opt/claude-code-telegram/.claude/hooks"
    ssh "$VPS" "cat > /opt/claude-code-telegram/.claude/hooks/neo-session-start.sh << 'HOOKEOF'
$HOOK_CONTENT
HOOKEOF"
    ssh "$VPS" "chmod +x /opt/claude-code-telegram/.claude/hooks/neo-session-start.sh"
    log "NEO-ONE hook作成完了"

    # NEO-TWO のhookディレクトリ
    ssh "$VPS" "mkdir -p /opt/claude-code-telegram-neo2/.claude/hooks"
    ssh "$VPS" "cp /opt/claude-code-telegram/.claude/hooks/neo-session-start.sh \
        /opt/claude-code-telegram-neo2/.claude/hooks/neo-session-start.sh"
    log "NEO-TWO hook作成完了（NEO-ONEからコピー）"
else
    echo "  [DRY] /opt/claude-code-telegram/.claude/hooks/neo-session-start.sh を作成"
    echo "  [DRY] /opt/claude-code-telegram-neo2/.claude/hooks/neo-session-start.sh を作成"
fi

# ── Step2: NEO-ONE の settings.json に SessionStart hook を追加 ─────────────
log "Step2: NEO-ONE settings.json を更新..."

if ! $DRY_RUN; then
    # 既存のsettings.jsonを確認
    EXISTING=$(ssh "$VPS" "cat /opt/claude-code-telegram/.claude/settings.json 2>/dev/null || echo '{}'")

    # SessionStartが既に設定されているか確認
    if echo "$EXISTING" | grep -q "neo-session-start"; then
        warn "NEO-ONE: SessionStart hook は既に設定済みです（スキップ）"
    else
        # settings.jsonをPythonで更新（jsonの構造を壊さずに追加）
        ssh "$VPS" python3 << 'PYEOF'
import json
import os

settings_path = "/opt/claude-code-telegram/.claude/settings.json"

# 既存のsettings.jsonを読み込む（なければ空のオブジェクト）
if os.path.exists(settings_path):
    with open(settings_path, "r") as f:
        settings = json.load(f)
else:
    settings = {}

# hooks セクションを追加/更新
if "hooks" not in settings:
    settings["hooks"] = {}

if "SessionStart" not in settings["hooks"]:
    settings["hooks"]["SessionStart"] = []

# 重複チェック
existing_cmds = [h.get("command", "") for h in settings["hooks"]["SessionStart"]
                 for h in (h.get("hooks", [{}]))]
if not any("neo-session-start" in cmd for cmd in existing_cmds):
    settings["hooks"]["SessionStart"].append({
        "matcher": "",
        "hooks": [{
            "type": "command",
            "command": "bash /opt/claude-code-telegram/.claude/hooks/neo-session-start.sh",
            "timeout": 10
        }]
    })
    # バックアップ
    import shutil
    if os.path.exists(settings_path):
        shutil.copy(settings_path, settings_path + ".bak")
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    print("NEO-ONE settings.json 更新完了")
else:
    print("既に設定済み（スキップ）")
PYEOF
    fi
    log "NEO-ONE設定完了"
else
    echo "  [DRY] NEO-ONE /opt/claude-code-telegram/.claude/settings.json に SessionStart hook を追加"
fi

# ── Step3: NEO-TWO も同様に更新 ───────────────────────────────────────────────
log "Step3: NEO-TWO settings.json を更新..."

if ! $DRY_RUN; then
    ssh "$VPS" python3 << 'PYEOF'
import json
import os

settings_path = "/opt/claude-code-telegram-neo2/.claude/settings.json"

if os.path.exists(settings_path):
    with open(settings_path, "r") as f:
        settings = json.load(f)
else:
    settings = {}

if "hooks" not in settings:
    settings["hooks"] = {}
if "SessionStart" not in settings["hooks"]:
    settings["hooks"]["SessionStart"] = []

existing_cmds = [h.get("command", "") for h in settings["hooks"]["SessionStart"]
                 for h in (h.get("hooks", [{}]))]
if not any("neo-session-start" in cmd for cmd in existing_cmds):
    settings["hooks"]["SessionStart"].append({
        "matcher": "",
        "hooks": [{
            "type": "command",
            "command": "bash /opt/claude-code-telegram-neo2/.claude/hooks/neo-session-start.sh",
            "timeout": 10
        }]
    })
    import shutil
    if os.path.exists(settings_path):
        shutil.copy(settings_path, settings_path + ".bak")
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    print("NEO-TWO settings.json 更新完了")
else:
    print("既に設定済み（スキップ）")
PYEOF
    log "NEO-TWO設定完了"
else
    echo "  [DRY] NEO-TWO /opt/claude-code-telegram-neo2/.claude/settings.json に SessionStart hook を追加"
fi

# ── Step4: VPS グローバル Claude Code 設定（Opus削減）を適用 ────────────────────
log "Step4: VPS グローバル Claude Code 設定（Opus削減）を適用..."
# 効果: NEO-ONE/TWO/将来のNEO-N 全員に自動適用される
# 設定先: /root/.claude/settings.json（rootユーザーのグローバル設定）

if ! $DRY_RUN; then
    ssh "$VPS" python3 << 'PYEOF'
import json
import os

settings_path = "/root/.claude/settings.json"

if os.path.exists(settings_path):
    with open(settings_path, "r") as f:
        settings = json.load(f)
else:
    settings = {}

# env セクションを追加/更新（既存値を上書き）
if "env" not in settings:
    settings["env"] = {}

settings["env"]["DISABLE_NON_ESSENTIAL_MODEL_CALLS"] = "1"
settings["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] = "70"

# バックアップ
import shutil
if os.path.exists(settings_path):
    shutil.copy(settings_path, settings_path + ".bak")

# ディレクトリ作成（初回）
os.makedirs(os.path.dirname(settings_path), exist_ok=True)

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)

print("VPS グローバル設定更新完了:")
print("  DISABLE_NON_ESSENTIAL_MODEL_CALLS=1")
print("  CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70")
print("  適用先: NEO-ONE / NEO-TWO / 将来の全NEOインスタンス")
PYEOF
    log "VPS グローバル設定完了"
else
    echo "  [DRY] /root/.claude/settings.json に Opus削減設定を追加"
    echo "  [DRY]   DISABLE_NON_ESSENTIAL_MODEL_CALLS=1"
    echo "  [DRY]   CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70"
fi

# ── Step5: 動作確認（hook が実行可能か確認） ─────────────────────────────────
log "Step5: hookの動作確認..."
if ! $DRY_RUN; then
    OUTPUT=$(ssh "$VPS" "bash /opt/claude-code-telegram/.claude/hooks/neo-session-start.sh 2>&1 | head -20" || echo "ERROR")
    if echo "$OUTPUT" | grep -q "セッション開始完了"; then
        log "NEO-ONE hook 動作確認OK"
    else
        warn "hookの出力: $OUTPUT"
        warn "hookが正常に動作していない可能性があります。手動で確認してください。"
    fi
fi

echo ""
log "=== NEO VPS Hook デプロイ完了 ==="
echo "  NEO-ONE hook: /opt/claude-code-telegram/.claude/hooks/neo-session-start.sh"
echo "  NEO-TWO hook: /opt/claude-code-telegram-neo2/.claude/hooks/neo-session-start.sh"
echo "  VPS グローバル設定: /root/.claude/settings.json"
echo "  効果1: 次回のNEOセッション開始時からAGENT_WISDOM.md等が自動注入される"
echo "  効果2: NEO-ONE/TWO/将来の全NEOインスタンスでOpus削減設定が自動適用される"
echo "  ★ 新しいNEO-3/4を追加するたびに、このスクリプトを1回実行するだけでOK"
