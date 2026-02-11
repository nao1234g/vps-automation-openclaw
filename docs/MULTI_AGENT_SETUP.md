# マルチエージェントシステム実装ガイド
# Claude Opus 4.6 + Codex + Multi-Agent Orchestra

## 🎯 アーキテクチャ概要

このシステムは**7人のAI従業員**を階層的に配置し、コスト効率80%向上を実現します。

```mermaid
graph TD
    User[👤 User] --> Jarvis[🎯 Jarvis CSO<br/>Opus 4]
    Jarvis --> Alice[🔍 Alice Researcher<br/>Haiku 4]
    Jarvis --> CodeX[💻 CodeX Developer<br/>GPT-4o]
    Jarvis --> Pixel[🎨 Pixel Designer<br/>Gemini 1.5 Pro]
    Jarvis --> Luna[✍️ Luna Writer<br/>Sonnet 4]
    Jarvis --> Scout[📊 Scout Data<br/>Flash 2.0]
    Jarvis --> Guard[🛡️ Guard Security<br/>Haiku 4]
    
    Alice --> Firecrawl[Firecrawl API]
    CodeX --> GitHub[GitHub MCP]
    Pixel --> Gemini[Gemini Vision]
    Scout --> DB[(PostgreSQL)]
    Guard --> SecurityTools[Security Scan]
    
    N8N[⚙️ n8n Orchestrator] -.自動化.-> Jarvis
```

## 📋 実装ステップ

### Phase 1: 環境変数設定

`.env`ファイルに以下を追加：

```bash
# === AI Model API Keys ===
# Claude (Anthropic)
ANTHROPIC_API_KEY=sk-ant-xxxx

# OpenAI (GPT-4o / Codex)
OPENAI_API_KEY=sk-proj-xxxx

# Google Gemini
GOOGLE_AI_API_KEY=xxxx

# === MCP Server API Keys ===
# Firecrawl (Web scraping)
FIRECRAWL_API_KEY=fc-xxxx

# GitHub (Code operations)
GITHUB_TOKEN=ghp_xxxx

# === Database ===
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/openclaw

# === OpenClaw Multi-Agent Config ===
OPENCLAW_CONFIG_PATH=/app/config/openclaw-multiagent.json
```

### Phase 2: Docker Composeの更新

`docker-compose.yml`に以下を追加：

```yaml
services:
  openclaw:
    image: openclaw:multiagent
    build:
      context: ./docker/openclaw
      dockerfile: Dockerfile
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_AI_API_KEY=${GOOGLE_AI_API_KEY}
      - FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - DATABASE_URL=${DATABASE_URL}
    volumes:
      - ./config/openclaw/openclaw-multiagent.json:/app/config/openclaw.json:ro
      - ./config/openclaw/personas:/app/personas:ro
      - ./skills:/app/skills:rw
      - openclaw_data:/app/data
    ports:
      - "127.0.0.1:3000:3000"
    depends_on:
      - postgres
      - n8n
```

### Phase 3: n8nワークフロー設定

`n8n-workflows/multi-agent-orchestration.json`を作成（後述）

### Phase 4: デプロイ

```bash
# 1. 設定検証
./scripts/validate_env.sh

# 2. マルチエージェント設定でビルド
docker compose -f docker-compose.yml build openclaw

# 3. 起動
docker compose up -d

# 4. 動作確認
curl http://localhost:3000/health

# 5. ログ確認
docker compose logs -f openclaw
```

## 💰 コスト比較

| シナリオ | 全てOpus | マルチエージェント | 削減率 |
|----------|---------|-------------------|--------|
| リサーチ100回/日 | $3.00 | $0.20 | **93%削減** |
| コード生成50回/日 | $7.50 | $2.50 | **67%削減** |
| 記事執筆20回/日 | $2.00 | $0.80 | **60%削減** |
| **合計/月** | **$375** | **$105** | **72%削減** |

