# パフォーマンス最適化ガイド

OpenClaw VPS環境のパフォーマンスを最適化するためのベストプラクティスとチューニング方法。

## 📋 目次

1. [システムレベルの最適化](#システムレベルの最適化)
2. [Dockerの最適化](#dockerの最適化)
3. [データベースの最適化](#データベースの最適化)
4. [Nginxの最適化](#nginxの最適化)
5. [アプリケーションの最適化](#アプリケーションの最適化)
6. [監視とボトルネック特定](#監視とボトルネック特定)

---

## システムレベルの最適化

### スワップの設定

```bash
# 現在のスワップ確認
free -h

# スワップファイル作成（4GB）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永続化
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# スワップ使用率の調整（デフォルト60 → 10に下げる）
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

### ファイルディスクリプタの増加

```bash
# 現在の制限確認
ulimit -n

# 制限を増加
sudo tee -a /etc/security/limits.conf << EOF
* soft nofile 65536
* hard nofile 65536
EOF

# システム全体の制限
sudo tee -a /etc/sysctl.conf << EOF
fs.file-max = 2097152
EOF

sudo sysctl -p
```

### I/O スケジューラの最適化

```bash
# SSD用の設定
echo "none" | sudo tee /sys/block/sda/queue/scheduler

# 永続化
echo 'ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/scheduler}="none"' | \
  sudo tee /etc/udev/rules.d/60-io-scheduler.rules
```

---

## Dockerの最適化

### イメージサイズの削減

**Dockerfile最適化:**
```dockerfile
# マルチステージビルド使用
FROM node:20-alpine AS builder
# ビルド処理

FROM node:20-alpine
# 本番環境（必要最小限）
COPY --from=builder /build ./
```

**不要なレイヤー削除:**
```bash
# イメージのスキャン
docker images

# 未使用イメージの削除
docker image prune -a

# ビルドキャッシュのクリア
docker builder prune -a
```

### リソース制限の調整

`docker-compose.production.yml`の最適化:

```yaml
services:
  openclaw:
    deploy:
      resources:
        limits:
          cpus: '2.0'      # 必要に応じて調整
          memory: 2G       # 実際の使用量に合わせる
        reservations:
          cpus: '1.0'      # 最小保証
          memory: 1G
```

### ログローテーション

```yaml
services:
  openclaw:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"    # ファイルサイズ制限
        max-file: "3"      # ファイル数制限
        compress: "true"   # 圧縮有効化
```

### ボリュームの最適化

```bash
# ボリュームドライバーのパフォーマンス確認
docker volume inspect <ボリューム名>

# local-persist ドライバーを使用（永続化が必要な場合）
# overlay2 ストレージドライバーを使用（デフォルト、推奨）
docker info | grep "Storage Driver"
```

---

## データベースの最適化

### PostgreSQL設定のチューニング

環境変数で設定（`docker-compose.production.yml`）:

```yaml
environment:
  # 接続設定
  POSTGRES_MAX_CONNECTIONS: 100

  # メモリ設定（システムRAMの25%推奨）
  POSTGRES_SHARED_BUFFERS: 512MB
  POSTGRES_EFFECTIVE_CACHE_SIZE: 2GB
  POSTGRES_MAINTENANCE_WORK_MEM: 128MB
  POSTGRES_WORK_MEM: 16MB

  # WAL設定
  POSTGRES_WAL_BUFFERS: 16MB
  POSTGRES_CHECKPOINT_COMPLETION_TARGET: 0.9

  # プランナー設定
  POSTGRES_DEFAULT_STATISTICS_TARGET: 100
  POSTGRES_RANDOM_PAGE_COST: 1.1  # SSDの場合
```

### インデックスの最適化

```sql
-- 使用頻度の高いクエリを分析
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

-- 欠落インデックスの検出
SELECT schemaname, tablename, attname, null_frac, avg_width, n_distinct
FROM pg_stats
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
  AND null_frac < 0.9
ORDER BY null_frac DESC;

-- インデックス作成例
CREATE INDEX CONCURRENTLY idx_notebooks_created_at
ON opennotebook.notebooks(created_at DESC);
```

### バキュームの自動化

```sql
-- 自動バキューム設定確認
SHOW autovacuum;

-- 手動バキューム
VACUUM ANALYZE;

-- 詳細バキューム
VACUUM (VERBOSE, ANALYZE) opennotebook.notebooks;
```

### コネクションプーリング

PgBouncer導入（オプション）:

```yaml
services:
  pgbouncer:
    image: pgbouncer/pgbouncer:latest
    environment:
      DATABASES_HOST: postgres
      DATABASES_PORT: 5432
      DATABASES_USER: openclaw
      DATABASES_PASSWORD: ${POSTGRES_PASSWORD}
      PGBOUNCER_POOL_MODE: transaction
      PGBOUNCER_MAX_CLIENT_CONN: 1000
      PGBOUNCER_DEFAULT_POOL_SIZE: 25
    ports:
      - "6432:5432"
```

---

## Nginxの最適化

### Worker設定

```nginx
# nginx.conf
worker_processes auto;  # CPUコア数に自動調整
worker_rlimit_nofile 65536;

events {
    worker_connections 4096;  # 増加
    use epoll;                # Linuxで最適
    multi_accept on;
}
```

### キャッシュ設定

```nginx
http {
    # ファイルキャッシュ
    open_file_cache max=10000 inactive=30s;
    open_file_cache_valid 60s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    # プロキシキャッシュ
    proxy_cache_path /var/cache/nginx levels=1:2
                     keys_zone=my_cache:10m
                     max_size=1g
                     inactive=60m
                     use_temp_path=off;

    server {
        location /api/ {
            proxy_cache my_cache;
            proxy_cache_use_stale error timeout http_500 http_502 http_503;
            proxy_cache_valid 200 10m;
            add_header X-Cache-Status $upstream_cache_status;
        }
    }
}
```

### Gzip圧縮

```nginx
gzip on;
gzip_vary on;
gzip_comp_level 6;
gzip_min_length 1000;
gzip_types
    text/plain
    text/css
    text/javascript
    application/json
    application/javascript
    application/xml
    image/svg+xml;
```

### HTTP/2有効化

```nginx
server {
    listen 443 ssl http2;  # http2追加
    listen [::]:443 ssl http2;
}
```

---

## アプリケーションの最適化

### Node.js (OpenClaw/OpenNotebook)

**メモリ制限:**
```yaml
services:
  openclaw:
    environment:
      NODE_OPTIONS: "--max-old-space-size=1536"  # MB単位
```

**クラスターモード:**
```javascript
// server.js
const cluster = require('cluster');
const os = require('os');

if (cluster.isMaster) {
  const numCPUs = os.cpus().length;
  for (let i = 0; i < numCPUs; i++) {
    cluster.fork();
  }
} else {
  // アプリケーション起動
  require('./app');
}
```

**キャッシング:**
```javascript
// Redisキャッシュ導入
const redis = require('redis');
const client = redis.createClient({
  host: 'redis',
  port: 6379
});

// キャッシュミドルウェア
const cacheMiddleware = (duration) => (req, res, next) => {
  const key = `cache:${req.originalUrl}`;
  client.get(key, (err, data) => {
    if (data) {
      return res.json(JSON.parse(data));
    }
    res.sendResponse = res.json;
    res.json = (body) => {
      client.setex(key, duration, JSON.stringify(body));
      res.sendResponse(body);
    };
    next();
  });
};
```

---

## 監視とボトルネック特定

### Prometheusメトリクス

監視スタック起動:
```bash
docker compose -f docker-compose.production.yml \
               -f docker-compose.monitoring.yml up -d
```

アクセス:
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001`

### 主要メトリクス

**CPU:**
```promql
100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

**メモリ:**
```promql
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

**ディスク I/O:**
```promql
rate(node_disk_read_bytes_total[5m])
rate(node_disk_written_bytes_total[5m])
```

**コンテナメモリ:**
```promql
container_memory_usage_bytes / container_spec_memory_limit_bytes * 100
```

### ボトルネック特定

```bash
# 1. システムリソース
htop
iotop
vmstat 1

# 2. Dockerコンテナ
docker stats

# 3. ネットワーク
iftop
nethogs

# 4. ディスク
iostat -x 1
df -h

# 5. PostgreSQL
docker compose exec postgres \
  psql -U openclaw -c "SELECT * FROM pg_stat_activity;"
```

---

## パフォーマンステスト

### 負荷テスト

**Apache Bench:**
```bash
# 100並列、1000リクエスト
ab -n 1000 -c 100 http://localhost/api/health
```

**wrk:**
```bash
# 12スレッド、400接続、30秒
wrk -t12 -c400 -d30s http://localhost/
```

### ベンチマーク

定期的に実行してパフォーマンス低下を検出:

```bash
# スクリプト作成
cat > benchmark.sh << 'EOF'
#!/bin/bash
echo "=== API Response Time ==="
time curl -s http://localhost/api/health > /dev/null

echo "=== Database Query Time ==="
docker compose exec -T postgres psql -U openclaw -c "\timing" -c "SELECT count(*) FROM opennotebook.notebooks;"

echo "=== Disk I/O ==="
dd if=/dev/zero of=/tmp/test bs=1M count=1024 oflag=direct
rm /tmp/test
EOF

chmod +x benchmark.sh
./benchmark.sh
```

---

## 推奨リソース配分

### 小規模環境（4GB RAM）

```yaml
postgres:
  deploy:
    resources:
      limits:
        memory: 1G
      reservations:
        memory: 512M

openclaw:
  deploy:
    resources:
      limits:
        memory: 1.5G
      reservations:
        memory: 768M

n8n:
  deploy:
    resources:
      limits:
        memory: 768M
      reservations:
        memory: 384M
```

### 中規模環境（8GB RAM）

```yaml
postgres:
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 1G

openclaw:
  deploy:
    resources:
      limits:
        memory: 3G
      reservations:
        memory: 1.5G

n8n:
  deploy:
    resources:
      limits:
        memory: 1.5G
      reservations:
        memory: 768M
```

---

## チェックリスト

パフォーマンス最適化を実施する際のチェックリスト:

- [ ] システムスワップ設定済み
- [ ] ファイルディスクリプタ増加済み
- [ ] Dockerイメージサイズ最小化
- [ ] リソース制限適切に設定
- [ ] ログローテーション設定済み
- [ ] PostgreSQLチューニング実施
- [ ] インデックス最適化済み
- [ ] Nginxキャッシュ設定済み
- [ ] 監視ダッシュボード構築済み
- [ ] 定期的なパフォーマンステスト実施

---

**💡 Tip**: パフォーマンス最適化は継続的なプロセスです。監視データを定期的に確認し、ボトルネックを特定して改善しましょう。
