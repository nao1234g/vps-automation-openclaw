# Load Testing with k6

## 概要

このディレクトリには、OpenClaw VPSの負荷テストスクリプトが含まれています。[k6](https://k6.io/)を使用して、システムのパフォーマンスとスケーラビリティをテストします。

## インストール

### macOS (Homebrew)

```bash
brew install k6
```

### Ubuntu/Debian

```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

### Docker

```bash
docker pull grafana/k6
```

## テストスイート

### 1. 標準負荷テスト (k6-config.js)

システムの通常運用時のパフォーマンスをテストします。

**実行方法**:
```bash
k6 run tests/load/k6-config.js
```

**テストステージ**:
- Warm-up: 10 VUs (1分)
- Stay: 10 VUs (3分)
- Ramp-up: 50 VUs (1分)
- Peak: 50 VUs (5分)
- Spike: 100 VUs (2分)
- Cool-down (2分)

**しきい値**:
- HTTPリクエストの95%が500ms以内
- エラー率5%未満
- ヘルスチェックの95%が200ms以内

### 2. スパイクテスト (spike-test.js)

突然の負荷急増に対するシステムの耐性をテストします。

**実行方法**:
```bash
k6 run tests/load/spike-test.js
```

**テストステージ**:
- 準備: 10 VUs (30秒)
- スパイク: 200 VUs (10秒で急増)
- 持続: 200 VUs (1分)
- 回復: 10 VUs (30秒)

**しきい値**:
- スパイク時も95%が1秒以内
- エラー率10%未満

### 3. ストレステスト (stress-test.js)

システムの限界を見つけるためのテストです。

**実行方法**:
```bash
k6 run tests/load/stress-test.js
```

**テストステージ**:
- 50 VUs → 100 VUs → 200 VUs → 300 VUs → 400 VUs
- 各ステージ2分間
- 合計約14分

**しきい値**:
- 95%が2秒以内
- エラー率20%未満

### 4. ソークテスト (soak-test.js)

長時間の負荷に対する安定性をテストします（メモリリーク検出など）。

**実行方法**:
```bash
k6 run tests/load/soak-test.js
```

**テストステージ**:
- ウォームアップ: 50 VUs (5分)
- ソーク: 50 VUs (2時間)
- クールダウン (5分)

**しきい値**:
- 95%が500ms以内を維持
- エラー率1%未満

## カスタムオプション

### 仮想ユーザー数と期間の変更

```bash
k6 run --vus 20 --duration 60s tests/load/k6-config.js
```

### ベースURLの指定

```bash
k6 run -e BASE_URL=https://your-domain.com tests/load/k6-config.js
```

### 結果の保存

```bash
# JSON形式で保存
k6 run --out json=results.json tests/load/k6-config.js

# InfluxDBに送信
k6 run --out influxdb=http://localhost:8086/k6 tests/load/k6-config.js
```

## 結果の分析

テスト実行後、以下のファイルが生成されます:

- `tests/load/results/summary.json` - 詳細なメトリクスデータ
- `tests/load/results/summary.html` - HTMLレポート

### 主要メトリクス

1. **http_req_duration**: HTTPリクエストの応答時間
   - avg: 平均
   - min: 最小
   - max: 最大
   - p(50), p(90), p(95), p(99): パーセンタイル

2. **http_req_failed**: 失敗したリクエストの割合

3. **errors**: カスタムエラー率

4. **health_check_duration**: ヘルスチェックの応答時間

5. **api_call_duration**: APIコールの応答時間

### レポート例

```
========================================
  Load Test Summary
========================================

Total Requests: 12,543
Error Rate: 2.34%
Failed Requests: 1.12%

Response Times:
  Avg: 245.67ms
  Min: 45.23ms
  Max: 1234.56ms
  p(50): 198.45ms
  p(90): 456.78ms
  p(95): 567.89ms
  p(99): 890.12ms

Health Check Duration:
  Avg: 123.45ms
  p(95): 178.90ms

API Call Duration:
  Avg: 345.67ms
  p(95): 678.90ms

========================================
```

## ベストプラクティス

### 1. テスト環境

- 本番環境では**実行しない**
- 専用のテスト環境またはステージング環境を使用
- テスト前にバックアップを取得

### 2. 段階的なテスト

```bash
# 1. まず小規模でテスト
k6 run --vus 5 --duration 30s tests/load/k6-config.js

# 2. 問題なければ中規模
k6 run --vus 20 --duration 2m tests/load/k6-config.js

# 3. 最終的に本番想定の負荷
k6 run tests/load/k6-config.js
```

### 3. 監視

テスト実行中は以下を監視:
- CPU使用率
- メモリ使用率
- ディスク I/O
- ネットワーク帯域
- データベース接続数

```bash
# 別のターミナルで監視
./scripts/status_dashboard.sh --watch
```

### 4. テスト後の確認

```bash
# ログ確認
docker compose logs

# リソース使用状況
docker stats

# データベース接続数
docker compose exec postgres psql -U openclaw -c "SELECT count(*) FROM pg_stat_activity;"
```

## トラブルシューティング

### k6が接続できない

```bash
# サーバーが起動しているか確認
curl http://localhost/health

# ファイアウォール確認
sudo ufw status
```

### タイムアウトエラーが多発

```bash
# タイムアウト時間を延長
k6 run --http-debug tests/load/k6-config.js
```

### メモリ不足

```bash
# VU数を減らす
k6 run --vus 10 tests/load/k6-config.js

# または、Docker のメモリ制限を増やす
docker compose up -d --scale openclaw=2
```

## CI/CD統合

### GitHub Actions

```yaml
name: Load Test

on:
  schedule:
    - cron: '0 2 * * 0'  # 毎週日曜 2:00 AM

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6

      - name: Start services
        run: docker compose -f docker-compose.minimal.yml up -d

      - name: Run load test
        run: k6 run tests/load/k6-config.js

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: load-test-results
          path: tests/load/results/
```

## 参考資料

- [k6 Documentation](https://k6.io/docs/)
- [k6 Examples](https://k6.io/docs/examples/)
- [Performance Testing Best Practices](https://k6.io/docs/testing-guides/api-load-testing/)

## パフォーマンス目標

| メトリクス | 目標 | 警告 | 危機 |
|-----------|------|------|------|
| 平均応答時間 | < 200ms | < 500ms | > 1000ms |
| p95応答時間 | < 500ms | < 1000ms | > 2000ms |
| p99応答時間 | < 1000ms | < 2000ms | > 5000ms |
| エラー率 | < 0.1% | < 1% | > 5% |
| スループット | > 100 req/s | > 50 req/s | < 20 req/s |

---

負荷テストにより、システムの限界を理解し、本番環境での安定性を確保できます。
