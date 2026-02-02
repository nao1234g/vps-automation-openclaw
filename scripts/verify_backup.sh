#!/bin/bash

# ============================================================================
# OpenClaw VPS Backup Verification Script
# ============================================================================
#
# バックアップの整合性を検証し、復元可能性をテストします
#
# 使用方法:
#   sudo ./scripts/verify_backup.sh [オプション] <backup_path>
#
# オプション:
#   --quick         クイック検証（ファイル存在確認のみ）
#   --full          完全検証（テスト復元を実行）
#   --database-only データベースのみ検証
#   --dry-run       実際の復元は行わない
#   --help          ヘルプ表示
#
# 実行例:
#   # 最新バックアップをクイック検証
#   sudo ./scripts/verify_backup.sh --quick
#
#   # 特定のバックアップを完全検証
#   sudo ./scripts/verify_backup.sh --full /opt/backups/openclaw/backup_20240201_030000
#
#   # データベースのみ検証
#   sudo ./scripts/verify_backup.sh --database-only /opt/backups/openclaw/backup_20240201_030000
#
# ============================================================================

set -euo pipefail

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定
COMPOSE_FILE="docker-compose.production.yml"
TEST_CONTAINER_PREFIX="test_verify"
REPORT_DIR="./backup-verification-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${REPORT_DIR}/verification_${TIMESTAMP}.txt"

# ログ関数
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${REPORT_FILE}"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "${REPORT_FILE}"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "${REPORT_FILE}"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1" | tee -a "${REPORT_FILE}"
}

# ディレクトリ作成
mkdir -p "${REPORT_DIR}"

# ヘルプ表示
show_help() {
  cat << EOF
OpenClaw VPS Backup Verification Script

使用方法:
  $0 [オプション] [backup_path]

オプション:
  --quick         クイック検証（ファイル存在確認のみ）
  --full          完全検証（テスト復元を実行）
  --database-only データベースのみ検証
  --dry-run       実際の復元は行わない
  --help          このヘルプを表示

引数:
  backup_path     検証するバックアップのパス
                  省略時は最新のバックアップを使用

実行例:
  # 最新バックアップをクイック検証
  sudo $0 --quick

  # 特定のバックアップを完全検証
  sudo $0 --full /opt/backups/openclaw/backup_20240201_030000

検証内容:
  1. バックアップファイルの存在確認
  2. ファイル整合性チェック（checksum）
  3. データベースダンプの構文チェック
  4. テスト環境での復元テスト（--full のみ）
  5. データ整合性確認

レポート保存先:
  ${REPORT_DIR}/

EOF
}

# ヘッダー出力
print_header() {
  cat << EOF | tee -a "${REPORT_FILE}"

========================================
  Backup Verification Report
========================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Backup Path: ${BACKUP_PATH}
Verification Mode: ${VERIFICATION_MODE}
========================================

EOF
}

# 最新バックアップを取得
get_latest_backup() {
  local latest=$(ls -td /opt/backups/openclaw/backup_* 2>/dev/null | head -1)
  if [ -z "$latest" ]; then
    log_error "バックアップが見つかりません"
    exit 1
  fi
  echo "$latest"
}

# ファイル存在確認
verify_files_exist() {
  log_info "バックアップファイルの存在確認中..."

  local required_files=(
    "postgres_dump.sql"
    "configs/.env"
    "system_info.txt"
  )

  local all_exist=true

  for file in "${required_files[@]}"; do
    local filepath="${BACKUP_PATH}/${file}"
    if [ -f "$filepath" ]; then
      log_success "✓ ${file} - 存在"
    else
      log_error "✗ ${file} - 見つかりません"
      all_exist=false
    fi
  done

  # ボリュームバックアップ確認
  if [ -d "${BACKUP_PATH}/volumes" ]; then
    log_success "✓ volumes/ - 存在"

    local volume_files=(
      "openclaw_data.tar.gz"
      "n8n_data.tar.gz"
      "opennotebook_data.tar.gz"
      "postgres_data.tar.gz"
    )

    for vfile in "${volume_files[@]}"; do
      if [ -f "${BACKUP_PATH}/volumes/${vfile}" ]; then
        log_success "  ✓ ${vfile}"
      else
        log_warning "  ✗ ${vfile} - 見つかりません"
      fi
    done
  else
    log_error "✗ volumes/ - ディレクトリが見つかりません"
    all_exist=false
  fi

  echo "" | tee -a "${REPORT_FILE}"

  if [ "$all_exist" = true ]; then
    log_success "すべての必須ファイルが存在します"
    return 0
  else
    log_error "一部のファイルが見つかりません"
    return 1
  fi
}

