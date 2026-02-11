#!/bin/bash
# ==============================================================================
# Multi-Agent Cost Monitor
# マルチエージェントシステムのコストを監視・レポート
# ==============================================================================

set -euo pipefail

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# デフォルト設定
PERIOD="7d"
AGENT_ID=""
FORMAT="table"
EXPORT_CSV=false
OUTPUT_FILE=""

# 使用方法
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Multi-Agent Cost Monitor - コスト分析とレポート生成

OPTIONS:
    -a, --agent AGENT_ID    特定のエージェントのみ表示
                            例: jarvis-cso, alice-researcher, codex-developer
    
    -p, --period PERIOD     集計期間（デフォルト: 7d）
                            例: 1d, 7d, 30d, 1h, 24h
    
    -f, --format FORMAT     出力フォーマット（デフォルト: table）
                            options: table, json, csv
    
    -e, --export FILE       CSVファイルにエクスポート
    
    -h, --help              このヘルプを表示

EXAMPLES:
    # 過去7日間の全エージェントのコスト
    $0

    # Jarvisのみ、過去24時間
    $0 --agent jarvis-cso --period 24h

    # JSON形式で出力
    $0 --format json

    # CSVにエクスポート
    $0 --export /tmp/cost-report.csv

AGENT IDs:
    - jarvis-cso        (Chief Strategy Officer - Opus 4)
    - alice-researcher  (Research Specialist - Haiku 4)
    - codex-developer   (Senior Developer - GPT-4o)
    - pixel-designer    (Visual Designer - Gemini 1.5 Pro)
    - luna-writer       (Content Writer - Sonnet 4)
    - scout-data        (Data Processor - Flash 2.0)
    - guard-security    (Security Auditor - Haiku 4)

EOF
    exit 1
}

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--agent)
            AGENT_ID="$2"
            shift 2
            ;;
        -p|--period)
            PERIOD="$2"
            shift 2
            ;;
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        -e|--export)
            EXPORT_CSV=true
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            usage
            ;;
    esac
done

# PostgreSQL接続確認
check_database() {
    echo -e "${BLUE}[INFO]${NC} Checking database connection..."
    
    if ! docker compose exec -T postgres pg_isready -U openclaw > /dev/null 2>&1; then
        echo -e "${RED}[ERROR]${NC} PostgreSQL is not running"
        exit 1
    fi
    
    echo -e "${GREEN}[OK]${NC} Database connection established"
}

# 期間をSQLのINTERVALに変換
parse_period() {
    local period=$1
    
    if [[ $period =~ ^([0-9]+)d$ ]]; then
        echo "${BASH_REMATCH[1]} days"
    elif [[ $period =~ ^([0-9]+)h$ ]]; then
        echo "${BASH_REMATCH[1]} hours"
    elif [[ $period =~ ^([0-9]+)m$ ]]; then
        echo "${BASH_REMATCH[1]} minutes"
    else
        echo "7 days"
    fi
}

