#!/bin/bash

# ============================================================================
# OpenClaw VPS Performance Benchmark Script
# ============================================================================
#
# システムとアプリケーションのパフォーマンスを測定します
#
# 使用方法:
#   ./scripts/benchmark.sh [オプション]
#
# オプション:
#   --quick     簡易ベンチマークのみ実行（5分）
#   --full      完全ベンチマーク実行（30分）
#   --report    レポートのみ表示
#   --help      ヘルプ表示
#
# 実行例:
#   ./scripts/benchmark.sh --quick
#   ./scripts/benchmark.sh --full
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
BENCHMARK_DIR="./benchmark-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${BENCHMARK_DIR}/benchmark_${TIMESTAMP}.txt"

# ヘルプ表示
show_help() {
  cat << EOF
OpenClaw VPS Performance Benchmark Script

使用方法:
  $0 [オプション]

オプション:
  --quick     簡易ベンチマーク（5分）
  --full      完全ベンチマーク（30分）
  --report    最新レポートを表示
  --help      このヘルプを表示

ベンチマーク項目:
  - システムリソース（CPU, メモリ, ディスク, ネットワーク）
  - Docker コンテナパフォーマンス
  - PostgreSQL クエリパフォーマンス
  - Nginx スループット
  - API レスポンスタイム

レポート保存先:
  ${BENCHMARK_DIR}/

EOF
}

# ディレクトリ作成
mkdir -p "${BENCHMARK_DIR}"

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

# ヘッダー出力
print_header() {
  cat << EOF | tee -a "${REPORT_FILE}"

========================================
  OpenClaw VPS Performance Benchmark
========================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Hostname: $(hostname)
========================================

EOF
}

# システム情報取得
get_system_info() {
  log_info "システム情報を取得中..."

  cat << EOF | tee -a "${REPORT_FILE}"

--- System Information ---
OS: $(lsb_release -d | cut -f2-)
Kernel: $(uname -r)
CPU: $(lscpu | grep "Model name" | cut -d: -f2 | xargs)
CPU Cores: $(nproc)
Total Memory: $(free -h | awk '/^Mem:/ {print $2}')
Total Disk: $(df -h / | awk 'NR==2 {print $2}')

EOF
}

# CPU ベンチマーク
benchmark_cpu() {
  log_info "CPU ベンチマーク実行中..."

  echo "--- CPU Benchmark ---" | tee -a "${REPORT_FILE}"

  # sysbench がインストールされているか確認
  if ! command -v sysbench &> /dev/null; then
    log_warning "sysbench がインストールされていません。インストール: apt install sysbench"
    return
  fi

  # シングルスレッド
  log_info "シングルスレッドテスト..."
  sysbench cpu --cpu-max-prime=20000 --threads=1 run 2>&1 | \
    grep "events per second" | tee -a "${REPORT_FILE}"

  # マルチスレッド
  log_info "マルチスレッドテスト ($(nproc) cores)..."
  sysbench cpu --cpu-max-prime=20000 --threads=$(nproc) run 2>&1 | \
    grep "events per second" | tee -a "${REPORT_FILE}"

  echo "" | tee -a "${REPORT_FILE}"
}

# メモリベンチマーク
benchmark_memory() {
  log_info "メモリベンチマーク実行中..."

  echo "--- Memory Benchmark ---" | tee -a "${REPORT_FILE}"

  if ! command -v sysbench &> /dev/null; then
    log_warning "sysbench がインストールされていません"
    return
  fi

  sysbench memory --memory-block-size=1M --memory-total-size=10G run 2>&1 | \
    grep -E "transferred|per second" | tee -a "${REPORT_FILE}"

  echo "" | tee -a "${REPORT_FILE}"
}

