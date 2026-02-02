# Grafana Dashboards

このディレクトリには、OpenClaw VPS環境の監視用Grafanaダッシュボードが含まれています。

## 📊 含まれるダッシュボード

### 1. System Overview Dashboard (system-overview.json)

**目的**: システム全体のリソース使用状況を監視

**パネル**:
- 🖥️ **CPU使用率**: システム全体のCPU使用状況（5分平均）
- 🧠 **メモリ使用率**: 使用可能なメモリと使用中メモリ
- 💾 **ディスク使用率**: ルートファイルシステムの使用状況
- 🌐 **ネットワークI/O**: 受信/送信バイト数

**推奨用途**:
- 日常的なシステムヘルスチェック
- リソース枯渇の早期発見
- キャパシティプランニング

**アクセス**: [http://localhost:3001](http://localhost:3001)

---

### 2. Container Monitoring Dashboard (container-monitoring.json)

**目的**: 各Dockerコンテナの詳細な監視

**パネル**:

#### リソース使用状況
- 📈 **Container CPU Usage**: 各コンテナのCPU使用率（%）
- 💾 **Container Memory Usage**: 各コンテナのメモリ使用量（bytes）
- 🌐 **Container Network I/O**: 送受信ネットワークトラフィック

#### ステータス監視（ゲージ）
- ✅ **OpenClaw Status**: コンテナの稼働状態
- ✅ **N8N Status**: コンテナの稼働状態
- ✅ **OpenNotebook Status**: コンテナの稼働状態
- ✅ **PostgreSQL Status**: コンテナの稼働状態
- ✅ **Nginx Status**: コンテナの稼働状態

#### 詳細メトリクス
- 📊 **Container States**: 実行中/停止中/一時停止のコンテナ数
- 🔄 **Container Restart History**: コンテナの再起動履歴

**推奨用途**:
- コンテナレベルのリソース分析
- パフォーマンスボトルネックの特定
- コンテナの安定性監視

**重要**: リソース制限値に対する使用率を確認し、必要に応じて[docker-compose.production.yml](../../docker-compose.production.yml)で調整してください。

---

### 3. PostgreSQL Monitoring Dashboard (postgresql-monitoring.json)

**目的**: PostgreSQLデータベースのパフォーマンスと健全性を監視

**パネル**:

#### 基本メトリクス（ゲージ）
- 🔗 **Active Connections**: アクティブな接続数
- 💾 **Database Size**: データベースサイズ（bytes）
- ⏱️ **PostgreSQL Uptime**: PostgreSQLの起動時間
- ✅ **PostgreSQL Status**: サービス稼働状態

#### トランザクション
- 📈 **Transaction Rate**: コミット/ロールバックレート（秒あたり）
- 📊 **Tuple Operations**: 行の読み取り/挿入/更新/削除レート

#### パフォーマンス
- ⚡ **Cache Hit Ratio**: バッファキャッシュヒット率（%）
  - **推奨値**: 95%以上
  - **警告**: 90%未満の場合、shared_buffersの増加を検討
- 🔒 **Database Locks**: ロック数の推移
- ⚠️ **Deadlocks & Conflicts**: デッドロック/競合の検出

#### データベースサイズ
- 📦 **Database Sizes by Schema**: スキーマ別のデータベースサイズ
  - N8N DB
  - OpenNotebook DB
  - OpenClaw DB

**推奨用途**:
- クエリパフォーマンスの監視
- キャッシュ効率の評価
- 接続プールのサイジング
- デッドロック問題の検出

**パフォーマンスチューニング**:
- Cache Hit Ratio < 95%: `shared_buffers`を増やす
- 接続数が頻繁に上限到達: 接続プール設定を見直す
- デッドロック頻発: トランザクション設計を見直す

---

## 🚀 使用方法

### 1. 監視スタックの起動

```bash
# 本番環境 + 監視スタックを起動
docker compose -f docker-compose.production.yml \
               -f docker-compose.monitoring.yml up -d

# または Makefile経由
make monitoring
```

### 2. Grafanaへのアクセス

```bash
# ローカル環境
http://localhost:3001

# 本番環境（ドメイン設定済みの場合）
https://your-domain.com:3001
```

**デフォルト認証情報**:
- Username: `admin`
- Password: `.env`ファイルの`GF_SECURITY_ADMIN_PASSWORD`で設定

### 3. ダッシュボードのインポート

ダッシュボードは自動的にプロビジョニングされますが、手動でインポートする場合:

1. Grafanaダッシュボードにログイン
2. 左メニュー「+」→「Import」を選択
3. このディレクトリのJSONファイルをアップロード
4. データソースに「Prometheus」を選択
5. 「Import」をクリック

### 4. データソースの設定

Prometheusデータソースは自動的に設定されますが、手動で追加する場合:

```yaml
Name: Prometheus
Type: Prometheus
URL: http://prometheus:9090
Access: Server (default)
```

---

## 🛠️ カスタマイズ

### パネルの追加

既存のダッシュボードに新しいパネルを追加:

1. ダッシュボードを開く
2. 右上の「Add panel」をクリック
3. クエリを設定（PromQL）
4. ビジュアライゼーションタイプを選択
5. 「Apply」で保存

### Prometheusクエリ例

```promql
# コンテナCPU使用率（パーセンテージ）
rate(container_cpu_usage_seconds_total{name="openclaw"}[5m]) * 100

# コンテナメモリ使用率
container_memory_usage_bytes{name="openclaw"}

# PostgreSQL接続数
pg_stat_activity_count

# PostgreSQLキャッシュヒット率
rate(pg_stat_database_blks_hit{datname="openclaw"}[5m]) /
(rate(pg_stat_database_blks_hit{datname="openclaw"}[5m]) +
 rate(pg_stat_database_blks_read{datname="openclaw"}[5m])) * 100

# ディスク使用率
(node_filesystem_size_bytes - node_filesystem_avail_bytes) /
node_filesystem_size_bytes * 100
```

### アラートの設定

ダッシュボードパネルにアラートを追加:

1. パネルを編集
2. 「Alert」タブを選択
3. 「Create Alert」をクリック
4. 条件を設定（例: CPU > 80%）
5. 通知チャンネルを選択
6. 「Save」で保存

**推奨アラート条件**:
- CPU使用率 > 80%
- メモリ使用率 > 85%
- ディスク使用率 > 85%
- PostgreSQL接続数 > 80
- キャッシュヒット率 < 95%

---

## 📊 ダッシュボード変数の活用

### 時間範囲の変更

各ダッシュボードの右上で時間範囲を変更可能:
- Last 5 minutes
- Last 15 minutes
- Last 1 hour
- Last 6 hours（デフォルト）
- Last 24 hours
- Last 7 days
- Custom range

### リフレッシュ間隔

自動リフレッシュ間隔の設定（右上）:
- Off
- 10s
- 30s（デフォルト）
- 1m
- 5m

---

## 🔧 トラブルシューティング

### ダッシュボードにデータが表示されない

1. Prometheusが正常に動作しているか確認:
   ```bash
   curl http://localhost:9090/api/v1/query?query=up
   ```

2. Prometheusターゲットの状態を確認:
   ```bash
   # ブラウザで開く
   http://localhost:9090/targets
   ```

3. Grafanaのデータソース設定を確認:
   - Configuration → Data Sources → Prometheus
   - 「Save & Test」で接続テスト

### メトリクスが一部欠けている

1. 対象のコンテナが起動しているか確認:
   ```bash
   docker compose -f docker-compose.production.yml ps
   ```

2. Prometheusの設定を確認:
   ```bash
   docker compose -f docker-compose.monitoring.yml exec prometheus \
     cat /etc/prometheus/prometheus.yml
   ```

3. exporterが正常に動作しているか確認:
   ```bash
   # Node Exporter
   curl http://localhost:9100/metrics

   # cAdvisor
   curl http://localhost:8080/metrics
   ```

### PostgreSQLメトリクスが表示されない

PostgreSQL Exporterが必要です（将来的に追加予定）:

```yaml
# docker-compose.monitoring.ymlに追加
postgres-exporter:
  image: prometheuscommunity/postgres-exporter
  environment:
    DATA_SOURCE_NAME: "postgresql://openclaw:${POSTGRES_PASSWORD}@postgres:5432/openclaw?sslmode=disable"
  ports:
    - "9187:9187"
```

---

## 📈 パフォーマンス最適化

### Grafana設定の最適化

[docker/grafana/grafana.ini](../grafana.ini)で以下を調整:

```ini
[database]
# クエリキャッシュを有効化
query_cache_type = 2
query_cache_max_size = 50MB

[dataproxy]
# タイムアウトを調整
timeout = 30
```

### Prometheusデータ保持期間の調整

[docker/prometheus/prometheus.yml](../prometheus/prometheus.yml)で調整:

```yaml
# デフォルト: 15日
storage:
  tsdb:
    retention.time: 30d
```

**注意**: 保持期間を長くするとディスク使用量が増加します。

---

## 🎨 ダッシュボード作成のベストプラクティス

### 1. 論理的なグループ化

関連するメトリクスを同じ行にグループ化:
```
Row 1: システム概要（CPU, メモリ, ディスク）
Row 2: コンテナステータス（ゲージ）
Row 3: ネットワーク & I/O
Row 4: アプリケーション固有のメトリクス
```

### 2. 適切なビジュアライゼーション

- **時系列データ**: Time series グラフ
- **現在値**: Gauge, Stat
- **比較**: Bar chart
- **分布**: Heatmap

### 3. 色の使い分け

```
Green: 正常（< 80%）
Yellow: 警告（80-90%）
Red: 危険（> 90%）
```

### 4. 単位の明記

すべてのパネルに適切な単位を設定:
- `bytes`: バイト
- `percent`: パーセント
- `short`: 数値
- `ops`: オペレーション/秒

---

## 📚 関連ドキュメント

- [Prometheus Configuration](../prometheus/prometheus.yml)
- [Alert Rules](../prometheus/alerts.yml)
- [PERFORMANCE.md](../../../PERFORMANCE.md) - パフォーマンス最適化ガイド
- [TROUBLESHOOTING.md](../../../TROUBLESHOOTING.md) - トラブルシューティング
- [Grafana公式ドキュメント](https://grafana.com/docs/)
- [Prometheus公式ドキュメント](https://prometheus.io/docs/)

---

## 🤝 コントリビューション

新しいダッシュボードを追加したい場合:

1. このディレクトリにJSONファイルを作成
2. わかりやすい命名規則に従う（例: `nginx-monitoring.json`）
3. このREADMEに説明を追加
4. プルリクエストを作成

---

## 📝 ライセンス

MIT License

---

<div align="center">

**📊 データドリブンなVPS運用を実現しましょう！ 📈**

</div>
