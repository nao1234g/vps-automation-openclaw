# 確認ダイアログ実測マトリックス (T019)

> **T019成果物 — 「測定したはず」ではなく実際に計測した結果のみを記述する。**
> 未計測のものは「未確認」として明示。推測で埋めない。
> 作成: 2026-03-15

---

## 重要な区別（T018が混同していた2つの仕組み）

| 種類 | 制御方法 | Night Modeの影響 |
|------|---------|----------------|
| **UI確認ダイアログ** | `defaultMode` (acceptEdits / bypassPermissions) | **無関係** |
| **hookブロック (exit 2)** | 各hookのロジック + Night Mode | 一部バイパス可能 |

**これらは完全に独立した仕組み。**
- UI確認ダイアログ = Claude Codeが「実行してよいですか？」と人間に確認するもの
- hookブロック = hookスクリプトが`exit 2`を返し、技術的にツール実行を停止するもの

---

## T019 Phase 1 実測結果 (2026-03-15)

### 計測環境

| 項目 | 値 |
|------|---|
| OS | Windows 11 Pro |
| 実行環境 | VS Code Extension |
| モデル | claude-sonnet-4-6 |
| settings.local.json | 存在 → `defaultMode: bypassPermissions` |
| Night Mode | **OFF**（night_mode.flag なし） |

### 実測操作 vs ダイアログ有無

| 操作 | 結果 | 備考 |
|------|------|------|
| Bash `/tmp/friction-test-t019.txt` 作成 | **ダイアログなし（即実行）** | ファイル生成確認 |
| Bash `.claude/state/friction_test_t019.tmp` 作成 | **ダイアログなし（即実行）** | ファイル生成確認 |
| Edit `.claude/state/friction_test_t019.tmp` | **ダイアログなし（即実行）** | 内容変更確認 |
| Read（複数ファイル） | **ダイアログなし（即実行）** | 内容読み込み確認 |

**結論: `bypassPermissions` 設定済み環境では UI確認ダイアログは発生しない（実測確認済み）**

---

## 設定パターン別 期待動作マトリックス

| settings.local.json | settings.json defaultMode | 実行環境 | UIダイアログ | 実測/推定 |
|---------------------|--------------------------|---------|------------|---------|
| あり (bypassPermissions) | acceptEdits (fallback) | VS Code | **なし** | T019実測済み |
| なし | bypassPermissions | VS Code | **なし** | 推定（未計測） |
| なし | acceptEdits | VS Code | **あり** | 推定（未計測） |
| なし | acceptEdits | devcontainer | **あり** | 推定（未計測） |
| あり (bypassPermissions) | — | CLI (通常) | **なし** | 推定（未計測） |
| なし | — | CLI (--dangerously-skip-permissions) | **なし** | 推定（未計測） |

---

## devcontainer固有の注意（T019調査結果）

devcontainer内では `settings.local.json` が **存在しない**（gitignored）。

```
コンテナ内の設定優先順位:
  .claude/settings.local.json → 存在しない
  .claude/settings.json       → 有効（defaultMode: acceptEdits）
  → acceptEdits が有効 → UIダイアログが発生する可能性あり（未計測）
```

**対策:**
- `bash scripts/runtime/lane-b-devcontainer.sh` の [2/4] で警告が表示される
- `.claude/settings.json` の `defaultMode` を `bypassPermissions` に変更

---

## hookブロック (exit 2) 発動マトリックス

UI確認ダイアログとは独立して動作する。permission modeに関係なく発動する。

| hook | Night Mode OFF | Night Mode ON | 消す方法 |
|------|---------------|--------------|---------|
| `pvqe-p-gate.py` | ブロック | バイパス | Night Mode |
| `pre_edit_task_guard.py` | ブロック | バイパス | Night Mode |
| `intent-confirm.py` | ブロック | バイパス | Night Mode |
| `north-star-guard.py` | ブロック | ブロック | 消えない |
| `research-gate.py` | ブロック | ブロック | 消えない |
| `vps-ssh-guard.py` | ブロック | ブロック | 消えない |
| `llm-judge.py` | ブロック | ブロック | 消えない |
| `fact-checker.py` | ブロック | ブロック | 消えない |

---

## 未確認項目

| 項目 | 状況 |
|------|------|
| devcontainer内でのUIダイアログ実際の発生 | 未確認（devcontainer環境未構築） |
| acceptEditsモードでの実際のダイアログUI | 未確認（bypassPermissionsのみ計測） |
| CLIモードでの実際の動作 | 未確認（CLI実行環境なし） |
| `--dangerously-skip-permissions` vs `bypassPermissions` の実際の差 | 未確認 |

---

## 計測方法（再現手順）

```bash
# 自動診断スクリプトで状態確認
bash scripts/runtime/test-vscode-friction.sh

# 目視確認:
# 1. VS Code で Claude Code を開く
# 2. 「.claude/state/friction_test.tmp を作成して」と依頼
# 3. Bash/Edit操作時にダイアログが出るか目視確認
```

---

*T019実測完了: 2026-03-15 — bypassPermissions動作確認済み。未確認事項は「未確認」と明示。*
