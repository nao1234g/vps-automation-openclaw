#!/bin/bash

# ============================================================================
# OpenClaw VPS System Status Dashboard
# ============================================================================
#
# システム全体のステータスを一画面で表示する統合ダッシュボード
#
# 使用方法:
#   ./scripts/status_dashboard.sh [オプション]
#
# オプション:
#   --watch       自動更新モード（5秒ごと）
#   --json        JSON形式で出力
#   --export      ステータスをファイル出力
#   --help        ヘルプ表示
#
# 実行例:
#   ./scripts/status_dashboard.sh
#   ./scripts/status_dashboard.sh --watch
#   ./scripts/status_dashboard.sh --json > status.json
#
# ============================================================================

set -euo pipefail

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 設定
COMPOSE_FILE="docker-compose.production.yml"
REFRESH_INTERVAL=5

# アイコン
ICON_OK="✅"
ICON_WARNING="⚠️"
ICON_ERROR="❌"
ICON_INFO="ℹ️"
ICON_ROCKET="🚀"
ICON_SHIELD="🔒"
ICON_CHART="📊"
ICON_MONEY="💰"
ICON_TIME="⏱️"

# ヘルプ表示
show_help() {
  cat << EOF
OpenClaw VPS System Status Dashboard

使用方法:
  $0 [オプション]

オプション:
  --watch       自動更新モード（${REFRESH_INTERVAL}秒ごと）
  --json        JSON形式で出力
  --export      ステータスをファイル出力
  --help        このヘルプを表示

表示内容:
  - システムリソース（CPU、メモリ、ディスク）
  - Dockerコンテナステータス
  - サービスヘルスチェック
  - セキュリティステータス
  - バックアップ状況
  - コスト情報
  - アラート状況

キーボード操作（--watchモード）:
  q または Ctrl+C: 終了

EOF
}

# 画面クリア
clear_screen() {
  clear
  echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║${WHITE}            OpenClaw VPS - System Status Dashboard                  ${BLUE}║${NC}"
  echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${CYAN}Last Update: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
  echo ""
}

# システムリソース情報
get_system_resources() {
  echo -e "${BLUE}═══ ${ICON_CHART} System Resources ═══${NC}"

  # CPU使用率
  local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
  local cpu_color="${GREEN}"
  if (( $(echo "$cpu_usage > 80" | bc -l) )); then
    cpu_color="${RED}"
  elif (( $(echo "$cpu_usage > 60" | bc -l) )); then
    cpu_color="${YELLOW}"
  fi

  # メモリ使用率
  local mem_used=$(free | grep Mem | awk '{print $3}')
  local mem_total=$(free | grep Mem | awk '{print $2}')
  local mem_percent=$(echo "scale=1; $mem_used / $mem_total * 100" | bc -l)
  local mem_color="${GREEN}"
  if (( $(echo "$mem_percent > 85" | bc -l) )); then
    mem_color="${RED}"
  elif (( $(echo "$mem_percent > 70" | bc -l) )); then
    mem_color="${YELLOW}"
  fi

  # ディスク使用率
  local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | cut -d'%' -f1)
  local disk_color="${GREEN}"
  if (( $disk_usage > 85 )); then
    disk_color="${RED}"
  elif (( $disk_usage > 70 )); then
    disk_color="${YELLOW}"
  fi

  # ロードアベレージ
  local load_avg=$(uptime | awk -F'load average:' '{print $2}' | xargs)

  # スワップ使用率
  local swap_usage=$(free | grep Swap | awk '{if ($2 > 0) print int($3/$2*100); else print 0}')

  echo -e "  ${cpu_color}CPU:${NC}     ${cpu_usage}%"
  echo -e "  ${mem_color}Memory:${NC}  ${mem_percent}% ($(numfmt --to=iec-i --suffix=B $((mem_used * 1024))) / $(numfmt --to=iec-i --suffix=B $((mem_total * 1024))))"
  echo -e "  ${disk_color}Disk:${NC}    ${disk_usage}%"
  echo -e "  ${CYAN}Load:${NC}    ${load_avg}"
  echo -e "  ${CYAN}Swap:${NC}    ${swap_usage}%"
  echo ""
}

