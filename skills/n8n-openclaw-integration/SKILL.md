---
name: n8n-openclaw-integration
description: "OpenClaw AIエージェントとN8Nワークフローを統合し、自動化タスクを効率的にオーケストレーションする"
source: community
risk: safe
tags:
  - n8n
  - workflow
  - automation
  - integration
  - openclaw
related_skills:
  - @workflow-automation
  - @postgres-integration
  - @telegram-bot
---

# N8N + OpenClaw 統合

## Overview

OpenClaw AIエージェントとN8Nワークフローエンジンを連携させ、スケジュール実行、データ処理、外部API連携を自動化します。このスキルは、AIエージェントが手動で行っていたタスクをN8Nで自動化し、人間の介入なしに定期実行できるようにします。

## When to Use This Skill

このスキルを使用する場面：

- ✅ 毎日決まった時刻にAIエージェントにタスクを実行させたい
- ✅ PostgreSQLのデータを定期的に処理・更新したい
- ✅ 外部API（Substack、Telegram等）と連携した自動投稿
- ✅ OpenClawエージェントの実行結果をN8Nで後処理したい
- ✅ 複数のサービスを跨ぐ複雑なワークフローを構築したい

Trigger keywords: `n8n`, `workflow automation`, `schedule`, `cron job`, `auto publish`

## How It Works

### Step 1: N8N APIキーの生成

N8Nは Basic Auth ではなく **APIキー認証** を使用します。

```bash
# N8Nコンテナ内でAPIキーを生成
docker exec -it openclaw-n8n n8n api-key create --name "openclaw-integration" --scopes "workflow:read,workflow:execute"
```

または、PostgreSQLに直接APIキーを挿入：

```sql
-- N8N所有者のuser_idを確認
SELECT id, email FROM n8n.user WHERE role = 'owner';

-- APIキーをn8n.api_keyテーブルに挿入
INSERT INTO n8n.api_key (user_id, api_key, scopes, created_at, expires_at)
VALUES (
  1, -- user_id（上記で確認したID）
  'n8n_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', -- APIキー
  '["workflow:read", "workflow:execute"]',
  NOW(),
  NOW() + INTERVAL '1 year'
);
```

### Step 2: 環境変数の設定

`.env` ファイルにN8N設定を追加：

```bash
# N8N API認証
N8N_API_KEY=n8n_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
N8N_HOST=n8n
N8N_PORT=5678

# ワークフロー用の外部API設定
GOOGLE_API_KEY=your_google_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Step 3: Docker Composeでの環境変数伝播

N8Nコンテナが外部APIにアクセスできるよう、環境変数を渡します：

```yaml
# docker-compose.quick.yml
services:
  n8n:
    environment:
      # N8N内部設定
      N8N_BASIC_AUTH_ACTIVE: "true"
      N8N_BASIC_AUTH_USER: ${N8N_USER:-admin}
      N8N_BASIC_AUTH_PASSWORD: ${N8N_PASSWORD:-admin}

      # ワークフロー用外部API（重要！）
      GOOGLE_API_KEY: ${GOOGLE_API_KEY:-}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:-}
      TELEGRAM_CHAT_ID: ${TELEGRAM_CHAT_ID:-}
      OPENCLAW_GATEWAY_TOKEN: ${OPENCLAW_GATEWAY_TOKEN}
```

### Step 4: ワークフローの作成

N8N Web UI (http://localhost:5678) でワークフローを作成：

1. **Schedule Trigger** - cron式で実行タイミングを設定
2. **PostgreSQL Node** - データ取得・更新
3. **HTTP Request Node** - 外部API呼び出し
4. **IF Node** - 条件分岐
5. **PostgreSQL Node** - 結果を保存

### Step 5: ワークフローのインポート

事前に作成したワークフローJSONをインポート：

```bash
# N8N Web UIからインポート
# Settings > Import from file > n8n-workflows/substack-auto-publish-api.json を選択
```

または、N8N API経由でインポート：

```bash
curl -X POST http://localhost:5678/api/v1/workflows \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @n8n-workflows/substack-auto-publish-api.json
```

## Examples

### Example 1: 毎朝8時にAI生成レポートをSubstackに自動投稿

```json
{
  "nodes": [
    {
      "name": "Schedule: Daily 8:00 JST",
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": {
          "interval": [{ "field": "hours", "hoursInterval": 24 }]
        }
      }
    },
    {
      "name": "Get Unpublished Report",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "query": "SELECT id, title, content FROM aisa.generated_reports WHERE published_at IS NULL LIMIT 1"
      }
    },
    {
      "name": "Publish to Substack",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://substack-api:8000/publish",
        "method": "POST",
        "bodyParameters": {
          "parameters": [
            { "name": "title", "value": "={{$json.title}}" },
            { "name": "content", "value": "={{$json.content}}" }
          ]
        }
      }
    },
    {
      "name": "Mark as Published",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "query": "UPDATE aisa.generated_reports SET published_at = NOW() WHERE id = {{$json.id}}"
      }
    }
  ]
}
```

### Example 2: Telegram経由でOpenClawエージェントにタスク実行を通知

```javascript
// N8N Function Nodeでの実装
const message = `🤖 Morning Briefing タスク完了

📊 処理件数: ${$json.count}
✅ ステータス: ${$json.status}
🕒 実行時刻: ${new Date().toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' })}`;

