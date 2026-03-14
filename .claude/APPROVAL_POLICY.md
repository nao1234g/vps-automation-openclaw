# APPROVAL_POLICY.md — 意思決定・承認フロー

> **このファイルが全承認フローの唯一の定義。**
> 承認が必要かどうかで迷ったらここを参照する。
> 更新: 変更時は末尾のCHANGELOGに1行追記。

---

## 承認レベルの定義（3段階）

| レベル | 名称 | 要件 | 違反時 |
|--------|------|------|--------|
| **L1** | 自律実行 | 承認不要。即実行してよい | - |
| **L2** | レビュー推奨 | Naotoへの事前通知 + 完了後報告 | 事後承認でOK |
| **L3** | 明示的承認必須 | Naotoの明示的な「GO」が必要 | 物理ブロック（実行不可） |

**判断の原則（Type 1 / Type 2）:**
- **Type 2（可逆的）** = L1または L2 → 自律判断で実行
- **Type 1（不可逆・影響大）** = L3 → 必ずNaotoの承認を取る

---

## L1: 自律実行（承認不要）

> AIは即実行する。事後報告もオプション（必要なら簡潔に）。

| カテゴリ | 具体的なアクション |
|----------|--------------------|
| ローカルファイル編集 | `.py` / `.json` / `.md` の作成・更新（設定外） |
| スクリプト実行 | `--dry-run` / `--report` フラグ付きの読み取り専用実行 |
| リサーチ | WebSearch / WebFetch（情報収集のみ） |
| タスク管理 | task_ledger.json へのタスク追加・ステータス更新 |
| 知識記録 | KNOWN_MISTAKES.md / AGENT_WISDOM.md への追記 |
| VPS読み取り | SSH `cat` / `tail` / `ls` / ログ確認 |
| テスト実行 | `--dry-run` モードのスクリプト |
| 予測DB読み取り | prediction_db.json の参照・分析 |
| Hook追加 | settings.local.json へのPostToolUse hook追加 |

---

## L2: レビュー推奨（事前通知）

> 実行前にNaotoへ「こういう理解でいいですか？」と1行確認。
> Night Modeでは L2 → L1 に自動降格（確認なしで実行）。

| カテゴリ | 具体的なアクション | 理由 |
|----------|--------------------|------|
| VPSファイル変更 | 本番スクリプトの修正・新規作成 | VPS本番環境のため |
| Cronジョブ変更 | 追加・削除・間隔変更 | 副作用が持続するため |
| Ghost記事投稿 | DRAFT/PUBLISHED問わず | 公開コンテンツのため |
| Docker設定変更 | `docker-compose.*.yml` の編集 | サービス停止リスク |
| Ghost CMS設定 | テーマ・コードインジェクション変更 | 全ページに影響 |
| Telegram通知送信 | 実際の通知送信（テスト以外） | Naotoのデバイスに届くため |
| prediction_db.json | 新規予測エントリ追加（APPEND） | 不変記録のため確認推奨 |
| Caddy設定変更 | `/etc/caddy/Caddyfile` の変更 | URL/リダイレクトに影響 |

---

## L3: 明示的承認必須（GOなしで実行禁止）

> 以下のアクションは必ずNaotoから「GO」「やって」「承認」等の明示的な言葉が必要。
> `ui_layout_approved.flag` / `proposal_shown.flag` 等のフラグで物理強制。

| カテゴリ | 具体的なアクション | 物理ブロック機構 |
|----------|--------------------|-----------------|
| **UIレイアウト変更** | `/predictions/` ページのデザイン変更 | `ui-layout-guard.py` |
| **有料API課金** | Anthropic API従量課金・新APIキー契約 | コスト承認フロー |
| **本番DB削除** | Ghost DB / SQLite 削除・テーブル変更 | 実行禁止（手動確認必須） |
| **VPS全体変更** | OSアップグレード・セキュリティ設定変更 | 実行禁止 |
| **外部公開投稿** | X/note/Substack への実際の投稿（手動） | Type 1判断 |
| **サービス停止** | NEO-ONE/TWO/Ghost の停止・再起動 | Telegram確認必須 |
| **prediction_db.json変更** | 既存エントリの修正・削除 | `PROJECT_BIBLE.md` 禁止事項 |
| **NORTH_STAR.md変更** | ミッション・Eternal Directivesの変更 | `north-star-guard.py` |
| **予算超過** | $200/月のClaude Max超え、新サービス契約 | コスト承認フロー |

---

## 承認フロー詳細（UIレイアウト変更の場合）

```
Step 1: ASCIIワイヤーフレームを作成
        → before/after を並べて表示（prediction-design-system.md 参照）

Step 2: proposal_shown.flag を作成
        → touch .claude/hooks/state/proposal_shown.flag

Step 3: Naotoへ提案テキストを送信
        → 「UIレイアウト変更の承認をお願いします: [変更内容]」

Step 4: Naotoから承認を受ける
        → 「やって」「OK」「承認」等の明示的な言葉

Step 5: ui_layout_approved.flag を作成
        → touch .claude/hooks/state/ui_layout_approved.flag

Step 6: 実装する
        → ui-layout-guard.py がフラグを確認してパス
```

---

## Night Mode（自律運転）での例外

Night Mode中（`night_mode.flag`が存在する間）:
- L2 → L1 に降格（確認なしで実行）
- L3 は変更なし（Night Mode中も承認必須）
- AskUserQuestion は完全禁止
- EnterPlanMode は完全禁止

---

## CHANGELOG

| 日付 | 変更内容 |
|------|---------|
| 2026-03-14 | 初版。L1/L2/L3の3段階定義。Type 1/2判断との対応。UIレイアウト変更の詳細フロー。 |
