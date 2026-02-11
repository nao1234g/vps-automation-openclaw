# 🚀 マルチエージェントシステム クイックスタート

**Claude Opus 4.6 + Codex + 7人のAI従業員 を5分で起動**

---

## ⚡ 最速セットアップ（5分）

### 1. 環境変数設定（2分）

```bash
# .envファイル作成
cp .env.example .env

# 必須のAPI Keyを設定
nano .env
```

**最低限必要なキー（3つ）：**
```bash
ANTHROPIC_API_KEY=sk-ant-xxxx    # Claude (Jarvis, Alice, Guard)
OPENAI_API_KEY=sk-proj-xxxx      # CodeX
GOOGLE_AI_API_KEY=xxxx            # Pixel, Scout
```

**強く推奨（Web検索用）：**
```bash
FIRECRAWL_API_KEY=fc-xxxx         # Alice用Web検索
GITHUB_TOKEN=ghp_xxxx              # CodeX用Git操作
```

### 2. マルチエージェント設定を有効化（1分）

```bash
# 既存のopenclaw.jsonをバックアップ
cp config/openclaw/openclaw.json config/openclaw/openclaw.json.backup

# マルチエージェント設定を適用
cp config/openclaw/openclaw-multiagent.json config/openclaw/openclaw.json
```

### 3. 起動（2分）

```bash
# ビルド＆起動
docker compose up -d

# ログ確認
docker compose logs -f openclaw

# 健全性チェック
curl http://localhost:3000/health
```

**✅ 成功時の出力例：**
```json
{
  "status": "healthy",
  "agents": {
    "jarvis-cso": "active",
    "alice-researcher": "active",
    "codex-developer": "active",
    "pixel-designer": "active",
    "luna-writer": "active",
    "scout-data": "active",
    "guard-security": "active"
  }
}
```

---

## 🎮 最初の命令（動作確認）

### テスト1: シンプルな質問（Jarvisに聞く）

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Authorization: Bearer ${OPENCLAW_GATEWAY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "今日の天気を教えて",
    "agent": "jarvis-cso"
  }'
```

**期待される動作：** Jarvisが「天気情報の取得はAliceに任せます」と判断

### テスト2: リサーチタスク（Aliceに直接指示）

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Authorization: Bearer ${OPENCLAW_GATEWAY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "OpenAIの最新ニュースを3件教えて",
    "agent": "alice-researcher"
  }'
```

**期待される動作：** Web検索して事実のみを報告（2秒以内）

### テスト3: コーディングタスク（CodeXに指示）

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Authorization: Bearer ${OPENCLAW_GATEWAY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "PythonでFizzBuzzを実装して",
    "agent": "codex-developer"
  }'
```

**期待される動作：** クリーンなコード＋説明を返す

---

## 📊 コスト監視（重要！）

```bash
# 今日の使用状況
./scripts/cost_monitor_multiagent.sh --period 1d

# 特定エージェントのみ
./scripts/cost_monitor_multiagent.sh --agent jarvis-cso --period 7d

# CSV出力
./scripts/cost_monitor_multiagent.sh --export /tmp/costs.csv
```

**出力例：**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Multi-Agent Cost Report - Period: 1d
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Agent ID             Tasks  Total Cost    Success %
───────────────────────────────────────────────────
alice-researcher       45      $0.09        98.0%
codex-developer        12      $0.60        100.0%
jarvis-cso              8      $0.16        100.0%
luna-writer             5      $0.15        100.0%

[SUMMARY]
  Total Tasks:  70
  Total Cost:   $1.00
  Period:       1d
```

---

## 🤖 n8n自動化ワークフロー（オプション）

### n8nにワークフローをインポート

1. **n8nにログイン:** http://localhost:5678
2. **Import → From File**
3. ファイル選択: `n8n-workflows/multi-agent-daily-report.json`
4. **Activate**

**このワークフローの動作：**
- **毎朝8:00AM自動実行**
- Alice → ニュース収集（$0.002）
- Luna → 記事執筆（$0.05）
- Jarvis → 品質チェック（$0.02）
- PostgreSQLに保存
- Telegram通知

**コスト:** 1日$0.072（月間$2.16）

---

## 💡 実践例：「ブログ記事を自動生成」

### ユーザー入力
```bash
curl -X POST http://localhost:3000/api/orchestrate \
  -H "Authorization: Bearer ${OPENCLAW_GATEWAY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "今日のAI業界ニュースをまとめてブログ記事にして",
    "coordinator": "jarvis-cso",
    "autoRoute": true
  }'
```

