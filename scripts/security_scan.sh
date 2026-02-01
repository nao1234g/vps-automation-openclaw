#!/bin/bash
#
# Security Scan Script
# Docker イメージとシステムのセキュリティスキャンを実行
#
# 使用方法: ./security_scan.sh [オプション]
# オプション:
#   --images-only    イメージスキャンのみ実行
#   --system-only    システム監査のみ実行
#   --all           全てのスキャンを実行（デフォルト）
#

set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ出力関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# デフォルト設定
SCAN_IMAGES=true
SCAN_SYSTEM=true
REPORT_DIR="./security-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# コマンドライン引数の処理
while [[ $# -gt 0 ]]; do
    case $1 in
        --images-only)
            SCAN_SYSTEM=false
            shift
            ;;
        --system-only)
            SCAN_IMAGES=false
            shift
            ;;
        --all)
            SCAN_IMAGES=true
            SCAN_SYSTEM=true
            shift
            ;;
        *)
            log_error "不明なオプション: $1"
            echo "使用方法: $0 [--images-only|--system-only|--all]"
            exit 1
            ;;
    esac
done

# レポートディレクトリの作成
mkdir -p "$REPORT_DIR"

log_info "=== セキュリティスキャン開始 ==="
log_info "日時: $(date)"
log_info "レポート保存先: $REPORT_DIR"

# ============================================
# Dockerイメージの脆弱性スキャン
# ============================================
if [ "$SCAN_IMAGES" = true ]; then
    log_section "Dockerイメージの脆弱性スキャン"

    # Trivyの存在確認
    if ! command -v trivy &> /dev/null; then
        log_error "Trivyがインストールされていません。"
        log_info "インストール方法: sudo ./setup_docker_security.sh"
        exit 1
    fi

    # Trivyデータベースの更新
    log_info "Trivyデータベースを更新中..."
    trivy image --download-db-only

    # 実行中のコンテナのイメージをスキャン
    log_info "実行中のコンテナイメージをスキャン中..."
    RUNNING_IMAGES=$(docker ps --format "{{.Image}}" | sort -u)

    if [ -z "$RUNNING_IMAGES" ]; then
        log_warn "実行中のコンテナがありません。"
    else
        for IMAGE in $RUNNING_IMAGES; do
            log_info "スキャン中: $IMAGE"

            REPORT_FILE="$REPORT_DIR/trivy_${IMAGE//\//_}_${TIMESTAMP}.txt"

            # 詳細スキャン実行
            trivy image \
                --severity HIGH,CRITICAL \
                --format table \
                "$IMAGE" | tee "$REPORT_FILE"

            # JSON形式でも保存
            trivy image \
                --severity HIGH,CRITICAL \
                --format json \
                --output "$REPORT_DIR/trivy_${IMAGE//\//_}_${TIMESTAMP}.json" \
                "$IMAGE"

            log_info "レポート保存: $REPORT_FILE"
        done
    fi

    # ローカルイメージ全体のスキャン（オプション）
    log_info "ローカルイメージの一覧をスキャン..."
    docker images --format "{{.Repository}}:{{.Tag}}" | grep -v "<none>" | head -10 | while read IMAGE; do
        log_info "クイックスキャン: $IMAGE"
        trivy image --severity CRITICAL --format table "$IMAGE" || true
    done
fi

# ============================================
# Docker Benchセキュリティ監査
# ============================================
if [ "$SCAN_SYSTEM" = true ]; then
    log_section "Docker Bench Securityによるシステム監査"

    DOCKER_BENCH_PATH="/opt/docker-bench-security/docker-bench-security.sh"

    if [ -f "$DOCKER_BENCH_PATH" ]; then
        log_info "Docker Bench Securityを実行中..."

        BENCH_REPORT="$REPORT_DIR/docker-bench_${TIMESTAMP}.log"

        sudo "$DOCKER_BENCH_PATH" | tee "$BENCH_REPORT"

        log_info "Docker Benchレポート保存: $BENCH_REPORT"
    else
        log_warn "Docker Bench Securityが見つかりません。"
        log_info "インストール方法: sudo ./setup_docker_security.sh"
    fi
fi

# ============================================
# システムセキュリティチェック
# ============================================
if [ "$SCAN_SYSTEM" = true ]; then
    log_section "システムセキュリティチェック"

    SYSTEM_REPORT="$REPORT_DIR/system-check_${TIMESTAMP}.txt"

    {
        echo "=== システムセキュリティレポート ==="
        echo "日時: $(date)"
        echo ""

        echo "--- UFWステータス ---"
        sudo ufw status verbose || echo "UFWが無効です"
        echo ""

        echo "--- Fail2banステータス ---"
        sudo fail2ban-client status || echo "Fail2banが実行されていません"
        echo ""

        echo "--- SSH設定チェック ---"
        echo "PermitRootLogin:"
        grep "^PermitRootLogin" /etc/ssh/sshd_config || echo "設定なし"
        echo "PasswordAuthentication:"
        grep "^PasswordAuthentication" /etc/ssh/sshd_config || echo "設定なし"
        echo ""

        echo "--- 開いているポート ---"
        sudo ss -tuln
        echo ""

        echo "--- 実行中のDockerコンテナ ---"
        docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
        echo ""

        echo "--- Dockerネットワーク ---"
        docker network ls
        echo ""

        echo "--- システムアップデート状況 ---"
        apt list --upgradable 2>/dev/null | head -20
        echo ""

    } | tee "$SYSTEM_REPORT"

    log_info "システムレポート保存: $SYSTEM_REPORT"
fi

# ============================================
# サマリー表示
# ============================================
log_section "スキャン完了"

echo ""
echo "生成されたレポート:"
ls -lh "$REPORT_DIR"/*_${TIMESTAMP}* 2>/dev/null || echo "レポートがありません"

echo ""
log_info "次のステップ:"
echo "1. レポートを確認してHIGH/CRITICAL脆弱性に対処"
echo "2. Docker Benchの警告を確認して設定を改善"
echo "3. 定期的にスキャンを実行（cron推奨）"
echo ""
log_info "セキュリティスキャンが完了しました。"
