# NEXT STEPS (Other IDE)

最終更新: 2026-02-06 04:55 UTC

## 1. ここまでで反映済みの内容

- OpenClaw が `config/openclaw/openclaw.json` を確実に読むように修正
  - マウント先を `/home/appuser/.openclaw/openclaw.json` に統一
- マルチエージェント設定を現行スキーマに合わせて修正
  - `agents.list` に `gemini-cheap` / `claude-premium` を定義
  - 不正キー `provider` を削除（`model: "provider/model"` 形式へ）
- OpenClaw コンテナに Gemini 用環境変数を注入
  - `GEMINI_API_KEY` と `GOOGLE_API_KEY` を渡すよう修正
- `openclaw-agent` は現在 `healthy` で稼働
- Gateway API 上で `agents.list` に以下が出ることを確認済み
  - `gemini-cheap`
  - `claude-premium`
  - `main`（OpenClawの内蔵デフォルト）

## 2. まだ残っている課題（最重要）

APIキーが無効で、実応答だけ失敗しています。

- Gemini: `API_KEY_INVALID`
- Claude: `invalid x-api-key`

つまり「エージェント切替・認識」は直っており、残りは「有効なキーに差し替える」作業です。

## 3. 他IDEで最初にやること（そのまま実行）

1. 最新を取得
```bash
git checkout main
git pull origin main
```

2. `.env` を開いて実キーを設定（コミット禁止）
```bash
# 必須
ANTHROPIC_API_KEY=...有効キー...
GOOGLE_API_KEY=...有効キー...
GEMINI_API_KEY=...有効キー...   # GOOGLE_API_KEY と同値でも可
OPENCLAW_GATEWAY_TOKEN=...既存運用値を維持...
```

3. OpenClaw を再作成
```bash
docker compose -f docker-compose.yml up -d --force-recreate openclaw
```

4. 反映確認
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker exec openclaw-agent env | grep -E "ANTHROPIC_API_KEY|GOOGLE_API_KEY|GEMINI_API_KEY"
docker exec openclaw-agent openclaw gateway call agents.list --json --params "{}"
```

5. 両エージェント送信テスト
```bash
docker exec openclaw-agent openclaw agent --agent gemini-cheap --message "こんにちは！あなたのモデル名を教えてください" --json
docker exec openclaw-agent openclaw agent --agent claude-premium --message "こんにちは！あなたのモデル名を教えてください" --json
```

## 4. Control UIでの確認手順

1. `http://localhost:3000` を開く
2. `Ctrl+Shift+R` でハードリロード
3. Agents 画面で以下を確認
   - `gemini-cheap 🔮`
   - `claude-premium 💎`
4. Chat画面でエージェントを切り替えて送信

## 5. 追加でやるとよいこと（任意）

- Telegram 未設定エラーを避けるため、使わないならTelegram連携を無効化
- OpenClaw を `2026.2.3-1` へ更新検討（現在 `2026.2.2-3`）
- API利用上限設定（Google/Anthropic両方）

## 6. 今回変更したファイル

- `config/openclaw/openclaw.json`
- `docker-compose.yml`
- `docker-compose.quick.yml`
- `docker-compose.production.yml`
- `docker-compose.dev.yml`
- `docker-compose.monitoring.yml`
- `HANDOFF_INSTRUCTIONS.md`
- `NEXT_STEPS_IDE.md`（このファイル）

