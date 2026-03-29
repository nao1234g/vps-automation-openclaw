# Multi-Agent Coordination OS — Architecture

> 実装完了: 2026-03-29
> 対象: NEO-ONE / NEO-TWO / NEO-GPT / local-claude + 将来の全エージェント

---

## 1. 目的

4体でも1000体でも、同時に動くエージェントが「全員同じ current truth・同じ優先順位・同じ担当・同じ競合状況」を見ながら、衝突なく・手戻りなく・証跡付きで動くための **強制 coordination layer**。

---

## 2. アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────┐
│                   coordination.db (SQLite WAL)               │
│   /opt/shared/coordination/coordination.db                   │
│                                                              │
│  agents │ tasks │ leases │ events │ decisions │ handoffs    │
└─────────────────────────────────────────────────────────────┘
         ↑↑↑             ↑↑↑                ↑↑↑
    coordination_core.py (Python library)
         ↑↑↑             ↑↑↑
┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
│coordination  │  │coordination  │  │coordination          │
│_cli.py       │  │_reaper.py    │  │_snapshot.py          │
│(CLI + gate)  │  │(cron, 1min)  │  │(cron, 1min→MD)       │
└──────────────┘  └──────────────┘  └──────────────────────┘
```

### ファイル構成

| ファイル | パス | 役割 |
|---|---|---|
| `coordination_core.py` | `/opt/shared/scripts/` | コアライブラリ。CoordinationDB クラス |
| `coordination_cli.py` | `/opt/shared/scripts/` | CLIラッパー。エージェントが呼ぶ |
| `coordination_reaper.py` | `/opt/shared/scripts/` | TTL/heartbeat cron daemon |
| `coordination_snapshot.py` | `/opt/shared/scripts/` | ダッシュボード生成cron |
| `coordination.db` | `/opt/shared/coordination/` | SQLite WAL DB |
| `COORDINATION_STATE.md` | `/opt/shared/` | 人間が読むダッシュボード（毎分更新） |

---

## 3. 10の設計原則（インバリアント）

| # | インバリアント | 実装 |
|---|---|---|
| 1 | **No work starts blind** | `preflight_check()` を必ず呼ぶ。registered・heartbeat fresh・task not claimed でないとブロック |
| 2 | **No write without lease** | `acquire_lease()` → `release_lease()` でファイル/リソース操作を囲む |
| 3 | **No completion without evidence** | `complete_task()` は `evidence_refs=[]` で呼ぶと即 BLOCKED |
| 4 | **No stale truth** | snapshot が 90秒以上古いと preflight が WARNING 発報 |
| 5 | **No duplicate work** | `UNIQUE partial index` on `leases(subject_type, subject_id) WHERE status='active'` |
| 6 | **Every decision becomes shared fact** | `record_decision()` で全エージェントが読める decision journal に書く |
| 7 | **Dead agent recovery is automatic** | reaper が TTL 120秒超のエージェントを dead 判定 → handoff 自動生成 |
| 8 | **Human can always see state** | `COORDINATION_STATE.md` が毎分更新される |
| 9 | **No all-to-all chat at scale** | Pull-based polling（エージェントが DB を読む）。Telegram は補助のみ |
| 10 | **Idempotent recovery** | 全 mutation に `idempotency_key`。重複実行しても安全 |

---

## 4. DB スキーマ

### agents

| 列 | 型 | 説明 |
|---|---|---|
| agent_id | TEXT PK | 'neo-one', 'local-claude' 等 |
| session_id | TEXT | UUID。再起動のたびに変わる |
| current_status | TEXT | idle/working/blocked/dead |
| last_heartbeat_at | REAL | UNIX timestamp |
| current_task_id | TEXT | 現在担当中のタスク |
| capabilities | TEXT | JSON array |

### tasks

| 列 | 型 | 説明 |
|---|---|---|
| task_id | TEXT PK | 'TASK-{8文字UUID}' |
| status | TEXT | pending/claimed/working/completed/failed/blocked/needs_handoff |
| owner_agent | TEXT | 担当エージェント |
| priority | INTEGER | 1=最高, 10=最低 |
| evidence_refs | TEXT | JSON array。完了時に必須 |
| idempotency_key | TEXT UNIQUE | 重複防止キー |

### leases

| 列 | 型 | 説明 |
|---|---|---|
| lease_id | TEXT PK | UUID |
| subject_type | TEXT | 'task'/'file'/'directory'/'resource' |
| subject_id | TEXT | ファイルパス等 |
| holder_agent | TEXT | 保持エージェント |
| expires_at | REAL | TTL。超えたら reaper が expire |
| status | TEXT | active/released/expired/stolen |

**重要**: `UNIQUE INDEX ON leases(subject_type, subject_id) WHERE status='active'`
→ 1つのリソースに同時に1エージェントしかアクティブleaseを持てない。

### events（append-only）

**絶対ルール: UPDATE/DELETE 禁止。INSERT のみ。**

全操作がイベントとして記録される。監査ログ・デバッグの基盤。

### decisions

エージェントが下した意思決定をチーム全員で共有する journal。
`supersedes` フィールドで古い決定を無効化できる。

### handoffs

死亡/ブロックしたエージェントが後継エージェントへ状態を引き渡す契約。
`to_agent=NULL` は「誰でも拾ってよい」を意味する。

---

## 5. エージェントの標準ワークフロー

```bash
# === 起動時 (1回) ===
python3 /opt/shared/scripts/coordination_cli.py register neo-one \
  --model claude-opus-4-6 --host vps --workspace /opt

