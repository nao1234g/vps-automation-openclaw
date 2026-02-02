#!/bin/bash

# ============================================================================
# OpenClaw VPS Cost Tracking Script
# ============================================================================
#
# このスクリプトは、VPS、API、ストレージのコストを追跡し、
# 月次レポートを生成します。
#
# 使用方法:
#   ./scripts/cost_tracker.sh [オプション]
#
# オプション:
#   --daily       日次コストレポート
#   --monthly     月次コストレポート
#   --forecast    月末予測
#   --alert       予算超過アラート
#   --export      CSVエクスポート
#
# 実行例:
#   ./scripts/cost_tracker.sh --monthly
#   ./scripts/cost_tracker.sh --forecast --alert
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
REPORT_DIR="./cost-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${REPORT_DIR}/cost_report_${TIMESTAMP}.txt"
CSV_FILE="${REPORT_DIR}/cost_data_${TIMESTAMP}.csv"

# 予算設定（.env から読み込み可能）
MONTHLY_BUDGET_JPY=${MONTHLY_BUDGET_JPY:-5000}
MONTHLY_BUDGET_USD=${MONTHLY_BUDGET_USD:-35}

# VPS料金（月額、円）
VPS_MONTHLY_COST=${VPS_MONTHLY_COST:-1200}

# 為替レート
USD_TO_JPY=${USD_TO_JPY:-150}

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

# ヘッダー出力
print_header() {
  cat << EOF | tee -a "${REPORT_FILE}"

========================================
  OpenClaw VPS Cost Report
========================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
========================================

EOF
}

# APIトークン使用量を取得（PostgreSQLから）
get_api_usage() {
  local period=$1  # 'today', 'month'

  log_info "API使用量を取得中..."

  # PostgreSQLに接続してトークン使用量を取得
  if docker compose -f docker-compose.production.yml ps postgres | grep -q "Up"; then
    case $period in
      today)
        local query="SELECT
          COALESCE(SUM(tokens_input), 0) as input_tokens,
          COALESCE(SUM(tokens_output), 0) as output_tokens,
          COUNT(*) as api_calls
        FROM api_usage
        WHERE date = CURRENT_DATE;"
        ;;
      month)
        local query="SELECT
          COALESCE(SUM(tokens_input), 0) as input_tokens,
          COALESCE(SUM(tokens_output), 0) as output_tokens,
          COUNT(*) as api_calls
        FROM api_usage
        WHERE DATE_TRUNC('month', date) = DATE_TRUNC('month', CURRENT_DATE);"
        ;;
      *)
        log_error "Invalid period: $period"
        return 1
        ;;
    esac

    # クエリ実行
    local result=$(docker compose -f docker-compose.production.yml exec -T postgres \
      psql -U openclaw -d openclaw -t -c "$query" 2>/dev/null || echo "0|0|0")

    echo "$result"
  else
    log_warning "PostgreSQL is not running. Cannot fetch API usage."
    echo "0|0|0"
  fi
}

# APIコスト計算（Anthropic Claude）
calculate_api_cost() {
  local input_tokens=$1
  local output_tokens=$2

  # Sonnet 4.5 料金
  # Input: $3.00 / 1M tokens
  # Output: $15.00 / 1M tokens

  local input_cost=$(echo "scale=4; $input_tokens / 1000000 * 3.00" | bc -l)
  local output_cost=$(echo "scale=4; $output_tokens / 1000000 * 15.00" | bc -l)
  local total_cost=$(echo "scale=4; $input_cost + $output_cost" | bc -l)

  echo "$total_cost"
}

# ストレージ使用量を取得
get_storage_usage() {
  log_info "ストレージ使用量を取得中..."

  # Dockerボリューム使用量
  local docker_volumes=$(docker system df -v | grep "Local Volumes" | awk '{print $4}')

  # データディレクトリ使用量
  local data_usage=$(du -sh data/ 2>/dev/null | awk '{print $1}' || echo "0")

  # バックアップディレクトリ使用量
  local backup_usage=$(du -sh /opt/backups/openclaw/ 2>/dev/null | awk '{print $1}' || echo "0")

  # ログディレクトリ使用量
  local log_usage=$(du -sh logs/ 2>/dev/null | awk '{print $1}' || echo "0")

  cat << EOF | tee -a "${REPORT_FILE}"

--- Storage Usage ---
Docker Volumes: ${docker_volumes:-N/A}
Data Directory: $data_usage
Backups: $backup_usage
Logs: $log_usage

EOF
}

