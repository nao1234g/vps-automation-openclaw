#!/bin/bash
#
# Cron Jobs Setup Script
# セキュリティスキャンとメンテナンスの自動化設定
#
# 使用方法: sudo ./setup_cron_jobs.sh
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

# rootユーザーチェック
if [ "$EUID" -ne 0 ]; then
    log_error "このスクリプトはroot権限で実行してください。"
    echo "使用方法: sudo $0"
    exit 1
fi

log_info "=== Cronジョブ自動化セットアップ開始 ==="

# スクリプトディレクトリの取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

log_info "プロジェクトディレクトリ: $PROJECT_DIR"

# スクリプトの実行可能確認
log_info "スクリプトの実行権限を確認中..."
chmod +x "$SCRIPT_DIR/security_scan.sh"
chmod +x "$SCRIPT_DIR/maintenance.sh"

# ログディレクトリの作成
LOG_DIR="/var/log/vps-automation"
mkdir -p "$LOG_DIR"

log_info "ログディレクトリ: $LOG_DIR"

# Cronジョブの定義
CRON_FILE="/etc/cron.d/vps-automation"

log_info "Cronジョブファイルを作成中: $CRON_FILE"

cat > "$CRON_FILE" <<EOF
# VPS Automation - セキュリティとメンテナンスの自動化
# このファイルは自動生成されました: $(date)

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=root

# ========================================
# セキュリティスキャン
# ========================================

# 毎週日曜日 2:00 AM - 完全なセキュリティスキャン
0 2 * * 0 root $SCRIPT_DIR/security_scan.sh --all >> $LOG_DIR/security_scan.log 2>&1

# 毎日 4:00 AM - イメージスキャンのみ（軽量）
0 4 * * 1-6 root $SCRIPT_DIR/security_scan.sh --images-only >> $LOG_DIR/security_scan_daily.log 2>&1

# ========================================
# システムメンテナンス
# ========================================

# 毎月1日 3:00 AM - 完全メンテナンス
0 3 1 * * root $SCRIPT_DIR/maintenance.sh >> $LOG_DIR/maintenance.log 2>&1

# 毎週日曜日 3:30 AM - ライトメンテナンス
30 3 * * 0 root $SCRIPT_DIR/maintenance.sh --dry-run >> $LOG_DIR/maintenance_dry.log 2>&1

# ========================================
# ログローテーション
# ========================================

# 毎月15日 1:00 AM - 古いログの削除（90日以上）
0 1 15 * * root find $LOG_DIR -name "*.log" -mtime +90 -delete

# ========================================
# Dockerクリーンアップ
# ========================================

# 毎週月曜日 1:00 AM - 未使用Dockerリソースのクリーンアップ
0 1 * * 1 root /usr/bin/docker system prune -f >> $LOG_DIR/docker_prune.log 2>&1

# ========================================
# システムアップデート確認
# ========================================

# 毎日 5:00 AM - アップデート可能パッケージの確認
0 5 * * * root apt update && apt list --upgradable > $LOG_DIR/updates_available.log 2>&1

EOF

# Cronファイルのパーミッション設定
chmod 644 "$CRON_FILE"

log_info "Cronジョブファイルを作成しました。"

# Cronサービスの再起動
log_info "Cronサービスを再起動中..."
systemctl restart cron

# 設定されたCronジョブの表示
log_info "=== 設定されたCronジョブ ==="
cat "$CRON_FILE"

echo ""
log_info "=== Cronジョブセットアップ完了 ==="

echo ""
echo "スケジュール概要:"
echo "=================="
echo "毎日:"
echo "  - 4:00 AM   セキュリティスキャン（イメージのみ）"
echo "  - 5:00 AM   アップデート確認"
echo ""
echo "毎週:"
echo "  - 日曜 2:00 AM    完全セキュリティスキャン"
echo "  - 日曜 3:30 AM    メンテナンスドライラン"
echo "  - 月曜 1:00 AM    Dockerクリーンアップ"
echo ""
echo "毎月:"
echo "  - 1日  3:00 AM    完全メンテナンス"
echo "  - 15日 1:00 AM    古いログ削除"
echo ""

log_info "ログファイル保存先: $LOG_DIR"
echo ""
echo "手動でCronジョブを確認:"
echo "  cat $CRON_FILE"
echo ""
echo "ログを確認:"
echo "  tail -f $LOG_DIR/security_scan.log"
echo "  tail -f $LOG_DIR/maintenance.log"
echo ""

# テストモード（オプション）
read -p "今すぐセキュリティスキャンをテスト実行しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "セキュリティスキャンをテスト実行中..."
    "$SCRIPT_DIR/security_scan.sh" --system-only
fi

log_info "Cronジョブのセットアップが完了しました。"
