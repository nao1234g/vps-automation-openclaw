#!/bin/bash
set -e
echo "🚀 ConoHa VPS OpenClaw 自動デプロイ開始..."
echo ""

# カラー定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== ステップ1: システム更新 ===${NC}"
apt update && apt upgrade -y

echo -e "${BLUE}=== ステップ2: Docker インストール ===${NC}"
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker

echo -e "${BLUE}=== ステップ3: Docker Compose インストール ===${NC}"
apt install -y docker-compose

echo -e "${BLUE}=== ステップ4: プロジェクトディレクトリ作成 ===${NC}"
mkdir -p /opt/openclaw
cd /opt/openclaw

echo -e "${BLUE}=== ステップ5: 設定ファイル作成 ===${NC}"
cat > .env << 'EOF'
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:?Please set ANTHROPIC_API_KEY environment variable}
DB_NAME=openclaw
DB_USER=openclaw
DB_PASSWORD=secure_postgres_password_$(openssl rand -hex 8)
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=${DB_NAME}
DB_HOST=db
EOF

echo -e "${GREEN}✅ デプロイ完了！${NC}"
echo ""
echo "次のコマンドで起動します："
echo "cd /opt/openclaw && docker compose up -d"
