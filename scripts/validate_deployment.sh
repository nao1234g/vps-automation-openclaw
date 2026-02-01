#!/bin/bash
#
# OpenClaw VPS - デプロイメント検証スクリプト
# デプロイ後にすべてのコンポーネントが正常に動作しているか確認
#
# 使用方法: ./scripts/validate_deployment.sh
#

set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# 検証カウンター
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# テスト実行関数
run_test() {
    local test_name="$1"
    local test_command="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if eval "$test_command" > /dev/null 2>&1; then
        log_success "$test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        log_error "$test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

echo "========================================="
echo "OpenClaw VPS デプロイメント検証"
echo "========================================="
echo ""

# ============================================
# 1. 環境変数チェック
# ============================================
log_info "1. 環境変数の確認"

if [ -f .env ]; then
    log_success ".env ファイルが存在します"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    log_error ".env ファイルが見つかりません"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 必須環境変数
source .env 2>/dev/null || true

required_vars=(
    "POSTGRES_PASSWORD"
    "ANTHROPIC_API_KEY"
    "TELEGRAM_BOT_TOKEN"
    "N8N_ENCRYPTION_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -n "${!var}" ]; then
        log_success "$var が設定されています"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_warn "$var が設定されていません"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
done

echo ""

# ============================================
# 2. Dockerサービスチェック
# ============================================
log_info "2. Dockerサービスの確認"

run_test "Docker がインストールされている" "docker --version"
run_test "Docker Compose がインストールされている" "docker compose version"
run_test "Docker サービスが実行中" "systemctl is-active docker"

echo ""

# ============================================
# 3. コンテナステータスチェック
# ============================================
log_info "3. コンテナステータスの確認"

COMPOSE_FILE="docker-compose.production.yml"

if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="docker-compose.yml"
fi

services=("postgres" "openclaw" "n8n" "opennotebook" "nginx")

for service in "${services[@]}"; do
    run_test "$service コンテナが実行中" \
        "docker compose -f $COMPOSE_FILE ps $service | grep -q 'running'"
done

echo ""

# ============================================
# 4. ヘルスチェック
# ============================================
log_info "4. ヘルスチェックの確認"

# PostgreSQL
run_test "PostgreSQL が応答" \
    "docker compose -f $COMPOSE_FILE exec -T postgres pg_isready -U openclaw"

# N8N
run_test "N8N が応答" \
    "docker compose -f $COMPOSE_FILE exec -T n8n wget --spider http://localhost:5678/healthz 2>&1 || true"

# OpenNotebook
run_test "OpenNotebook が応答" \
    "docker compose -f $COMPOSE_FILE exec -T opennotebook wget --spider http://localhost:8080/health 2>&1 || true"

# Nginx
run_test "Nginx が応答" \
    "docker compose -f $COMPOSE_FILE exec -T nginx wget --spider http://localhost/health 2>&1 || true"

echo ""

# ============================================
# 5. ネットワーク接続チェック
# ============================================
log_info "5. ネットワーク接続の確認"

run_test "Frontend ネットワークが存在" \
    "docker network ls | grep -q 'frontend'"

run_test "Backend ネットワークが存在" \
    "docker network ls | grep -q 'backend'"

echo ""

# ============================================
# 6. ボリュームチェック
# ============================================
log_info "6. ボリュームの確認"

volumes=("postgres_data" "openclaw_data" "n8n_data" "opennotebook_data")

for volume in "${volumes[@]}"; do
    run_test "$volume ボリュームが存在" \
        "docker volume ls | grep -q $volume"
done

echo ""

# ============================================
# 7. ポート接続チェック
# ============================================
log_info "7. ポート接続の確認"

run_test "ポート 80 が開いている" \
    "ss -tuln | grep -q ':80 '"

run_test "ポート 443 が開いている" \
    "ss -tuln | grep -q ':443 '"

echo ""

# ============================================
# 8. セキュリティチェック
# ============================================
log_info "8. セキュリティ設定の確認"

# UFW
if command -v ufw &> /dev/null; then
    run_test "UFW が有効" \
        "sudo ufw status | grep -q 'Status: active'"
else
    log_warn "UFW がインストールされていません"
fi

# Fail2ban
if command -v fail2ban-client &> /dev/null; then
    run_test "Fail2ban が実行中" \
        "sudo systemctl is-active fail2ban"
else
    log_warn "Fail2ban がインストールされていません"
fi

echo ""

# ============================================
# 9. ログチェック
# ============================================
log_info "9. ログの確認"

run_test "ログディレクトリが存在" \
    "[ -d logs ]"

run_test "PostgreSQL ログにエラーがない" \
    "! docker compose -f $COMPOSE_FILE logs postgres | grep -i 'ERROR' | grep -v 'pg_isready'"

echo ""

# ============================================
# 10. バックアップチェック
# ============================================
log_info "10. バックアップの確認"

if [ -d /opt/backups/openclaw ]; then
    backup_count=$(find /opt/backups/openclaw -type d -name "backup_*" 2>/dev/null | wc -l)
    if [ "$backup_count" -gt 0 ]; then
        log_success "バックアップが $backup_count 個存在します"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_warn "バックアップがまだ作成されていません"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    log_warn "バックアップディレクトリが存在しません"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo ""

# ============================================
# 結果サマリー
# ============================================
echo "========================================="
echo "検証結果サマリー"
echo "========================================="
echo ""
echo "総テスト数: $TOTAL_TESTS"
echo -e "${GREEN}成功: $PASSED_TESTS${NC}"
echo -e "${RED}失敗: $FAILED_TESTS${NC}"
echo ""

PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))

if [ "$PASS_RATE" -ge 90 ]; then
    echo -e "${GREEN}✓ デプロイメントは正常です（成功率: ${PASS_RATE}%）${NC}"
    exit 0
elif [ "$PASS_RATE" -ge 70 ]; then
    echo -e "${YELLOW}⚠ デプロイメントに一部問題があります（成功率: ${PASS_RATE}%）${NC}"
    exit 1
else
    echo -e "${RED}✗ デプロイメントに重大な問題があります（成功率: ${PASS_RATE}%）${NC}"
    exit 2
fi
