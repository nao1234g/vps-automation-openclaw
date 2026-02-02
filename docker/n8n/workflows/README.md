# N8N Sample Workflows

このディレクトリには、OpenClaw VPS環境で使用できる実用的なN8Nワークフローサンプルが含まれています。

## 📦 含まれるワークフロー

### 1. 研究ノート自動作成 (example-research-automation.json)

**目的**: Webから情報を収集し、OpenNotebookに研究ノートを自動作成

**トリガー**:
- Webhook経由で起動
- Telegram経由で起動

**フロー**:
```
Webhook/Telegram → Web検索 → データ整形 → OpenNotebook保存 → 通知
```

**使用例**:
- 特定トピックの最新情報を定期収集
- ニュース記事の自動要約とアーカイブ
- 研究データの自動整理

---

### 2. バックアップ通知 (example-backup-notification.json)

**目的**: データベースバックアップの成功/失敗を通知

**トリガー**:
- スケジュール（日次・午前3時）

**フロー**:
```
スケジュール → バックアップスクリプト実行 → 結果確認 → Telegram通知
```

**通知内容**:
- バックアップの成功/失敗
- バックアップサイズ
- 保存先パス
- エラーメッセージ（失敗時）

---

### 3. VPSヘルスチェック (example-vps-health-check.json)

**目的**: VPSの健全性を定期的に監視し、異常があれば通知

**トリガー**:
- スケジュール（6時間ごと）

**チェック項目**:
- ✅ Dockerコンテナの稼働状態
- 💾 ディスク使用率
- 🧠 メモリ使用率
- 📊 システムロードアベレージ

**アラート条件**:
- ディスク使用率 > 85%
- メモリ使用率 > 90%
- コンテナが停止している

**フロー**:
```
スケジュール → 各種チェック → 結果を集約 → 異常判定 → Telegram通知
```

---

### 4. セキュリティスキャンアラート (example-security-scan-alert.json)

**目的**: セキュリティスキャンを自動実行し、脆弱性を検出したら通知

**トリガー**:
- スケジュール（日次・午前2時）

**スキャン内容**:
- Trivy脆弱性スキャン
- Docker Bench Security
- システムセキュリティチェック

**アラート重要度**:
- 🚨 **CRITICAL**: 緊急対応必要（HIGH/CRITICAL脆弱性検出）
- ⚠️ **MEDIUM**: 警告（MEDIUM脆弱性検出）
- ✅ **LOW**: 正常

**フロー**:
```
スケジュール → セキュリティスキャン → レポート解析 → 重要度判定 → Telegram/Slack通知
```

---

### 5. データベースバックアップ検証 (example-database-backup-verification.json)

**目的**: バックアップの作成、検証、古いバックアップの削除を自動化

**トリガー**:
- スケジュール（日次・午前3時）

**実行内容**:
1. データベースバックアップ作成
2. バックアップファイルの存在確認
3. 総バックアップサイズの確認
4. バックアップ数のカウント
5. 30日以上古いバックアップを削除

**通知内容**:
- ✅ 成功時: バックアップ情報（サイズ、数、最新ファイル）
- 🚨 失敗時: エラー詳細とアラート

**フロー**:
```
スケジュール → バックアップ実行 → 検証 → 成功/失敗判定 → 通知 → 古いバックアップ削除
```

---

### 6. システムリソース監視 (example-resource-monitoring.json)

**目的**: システムリソースを継続的に監視し、トレンドをデータベースに保存

**トリガー**:
- スケジュール（15分ごと）

**監視項目**:
- 🖥️ CPU使用率
- 🧠 メモリ使用率
- 💾 ディスク使用率
- 🐳 各コンテナのリソース使用状況

**機能**:
- PostgreSQLにメトリクスを記録（時系列データ）
- 24時間のトレンドデータを取得可能
- 閾値を超えたらアラート送信

**アラート条件**:
- ⚠️ **WARNING**: CPU > 80%, Memory > 85%, Disk > 85%
- 🚨 **CRITICAL**: CPU > 90%, Memory > 95%, Disk > 95%

**フロー**:
```
スケジュール → リソース取得 → メトリクス処理 → DB保存 → 閾値チェック → アラート送信
```

---

## 🚀 使用方法

### 1. ワークフローのインポート

N8Nダッシュボードにアクセスし、ワークフローをインポート:

```bash
# N8Nにアクセス
http://localhost:5678

# または本番環境
https://your-domain.com/n8n
```

1. N8Nダッシュボードで「Workflows」→「Import from File」を選択
2. このディレクトリのJSONファイルを選択
3. インポート完了後、設定を編集

### 2. 必須設定項目

各ワークフローで以下を設定してください:

#### Telegram通知を使用する場合:
```javascript
// Telegramノードの設定
chatId: "YOUR_TELEGRAM_CHAT_ID"  // 自分のChat IDに変更

// Telegram Bot Tokenの設定
// N8N → Credentials → Telegram API → Bot Tokenを設定
```

#### Slack通知を使用する場合:
```javascript
// HTTPリクエストノードの設定
url: "YOUR_SLACK_WEBHOOK_URL"  // Slack Webhook URLに変更
```

#### PostgreSQL接続を使用する場合:
```javascript
// PostgreSQLノードの設定
// N8N → Credentials → PostgreSQL
Host: postgres
Port: 5432
Database: n8n
User: openclaw
Password: <your_password>
```

### 3. ワークフローの有効化

インポート後、各ワークフローを有効化:

