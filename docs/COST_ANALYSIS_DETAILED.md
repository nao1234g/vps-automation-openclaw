# マルチエージェントシステム コスト分析
# 2026年2月版 - 詳細料金表と最適化プラン

## 📊 各モデルの料金表（最新）

### 10,000トークンあたりのコスト

| モデル | Input (10K tokens) | Output (10K tokens) | 用途 |
|--------|-------------------|---------------------|------|
| **Claude Opus 4** | $0.15 | $0.75 | 戦略・複雑推論 |
| **Claude Sonnet 4** | $0.03 | $0.15 | バランス型・執筆 |
| **Claude Haiku 4** | $0.0025 | $0.0125 | リサーチ・高速処理 |
| **GPT-4o** | $0.025 | $0.10 | コーディング |
| **Gemini 1.5 Pro** | $0.0125 | $0.05 | デザイン・画像処理 |
| **Gemini 2.0 Flash** | $0.00075 | $0.003 | 軽量処理・高速 |

### 1Mトークンあたりのコスト（参考）

| モデル | Input | Output | 合計（想定3:1比率） |
|--------|-------|--------|-------------------|
| Claude Opus 4 | $15 | $75 | **$33.75** |
| Claude Sonnet 4 | $3 | $15 | **$6.75** |
| Claude Haiku 4 | $0.25 | $1.25 | **$0.56** |
| GPT-4o | $2.5 | $10 | **$5.63** |
| Gemini 1.5 Pro | $1.25 | $5 | **$2.81** |
| Gemini 2.0 Flash | $0.075 | $0.30 | **$0.17** |

---

## 💰 24時間365日稼働時のコスト見積もり

### 前提条件

**使用パターン（現実的な見積もり）**
- **軽量自動化**: n8nで日次レポート自動生成、監視タスク
- **中程度の対話**: 1日10-20回のチャット（開発作業、質問回答）
- **重度の作業**: コード生成、リサーチ、記事執筆

#### パターン1: 軽量使用（個人開発者）

**想定タスク:**
- 日次自動レポート: 1回/日（Alice + Luna + Jarvis）
- チャット: 10回/日（平均5,000トークン/回）
- コード生成: 2回/日（CodeX、平均8,000トークン/回）

**月間トークン数:**
```
日次レポート: 20,000 tokens × 30日 = 600,000 tokens
チャット: 50,000 tokens × 30日 = 1,500,000 tokens
コード生成: 16,000 tokens × 30日 = 480,000 tokens
──────────────────────────────────────────────────
合計: 約2.58M tokens/月
```

**エージェント別内訳:**
```
Jarvis (Opus 4):     300K tokens  → $10.13
Alice (Haiku 4):     400K tokens  → $0.22
CodeX (GPT-4o):      480K tokens  → $2.70
Luna (Sonnet 4):     600K tokens  → $4.05
Scout (Flash):       400K tokens  → $0.07
Pixel (Gemini Pro):  200K tokens  → $0.56
Guard (Haiku 4):     200K tokens  → $0.11
──────────────────────────────────────────────────
月額合計: $17.84（約2,676円）
```

#### パターン2: 中規模使用（小規模チーム/スタートアップ）

**想定タスク:**
- 自動化ワークフロー: 3回/日
- チャット: 30回/日
- コード生成: 10回/日
- 記事執筆: 5回/日

**月間トークン数: 約8M tokens**

**月額合計: $55-75（約8,250-11,250円）**

#### パターン3: 重度使用（フル活用）

**想定タスク:**
- チャット: 100回/日（開発作業メイン）
- コード生成: 30回/日
- 包括的自動化

**月間トークン数: 約25M tokens**

**月額合計: $180-220（約27,000-33,000円）**

---

## 🔌 API接続方法とアーキテクチャ

### 方式1: 直接API接続（現在の実装）

```
OpenClaw → Anthropic API (Claude)
         → OpenAI API (GPT-4o)
         → Google AI API (Gemini)
```