# 日次コストレポート
daily_report() {
  print_header

  log_info "日次コストレポートを生成中..."

  # API使用量取得
  local usage=$(get_api_usage "today")
  local input_tokens=$(echo "$usage" | awk '{print $1}')
  local output_tokens=$(echo "$usage" | awk '{print $3}')
  local api_calls=$(echo "$usage" | awk '{print $5}')

  # コスト計算
  local api_cost_usd=$(calculate_api_cost "$input_tokens" "$output_tokens")
  local api_cost_jpy=$(echo "scale=0; $api_cost_usd * $USD_TO_JPY" | bc -l)

  # VPS日次コスト
  local vps_daily_cost=$(echo "scale=0; $VPS_MONTHLY_COST / 30" | bc -l)

  # 合計
  local total_daily_jpy=$(echo "scale=0; $vps_daily_cost + $api_cost_jpy" | bc -l)

  cat << EOF | tee -a "${REPORT_FILE}"

========================================
  Daily Cost Report
========================================

--- API Usage (Today) ---
Input Tokens:  $(printf "%'d" "$input_tokens")
Output Tokens: $(printf "%'d" "$output_tokens")
API Calls:     $api_calls

--- API Cost ---
Cost (USD): \$$api_cost_usd
Cost (JPY): ¥$api_cost_jpy

--- VPS Cost ---
Daily Cost: ¥$vps_daily_cost

--- Total Daily Cost ---
¥$total_daily_jpy

========================================

EOF

  get_storage_usage
}

# 月次コストレポート
monthly_report() {
  print_header

  log_info "月次コストレポートを生成中..."

  # API使用量取得
  local usage=$(get_api_usage "month")
  local input_tokens=$(echo "$usage" | awk '{print $1}')
  local output_tokens=$(echo "$usage" | awk '{print $3}')
  local api_calls=$(echo "$usage" | awk '{print $5}')

  # コスト計算
  local api_cost_usd=$(calculate_api_cost "$input_tokens" "$output_tokens")
  local api_cost_jpy=$(echo "scale=0; $api_cost_usd * $USD_TO_JPY" | bc -l)

  # ストレージコスト（仮定: バックアップが50GBで月額¥300）
  local storage_cost=300

  # 合計
  local total_monthly_jpy=$(echo "scale=0; $VPS_MONTHLY_COST + $api_cost_jpy + $storage_cost" | bc -l)

  # 予算比較
  local budget_diff=$(echo "scale=0; $MONTHLY_BUDGET_JPY - $total_monthly_jpy" | bc -l)
  local budget_percent=$(echo "scale=1; $total_monthly_jpy / $MONTHLY_BUDGET_JPY * 100" | bc -l)

  cat << EOF | tee -a "${REPORT_FILE}"

========================================
  Monthly Cost Report
========================================

--- API Usage (This Month) ---
Input Tokens:  $(printf "%'d" "$input_tokens")
Output Tokens: $(printf "%'d" "$output_tokens")
API Calls:     $api_calls

--- Cost Breakdown ---
VPS:       ¥$VPS_MONTHLY_COST
API:       ¥$api_cost_jpy
Storage:   ¥$storage_cost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total:     ¥$total_monthly_jpy

--- Budget Analysis ---
Monthly Budget:  ¥$MONTHLY_BUDGET_JPY
Current Cost:    ¥$total_monthly_jpy
Remaining:       ¥$budget_diff
Usage:           ${budget_percent}%

EOF

  # 予算超過アラート
  if (( $(echo "$total_monthly_jpy > $MONTHLY_BUDGET_JPY" | bc -l) )); then
    log_error "⚠️ 予算超過！ ¥$(echo "$total_monthly_jpy - $MONTHLY_BUDGET_JPY" | bc -l) オーバー"
  elif (( $(echo "$budget_percent > 80" | bc -l) )); then
    log_warning "⚠️ 予算の${budget_percent}%を使用中"
  else
    log_success "✅ 予算内（${budget_percent}%使用）"
  fi

  echo "" | tee -a "${REPORT_FILE}"
  get_storage_usage

  # コスト内訳グラフ（テキストベース）
  cat << EOF | tee -a "${REPORT_FILE}"

--- Cost Breakdown Chart ---
VPS     [$(printf '█%.0s' $(seq 1 $((VPS_MONTHLY_COST * 20 / total_monthly_jpy))))] ${VPS_MONTHLY_COST}円 ($(echo "scale=1; $VPS_MONTHLY_COST / $total_monthly_jpy * 100" | bc -l)%)
API     [$(printf '█%.0s' $(seq 1 $((api_cost_jpy * 20 / total_monthly_jpy))))] ${api_cost_jpy}円 ($(echo "scale=1; $api_cost_jpy / $total_monthly_jpy * 100" | bc -l)%)
Storage [$(printf '█%.0s' $(seq 1 $((storage_cost * 20 / total_monthly_jpy))))] ${storage_cost}円 ($(echo "scale=1; $storage_cost / $total_monthly_jpy * 100" | bc -l)%)

========================================

EOF
}

