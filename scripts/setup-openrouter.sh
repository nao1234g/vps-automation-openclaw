#!/bin/bash
# OpenRouter APIキーをOpenClawに設定

set -e

echo "🔧 OpenRouter APIキー設定スクリプト"
echo "=================================="
echo ""

# APIキーを入力
read -p "OpenRouter APIキー (sk-or-v1-...): " OPENROUTER_KEY

if [[ ! $OPENROUTER_KEY =~ ^sk-or-v1- ]]; then
    echo "❌ エラー: 正しいOpenRouter APIキーを入力してください"
    exit 1
fi

echo ""
echo "📝 OpenClawに設定中..."

# OpenClawコンテナに環境変数を追加
docker exec openclaw-agent sh -c "echo 'OPENROUTER_API_KEY=$OPENROUTER_KEY' >> /home/appuser/.openclaw/.env"

echo "✅ 環境変数を追加しました"

# OpenRouterプロバイダーを登録
echo ""
echo "📡 OpenRouterプロバイダーを登録中..."

docker exec openclaw-agent openclaw onboard --auth-choice openrouter

echo ""
echo "✅ 設定完了！"
echo ""
echo "次のステップ:"
echo "1. エージェントのモデル設定を変更"
echo "2. OpenClawを再起動"
echo ""
