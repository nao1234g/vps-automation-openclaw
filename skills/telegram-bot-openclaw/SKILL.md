---
name: telegram-bot-openclaw
description: "OpenClaw と Telegram Bot を統合し、チャットベースでAIエージェントを操作する完全ガイド"
source: community
risk: safe
tags:
  - telegram
  - bot
  - openclaw
  - chat-interface
  - automation
related_skills:
  - @n8n-openclaw-integration
  - @openclaw-pairing
  - @multi-agent-orchestration
---

# Telegram Bot + OpenClaw 統合

## Overview

Telegram Bot API と OpenClaw Gateway を連携させ、チャットインターフェースからAIエージェント（Jarvis、Alice、Luna等）を操作します。BotFather でボットを作成し、OpenClaw に接続し、ペアリング承認を完了することで、どこからでもスマホ・PCからAIエージェントにタスクを依頼できます。

## When to Use This Skill

このスキルを使用する場面：

- ✅ スマホからAIエージェントにタスクを依頼したい
- ✅ OpenClaw をコマンドラインではなくチャットで操作したい
- ✅ N8N ワークフローの実行結果を Telegram に通知したい
- ✅ リモートワーク中に VPS 上の AI エージェントにアクセスしたい
- ✅ 複数人でAIエージェントを共有したい（グループチャット）

Trigger keywords: `telegram bot`, `openclaw telegram`, `chat interface`, `bot setup`

## How It Works

### Step 1: Telegram Bot の作成

BotFather で新しいボットを作成します。

1. Telegram で `@BotFather` を検索して開始
2. `/newbot` コマンドを送信
3. ボット名を入力（例: `OpenClaw NN 2026`）
4. ユーザー名を入力（例: `openclaw_nn2026_bot`、末尾は `_bot` 必須）
5. **Bot Token を取得**（例: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`）

**重要:** Bot Token は秘密情報です。`.env` ファイルに保存し、**絶対にGitにコミットしない**でください。

### Step 2: Chat ID の取得

Telegram チャットIDを取得します（ボットにメッセージを送る先を指定するため）。

```bash
# 1. ボットに任意のメッセージを送信（Telegramアプリで）
# 例: 「Hello」

# 2. 以下のAPIを呼び出してChat IDを取得
curl -s "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates" | jq

# 出力例:
# {
#   "ok": true,
#   "result": [
#     {
#       "message": {
#         "chat": {
#           "id": 123456789,  ← これがChat ID
#           "first_name": "Your Name",
#           "type": "private"
#         }
#       }
#     }
#   ]
# }
```

### Step 3: 環境変数の設定

`.env` ファイルに Telegram 設定を追加：

```bash
# --- Telegram Bot Settings ---
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### Step 4: OpenClaw 設定ファイルに Telegram プラグインを有効化

`config/openclaw/openclaw.json` に Telegram 設定を追加：

```json
{
  "plugins": {
    "entries": {
      "telegram": {
        "enabled": true,
        "token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
      }
    }
  }
}
```

**注意:** `token` は環境変数から読み込むことができないため、直接記載が必要です。セキュリティのため、この設定ファイルを `.gitignore` に追加してください。

### Step 5: Docker Compose で環境変数を伝播

```yaml
# docker-compose.quick.yml
services:
  openclaw:
    environment:
      # Telegram Bot
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:-}
      TELEGRAM_CHAT_ID: ${TELEGRAM_CHAT_ID:-}
```

### Step 6: OpenClaw コンテナを再起動

```bash
# 設定反映のため再起動
docker compose -f docker-compose.quick.yml up -d --force-recreate openclaw

# ログでTelegram接続を確認
docker logs openclaw-agent --tail 50 | grep -i telegram
```

### Step 7: Telegram プラグインを有効化

OpenClaw の `doctor` コマンドでプラグインを有効化：