# 月末予測
forecast_month_end() {
  print_header

  log_info "月末コスト予測を計算中..."

  # 現在の日付と月の日数
  local current_day=$(date +%d)
  local days_in_month=$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%d)
  local days_remaining=$((days_in_month - current_day))

  # API使用量取得
  local usage=$(get_api_usage "month")
  local input_tokens=$(echo "$usage" | awk '{print $1}')
  local output_tokens=$(echo "$usage" | awk '{print $3}')

  # 1日あたりの平均使用量
  local avg_input_per_day=$(echo "scale=0; $input_tokens / $current_day" | bc -l)
  local avg_output_per_day=$(echo "scale=0; $output_tokens / $current_day" | bc -l)

  # 月末予測
  local forecast_input=$(echo "scale=0; $avg_input_per_day * $days_in_month" | bc -l)
  local forecast_output=$(echo "scale=0; $avg_output_per_day * $days_in_month" | bc -l)

  # 予測コスト
  local forecast_api_cost_usd=$(calculate_api_cost "$forecast_input" "$forecast_output")
  local forecast_api_cost_jpy=$(echo "scale=0; $forecast_api_cost_usd * $USD_TO_JPY" | bc -l)
  local forecast_total_jpy=$(echo "scale=0; $VPS_MONTHLY_COST + $forecast_api_cost_jpy + 300" | bc -l)

  cat << EOF | tee -a "${REPORT_FILE}"

========================================
  Month-End Forecast
========================================

--- Current Status ---
Days Elapsed:   $current_day / $days_in_month
Days Remaining: $days_remaining

--- Current Usage ---
Input Tokens:   $(printf "%'d" "$input_tokens")
Output Tokens:  $(printf "%'d" "$output_tokens")

--- Daily Average ---
Input:  $(printf "%'d" "$avg_input_per_day") tokens/day
Output: $(printf "%'d" "$avg_output_per_day") tokens/day

--- Month-End Forecast ---
Forecast Input:  $(printf "%'d" "$forecast_input")
Forecast Output: $(printf "%'d" "$forecast_output")

--- Forecast Cost ---
VPS:       ¥$VPS_MONTHLY_COST
API:       ¥$forecast_api_cost_jpy
Storage:   ¥300
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total:     ¥$forecast_total_jpy

--- Budget Comparison ---
Monthly Budget:  ¥$MONTHLY_BUDGET_JPY
Forecast Cost:   ¥$forecast_total_jpy
Difference:      ¥$(echo "$MONTHLY_BUDGET_JPY - $forecast_total_jpy" | bc -l)

EOF

  # アラート
  if (( $(echo "$forecast_total_jpy > $MONTHLY_BUDGET_JPY" | bc -l) )); then
    log_error "⚠️ 月末に予算超過の見込み！ ¥$(echo "$forecast_total_jpy - $MONTHLY_BUDGET_JPY" | bc -l) オーバー予測"
    echo "" | tee -a "${REPORT_FILE}"
    log_warning "💡 推奨アクション:"
    echo "  - APIモデルをHaikuに切り替え（60%削減）" | tee -a "${REPORT_FILE}"
    echo "  - プロンプトを最適化" | tee -a "${REPORT_FILE}"
    echo "  - 不要なワークフローを停止" | tee -a "${REPORT_FILE}"
  else
    log_success "✅ 月末も予算内の見込み"
  fi

  echo "" | tee -a "${REPORT_FILE}"
  echo "========================================" | tee -a "${REPORT_FILE}"
  echo "" | tee -a "${REPORT_FILE}"
}

