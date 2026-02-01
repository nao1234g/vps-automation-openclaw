#!/bin/bash

# OpenClaw自動セットアップスクリプト
# ConoHa VPS / Ubuntu 22.04対応

set -e  # エラーで停止

echo "====================================="
echo "  OpenClaw自動インストール開始"
echo "====================================="

# Step 1: システムアップデート
echo "[1/7] システムアップデート中..."
sudo apt update && sudo apt upgrade -y

# Step 2: Node.js 20.xのインストール
echo "[2/7] Node.js 20.xインストール中..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
fi

echo "Node.js version: $(node -v)"
echo "npm version: $(npm -v)"

# Step 3: 必要なパッケージのインストール
echo "[3/7] 依存パッケージインストール中..."
sudo apt install -y git build-essential

# Step 4: OpenClawのクローン
echo "[4/7] OpenClawリポジトリをクローン中..."
INSTALL_DIR="/opt/open-claw"
if [ -d "$INSTALL_DIR" ]; then
    echo "既存のディレクトリを検出。更新します..."
    cd $INSTALL_DIR
    sudo git pull
else
    sudo git clone https://github.com/Sh-Osakana/open-claw.git $INSTALL_DIR
    cd $INSTALL_DIR
fi

# Step 5: npm依存関係のインストール
echo "[5/7] npm依存関係インストール中..."
sudo npm install

# Step 6: 環境変数ファイルの作成
echo "[6/7] 環境変数ファイル作成中..."
if [ ! -f ".env" ]; then
    cat > .env << 'ENVEOF'
# LLM Provider設定
ANTHROPIC_API_KEY=your_api_key_here
# または ZhipuAI GLM-4を使用する場合
# ZHIPUAI_API_KEY=your_zhipuai_api_key
# MODEL_PROVIDER=zhipuai
# MODEL_NAME=glm-4-flash

# Telegramボット設定
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# セキュリティ設定
ALLOWED_HOSTS=localhost,127.0.0.1
PORT=3000
ENVEOF
    echo ".envファイルを作成しました。APIキーを設定してください。"
else
    echo ".envファイルは既に存在します。"
fi

# Step 7: systemdサービスの作成
echo "[7/7] systemdサービス設定中..."
sudo tee /etc/systemd/system/openclaw.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=OpenClaw AI Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/open-claw
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable openclaw

echo "====================================="
echo "  インストール完了！"
echo "====================================="
echo ""
echo "次のステップ："
echo "1. .envファイルを編集してAPIキーを設定"
echo "   sudo nano /opt/open-claw/.env"
echo ""
echo "2. OpenClawを起動"
echo "   sudo systemctl start openclaw"
echo ""
echo "3. ステータス確認"
echo "   sudo systemctl status openclaw"
echo ""
echo "4. ログ確認"
echo "   sudo journalctl -u openclaw -f"
echo ""

