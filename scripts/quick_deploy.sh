#!/bin/bash
# ============================================
# OpenClaw VPS - Quick Deploy Script
# ワンコマンドでOpenClawを起動するスクリプト
# ============================================
#
# 使用方法:
#   ./scripts/quick_deploy.sh
#   または: make quick-deploy
#
# 前提条件:
#   - Docker & Docker Compose がインストール済み
#   - .env ファイルが設定済み（ANTHROPIC_API_KEY が必須）
# ============================================

set -e

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo ""
echo "============================================"
echo "  OpenClaw VPS - Quick Deploy"
echo "============================================"
echo ""

# ステップ1: 前提条件チェック
log_info "前提条件をチェック中..."

# Docker チェック
if ! command -v docker &> /dev/null; then
    log_error "Docker がインストールされていません"
    echo "  インストール: curl -fsSL https://get.docker.com | sh"
    exit 1
fi
log_success "Docker: OK"

# Docker Compose チェック
if ! docker compose version &> /dev/null; then
    log_error "Docker Compose がインストールされていません"
    exit 1
fi
log_success "Docker Compose: OK"

# ステップ2: 環境変数ファイルチェック
log_info "環境変数ファイルをチェック中..."

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        log_warn ".env ファイルが見つかりません。.env.example からコピーします..."
        cp .env.example .env
        log_warn "重要: .env ファイルを編集して ANTHROPIC_API_KEY を設定してください！"
        echo ""
        echo "  nano .env"
        echo "  # または"
        echo "  vim .env"
        echo ""
        echo "最低限必要な設定:"
        echo "  ANTHROPIC_API_KEY=sk-ant-xxxxx"
        echo ""
        read -p "設定が完了したら Enter を押してください..." -r
    else
        log_error ".env.example ファイルが見つかりません"
        exit 1
    fi
fi

# ANTHROPIC_API_KEY のチェック
source .env 2>/dev/null || true
if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "sk-ant-CHANGE_ME" ]; then
    log_error "ANTHROPIC_API_KEY が設定されていません"
    echo ""
    echo "  .env ファイルを編集して ANTHROPIC_API_KEY を設定してください:"
    echo "  nano .env"
    echo ""
    exit 1
fi
log_success "環境変数: OK"

# ステップ3: 必要なディレクトリ作成
log_info "ディレクトリを準備中..."
mkdir -p docker/postgres/init
mkdir -p skills
log_success "ディレクトリ: OK"

# PostgreSQL 初期化スクリプト作成（存在しない場合）
if [ ! -f "docker/postgres/init/00-init.sql" ]; then
    log_info "PostgreSQL 初期化スクリプトを作成中..."
    cat > docker/postgres/init/00-init.sql << 'EOF'
-- OpenClaw Database Initialization
-- N8N用のスキーマを作成
CREATE SCHEMA IF NOT EXISTS n8n;

-- 必要な拡張を有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ログ出力
DO $$
BEGIN
    RAISE NOTICE 'OpenClaw database initialized successfully';
END $$;
EOF
    log_success "初期化スクリプト: 作成完了"
fi

# ステップ4: 既存コンテナの停止
log_info "既存のコンテナを停止中..."
docker compose -f docker-compose.quick.yml down --remove-orphans 2>/dev/null || true
log_success "クリーンアップ: OK"

# ステップ5: イメージのビルドと起動
log_info "OpenClaw をビルド・起動中..."
echo ""

docker compose -f docker-compose.quick.yml up -d --build

echo ""

# ステップ6: ヘルスチェック
log_info "サービスの起動を確認中..."

# PostgreSQL の起動を待機
echo -n "  PostgreSQL: "
for i in {1..30}; do
    if docker compose -f docker-compose.quick.yml exec -T postgres pg_isready -U "${POSTGRES_USER:-openclaw}" &>/dev/null; then
        echo -e "${GREEN}起動完了${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# OpenClaw の起動を待機
echo -n "  OpenClaw: "
for i in {1..60}; do
    if curl -s http://localhost:3000/health &>/dev/null; then
        echo -e "${GREEN}起動完了${NC}"
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${YELLOW}起動中...（バックグラウンドで継続）${NC}"
    else
        echo -n "."
        sleep 3
    fi
done

# N8N の起動を待機
echo -n "  N8N: "
for i in {1..30}; do
    if curl -s http://localhost:5678/healthz &>/dev/null; then
        echo -e "${GREEN}起動完了${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${YELLOW}起動中...（バックグラウンドで継続）${NC}"
    else
        echo -n "."
        sleep 2
    fi
done

echo ""
echo "============================================"
log_success "OpenClaw VPS デプロイ完了！"
echo "============================================"
echo ""
echo "アクセス先:"
echo "  🤖 OpenClaw API:  http://localhost:3000"
echo "  🔄 N8N:           http://localhost:5678"
echo "  🗄️  PostgreSQL:    localhost:5432"
echo ""
echo "N8N ログイン情報:"
echo "  ユーザー: ${N8N_USER:-admin}"
echo "  パスワード: （.env の N8N_PASSWORD を確認）"
echo ""
echo "ログ確認:"
echo "  docker compose -f docker-compose.quick.yml logs -f"
echo ""
echo "停止:"
echo "  docker compose -f docker-compose.quick.yml down"
echo ""
echo "============================================"