# === 作業ループ (毎回) ===

# 1. heartbeat（60秒ごと）
python3 /opt/shared/scripts/coordination_cli.py heartbeat neo-one

# 2. 次のタスクを取得
python3 /opt/shared/scripts/coordination_cli.py task-next --agent neo-one

# 3. 開始前にpreflight
python3 /opt/shared/scripts/coordination_cli.py preflight neo-one --task TASK-XXXXXXXX

# 4. タスクを担当宣言
python3 /opt/shared/scripts/coordination_cli.py task-claim neo-one TASK-XXXXXXXX

# 5. ファイルにleaseを取る（書き込む前に必ず）
python3 /opt/shared/scripts/coordination_cli.py lease neo-one file /opt/shared/scripts/foo.py

# 6. 作業開始
python3 /opt/shared/scripts/coordination_cli.py task-start neo-one TASK-XXXXXXXX

# === 作業中 ===
# ... ファイル編集・スクリプト実行 ...

# 意思決定を記録（重要な判断）
python3 /opt/shared/scripts/coordination_cli.py decide neo-one prediction_page "Use WAL mode" \
  --rationale "SQLite WAL supports concurrent readers without blocking"

# 7. leaseを解放
python3 /opt/shared/scripts/coordination_cli.py release neo-one \
  --type file --subject /opt/shared/scripts/foo.py

# 8. 完了（evidence必須）
python3 /opt/shared/scripts/coordination_cli.py task-done neo-one TASK-XXXXXXXX \
  --evidence "log:/opt/shared/logs/...,url:https://nowpattern.com/..."

# === 完了できない場合 ===
python3 /opt/shared/scripts/coordination_cli.py task-fail neo-one TASK-XXXXXXXX \
  --reason "Blocked by Ghost API timeout"
# → 自動でhandoff contractが生成される
```

---

## 6. Reaper の動作

毎分 cron で `coordination_reaper.py` が実行される:

1. `last_heartbeat_at > 120秒前` のエージェントを `dead` に変更
2. `expires_at < now` のリースを `expired` に変更
3. `dead` エージェントが持っていた `claimed/working` タスクを `needs_handoff` に変更
4. 該当タスクに対して handoff contract を自動生成
5. TTL 切れの handoff を `expired` に変更

---

## 7. conflict_policy

| ポリシー | 動作 |
|---|---|
| `reject`（デフォルト）| 既存リースがあれば即エラー返却 |
| `steal` | 強制的に前のリースを奪う（緊急時用） |
| `queue` | 未実装（将来対応） |

---

## 8. TTL 設定

| 設定値 | デフォルト | 意味 |
|---|---|---|
| `AGENT_TTL` | 120秒 | この秒数 heartbeat がないと dead |
| `AGENT_HB_INTERVAL` | 60秒 | エージェントが heartbeat すべき間隔 |
| `LEASE_TTL_DEFAULT` | 300秒 | リースのデフォルト有効期限 |
| `TASK_ACTIVITY_TTL` | 600秒 | (参考) working タスクの活動期限 |
| `SNAPSHOT_MAX_AGE` | 90秒 | preflight でスナップショット陳腐化警告 |

---

## 9. スケーラビリティ

- **SQLite WAL**: 複数の同時読み取り + 単一ライターを安全に処理
- **Partial UNIQUE INDEX**: `O(1)` でリース競合を検出
- **Pull-based**: エージェントが DB を直接読む。ブロードキャスト不要
- **Idempotency keys**: 重複実行・リトライに強い
- **将来 PostgreSQL 移行**: `CoordinationDB` クラスを差し替えるだけ（インターフェース固定）

現在4エージェント → 100エージェントでも再設計不要。

---

## 10. ダッシュボードの確認

```bash
# リアルタイム状態
cat /opt/shared/COORDINATION_STATE.md

# CLIステータス
python3 /opt/shared/scripts/coordination_cli.py status

# 競合チェック
python3 /opt/shared/scripts/coordination_cli.py conflicts

# イベントストリーム
python3 /opt/shared/scripts/coordination_cli.py events --limit 50

# 意思決定ジャーナル
python3 /opt/shared/scripts/coordination_cli.py decisions
```

---

## 11. NEO-ONE/TWO への統合手順

NEO のシステムプロンプトに以下を追加済み（予定）:

```
作業開始前に必ず:
  python3 /opt/shared/scripts/coordination_cli.py heartbeat neo-one
  python3 /opt/shared/scripts/coordination_cli.py preflight neo-one

ファイル書き込み前:
  python3 /opt/shared/scripts/coordination_cli.py lease neo-one file <パス>

作業完了時:
  python3 /opt/shared/scripts/coordination_cli.py task-done neo-one <task_id> --evidence <証拠>
```

---

## CHANGELOG

| 日付 | 変更内容 |
|---|---|
| 2026-03-29 | 初版。4スクリプト実装・デプロイ・cron登録完了。4エージェント登録・全テスト PASS |
