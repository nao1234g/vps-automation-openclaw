# Claude Code 自律実行レーン（Autonomous Lane）

> **このファイルの目的**: 長時間・夜間・大量タスクを「確認なし」で自動実行する方法を正直に説明する。
> 「自律実行」とは何か、どう設定するか、どこに限界があるかを記述する。
> 最終更新: 2026-03-15 (T018)

---

## TL;DR（30秒まとめ）

| したいこと | 手順 |
|-----------|------|
| VS Code で夜間自律実行 | `bash scripts/night-mode-on.sh` → 就寝 → 翌朝 `bash scripts/night-mode-off.sh` |
| CLI で最大自律（1コマンド） | `bash scripts/runtime/lane-b-autonomous.sh` |
| VS Code の確認ダイアログを消す | すでに消えている（`settings.local.json` の `bypassPermissions`） |
| hook のブロックも全て消す | 設計上不可能（消すべきでない） |

---

## 2つのレーン

### Lane A — VS Code Extension（日常作業用）

```
[設定ファイル]
settings.local.json:  defaultMode = bypassPermissions
settings.json:        defaultMode = acceptEdits (共有用デフォルト)

[結果]
✅ Edit/Write/Bash の確認ダイアログ → なし
✅ 通常タスクの摩擦 → 最小
⚠️ hookガード（exit 2） → 意図的に残存
```

**Night Mode で追加バイパス（長期作業時）:**
```bash
bash scripts/night-mode-on.sh
# → pvqe-p-gate をバイパス
# → pre_edit_task_guard をバイパス
# → AskUserQuestion / EnterPlanMode を注入で抑制
```

### Lane B — CLI 自律実行（夜間・大量タスク用）

```
[コマンド]
bash scripts/runtime/lane-b-autonomous.sh

[実行される設定]
--dangerously-skip-permissions  ← CLI専用フラグ（VS Codeでは使えない）
night_mode.flag 作成            ← pvqe-p-gate + pre_edit_task_guard をバイパス

[結果]
✅ 全ての確認ダイアログ → なし
✅ pvqe-p-gate → バイパス
✅ pre_edit_task_guard → バイパス
⚠️ north-star-guard / vps-ssh-guard → 消えない（設計上）
```

---

## 各ガードの Night Mode 対応表

| ガード | 担当ファイル | Night Mode でバイパス？ | 残る理由 |
|--------|------------|----------------------|---------|
| pvqe-p-gate | `.claude/hooks/pvqe-p-gate.py` | ✅ はい | — |
| pre_edit_task_guard | `scripts/guard/pre_edit_task_guard.py` | ✅ はい | — |
| intent-confirm | `.claude/hooks/intent-confirm.py` | ✅ はい（フラグ削除） | — |
| research-gate | `.claude/hooks/research-gate.py` | ❌ **残る** | 廃止用語・未調査実装の防御 |
| north-star-guard | `.claude/hooks/north-star-guard.py` | ❌ **残る** | NORTH_STAR.md保護 |
| vps-ssh-guard | `.claude/hooks/vps-ssh-guard.py` | ❌ **残る** | VPS SSH前の健全性チェック |
| llm-judge | `.claude/hooks/llm-judge.py` | ❌ **残る** | 意味レベルの誤実装検知 |
| fact-checker | `.claude/hooks/fact-checker.py` | ❌ **残る** | 出力品質チェック |
| north-star-guard（OPERATING_PRINCIPLES） | 同上 | ❌ **残る** | 三原則保護 |

**重要**: Night Mode で消えるのは「作業フロー摩擦」だけ。「品質・安全ガード」は設計上不変。

---

## Lane B の使い方

### 事前準備（初回のみ）

```bash
# スクリプトに実行権限を付与
chmod +x scripts/runtime/lane-b-autonomous.sh
```

### 基本的な使い方