return {
  json: {
    chat_id: process.env.TELEGRAM_CHAT_ID,
    text: message
  }
};
```

```json
{
  "name": "Send Telegram Notification",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "url": "https://api.telegram.org/bot{{$env.TELEGRAM_BOT_TOKEN}}/sendMessage",
    "method": "POST",
    "bodyParameters": {
      "parameters": [
        { "name": "chat_id", "value": "={{$json.chat_id}}" },
        { "name": "text", "value": "={{$json.text}}" }
      ]
    }
  }
}
```

## Best Practices

### ✅ Do This

- **環境変数を活用**: APIキーやトークンをハードコードしない
- **エラーハンドリング**: IFノードで成功/失敗を分岐し、失敗時はログ記録
- **PostgreSQLスキーマ分離**: N8Nは`n8n`スキーマ、アプリデータは別スキーマ（`aisa`等）
- **Docker内部DNS**: サービス間通信は`http://service-name:port`（例: `http://substack-api:8000`）
- **スケジュール実行**: 公開APIからワークフロー実行はできないため、Schedule Triggerを使う
- **Telegram送信とOpenClaw受信は競合しない**: `sendMessage` APIと`getUpdates`は別処理

### ❌ Avoid This

- **Basic Auth でN8N APIにアクセス**: N8N APIは`X-N8N-API-KEY`ヘッダー必須
- **OpenClawへのREST API呼び出し**: OpenClawにはREST APIがない（WebSocketのみ）
- **N8Nワークフローから直接OpenClawエージェントを呼ぶ**: 技術的に不可能。代わりにLLM APIを直接呼ぶ
- **環境変数の渡し忘れ**: N8Nコンテナに`GOOGLE_API_KEY`等を渡さないと、ワークフロー内で使えない
- **ポートバインドミス**: `127.0.0.1:8000:8000` は外部アクセス不可。Docker内部は`service-name:port`

## Common Pitfalls

### Problem: N8N APIに401 Unauthorized

**Root Cause:** Basic Auth でアクセスしようとしている

**Solution:**
```bash
# ❌ Wrong
curl -u admin:password http://localhost:5678/api/v1/workflows

# ✅ Correct
curl -H "X-N8N-API-KEY: n8n_api_xxx" http://localhost:5678/api/v1/workflows
```

**Prevention:** N8N APIドキュメントで認証方式を確認してから実装

---

### Problem: ワークフロー内で環境変数が undefined

**Root Cause:** Docker Composeで環境変数をN8Nコンテナに渡していない

**Solution:**
```yaml
# docker-compose.quick.yml
services:
  n8n:
    environment:
      GOOGLE_API_KEY: ${GOOGLE_API_KEY:-}  # 追加
```

**Prevention:** ワークフロー作成前に、必要な環境変数をすべてCompose設定に追加

---

### Problem: OpenClawエージェントをN8Nから呼び出せない

**Root Cause:** OpenClawにはREST APIが存在しない（WebSocketのみ）

**Solution:**
N8NからOpenClawを呼ぶのではなく、以下のいずれかを選択：

1. **N8NからLLM APIを直接呼ぶ**（Gemini, OpenAI等）
2. **TelegramでOpenClawに通知** → Jarvisが手動で処理
3. **OpenClawのスキルとして実装** → Telegramコマンドで実行

**Prevention:** アーキテクチャ設計時に、OpenClawとN8Nの役割分担を明確にする

---

### Problem: Substack APIが404エラー