# 予算超過アラート
budget_alert() {
  log_info "予算アラートをチェック中..."

  # 月次使用量取得
  local usage=$(get_api_usage "month")
  local input_tokens=$(echo "$usage" | awk '{print $1}')
  local output_tokens=$(echo "$usage" | awk '{print $3}')

  # コスト計算
  local api_cost_usd=$(calculate_api_cost "$input_tokens" "$output_tokens")
  local api_cost_jpy=$(echo "scale=0; $api_cost_usd * $USD_TO_JPY" | bc -l)
  local total_jpy=$(echo "scale=0; $VPS_MONTHLY_COST + $api_cost_jpy + 300" | bc -l)

  local budget_percent=$(echo "scale=1; $total_jpy / $MONTHLY_BUDGET_JPY * 100" | bc -l)

  if (( $(echo "$budget_percent > 100" | bc -l) )); then
    log_error "🚨 予算超過アラート！"
    log_error "現在: ¥$total_jpy (予算の${budget_percent}%)"

    # Telegram通知（オプション）
    if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
      local message="🚨 予算超過アラート！%0A現在コスト: ¥$total_jpy%0A予算: ¥$MONTHLY_BUDGET_JPY%0A使用率: ${budget_percent}%"
      curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=${message}" > /dev/null
    fi

    return 1
  elif (( $(echo "$budget_percent > 80" | bc -l) )); then
    log_warning "⚠️ 予算の${budget_percent}%を使用中"
    return 0
  else
    log_success "✅ 予算内（${budget_percent}%使用）"
    return 0
  fi
}

# CSVエクスポート
export_csv() {
  log_info "CSVエクスポート中..."

  # ヘッダー
  echo "date,input_tokens,output_tokens,api_cost_usd,vps_cost_jpy,storage_cost_jpy,total_cost_jpy" > "${CSV_FILE}"

  # データ取得（PostgreSQLから）
  if docker compose -f docker-compose.production.yml ps postgres | grep -q "Up"; then
    docker compose -f docker-compose.production.yml exec -T postgres \
      psql -U openclaw -d openclaw -t -c "
        SELECT
          date,
          input_tokens,
          output_tokens,
          api_cost_usd,
          vps_cost_jpy,
          storage_cost_jpy,
          total_cost_jpy
        FROM daily_costs
        WHERE DATE_TRUNC('month', date) = DATE_TRUNC('month', CURRENT_DATE)
        ORDER BY date;
      " | sed 's/|/,/g' >> "${CSV_FILE}" 2>/dev/null || true
  fi

  log_success "CSVエクスポート完了: ${CSV_FILE}"
}

# ヘルプ表示
show_help() {
  cat << EOF
OpenClaw VPS Cost Tracking Script

使用方法:
  $0 [オプション]

オプション:
  --daily       日次コストレポート
  --monthly     月次コストレポート
  --forecast    月末予測
  --alert       予算超過アラート
  --export      CSVエクスポート
  --help        このヘルプを表示

実行例:
  $0 --monthly
  $0 --forecast --alert
  $0 --daily --export

環境変数:
  MONTHLY_BUDGET_JPY    月次予算（円）デフォルト: 5000
  VPS_MONTHLY_COST      VPS月額（円）デフォルト: 1200
  USD_TO_JPY            為替レート デフォルト: 150

レポート保存先:
  ${REPORT_DIR}/

EOF
}

# メイン処理
main() {
  local mode="${1:-}"

  case "$mode" in
    --daily)
      daily_report
      ;;
    --monthly)
      monthly_report
      ;;
    --forecast)
      forecast_month_end
      ;;
    --alert)
      budget_alert
      ;;
    --export)
      export_csv
      ;;
    --help)
      show_help
      exit 0
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
