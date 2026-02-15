#!/bin/bash
# X公式API投稿セットアップスクリプト（VPS）
set -e

echo "🚀 X公式API投稿セットアップ開始..."

# VPS接続情報
VPS_HOST="163.44.124.123"
VPS_USER="root"
SSH_KEY="$HOME/.ssh/conoha_ed25519"

# 認証情報（環境変数から読み込み、または直接設定）
TWITTER_API_KEY="${TWITTER_API_KEY:-DNQb67dsQEH7V3rjyKj4IM9bK}"
TWITTER_API_SECRET="${TWITTER_API_SECRET:-VZ8zi7wfVpglNGRif2ks8TD3WHHpIVB3PSbXxBqZJ0XlTcWC12}"
TWITTER_ACCESS_TOKEN="${TWITTER_ACCESS_TOKEN:-2022878624463118336-YepYQmIaHxAYCSKTmODNB9GhAm3FmZ}"
TWITTER_ACCESS_SECRET="${TWITTER_ACCESS_SECRET:-1Qv4nLEyevQ3GoOrAOMcB3Y1tJhxCBiEVLR39RA7ay43w}"

echo "📤 スクリプトをVPSにアップロード中..."
scp -i "$SSH_KEY" scripts/x-post-official-api.js "$VPS_USER@$VPS_HOST:/opt/x-post-official-api.js"

echo "🔧 VPS上でセットアップ中..."
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" << 'EOF'
  cd /opt

  # twitter-api-v2をインストール
  echo "📦 twitter-api-v2をインストール中..."
  if ! npm list twitter-api-v2 > /dev/null 2>&1; then
    npm install twitter-api-v2
  else
    echo "✅ twitter-api-v2は既にインストール済み"
  fi

  # 実行権限を付与
  chmod +x /opt/x-post-official-api.js

  echo "✅ VPS上のセットアップ完了"
EOF

echo "🔑 環境変数を設定中..."
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" << EOF
  # .env.x ファイルを作成（環境変数保存用）
  cat > /opt/.env.x << 'ENVFILE'
export TWITTER_API_KEY="$TWITTER_API_KEY"
export TWITTER_API_SECRET="$TWITTER_API_SECRET"
export TWITTER_ACCESS_TOKEN="$TWITTER_ACCESS_TOKEN"
export TWITTER_ACCESS_SECRET="$TWITTER_ACCESS_SECRET"
ENVFILE

  # 権限を600に設定（rootのみ読み書き可能）
  chmod 600 /opt/.env.x

  echo "✅ 環境変数を /opt/.env.x に保存しました"
EOF

echo ""
echo "🎉 セットアップ完了！"
echo ""
echo "📋 テスト投稿コマンド:"
echo "  ssh -i $SSH_KEY $VPS_USER@$VPS_HOST"
echo "  source /opt/.env.x && node /opt/x-post-official-api.js \"🚀 Test tweet from AISA!\""
echo ""