**メリット:**
- ✅ 最速（レイテンシ最小）
- ✅ 公式サポート
- ✅ 最新モデルに即座にアクセス

**デメリット:**
- ❌ 3つのAPIキー管理が必要
- ❌ 請求がバラバラ

### 方式2: LiteLLM統合（推奨）

```
OpenClaw → LiteLLM Proxy → Anthropic
                         → OpenAI
                         → Google AI
                         → OpenRouter (フォールバック)
```

**メリット:**
- ✅ 統一インターフェース
- ✅ コスト追跡機能
- ✅ レート制限管理
- ✅ フォールバック設定可能

**デメリット:**
- ⚠️ プロキシのホスティング必要（Docker 1コンテナ追加）

### 方式3: OpenRouter統合

```
OpenClaw → OpenRouter API → 100+ モデル
```

**メリット:**
- ✅ 1つのAPIキーで全モデルアクセス
- ✅ 統一請求
- ✅ コスト追跡ダッシュボード

**デメリット:**
- ⚠️ 若干の価格上乗せ（5-10%）
- ⚠️ 公式APIより遅延が大きい可能性

**OpenRouter料金例:**
```
Claude Opus 4:    $15-16.5/1M  (公式比 +10%)
Claude Sonnet 4:  $3-3.3/1M    (公式比 +10%)
GPT-4o:           $2.5-2.75/1M (公式比 +10%)
```

---

## 💳 現在の契約状況との統合

### あなたの現在の契約

1. **Claude Code (Anthropic)**: $200/月 → **$100に削減希望**
2. **Gemini**: 契約済み（Pro/Advancedプラン？）
3. **OpenAI**: $20/月（ChatGPT Plus）

### ⚠️ 重要な注意点

**ChatGPT Plus ($20/月) ≠ API ($0.025/10K tokens)**

| プラン | 何ができる | API連携 | コスト |
|--------|----------|---------|--------|
| ChatGPT Plus | Webチャット、GPT-4o使い放題 | ❌ 不可 | $20/月定額 |
| OpenAI API | プログラム連携、自動化 | ✅ 可能 | 従量課金 |

**つまり：** OpenClawでGPT-4oを使うには、別途**OpenAI API**の契約が必要です。

### 🎯 最適化プラン：3つの提案

---

## プランA: コスト最優先（月額 $50-70 / 約7,500-10,500円）

### 構成
```yaml
Jarvis (CSO):      Claude Sonnet 4  # Opusから格下げ
Alice (Research):  Gemini Flash     # 既存契約活用
CodeX (Dev):       GPT-4o mini      # API新規・軽量版
Luna (Writer):     Claude Haiku 4   # 安価モデル
Scout (Data):      Gemini Flash     # 既存契約
Pixel (Design):    Gemini Pro       # 既存契約
Guard (Security):  Local Llama 3.1  # 完全無料（ローカル実行）
```

### 必要なAPI契約
- ✅ Anthropic API: $20-30/月（Sonnet + Haiku）
- ✅ Google AI: **既存契約利用**（追加コストなし or 微増）
- ✅ OpenAI API: $15-25/月（新規）

### メリット
- 💰 Claude Code $200 → API $30（**$170削減**）
- 💰 総コスト: 既存$220 → 新$65（**$155削減/月**）
- ⚡ Gemini活用で速度も維持

### デメリット
- ⚠️ Jarvisの判断力がOpusより劣る（Sonnetでも十分実用的）

---

## プランB: バランス型（月額 $90-120 / 約13,500-18,000円）

### 構成
```yaml
Jarvis (CSO):      Claude Opus 4    # 最高性能維持
Alice (Research):  Perplexity API   # リサーチ特化
CodeX (Dev):       GPT-4o           # フル機能
Luna (Writer):     Claude Sonnet 4  # バランス型
Scout (Data):      Gemini Flash     # 既存契約
Pixel (Design):    Gemini Pro       # 既存契約
Guard (Security):  Claude Haiku 4   # 高速チェック
```

