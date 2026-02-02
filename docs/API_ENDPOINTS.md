# API & Monitoring Endpoints Documentation

OpenClaw VPS 環境のAPI・監視エンドポイント完全リファレンス

## 📋 目次

- [概要](#概要)
- [ヘルスチェックエンドポイント](#ヘルスチェックエンドポイント)
- [メトリクスエンドポイント](#メトリクスエンドポイント)
- [管理エンドポイント](#管理エンドポイント)
- [N8N API](#n8n-api)
- [Grafana API](#grafana-api)
- [Prometheus API](#prometheus-api)

---

## 概要

### ベースURL

```
本番環境: https://your-domain.com
開発環境: http://localhost:3000
ステージング: https://staging.your-domain.com
```

### 認証

各サービスの認証方式:
- **OpenClaw**: JWT トークン
- **N8N**: Basic認証 または JWT
- **Grafana**: セッションCookie または API Key
- **Prometheus**: Basic認証（オプション）

---

## ヘルスチェックエンドポイント

### OpenClaw Health Check

#### `GET /health`

アプリケーションの健全性をチェック

**リクエスト例**:
```bash
curl http://localhost:3000/health
```

**レスポンス例**:
```json
{
  "status": "ok",
  "timestamp": "2024-02-01T12:00:00.000Z",
  "uptime": 86400,
  "version": "1.0.0",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "storage": "healthy"
  }
}
```

**ステータスコード**:
- `200`: 正常
- `503`: サービス利用不可（依存サービス障害）

---

#### `GET /health/ready`

アプリケーションがリクエストを受け付け可能かチェック

**リクエスト例**:
```bash
curl http://localhost:3000/health/ready
```

**レスポンス例**:
```json
{
  "status": "ready",
  "checks": {
    "database": true,
    "migrations": true,
    "cache": true
  }
}
```

**用途**: Kubernetes readiness probe等で使用

---

#### `GET /health/live`

アプリケーションプロセスが生存しているかチェック

**リクエスト例**:
```bash
curl http://localhost:3000/health/live
```

**レスポンス例**:
```json
{
  "status": "alive"
}
```

**用途**: Kubernetes liveness probe等で使用

---

### PostgreSQL Health Check

#### Database Connection Test

```bash
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -c "SELECT version();"
```

#### Database Size Check

```bash
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -d openclaw -c "\
    SELECT \
      pg_size_pretty(pg_database_size('openclaw')) as size;"
```

---

### N8N Health Check

#### `GET /healthz`

N8Nの健全性チェック

**リクエスト例**:
```bash
curl http://localhost:5678/healthz
```

**レスポンス例**:
```json
{
  "status": "ok"
}
```

---

### OpenNotebook Health Check

#### `GET /health`

OpenNotebookの健全性チェック

**リクエスト例**:
```bash
curl http://localhost:8080/health
```

**レスポンス例**:
```json
{
  "status": "healthy",
  "database": "connected",
  "storage": "available"
}
```

---

## メトリクスエンドポイント

### Prometheus Metrics

#### `GET /metrics`

Prometheusフォーマットのメトリクスを取得

**リクエスト例**:
```bash
curl http://localhost:9090/metrics
```

**主要メトリクス**:

```promql
# CPU使用率
node_cpu_seconds_total

# メモリ使用量
node_memory_MemAvailable_bytes
node_memory_MemTotal_bytes

# ディスク使用量
node_filesystem_avail_bytes
node_filesystem_size_bytes

# ネットワークI/O
node_network_receive_bytes_total
node_network_transmit_bytes_total

# コンテナメトリクス
container_cpu_usage_seconds_total
container_memory_usage_bytes

# PostgreSQLメトリクス
pg_stat_activity_count
pg_database_size_bytes
```

---

### Node Exporter Metrics

#### `GET :9100/metrics`

システムメトリクスを取得

**エンドポイント**: `http://localhost:9100/metrics`

**主要メトリクス**:
- CPU使用率
- メモリ使用量
- ディスクI/O
- ネットワーク統計
- システムロード

---

### cAdvisor Metrics

#### `GET :8080/metrics`

Dockerコンテナメトリクスを取得

**エンドポイント**: `http://localhost:8080/metrics`

**主要メトリクス**:
- コンテナCPU使用率
- コンテナメモリ使用量
- コンテナネットワークI/O
- コンテナディスクI/O

---

## 管理エンドポイント

### OpenClaw API

#### `POST /api/chat`

AIチャットメッセージを送信

**認証**: JWT必須

**リクエスト例**:
```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "こんにちは",
    "conversation_id": "conv-123",
    "model": "claude-sonnet-4-5"
  }'
```

**レスポンス例**:
```json
{
  "id": "msg-456",
  "conversation_id": "conv-123",
  "message": "こんにちは！何かお手伝いできることはありますか？",
  "model": "claude-sonnet-4-5",
  "tokens": {
    "input": 10,
    "output": 25,
    "total": 35
  },
  "cost": {
    "usd": 0.000525
  },
  "timestamp": "2024-02-01T12:00:00.000Z"
}
```

---

#### `GET /api/conversations`

会話履歴一覧を取得

**認証**: JWT必須

**クエリパラメータ**:
- `limit` (number): 取得件数（デフォルト: 20）
- `offset` (number): オフセット（デフォルト: 0）
- `user_id` (string): ユーザーID

**リクエスト例**:
```bash
curl http://localhost:3000/api/conversations?limit=10 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**レスポンス例**:
```json
{
  "conversations": [
    {
      "id": "conv-123",
      "user_id": "user-1",
      "title": "技術相談",
      "message_count": 15,
      "last_message_at": "2024-02-01T12:00:00.000Z",
      "created_at": "2024-01-31T10:00:00.000Z"
    }
  ],
  "total": 50,
  "limit": 10,
  "offset": 0
}
```

---

#### `GET /api/stats`

使用統計を取得

**認証**: JWT必須

**リクエスト例**:
```bash
curl http://localhost:3000/api/stats \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**レスポンス例**:
```json
{
  "today": {
    "messages": 120,
    "tokens": 45000,
    "cost_usd": 0.675
  },
  "this_month": {
    "messages": 2500,
    "tokens": 950000,
    "cost_usd": 14.25
  },
  "models": {
    "claude-sonnet-4-5": {
      "count": 1800,
      "tokens": 750000
    },
    "claude-haiku-4-5": {
      "count": 700,
      "tokens": 200000
    }
  }
}
```

---

### Cost Tracking API

#### `GET /api/costs/daily`

日次コスト取得

**認証**: JWT必須

**クエリパラメータ**:
- `date` (string): 日付（YYYY-MM-DD）

**リクエスト例**:
```bash
curl "http://localhost:3000/api/costs/daily?date=2024-02-01" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**レスポンス例**:
```json
{
  "date": "2024-02-01",
  "api_calls": 120,
  "tokens": {
    "input": 45000,
    "output": 22500,
    "total": 67500
  },
  "cost": {
    "api_usd": 0.675,
    "vps_jpy": 40,
    "storage_jpy": 10,
    "total_jpy": 151
  }
}
```

---

#### `GET /api/costs/monthly`

月次コスト取得

**認証**: JWT必須

**クエリパラメータ**:
- `year` (number): 年
- `month` (number): 月

**リクエスト例**:
```bash
curl "http://localhost:3000/api/costs/monthly?year=2024&month=2" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**レスポンス例**:
```json
{
  "year": 2024,
  "month": 2,
  "api_calls": 2500,
  "tokens": {
    "input": 950000,
    "output": 475000,
    "total": 1425000
  },
  "cost": {
    "api_usd": 14.25,
    "vps_jpy": 1200,
    "storage_jpy": 300,
    "total_jpy": 3638
  },
  "budget": {
    "amount_jpy": 5000,
    "used_percent": 72.76,
    "remaining_jpy": 1362
  }
}
```

---

## N8N API

### Workflow Execution

#### `POST /webhook/:webhookPath`

Webhookトリガーのワークフローを実行

**リクエスト例**:
```bash
curl -X POST http://localhost:5678/webhook/test-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": "テストメッセージ",
    "priority": "high"
  }'
```

**レスポンス例**:
```json
{
  "success": true,
  "executionId": "exec-123",
  "data": {
    "result": "処理完了"
  }
}
```

---

#### `GET /api/v1/workflows`

ワークフロー一覧を取得

**認証**: Basic認証必須

**リクエスト例**:
```bash
curl http://localhost:5678/api/v1/workflows \
  -u admin:password
```

**レスポンス例**:
```json
{
  "data": [
    {
      "id": "1",
      "name": "VPS Health Check",
      "active": true,
      "createdAt": "2024-01-01T00:00:00.000Z",
      "updatedAt": "2024-02-01T00:00:00.000Z"
    }
  ]
}
```

---

#### `POST /api/v1/workflows/:id/activate`

ワークフローを有効化

**認証**: Basic認証必須

**リクエスト例**:
```bash
curl -X POST http://localhost:5678/api/v1/workflows/1/activate \
  -u admin:password
```

---

## Grafana API

### Dashboard API

#### `GET /api/dashboards/uid/:uid`

ダッシュボードを取得

**認証**: API Key必須

**リクエスト例**:
```bash
curl http://localhost:3001/api/dashboards/uid/container-monitoring \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

#### `GET /api/datasources`

データソース一覧を取得

**認証**: API Key必須

**リクエスト例**:
```bash
curl http://localhost:3001/api/datasources \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### Alerting API

#### `GET /api/alerts`

アラート一覧を取得

**認証**: API Key必須

**リクエスト例**:
```bash
curl http://localhost:3001/api/alerts \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Prometheus API

### Query API

#### `GET /api/v1/query`

PromQLクエリを実行

**クエリパラメータ**:
- `query` (string): PromQLクエリ
- `time` (timestamp): 評価時刻（オプション）

**リクエスト例**:
```bash
curl 'http://localhost:9090/api/v1/query?query=up'
```

**レスポンス例**:
```json
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {
          "__name__": "up",
          "instance": "localhost:9090",
          "job": "prometheus"
        },
        "value": [1706787600, "1"]
      }
    ]
  }
}
```

---

#### `GET /api/v1/query_range`

時系列データクエリ

**クエリパラメータ**:
- `query` (string): PromQLクエリ
- `start` (timestamp): 開始時刻
- `end` (timestamp): 終了時刻
- `step` (duration): ステップ間隔

**リクエスト例**:
```bash
curl 'http://localhost:9090/api/v1/query_range?query=rate(node_cpu_seconds_total[5m])&start=1706780000&end=1706787600&step=300'
```

---

### Targets API

#### `GET /api/v1/targets`

スクレイプターゲット一覧を取得

**リクエスト例**:
```bash
curl http://localhost:9090/api/v1/targets
```

**レスポンス例**:
```json
{
  "status": "success",
  "data": {
    "activeTargets": [
      {
        "discoveredLabels": {},
        "labels": {
          "instance": "localhost:9090",
          "job": "prometheus"
        },
        "scrapeUrl": "http://localhost:9090/metrics",
        "lastError": "",
        "lastScrape": "2024-02-01T12:00:00.000Z",
        "health": "up"
      }
    ]
  }
}
```

---

## 使用例

### ヘルスチェックスクリプト

```bash
#!/bin/bash

# 全サービスのヘルスチェック
services=(
  "http://localhost:3000/health"
  "http://localhost:5678/healthz"
  "http://localhost:8080/health"
  "http://localhost:9090/-/healthy"
  "http://localhost:3001/api/health"
)

for service in "${services[@]}"; do
  if curl -sf "$service" > /dev/null; then
    echo "✅ $service - OK"
  else
    echo "❌ $service - FAILED"
  fi
done
```

---

### コスト監視スクリプト

```bash
#!/bin/bash

# 今日のコストを取得
COST=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost:3000/api/costs/daily | jq -r '.cost.total_jpy')

echo "今日のコスト: ¥$COST"

# 予算チェック
if [ "$COST" -gt 200 ]; then
  echo "⚠️ 予算警告: 1日あたり¥200を超えています"
fi
```

---

### Prometheusメトリクス取得

```bash
#!/bin/bash

# CPU使用率を取得
curl -s 'http://localhost:9090/api/v1/query?query=100-avg(irate(node_cpu_seconds_total{mode="idle"}[5m]))*100' \
  | jq -r '.data.result[0].value[1]'

# メモリ使用率を取得
curl -s 'http://localhost:9090/api/v1/query?query=100*(1-(node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes))' \
  | jq -r '.data.result[0].value[1]'
```

---

## エラーコード

### 共通エラーコード

| コード | 説明 | 対処法 |
|-------|------|-------|
| 400 | 不正なリクエスト | リクエストパラメータを確認 |
| 401 | 認証エラー | トークン・認証情報を確認 |
| 403 | 権限不足 | ユーザー権限を確認 |
| 404 | リソースが見つからない | URLとリソースIDを確認 |
| 429 | レート制限超過 | しばらく待ってから再試行 |
| 500 | サーバーエラー | ログを確認し、管理者に連絡 |
| 503 | サービス利用不可 | 依存サービスの状態を確認 |

---

## セキュリティ

### API キーの管理

```bash
# Grafana API キー生成
curl -X POST http://localhost:3001/api/auth/keys \
  -H "Content-Type: application/json" \
  -u admin:password \
  -d '{
    "name": "monitoring-key",
    "role": "Viewer",
    "secondsToLive": 86400
  }'
```

### レート制限

- **OpenClaw**: 100リクエスト/15分
- **N8N**: 制限なし（内部使用）
- **Grafana**: 30リクエスト/分
- **Prometheus**: 制限なし

---

## 参考資料

- [Prometheus API Documentation](https://prometheus.io/docs/prometheus/latest/querying/api/)
- [Grafana API Documentation](https://grafana.com/docs/grafana/latest/http_api/)
- [N8N API Documentation](https://docs.n8n.io/api/)

---

<div align="center">

**📡 すべてのエンドポイントをフル活用して、効率的な運用を実現しましょう！ 🚀**

</div>
