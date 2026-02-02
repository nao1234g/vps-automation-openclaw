-- Seed Data for OpenClaw VPS Development
-- このスクリプトは開発環境用のサンプルデータを作成します
--
-- 使用方法:
-- docker compose -f docker-compose.production.yml exec postgres \
--   psql -U openclaw -d openclaw -f /docker-entrypoint-initdb.d/seed_data.sql

-- ====================
-- N8N Schema
-- ====================

-- N8Nワークフローサンプル（メタデータのみ）
-- 実際のワークフローはN8N UIからインポートしてください

\c n8n;

-- N8Nワークフロー実行履歴のサンプル
-- 注意: 実際のN8Nテーブル構造に依存します
-- このセクションはN8Nのバージョンに応じて調整が必要です

-- ====================
-- OpenNotebook Schema
-- ====================

\c opennotebook;

-- サンプルノート
INSERT INTO notes (id, title, content, tags, created_at, updated_at)
VALUES
  (
    gen_random_uuid(),
    'OpenClaw VPS セットアップガイド',
    '# OpenClaw VPS セットアップガイド

## 1. 初期セットアップ
- VPS環境の準備
- Docker/Docker Composeのインストール
- セキュリティ設定（UFW, Fail2ban）

## 2. アプリケーションデプロイ
```bash
make quick-deploy
```

## 3. 監視の確認
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090

## 4. バックアップ設定
日次バックアップスクリプトをCronに登録:
```bash
0 3 * * * /opt/vps-automation-openclaw/scripts/backup.sh
```',
    ARRAY['vps', 'setup', 'guide'],
    NOW(),
    NOW()
  ),
  (
    gen_random_uuid(),
    'セキュリティチェックリスト',
    '# セキュリティチェックリスト

## 必須項目
- [ ] SSH鍵認証の設定
- [ ] rootログインの無効化
- [ ] UFWファイアウォールの有効化
- [ ] Fail2banの設定
- [ ] SSL/TLS証明書の取得
- [ ] 定期的なセキュリティスキャン

## 推奨項目
- [ ] 2要素認証の有効化
- [ ] VPN接続の設定
- [ ] ログ監視の自動化
- [ ] バックアップの暗号化',
    ARRAY['security', 'checklist'],
    NOW(),
    NOW()
  ),
  (
    gen_random_uuid(),
    'トラブルシューティングメモ',
    '# トラブルシューティングメモ

## コンテナが起動しない
```bash
docker compose -f docker-compose.production.yml logs <service>
docker compose -f docker-compose.production.yml ps
```

## データベース接続エラー
PostgreSQL接続情報を確認:
```bash
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -c "SELECT version();"
```

## ディスク容量不足
```bash
df -h
docker system prune -a --volumes
```',
    ARRAY['troubleshooting', 'debug'],
    NOW(),
    NOW()
  );

-- サンプルタグ
INSERT INTO tags (name, color, created_at)
VALUES
  ('vps', '#3B82F6', NOW()),
  ('security', '#EF4444', NOW()),
  ('docker', '#2563EB', NOW()),
  ('guide', '#10B981', NOW()),
  ('troubleshooting', '#F59E0B', NOW()),
  ('setup', '#8B5CF6', NOW()),
  ('checklist', '#EC4899', NOW()),
  ('debug', '#6366F1', NOW())
ON CONFLICT (name) DO NOTHING;

-- ====================
-- OpenClaw Schema
-- ====================

\c openclaw;

-- サンプルチャット履歴
INSERT INTO chat_history (id, user_id, message, response, timestamp, tokens_used)
VALUES
  (
    gen_random_uuid(),
    'dev-user-001',
    'VPSのセキュリティ設定について教えてください',
    'VPSのセキュリティ設定は以下の項目が重要です：

1. SSH鍵認証の設定
2. UFWファイアウォールの有効化
3. Fail2banによる侵入防止
4. 定期的なアップデート
5. 非rootユーザーでの運用

詳細は SECURITY_CHECKLIST.md を参照してください。',
    NOW() - INTERVAL '2 days',
    512
  ),
  (
    gen_random_uuid(),
    'dev-user-001',
    'Docker Composeでアプリをデプロイする方法は？',
    'Docker Composeでのデプロイ手順：

```bash
# 環境変数の設定
cp .env.example .env
nano .env

# 本番環境デプロイ
docker compose -f docker-compose.production.yml up -d

# ヘルスチェック
./scripts/health_check.sh
```

簡単にデプロイするには:
```bash
make quick-deploy
```',
    NOW() - INTERVAL '1 day',
    384
  ),
  (
    gen_random_uuid(),
    'dev-user-002',
    'Grafanaでメトリクスを確認したい',
    'Grafanaダッシュボードへのアクセス：

1. 監視スタックを起動:
```bash
docker compose -f docker-compose.production.yml \
               -f docker-compose.monitoring.yml up -d
```

2. ブラウザでアクセス:
http://localhost:3001

3. デフォルト認証情報:
- Username: admin
- Password: .envファイルで設定したパスワード

利用可能なダッシュボード:
- System Overview
- Container Monitoring
- PostgreSQL Monitoring',
    NOW() - INTERVAL '12 hours',
    456
  );