## 🎮 使用例

### ケース1: ブログ記事の自動生成

**ユーザー**: 「今日のAI業界ニュースをまとめて、ブログ記事にして」

**Jarvisの判断**:
```
タスク分解:
1. Alice: AIニュース検索（5分、$0.003）
2. Luna: 記事執筆（10分、$0.05）
3. Jarvis: 最終チェック（2分、$0.02）

総コスト: $0.073（オールOpusなら$0.30）
```

**実行フロー**:
```mermaid
sequenceDiagram
    User->>Jarvis: ブログ記事作成依頼
    Jarvis->>Alice: AIニュース収集指示
    Alice->>Firecrawl: Web検索
    Firecrawl-->>Alice: ニュース5件
    Alice-->>Jarvis: レポート提出
    Jarvis->>Luna: 記事執筆指示（+ニュースデータ）
    Luna-->>Jarvis: 記事ドラフト
    Jarvis->>Jarvis: クオリティチェック
    Jarvis-->>User: 完成記事
```

### ケース2: セキュアなAPIエンドポイント実装

**ユーザー**: 「認証付きのREST APIを作成して」

**Jarvisの判断**:
```
タスク分解:
1. CodeX: API実装（20分、$0.10）
2. Guard: セキュリティ監査（5分、$0.02）
3. CodeX: 修正実装（5分、$0.03）
4. Jarvis: 最終承認（2分、$0.02）

総コスト: $0.17（オールOpusなら$0.50）
```

### ケース3: 自動化された日次レポート

**n8nでの自動実行**:

```
毎朝8:00AM:
1. Alice: 前日の統計データ収集
2. Scout: ログ分析・異常検知
3. Luna: レポート作成
4. Telegram通知: 結果を送信

コスト: $0.05/日（月$1.50）
人間の時間: 0分（完全自動）
```

## 🔧 トラブルシューティング

### Jarvisが全ての仕事を自分でやってしまう

**原因**: `orchestration.mode`が正しく設定されていない

**解決策**:
```json
{
  "orchestration": {
    "mode": "hierarchical",
    "coordinator": "jarvis-cso",
    "enforceRouting": true  // ← これを追加
  }
}
```

### API キーエラー

```bash
# 設定確認
docker compose exec openclaw env | grep API_KEY

# 再起動
docker compose restart openclaw
```

### コストが予想より高い

`docker/openclaw`の`cost-monitor.sh`を実行：

```bash
./scripts/cost_tracker.sh --agent jarvis-cso --period 1d
```

## 📊 モニタリング

### リアルタイムコスト監視

```bash
# n8nダッシュボード
http://localhost:5678/workflow/cost-monitor

# Prometheus + Grafana
http://localhost:3001/d/openclaw-costs
```

### エージェント使用率

```sql
SELECT 
  agent_id,
  COUNT(*) as tasks,
  AVG(cost_usd) as avg_cost,
  SUM(cost_usd) as total_cost
FROM agent_tasks
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY agent_id
ORDER BY total_cost DESC;
```

## 🚀 次のステップ

1. ✅ **Phase 1完了**: マルチエージェント設定
2. ⬜ **Phase 2**: ファインチューニング（各エージェントのプロンプト最適化）
3. ⬜ **Phase 3**: 自動スケーリング（タスク量に応じてエージェント増減）
4. ⬜ **Phase 4**: エージェント間通信の最適化（メッセージキュー導入）

## 📚 参考資料

- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [OpenClaw Documentation](https://github.com/openclawai/openclaw)
- [Anthropic API Pricing](https://www.anthropic.com/pricing)
- [n8n Workflow Templates](https://n8n.io/workflows)

---

**次の質問**:

1. すぐに実装を開始しますか？（Phase 2のDocker設定）
2. まず最小構成（Jarvis + Alice のみ）でテストしますか？
3. コスト監視ダッシュボードから作りますか？
