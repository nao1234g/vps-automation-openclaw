---
name: postgres-openclaw-optimization
description: "OpenClaw環境でのPostgreSQL 16パフォーマンス最適化：スキーマ分離、インデックス設計、クエリ最適化"
source: community
risk: safe
tags:
  - postgresql
  - database
  - performance
  - optimization
  - openclaw
related_skills:
  - @database-design
  - @n8n-integration
  - @backup-strategy
---

# PostgreSQL 最適化 for OpenClaw

## Overview

OpenClaw環境で稼働するPostgreSQL 16データベースのパフォーマンスを最適化します。N8N、OpenClaw、カスタムアプリケーション（AISA等）が共有するデータベースで、スキーマ分離、適切なインデックス設計、クエリ最適化を実践し、高速かつスケーラブルなシステムを構築します。

## When to Use This Skill

このスキルを使用する場面：

- ✅ PostgreSQLが遅い・レスポンスが悪い
- ✅ N8Nワークフローの実行に数秒かかる
- ✅ 複数のアプリケーションが同じDBを共有している
- ✅ データ量が増えてきてスケーラビリティが心配
- ✅ バックアップ・リストア戦略を見直したい

Trigger keywords: `postgres slow`, `database optimization`, `query performance`, `index tuning`

## How It Works

### Step 1: 現状分析

まず、PostgreSQLのパフォーマンスボトルネックを特定します。

```bash
# コンテナに接続
docker exec -it openclaw-postgres psql -U openclaw -d openclaw

# 実行中のクエリを確認
SELECT pid, usename, application_name, state, query_start, query
FROM pg_stat_activity
WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
ORDER BY query_start;

# データベースサイズを確認
SELECT
  pg_database.datname,
  pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
ORDER BY pg_database_size(pg_database.datname) DESC;

# テーブルサイズを確認
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;
```

### Step 2: スキーマ分離

複数アプリケーションでPostgreSQLを共有する場合、スキーマを分離します。

```sql
-- N8N用スキーマ
CREATE SCHEMA IF NOT EXISTS n8n;
ALTER SCHEMA n8n OWNER TO openclaw;

-- OpenClaw用スキーマ（将来の拡張用）
CREATE SCHEMA IF NOT EXISTS openclaw;
ALTER SCHEMA openclaw OWNER TO openclaw;

-- カスタムアプリ用スキーマ（例: AISA）
CREATE SCHEMA IF NOT EXISTS aisa;
ALTER SCHEMA aisa OWNER TO openclaw;

-- デフォルトスキーマをpublicに戻す
ALTER ROLE openclaw SET search_path TO public, n8n, openclaw, aisa;
```

**スキーマ分離のメリット:**
- 権限管理が容易（スキーマ単位で権限設定可能）
- バックアップ・リストアがスキーマ単位で可能
- テーブル名の衝突を回避
- アプリケーション単位で論理的に整理

### Step 3: インデックス設計

頻繁にクエリされるカラムにインデックスを作成します。

```sql
-- 未公開レポートを取得するクエリ用インデックス
CREATE INDEX IF NOT EXISTS idx_generated_reports_published_at
ON aisa.generated_reports (published_at)
WHERE published_at IS NULL;

-- created_atでのソート用インデックス
CREATE INDEX IF NOT EXISTS idx_generated_reports_created_at
ON aisa.generated_reports (created_at DESC);

-- 複合インデックス（published_at + created_at）
CREATE INDEX IF NOT EXISTS idx_generated_reports_pub_created
ON aisa.generated_reports (published_at, created_at DESC);

-- 全文検索用インデックス（タイトル・コンテンツ）
CREATE INDEX IF NOT EXISTS idx_generated_reports_fts
ON aisa.generated_reports
USING gin(to_tsvector('english', title || ' ' || content));
```

**インデックス設計のルール:**
1. WHERE句で頻繁に使われるカラム
2. ORDER BY で使われるカラム
3. JOIN のキーカラム
4. ただし、インデックスの作りすぎは書き込み速度を低下させる

### Step 4: クエリ最適化

EXPLAIN ANALYZEでクエリの実行計画を確認し、最適化します。

