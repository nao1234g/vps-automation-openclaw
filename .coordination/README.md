# Agent Coordination Protocol

ローカルエージェント（Claude Code / Codex）がお互いの作業を認識し、
ファイル競合を防ぐためのファイルベース調整システム。

人間と全エージェントが最初に読む共有ボードは
`docs/OPERATIONS_BOARD.md`。
`.coordination/{agent}.json` が機械向けの authoritative state で、
board と `lock-registry.json` はそこから導出される補助ビューです。

## 仕組み

1. 各エージェントが最初に `docs/OPERATIONS_BOARD.md` を読む
2. 各エージェントが discovery される `{agent-name}.json` に `status/current_task/next_step/locked_files` を書く
3. `python3 scripts/update_operations_board.py` で board と derived lock registry を同期する
4. 作業開始前に他エージェントの `.json` を読んで競合チェック
5. `lock-registry.json` は agent state から生成される lock view

## ファイル

- `claude-code.json` — Claude Code の現在タスク・ロック中ファイル
- `codex.json` — Codex の現在タスク・ロック中ファイル
- `*.json` — 追加エージェントも同じ形式で自動 discovery 対象
- `lock-registry.json` — 全エージェントのファイルロック集約（generated / non-authoritative）
- `protocol.json` — プロトコル定義（フック参照用）
- `../docs/OPERATIONS_BOARD.md` — 人間可読の単一運用ボード

## 自動化

- Claude Code: `coordination-pretool.py` フック（PreToolUse/Edit,Write）
- Codex: `python3 scripts/coordination_guard.py check <path>` で衝突確認し、`heartbeat` で状態更新 + 同期
- 長時間タスクは `python3 scripts/coordination_guard.py keepalive ... --interval 300` で stale を防げる

## ロックの書き方

- `locked_files` は basename ではなく **repo-relative path** を使う
- 例: `scripts/prediction_page_builder.py`
- 旧 basename-only 形式は読み取り時だけ互換サポートするが、新規追記では使わない

### 推奨同期コマンド

```bash
python3 scripts/update_operations_board.py
```

### Codex 向け推奨コマンド

```bash
python3 scripts/coordination_guard.py check scripts/prediction_page_builder.py
python3 scripts/coordination_guard.py heartbeat --agent codex --task "..." --next-step "..." --locked-files "scripts/prediction_page_builder.py"
python3 scripts/coordination_guard.py keepalive --agent codex --task "..." --next-step "..." --locked-files "scripts/prediction_page_builder.py" --interval 300
```
