#!/bin/bash
# Neo → Jarvis Task Sender
# Usage: ./send-task-to-jarvis.sh "タスク内容"

set -e

if [ -z "$1" ]; then
  echo "使用方法: $0 'タスク内容'"
  echo "例: $0 'X APIの最新情報を調査してください'"
  exit 1
fi

TASK_MESSAGE="$1"
TASK_FILE="/opt/shared/neo-tasks/new/task_$(date +%Y%m%d_%H%M%S).md"

# Create task file
cat > "$TASK_FILE" <<EOF
# Neo からのタスク
作成日時: $(date '+%Y-%m-%d %H:%M:%S')

## タスク内容
$TASK_MESSAGE

## 指示
- このタスクを適切なエージェントに委任してください
- 完了後、結果をTelegram経由で報告してください
- 緊急度: 通常

---
From: Neo (Claude Opus 4.6)
To: Jarvis (OpenClaw CSO)
EOF

echo "✅ タスクを送信しました: $TASK_FILE"
echo "📋 内容: $TASK_MESSAGE"
echo "⏰ 5分以内にJarvisが処理を開始します"