# Dockerコンテナステータス
get_docker_status() {
  echo -e "${BLUE}═══ ${ICON_ROCKET} Docker Containers ═══${NC}"

  if ! docker compose -f "$COMPOSE_FILE" ps > /dev/null 2>&1; then
    echo -e "  ${ICON_ERROR} Docker Composeが実行されていません"
    echo ""
    return
  fi

  # コンテナ一覧
  local containers=(openclaw n8n opennotebook postgres nginx)

  for container in "${containers[@]}"; do
    if docker compose -f "$COMPOSE_FILE" ps "$container" 2>/dev/null | grep -q "Up"; then
      echo -e "  ${ICON_OK} ${GREEN}${container}${NC} - Running"
    else
      echo -e "  ${ICON_ERROR} ${RED}${container}${NC} - Stopped"
    fi
  done

  echo ""

  # コンテナリソース使用状況
  echo -e "${CYAN}  Container Resources:${NC}"
  docker stats --no-stream --format "  {{.Name}}: CPU {{.CPUPerc}} | Mem {{.MemUsage}}" 2>/dev/null || echo "  情報取得不可"
  echo ""
}

# サービスヘルスチェック
get_health_checks() {
  echo -e "${BLUE}═══ ${ICON_SHIELD} Service Health ═══${NC}"

  # OpenClaw
  if curl -sf http://localhost:3000/health > /dev/null 2>&1; then
    echo -e "  ${ICON_OK} ${GREEN}OpenClaw${NC}     - Healthy"
  else
    echo -e "  ${ICON_ERROR} ${RED}OpenClaw${NC}     - Unhealthy"
  fi

  # N8N
  if curl -sf http://localhost:5678/healthz > /dev/null 2>&1; then
    echo -e "  ${ICON_OK} ${GREEN}N8N${NC}          - Healthy"
  else
    echo -e "  ${ICON_ERROR} ${RED}N8N${NC}          - Unhealthy"
  fi

  # OpenNotebook
  if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "  ${ICON_OK} ${GREEN}OpenNotebook${NC} - Healthy"
  else
    echo -e "  ${ICON_ERROR} ${RED}OpenNotebook${NC} - Unhealthy"
  fi

  # PostgreSQL
  if docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U openclaw -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "  ${ICON_OK} ${GREEN}PostgreSQL${NC}   - Healthy"
  else
    echo -e "  ${ICON_ERROR} ${RED}PostgreSQL${NC}   - Unhealthy"
  fi

  # Nginx
  if curl -sf http://localhost > /dev/null 2>&1; then
    echo -e "  ${ICON_OK} ${GREEN}Nginx${NC}        - Healthy"
  else
    echo -e "  ${ICON_ERROR} ${RED}Nginx${NC}        - Unhealthy"
  fi

  echo ""
}

