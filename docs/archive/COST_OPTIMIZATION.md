# Cost Optimization Guide

OpenClaw VPS 環境のコスト最適化ガイド

VPSとAPIの費用を最小限に抑えながら、高品質なサービスを維持するための実践的なガイド

## 📋 目次

- [コスト構造の理解](#コスト構造の理解)
- [VPS費用の最適化](#vps費用の最適化)
- [API費用の最適化](#api費用の最適化)
- [ストレージ費用の最適化](#ストレージ費用の最適化)
- [ネットワーク費用の最適化](#ネットワーク費用の最適化)
- [運用コストの削減](#運用コストの削減)
- [コスト監視](#コスト監視)

---

## コスト構造の理解

### 典型的な月額コスト

```
┌─────────────────────────────────────────┐
│ 月額コスト内訳（例）                     │
├─────────────────────────────────────────┤
│ VPS基本料金        ¥500 - ¥2,000       │
│ Anthropic API      ¥1,000 - ¥5,000     │
│ ストレージ追加     ¥0 - ¥500           │
│ 転送量超過         ¥0 - ¥1,000         │
│ バックアップ       ¥0 - ¥300           │
│ ドメイン           ¥100 - ¥200/年      │
├─────────────────────────────────────────┤
│ 合計              ¥1,600 - ¥9,000/月   │
└─────────────────────────────────────────┘
```

### コスト削減目標

- **短期目標**: 月額費用を30%削減
- **中期目標**: リソース効率を2倍に向上
- **長期目標**: 自動スケーリングで使用量に応じた最適化

---

## VPS費用の最適化

### 1. 適切なプラン選択

#### スペック別推奨用途

| スペック | 月額 | 推奨用途 | 同時ユーザー |
|---------|------|---------|------------|
| 1vCPU, 1GB RAM | ¥500-800 | テスト環境のみ | 1-2人 |
| 2vCPU, 2GB RAM | ¥800-1,200 | 個人利用 | 2-5人 |
| 2vCPU, 4GB RAM | ¥1,200-1,800 | 小規模チーム | 5-10人 |
| 4vCPU, 8GB RAM | ¥2,000-3,000 | 中規模運用 | 10-20人 |

#### プラン選択のポイント

```bash
# 現在のリソース使用率を確認
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemPerc}}"

# 推奨:
# - CPU平均使用率: 50-70%
# - メモリ平均使用率: 60-80%
# 常に80%以上 → アップグレード検討
# 常に30%以下 → ダウングレード検討
```

### 2. プロバイダー比較

#### 主要VPSプロバイダー比較（2vCPU, 4GB RAM）

| プロバイダー | 月額 | SSD | 転送量 | 特徴 |
|------------|-----|-----|--------|-----|
| ConoHa VPS | ¥1,180 | 100GB | 無制限 | 日本データセンター |
| さくらVPS | ¥1,738 | 50GB | 無制限 | 老舗、安定性高 |
| DigitalOcean | $18 | 80GB | 4TB/月 | グローバル、API充実 |
| Vultr | $18 | 80GB | 3TB/月 | 高速、多拠点 |
| AWS Lightsail | $20 | 80GB | 4TB/月 | AWS統合 |

#### 切り替え検討

```bash
# 年間コスト差（例）
ConoHa VPS:     ¥1,180 × 12 = ¥14,160/年
さくらVPS:      ¥1,738 × 12 = ¥20,856/年
差額:          ¥6,696/年

# 移行手順: docs/MIGRATION.md 参照
```

### 3. リザーブドインスタンス（長期契約割引）

```bash
# ConoHa VPS の場合
# 6ヶ月契約: 約5%割引
# 12ヶ月契約: 約10%割引

# 例: 2vCPU, 4GB RAM
時間課金: ¥1,180/月
12ヶ月契約: ¥1,062/月（¥12,744/年）
年間節約: ¥1,416
```

### 4. スナップショット費用の削減

```bash
# 不要なスナップショット削除
# ConoHa: ¥0.3/GB/月

# 例: 50GBスナップショット×3個
月額: 50GB × 3 × ¥0.3 = ¥45

# 削減策:
# - 古いスナップショット削除（30日以上）
# - 必要最小限のみ保持（最新2個のみ）
```

---

## API費用の最適化

### Anthropic API 課金モデル

```
Claude Sonnet 4.5:
- Input:  $3.00 / 1M tokens
- Output: $15.00 / 1M tokens

Claude Haiku 4.5:
- Input:  $0.80 / 1M tokens
- Output: $4.00 / 1M tokens
```

### 1. プロンプト最適化

#### ❌ 非効率なプロンプト

```python
# 悪い例: 毎回全コンテキストを送信
prompt = f"""
ユーザー履歴:
{全履歴（10,000文字）}

現在の質問: こんにちは

回答してください。
"""
# トークン数: 約3,000トークン
```

#### ✅ 効率的なプロンプト

```python
# 良い例: 必要な情報のみ
prompt = f"""
最近の会話:
{直近3回のみ（300文字）}

現在の質問: こんにちは

回答してください。
"""
# トークン数: 約200トークン（15分の1！）
```

**節約額**: 1,000回の会話で約$8 → 約$0.5（93%削減）

### 2. モデル選択の最適化

```python
# タスク別最適モデル

# 簡単なタスク → Haiku（コスト1/4）
簡単な質問応答 → Claude Haiku 4.5
データ抽出 → Claude Haiku 4.5
要約 → Claude Haiku 4.5

# 複雑なタスク → Sonnet
コード生成 → Claude Sonnet 4.5
複雑な推論 → Claude Sonnet 4.5
創造的作業 → Claude Sonnet 4.5

# 最も難しいタスク → Opus
研究・分析 → Claude Opus 4.5
```

**コスト比較**:
```
100万トークン処理（Input + Output）
Haiku:   $4.80
Sonnet:  $18.00
Opus:    $60.00

節約額: Sonnet → Haiku で $13.20/100万トークン
```

### 3. キャッシング活用

```python
# プロンプトキャッシング（近日実装予定）
# 繰り返し使用するコンテキストをキャッシュ

# 例: システムプロンプトをキャッシュ
system_prompt = """
あなたは親切なアシスタントです。
[長いガイドライン 5,000文字]
"""  # このシステムプロンプトをキャッシュ

# 2回目以降: キャッシュから取得（90%削減）
```

### 4. トークン数の監視

```bash
# N8Nワークフローでトークン使用量を記録

# PostgreSQLに記録
INSERT INTO token_usage (date, tokens, cost)
VALUES (NOW(), 1500, 0.045);

# 週次レポート
SELECT
  DATE_TRUNC('week', date) as week,
  SUM(tokens) as total_tokens,
  SUM(cost) as total_cost
FROM token_usage
GROUP BY week
ORDER BY week DESC;
```

### 5. レート制限の設定

```javascript
// N8Nワークフローで1日の上限設定

const DAILY_TOKEN_LIMIT = 100000;  // 1日10万トークン
const current_usage = await getTokenUsage(today);

if (current_usage > DAILY_TOKEN_LIMIT) {
  return {
    error: "Daily token limit exceeded",
    message: "明日まで待ってください"
  };
}
```

**節約額**: 予期しない大量利用を防止（月額$50-100の節約）

---

## ストレージ費用の最適化

### 1. ログローテーション

```bash
# /etc/logrotate.d/openclaw
/opt/vps-automation-openclaw/logs/*/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0640 root root
}

# ディスク削減: 約5-10GB/月
```

### 2. Dockerイメージの最適化

```bash
# 未使用イメージの削除
docker image prune -a

# ビルドキャッシュの削除
docker builder prune -a

# 削減: 10-20GB
```

### 3. バックアップの圧縮と保持期間

```bash
# 圧縮バックアップ（scripts/backup.sh）
tar -czf backup.tar.gz data/  # gzip圧縮

# 保持期間の設定
find /opt/backups/openclaw/ -mtime +30 -delete  # 30日以上削除

# オフサイトバックアップ（安価なストレージへ）
# AWS S3 Glacier: $0.004/GB/月（通常S3の1/10）
aws s3 sync /opt/backups/openclaw/ \
  s3://backup-bucket/openclaw/ \
  --storage-class GLACIER
```

**節約額**: 月額¥200-500

### 4. データベース最適化

```sql
-- 古いデータのアーカイブ
-- 90日以上古いチャット履歴を削除
DELETE FROM chat_history
WHERE timestamp < NOW() - INTERVAL '90 days';

-- VACUUM実行（ディスク領域回収）
VACUUM FULL;

-- 削減: 1-5GB
```

---

## ネットワーク費用の最適化

### 1. CDN活用（静的ファイル）

```nginx
# Nginxで画像を圧縮
location ~* \.(jpg|jpeg|png|gif)$ {
    gzip_static on;
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# または、Cloudflare（無料プラン）を使用
# - 画像最適化
# - キャッシング
# - DDoS保護
```

**節約額**: 転送量30-50%削減

### 2. アクセス制限

```bash
# 不要なボットをブロック
# /etc/nginx/nginx.conf

if ($http_user_agent ~* (bot|crawler|spider)) {
    return 403;
}

# 地域制限（必要な場合）
# GeoIP2を使用して特定地域のみ許可
```

### 3. Gzip圧縮

```nginx
# docker/nginx/nginx.conf
gzip on;
gzip_vary on;
gzip_types text/plain text/css application/json application/javascript;
gzip_comp_level 6;

# 転送量: 60-70%削減
```

---

## 運用コストの削減

### 1. 自動化による人件費削減

```bash
# 手動運用（週5時間）vs 自動化（週0.5時間）
時給換算 ¥2,000 の場合:
手動: 5時間 × ¥2,000 × 4週 = ¥40,000/月
自動化: 0.5時間 × ¥2,000 × 4週 = ¥4,000/月
節約: ¥36,000/月
```

#### 自動化すべきタスク

- [x] バックアップ（Cron）
- [x] セキュリティスキャン（Cron）
- [x] ヘルスチェック（N8Nワークフロー）
- [x] リソース監視（Prometheus + Grafana）
- [x] アラート通知（Alertmanager）

### 2. 監視コストの最適化

```yaml
# Prometheus データ保持期間を調整
# docker/prometheus/prometheus.yml

storage:
  tsdb:
    retention.time: 15d  # 30d → 15d に短縮

# ディスク削減: 5-10GB
```

### 3. 開発環境との分離

```bash
# 本番環境: VPS
docker compose -f docker-compose.production.yml up -d

# 開発環境: ローカル（無料）
docker compose -f docker-compose.dev.yml up -d

# VPS費用: ¥1,200/月節約
```

---

## コスト監視

### 1. リソース使用量ダッシュボード

```bash
# Grafanaで作成
# - CPU使用率（時系列）
# - メモリ使用率
# - ディスク使用量
# - ネットワーク転送量

# 月次レポート自動生成
# N8Nワークフローで月初に前月のレポート送信
```

### 2. APIコスト追跡

```sql
-- PostgreSQLでトークン使用量を記録

CREATE TABLE api_costs (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  service VARCHAR(50),
  tokens_input BIGINT,
  tokens_output BIGINT,
  cost_usd DECIMAL(10,4),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 月次集計
SELECT
  DATE_TRUNC('month', date) as month,
  SUM(cost_usd) as total_cost
FROM api_costs
WHERE service = 'anthropic'
GROUP BY month
ORDER BY month DESC;
```

### 3. アラート設定

```yaml
# docker/prometheus/alerts.yml

- alert: HighMonthlyCost
  expr: monthly_cost_usd > 100
  for: 1h
  annotations:
    summary: "月額コストが予算を超えています"
    description: "現在の月額コスト: {{ $value }}ドル"
```

### 4. 予算管理

```bash
# 月額予算: ¥5,000の場合

コスト内訳:
┌────────────────────────────────┐
│ VPS:           ¥1,200 (24%)    │
│ API:           ¥3,000 (60%)    │
│ ストレージ:    ¥300 (6%)       │
│ その他:        ¥500 (10%)      │
├────────────────────────────────┤
│ 合計:          ¥5,000 (100%)   │
└────────────────────────────────┘

週次チェック:
- 現在の累計費用
- 月末予測
- 予算超過リスク
```

---

## 実践的な節約例

### ケーススタディ1: 個人利用

**Before**:
```
VPS: 4vCPU, 8GB RAM     ¥2,500/月
API: Sonnet 4.5のみ     ¥5,000/月
ストレージ: 無制限      ¥500/月
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
合計:                   ¥8,000/月
```

**After**:
```
VPS: 2vCPU, 4GB RAM     ¥1,200/月（52%削減）
API: Haiku + Sonnet混合  ¥2,000/月（60%削減）
ストレージ: 30日保持    ¥200/月（60%削減）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
合計:                   ¥3,400/月（57%削減）

年間節約: ¥55,200
```

### ケーススタディ2: 小規模チーム

**Before**:
```
VPS: 4vCPU, 8GB RAM     ¥2,500/月
API: Sonnet 4.5大量使用  ¥10,000/月
バックアップ: 複数      ¥800/月
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
合計:                   ¥13,300/月
```

**After**:
```
VPS: 4vCPU, 8GB RAM（維持）           ¥2,500/月
API: モデル使い分け + キャッシング    ¥4,000/月（60%削減）
バックアップ: Glacier移行            ¥100/月（87%削減）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
合計:                                ¥6,600/月（50%削減）

年間節約: ¥80,400
```

---

## クイックチェックリスト

### 月次最適化タスク

- [ ] リソース使用率を確認（CPU, メモリ, ディスク）
- [ ] API使用量とコストを確認
- [ ] 不要なスナップショット削除
- [ ] ログファイルのクリーンアップ
- [ ] 古いバックアップの削除
- [ ] プラン変更の検討

### 四半期最適化タスク

- [ ] VPSプロバイダーの料金比較
- [ ] APIモデル使用率の分析
- [ ] プロンプト効率化の検討
- [ ] 予算vs実績の分析

---

## ツールとリソース

### コスト計算ツール

```bash
# scripts/cost_calculator.sh（作成推奨）

#!/bin/bash

# VPS費用
VPS_MONTHLY=1200

# API使用量（トークン/月）
INPUT_TOKENS=1000000
OUTPUT_TOKENS=500000

# APIコスト計算（Sonnet 4.5）
INPUT_COST=$(echo "$INPUT_TOKENS / 1000000 * 3" | bc -l)
OUTPUT_COST=$(echo "$OUTPUT_TOKENS / 1000000 * 15" | bc -l)
API_COST=$(echo "$INPUT_COST + $OUTPUT_COST" | bc -l)

# 合計（円換算、1ドル=150円）
TOTAL_USD=$(echo "$API_COST" | bc -l)
TOTAL_JPY=$(echo "$VPS_MONTHLY + $TOTAL_USD * 150" | bc -l)

echo "月額費用概算: ¥${TOTAL_JPY}"
```

---

## まとめ

### コスト最適化の優先順位

1. **高優先度**（すぐに実施）
   - APIモデルの使い分け
   - プロンプト最適化
   - 不要なリソース削除

2. **中優先度**（1ヶ月以内）
   - VPSプラン見直し
   - バックアップ戦略最適化
   - 監視体制の構築

3. **低優先度**（長期的）
   - プロバイダー切り替え
   - アーキテクチャ最適化

### 期待される効果

```
最適化前: ¥8,000-13,000/月
最適化後: ¥3,000-7,000/月
削減率: 40-60%
年間節約: ¥60,000-72,000
```

---

## 参考資料

- [PERFORMANCE.md](../PERFORMANCE.md) - パフォーマンス最適化
- [OPERATIONS_GUIDE.md](../OPERATIONS_GUIDE.md) - 運用マニュアル
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) - バックアップ戦略

---

<div align="center">

**💰 賢くコストを削減して、持続可能な運用を実現しましょう！ 📊**

</div>
