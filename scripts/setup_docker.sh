#!/bin/bash

# OpenClaw VPS + Docker自動セットアップスクリプト
# ConoHa VPS / Ubuntu 22.04 + Docker対応

set -e

echo "============================================"
echo "  OpenClaw Docker環境セットアップ"
echo "  二重隔離で最強のセキュリティ構成"
echo "============================================"
echo ""

# Step 1: システムアップデート
echo "[1/6] システムアップデート..."
sudo apt update && sudo apt upgrade -y

# Step 2: Dockerのインストール
echo "[2/6] Dockerインストール..."
if ! command -v docker &> /dev/null; then
    # Docker公式リポジトリ追加
    sudo apt install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    
    echo \
      "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # 現在のユーザーをdockerグループに追加
    sudo usermod -aG docker $USER
    
    echo "✅ Docker インストール完了"
else
    echo "✅ Docker は既にインストール済み"
fi

echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker compose version)"

# Step 3: プロジェクトディレクトリ作成
echo "[3/6] プロジェクトディレクトリ作成..."
PROJECT_DIR="/opt/openclaw-docker"
sudo mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Step 4: GitHubからプロジェクトをクローン
echo "[4/6] GitHubリポジトリをクローン..."
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "既存のリポジトリを更新..."
    sudo git pull
else
    sudo git clone https://github.com/nao1234g/vps-automation-openclaw.git .
fi

# Step 5: 環境変数ファイルの設定
echo "[5/6] 環境変数ファイル設定..."
if [ ! -f ".env" ]; then
    sudo cp .env.example .env
    echo "⚠️  .envファイルを作成しました"
    echo "   APIキーとパスワードを設定してください："
    echo "   sudo nano /opt/openclaw-docker/.env"
else
    echo "✅ .env ファイルは既に存在します"
fi

# Step 6: 必要なディレクトリを作成
echo "[6/6] 必要なディレクトリ作成..."
sudo mkdir -p docker/nginx
sudo mkdir -p docker/n8n/workflows

echo ""
echo "============================================"
echo "  ✅ セットアップ完了！"
echo "============================================"
echo ""
echo "📝 次のステップ："
echo ""
echo "1. 環境変数を設定："
echo "   sudo nano /opt/openclaw-docker/.env"
echo ""
echo "2. .envファイルで必須項目を設定："
echo "   - ANTHROPIC_API_KEY または ZHIPUAI_API_KEY"
echo "   - TELEGRAM_BOT_TOKEN"
echo "   - TELEGRAM_CHAT_ID"
echo "   - POSTGRES_PASSWORD（デフォルトから変更推奨）"
echo ""
echo "3. Docker Composeでビルド＆起動："
echo "   cd /opt/openclaw-docker"
echo "   sudo docker compose up -d --build"
echo ""
echo "4. ログを確認："
echo "   sudo docker compose logs -f"
echo ""
echo "5. SSH Tunnelで接続（ローカルPCから）："
echo "   ssh -L 3000:localhost:3000 -L 5678:localhost:5678 -L 8080:localhost:8080 root@YOUR_VPS_IP"
echo ""
echo "6. ブラウザでアクセス："
echo "   OpenClaw:     http://localhost:3000"
echo "   N8N:          http://localhost:5678"
echo "   OpenNotebook: http://localhost:8080"
echo ""
echo "🔐 セキュリティ："
echo "   ✓ 全サービスは127.0.0.1のみバインド"
echo "   ✓ SSH Tunnelでのみ外部アクセス可能"
echo "   ✓ Dockerネットワークで内部隔離"
echo ""