# セキュリティステータス
get_security_status() {
  echo -e "${BLUE}═══ ${ICON_SHIELD} Security Status ═══${NC}"

  # UFWステータス
  if sudo ufw status 2>/dev/null | grep -q "Status: active"; then
    echo -e "  ${ICON_OK} ${GREEN}UFW Firewall${NC}   - Active"
  else
    echo -e "  ${ICON_WARNING} ${YELLOW}UFW Firewall${NC}   - Inactive"
  fi

  # Fail2banステータス
  if sudo systemctl is-active fail2ban > /dev/null 2>&1; then
    local banned=$(sudo fail2ban-client status sshd 2>/dev/null | grep "Currently banned" | awk '{print $NF}' || echo "0")
    echo -e "  ${ICON_OK} ${GREEN}Fail2ban${NC}       - Active (${banned} banned)"
  else
    echo -e "  ${ICON_WARNING} ${YELLOW}Fail2ban${NC}       - Inactive"
  fi

  # 最新セキュリティスキャン
  local latest_scan=$(ls -t security-reports/*.txt 2>/dev/null | head -1)
  if [ -n "$latest_scan" ]; then
    local scan_date=$(stat -c %y "$latest_scan" | cut -d' ' -f1)
    echo -e "  ${ICON_INFO} Last Scan:     ${scan_date}"
  else
    echo -e "  ${ICON_WARNING} ${YELLOW}Last Scan:     No scans found${NC}"
  fi

  # SSL証明書の有効期限
  if [ -f "/etc/letsencrypt/live/*/cert.pem" ]; then
    local cert_expiry=$(sudo openssl x509 -enddate -noout -in /etc/letsencrypt/live/*/cert.pem 2>/dev/null | cut -d= -f2)
    if [ -n "$cert_expiry" ]; then
      echo -e "  ${ICON_INFO} SSL Expires:   ${cert_expiry}"
    fi
  fi

  echo ""
}

# バックアップ状況
get_backup_status() {
  echo -e "${BLUE}═══ ${ICON_TIME} Backup Status ═══${NC}"

  # 最新バックアップ
  local latest_backup=$(ls -td /opt/backups/openclaw/backup_* 2>/dev/null | head -1)

  if [ -n "$latest_backup" ]; then
    local backup_date=$(basename "$latest_backup" | sed 's/backup_//' | sed 's/_/ /')
    local backup_size=$(du -sh "$latest_backup" 2>/dev/null | cut -f1)
    local backup_age=$(($(date +%s) - $(stat -c %Y "$latest_backup")))
    local backup_age_hours=$((backup_age / 3600))

    local backup_color="${GREEN}"
    if (( backup_age_hours > 48 )); then
      backup_color="${RED}"
    elif (( backup_age_hours > 24 )); then
      backup_color="${YELLOW}"
    fi

    echo -e "  ${backup_color}Latest Backup:${NC} ${backup_date}"
    echo -e "  ${CYAN}Size:${NC}          ${backup_size}"
    echo -e "  ${CYAN}Age:${NC}           ${backup_age_hours} hours ago"

    # バックアップ数
    local backup_count=$(ls -d /opt/backups/openclaw/backup_* 2>/dev/null | wc -l)
    echo -e "  ${CYAN}Total Backups:${NC} ${backup_count}"
  else
    echo -e "  ${ICON_WARNING} ${YELLOW}No backups found${NC}"
  fi

  echo ""
}

# コスト情報
get_cost_info() {
  echo -e "${BLUE}═══ ${ICON_MONEY} Cost Information ═══${NC}"

  # PostgreSQLからコスト情報取得
  if docker compose -f "$COMPOSE_FILE" ps postgres 2>/dev/null | grep -q "Up"; then
    # 今日のコスト
    local today_cost=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U openclaw -d openclaw -t -c "\
        SELECT COALESCE(total_cost_jpy, 0) \
        FROM daily_costs \
        WHERE date = CURRENT_DATE;" 2>/dev/null | xargs || echo "0")

    # 今月のコスト
    local month_cost=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U openclaw -d openclaw -t -c "\
        SELECT COALESCE(SUM(total_cost_jpy), 0) \
        FROM daily_costs \
        WHERE DATE_TRUNC('month', date) = DATE_TRUNC('month', CURRENT_DATE);" 2>/dev/null | xargs || echo "0")

    # 予算
    local budget=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U openclaw -d openclaw -t -c "\
        SELECT COALESCE(budget_jpy, 5000) \
        FROM monthly_budgets \
        WHERE year = EXTRACT(YEAR FROM CURRENT_DATE) \
          AND month = EXTRACT(MONTH FROM CURRENT_DATE);" 2>/dev/null | xargs || echo "5000")

    # 予算使用率
    local budget_percent=$(echo "scale=1; $month_cost / $budget * 100" | bc -l 2>/dev/null || echo "0")

    local cost_color="${GREEN}"
    if (( $(echo "$budget_percent > 100" | bc -l 2>/dev/null) )); then
      cost_color="${RED}"
    elif (( $(echo "$budget_percent > 80" | bc -l 2>/dev/null) )); then
      cost_color="${YELLOW}"
    fi

    echo -e "  ${CYAN}Today:${NC}         ¥${today_cost}"
    echo -e "  ${CYAN}This Month:${NC}    ¥${month_cost}"
    echo -e "  ${CYAN}Budget:${NC}        ¥${budget}"
    echo -e "  ${cost_color}Usage:${NC}         ${budget_percent}%"
  else
    echo -e "  ${ICON_WARNING} ${YELLOW}Cost tracking unavailable${NC}"
  fi

  echo ""
}

# アラート状況
get_alerts() {
  echo -e "${BLUE}═══ ${ICON_WARNING} Active Alerts ═══${NC}"

  local has_alerts=false

  # CPU警告
  local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
  if (( $(echo "$cpu_usage > 80" | bc -l) )); then
    echo -e "  ${ICON_WARNING} ${YELLOW}High CPU usage: ${cpu_usage}%${NC}"
    has_alerts=true
  fi

  # メモリ警告
  local mem_percent=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
  if (( $mem_percent > 85 )); then
    echo -e "  ${ICON_WARNING} ${YELLOW}High memory usage: ${mem_percent}%${NC}"
    has_alerts=true
  fi

  # ディスク警告
  local disk_usage=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
  if (( $disk_usage > 85 )); then
    echo -e "  ${ICON_WARNING} ${YELLOW}High disk usage: ${disk_usage}%${NC}"
    has_alerts=true
  fi

  # バックアップ警告
  local latest_backup=$(ls -td /opt/backups/openclaw/backup_* 2>/dev/null | head -1)
  if [ -n "$latest_backup" ]; then
    local backup_age=$(($(date +%s) - $(stat -c %Y "$latest_backup")))
    local backup_age_hours=$((backup_age / 3600))
    if (( backup_age_hours > 48 )); then
      echo -e "  ${ICON_WARNING} ${YELLOW}Backup is old: ${backup_age_hours} hours${NC}"
      has_alerts=true
    fi
  fi

  if [ "$has_alerts" = false ]; then
    echo -e "  ${ICON_OK} ${GREEN}No active alerts${NC}"
  fi

  echo ""
}

# 推奨アクション
get_recommendations() {
  echo -e "${BLUE}═══ ${ICON_INFO} Recommendations ═══${NC}"

  local has_recommendations=false

  # ディスク使用率チェック
  local disk_usage=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
  if (( $disk_usage > 70 )); then
    echo -e "  ${ICON_INFO} ${CYAN}Consider cleaning up disk space${NC}"
    echo -e "      ${WHITE}Run:${NC} docker system prune -a"
    has_recommendations=true
  fi

  # バックアップチェック
  local backup_count=$(ls -d /opt/backups/openclaw/backup_* 2>/dev/null | wc -l)
  if (( backup_count > 30 )); then
    echo -e "  ${ICON_INFO} ${CYAN}Too many backups (${backup_count})${NC}"
    echo -e "      ${WHITE}Run:${NC} find /opt/backups/openclaw -mtime +30 -delete"
    has_recommendations=true
  fi

  # セキュリティスキャンチェック
  local latest_scan=$(ls -t security-reports/*.txt 2>/dev/null | head -1)
  if [ -z "$latest_scan" ] || [ $(find "$latest_scan" -mtime +7 2>/dev/null | wc -l) -gt 0 ]; then
    echo -e "  ${ICON_INFO} ${CYAN}Security scan recommended${NC}"
    echo -e "      ${WHITE}Run:${NC} ./scripts/security_scan.sh --all"
    has_recommendations=true
  fi

  if [ "$has_recommendations" = false ]; then
    echo -e "  ${ICON_OK} ${GREEN}System is well maintained${NC}"
  fi

  echo ""
}

# フッター
print_footer() {
  echo -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}Press 'q' to quit | Refresh: ${REFRESH_INTERVAL}s${NC}"
  echo ""
}

# JSON出力
output_json() {
  # 簡易的なJSON出力（jqがあればもっと綺麗に）
  cat << EOF
{
  "timestamp": "$(date -Iseconds)",
  "system": {
    "cpu_percent": $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1),
    "memory_percent": $(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}'),
    "disk_percent": $(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
  },
  "containers": {
    "openclaw": "$(docker compose -f "$COMPOSE_FILE" ps openclaw 2>/dev/null | grep -q "Up" && echo "running" || echo "stopped")",
    "n8n": "$(docker compose -f "$COMPOSE_FILE" ps n8n 2>/dev/null | grep -q "Up" && echo "running" || echo "stopped")",
    "postgres": "$(docker compose -f "$COMPOSE_FILE" ps postgres 2>/dev/null | grep -q "Up" && echo "running" || echo "stopped")"
  }
}
EOF
}

# ウォッチモード
watch_mode() {
  while true; do
    clear_screen
    get_system_resources
    get_docker_status
    get_health_checks
    get_security_status
    get_backup_status
    get_cost_info
    get_alerts
    get_recommendations
    print_footer

    # q キー入力待ち（タイムアウト付き）
    read -t $REFRESH_INTERVAL -n 1 key 2>/dev/null || true
    if [[ $key == "q" ]]; then
      break
    fi
  done
}

# 通常モード
normal_mode() {
  clear_screen
  get_system_resources
  get_docker_status
  get_health_checks
  get_security_status
  get_backup_status
  get_cost_info
  get_alerts
  get_recommendations
  echo -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"
  echo ""
}

# メイン処理
main() {
  local mode="${1:-}"

  case "$mode" in
    --watch)
      watch_mode
      ;;
    --json)
      output_json
      ;;
    --export)
      local export_file="status-reports/system_status_$(date +%Y%m%d_%H%M%S).txt"
      mkdir -p status-reports
      normal_mode > "$export_file"
      echo "Status exported to: $export_file"
      ;;
    --help)
      show_help
      exit 0
      ;;
    *)
      normal_mode
      ;;
  esac
}

# スクリプト実行
main "$@"