```sql
-- 最適化前（全テーブルスキャン）
EXPLAIN ANALYZE
SELECT id, title, content, created_at
FROM aisa.generated_reports
WHERE published_at IS NULL
ORDER BY created_at DESC
LIMIT 1;

-- 最適化後（インデックススキャン）
-- idx_generated_reports_published_at を使用
-- Execution Time: 0.05 ms（1000倍高速化）

-- クエリプランを確認
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT id, title FROM aisa.generated_reports WHERE published_at IS NULL;
```

### Step 5: PostgreSQL設定のチューニング

Docker Composeで環境変数を設定し、PostgreSQLをチューニング：

```yaml
# docker-compose.quick.yml
services:
  postgres:
    environment:
      # 基本設定
      POSTGRES_INITDB_ARGS: "-E UTF8 --locale=C"  # パフォーマンス最適化

      # チューニングパラメータ（postgresql.confで設定可能）
      # shared_buffers: メモリの25%を割り当て（デフォルト128MB）
      # effective_cache_size: 利用可能なメモリの50-75%
      # work_mem: ソート・ハッシュ操作用（4MB〜16MB）
      # maintenance_work_mem: VACUUM, INDEX作成用（64MB〜256MB）

    command:
      - "postgres"
      - "-c"
      - "shared_buffers=256MB"
      - "-c"
      - "effective_cache_size=1GB"
      - "-c"
      - "work_mem=16MB"
      - "-c"
      - "maintenance_work_mem=128MB"
      - "-c"
      - "max_connections=100"
      - "-c"
      - "random_page_cost=1.1"  # SSD前提
```

### Step 6: 定期メンテナンス

VACUUM、ANALYZE、REINDEXを定期実行してパフォーマンスを維持します。

```sql
-- VACUUM: 削除された行の領域を回収
VACUUM ANALYZE aisa.generated_reports;

-- VACUUM FULL: テーブル全体を再構築（ロック注意）
VACUUM FULL aisa.generated_reports;

-- REINDEX: インデックスを再構築
REINDEX TABLE aisa.generated_reports;

-- 統計情報を更新（クエリプランナーの判断材料）
ANALYZE aisa.generated_reports;
```

自動VACUUMを有効化：

```sql
-- 自動VACUUM設定を確認
SHOW autovacuum;

-- テーブル単位で自動VACUUM設定
ALTER TABLE aisa.generated_reports SET (
  autovacuum_vacuum_scale_factor = 0.1,  -- 10%の行が変更されたらVACUUM
  autovacuum_analyze_scale_factor = 0.05  -- 5%の行が変更されたらANALYZE
);
```

## Examples

### Example 1: スロークエリの特定と最適化

```sql
-- pg_stat_statements拡張をインストール（初回のみ）
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 実行時間が長いクエリTOP 10
SELECT
  round(total_exec_time::numeric, 2) AS total_time_ms,
  calls,
  round(mean_exec_time::numeric, 2) AS avg_time_ms,
  query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- 特定のクエリを最適化
-- 例: WHERE published_at IS NULL が遅い
-- → 部分インデックスを作成
CREATE INDEX idx_unpublished ON aisa.generated_reports (created_at DESC)
WHERE published_at IS NULL;
```

### Example 2: コネクションプーリング

N8Nや複数アプリケーションからの接続を効率化：

```yaml
# docker-compose.quick.yml
services:
  pgbouncer:
    image: pgbouncer/pgbouncer:latest
    environment:
      DATABASES_HOST: postgres
      DATABASES_PORT: 5432
      DATABASES_USER: openclaw
      DATABASES_PASSWORD: ${POSTGRES_PASSWORD}
      PGBOUNCER_POOL_MODE: transaction  # トランザクション単位でプール
      PGBOUNCER_MAX_CLIENT_CONN: 1000
      PGBOUNCER_DEFAULT_POOL_SIZE: 25
    ports:
      - "6432:6432"
    depends_on:
      - postgres
```

アプリケーション側の接続先を変更：

