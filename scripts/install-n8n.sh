#!/bin/bash
# N8N Installation Script for ConoHa VPS
# Run this script on the VPS to install N8N

set -e

echo "🚀 N8N インストール開始..."

# Step 1: Check Docker
echo "📦 Step 1: Docker確認..."
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
fi
docker --version

# Step 2: Create N8N directory
echo "📁 Step 2: ディレクトリ作成..."
mkdir -p /opt/n8n
cd /opt/n8n

# Step 3: Run N8N container
echo "🐳 Step 3: N8Nコンテナ起動..."
docker stop n8n 2>/dev/null || true
docker rm n8n 2>/dev/null || true

docker run -d \
  --name n8n \
  --restart always \
  -p 5678:5678 \
  -e N8N_HOST=n8n.163.44.124.123.nip.io \
  -e N8N_PORT=5678 \
  -e N8N_PROTOCOL=https \
  -e WEBHOOK_URL=https://n8n.163.44.124.123.nip.io/ \
  -e GENERIC_TIMEZONE=Asia/Tokyo \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n

# Step 4: Open firewall port
echo "🔥 Step 4: ファイアウォール設定..."
ufw allow 5678/tcp
ufw reload

# Step 5: Add Caddy reverse proxy
echo "🔒 Step 5: Caddyリバースプロキシ追加..."
if ! grep -q "n8n.163.44.124.123.nip.io" /etc/caddy/Caddyfile; then
    cat >> /etc/caddy/Caddyfile << 'EOF'

n8n.163.44.124.123.nip.io {
    reverse_proxy localhost:5678
}
EOF
fi

# Step 6: Restart Caddy
echo "🔄 Step 6: Caddy再起動..."
systemctl restart caddy

# Step 7: Wait for N8N to start
echo "⏳ Step 7: N8N起動待機..."
sleep 10

# Step 8: Verify
echo "✅ Step 8: 動作確認..."
docker ps | grep n8n
curl -s -o /dev/null -w "%{http_code}" http://localhost:5678/ || echo "Waiting..."

echo ""
echo "🎉 N8Nインストール完了！"
echo ""
echo "アクセスURL: https://n8n.163.44.124.123.nip.io/"
echo ""
echo "初回アクセス時にアカウント作成画面が表示されます。"