# ディスクI/Oベンチマーク
benchmark_disk() {
  log_info "ディスクI/Oベンチマーク実行中..."

  echo "--- Disk I/O Benchmark ---" | tee -a "${REPORT_FILE}"

  # dd コマンドでシーケンシャルライト測定
  log_info "シーケンシャルライトテスト..."
  dd if=/dev/zero of="${BENCHMARK_DIR}/testfile" bs=1M count=1024 oflag=direct 2>&1 | \
    tail -1 | tee -a "${REPORT_FILE}"

  # dd コマンドでシーケンシャルリード測定
  log_info "シーケンシャルリードテスト..."
  dd if="${BENCHMARK_DIR}/testfile" of=/dev/null bs=1M count=1024 iflag=direct 2>&1 | \
    tail -1 | tee -a "${REPORT_FILE}"

  # クリーンアップ
  rm -f "${BENCHMARK_DIR}/testfile"

  echo "" | tee -a "${REPORT_FILE}"
}

# Docker コンテナパフォーマンス
benchmark_docker() {
  log_info "Docker コンテナパフォーマンス測定中..."

  echo "--- Docker Container Performance ---" | tee -a "${REPORT_FILE}"

  # コンテナリソース使用状況
  docker stats --no-stream --format \
    "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" | \
    tee -a "${REPORT_FILE}"

  echo "" | tee -a "${REPORT_FILE}"
}

# PostgreSQL ベンチマーク
benchmark_postgres() {
  log_info "PostgreSQL ベンチマーク実行中..."

  echo "--- PostgreSQL Benchmark ---" | tee -a "${REPORT_FILE}"

  # 接続テスト
  if ! docker compose -f docker-compose.production.yml exec -T postgres \
    psql -U openclaw -d postgres -c "SELECT version();" &> /dev/null; then
    log_warning "PostgreSQL に接続できません"
    return
  fi

  # データベースサイズ
  log_info "データベースサイズ..."
  docker compose -f docker-compose.production.yml exec -T postgres \
    psql -U openclaw -d postgres -c "\
      SELECT datname, pg_size_pretty(pg_database_size(datname)) AS size \
      FROM pg_database WHERE datname IN ('openclaw', 'n8n', 'opennotebook');" | \
    tee -a "${REPORT_FILE}"

  # 接続数
  log_info "アクティブ接続数..."
  docker compose -f docker-compose.production.yml exec -T postgres \
    psql -U openclaw -d postgres -c "\
      SELECT count(*) as active_connections \
      FROM pg_stat_activity WHERE state = 'active';" | \
    tee -a "${REPORT_FILE}"

  # キャッシュヒット率
  log_info "キャッシュヒット率..."
  docker compose -f docker-compose.production.yml exec -T postgres \
    psql -U openclaw -d openclaw -c "\
      SELECT \
        datname, \
        ROUND(100.0 * blks_hit / NULLIF(blks_hit + blks_read, 0), 2) AS cache_hit_ratio \
      FROM pg_stat_database \
      WHERE datname = 'openclaw';" | \
    tee -a "${REPORT_FILE}"

  # 簡易クエリパフォーマンステスト
  log_info "簡易クエリパフォーマンステスト..."
  local start_time=$(date +%s%N)
  docker compose -f docker-compose.production.yml exec -T postgres \
    psql -U openclaw -d openclaw -c "\
      SELECT COUNT(*) FROM (SELECT generate_series(1, 100000)) AS t;" \
    > /dev/null 2>&1
  local end_time=$(date +%s%N)
  local duration=$((($end_time - $start_time) / 1000000))
  echo "Query execution time: ${duration}ms" | tee -a "${REPORT_FILE}"

  echo "" | tee -a "${REPORT_FILE}"
}

