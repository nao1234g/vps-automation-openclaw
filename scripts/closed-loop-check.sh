#!/bin/bash
# =============================================================================
# CLOSED LOOP CHECK — VPS pipeline health monitor
# =============================================================================
# OPERATING_PRINCIPLES 閉ループ設計原則の実装:
#   [観測] → [判断] → [実行] → [検証] → [記録] → [改善]
#
# 実行: VPS cron で毎時 or 手動で実行
# 用途: パイプライン稼働確認 → 異常時Telegram通知
# =============================================================================
set -e

VPS_USER="root"
VPS_HOST="163.44.124.123"

# ─── VPS上で実行するチェックスクリプト ───
ssh -o ConnectTimeout=10 -o BatchMode=yes "${VPS_USER}@${VPS_HOST}" << 'REMOTE_SCRIPT'
#!/bin/bash

TELEGRAM_TOKEN=$(grep TELEGRAM_BOT_TOKEN /opt/cron-env.sh 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'")
TELEGRAM_CHAT_ID=$(grep TELEGRAM_CHAT_ID /opt/cron-env.sh 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'")
SHARED_DIR="/opt/shared"
REPORTS_DIR="${SHARED_DIR}/reports"
LOG_DIR="${SHARED_DIR}/logs"
NOW=$(date '+%Y-%m-%d %H:%M JST' --date='+9 hours')
DATE_TODAY=$(date '+%Y-%m-%d' --date='+9 hours')

ISSUES=""
CHECKS_PASSED=0
CHECKS_FAILED=0

send_telegram() {
    local msg="$1"
    if [ -n "$TELEGRAM_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${msg}" \
            -d "parse_mode=Markdown" > /dev/null 2>&1
    fi
}

check_pass() { CHECKS_PASSED=$((CHECKS_PASSED + 1)); }
check_fail() { CHECKS_FAILED=$((CHECKS_FAILED + 1)); ISSUES="${ISSUES}\n❌ $1"; }

# ── [観測] 1: Hey Loop が今日実行されたか ──
LEARNING_LOG="${LOG_DIR}/daily-learning.log"
if [ -f "$LEARNING_LOG" ]; then
    if grep -q "$DATE_TODAY" "$LEARNING_LOG" 2>/dev/null; then
        check_pass
    else
        check_fail "Hey Loop が今日未実行 (last log: $(tail -1 $LEARNING_LOG 2>/dev/null | head -c 30))"
    fi
else
    check_fail "Hey Loop ログファイルが存在しない: $LEARNING_LOG"
fi

# ── [観測] 2: news-analyst-pipeline が今日実行されたか ──
ANALYST_LOG="${LOG_DIR}/news-analyst.log"
if [ -f "$ANALYST_LOG" ]; then
    if grep -q "$DATE_TODAY" "$ANALYST_LOG" 2>/dev/null; then
        check_pass
    else
        check_fail "news-analyst-pipeline が今日未実行"
    fi
else
    # logがない場合はreportsディレクトリで確認
    if ls "${REPORTS_DIR}/${DATE_TODAY}"*.md 2>/dev/null | head -1 > /dev/null; then
        check_pass
    else
        check_fail "news-analyst-pipeline: 今日のレポートが存在しない"
    fi
fi

# ── [観測] 3: NEO-ONE サービス稼働確認 ──
if systemctl is-active --quiet neo-telegram.service 2>/dev/null; then
    check_pass
else
    check_fail "NEO-ONE (neo-telegram.service) が停止中"
fi

# ── [観測] 4: Ghost CMS 稼働確認 ──
if systemctl is-active --quiet ghost-nowpattern.service 2>/dev/null; then
    check_pass
else
    check_fail "Ghost CMS (ghost-nowpattern.service) が停止中"
fi

# ── [観測] 5: OpenClaw コンテナ稼働確認 ──
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "openclaw-agent"; then
    check_pass
else
    check_fail "openclaw-agent コンテナが停止中"
fi

# ── [観測] 6: ディスク使用率チェック ──
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 80 ]; then
    check_pass
else
    check_fail "ディスク使用率が ${DISK_USAGE}% (80%超)"
fi

# ── [判断] 異常があればTelegram通知 ──
if [ $CHECKS_FAILED -gt 0 ]; then
    MSG="🔴 *閉ループ異常検知* (${NOW})

チェック結果: ${CHECKS_PASSED}✅ / ${CHECKS_FAILED}❌

$(echo -e "$ISSUES")

→ VPSを確認してください: \`ssh root@163.44.124.123\`"
    send_telegram "$MSG"
    echo "[$(date)] ALERT: ${CHECKS_FAILED} issues found" >> "${LOG_DIR}/closed-loop-check.log" 2>/dev/null || true
    echo "❌ ALERT sent: ${CHECKS_FAILED} issues"
    exit 1
else
    echo "✅ All ${CHECKS_PASSED} checks passed at ${NOW}"
    # 正常時は6時間おきにサマリー通知（07:00 JSTのみ詳細を送る）
    HOUR=$(date '+%H' --date='+9 hours')
    if [ "$HOUR" = "07" ]; then
        MSG="✅ *システム正常* (${NOW})

全 ${CHECKS_PASSED} チェックをパス:
• Hey Loop: 稼働中
• news-analyst: 稼働中
• NEO-ONE: 稼働中
• Ghost CMS: 稼働中
• OpenClaw: 稼働中
• Disk: ${DISK_USAGE}% 使用"
        send_telegram "$MSG"
    fi
fi

REMOTE_SCRIPT

echo "Closed loop check completed."
