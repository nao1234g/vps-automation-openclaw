#!/bin/bash
# VS CodeからNeoのTelegramにメッセージを送信

set -e

# VPS接続情報
VPS_HOST="163.44.124.123"
VPS_USER="root"
SSH_KEY="$HOME/.ssh/conoha_ed25519"

# メッセージ（引数から取得）
MESSAGE="$1"

if [ -z "$MESSAGE" ]; then
  echo "使い方: ./send-to-neo.sh \"メッセージ内容\""
  echo ""
  echo "例:"
  echo "  ./send-to-neo.sh \"X API料金について調べて\""
  echo "  ./send-to-neo.sh \"レポートを読んで: /opt/shared/reports/2026-02-15_X-API-auto-post-complete.md\""
  exit 1
fi

echo "📤 Neoにメッセージを送信中..."

# プログレス表示用の関数
show_progress() {
  local seconds=0
  local spinner='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
  while true; do
    for (( i=0; i<${#spinner}; i++ )); do
      printf "\r${spinner:$i:1} 送信中... (${seconds}s) " >&2
      sleep 0.1
    done
    ((seconds++))
  done
}

# プログレス表示開始（バックグラウンド）
show_progress &
PROGRESS_PID=$!

# VPS上でTelegram Bot APIを叩いてメッセージを送信
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" -o ConnectTimeout=60 -o ServerAliveInterval=15 << EOF
# Bot TokenとChat IDを取得
BOT_TOKEN=\$(grep TELEGRAM_BOT_TOKEN /opt/claude-code-telegram/.env | cut -d= -f2)
CHAT_ID=\$(grep ALLOWED_USERS /opt/claude-code-telegram/.env | cut -d= -f2)

if [ -z "\$CHAT_ID" ]; then
  echo "❌ Chat IDが見つかりません"
  exit 1
fi

# メッセージを送信
RESPONSE=\$(curl -s -X POST "https://api.telegram.org/bot\${BOT_TOKEN}/sendMessage" \
  -d "chat_id=\${CHAT_ID}" \
  -d "text=${MESSAGE}")

# レスポンス確認
if echo "\${RESPONSE}" | grep -q '"ok":true'; then
  echo "✅ メッセージ送信完了"
  echo "📱 Telegramで確認してください"
else
  echo "❌ メッセージ送信失敗"
  echo "エラー: \${RESPONSE}"
  exit 1
fi
EOF

SSH_EXIT=$?

# プログレス表示停止（エラーでも続行）
kill $PROGRESS_PID 2>/dev/null || true
wait $PROGRESS_PID 2>/dev/null || true
printf "\r\033[K"  # 行をクリア

if [ $SSH_EXIT -eq 0 ]; then
  echo ""
  echo "✅ 送信処理完了"
else
  echo ""
  echo "⚠️ 接続エラーが発生しましたが、メッセージは送信された可能性があります"
  echo "📱 Telegramを確認してください"
fi

exit 0