```bash
# OpenClawコンテナ内で実行
docker exec -it openclaw-agent openclaw doctor --fix

# 出力を確認:
# ✓ Telegram configured
# ✓ Plugin enabled: telegram
```

**重要:** `openclaw doctor --fix` は `plugins.entries.telegram.enabled: false` で追加することがあります。その場合、`openclaw.json` を手動で `enabled: true` に変更してください。

### Step 8: ペアリング承認

Telegram プラグインをGateway に接続するには、ペアリング承認が必要です。

```bash
# 1. Telegram ボットにメッセージを送信（Telegramアプリで）
# 例: 「Hello」

# 2. OpenClaw Gateway がペアリングリクエストを受信
# ログを確認:
docker logs openclaw-agent | grep -i pairing

# 3. pending.json からペアリングコードを取得
docker exec openclaw-agent cat ~/.openclaw/devices/pending.json

# 出力例:
# {
#   "device-id-xxx": {
#     "code": "ABC123",
#     "label": "telegram",
#     "requestedAt": "2026-02-14T..."
#   }
# }

# 4. ペアリング承認
docker exec openclaw-agent openclaw pairing approve telegram ABC123
```

**代替方法（手動登録）:**

ペアリングコマンドが動作しない場合、`paired.json` に手動でデバイスを登録：

```bash
# pending.json からデバイスIDとコードを取得
DEVICE_ID=$(docker exec openclaw-agent cat ~/.openclaw/devices/pending.json | jq -r 'keys[0]')

# Node.jsスクリプトで paired.json に追加
docker exec openclaw-agent node -e "
const fs = require('fs');
const path = '/home/appuser/.openclaw/devices/paired.json';
const paired = JSON.parse(fs.readFileSync(path, 'utf8'));
paired['$DEVICE_ID'] = {
  approvedAt: new Date().toISOString(),
  label: 'telegram'
};
fs.writeFileSync(path, JSON.stringify(paired, null, 2));
"

# pending.json をクリア
docker exec openclaw-agent sh -c 'echo "{}" > ~/.openclaw/devices/pending.json'

# Gateway 再起動
docker restart openclaw-agent
```

### Step 9: 接続確認

Telegram ボットにメッセージを送信して、OpenClaw が応答するか確認：

```
（Telegramアプリで）
> Hello Jarvis

（OpenClaw Jarvis の応答）
< こんにちは！どのようなお手伝いができますか？
```

## Examples

### Example 1: Telegram から AI エージェントにタスク依頼

```
（Telegramアプリで）
> PostgreSQLのパフォーマンスチューニング方法を調べて

（Jarvis が Alice にリサーチを委任）
（数十秒後、Aliceの調査結果が返ってくる）
< PostgreSQLのパフォーマンスチューニングについて調査しました。
  1. インデックス設計: WHERE, ORDER BY, JOINで使うカラムにインデックスを作成
  2. VACUUM: 定期的に実行してdead tuplesを削除
  3. shared_buffers: メモリの25%を割り当て
  ...
```

### Example 2: N8N から Telegram に通知

N8N ワークフロー内で HTTP Request Node を使用：

```json
{
  "name": "Send Telegram Notification",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "https://api.telegram.org/bot{{$env.TELEGRAM_BOT_TOKEN}}/sendMessage",
    "bodyParameters": {
      "parameters": [
        {
          "name": "chat_id",
          "value": "={{$env.TELEGRAM_CHAT_ID}}"
        },
        {
          "name": "text",
          "value": "🤖 Morning Briefing タスク完了\n\n処理件数: {{$json.count}}\nステータス: {{$json.status}}"
        },
        {
          "name": "parse_mode",
          "value": "Markdown"
        }
      ]
    }
  }
}
```

### Example 3: グループチャットで複数人がAIエージェントを共有