### 必要なAPI契約
- ✅ Anthropic API: $40-60/月（Opus少量 + Sonnet/Haiku）
- ✅ Google AI: **既存契約**
- ✅ OpenAI API: $30-40/月
- ✅ Perplexity API: $20/月（Pro契約でAPI付属）

### メリット
- ⚡ Opus維持で最高の判断力
- 🔍 Perplexity統合でリサーチ精度向上
- 💰 Claude Code削減効果: $200 → $60（**$140削減**）

### デメリット
- 💰 コスト削減効果はプランAより小さい

---

## プランC: ハイブリッド（月額 $70-90 / 約10,500-13,500円）**←推奨**

### 構成
```yaml
Jarvis (CSO):      Claude Opus 4        # 戦略のみ使用（使用量制限）
Alice (Research):  Gemini Flash + Perplexity  # コスパ最強
CodeX (Dev):       GPT-4o               # コーディング特化
Luna (Writer):     Claude Sonnet 4      # 品質重視
Scout (Data):      Gemini Flash         # 既存契約
Pixel (Design):    Gemini Pro           # 既存契約
Guard (Security):  Claude Haiku 4       # 高速
```

### コスト管理ルール（重要！）
```javascript
// config/openclaw/cost-limits.json
{
  "monthlyBudget": 90,
  "agentLimits": {
    "jarvis-cso": {
      "maxCostPerDay": 1.5,  // $45/月
      "maxTokensPerRequest": 8000
    },
    "codex-developer": {
      "maxCostPerDay": 1.0   // $30/月
    }
  },
  "fallbackRules": {
    "when": "budgetExceeded",
    "action": "downgradeToSonnet"  // Opus → Sonnet自動切替
  }
}
```

### 必要なAPI契約
1. **Anthropic API**: $30-45/月
   - Opus: 制限付き使用（本当に重要な判断のみ）
   - Sonnet/Haiku: メイン使用
   
2. **Google AI**: **既存契約継続**
   - Gemini Pro: デザイン用
   - Flash: データ処理・リサーチ補助
   
3. **OpenAI API**: $25-35/月
   - GPT-4o: コーディング専用
   
4. **Perplexity Pro**: $20/月（オプション）
   - API付属でリサーチ強化

### 既存契約の扱い

| 現在 | 新プラン | 変更 |
|------|----------|------|
| Claude Code $200 | ❌ 解約 | Anthropic APIへ |
| Gemini契約 | ✅ 継続 | そのまま活用 |
| OpenAI Plus $20 | ⚠️ 検討 | API契約追加 or 移行 |

**OpenAI戦略2択:**
- **A**: Plus継続＋API追加 = $20 + $30 = $50/月
- **B**: Plus解約、API統合 = $35/月（**$15削減**）

### 総コスト比較

```
【現在】
Claude Code:   $200
Gemini:        $20-30（想定）
OpenAI Plus:   $20
─────────────────────
合計:          $240-250/月

【プランC】
Anthropic API: $40
Google AI:     $25（想定継続）
OpenAI API:    $35
─────────────────────
合計:          $100/月

削減額: $140-150/月（約21,000-22,500円）
```

---

## 🔧 実装手順（プランC採用時）

### Step 1: API契約（優先順位順）

```bash
# 1. Anthropic API（最優先）
# https://console.anthropic.com/
# → Usage-based pricing選択
# → $10クレジットチャージ（まず試す）

# 2. OpenAI API（APIキー取得）
# https://platform.openai.com/api-keys
# → 新規キー作成
# → Usage limits設定: $50/月

# 3. Perplexity Pro（オプション）
# https://www.perplexity.ai/pro
# → $20/月契約でAPI付属
```

### Step 2: コスト制限設定

