#!/bin/bash
#
# Backup Script
# VPSのデータベース、設定ファイル、ボリュームをバックアップ
#
# 使用方法: sudo ./backup.sh [オプション]
# オプション:
#   --full          完全バックアップ（デフォルト）
#   --db-only       データベースのみ
#   --volumes-only  Dockerボリュームのみ
#   --config-only   設定ファイルのみ
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

# プロジェクトディレクトリ
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# .envファイルの読み込み
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
else
    log_warn ".envファイルが見つかりません。デフォルト値を使用します。"
fi

# バックアップ設定
BACKUP_DIR=${BACKUP_DIR:-"/opt/backups/openclaw"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# バックアップタイプ
BACKUP_DB=true
BACKUP_VOLUMES=true
BACKUP_CONFIG=true

# コマンドライン引数の処理
while [[ $# -gt 0 ]]; do
    case $1 in
        --db-only)
            BACKUP_VOLUMES=false
            BACKUP_CONFIG=false
            shift
            ;;
        --volumes-only)
            BACKUP_DB=false
            BACKUP_CONFIG=false
            shift
            ;;
        --config-only)
            BACKUP_DB=false
            BACKUP_VOLUMES=false
            shift
            ;;
        --full)
            BACKUP_DB=true
            BACKUP_VOLUMES=true
            BACKUP_CONFIG=true
            shift
            ;;
        *)
            log_error "不明なオプション: $1"
            echo "使用方法: $0 [--full|--db-only|--volumes-only|--config-only]"
            exit 1
            ;;
    esac
done

log_info "=== バックアップ開始 ==="
log_info "日時: $(date)"
log_info "バックアップ先: $BACKUP_PATH"

# バックアップディレクトリの作成
mkdir -p "$BACKUP_PATH"

# ============================================
# データベースバックアップ
# ============================================
if [ "$BACKUP_DB" = true ]; then
    log_section "データベースバックアップ"

    DB_CONTAINER=$(docker ps --filter "name=db" --format "{{.Names}}" | head -1)

    if [ -z "$DB_CONTAINER" ]; then
        log_warn "データベースコンテナが見つかりません。スキップします。"
    else
        log_info "データベースコンテナ: $DB_CONTAINER"

        # PostgreSQLバックアップ
        DB_BACKUP_FILE="$BACKUP_PATH/database_${TIMESTAMP}.sql.gz"

        log_info "PostgreSQLをバックアップ中..."
        docker exec "$DB_CONTAINER" pg_dumpall -U "${POSTGRES_USER:-openclaw}" | gzip > "$DB_BACKUP_FILE"

        BACKUP_SIZE=$(du -h "$DB_BACKUP_FILE" | cut -f1)
        log_info "データベースバックアップ完了: $DB_BACKUP_FILE ($BACKUP_SIZE)"
    fi
fi

# ============================================
# Dockerボリュームバックアップ
# ============================================
if [ "$BACKUP_VOLUMES" = true ]; then
    log_section "Dockerボリュームバックアップ"

    VOLUMES=$(docker volume ls --format "{{.Name}}" | grep -E "(openclaw|n8n|opennotebook)" || true)

    if [ -z "$VOLUMES" ]; then
        log_warn "バックアップ対象のボリュームが見つかりません。"
    else
        mkdir -p "$BACKUP_PATH/volumes"

        for VOLUME in $VOLUMES; do
            log_info "ボリュームをバックアップ中: $VOLUME"

            VOLUME_BACKUP="$BACKUP_PATH/volumes/${VOLUME}_${TIMESTAMP}.tar.gz"

            docker run --rm \
                -v "$VOLUME":/source:ro \
                -v "$BACKUP_PATH/volumes":/backup \
                alpine \
                tar czf "/backup/${VOLUME}_${TIMESTAMP}.tar.gz" -C /source .

            VOLUME_SIZE=$(du -h "$VOLUME_BACKUP" | cut -f1)
            log_info "ボリュームバックアップ完了: $VOLUME ($VOLUME_SIZE)"
        done
    fi
fi

