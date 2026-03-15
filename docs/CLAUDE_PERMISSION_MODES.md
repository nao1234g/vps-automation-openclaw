# Claude Code パーミッションモード リファレンス

> **このファイルが唯一の正（Single Source of Truth）。**
> 設定の現実を正直に記述する。推測で書かない。
> 最終更新: 2026-03-15 (T018)

---

## 現在の設定構成（2ファイル方式）

| ファイル | モード | スコープ | gitignore |
|----------|--------|---------|-----------|
| `.claude/settings.json` | `acceptEdits` | リポジトリ全体（共有） | **いいえ（共有される）** |
| `.claude/settings.local.json` | `bypassPermissions` | Naotoのローカルのみ | **はい（ローカル専用）** |

**優先順位**: `settings.local.json` > `settings.json`

現在Naotoの環境では `bypassPermissions` が有効（settings.local.jsonが優先）。

---

## 3つのパーミッションモード

### 1. `acceptEdits`（保守的・デフォルト）

```json
// .claude/settings.json（現在の値）
{ "defaultMode": "acceptEdits" }
```

- Edit/Writeツール: **毎回UIで確認**
- Bash: 毎回確認
- 用途: 新メンバーのオンボーディング、慎重な作業時

### 2. `bypassPermissions`（高速・Naoto推奨）

```json
// .claude/settings.local.json（現在の値）
{ "defaultMode": "bypassPermissions" }
```

- Edit/Write/Bash: **確認なしで自動実行**
- 用途: 通常の開発作業（Naotoのローカル環境）
- **注意**: bare-metalで`settings.json`に書くのは危険。`settings.local.json`に限定する

### 3. `--dangerously-skip-permissions`（CLIフラグ）

```bash
claude --dangerously-skip-permissions
```

- `bypassPermissions`と同等だがCLIフラグとして指定
- **VS Code拡張では使用不可**（CLI専用）
- 用途: 自律実行スクリプト、sandbox/VM環境

---

## Hook ブロック（exit 2）はパーミッションモードとは別物

> **重要**: `bypassPermissions` や `--dangerously-skip-permissions` を設定しても、
> hookが `exit 2` を返せばツール実行は停止する。

| 混同しがち | 正確な理解 |
|----------|-----------|
| "bypassPermissions = 全確認が消える" | × |
| "bypassPermissions = Claude CodeのUI確認が消える。hookブロックは別" | ✅ |

### ブロックの種類

```
┌─────────────────────────────────────────────────────┐
│  Claude Code が表示するもの                           │
│                                                     │
│  (A) 確認ダイアログ   ← bypassPermissions で消える    │
│      「このファイルを編集しますか？」                 │
│                                                     │
│  (B) hookエラー       ← bypassPermissions では消えない│
│      「[TASK GUARD] ❌ タスク未登録」               │
│      hookが exit 2 を返してツール実行を停止          │
└─────────────────────────────────────────────────────┘
```

---

## 現在の全Hook一覧（PreToolUse）

| Hook | Trigger | ブロック条件 | Night Modeでバイパス？ |
|------|---------|------------|----------------------|
| `pre_edit_task_guard.py` | Edit/Write | active_task_id.txtが空 | ✅ はい |
| `task_state_integrity_check.py` | Edit/Write | 完了タスクを再編集（ソフトブロック） | ❌ いいえ（ただしソフト） |
| `pvqe-p-gate.py` | Edit/Write | pvqe_p.jsonが古い/なし | ✅ はい |
| `research-gate.py` | Edit/Write/Read | 新規コードで調査なし | ❌ いいえ（調査で解除） |
| `llm-judge.py` | Edit/Write | 200+文字の.py/.shで意味エラー検知 | ❌ いいえ（8秒タイムアウトで通過） |
| `north-star-guard.py` | Edit/Write | NORTH_STAR.md等への書き込み | ❌ 絶対不可 |
| `ui-layout-guard.py` | Edit/Write/Bash | 承認なしUIレイアウト変更 | ❌ いいえ |
| `release_gate.py --ssh-only` | Bash | SSH前ゲートチェック | ❌ いいえ |
| `vps-ssh-guard.py` | Bash | VPS SSH健全性チェック | ❌ いいえ |

---

## Night Modeが消すもの / 消さないもの

```bash
# Night Mode 有効化
bash scripts/night-mode-on.sh

# Night Mode 解除
bash scripts/night-mode-off.sh
```

### Night Modeで消える摩擦

- `pvqe-p-gate.py`: 証拠計画(pvqe_p.json)の要求 → **消える**
- `pre_edit_task_guard.py`: active_task_id.txtの要求 → **消える**
- `flash-cards-inject.sh`: 「AskUserQuestion禁止」指示の注入 → **自律実行指示に変わる**

### Night Modeでも消えない安全ガード

- `north-star-guard.py`: NORTH_STAR.md/OPERATING_PRINCIPLES.md保護 → **消えない（永久保護）**
- `vps-ssh-guard.py`: VPS SSH健全性チェック → **消えない**
- `research-gate.py`: 調査なし新規コードのブロック → **消えない**
- `ui-layout-guard.py`: UIレイアウト承認フロー → **消えない**

---

## ファイル変更の影響範囲

| 変更したいとき | 変更するファイル | 影響範囲 |
|--------------|----------------|---------|
| Naotoのローカルを高速化したい | `.claude/settings.local.json` | 自分だけ |
| リポジトリのデフォルトを変えたい | `.claude/settings.json` | 全クローン |
| CLI自律実行スクリプトを作りたい | `scripts/runtime/` | スクリプト実行時のみ |
| sandbox/VM用設定を変えたい | `.devcontainer/devcontainer.json` | コンテナ内のみ |

---

*最終更新: 2026-03-15 — T018: Runtime Lane A+B 実装。Phase 0監査結果を正確に記述。*