```bash
# .envに追加
cat >> .env << 'EOF'

# === Cost Management ===
MONTHLY_BUDGET_USD=90
ENABLE_COST_ALERTS=true
ALERT_THRESHOLD_PERCENT=80

# Opus使用制限（1日$1.50 = 月$45）
JARVIS_MAX_COST_PER_DAY=1.5
JARVIS_FALLBACK_MODEL=anthropic/claude-sonnet-4

# 通知先
COST_ALERT_TELEGRAM=true
COST_ALERT_EMAIL=your-email@example.com
EOF
```

### Step 3: OpenClawコスト監視強化

```bash
# コスト監視cronジョブ
echo "0 * * * * /app/scripts/cost_monitor_multiagent.sh --period 1h --alert-if-high" >> /etc/crontab

# 日次レポート
echo "0 9 * * * /app/scripts/cost_monitor_multiagent.sh --period 1d --export /tmp/daily-cost.csv && curl -X POST -H 'Content-Type: application/json' -d @/tmp/daily-cost.csv $TELEGRAM_WEBHOOK" >> /etc/crontab
```

### Step 4: n8nコストダッシュボード

`n8n-workflows/cost-dashboard.json`:

```json
{
  "nodes": [
    {
      "name": "Daily Cost Check",
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": {
          "interval": [{"field": "cronExpression", "expression": "0 9 * * *"}]
        }
      }
    },
    {
      "name": "Query PostgreSQL",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "query": "SELECT agent_id, SUM(cost_usd) as daily_cost FROM agent_tasks WHERE created_at > NOW() - INTERVAL '1 day' GROUP BY agent_id"
      }
    },
    {
      "name": "Check Budget",
      "type": "n8n-nodes-base.code",
      "parameters": {
        "jsCode": "const budget = 3; // $3/日 = $90/月\nconst total = $input.all().reduce((sum, item) => sum + parseFloat(item.json.daily_cost), 0);\n\nif (total > budget) {\n  return {json: {alert: true, total: total, budget: budget, message: `⚠️ 予算超過！ $${total.toFixed(2)} / $${budget}`}};\n}\nreturn {json: {alert: false, total: total}};"
      }
    },
    {
      "name": "Send Telegram Alert",
      "type": "n8n-nodes-base.telegram",
      "parameters": {
        "text": "={{$json.message}}"
      }
    }
  ]
}
```

---

## 📱 「アンチグラビティ」について

「アンチグラビティ」について：私の知識ベースには該当するサービスがありません。もしかして以下のいずれかを指していますか？

1. **OpenRouter** ([openrouter.ai](https://openrouter.ai))
   - 100+モデルへの統一API
   - Claude Opusも利用可能
   
2. **LiteLLM** (オープンソース)
   - セルフホスト型プロキシ
   - 全モデル対応

3. **Together AI** ([together.ai](https://www.together.ai))
   - オープンソースモデル中心

4. **Anthropic Partner経由**
   - AWS Bedrock
   - Google Vertex AI

もし具体的なサービス名やURLを教えていただければ、そのサービス経由でのコスト試算も可能です。

---

## ✅ 最終推奨プラン

### 【推奨】プランC: ハイブリッド型

**理由:**
1. ✅ コスト削減: $240 → $100（**58%削減**）
2. ✅ Opus維持: 本当に必要な判断のみ使用
3. ✅ 既存契約活用: Gemini無駄なし
4. ✅ 実用性: 開発に十分なパフォーマンス

**月額内訳（円換算 1ドル=150円）:**
```
Anthropic API: $40   (6,000円)
Google AI:     $25   (3,750円)
OpenAI API:    $35   (5,250円)
────────────────────────────
合計:          $100  (15,000円)

現在比: -$140 (-21,000円)
```

**次のアクション:**
1. まずAnthropicとOpenAI APIを少額で試す（$10ずつ）
2. 1週間運用してコスト監視
3. 予算内なら本格運用開始
4. Claude Code解約（$200削減）

実装を始めますか？それとも、特定のサービス（「アンチグラビティ」など）について追加情報が必要ですか？
