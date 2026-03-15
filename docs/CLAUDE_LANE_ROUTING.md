# Lane Routing ガイド（T019成果物）

> T019成果物。「理論で書いた」T018の失敗を繰り返さず、
> 実際のワークフローに基づいた判断基準を提供する。
> 作成: 2026-03-15

---

## Lane 一覧

| Lane | 実行環境 | 起動方法 | UIダイアログ | deny list |
|------|---------|---------|------------|---------|
| **Lane A** | VS Code Extension | VS Code起動のまま | なし（bypassPermissions済み） | 有効 |
| **Lane B CLI** | ローカルターミナル | `bash scripts/runtime/lane-b-autonomous.sh` | なし（--dangerously-skip-permissions） | 無効化 |
| **Lane B devcontainer** | devcontainer内 | `bash scripts/runtime/lane-b-devcontainer.sh` | settings.json依存（要確認） | 有効 |

---

## 判断フロー

```
作業したい
  │
  ├─ 通常作業（hookガードが必要）
  │   → Lane A（VS Code Extension）
  │     bypassPermissions有効 → UIダイアログなし
  │     pvqe-p-gate等のhookは有効
  │     必要に応じて Night Mode を手動で追加
  │
  ├─ 夜間/大量タスク（hookを一部バイパスしたい）
  │   ├─ CLIで動かしてよい
  │   │   → Lane B CLI（lane-b-autonomous.sh）
  │   │     Night Mode自動ON + --dangerously-skip-permissions
  │   └─ VS Codeのまま動かしたい
  │       → Lane A + Night Mode
  │         bash scripts/night-mode-on.sh
  │         ... 作業 ...
  │         bash scripts/night-mode-off.sh
  │
  └─ devcontainer内で動作確認したい（環境分離が必要）
      → Lane B devcontainer（lane-b-devcontainer.sh）
        Night Mode自動ON + VS Codeガイド付き
        注意: settings.local.jsonが存在しないため settings.json確認必須
```

---

## Lane A: 通常運用（推奨）

**使う場面**: 日常的な開発作業、hookガードが重要なタスク

特別な起動手順は不要。VS Codeでいつも通り使う。

**特徴**:
- `settings.local.json` の bypassPermissions → UIダイアログなし（T019実測確認済み）
- 全hookが有効（pvqe-p-gate, north-star-guard 等）
- Night Mode OFF → pvqe-p-gate が証拠計画要求

**Night Modeを追加する場合（大量タスク時）**:
```bash
bash scripts/night-mode-on.sh
# ... VS Code内で作業 ...
bash scripts/night-mode-off.sh  # 必ず解除！
```

---

## Lane B CLI: 自律実行（大量タスク・夜間向け）

**使う場面**: 夜間バッチ、大量ファイル処理、hookを可能な限りバイパスしたい

```bash
bash scripts/runtime/lane-b-autonomous.sh
```

**特徴**:
- `--dangerously-skip-permissions` → UIダイアログなし + deny listも無効化
- Night Mode自動ON → pvqe-p-gate / pre_edit_task_guard バイパス
- **残るガード**: north-star-guard / research-gate / vps-ssh-guard / llm-judge
- 終了時に Night Mode解除を確認するtrap付き

**VS Code版との違い**:
```
VS Code (Lane A):      bypassPermissions → UIダイアログなし、deny list有効
CLI (Lane B):          --dangerously-skip-permissions → UIダイアログなし、deny list無効化
```

---

## Lane B devcontainer: コンテナ内実行

**使う場面**: 環境を完全に分離したい、VPS相当の環境でテストしたい

```bash
bash scripts/runtime/lane-b-devcontainer.sh
```

**特徴**:
- devcontainer内でClaude CLIが実行可能（`npm install -g @anthropic-ai/claude-code` 自動インストール）
- Night Mode自動ON → pvqe-p-gate / pre_edit_task_guard バイパス
- **deny listは有効**（Lane B CLIより安全）
- VS Codeの「Reopen in Container」後にdevcontainer内でclaude実行

### devcontainer固有の注意点

```
settings.local.json は gitignored → devcontainer内に存在しない
→ settings.json の defaultMode が有効（デフォルト: acceptEdits）
→ acceptEdits なら UIダイアログが発生する！

対策: lane-b-devcontainer.sh の [2/4] ステップで警告が表示される
     → 警告内容を確認してから devcontainer を開く
     → 必要なら .claude/settings.json を bypassPermissions に変更
```

---

## Night Mode の扱い

Night ModeはLane選択とは独立して有効化できる。

```bash
# 手動管理（Lane A）
bash scripts/night-mode-on.sh
# ... 作業 ...
bash scripts/night-mode-off.sh

# 自動管理（Lane B — スクリプトが管理）
bash scripts/runtime/lane-b-autonomous.sh      # Night Mode自動ON/終了時解除確認
bash scripts/runtime/lane-b-devcontainer.sh    # Night Mode自動ON/終了時解除確認
```

**Night Modeがバイパスするもの**:
- pvqe-p-gate.py（証拠計画要求）
- pre_edit_task_guard.py（タスクID確認）
- intent-confirm.py

**Night Modeでもバイパスできないもの**（常時有効）:
- north-star-guard.py
- research-gate.py
- vps-ssh-guard.py
- llm-judge.py

---

## まとめ

| 状況 | 推奨Lane | 根拠 |
|------|---------|------|
| 通常の開発作業 | Lane A | hookガードが重要、VS Codeの方が使いやすい |
| 大量タスク・夜間 | Lane B CLI | シンプル、Night Mode込み自動化 |
| 環境分離が必要 | Lane B devcontainer | VPS相当環境、deny listも有効 |
| Lane Aで長時間作業 | Lane A + Night Mode | VS Codeのまま、hookをバイパス |

---

*T019成果物: 2026-03-15 — 実際のワークフローに基づくLane選択ガイド*