```bash
# 方法1: Lane Bスクリプト経由（推奨）
bash scripts/runtime/lane-b-autonomous.sh

# 方法2: 手動で同等の操作
bash scripts/night-mode-on.sh
claude --dangerously-skip-permissions

# 終了後（Night Modeを解除）
bash scripts/night-mode-off.sh
```

### Night Mode の解除を忘れた場合

```bash
# 現在の状態確認
ls .claude/hooks/state/night_mode.flag && echo "Night Mode: ON" || echo "Night Mode: OFF"

# 手動解除
bash scripts/night-mode-off.sh
```

---

## どんな状況で使うか

| 状況 | 推奨レーン | 備考 |
|------|-----------|------|
| 通常の開発作業 | Lane A（VS Code） | 既に bypassPermissions で最小摩擦 |
| 長期タスク（1時間以上） | Lane A + Night Mode | VS Code 内で `bash scripts/night-mode-on.sh` |
| 夜間自律実行 | Lane B（CLI） | 就寝前に起動、翌朝確認 |
| CI/CD パイプライン | Lane B | `--dangerously-skip-permissions` + 自動化 |
| 複数タスクの一括処理 | Lane B | 確認待ちがなく止まらない |

---

## Night Mode の仕組み

```
bash scripts/night-mode-on.sh
  ↓
.claude/hooks/state/night_mode.flag が作成される
  ↓
各ガードが起動時に night_mode.flag を確認:
  pvqe-p-gate.py:       if NIGHT_MODE_FLAG.exists(): sys.exit(0)
  pre_edit_task_guard:  if night_mode_path.exists(): return (allow)
  intent-confirm.py:    if NIGHT_MODE.exists(): sys.exit(0)
  ↓
また flash-cards-inject.sh が UserPromptSubmit で自律指示を注入:
  - AskUserQuestion 完全禁止
  - EnterPlanMode 完全禁止
  - 確認を求めるテキスト禁止
  - エラーが出ても止まらない → ログして次タスクへ
```

---

## 安全についての正直な説明

### Night Mode にリスクはあるか

**あります。意図的なトレードオフです。**

Night Mode で消えるガードは「フロー制御」（証拠計画の提出、タスクIDの確認）であり、
セキュリティガード（廃止用語ブロック、VPS健全性チェック）ではありません。

| Night Mode でのリスク | 軽減策 |
|-----------------------|-------|
| pvqe_p.json なしに実装が始まる | タスクの意図は会話コンテキストで代替 |
| task_id なしに Edit が実行される | 緊急時はログで追跡可能 |
| AskUserQuestion が禁止される | 安全側の選択を自動で実施 |

### やってはいけないこと

```
❌ night-mode-on.sh を実行したまま長期間放置する
   → 戻り忘れのリスク。夜明けに必ず night-mode-off.sh を実行

❌ settings.json（共有ファイル）を bypassPermissions に変更する
   → リポジトリをクローンした全員に適用される

❌ north-star-guard / vps-ssh-guard を手動で無効化する
   → これらは消すべきでない（設計上の安全装置）
```

---

## 関連ドキュメント

| ファイル | 内容 |
|---------|------|
| [docs/CLAUDE_PERMISSION_MODES.md](CLAUDE_PERMISSION_MODES.md) | 3つのパーミッションモードの詳細説明 |
| [docs/CLAUDE_VSCODE_LIMITATIONS.md](CLAUDE_VSCODE_LIMITATIONS.md) | VS Code拡張でできること/できないこと |
| [scripts/runtime/lane-b-autonomous.sh](../scripts/runtime/lane-b-autonomous.sh) | Lane B 起動スクリプト |
| [scripts/night-mode-on.sh](../scripts/night-mode-on.sh) | Night Mode 有効化 |
| [scripts/night-mode-off.sh](../scripts/night-mode-off.sh) | Night Mode 解除 |

---

*最終更新: 2026-03-15 — T018: Phase 0監査の結果から設計。「できる」「できない」を推測ではなく確認から記述。*