```bash
# Before: 直接PostgreSQLに接続
DATABASE_URL=postgresql://openclaw:password@postgres:5432/openclaw

# After: PgBouncerを経由
DATABASE_URL=postgresql://openclaw:password@pgbouncer:6432/openclaw
```

### Example 3: パーティショニング

大量データを月単位で分割して管理：

```sql
-- 親テーブル作成
CREATE TABLE aisa.generated_reports_partitioned (
  id SERIAL,
  title VARCHAR(500),
  content TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  published_at TIMESTAMP
) PARTITION BY RANGE (created_at);

-- 月別パーティション作成
CREATE TABLE aisa.generated_reports_2026_02 PARTITION OF aisa.generated_reports_partitioned
FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE aisa.generated_reports_2026_03 PARTITION OF aisa.generated_reports_partitioned
FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- インデックスは各パーティションに自動作成される
CREATE INDEX ON aisa.generated_reports_partitioned (published_at) WHERE published_at IS NULL;
```

## Best Practices

### ✅ Do This

- **スキーマ分離**: アプリケーションごとにスキーマを作成
- **適切なインデックス**: WHERE, ORDER BY, JOINで使うカラムに作成
- **EXPLAIN ANALYZE**: 本番投入前に必ずクエリプランを確認
- **定期VACUUM**: 自動VACUUMを有効化 + 手動VACUUM FULLを月1回
- **統計情報更新**: ANALYZEを定期実行してプランナーを最新化
- **バックアップ**: スキーマ単位で`pg_dump`を定期実行
- **モニタリング**: `pg_stat_activity`, `pg_stat_statements`で監視

### ❌ Avoid This

- **SELECT ***: 必要なカラムだけを指定する
- **インデックスの作りすぎ**: 書き込み速度が低下する
- **VACUUM FULL の頻繁な実行**: テーブルロックが発生する
- **過度なJOIN**: サブクエリやCTEで分割する
- **N+1クエリ**: ループ内でクエリを発行しない
- **トランザクションの長時間保持**: VACUUM が動作しなくなる

## Common Pitfalls

### Problem: N8Nワークフローが遅い

**Root Cause:** PostgreSQLノードのクエリが最適化されていない

**Solution:**
```sql
-- Before: 全テーブルスキャン
SELECT * FROM aisa.generated_reports WHERE published_at IS NULL;

-- After: インデックス + 必要なカラムのみ
SELECT id, title, content FROM aisa.generated_reports
WHERE published_at IS NULL
ORDER BY created_at DESC
LIMIT 1;

-- インデックス作成
CREATE INDEX idx_unpublished ON aisa.generated_reports (published_at, created_at DESC);
```

**Prevention:** N8Nワークフロー作成時にEXPLAIN ANALYZEで検証

---

### Problem: ディスク容量がすぐ満杯になる

**Root Cause:** VACUUM が実行されず、dead tuples（削除済み行）が蓄積

**Solution:**
```sql
-- 自動VACUUMの状態を確認
SELECT schemaname, tablename, last_vacuum, last_autovacuum, n_dead_tup
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- 手動VACUUM
VACUUM FULL aisa.generated_reports;

-- 自動VACUUMを有効化
ALTER SYSTEM SET autovacuum = on;
SELECT pg_reload_conf();
```

**Prevention:** 自動VACUUMを必ず有効化、月1回のVACUUM FULLをcron登録

---

### Problem: コネクション数上限エラー

**Root Cause:** `max_connections=100` を超えた接続

**Solution:**
```sql
-- 現在の接続数を確認
SELECT count(*) FROM pg_stat_activity;

-- アプリケーション別の接続数
SELECT application_name, count(*)
FROM pg_stat_activity
GROUP BY application_name;

-- max_connectionsを増やす（再起動必要）
ALTER SYSTEM SET max_connections = 200;
-- または PgBouncer でコネクションプーリング
```

**Prevention:** PgBouncerを導入してコネクションプール管理

## Configuration Reference

### 推奨PostgreSQL設定