**Root Cause:** Substack公式APIは存在しない（非公式ライブラリを使用）

**Solution:**
```bash
# FastAPI + python-substack でAPIサーバーを構築
docker compose -f docker-compose.quick.yml up -d substack-api
```

**Prevention:** 「◯◯ API」が存在するか、必ず公式ドキュメントで確認してから実装

## Configuration Reference

### N8N環境変数

```bash
# Basic Auth（Web UIログイン用）
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=strong_password

# Database（PostgreSQL推奨）
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=openclaw
DB_POSTGRESDB_USER=openclaw
DB_POSTGRESDB_PASSWORD=your_password
DB_POSTGRESDB_SCHEMA=n8n

# Webhook URL（外部トリガー用）
WEBHOOK_URL=http://localhost:5678/

# Timezone
GENERIC_TIMEZONE=Asia/Tokyo
```

### ワークフロー用外部API

```bash
# Google Gemini API
GOOGLE_API_KEY=AIza...

# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_CHAT_ID=123456789

# OpenClaw Gateway（Telegram経由でエージェント通知用）
OPENCLAW_GATEWAY_TOKEN=your_gateway_token
```

## Related Skills

- `@telegram-bot-builder` - Telegram Bot構築の基礎
- `@postgres-best-practices` - PostgreSQL最適化
- `@fastapi-integration` - FastAPIでカスタムAPIサーバー構築
- See also: `docs/KNOWN_MISTAKES.md` - N8N関連の過去のミス

## Troubleshooting

### Issue 1: ワークフローが実行されない

**Symptoms:**
- スケジュールトリガーが発火しない
- 手動実行もできない

**Diagnosis:**
```bash
# N8Nログを確認
docker logs openclaw-n8n --tail 50

# N8Nコンテナのステータス確認
docker ps | grep n8n
```

**Fix:**
```bash
# N8Nを再起動
docker restart openclaw-n8n

# ワークフローをアクティブ化（Web UIで）
# Workflows > Your Workflow > Active toggle ON
```

### Issue 2: PostgreSQL接続エラー

**Symptoms:**
- `connection refused` or `ECONNREFUSED`

**Diagnosis:**
```bash
# PostgreSQLが起動しているか確認
docker exec openclaw-postgres pg_isready -U openclaw

# N8NからPostgreSQLに接続できるか確認
docker exec openclaw-n8n ping postgres
```

**Fix:**
```yaml
# docker-compose.quick.yml
services:
  n8n:
    depends_on:
      postgres:
        condition: service_healthy  # ヘルスチェック待機
    networks:
      - openclaw-network  # 同じネットワーク
```

## Advanced Usage

### Custom Webhook Trigger

外部サービスからN8Nワークフローをトリガー：

```javascript
// Webhook URL: http://localhost:5678/webhook/custom-trigger
fetch('http://localhost:5678/webhook/custom-trigger', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    task: 'generate_report',
    topic: 'AI trends 2026'
  })
});
```

N8N側でWebhook Nodeを設定：
- Path: `custom-trigger`
- HTTP Method: `POST`
- Response: `Respond with JSON`

### Multi-Agent Orchestration

JarvisからAlice、Luna、CodeXに並列タスク振り分け：

```sql
-- タスクキューテーブル（PostgreSQL）
CREATE TABLE aisa.agent_tasks (
  id SERIAL PRIMARY KEY,
  agent VARCHAR(50),
  task_type VARCHAR(100),
  payload JSONB,
  status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW()
);

-- N8Nでタスクを登録
INSERT INTO aisa.agent_tasks (agent, task_type, payload)
VALUES
  ('alice-research', 'web_search', '{"query": "PostgreSQL optimization"}'),
  ('luna-writer', 'blog_post', '{"topic": "Database best practices"}');
```

N8Nワークフローで各エージェントにTelegram通知 → Jarvisが`sessions_spawn`で実行。

## References

- [N8N Official Documentation](https://docs.n8n.io/)
- [N8N API Documentation](https://docs.n8n.io/api/)
- [OpenClaw Sessions API](https://github.com/openclaw/openclaw/blob/main/docs/sessions.md)
- [python-substack Library](https://github.com/akshay-ap/python-substack)
- Related: `docs/SUBSTACK_AUTO_PUBLISH_SETUP.md`

---

*最終更新: 2026-02-14 — N8N + OpenClaw統合の実践ノウハウを追加*
