#!/bin/bash
#
# Health Check Script
# システム全体の健全性をチェック
#
# 使用方法: ./health_check.sh
#

set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# チェック結果カウンター
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

# ログ出力関数
log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS_COUNT++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARN_COUNT++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL_COUNT++))
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# プロジェクトディレクトリ
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

log_info "=== システムヘルスチェック開始 ==="
log_info "日時: $(date)"

# ============================================
# システムリソース
# ============================================
log_section "システムリソース"

# ディスク使用率
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
log_info "ディスク使用率: ${DISK_USAGE}%"

if [ "$DISK_USAGE" -lt 70 ]; then
    log_pass "ディスク使用率が正常範囲内 (${DISK_USAGE}% < 70%)"
elif [ "$DISK_USAGE" -lt 85 ]; then
    log_warn "ディスク使用率が高め (${DISK_USAGE}%)"
else
    log_fail "ディスク使用率が危険 (${DISK_USAGE}% >= 85%)"
fi

# メモリ使用率
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
log_info "メモリ使用率: ${MEMORY_USAGE}%"

if [ "$MEMORY_USAGE" -lt 80 ]; then
    log_pass "メモリ使用率が正常範囲内 (${MEMORY_USAGE}% < 80%)"
elif [ "$MEMORY_USAGE" -lt 90 ]; then
    log_warn "メモリ使用率が高め (${MEMORY_USAGE}%)"
else
    log_fail "メモリ使用率が危険 (${MEMORY_USAGE}% >= 90%)"
fi

# CPU負荷
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
log_info "CPU負荷 (1分平均): $LOAD_AVG"

# ============================================
# セキュリティ
# ============================================
log_section "セキュリティ"

# UFW
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        log_pass "UFWファイアウォールが有効"
    else
        log_fail "UFWファイアウォールが無効"
    fi
else
    log_warn "UFWがインストールされていません"
fi

# Fail2ban
if command -v fail2ban-client &> /dev/null; then
    if sudo fail2ban-client status &> /dev/null; then
        log_pass "Fail2banが実行中"
    else
        log_fail "Fail2banが停止中"
    fi
else
    log_warn "Fail2banがインストールされていません"
fi

# SSH設定
if [ -f /etc/ssh/sshd_config ]; then
    if grep -q "^PermitRootLogin no" /etc/ssh/sshd_config; then
        log_pass "SSHでのrootログインが無効"
    else
        log_warn "SSHでのrootログインが有効"
    fi

    if grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config; then
        log_pass "SSHパスワード認証が無効"
    else
        log_warn "SSHパスワード認証が有効"
    fi
fi

# ============================================
# Docker
# ============================================
log_section "Docker"

# Dockerサービス
if systemctl is-active --quiet docker; then
    log_pass "Dockerサービスが実行中"
else
    log_fail "Dockerサービスが停止中"
fi

# Dockerコンテナ
if command -v docker &> /dev/null; then
    RUNNING_CONTAINERS=$(docker ps -q | wc -l)
    TOTAL_CONTAINERS=$(docker ps -a -q | wc -l)

    log_info "実行中のコンテナ: $RUNNING_CONTAINERS / $TOTAL_CONTAINERS"

    if [ "$RUNNING_CONTAINERS" -gt 0 ]; then
        log_pass "コンテナが実行中"

        # 各コンテナのステータス
        docker ps --format "table {{.Names}}\t{{.Status}}" | while read line; do
            if echo "$line" | grep -q "Up"; then
                CONTAINER_NAME=$(echo "$line" | awk '{print $1}')
                if [ "$CONTAINER_NAME" != "NAMES" ]; then
                    log_info "  ✓ $CONTAINER_NAME"
                fi
            fi
        done
    else
        log_warn "実行中のコンテナがありません"
    fi

    # 停止中のコンテナ
    STOPPED_CONTAINERS=$(docker ps -a -f status=exited -q | wc -l)
    if [ "$STOPPED_CONTAINERS" -gt 0 ]; then
        log_warn "$STOPPED_CONTAINERS 個の停止中コンテナ"
    fi

    # Dockerボリューム
    VOLUMES=$(docker volume ls -q | wc -l)
    log_info "Dockerボリューム数: $VOLUMES"
fi

# ============================================
# ネットワーク
# ============================================
log_section "ネットワーク"

# 外部接続
if ping -c 1 8.8.8.8 &> /dev/null; then
    log_pass "外部ネットワーク接続OK"