-- サンプル設定
INSERT INTO settings (key, value, description, updated_at)
VALUES
  ('telegram_notifications', 'true', 'Telegram通知の有効/無効', NOW()),
  ('backup_retention_days', '30', 'バックアップ保持日数', NOW()),
  ('security_scan_interval', '24', 'セキュリティスキャン実行間隔（時間）', NOW()),
  ('max_concurrent_tasks', '5', '同時実行タスク数の上限', NOW()),
  ('log_level', 'info', 'ログレベル (debug/info/warn/error)', NOW())
ON CONFLICT (key) DO NOTHING;

-- サンプルタスク履歴
INSERT INTO task_history (id, task_name, status, started_at, completed_at, output)
VALUES
  (
    gen_random_uuid(),
    'daily_backup',
    'success',
    NOW() - INTERVAL '3 hours',
    NOW() - INTERVAL '2 hours 50 minutes',
    '✅ バックアップ完了
サイズ: 245MB
保存先: /opt/backups/openclaw/backup_20240201_030000'
  ),
  (
    gen_random_uuid(),
    'security_scan',
    'success',
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '23 hours 45 minutes',
    '✅ セキュリティスキャン完了
脆弱性: 0件（CRITICAL/HIGH）
警告: 2件（MEDIUM）
詳細: /opt/vps-automation-openclaw/security-reports/'
  ),
  (
    gen_random_uuid(),
    'health_check',
    'success',
    NOW() - INTERVAL '30 minutes',
    NOW() - INTERVAL '29 minutes',
    '✅ ヘルスチェック完了
全サービス正常稼働中
CPU: 32%, メモリ: 58%, ディスク: 42%'
  );

-- ====================
-- システムメトリクステーブル作成
-- ====================

\c n8n;

-- リソース監視用のメトリクステーブル
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
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_alert_level ON system_metrics(alert_level);

-- サンプルメトリクスデータ（過去24時間分）
INSERT INTO system_metrics (timestamp, cpu_percent, memory_percent, disk_percent, alert_level)
SELECT
  NOW() - (INTERVAL '15 minutes' * generate_series(0, 95)),
  20 + (random() * 40)::DECIMAL(5,2),  -- CPU: 20-60%
  40 + (random() * 30)::DECIMAL(5,2),  -- Memory: 40-70%
  35 + (random() * 10)::INTEGER,       -- Disk: 35-45%
  CASE
    WHEN random() > 0.9 THEN 'WARNING'
    ELSE 'NORMAL'
  END
FROM generate_series(0, 95);

-- ワークフローログテーブル
CREATE TABLE IF NOT EXISTS workflow_logs (
  id SERIAL PRIMARY KEY,
  workflow_name VARCHAR(255) NOT NULL,
  status VARCHAR(50) NOT NULL,
  message TEXT,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflow_logs_timestamp ON workflow_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_logs_workflow_name ON workflow_logs(workflow_name);

-- サンプルワークフローログ
INSERT INTO workflow_logs (workflow_name, status, message, timestamp)
VALUES
  ('VPS Health Check', 'SUCCESS', 'All checks passed', NOW() - INTERVAL '6 hours'),
  ('Security Scan Alert', 'SUCCESS', 'No critical vulnerabilities found', NOW() - INTERVAL '24 hours'),
  ('Database Backup Verification', 'SUCCESS', 'Backup completed: 245MB', NOW() - INTERVAL '3 hours'),
  ('System Resource Monitoring', 'SUCCESS', 'Metrics recorded', NOW() - INTERVAL '15 minutes');

-- ====================
-- ユーティリティ関数
-- ====================

\c n8n;

-- 古いメトリクスを削除する関数
CREATE OR REPLACE FUNCTION cleanup_old_metrics()
RETURNS void AS $$
BEGIN
  DELETE FROM system_metrics WHERE timestamp < NOW() - INTERVAL '90 days';
  RAISE NOTICE 'Old metrics cleaned up';
END;
$$ LANGUAGE plpgsql;

-- 古いワークフローログを削除する関数
CREATE OR REPLACE FUNCTION cleanup_old_workflow_logs()
RETURNS void AS $$
BEGIN
  DELETE FROM workflow_logs WHERE timestamp < NOW() - INTERVAL '30 days';
  RAISE NOTICE 'Old workflow logs cleaned up';
END;
$$ LANGUAGE plpgsql;

-- ====================
-- 完了メッセージ
-- ====================

\c postgres;

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'シードデータの投入が完了しました！';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE '作成されたデータ:';
  RAISE NOTICE '- OpenNotebook: 3件のノート, 8件のタグ';
  RAISE NOTICE '- OpenClaw: 3件のチャット履歴, 5件の設定, 3件のタスク履歴';
  RAISE NOTICE '- N8N: 96件のメトリクス（24時間分）, 4件のワークフローログ';
  RAISE NOTICE '';
  RAISE NOTICE 'アクセス方法:';
  RAISE NOTICE '- OpenNotebook: http://localhost:8080';
  RAISE NOTICE '- OpenClaw: http://localhost:3000';
  RAISE NOTICE '- N8N: http://localhost:5678';
  RAISE NOTICE '- Grafana: http://localhost:3001';
  RAISE NOTICE '';
END $$;