# コスト取得クエリ
get_cost_query() {
    local interval=$(parse_period "$PERIOD")
    local where_clause=""
    
    if [[ -n "$AGENT_ID" ]]; then
        where_clause="AND agent_id = '$AGENT_ID'"
    fi
    
    cat << EOF
SELECT 
    agent_id,
    COUNT(*) as total_tasks,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(cost_usd) as total_cost_usd,
    AVG(cost_usd) as avg_cost_per_task,
    AVG(execution_time_seconds) as avg_execution_time,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
    ROUND((COUNT(CASE WHEN status = 'success' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2) as success_rate
FROM agent_tasks
WHERE created_at > NOW() - INTERVAL '$interval' $where_clause
GROUP BY agent_id
ORDER BY total_cost_usd DESC;
EOF
}

# テーブル形式で表示
display_table() {
    local result=$1
    
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   Multi-Agent Cost Report - Period: ${PERIOD}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    printf "${YELLOW}%-20s %10s %12s %12s %15s %10s${NC}\n" \
        "Agent ID" "Tasks" "Input Tokens" "Output Tokens" "Total Cost (USD)" "Success %"
    echo -e "${BLUE}─────────────────────────────────────────────────────────────────────────${NC}"
    
    echo "$result" | while IFS='|' read -r agent tasks input_tokens output_tokens cost avg_cost avg_time success error rate; do
        # 空行スキップ
        [[ -z "$agent" || "$agent" == "agent_id" ]] && continue
        
        # トリム
        agent=$(echo "$agent" | xargs)
        tasks=$(echo "$tasks" | xargs)
        input_tokens=$(echo "$input_tokens" | xargs)
        output_tokens=$(echo "$output_tokens" | xargs)
        cost=$(echo "$cost" | xargs)
        rate=$(echo "$rate" | xargs)
        
        # コストに応じて色分け
        if (( $(echo "$cost > 10" | bc -l 2>/dev/null || echo 0) )); then
            color=$RED
        elif (( $(echo "$cost > 1" | bc -l 2>/dev/null || echo 0) )); then
            color=$YELLOW
        else
            color=$GREEN
        fi
        
        printf "${color}%-20s${NC} %10s %12s %12s %15s %10s\n" \
            "$agent" "$tasks" "$input_tokens" "$output_tokens" "\$$cost" "${rate}%"
    done
    
    echo -e "${BLUE}─────────────────────────────────────────────────────────────────────────${NC}\n"
    
    # 合計計算
    local total_cost=$(echo "$result" | tail -n +3 | awk -F'|' '{sum+=$5} END {printf "%.4f", sum}')
    local total_tasks=$(echo "$result" | tail -n +3 | awk -F'|' '{sum+=$2} END {print sum}')
    
    echo -e "${GREEN}[SUMMARY]${NC}"
    echo -e "  Total Tasks:  ${YELLOW}$total_tasks${NC}"
    echo -e "  Total Cost:   ${YELLOW}\$$total_cost${NC}"
    echo -e "  Period:       ${YELLOW}$PERIOD${NC}"
    echo ""
}

# JSON形式で表示
display_json() {
    local result=$1
    
    echo "{"
    echo "  \"period\": \"$PERIOD\","
    echo "  \"generated_at\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
    echo "  \"agents\": ["
    
    local first=true
    echo "$result" | tail -n +3 | while IFS='|' read -r agent tasks input_tokens output_tokens cost avg_cost avg_time success error rate; do
        [[ -z "$agent" ]] && continue
        
        if [[ "$first" == "false" ]]; then
            echo "    ,"
        fi
        first=false
        
        cat << JSON
    {
      "agent_id": "$(echo $agent | xargs)",
      "total_tasks": $(echo $tasks | xargs),
      "input_tokens": $(echo $input_tokens | xargs),
      "output_tokens": $(echo $output_tokens | xargs),
      "total_cost_usd": $(echo $cost | xargs),
      "avg_cost_per_task": $(echo $avg_cost | xargs),
      "avg_execution_time_seconds": $(echo $avg_time | xargs),
      "success_count": $(echo $success | xargs),
      "error_count": $(echo $error | xargs),
      "success_rate": $(echo $rate | xargs)
    }
JSON
    done
    
    echo "  ]"
    echo "}"
}

# CSV形式で表示
display_csv() {
    local result=$1
    
    echo "agent_id,total_tasks,input_tokens,output_tokens,total_cost_usd,avg_cost_per_task,avg_execution_time_seconds,success_count,error_count,success_rate"
    
    echo "$result" | tail -n +3 | while IFS='|' read -r agent tasks input_tokens output_tokens cost avg_cost avg_time success error rate; do
        [[ -z "$agent" ]] && continue
        echo "$(echo $agent | xargs),$(echo $tasks | xargs),$(echo $input_tokens | xargs),$(echo $output_tokens | xargs),$(echo $cost | xargs),$(echo $avg_cost | xargs),$(echo $avg_time | xargs),$(echo $success | xargs),$(echo $error | xargs),$(echo $rate | xargs)"
    done
}

# メイン処理
main() {
    check_database
    
    echo -e "${BLUE}[INFO]${NC} Querying agent costs..."
    
    local query=$(get_cost_query)
    local result=$(docker compose exec -T postgres psql -U openclaw -d openclaw -c "$query" 2>/dev/null)
    
    if [[ -z "$result" ]]; then
        echo -e "${RED}[ERROR]${NC} No data found"
        exit 1
    fi
    
    case $FORMAT in
        table)
            display_table "$result"
            ;;
        json)
            display_json "$result"
            ;;
        csv)
            display_csv "$result"
            ;;
        *)
            echo -e "${RED}[ERROR]${NC} Unknown format: $FORMAT"
            exit 1
            ;;
    esac
    
    # CSVエクスポート
    if [[ "$EXPORT_CSV" == "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} Exporting to CSV: $OUTPUT_FILE"
        display_csv "$result" > "$OUTPUT_FILE"
        echo -e "${GREEN}[OK]${NC} Export completed"
    fi
}

main "$@"
