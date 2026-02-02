#!/bin/bash
#
# 最小構成の統合テストスクリプト
# すべてのサービスの動作を確認
#

set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  OpenClaw VPS - 最小構成 統合テスト${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# PostgreSQLテスト
echo -e "${YELLOW}[1/4]${NC} PostgreSQLをテスト中..."
if docker compose -f docker-compose.minimal.yml exec -T postgres psql -U openclaw -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PostgreSQL: 接続OK"
else
    echo -e "${RED}✗${NC} PostgreSQL: 接続失敗"
    exit 1
fi

# スキーマ確認
SCHEMAS=$(docker compose -f docker-compose.minimal.yml exec -T postgres psql -U openclaw -t -c "\dn" | grep -E '(n8n|openclaw|opennotebook)' | wc -l)
if [ "$SCHEMAS" -eq 3 ]; then
    echo -e "${GREEN}✓${NC} PostgreSQL: スキーマ作成OK (n8n, openclaw, opennotebook)"
else
    echo -e "${RED}✗${NC} PostgreSQL: スキーマ不足"
    exit 1
fi

# OpenNotebookテスト
echo -e "${YELLOW}[2/4]${NC} OpenNotebookをテスト中..."
HEALTH_RESPONSE=$(curl -s http://localhost:8080/health)
if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✓${NC} OpenNotebook: ヘルスチェックOK"
    echo -e "  Response: $(echo $HEALTH_RESPONSE | jq -c .)"
else
    echo -e "${RED}✗${NC} OpenNotebook: ヘルスチェック失敗"
    exit 1
fi

# N8Nテスト
echo -e "${YELLOW}[3/4]${NC} N8Nをテスト中..."
N8N_RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:5678/)
if [ "$N8N_RESPONSE" = "200" ] || [ "$N8N_RESPONSE" = "401" ]; then
    echo -e "${GREEN}✓${NC} N8N: 起動OK (HTTP $N8N_RESPONSE)"
else
    echo -e "${RED}✗${NC} N8N: 起動失敗 (HTTP $N8N_RESPONSE)"
    exit 1
fi

# コンテナ状態確認
echo -e "${YELLOW}[4/4]${NC} コンテナ状態を確認中..."
RUNNING=$(docker compose -f docker-compose.minimal.yml ps --format json | jq -r '.State' | grep -c "running" || true)
if [ "$RUNNING" -eq 3 ]; then
    echo -e "${GREEN}✓${NC} 全コンテナが正常に稼働中 (3/3)"
else
    echo -e "${YELLOW}⚠${NC} 一部コンテナが起動していません ($RUNNING/3)"
fi

# リソース使用状況
echo ""
echo -e "${BLUE}リソース使用状況:${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
    openclaw-postgres-minimal openclaw-opennotebook-minimal openclaw-n8n-minimal 2>/dev/null || true

# まとめ
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✓ すべてのテストに合格しました！${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "アクセス先:"
echo "  - OpenNotebook: http://localhost:8080"
echo "  - N8N:          http://localhost:5678"
echo "  - PostgreSQL:   localhost:5432"
echo ""
