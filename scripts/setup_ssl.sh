#!/bin/bash
#
# SSL/TLS Certificate Setup Script
# Let's Encryptを使用してSSL証明書を取得・更新
#
# 使用方法: sudo ./setup_ssl.sh [ドメイン名] [メールアドレス]
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
    echo "使用方法: sudo $0 [ドメイン名] [メールアドレス]"
    exit 1
fi

# プロジェクトディレクトリ
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# .envファイルの読み込み
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
fi

# パラメータ設定
DOMAIN=${1:-${DOMAIN_NAME}}
EMAIL=${2:-${LETSENCRYPT_EMAIL}}

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    log_error "ドメイン名とメールアドレスが必要です。"
    echo "使用方法: sudo $0 <ドメイン名> <メールアドレス>"
    echo "または、.envファイルにDOMAIN_NAMEとLETSENCRYPT_EMAILを設定してください。"
    exit 1
fi

log_info "=== SSL証明書セットアップ開始 ==="
log_info "ドメイン: $DOMAIN"
log_info "Email: $EMAIL"

# ============================================
# Certbotのインストール
# ============================================
log_section "Certbotのインストール"

if ! command -v certbot &> /dev/null; then
    log_info "Certbotをインストール中..."

    apt update
    apt install -y certbot python3-certbot-nginx

    log_info "Certbotのインストールが完了しました。"
else
    log_info "Certbotは既にインストールされています。"
    certbot --version
fi

# ============================================
# ファイアウォール設定の確認
# ============================================
log_section "ファイアウォール設定の確認"

log_info "HTTP/HTTPSポートの確認..."

if command -v ufw &> /dev/null; then
    # HTTP (80)
    if ! ufw status | grep -q "80/tcp"; then
        log_info "HTTP (80) ポートを開放中..."
        ufw allow 80/tcp
    fi

    # HTTPS (443)
    if ! ufw status | grep -q "443/tcp"; then
        log_info "HTTPS (443) ポートを開放中..."
        ufw allow 443/tcp
    fi

    ufw status
else
    log_warn "UFWがインストールされていません。"
fi

# ============================================
# DNS設定の確認
# ============================================
log_section "DNS設定の確認"

log_info "DNSレコードを確認中..."

DOMAIN_IP=$(dig +short "$DOMAIN" @8.8.8.8 | tail -1)
SERVER_IP=$(curl -s ifconfig.me)

log_info "ドメインIP: $DOMAIN_IP"
log_info "サーバーIP: $SERVER_IP"

if [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
    log_warn "⚠️ ドメインのDNSレコードがこのサーバーを指していません！"
    log_warn "DNSレコードを以下に設定してください:"
    log_warn "  タイプ: A"
    log_warn "  ホスト: @ または $DOMAIN"
    log_warn "  値: $SERVER_IP"
    echo ""
    read -p "DNSが正しく設定されていますか？ (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "DNS設定を確認してから再度実行してください。"
        exit 0
    fi
else
    log_info "✓ DNS設定が正しく設定されています。"
fi

# ============================================
# Nginxの設定確認
# ============================================
log_section "Nginx設定の確認"

if docker compose ps | grep -q "nginx"; then
    log_info "Nginxコンテナが実行中です。"

    # 一時的にNginxを停止（Certbot standaloneモード用）
    log_info "Nginxを一時停止中..."
    docker compose stop nginx || true
else
    log_info "Nginxコンテナは実行されていません。"
fi

# ============================================
# SSL証明書の取得
# ============================================
log_section "SSL証明書の取得"

SSL_DIR="$PROJECT_DIR/docker/nginx/ssl"
mkdir -p "$SSL_DIR"

log_info "Let's Encryptから証明書を取得中..."

# Certbot standaloneモード
certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    -d "$DOMAIN" \
    --preferred-challenges http

if [ $? -eq 0 ]; then
    log_info "✓ SSL証明書の取得に成功しました！"

    # 証明書をプロジェクトディレクトリにコピー
    log_info "証明書をコピー中..."

    cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/fullchain.pem"
    cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/privkey.pem"
    cp "/etc/letsencrypt/live/$DOMAIN/chain.pem" "$SSL_DIR/chain.pem"

    chmod 644 "$SSL_DIR/fullchain.pem"
    chmod 600 "$SSL_DIR/privkey.pem"
    chmod 644 "$SSL_DIR/chain.pem"

    log_info "証明書を $SSL_DIR にコピーしました。"
else
    log_error "SSL証明書の取得に失敗しました。"
    exit 1
fi

# ============================================
# 自動更新の設定
# ============================================
log_section "SSL証明書の自動更新設定"

# Certbot更新スクリプト
RENEW_SCRIPT="/etc/cron.d/certbot-renew"

log_info "自動更新cronジョブを設定中..."

cat > "$RENEW_SCRIPT" <<EOF
# SSL証明書の自動更新
# 毎日 2:30 AM に証明書の更新確認を実行

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

30 2 * * * root certbot renew --quiet --deploy-hook "docker compose -f $PROJECT_DIR/docker-compose.yml restart nginx" >> /var/log/certbot-renew.log 2>&1
EOF

chmod 644 "$RENEW_SCRIPT"

log_info "自動更新cronジョブを設定しました。"

# ============================================
# Nginxの起動
# ============================================
log_section "Nginxの起動"

cd "$PROJECT_DIR"

if [ -f "docker-compose.yml" ]; then
    log_info "Nginxコンテナを起動中..."
    docker compose up -d nginx

    log_info "Nginxが起動しました。"

    # 設定テスト
    sleep 3
    docker compose exec nginx nginx -t || log_warn "Nginx設定にエラーがあります。"
else
    log_warn "docker-compose.ymlが見つかりません。"
fi

# ============================================
# SSL設定の確認
# ============================================
log_section "SSL設定の確認"

log_info "SSL証明書情報:"
openssl x509 -in "$SSL_DIR/fullchain.pem" -text -noout | grep -E "(Subject:|Issuer:|Not Before|Not After)"

echo ""
log_info "証明書の有効期限:"
openssl x509 -in "$SSL_DIR/fullchain.pem" -noout -dates

# ============================================
# 完了
# ============================================
log_section "SSL証明書セットアップ完了"

echo ""
echo "SSL証明書情報:"
echo "===================="
echo "ドメイン: $DOMAIN"
echo "証明書ディレクトリ: $SSL_DIR"
echo "証明書ファイル:"
echo "  - fullchain.pem (公開鍵+中間証明書)"
echo "  - privkey.pem (秘密鍵)"
echo "  - chain.pem (中間証明書)"
echo ""
echo "自動更新:"
echo "  毎日 2:30 AM に証明書の更新確認"
echo "  証明書は有効期限の30日前から更新可能"
echo ""
echo "次のステップ:"
echo "1. https://$DOMAIN にアクセスして確認"
echo "2. SSL Labs でセキュリティチェック: https://www.ssllabs.com/ssltest/"
echo "3. Nginx設定を確認: docker compose exec nginx nginx -t"
echo ""
echo "手動更新コマンド:"
echo "  sudo certbot renew"
echo ""

log_info "SSL証明書のセットアップが完了しました。"
