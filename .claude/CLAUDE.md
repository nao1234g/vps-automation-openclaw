# OpenClaw VPS Automation — CLAUDE.md

> AIエージェントが毎セッション自動読み込みする永続的コンテキスト。
> 更新方法: 「CLAUDE.mdに追記して」と指示するだけ。

---

## 参照優先順位（問題発生時）

1. **`.claude/rules/NORTH_STAR.md`** ← 最優先（Naotoの意図・判断基準）
2. **`docs/KNOWN_MISTAKES.md`** ← 第2優先（実装前に必ず確認）
3. **`docs/AGENT_WISDOM.md`** ← 第3優先
4. 各rulesファイル → `QUICK_REFERENCE.md` → `DEVELOPMENT.md`

---

## Known Mistakes クイックリファレンス（→詳細: docs/KNOWN_MISTAKES.md）

### 最重要の教訓
1. **指示が来たらすぐ動くのではなく「こういう理解でいいですか？」と確認してから動く**
2. **実装前に世界中の実装例を検索する** — GitHub/X/公式ドキュメントで3回以上
3. **機能の存在を推測で語らない** — 公式ドキュメント/APIレスポンスで裏付けを取る
4. **OpenClawの設定変更は openclaw.json で行う**（CLIフラグではない）
5. **フルエージェント（SDK+メモリ+ツール）をステートレスAPIに置き換えない**

### よくあるミス
| 問題 | 解決策 |
|------|--------|
| OpenClaw ペアリングエラー | `openclaw.json`で設定（CLIフラグではない） |
| EBUSY エラー | ディレクトリ単位でマウント、`:ro` なし |
| Gemini モデル名エラー | APIで利用可能モデル名を確認してから設定 |
| N8N API 401 Unauthorized | `X-N8N-API-KEY` ヘッダーで認証 |
| Substack CAPTCHA | Cookie認証（`connect.sid`）に切り替え |
| Neo品質崩壊 | フルエージェント（SDK+メモリ+ツール）をステートレスAPIに置き換えない |
| Notes API 403 | `curl_cffi`（Chrome impersonation）を使う |
| .envパスワード未展開 | 静的な値を設定する |
| source .envが壊れる | cron内ではインラインでAPIキー指定 |
| OpenRouter api:undefined | GLM-5はZhipuAI直接API（`zai/`）を使う |
| NEOをOpenClawに追加 | NEOは別の`claude-code-telegram`サービスで運用 |
| NEO permission_mode エラー | `acceptEdits`を使う（rootでもツール自動承認） |
| NEOが「Claude Code」と名乗る | SDK `system_prompt`パラメータでアイデンティティ注入 |
| NEO OAuthトークンスパム | ローカルPC→VPSへSCPコピー（4時間ごと自動） |
| NEO画像読み込み不可 | 画像をファイル保存→Readツールで読み込み指示 |
| NEO指示を実行しない | system_promptに「メッセージ=実行指示」と明示 |
| Bot APIでNEOに指示が届かない | **Telethon**（User API）で送信する |
| note Cookie認証エラー | 手動Seleniumスクリプトで再ログイン→`.note-cookies.json`更新 |
| note-auto-post.pyがXに二重投稿 | subprocess呼び出しに`--no-x-thread`フラグを追加 |
| X「duplicate content」403 | キューの`tweet_url`フィールドで重複チェック |
| **X API $100/月と言う（古い情報）** | **2026年にサブスク廃止→Pay-Per-Use。検索=Grok API、投稿=X API（$5クレジット）** |
| nowpattern Ghost API 403 | `/etc/hosts`に`127.0.0.1 nowpattern.com`追加、HTTPSでアクセス |
| Ghost API SSLエラー | `verify=False`と`urllib3.disable_warnings()`を追加 |
| Ghost Settings API 501 | SQLite直接更新（`ghost.db`）+ Ghost再起動 |
| Ghost投稿の本文が空 | URLに`?source=html`を追加 |
| NEOがカスタムタグ作成 | 5層防御: validator→publisher→hook→audit→env isolation |
| sync-vps.ps1がVPS修正を上書き | v2.0: バックアップ付き同期 + VPS専用ファイル保護 |
| **UI変更後に「直った」と思い込む** | **変更後は必ず `python3 /opt/shared/scripts/site_health_check.py --quick` を実行。FAIL 0件が出荷基準** |
| **一部修正で関連領域を見落とす** | **変更後はスコープ外も確認: EN/JA両方、pagination、prediction tracker** |
| ENタグ監査で全件FAILと誤検知 | ENタグは `geopolitics`/`crypto` 等（`genre-*` プレフィックスなし）。validator も旧形式を使用 |
| **UIレイアウト承認なし変更** | **承認フロー必須: ASCII mockup → proposal_shown.flag → 承認 → ui_layout_approved.flag** |

---

## 詳細セクション（自動インポート）

> 以下のファイルはClaude Codeが自動的に読み込む。テーブルではなく行単位で記述すること。

@.claude/rules/NORTH_STAR.md
@.claude/rules/execution-map.md
@.claude/rules/agent-instructions.md
@.claude/rules/infrastructure.md
@.claude/rules/content-rules.md
@.claude/rules/prediction-design-system.md

---

## 制約条件

- **VPS**: ConoHa / Ubuntu 22.04 LTS / Docker Compose v2
- **セキュリティ**: UFW拒否デフォルト + Fail2ban + SSH鍵認証のみ
- **本番デプロイ前**: `./scripts/security_scan.sh --all` 必須
- **LLM**: Gemini 2.5 Pro（無料枠）+ Grok 4.1（$5クレジット）
- **課金**: Claude Max $200/月（定額）— Anthropic API従量課金は使用禁止
- **PostgreSQL**: 16-alpine固定 / Node.js: 22-slim

---

*最終更新: 2026-02-27 — NORTH_STAR.md追加、rules/ 9→6ファイルに統合*