```bash
# 1. Telegram でグループチャットを作成
# 2. OpenClaw ボットをグループに追加
# 3. グループのChat IDを取得

curl -s "https://api.telegram.org/bot<BOT_TOKEN>/getUpdates" | jq '.result[].message.chat | select(.type=="group")'

# 4. .env のTELEGRAM_CHAT_IDをグループIDに変更
TELEGRAM_CHAT_ID=-1001234567890  # グループIDは負の数

# 5. OpenClaw 再起動
docker restart openclaw-agent
```

グループチャットでは、複数人がJarvisにタスクを依頼できます。

## Best Practices

### ✅ Do This

- **Bot Token を秘密に保つ**: `.env` に保存し、Gitにコミットしない
- **Chat ID を正しく設定**: private チャットは正の数、グループは負の数
- **ペアリング承認を完了**: `openclaw pairing approve` または手動登録
- **Markdown記法を活用**: `parse_mode: Markdown` で見やすい通知
- **レート制限に注意**: Telegram API は1秒あたり30メッセージまで
- **エラーハンドリング**: Telegram API の失敗時は再試行ロジックを実装

### ❌ Avoid This

- **Bot Token をハードコード**: ソースコードに直接書かない
- **getUpdates と Webhook の併用**: どちらか一方のみ使用（OpenClaw は getUpdates）
- **過度な通知**: スパム扱いされる可能性
- **ペアリング承認を忘れる**: 接続できない原因になる

## Common Pitfalls

### Problem: Telegram ボットが応答しない

**Root Cause:** OpenClaw Gateway に Telegram プラグインが正しく接続されていない

**Diagnosis:**
```bash
# Telegramプラグインの状態を確認
docker exec openclaw-agent openclaw doctor

# 出力:
# ✗ Telegram configured, not enabled yet  ← enabled が false

# または
# ✗ Telegram pairing required  ← ペアリング未承認
```

**Solution:**
```bash
# Case 1: enabled が false の場合
# openclaw.json を編集
docker exec openclaw-agent vi ~/.openclaw/openclaw.json
# "plugins.entries.telegram.enabled" を true に変更

# Case 2: ペアリング未承認の場合
docker exec openclaw-agent openclaw pairing approve telegram <code>

# Gateway 再起動
docker restart openclaw-agent
```

**Prevention:** `openclaw doctor --fix` 実行後、必ず `openclaw.json` で `enabled: true` になっているか確認

---

### Problem: getUpdates conflict エラー

**Root Cause:** 複数のプロセスが同時に `getUpdates` API を呼び出している

**Symptoms:**
```
Error: Conflict: terminated by other getUpdates request
```

**Solution:**
```bash
# 他のプロセスが getUpdates を使っているか確認
ps aux | grep telegram
ps aux | grep python.*telegram

# 競合するプロセスを停止
kill <PID>

# OpenClaw を再起動
docker restart openclaw-agent
```

**Prevention:**
- Telegram Bot は1つのアプリケーションからのみ接続する
- Webhook と getUpdates を併用しない
- 開発環境と本番環境で**異なるBot Token**を使用

---

### Problem: N8N から送信したメッセージが OpenClaw に届かない

**Root Cause:** N8N の `sendMessage` API と OpenClaw の `getUpdates` は競合しない（別のAPI）

**Solution:**
N8N から Telegram に通知を送っても、OpenClaw の受信には影響しません。

```bash
# N8N → Telegram (sendMessage): メッセージを送信
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=123456789" \
  -d "text=通知メッセージ"

# OpenClaw → Telegram (getUpdates): メッセージを受信（別のAPI）
# 競合しない
```

**Prevention:** sendMessage と getUpdates は独立しているため、問題なし

## Configuration Reference

### Telegram Bot API 環境変数

```bash
# Bot Token（BotFatherから取得）
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Chat ID（個人チャット: 正の数、グループ: 負の数）
TELEGRAM_CHAT_ID=123456789
```

### openclaw.json 設定

