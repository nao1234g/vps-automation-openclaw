#!/bin/bash
#
# OpenClaw VPS - 環境変数バリデーションスクリプト
# .envファイルの必須環境変数をチェック
#
# 使用方法: ./scripts/validate_env.sh
#

set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# カウンター
ERRORS=0
WARNINGS=0

# ログ関数
log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ERRORS=$((ERRORS + 1))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

# .envファイルの存在確認
if [ ! -f .env ]; then
    log_error ".envファイルが見つかりません"
    echo ""
    echo "以下のコマンドで作成してください:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

echo "========================================="
echo "環境変数バリデーション"
echo "========================================="
echo ""

# .envファイルを読み込み
source .env

# ============================================
# 必須環境変数のチェック
# ============================================
echo "1. 必須環境変数のチェック"
echo ""

# Database
if [ -z "$POSTGRES_PASSWORD" ]; then
    log_error "POSTGRES_PASSWORD が設定されていません"
else
    if [ ${#POSTGRES_PASSWORD} -lt 12 ]; then
        log_warn "POSTGRES_PASSWORD が短すぎます（12文字以上推奨）"
    else
        log_success "POSTGRES_PASSWORD が設定されています"
    fi
fi

# LLM Providers（少なくとも1つ必要）
llm_count=0
if [ -n "$ANTHROPIC_API_KEY" ]; then
    log_success "ANTHROPIC_API_KEY が設定されています"
    llm_count=$((llm_count + 1))
fi

if [ -n "$OPENAI_API_KEY" ]; then
    log_success "OPENAI_API_KEY が設定されています"
    llm_count=$((llm_count + 1))
fi

if [ -n "$ZHIPUAI_API_KEY" ]; then
    log_success "ZHIPUAI_API_KEY が設定されています"
    llm_count=$((llm_count + 1))
fi

if [ $llm_count -eq 0 ]; then
    log_error "LLM Provider API Key（ANTHROPIC/OPENAI/ZHIPUAI）が1つも設定されていません"
fi

# Telegram
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    log_warn "TELEGRAM_BOT_TOKEN が設定されていません（Telegram通知を使用する場合は必須）"
else
    log_success "TELEGRAM_BOT_TOKEN が設定されています"
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    log_warn "TELEGRAM_CHAT_ID が設定されていません（Telegram通知を使用する場合は必須）"
else
    log_success "TELEGRAM_CHAT_ID が設定されています"
fi

# N8N
if [ -z "$N8N_ENCRYPTION_KEY" ]; then
    log_error "N8N_ENCRYPTION_KEY が設定されていません"
else
    if [ ${#N8N_ENCRYPTION_KEY} -lt 24 ]; then
        log_warn "N8N_ENCRYPTION_KEY が短すぎます（24文字以上推奨）"
    else
        log_success "N8N_ENCRYPTION_KEY が設定されています"
    fi
fi

if [ -z "$N8N_PASSWORD" ]; then
    log_warn "N8N_PASSWORD が設定されていません（デフォルト値を使用します）"
else
    if [ ${#N8N_PASSWORD} -lt 8 ]; then
        log_warn "N8N_PASSWORD が短すぎます（8文字以上推奨）"
    else
        log_success "N8N_PASSWORD が設定されています"
    fi
fi

# Security
if [ -z "$SESSION_SECRET" ]; then
    log_error "SESSION_SECRET が設定されていません"
else
    if [ ${#SESSION_SECRET} -lt 32 ]; then
        log_warn "SESSION_SECRET が短すぎます（32文字以上推奨）"
    else
        log_success "SESSION_SECRET が設定されています"
    fi
fi

if [ -z "$JWT_SECRET" ]; then
    log_error "JWT_SECRET が設定されていません"
else
    if [ ${#JWT_SECRET} -lt 32 ]; then
        log_warn "JWT_SECRET が短すぎます（32文字以上推奨）"
    else
        log_success "JWT_SECRET が設定されています"
    fi
fi

echo ""

# ============================================
# オプション環境変数のチェック
# ============================================
echo "2. オプション環境変数のチェック"
echo ""

# SSL/Domain
if [ -n "$DOMAIN_NAME" ]; then
    log_success "DOMAIN_NAME が設定されています: $DOMAIN_NAME"

    if [ -z "$SSL_EMAIL" ]; then
        log_warn "SSL_EMAIL が設定されていません（SSL証明書取得に必要）"
    else
        log_success "SSL_EMAIL が設定されています"
    fi
else
    log_warn "DOMAIN_NAME が設定されていません（HTTPアクセスのみ）"
fi

# Backup
if [ -n "$S3_BUCKET" ]; then
    log_success "S3_BUCKET が設定されています（S3バックアップ有効）"

    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        log_warn "AWS認証情報が設定されていません（S3バックアップに必要）"
    fi
fi

echo ""

# ============================================
# セキュリティチェック
# ============================================
echo "3. セキュリティチェック"
echo ""

# デフォルト値のチェック
if [ "$POSTGRES_PASSWORD" = "changeme" ] || [ "$POSTGRES_PASSWORD" = "password" ]; then
    log_error "POSTGRES_PASSWORD にデフォルト値が使用されています"
fi

if [ "$N8N_PASSWORD" = "changeme" ] || [ "$N8N_PASSWORD" = "password" ]; then
    log_error "N8N_PASSWORD にデフォルト値が使用されています"
fi

# .envファイルのパーミッション
env_perms=$(stat -c %a .env 2>/dev/null || stat -f %A .env 2>/dev/null)
if [ "$env_perms" != "600" ]; then
    log_warn ".envファイルのパーミッションが600ではありません（現在: $env_perms）"
    echo "  推奨コマンド: chmod 600 .env"
else
    log_success ".envファイルのパーミッションが適切です（600）"
fi

# .gitignoreに.envが含まれているか
if grep -q "^\.env$" .gitignore 2>/dev/null; then
    log_success ".envファイルがGit除外されています"
else
    log_error ".envファイルがGit除外されていません（.gitignoreに追加してください）"
fi

echo ""

# ============================================
# 結果サマリー
# ============================================
echo "========================================="
echo "検証結果"
echo "========================================="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ すべてのチェックに合格しました${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ 警告: $WARNINGS 件の問題があります${NC}"
    echo ""
    echo "推奨事項:"
    echo "  - 警告を確認して、必要に応じて修正してください"
    exit 0
else
    echo -e "${RED}✗ エラー: $ERRORS 件、警告: $WARNINGS 件${NC}"
    echo ""
    echo "必須事項:"
    echo "  - エラーを修正してから続行してください"
    echo "  - パスワード生成: openssl rand -base64 32"
    exit 1
fi