1. ワークフローを開く
2. 右上の「Inactive」トグルを「Active」に変更
3. スケジュールが設定されているワークフローは自動実行開始

---

## 🛠️ カスタマイズ

### スケジュール変更

```javascript
// Scheduleノードで変更
// 例: 6時間ごと → 3時間ごとに変更
{
  "rule": {
    "interval": [
      {
        "field": "hours",
        "hoursInterval": 3  // 6 → 3に変更
      }
    ]
  }
}
```

### アラート閾値の変更

```javascript
// Functionノードで変更
// 例: ディスク使用率の警告閾値を変更
if (diskUsage > 80) {  // 85% → 80%に変更
  alertLevel = 'WARNING';
  alerts.push(`ディスク使用率が高い: ${disk}`);
}
```

### 通知先の追加

既存のワークフローに新しい通知先を追加:

1. ノードを追加（Slack, Email, Webhookなど）
2. 既存の通知ノードと並列に接続
3. 認証情報を設定

---

## 📊 データベーステーブル作成

リソース監視ワークフローを使用する場合、以下のテーブルを作成:

```sql
-- PostgreSQLに接続
docker compose -f docker-compose.production.yml exec postgres psql -U openclaw -d n8n

-- テーブル作成
CREATE TABLE IF NOT EXISTS system_metrics (
  id SERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  cpu_percent DECIMAL(5,2),
  memory_percent DECIMAL(5,2),
  disk_percent INTEGER,
  alert_level VARCHAR(20),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- インデックス作成
CREATE INDEX idx_metrics_timestamp ON system_metrics(timestamp DESC);
CREATE INDEX idx_metrics_alert_level ON system_metrics(alert_level);

-- データ保持期間の設定（90日以上古いデータを削除）
CREATE OR REPLACE FUNCTION cleanup_old_metrics()
RETURNS void AS $$
BEGIN
  DELETE FROM system_metrics WHERE timestamp < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- 定期削除のCronジョブ設定（PostgreSQL pg_cron拡張が必要）
-- 毎日午前4時に実行
-- SELECT cron.schedule('cleanup-metrics', '0 4 * * *', 'SELECT cleanup_old_metrics()');
```

---

## 🔧 トラブルシューティング

### ワークフローが実行されない

1. ワークフローが「Active」になっているか確認
2. N8Nコンテナのログを確認:
   ```bash
   docker compose -f docker-compose.production.yml logs n8n
   ```

### Telegram通知が届かない

1. Bot Tokenが正しく設定されているか確認
2. Chat IDが正しいか確認（Bot経由で自分にメッセージを送信し、以下のコマンドでChat IDを取得）:
   ```bash
   curl https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   ```

### コマンド実行エラー

1. N8Nコンテナがホストのコマンドを実行できるか確認
2. docker-compose.ymlでボリュームマウントを確認:
   ```yaml
   volumes:
     - /var/run/docker.sock:/var/run/docker.sock  # Docker操作用
     - /opt:/opt  # スクリプト実行用
   ```

### データベース接続エラー

1. PostgreSQL接続情報が正しいか確認
2. N8NからPostgreSQLへのネットワーク接続を確認:
   ```bash
   docker compose -f docker-compose.production.yml exec n8n ping postgres
   ```

---

## 🎨 ワークフロー作成のベストプラクティス

### 1. エラーハンドリング

全てのワークフローにエラーハンドリングを追加:

```javascript
// Functionノードでtry-catchを使用
try {
  // メイン処理
  const result = performOperation();
  return { json: { success: true, data: result } };
} catch (error) {
  return {
    json: {
      success: false,
      error: error.message,
      timestamp: new Date().toISOString()
    }
  };
}
```

### 2. ログ記録

重要な操作はログに記録:

```javascript
// PostgreSQLにログを保存
INSERT INTO workflow_logs (workflow_name, status, message, timestamp)
VALUES ('VPS Health Check', 'SUCCESS', 'All checks passed', NOW());
```

### 3. リトライロジック

外部APIやネットワーク操作にはリトライを設定:

```javascript
// N8Nのノード設定で「Retry On Fail」を有効化
{
  "retryOnFail": true,
  "maxTries": 3,
  "waitBetweenTries": 1000  // 1秒待機
}
```

### 4. 通知の重複防止

同じアラートを短時間で複数回送信しないように制御:

```javascript
// 最後の通知時刻をチェック
const lastAlert = await getLastAlertTime();
const timeSinceLastAlert = Date.now() - lastAlert;

if (timeSinceLastAlert < 3600000) {  // 1時間以内
  return { json: { skipped: true, reason: 'Too soon since last alert' } };
}
```

---

## 📚 関連ドキュメント

- [N8N公式ドキュメント](https://docs.n8n.io/)
- [OPERATIONS_GUIDE.md](../../../OPERATIONS_GUIDE.md) - 運用ガイド
- [TROUBLESHOOTING.md](../../../TROUBLESHOOTING.md) - トラブルシューティング
- [skills/n8n-integration.js](../../../skills/n8n-integration.js) - N8Nスキル実装

---

## 🤝 コントリビューション

新しいワークフローサンプルを追加したい場合:

1. このディレクトリにJSONファイルを作成
2. `example-` プレフィックスを付ける
3. このREADMEに説明を追加
4. プルリクエストを作成

---

## 📝 ライセンス

MIT License

---

<div align="center">

**🚀 自動化で効率的なVPS運用を実現しましょう！ 🤖**

</div>