```json
{
  "plugins": {
    "entries": {
      "telegram": {
        "enabled": true,
        "token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
      }
    }
  }
}
```

### Telegram API エンドポイント

```bash
# メッセージ送信
POST https://api.telegram.org/bot<TOKEN>/sendMessage
Body: { "chat_id": 123456789, "text": "Hello" }

# 更新取得（OpenClawが使用）
GET https://api.telegram.org/bot<TOKEN>/getUpdates

# Webhook設定（OpenClawでは未使用）
POST https://api.telegram.org/bot<TOKEN>/setWebhook
Body: { "url": "https://yourdomain.com/webhook" }
```

## Related Skills

- `@openclaw-pairing-solution` - デバイスペアリングの詳細
- `@n8n-openclaw-integration` - N8Nとの連携
- `@multi-agent-orchestration` - 複数エージェント管理
- See also: `docs/KNOWN_MISTAKES.md` - Telegram接続の過去のミス

## Troubleshooting

### Issue 1: Bot Token が無効

**Symptoms:**
- `401 Unauthorized` エラー
- `Invalid token` メッセージ

**Diagnosis:**
```bash
# Bot Tokenをテスト
curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getMe" | jq

# 正常な応答:
# {
#   "ok": true,
#   "result": {
#     "id": 1234567890,
#     "is_bot": true,
#     "first_name": "OpenClaw NN 2026",
#     "username": "openclaw_nn2026_bot"
#   }
# }
```

**Fix:**
BotFather で新しいトークンを生成：
```
/mybots
<ボット選択>
API Token
Regenerate Token
```

### Issue 2: Chat ID が間違っている

**Symptoms:**
- メッセージが届かない
- `Bad Request: chat not found` エラー

**Diagnosis:**
```bash
# 正しいChat IDを再取得
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq '.result[].message.chat.id'
```

**Fix:**
`.env` の `TELEGRAM_CHAT_ID` を正しい値に更新し、再起動：
```bash
docker restart openclaw-agent
```

## Advanced Usage

### Custom Commands

Telegram ボットにカスタムコマンドを追加：

```javascript
// skills/telegram-commands.js
module.exports = {
  name: 'telegram-commands',
  description: 'Custom Telegram bot commands',

  commands: {
    '/status': async () => {
      const uptime = process.uptime();
      return `🤖 OpenClaw Status\n⏱ Uptime: ${uptime}s`;
    },

    '/agents': async () => {
      const agents = await listAgents();
      return `👥 Available Agents:\n${agents.map(a => `- ${a.name}`).join('\n')}`;
    }
  }
};
```

### Rich Notifications

Markdown/HTML形式でリッチな通知：

```bash
# Markdown
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": 123456789,
    "text": "*太字* _イタリック_ `コード` [リンク](https://example.com)",
    "parse_mode": "Markdown"
  }'

# HTML
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": 123456789,
    "text": "<b>太字</b> <i>イタリック</i> <code>コード</code> <a href=\"https://example.com\">リンク</a>",
    "parse_mode": "HTML"
  }'
```

### Inline Keyboards

ボタン付きメッセージ：

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": 123456789,
    "text": "タスクを選択してください:",
    "reply_markup": {
      "inline_keyboard": [
        [
          {"text": "リサーチ", "callback_data": "research"},
          {"text": "執筆", "callback_data": "writing"}
        ],
        [
          {"text": "コーディング", "callback_data": "coding"}
        ]
      ]
    }
  }'
```

## References

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [BotFather Guide](https://core.telegram.org/bots#botfather)
- [OpenClaw Telegram Plugin](https://github.com/openclaw/openclaw/tree/main/plugins/telegram)
- [Markdown Formatting](https://core.telegram.org/bots/api#markdown-style)
- Related: `docs/OPENCLAW_PAIRING_SOLUTION.md`

---

*最終更新: 2026-02-15 — OpenClaw + Telegram Bot 統合の完全ガイドを作成*
