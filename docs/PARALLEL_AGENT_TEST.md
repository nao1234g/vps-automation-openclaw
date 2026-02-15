# 並列エージェント処理テスト手順

> Jarvis が sessions_spawn を使って複数のエージェントを同時実行するテスト

---

## テスト目的

OpenClaw の `sessions_spawn` 機能を使い、Jarvis が Alice と Luna を **同時に** 異なるタスクで起動し、結果を統合できるかを検証します。

## 前提条件

- ✅ VPS上の OpenClaw Gateway が稼働中
- ✅ Telegram Bot が接続済み
- ✅ Jarvis が `subagents.allowAgents` に Alice と Luna を登録済み
- ✅ `tools.allow` に `"group:sessions"` が含まれている

## 実行方法

### オプション1: Telegram経由（推奨）

Telegram で OpenClaw ボット (`@openclaw_nn2026_bot`) に以下のメッセージを送信：

```
AliceとLunaを同時に呼んで。
Alice: 「PostgreSQL パフォーマンスチューニングのベストプラクティスを調べて」
Luna: 「Substack投稿の見出しの書き方（エンゲージメントを高める方法）を調べて」
```

### オプション2: SSH経由で直接実行

VPSにSSH接続して、OpenClaw CLIから実行：

```bash
# VPSにSSH接続
ssh -i ~/.ssh/id_ed25519 root@163.44.124.123

# OpenClawコンテナ内に入る
docker exec -it openclaw-agent bash

# sessions_spawn でAliceを起動（バックグラウンド）
openclaw sessions spawn \
  --agent alice-research \
  --prompt "PostgreSQL パフォーマンスチューニングのベストプラクティスを調べてください。インデックス設計、VACUUM、クエリ最適化の3点を重点的にお願いします。" \
  --background

# sessions_spawn でLunaを起動（バックグラウンド）
openclaw sessions spawn \
  --agent luna-writer \
  --prompt "Substack投稿の見出しの書き方について調べてください。エンゲージメントを高めるテクニック、クリック率を上げる方法を重点的にお願いします。" \
  --background

# セッション一覧を確認
openclaw sessions list

# 各セッションの出力を確認
openclaw sessions output <session-id>
```

## 期待される動作

1. **Jarvis が sessions_spawn を2回呼び出す**
   - Alice: PostgreSQL最適化のリサーチ
   - Luna: Substack見出しのリサーチ

2. **並列実行**
   - 2つのセッションが同時に動作
   - `subagents.maxConcurrent: 3` の範囲内

3. **結果の統合**
   - Jarvis が両エージェントの結果を受け取る
   - 統合された報告をユーザーに返す

## 検証ポイント

### ✅ 成功の条件

- [ ] Alice と Luna が同時に起動される
- [ ] 両方のタスクが完了する
- [ ] Jarvis が結果を統合して報告する
- [ ] エラーなく終了する

### ❌ 失敗のパターン

- **pairing required エラー**: デバイス認証が通っていない → `docs/OPENCLAW_PAIRING_SOLUTION.md` 参照
- **sessions_spawn: command not found**: sessions ツールが有効化されていない → `openclaw.json` の `tools.allow` を確認
- **agent not found**: エージェントIDの typo → `agents.list` の `id` を確認

## トラブルシューティング

### Issue: sessions_spawn が動作しない

**Diagnosis:**
```bash
# Jarvis の設定を確認
docker exec openclaw-agent cat ~/.openclaw/openclaw.json | jq '.agents.list[] | select(.id=="jarvis-cso")'

# tools.allow に "group:sessions" があるか確認
# subagents.allowAgents に "alice-research", "luna-writer" があるか確認
```

**Fix:**
```json
{
  "id": "jarvis-cso",
  "tools": {
    "allow": [
      "group:sessions",  // 追加
      "group:runtime",
      "group:fs",
      "group:web"
    ]
  },
  "subagents": {
    "allowAgents": [
      "alice-research",  // 追加
      "luna-writer"      // 追加
    ]
  }
}
```

### Issue: pairing required

**Solution:**
```bash
# デバイスが登録されているか確認
docker exec openclaw-agent cat ~/.openclaw/devices/paired.json

# 空 {} の場合、手動登録が必要
# docs/OPENCLAW_PAIRING_SOLUTION.md 参照
```

## 結果の記録

テスト完了後、以下を記録：

1. **実行時刻**: YYYY-MM-DD HH:MM
2. **成功/失敗**: ✅ / ❌
3. **実行時間**: Alice: XX秒, Luna: YY秒
4. **並列実行確認**: 同時実行されたか？
5. **結果の質**: リサーチ結果は有用だったか？

## 次のステップ

並列実行が成功したら、以下の拡張テストを実施：

1. **3エージェント同時実行**: Alice + Luna + CodeX
2. **長時間タスク**: 各エージェントに5分以上かかるタスクを振る
3. **エラーハンドリング**: 1つのエージェントが失敗した場合の挙動
4. **N8N統合**: ワークフローから sessions_spawn を呼び出す（間接的に）

---

*最終更新: 2026-02-15 — 並列エージェント処理テスト手順を作成*
