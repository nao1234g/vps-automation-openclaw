# VS Code Extension の既知制約

> **このファイルの目的**: VS Code拡張でできること/できないことを正直に記述する。
> 「できない」と思ったことが実は「設定次第でできる」ケースもある。
> 最終更新: 2026-03-15 (T018)

---

## TL;DR（30秒まとめ）

| 制約 | 現実 |
|------|------|
| `--dangerously-skip-permissions` フラグ | VS Code拡張では**使えない**（CLI専用） |
| `bypassPermissions`設定 | settings.local.jsonで**すでに設定済み** |
| hookブロック(exit 2) | パーミッションモードに関係なく**発動する** |
| 夜間自律実行 | Night Mode(`bash scripts/night-mode-on.sh`)で**可能** |

---

## VS Code Extension でできること

### ✅ パーミッションモードの設定

`.claude/settings.local.json`（またはsettings.json）の`defaultMode`で制御:

```json
// 現在Naotoの設定（settings.local.json）
{ "defaultMode": "bypassPermissions" }
```

これにより:
- Edit/Writeの確認ダイアログ → **なし**
- Bashの確認ダイアログ → **なし**
- 効果: CLIの`--dangerously-skip-permissions`と同等

### ✅ hookの動作（全hook有効）

VS Code拡張でも全hook（PreToolUse/PostToolUse/Stop等）は正常に動作する。
hookが`exit 2`を返せばツール実行は停止する。

### ✅ Night Modeの有効化

VS Code内のターミナルから:
```bash
bash scripts/night-mode-on.sh
```
これで`pvqe-p-gate`と`pre_edit_task_guard`がバイパスされる。

### ✅ 追加ディレクトリアクセス

`settings.local.json`の`additionalDirectories`で拡張:
```json
{
  "additionalDirectories": ["\\tmp", "c:\\tmp", "C:\\Users\\user\\AppData\\Roaming\\Code\\User"]
}
```

---

## VS Code Extension でできないこと

### ❌ `--dangerously-skip-permissions` フラグ

CLIでは:
```bash
claude --dangerously-skip-permissions  # 動作する
```

VS Code拡張では:
- GUIからこのフラグを渡す方法が**存在しない**
- ただし`settings.local.json`の`bypassPermissions`で同等の効果が得られる

### ❌ 複数の設定プロファイル切り替え

VS Code拡張は起動時に設定を読み込み、セッション中の動的切り替えができない。
→ CLI版なら `claude --permission-mode acceptEdits` のように指定できる

### ❌ セッション外部からの権限変更

実行中のVS Codeセッションに対して外部から`bypassPermissions`を注入できない。
→ 設定ファイルを変更して**再起動が必要**

---

## 現在の設定状態（Phase 0監査結果）

```
.claude/settings.json      → defaultMode: acceptEdits  (共有、git管理)
.claude/settings.local.json → defaultMode: bypassPermissions (ローカル専用、gitignored)
```

**Naotoの環境では `settings.local.json` が優先され、bypassPermissionsが有効。**

つまり現状でVS Codeの確認ダイアログは**なし（T019実測確認済み: 2026-03-15）**。
Bash/Edit/Read全てダイアログなしで即実行されることを実際に計測済み。
残る「摩擦」はhookガードによるblockであり、意図的な安全装置。

---

## 残る摩擦の分類

```
摩擦の種類         消し方                   消すべきか
─────────────────────────────────────────────────────
UI確認ダイアログ   bypassPermissions       ✅ 既に設定済み
pvqe_p.json要求   Night Mode              ✅ 長期作業時に有効化
task_id要求       Night Mode              ✅ 長期作業時に有効化
research-gate     WebSearch 1回実行       ✅ 調査してから実装
north-star保護    消せない（設計上）       ❌ 消すべきでない
VPS SSH guard     消せない（設計上）       ❌ 消すべきでない
```

---

## devcontainer でのClaude Code設定

現在の `.devcontainer/devcontainer.json` にはClaude Code設定がない。
追加するには `customizations.claude` セクションを追加:

```json
{
  "customizations": {
    "claude": {
      "permissions": {
        "defaultMode": "bypassPermissions"
      }
    }
  }
}
```

**ただし公式サポートされた書式は要確認。** devcontainer内での設定は`.claude/settings.json`を編集する方が確実。

---

*最終更新: 2026-03-15 — T018: Phase 0監査の正直な記録。「できない」を推測ではなく確認から記述。*
