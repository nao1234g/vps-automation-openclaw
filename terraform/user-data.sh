#!/bin/bash

# ==============================================================================
# OpenClaw VPS User Data Script
# ==============================================================================
# このスクリプトはEC2インスタンス起動時に自動実行されます
# ==============================================================================

set -euo pipefail

# ログ設定
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "========================================="
echo "OpenClaw VPS Setup Started"
echo "Date: $(date)"
echo "========================================="

# ==============================================================================
# Variables (Terraformから渡される)
# ==============================================================================

DOMAIN_NAME="${domain_name}"
ENVIRONMENT="${environment}"
ANTHROPIC_API_KEY="${anthropic_api_key}"
TELEGRAM_BOT_TOKEN="${telegram_bot_token}"
TELEGRAM_CHAT_ID="${telegram_chat_id}"
POSTGRES_PASSWORD="${postgres_password}"
N8N_ENCRYPTION_KEY="${n8n_encryption_key}"
GRAFANA_ADMIN_PASSWORD="${grafana_admin_password}"

# ==============================================================================
# System Update
# ==============================================================================

echo "[1/8] システムアップデート中..."
apt-get update
apt-get upgrade -y

# ==============================================================================
# Install Required Packages
# ==============================================================================

echo "[2/8] 必要なパッケージをインストール中..."
apt-get install -y \
  git \
  curl \
  wget \
  vim \
  htop \
  unzip \
  jq \
  make \
  build-essential \
  ca-certificates \
  gnupg \
  lsb-release \
  fail2ban \
  ufw

# ==============================================================================
# Install Docker
# ==============================================================================

echo "[3/8] Docker をインストール中..."

# Docker の GPG キーを追加
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Docker リポジトリを追加
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker をインストール
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Docker を有効化
systemctl enable docker
systemctl start docker

# ubuntu ユーザーを docker グループに追加
usermod -aG docker ubuntu

# ==============================================================================
# UFW Firewall Setup
# ==============================================================================

echo "[4/8] ファイアウォールを設定中..."

# UFW を有効化
ufw --force enable

# デフォルトポリシー
ufw default deny incoming
ufw default allow outgoing

# SSH (22)
ufw allow 22/tcp comment 'SSH'

# HTTP (80)
ufw allow 80/tcp comment 'HTTP'

# HTTPS (443)
ufw allow 443/tcp comment 'HTTPS'

# UFW ステータス確認
ufw status verbose

# ==============================================================================
# Fail2ban Setup
# ==============================================================================

echo "[5/8] Fail2ban を設定中..."

# Fail2ban を有効化
systemctl enable fail2ban
systemctl start fail2ban

# カスタム設定
cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s
EOF

systemctl restart fail2ban

# ==============================================================================
# Clone OpenClaw Repository
# ==============================================================================

echo "[6/8] OpenClaw リポジトリをクローン中..."

cd /opt
git clone https://github.com/nao1234g/vps-automation-openclaw.git openclaw
cd openclaw

# ==============================================================================
# Setup Environment Variables
# ==============================================================================

echo "[7/8] 環境変数を設定中..."

cat > .env <<EOF
# Environment
NODE_ENV=$${ENVIRONMENT}
ENVIRONMENT=$${ENVIRONMENT}

# Domain
DOMAIN_NAME=$${DOMAIN_NAME}

# Database
POSTGRES_USER=openclaw
POSTGRES_PASSWORD=$${POSTGRES_PASSWORD}
POSTGRES_DB=openclaw

# API Keys
ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY}

# Telegram
TELEGRAM_BOT_TOKEN=$${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=$${TELEGRAM_CHAT_ID}

# N8N
N8N_HOST=n8n.$${DOMAIN_NAME}
N8N_ENCRYPTION_KEY=$${N8N_ENCRYPTION_KEY}

# Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=$${GRAFANA_ADMIN_PASSWORD}

# Session & Security
SESSION_SECRET=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)

# Timezone
TZ=Asia/Tokyo
GENERIC_TIMEZONE=Asia/Tokyo
EOF

# 権限設定
chown -R ubuntu:ubuntu /opt/openclaw
chmod 600 /opt/openclaw/.env

# ==============================================================================
# Start Docker Compose
# ==============================================================================

echo "[8/8] Docker Compose を起動中..."

cd /opt/openclaw
docker compose -f docker-compose.production.yml up -d

# サービスが起動するまで待機
echo "サービスの起動を待機中..."
sleep 30

# ==============================================================================
# Setup SSL Certificate (Let's Encrypt)
# ==============================================================================

echo "SSL証明書を取得中..."

# Certbot のインストール
apt-get install -y certbot

# SSL証明書の取得（本番環境のみ）
if [ "$ENVIRONMENT" = "production" ]; then
  certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --email admin@$${DOMAIN_NAME} \
    -d $${DOMAIN_NAME} \
    -d www.$${DOMAIN_NAME}

  # 自動更新設定
  echo "0 3 * * * root certbot renew --quiet" >> /etc/crontab
fi

# ==============================================================================
# Setup Cron Jobs
# ==============================================================================

echo "Cron ジョブを設定中..."

# バックアップ（毎日 3:00 AM）
echo "0 3 * * * ubuntu cd /opt/openclaw && ./scripts/backup.sh > /var/log/openclaw-backup.log 2>&1" >> /etc/crontab

# ヘルスチェック（毎時）
echo "0 * * * * ubuntu cd /opt/openclaw && ./scripts/health_check.sh > /var/log/openclaw-health.log 2>&1" >> /etc/crontab

# セキュリティスキャン（毎日 1:00 AM）
echo "0 1 * * * ubuntu cd /opt/openclaw && ./scripts/security_scan.sh > /var/log/openclaw-security.log 2>&1" >> /etc/crontab

# システムメンテナンス（毎週日曜日 4:00 AM）
echo "0 4 * * 0 ubuntu cd /opt/openclaw && ./scripts/maintenance.sh > /var/log/openclaw-maintenance.log 2>&1" >> /etc/crontab

# ==============================================================================
# Health Check
# ==============================================================================

echo "ヘルスチェック実行中..."

sleep 10

# Docker コンテナの状態確認
docker ps

# ヘルスチェックスクリプト実行
cd /opt/openclaw
sudo -u ubuntu ./scripts/health_check.sh || true

# ==============================================================================
# Completion
# ==============================================================================

echo "========================================="
echo "OpenClaw VPS Setup Completed!"
echo "Date: $(date)"
echo ""
echo "Access your application at:"
echo "  https://$${DOMAIN_NAME}"
echo ""
echo "Grafana:"
echo "  https://$${DOMAIN_NAME}/grafana"
echo ""
echo "N8N:"
echo "  https://$${DOMAIN_NAME}/n8n"
echo ""
echo "========================================="

# Telegram通知（オプション）
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
  curl -s -X POST "https://api.telegram.org/bot$${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=$${TELEGRAM_CHAT_ID}" \
    -d "text=✅ OpenClaw VPS セットアップ完了！%0A%0AURL: https://$${DOMAIN_NAME}" > /dev/null || true
fi

# セットアップ完了フラグ
touch /opt/openclaw/.setup-complete