# ============================================
# 設定ファイルバックアップ
# ============================================
if [ "$BACKUP_CONFIG" = true ]; then
    log_section "設定ファイルバックアップ"

    CONFIG_BACKUP="$BACKUP_PATH/config_${TIMESTAMP}.tar.gz"

    log_info "設定ファイルをバックアップ中..."

    # バックアップ対象ファイル
    tar czf "$CONFIG_BACKUP" \
        -C "$PROJECT_DIR" \
        docker-compose.yml \
        .env.example \
        docker/ \
        scripts/ \
        --exclude="*.log" \
        --exclude="node_modules" \
        --exclude=".git" 2>/dev/null || true

    CONFIG_SIZE=$(du -h "$CONFIG_BACKUP" | cut -f1)
    log_info "設定ファイルバックアップ完了: $CONFIG_BACKUP ($CONFIG_SIZE)"
fi

# ============================================
# システム情報の保存
# ============================================
log_section "システム情報の保存"

SYSTEM_INFO="$BACKUP_PATH/system_info.txt"

{
    echo "=== バックアップ情報 ==="
    echo "日時: $(date)"
    echo "ホスト名: $(hostname)"
    echo "バックアップパス: $BACKUP_PATH"
    echo ""

    echo "=== Dockerコンテナ ==="
    docker ps -a
    echo ""

    echo "=== Dockerイメージ ==="
    docker images
    echo ""

    echo "=== Dockerボリューム ==="
    docker volume ls
    echo ""

    echo "=== Dockerネットワーク ==="
    docker network ls
    echo ""

    echo "=== システム情報 ==="
    uname -a
    echo ""

    echo "=== ディスク使用状況 ==="
    df -h
    echo ""

} > "$SYSTEM_INFO"

log_info "システム情報を保存しました: $SYSTEM_INFO"

# ============================================
# バックアップの検証
# ============================================
log_section "バックアップの検証"

BACKUP_TOTAL_SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)
FILE_COUNT=$(find "$BACKUP_PATH" -type f | wc -l)

log_info "バックアップサイズ: $BACKUP_TOTAL_SIZE"
log_info "ファイル数: $FILE_COUNT"

# ファイル一覧
log_info "バックアップファイル一覧:"
ls -lh "$BACKUP_PATH"

# ============================================
# 古いバックアップの削除
# ============================================
log_section "古いバックアップの削除"

log_info "${RETENTION_DAYS}日以上古いバックアップを削除中..."
DELETED_COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "backup_*" -mtime +${RETENTION_DAYS} -print -exec rm -rf {} \; | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    log_info "$DELETED_COUNT 個の古いバックアップを削除しました。"
else
    log_info "削除対象のバックアップはありません。"
fi

# ============================================
# リモートバックアップ（オプション）
# ============================================
if [ ! -z "${AWS_S3_BUCKET}" ]; then
    log_section "S3へのアップロード"

    if command -v aws &> /dev/null; then
        log_info "S3バケットにアップロード中: ${AWS_S3_BUCKET}"

        ARCHIVE_NAME="${BACKUP_NAME}.tar.gz"
        tar czf "/tmp/${ARCHIVE_NAME}" -C "$BACKUP_DIR" "$BACKUP_NAME"

        aws s3 cp "/tmp/${ARCHIVE_NAME}" "s3://${AWS_S3_BUCKET}/backups/${ARCHIVE_NAME}"

        rm "/tmp/${ARCHIVE_NAME}"

        log_info "S3アップロード完了"
    else
        log_warn "AWS CLIがインストールされていません。S3アップロードをスキップします。"
    fi
fi

# ============================================
# 完了
# ============================================
log_section "バックアップ完了"

echo ""
echo "バックアップサマリー:"
echo "===================="
echo "バックアップ場所: $BACKUP_PATH"
echo "総サイズ: $BACKUP_TOTAL_SIZE"
echo "ファイル数: $FILE_COUNT"
echo ""
echo "復元方法:"
echo "  sudo ./scripts/restore.sh $BACKUP_PATH"
echo ""
echo "バックアップ一覧:"
ls -lht "$BACKUP_DIR" | head -10
echo ""

log_info "バックアップが正常に完了しました。"