# Nginx ベンチマーク
benchmark_nginx() {
  log_info "Nginx ベンチマーク実行中..."

  echo "--- Nginx Benchmark ---" | tee -a "${REPORT_FILE}"

  # ab (Apache Bench) がインストールされているか確認
  if ! command -v ab &> /dev/null; then
    log_warning "ab (Apache Bench) がインストールされていません。インストール: apt install apache2-utils"
    return
  fi

  # Nginx が起動しているか確認
  if ! docker compose -f docker-compose.production.yml ps nginx | grep -q "Up"; then
    log_warning "Nginx が起動していません"
    return
  fi

  log_info "スループットテスト (100 requests, concurrency 10)..."
  ab -n 100 -c 10 http://localhost/ 2>&1 | \
    grep -E "Requests per second|Time per request|Transfer rate" | \
    tee -a "${REPORT_FILE}"

  echo "" | tee -a "${REPORT_FILE}"
}

# ネットワークベンチマーク
benchmark_network() {
  log_info "ネットワークベンチマーク実行中..."

  echo "--- Network Benchmark ---" | tee -a "${REPORT_FILE}"

  # iperf3 がインストールされているか確認
  if ! command -v iperf3 &> /dev/null; then
    log_warning "iperf3 がインストールされていません。インストール: apt install iperf3"
    return
  fi

  # ローカルネットワークスループット測定
  log_info "ローカルネットワークスループット..."
  # Note: iperf3サーバーが必要。実装は環境に応じて調整

  echo "Network throughput test requires iperf3 server setup" | tee -a "${REPORT_FILE}"
  echo "" | tee -a "${REPORT_FILE}"
}

# レポートサマリー
generate_summary() {
  log_info "サマリーを生成中..."

  cat << EOF | tee -a "${REPORT_FILE}"

========================================
  Benchmark Summary
========================================

レポートファイル: ${REPORT_FILE}

推奨事項:
EOF

  # CPU使用率チェック
  local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
  if (( $(echo "$cpu_usage > 80" | bc -l) )); then
    log_warning "CPU使用率が高い: ${cpu_usage}%"
    echo "  - CPU使用率が高いため、リソース制限の見直しを推奨" | tee -a "${REPORT_FILE}"
  fi

  # メモリ使用率チェック
  local mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
  if (( $mem_usage > 85 )); then
    log_warning "メモリ使用率が高い: ${mem_usage}%"
    echo "  - メモリ使用率が高いため、スワップ設定またはメモリ増設を推奨" | tee -a "${REPORT_FILE}"
  fi

  # ディスク使用率チェック
  local disk_usage=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
  if (( $disk_usage > 80 )); then
    log_warning "ディスク使用率が高い: ${disk_usage}%"
    echo "  - ディスク使用率が高いため、古いログやバックアップの削除を推奨" | tee -a "${REPORT_FILE}"
  fi

  cat << EOF | tee -a "${REPORT_FILE}"

詳細なパフォーマンス最適化については以下を参照:
  - PERFORMANCE.md
  - TROUBLESHOOTING.md

========================================

EOF

  log_success "ベンチマーク完了！"
}

# 最新レポート表示
show_latest_report() {
  local latest=$(ls -t "${BENCHMARK_DIR}"/benchmark_*.txt 2>/dev/null | head -1)

  if [ -z "$latest" ]; then
    log_error "レポートが見つかりません"
    exit 1
  fi

  log_info "最新レポートを表示: ${latest}"
  cat "$latest"
}

# メイン実行
main() {
  local mode="${1:-}"

  case "$mode" in
    --help)
      show_help
      exit 0
      ;;
    --report)
      show_latest_report
      exit 0
      ;;
    --quick)
      log_info "簡易ベンチマークを開始します..."
      print_header
      get_system_info
      benchmark_docker
      benchmark_postgres
      generate_summary
      ;;
    --full)
      log_info "完全ベンチマークを開始します（約30分かかります）..."
      print_header
      get_system_info
      benchmark_cpu
      benchmark_memory
      benchmark_disk
      benchmark_docker
      benchmark_postgres
      benchmark_nginx
      benchmark_network
      generate_summary
      ;;
    *)
      show_help
      exit 1
      ;;
  esac

  log_success "レポートが保存されました: ${REPORT_FILE}"
}

# スクリプト実行
main "$@"