```ini
# postgresql.conf（Docker commandで指定）

# メモリ設定
shared_buffers = 256MB              # 搭載メモリの25%
effective_cache_size = 1GB          # 搭載メモリの50-75%
work_mem = 16MB                     # ソート・ハッシュ用
maintenance_work_mem = 128MB        # VACUUM, INDEX作成用

# コネクション
max_connections = 100               # 同時接続数上限

# クエリプランナー
random_page_cost = 1.1              # SSD前提（HDD: 4.0）
effective_io_concurrency = 200      # SSD並列I/O

# WAL設定
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# ログ設定
log_min_duration_statement = 1000   # 1秒以上のクエリをログ
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
```

### Docker Composeでの適用

```yaml
services:
  postgres:
    command:
      - "postgres"
      - "-c"
      - "shared_buffers=256MB"
      - "-c"
      - "effective_cache_size=1GB"
      - "-c"
      - "work_mem=16MB"
      - "-c"
      - "maintenance_work_mem=128MB"
      - "-c"
      - "max_connections=100"
      - "-c"
      - "random_page_cost=1.1"
      - "-c"
      - "log_min_duration_statement=1000"
```

## Related Skills

- `@n8n-openclaw-integration` - N8NとPostgreSQLの統合
- `@database-backup-restore` - バックアップ戦略
- `@docker-performance-tuning` - Dockerコンテナ最適化
- See also: `docs/ARCHITECTURE.md` - データベース設計

## Troubleshooting

### Issue 1: VACUUM FULL が終わらない

**Symptoms:**
- VACUUM FULLが数時間実行されたまま

**Diagnosis:**
```sql
-- VACUUM進捗を確認
SELECT pid, phase, round(100.0 * heap_blks_scanned / heap_blks_total, 1) AS progress_pct
FROM pg_stat_progress_vacuum;
```

**Fix:**
```sql
-- VACUUM FULLをキャンセル
SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE query LIKE 'VACUUM FULL%';

-- 通常のVACUUMで対処
VACUUM ANALYZE aisa.generated_reports;
```

### Issue 2: インデックスが使われない

**Symptoms:**
- インデックスを作成したのにSeq Scan（全テーブルスキャン）が実行される

**Diagnosis:**
```sql
EXPLAIN ANALYZE SELECT * FROM aisa.generated_reports WHERE published_at IS NULL;
-- → Seq Scan on generated_reports
```

**Fix:**
```sql
-- 統計情報を更新
ANALYZE aisa.generated_reports;

-- インデックスの状態を確認
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE schemaname = 'aisa';

-- インデックスが適切に設計されているか確認
-- → WHERE句のカラムとインデックスのカラムが一致しているか
```

## Advanced Usage

### Materialized View でクエリ高速化

集計クエリを Materialized View で事前計算：

```sql
-- 月別レポート数の集計ビュー
CREATE MATERIALIZED VIEW aisa.monthly_report_stats AS
SELECT
  DATE_TRUNC('month', created_at) AS month,
  COUNT(*) AS total_reports,
  COUNT(published_at) AS published_reports
FROM aisa.generated_reports
GROUP BY DATE_TRUNC('month', created_at);

-- インデックス作成
CREATE INDEX ON aisa.monthly_report_stats (month);

-- 定期的にリフレッシュ（N8Nで自動化）
REFRESH MATERIALIZED VIEW aisa.monthly_report_stats;
```

### レプリケーション設定

本番環境でのHA構成：

```yaml
# docker-compose.production.yml
services:
  postgres-primary:
    image: postgres:16-alpine
    environment:
      POSTGRES_REPLICATION_MODE: master
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}

  postgres-replica:
    image: postgres:16-alpine
    environment:
      POSTGRES_REPLICATION_MODE: slave
      POSTGRES_MASTER_HOST: postgres-primary
      POSTGRES_MASTER_PORT: 5432
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
```

## References

- [PostgreSQL Official Documentation](https://www.postgresql.org/docs/16/)
- [PgTune](https://pgtune.leopard.in.ua/) - PostgreSQL設定自動生成ツール
- [pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html)
- [PgBouncer](https://www.pgbouncer.org/)
- Related: `docker/postgres/init/` - 初期化スクリプト

---

*最終更新: 2026-02-14 — OpenClaw環境でのPostgreSQL最適化ノウハウを追加*
