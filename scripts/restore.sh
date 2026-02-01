#!/bin/bash
#
# Restore Script
# バックアップからデータを復元
#
# 使用方法: sudo ./restore.sh <バックアップディレクトリ> [オプション]
# オプション:
#   --db-only       データベースのみ復元
#   --volumes-only  Dockerボリュームのみ復元
#   --config-only   設定ファイルのみ復元
#   --force         確認なしで実行
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
    echo "使用方法: sudo $0 <バックアップディレクトリ>"
    exit 1
fi

# 引数チェック
if [ -z "$1" ]; then
    log_error "バックアップディレクトリを指定してください。"
    echo "使用方法: sudo $0 <バックアップディレクトリ>"
    exit 1
fi

BACKUP_PATH="$1"
shift

# バックアップディレクトリの存在確認
if [ ! -d "$BACKUP_PATH" ]; then
    log_error "バックアップディレクトリが見つかりません: $BACKUP_PATH"
    exit 1
fi

# プロジェクトディレクトリ
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# .envファイルの読み込み
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
fi

# 復元タイプ
RESTORE_DB=true
RESTORE_VOLUMES=true
RESTORE_CONFIG=true
FORCE=false

# コマンドライン引数の処理
while [[ $# -gt 0 ]]; do
    case $1 in
        --db-only)
            RESTORE_VOLUMES=false
            RESTORE_CONFIG=false
            shift
            ;;
        --volumes-only)
            RESTORE_DB=false
            RESTORE_CONFIG=false
            shift
            ;;
        --config-only)
            RESTORE_DB=false
            RESTORE_VOLUMES=false
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            log_error "不明なオプション: $1"
            echo "使用方法: $0 <バックアップディレクトリ> [--db-only|--volumes-only|--config-only] [--force]"
            exit 1
            ;;
    esac
done

log_info "=== 復元開始 ==="
log_info "バックアップ元: $BACKUP_PATH"

# バックアップ情報の表示
if [ -f "$BACKUP_PATH/system_info.txt" ]; then
    log_info "バックアップ情報:"
    head -10 "$BACKUP_PATH/system_info.txt"
fi

# 確認
if [ "$FORCE" = false ]; then
    log_warn "⚠️ 警告: 既存のデータは上書きされます！"
    echo ""
    read -p "復元を続行しますか？ (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "復元をキャンセルしました。"
        exit 0
    fi
fi

# ============================================
# コンテナの停止
# ============================================
log_section "Dockerコンテナの停止"

cd "$PROJECT_DIR"

if [ -f "docker-compose.yml" ]; then
    log_info "Dockerコンテナを停止中..."
    docker compose down || true
    log_info "コンテナを停止しました。"
else
    log_warn "docker-compose.ymlが見つかりません。"
fi

# ============================================
# データベースの復元
# ============================================
if [ "$RESTORE_DB" = true ]; then
    log_section "データベースの復元"

    # データベースバックアップファイルを検索
    DB_BACKUP=$(find "$BACKUP_PATH" -name "database_*.sql.gz" | head -1)

    if [ -z "$DB_BACKUP" ]; then
        log_warn "データベースバックアップが見つかりません。スキップします。"
    else
        log_info "データベースバックアップ: $DB_BACKUP"

        # データベースコンテナを一時起動
        log_info "データベースコンテナを起動中..."
        docker compose up -d db

        # データベースの準備待ち
        log_info "データベースの準備を待機中..."
        sleep 10

        DB_CONTAINER=$(docker ps --filter "name=db" --format "{{.Names}}" | head -1)

        if [ -z "$DB_CONTAINER" ]; then
            log_error "データベースコンテナが起動しませんでした。"
            exit 1
        fi

        log_info "データベースを復元中..."
        gunzip -c "$DB_BACKUP" | docker exec -i "$DB_CONTAINER" psql -U "${POSTGRES_USER:-openclaw}"

        log_info "データベースの復元が完了しました。"

        # コンテナ停止
        docker compose down
    fi
fi

# ============================================
# Dockerボリュームの復元
# ============================================
if [ "$RESTORE_VOLUMES" = true ]; then
    log_section "Dockerボリュームの復元"

    VOLUMES_DIR="$BACKUP_PATH/volumes"

    if [ ! -d "$VOLUMES_DIR" ]; then
        log_warn "ボリュームバックアップが見つかりません。スキップします。"
    else
        for VOLUME_BACKUP in "$VOLUMES_DIR"/*.tar.gz; do
            if [ -f "$VOLUME_BACKUP" ]; then
                VOLUME_NAME=$(basename "$VOLUME_BACKUP" | sed 's/_[0-9]*\.tar\.gz$//')

                log_info "ボリュームを復元中: $VOLUME_NAME"

                # ボリュームが存在しない場合は作成
                docker volume create "$VOLUME_NAME" || true

                # ボリュームにデータを復元
                docker run --rm \
                    -v "$VOLUME_NAME":/target \
                    -v "$VOLUMES_DIR":/backup:ro \
                    alpine \
                    sh -c "rm -rf /target/* /target/..?* /target/.[!.]* 2>/dev/null; tar xzf /backup/$(basename $VOLUME_BACKUP) -C /target"

                log_info "ボリューム復元完了: $VOLUME_NAME"
            fi
        done
    fi
fi

# ============================================
# 設定ファイルの復元
# ============================================
if [ "$RESTORE_CONFIG" = true ]; then
    log_section "設定ファイルの復元"

    CONFIG_BACKUP=$(find "$BACKUP_PATH" -name "config_*.tar.gz" | head -1)

    if [ -z "$CONFIG_BACKUP" ]; then
        log_warn "設定ファイルバックアップが見つかりません。スキップします。"
    else
        log_info "設定ファイルバックアップ: $CONFIG_BACKUP"

        # 既存の設定ファイルをバックアップ
        if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
            BACKUP_SUFFIX=$(date +%Y%m%d_%H%M%S)
            cp "$PROJECT_DIR/docker-compose.yml" "$PROJECT_DIR/docker-compose.yml.backup.$BACKUP_SUFFIX"
            log_info "既存の設定をバックアップしました。"
        fi

        log_info "設定ファイルを復元中..."
        tar xzf "$CONFIG_BACKUP" -C "$PROJECT_DIR"

        log_info "設定ファイルの復元が完了しました。"
    fi
fi

# ============================================
# コンテナの起動
# ============================================
log_section "Dockerコンテナの起動"

if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
    log_info "Dockerコンテナを起動中..."
    cd "$PROJECT_DIR"
    docker compose up -d

    log_info "コンテナ起動完了"

    # ヘルスチェック
    log_info "ヘルスチェック待機中..."
    sleep 10

    docker compose ps
else
    log_warn "docker-compose.ymlが見つかりません。手動でコンテナを起動してください。"
fi

# ============================================
# 復元完了
# ============================================
log_section "復元完了"

echo ""
echo "復元サマリー:"
echo "===================="
echo "復元元: $BACKUP_PATH"
echo "復元内容:"
[ "$RESTORE_DB" = true ] && echo "  ✓ データベース"
[ "$RESTORE_VOLUMES" = true ] && echo "  ✓ Dockerボリューム"
[ "$RESTORE_CONFIG" = true ] && echo "  ✓ 設定ファイル"
echo ""
echo "次のステップ:"
echo "1. アプリケーションの動作確認"
echo "2. ログの確認: docker compose logs -f"
echo "3. データベース接続の確認"
echo ""

log_info "復元が正常に完了しました。"