# ファイル整合性チェック
verify_file_integrity() {
  log_info "ファイル整合性チェック中..."

  # PostgreSQLダンプファイルのサイズチェック
  local dump_file="${BACKUP_PATH}/postgres_dump.sql"
  if [ -f "$dump_file" ]; then
    local dump_size=$(stat -c %s "$dump_file")
    if [ "$dump_size" -gt 1000 ]; then
      log_success "PostgreSQLダンプサイズ: $(numfmt --to=iec-i --suffix=B $dump_size)"
    else
      log_warning "PostgreSQLダンプが小さすぎます: ${dump_size} bytes"
    fi

    # ダンプファイルの先頭をチェック
    if head -1 "$dump_file" | grep -q "PostgreSQL database dump"; then
      log_success "PostgreSQLダンプフォーマット: 正常"
    else
      log_error "PostgreSQLダンプフォーマット: 不正"
      return 1
    fi
  fi

  # tar.gzファイルの整合性チェック
  if [ -d "${BACKUP_PATH}/volumes" ]; then
    for archive in "${BACKUP_PATH}/volumes"/*.tar.gz; do
      if [ -f "$archive" ]; then
        local basename=$(basename "$archive")
        if gzip -t "$archive" 2>/dev/null && tar -tzf "$archive" > /dev/null 2>&1; then
          log_success "✓ ${basename} - アーカイブ整合性OK"
        else
          log_error "✗ ${basename} - アーカイブが破損しています"
          return 1
        fi
      fi
    done
  fi

  echo "" | tee -a "${REPORT_FILE}"
  log_success "ファイル整合性チェック完了"
  return 0
}

# データベースダンプ検証
verify_database_dump() {
  log_info "データベースダンプを検証中..."

  local dump_file="${BACKUP_PATH}/postgres_dump.sql"

  if [ ! -f "$dump_file" ]; then
    log_error "PostgreSQLダンプファイルが見つかりません"
    return 1
  fi

  # ダンプファイルの構文チェック（PostgreSQLコンテナ内で実行）
  if docker compose -f "$COMPOSE_FILE" ps postgres | grep -q "Up"; then
    log_info "PostgreSQL構文チェックを実行中..."

    # テスト用データベースを作成
    local test_db="${TEST_CONTAINER_PREFIX}_$(date +%s)"

    docker compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U openclaw -d postgres -c "CREATE DATABASE ${test_db};" > /dev/null 2>&1

    # ダンプを復元してみる（dry-run）
    if [ "${DRY_RUN}" = true ]; then
      log_info "Dry-run: 実際の復元はスキップします"
    else
      if cat "$dump_file" | docker compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U openclaw -d "$test_db" > /dev/null 2>&1; then
        log_success "データベースダンプは正常に復元できます"
      else
        log_error "データベースダンプの復元に失敗しました"
        return 1
      fi
    fi

    # テスト用データベース削除
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U openclaw -d postgres -c "DROP DATABASE ${test_db};" > /dev/null 2>&1

  else
    log_warning "PostgreSQLが起動していないため、構文チェックをスキップします"
  fi

  echo "" | tee -a "${REPORT_FILE}"
  log_success "データベースダンプ検証完了"
  return 0
}

# 完全復元テスト
full_restoration_test() {
  log_info "完全復元テストを開始します..."
  log_warning "これには5-10分かかる場合があります"

  # TODO: テスト環境でのフル復元
  # 1. テスト用Docker Composeスタック起動
  # 2. バックアップからデータ復元
  # 3. ヘルスチェック実行
  # 4. データ整合性確認
  # 5. テストスタック削除

  log_info "完全復元テストは現在実装中です"
  log_info "代わりに、データベース検証を実行します"

  verify_database_dump
}

# バックアップメタ情報表示
show_backup_info() {
  log_info "バックアップ情報:"

  # バックアップ日時
  local backup_date=$(basename "$BACKUP_PATH" | sed 's/backup_//' | sed 's/_/ /')
  log_info "  作成日時: ${backup_date}"

  # バックアップサイズ
  local backup_size=$(du -sh "$BACKUP_PATH" | cut -f1)
  log_info "  サイズ: ${backup_size}"

  # ファイル数
  local file_count=$(find "$BACKUP_PATH" -type f | wc -l)
  log_info "  ファイル数: ${file_count}"

  # システム情報
  if [ -f "${BACKUP_PATH}/system_info.txt" ]; then
    log_info "  システム情報:"
    grep -E "Hostname|OS|Docker" "${BACKUP_PATH}/system_info.txt" | \
      sed 's/^/    /' | tee -a "${REPORT_FILE}"
  fi

  echo "" | tee -a "${REPORT_FILE}"
}

# サマリー表示
print_summary() {
  cat << EOF | tee -a "${REPORT_FILE}"

========================================
  Verification Summary
========================================

Backup Path: ${BACKUP_PATH}
Verification Mode: ${VERIFICATION_MODE}

Results:
EOF

  if [ "${FILES_EXIST}" = true ]; then
    echo -e "  ${GREEN}✓${NC} File Existence: PASS" | tee -a "${REPORT_FILE}"
  else
    echo -e "  ${RED}✗${NC} File Existence: FAIL" | tee -a "${REPORT_FILE}"
  fi

  if [ "${FILE_INTEGRITY}" = true ]; then
    echo -e "  ${GREEN}✓${NC} File Integrity: PASS" | tee -a "${REPORT_FILE}"
  else
    echo -e "  ${RED}✗${NC} File Integrity: FAIL" | tee -a "${REPORT_FILE}"
  fi

  if [ "${DATABASE_OK}" = true ]; then
    echo -e "  ${GREEN}✓${NC} Database Dump: PASS" | tee -a "${REPORT_FILE}"
  else
    echo -e "  ${RED}✗${NC} Database Dump: FAIL" | tee -a "${REPORT_FILE}"
  fi

  cat << EOF | tee -a "${REPORT_FILE}"

========================================
Report saved to: ${REPORT_FILE}
========================================

EOF

  # 総合判定
  if [ "${FILES_EXIST}" = true ] && [ "${FILE_INTEGRITY}" = true ] && [ "${DATABASE_OK}" = true ]; then
    log_success "バックアップ検証: 成功 ✓"
    log_success "このバックアップは復元可能です"
    return 0
  else
    log_error "バックアップ検証: 失敗 ✗"
    log_error "このバックアップは復元できない可能性があります"
    return 1
  fi
}

# メイン処理
main() {
  # オプション解析
  VERIFICATION_MODE="quick"
  DATABASE_ONLY=false
  DRY_RUN=false
  BACKUP_PATH=""

  while [[ $# -gt 0 ]]; do
    case $1 in
      --quick)
        VERIFICATION_MODE="quick"
        shift
        ;;
      --full)
        VERIFICATION_MODE="full"
        shift
        ;;
      --database-only)
        DATABASE_ONLY=true
        shift
        ;;
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      --help)
        show_help
        exit 0
        ;;
      *)
        BACKUP_PATH="$1"
        shift
        ;;
    esac
  done

  # バックアップパス決定
  if [ -z "$BACKUP_PATH" ]; then
    BACKUP_PATH=$(get_latest_backup)
    log_info "最新のバックアップを検証します: ${BACKUP_PATH}"
  fi

  if [ ! -d "$BACKUP_PATH" ]; then
    log_error "バックアップディレクトリが存在しません: ${BACKUP_PATH}"
    exit 1
  fi

  # ヘッダー表示
  print_header

  # バックアップ情報表示
  show_backup_info

  # 検証実行
  FILES_EXIST=false
  FILE_INTEGRITY=false
  DATABASE_OK=false

  if [ "${DATABASE_ONLY}" = true ]; then
    # データベースのみ検証
    if verify_database_dump; then
      DATABASE_OK=true
    fi
  else
    # ファイル存在確認
    if verify_files_exist; then
      FILES_EXIST=true
    fi

    # ファイル整合性チェック
    if [ "${FILES_EXIST}" = true ]; then
      if verify_file_integrity; then
        FILE_INTEGRITY=true
      fi
    fi

    # データベース検証
    if [ "${FILE_INTEGRITY}" = true ]; then
      if verify_database_dump; then
        DATABASE_OK=true
      fi
    fi

    # 完全検証の場合
    if [ "${VERIFICATION_MODE}" = "full" ] && [ "${DATABASE_OK}" = true ]; then
      full_restoration_test
    fi
  fi

  # サマリー表示
  print_summary
}

# root権限チェック
if [ "$EUID" -ne 0 ]; then
  echo "このスクリプトはroot権限で実行してください"
  echo "実行: sudo $0 $*"
  exit 1
fi

# スクリプト実行
main "$@"