### Jarvisの判断（自動）
```json
{
  "plan": {
    "step1": {
      "agent": "alice-researcher",
      "task": "AIニュース検索（今日）",
      "estimatedCost": "$0.003"
    },
    "step2": {
      "agent": "luna-writer",
      "task": "ブログ記事執筆（800字）",
      "estimatedCost": "$0.05",
      "dependencies": ["step1"]
    },
    "step3": {
      "agent": "jarvis-cso",
      "task": "最終レビュー",
      "estimatedCost": "$0.02",
      "dependencies": ["step2"]
    }
  },
  "totalEstimatedCost": "$0.073",
  "estimatedTime": "15分"
}
```

### 実行結果
```json
{
  "status": "completed",
  "result": {
    "title": "2026年2月11日のAI業界トップニュース",
    "content": "...(800字の記事)...",
    "sources": [
      {"title": "OpenAI GPT-5発表", "url": "..."},
      {"title": "Anthropic Claude 4リリース", "url": "..."}
    ]
  },
  "execution": {
    "totalTime": "12分23秒",
    "totalCost": "$0.068",
    "agentsUsed": ["alice-researcher", "luna-writer", "jarvis-cso"]
  }
}
```

**もしOpus 1人でやったら：** $0.25（約4倍高い）

---

## 🛠️ トラブルシューティング

### エージェントが起動しない

```bash
# ログ確認
docker compose logs openclaw | grep -i error

# 設定検証
./scripts/validate_env.sh

# 再起動
docker compose restart openclaw
```

### API Keyエラー

```bash
# 環境変数確認
docker compose exec openclaw env | grep API_KEY

# .envを再読み込み
docker compose down
docker compose up -d
```

### コストが予想より高い

```bash
# エージェント使用率確認
./scripts/cost_monitor_multiagent.sh --period 1d

# Jarvisが全てやってる場合
# → config/openclaw/openclaw-multiagent.json の 
#    "enforceRouting": true を確認
```

### Firecrawl API（Web検索）が動かない

```bash
# Firecrawl無しでも動作します（ただし検索精度は低下）
# 代替: Google Custom Search APIを設定

# .envに追加
GOOGLE_CSE_API_KEY=xxx
GOOGLE_CSE_CX=xxx
```

---

## 📈 次のステップ

### Level 2: カスタムスキル追加
`skills/` フォルダにJavaScriptファイルを追加すると、全エージェントから呼び出し可能になります。

例: `skills/slack-notifier.js`

```javascript
module.exports = {
  name: 'slack-notifier',
  description: 'Send notifications to Slack',
  
  async notify(context, message) {
    // Slack Webhook実装
    // ...
  }
};
```

### Level 3: プロンプト最適化
`config/openclaw/personas/*.md` を編集してエージェントの性格をカスタマイズ。

例: Jarvisをより攻撃的な戦略家にする
```markdown
# config/openclaw/personas/jarvis-cso.md

判断基準：
1. **速度優先**：迷ったら並列実行
2. **リスクテイク**：不確実性を恐れない
3. **コスト二の次**：品質が最優先
```

### Level 4: 自動スケーリング
タスク量に応じて、エージェントのインスタンス数を動的に増やす。

```yaml
# docker-compose.scale.yml
services:
  alice-researcher:
    image: openclaw:latest
    deploy:
      replicas: 3  # Aliceを3人に増やす
```

---

## 🎯 想定コスト（月間）

| 使用パターン | 月間コスト | 人間換算（時給$30） |
|-------------|-----------|-------------------|
| **軽量（個人ブログ）** | $10-30 | 0.3-1時間/月 |
| **中規模（スタートアップ）** | $100-300 | 3-10時間/月 |
| **大規模（企業）** | $500-1500 | 17-50時間/月 |

**ROI計算例：**
- 人間ライター: 記事1本$50 × 20本/月 = **$1,000**
- AI（Luna + Alice）: 記事1本$0.07 × 20本/月 = **$1.40**
- **節約額: $998.60/月（99.86%削減）**

---

## 📚 関連ドキュメント

- **詳細設計:** [docs/MULTI_AGENT_SETUP.md](./MULTI_AGENT_SETUP.md)
- **Personas設定:** `config/openclaw/personas/*.md`
- **n8nワークフロー:** `n8n-workflows/multi-agent-*.json`
- **コスト最適化:** [docs/COST_OPTIMIZATION.md](./COST_OPTIMIZATION.md)

---

## ✅ チェックリスト

- [ ] .env設定完了（最低3つのAPI Key）
- [ ] マルチエージェント設定適用
- [ ] Docker Compose起動成功
- [ ] ヘルスチェックOK
- [ ] テスト命令実行成功
- [ ] コスト監視ダッシュボード確認
- [ ] n8nワークフローインポート（オプション）

**全てチェックが入ったら、あなたは100倍エンジニアです。おめでとうございます🎉**

---

**サポート:** 問題が発生したら [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) を確認してください。
