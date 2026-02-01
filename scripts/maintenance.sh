#!/bin/bash
#
# VPS & Docker Maintenance Script
# VPSとDockerの定期メンテナンスを自動化
#
# 使用方法: sudo ./maintenance.sh [オプション]
# オプション:
#   --dry-run       実際の削除を行わず、プレビューのみ
#   --aggressive    より積極的なクリーンアップ
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

# rootユーザーチェック
if [ "$EUID" -ne 0 ]; then
    log_error "このスクリプトはroot権限で実行してください。"
    echo "使用方法: sudo $0"
    exit 1
fi

# デフォルト設定
DRY_RUN=false
AGGRESSIVE=false

# コマンドライン引数の処理
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --aggressive)
            AGGRESSIVE=true
            shift
            ;;
        *)
            log_error "不明なオプション: $1"
            echo "使用方法: $0 [--dry-run] [--aggressive]"
            exit 1
            ;;
    esac
done

if [ "$DRY_RUN" = true ]; then
    log_warn "ドライランモード: 実際の削除は行いません"
fi

log_info "=== VPS & Docker メンテナンス開始 ==="
log_info "日時: $(date)"

# ============================================
# システムアップデート
# ============================================
log_section "システムアップデート"

log_info "パッケージリストを更新中..."
apt update

log_info "アップグレード可能なパッケージを確認中..."
UPGRADABLE=$(apt list --upgradable 2>/dev/null | grep -v "Listing" | wc -l)

if [ "$UPGRADABLE" -gt 0 ]; then
    log_info "$UPGRADABLE 個のパッケージがアップグレード可能です"

    if [ "$DRY_RUN" = false ]; then
        log_info "パッケージをアップグレード中..."
        apt upgrade -y
        log_info "アップグレード完了"
    else
        log_info "ドライランモード: アップグレードをスキップ"
        apt list --upgradable 2>/dev/null | head -20
    fi
else
    log_info "全てのパッケージは最新です"
fi

# ============================================
# Dockerクリーンアップ
# ============================================
log_section "Dockerリソースのクリーンアップ"

log_info "Dockerディスク使用状況:"
docker system df

# 停止中のコンテナの削除
log_info "停止中のコンテナを確認中..."
STOPPED_CONTAINERS=$(docker ps -aq -f status=exited)

if [ -n "$STOPPED_CONTAINERS" ]; then
    CONTAINER_COUNT=$(echo "$STOPPED_CONTAINERS" | wc -l)
    log_info "$CONTAINER_COUNT 個の停止中のコンテナがあります"

    if [ "$DRY_RUN" = false ]; then
        log_info "停止中のコンテナを削除中..."
        docker container prune -f
    else
        log_info "ドライランモード: 以下のコンテナが削除されます"
        docker ps -a -f status=exited
    fi
else
    log_info "停止中のコンテナはありません"
fi

# 未使用のイメージの削除
log_info "未使用のイメージを確認中..."
DANGLING_IMAGES=$(docker images -f "dangling=true" -q)

if [ -n "$DANGLING_IMAGES" ]; then
    IMAGE_COUNT=$(echo "$DANGLING_IMAGES" | wc -l)
    log_info "$IMAGE_COUNT 個の未使用イメージがあります"

    if [ "$DRY_RUN" = false ]; then
        log_info "未使用イメージを削除中..."
        docker image prune -f
    else
        log_info "ドライランモード: 以下のイメージが削除されます"
        docker images -f "dangling=true"
    fi
else
    log_info "未使用イメージはありません"
fi

# より積極的なクリーンアップ
if [ "$AGGRESSIVE" = true ]; then
    log_warn "積極的なクリーンアップモード"

    if [ "$DRY_RUN" = false ]; then
        log_info "全ての未使用リソースを削除中..."
        docker system prune -a --volumes -f
    else
        log_info "ドライランモード: 全ての未使用リソースが削除されます"
        docker system df
    fi
fi

# ============================================
# ログのローテーションとクリーンアップ
# ============================================
log_section "ログファイルのクリーンアップ"

log_info "古いログファイルを確認中..."

# journalログのクリーンアップ（30日以上古いログ）
if [ "$DRY_RUN" = false ]; then
    log_info "journalログをクリーンアップ中..."
    journalctl --vacuum-time=30d
else
    log_info "ドライランモード: journalログのサイズ"
    journalctl --disk-usage
fi

# Dockerコンテナログのサイズ確認
log_info "Dockerコンテナログのサイズを確認中..."
CONTAINER_LOGS=$(find /var/lib/docker/containers -name "*-json.log" -type f 2>/dev/null)

if [ -n "$CONTAINER_LOGS" ]; then
    echo "$CONTAINER_LOGS" | xargs du -h 2>/dev/null | sort -rh | head -10
else
    log_info "コンテナログが見つかりません"
fi

# ============================================
# ディスク使用状況の確認
# ============================================
log_section "ディスク使用状況"

df -h | grep -E "(Filesystem|/dev/)"

log_info "最も容量を使用しているディレクトリ（トップ10）:"
du -sh /* 2>/dev/null | sort -rh | head -10

# ============================================
# セキュリティチェック
# ============================================
log_section "セキュリティステータス"

log_info "UFWステータス:"
ufw status | head -20

log_info "Fail2banステータス:"
fail2ban-client status 2>/dev/null || log_warn "Fail2banが実行されていません"

log_info "最近のSSH失敗ログイン試行:"
grep "Failed password" /var/log/auth.log 2>/dev/null | tail -10 || log_info "ログなし"

# ============================================
# 不要なカーネルの削除
# ============================================
if [ "$AGGRESSIVE" = true ]; then
    log_section "古いカーネルのクリーンアップ"

    CURRENT_KERNEL=$(uname -r)
    log_info "現在のカーネル: $CURRENT_KERNEL"

    if [ "$DRY_RUN" = false ]; then
        log_info "古いカーネルを削除中..."
        apt autoremove -y --purge
    else
        log_info "ドライランモード: 以下のパッケージが削除されます"
        apt autoremove --dry-run
    fi
fi

# ============================================
# サマリー
# ============================================
log_section "メンテナンス完了"

echo ""
log_info "最終ディスク使用状況:"
df -h | grep -E "(Filesystem|/dev/)"

echo ""
log_info "Docker最終状態:"
docker system df

echo ""
log_info "次のステップ:"
echo "1. セキュリティスキャンを実行: ./security_scan.sh"
echo "2. ログを確認して異常がないか確認"
echo "3. 重要なデータのバックアップを確認"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_warn "ドライランモードでした。実際のクリーンアップを行うには --dry-run オプションなしで実行してください"
fi

log_info "メンテナンスが完了しました。"