else
    log_fail "外部ネットワーク接続失敗"
fi

# DNS解決
if nslookup google.com &> /dev/null; then
    log_pass "DNS解決OK"
else
    log_fail "DNS解決失敗"
fi

# ポート80/443
if ss -tuln | grep -q ":80 "; then
    log_pass "ポート80が開いています"
else
    log_warn "ポート80が開いていません"
fi

if ss -tuln | grep -q ":443 "; then
    log_pass "ポート443が開いています"
else
    log_warn "ポート443が開いていません"
fi

# ============================================
# SSL証明書
# ============================================
log_section "SSL証明書"

SSL_DIR="$PROJECT_DIR/docker/nginx/ssl"

if [ -f "$SSL_DIR/fullchain.pem" ]; then
    log_pass "SSL証明書が存在します"

    # 証明書の有効期限
    EXPIRY_DATE=$(openssl x509 -in "$SSL_DIR/fullchain.pem" -noout -enddate | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
    CURRENT_EPOCH=$(date +%s)
    DAYS_LEFT=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

    log_info "証明書の有効期限: $EXPIRY_DATE ($DAYS_LEFT 日後)"

    if [ "$DAYS_LEFT" -gt 30 ]; then
        log_pass "証明書は有効 (残り ${DAYS_LEFT} 日)"
    elif [ "$DAYS_LEFT" -gt 7 ]; then
        log_warn "証明書の有効期限が近い (残り ${DAYS_LEFT} 日)"
    else
        log_fail "証明書の有効期限が切迫 (残り ${DAYS_LEFT} 日)"
    fi
else
    log_warn "SSL証明書が見つかりません"
fi

# ============================================
# バックアップ
# ============================================
log_section "バックアップ"

BACKUP_DIR=${BACKUP_DIR:-"/opt/backups/openclaw"}

if [ -d "$BACKUP_DIR" ]; then
    BACKUP_COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "backup_*" | wc -l)
    log_info "バックアップ数: $BACKUP_COUNT"

    if [ "$BACKUP_COUNT" -gt 0 ]; then
        LATEST_BACKUP=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "backup_*" | sort -r | head -1)
        BACKUP_AGE=$(( ($(date +%s) - $(stat -c %Y "$LATEST_BACKUP")) / 86400 ))

        log_info "最新バックアップ: $(basename $LATEST_BACKUP) (${BACKUP_AGE} 日前)"

        if [ "$BACKUP_AGE" -le 1 ]; then
            log_pass "最近のバックアップが存在 (${BACKUP_AGE} 日前)"
        elif [ "$BACKUP_AGE" -le 7 ]; then
            log_warn "バックアップが古い (${BACKUP_AGE} 日前)"
        else
            log_fail "バックアップが非常に古い (${BACKUP_AGE} 日前)"
        fi
    else
        log_warn "バックアップが見つかりません"
    fi
else
    log_warn "バックアップディレクトリが見つかりません"
fi

# ============================================
# ログ
# ============================================
log_section "ログ"

# システムログのエラー
ERROR_COUNT=$(sudo journalctl -p err -S today --no-pager | wc -l)
log_info "本日のシステムエラー数: $ERROR_COUNT"

if [ "$ERROR_COUNT" -eq 0 ]; then
    log_pass "システムエラーなし"
elif [ "$ERROR_COUNT" -lt 10 ]; then
    log_warn "少数のシステムエラー (${ERROR_COUNT} 件)"
else
    log_fail "多数のシステムエラー (${ERROR_COUNT} 件)"
fi

# ============================================
# サマリー
# ============================================
log_section "ヘルスチェック サマリー"

TOTAL_CHECKS=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))

echo ""
echo "チェック結果:"
echo "===================="
echo -e "${GREEN}PASS: $PASS_COUNT${NC} / $TOTAL_CHECKS"
echo -e "${YELLOW}WARN: $WARN_COUNT${NC} / $TOTAL_CHECKS"
echo -e "${RED}FAIL: $FAIL_COUNT${NC} / $TOTAL_CHECKS"
echo ""

# 総合判定
if [ "$FAIL_COUNT" -eq 0 ] && [ "$WARN_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ システムは完全に健全です${NC}"
    exit 0
elif [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠ システムは概ね健全ですが、警告があります${NC}"
    exit 0
else
    echo -e "${RED}✗ システムに問題があります。早急な対応が必要です${NC}"
    exit 1
fi
