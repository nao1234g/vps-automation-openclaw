# AGENTS.md — 全エージェント共通エントリーポイント

> このファイルはClaude, Codex, GPT, 将来のあらゆるAIエージェントが最初に読むファイル。
> エージェントの種類に関係なく、このリポジトリで作業する前に必ず読むこと。

---

## このリポジトリの正体

**`vps-automation-openclaw` = NAOTO OS（Naoto Intelligence OS）のルートリポジトリ。**

NAOTO OS = 創設者Naotoの意図を実行するOS。
Nowpattern = NAOTO OS配下の最重要プロジェクト（予測オラクルプラットフォーム）。

---

## 読む順番（Read Order）

| 順番 | ファイル | 内容 |
|------|---------|------|
| 1 | `.claude/rules/NORTH_STAR.md` | 意図・哲学・ミッション・永遠の三原則 |
| 2 | `docs/OPERATIONS_BOARD.md` | 今の真実、進行中タスク、次の優先順位、完了/未完了 |
| 3 | `scripts/mission_contract.py` | ミッション契約（全エージェント必読） |
| 4 | `scripts/agent_bootstrap_context.py` | 現在の状態を把握するブートストラップ |
| 5 | `reports/content_release_snapshot.json` | コンテンツリリースの最新スナップショット |
| 6 | `docs/KNOWN_MISTAKES.md` | 既知のミス（同じミスを繰り返さない） |
| 7 | `docs/AGENT_WISDOM.md` | 蓄積された知恵 |

---

## 非交渉条件（全エージェント共通）

- `mission_contract.py` を読まずに public action してはならない
- `bootstrap_context` を読まずに現状判断してはならない
- public UI は `canonical_public_lexicon` 以外の語彙を使ってはならない
- public release は `release_governor` を通らずに行ってはならない
- incident は `rule + test + monitor` に変換されなければ完了ではない

---

## JIT参照（必要時に読む）

| いつ読むか | ファイル |
|-----------|---------|
| NORTH_STARの詳細版（実践ガイド・テンプレート） | `.claude/reference/NORTH_STAR_DETAIL.md` |
| 行動規範・コンテンツ・タグ・X投稿 | `.claude/reference/OPERATING_PRINCIPLES.md` |
| フック・NEO・Docker・VPS・予測ページUI | `.claude/reference/IMPLEMENTATION_REF.md` |
| エントリーポイント（Claude専用設定） | `.claude/CLAUDE.md` |
| 類似予測検索（AI Notion実装） | `scripts/prediction_similarity_search.py` |

---

## Agent Coordination Protocol（排他制御）

全エージェントは `docs/OPERATIONS_BOARD.md` を見てから `.coordination/` を確認し、競合を防ぐこと。

### 仕組み

```
.coordination/
├── protocol.json       # ルール定義（heartbeat間隔、stale閾値）
├── claude-code.json    # Claude Codeの authoritative state
├── codex.json          # Codexの authoritative state
├── <other-agent>.json  # 追加エージェントも同形式で自動 discovery
└── lock-registry.json  # state files から生成される lock view
```

### 各エージェントの義務

| タイミング | やること |
|-----------|---------|
| セッション開始時 | `docs/OPERATIONS_BOARD.md` を読む → `.coordination/{自分の名前}.json` を `status: "active"` + `current_task` で更新 → derived artifacts を同期 |
| ファイル編集前 | 他エージェントの `locked_files` に **repo-relative path** で対象ファイルが含まれていないか確認。Codex/他エージェントは `python3 scripts/coordination_guard.py check <path>` を使う |
| 長時間作業時 | `locked_files` に **repo-relative path** で作業中ファイルを追加（排他宣言）。5分ごとを目安に `python3 scripts/coordination_guard.py keepalive ... --interval 300` を使う |
| タスク更新時 | `current_task` / `next_step` を更新し、必要なら board を再同期 |
| セッション終了時 | `status: "idle"`, `locked_files: []` にリセットし、derived artifacts を同期 |

### 状態ファイルのフォーマット

```json
{
  "agent": "codex",
  "status": "active",
  "current_task": "prediction tracker performance optimization",
  "locked_files": ["scripts/prediction_page_builder.py", "scripts/reader_prediction_api.py"],
  "vps_resources": [],
  "updated_at": "2026-04-05T12:00:00+09:00",
  "session_id": ""
}
```

### ルール

- `status` が `active` かつ `updated_at` が10分以内のエージェントのロックのみ有効
- state files は `.coordination/*.json` から自動 discovery される
- `locked_files` は **basename ではなく repo-relative path** を使うこと
- 旧データ互換のため basename-only ロックは暫定で読まれるが、新規追記では禁止
- 機械向け authoritative source は `.coordination/{agent}.json`
- `docs/OPERATIONS_BOARD.md` と `.coordination/lock-registry.json` は derived artifacts
- `.coordination/` ディレクトリ自体の編集は常に許可（デッドロック防止）
- Claude Codeは `PreToolUse` hookで自動チェック（`coordination-pretool.py`）
- Codex/他エージェントは `scripts/coordination_guard.py` を使って check / heartbeat / keepalive を行うこと
- 競合が検出された場合: 相手のタスク完了を待つか、`.coordination/` で調整

---

## エージェント別の追加設定

| エージェント | 追加設定ファイル |
|-------------|----------------|
| Claude Code（ローカル） | `.claude/CLAUDE.md` + `.claude/settings.json` |
| NEO-ONE（VPS） | `/opt/claude-code-telegram/CLAUDE.md` |
| NEO-TWO（VPS） | `/opt/neo2/CLAUDE.md` |
| NEO-GPT / Codex（VPS） | `/opt/neo3-codex/CLAUDE.md` |

---

*最終更新: 2026-04-05 — Agent Coordination Protocol追加（.coordination/排他制御）*
