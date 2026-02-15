# APIキー取得ガイド（コスト削減プラン）

## 1. DeepSeek API（$1無料クレジット）

1. https://platform.deepseek.com/ にアクセス
2. アカウント作成（GitHub/Google でサインイン可）
3. 「API Keys」→「Create API Key」
4. キーをコピー: `sk-...`
5. VPS `.env` に追加:
   ```bash
   DEEPSEEK_API_KEY="sk-..."
   ```

## 2. OpenRouter（18個の無料モデル）

1. https://openrouter.ai/ にアクセス
2. アカウント作成
3. 「API Keys」→「Create Key」
4. キーをコピー: `sk-or-v1-...`
5. VPS `.env` に追加:
   ```bash
   OPENROUTER_API_KEY="sk-or-v1-..."
   ```

**メリット**: 300+モデルを統一APIで管理、手数料5.5%

## 3. xAI Grok（$25無料クレジット）

**既に取得済み**: CLAUDE.mdに記載の$5購入済みキーを継続利用

追加クレジットが必要な場合:
1. https://console.x.ai/ にアクセス
2. 新規アカウント作成で$25無料
3. Data Sharingプログラムで月額$150追加

## 4. OpenClaw への登録

```bash
# VPS で実行
ssh root@163.44.124.123

# 1. OpenRouter登録
docker exec openclaw-agent openclaw onboard --auth-choice openrouter
# → プロンプトに従ってAPIキー入力

# 2. DeepSeek登録（カスタムプロバイダー）
docker exec openclaw-agent sh -c 'echo "DEEPSEEK_API_KEY=sk-..." >> /home/appuser/.openclaw/.env'

# 3. 確認
docker exec openclaw-agent openclaw models status
```

## 5. openclaw.json 更新

```bash
# バックアップ
docker exec openclaw-agent cp /home/appuser/.openclaw/config.json /home/appuser/.openclaw/config.json.bak

# 最適化構成を適用（次のセクション参照）
```
