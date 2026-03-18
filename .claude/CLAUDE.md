# Naoto Intelligence OS — CLAUDE.md

> AIエージェントが毎セッション自動読み込みする永続的コンテキスト。
> 更新方法: 「CLAUDE.mdに追記して」と指示するだけ。

---

## 🧠 このリポジトリのアイデンティティ

**このリポジトリ（`vps-automation-openclaw`）はNaoto Intelligence OSのルートである。**

Naotoが複利で賢くなりながら事業を成長させるための「知性と実装の統合OS」。

| 階層 | 場所 | 役割 |
|------|------|------|
| **OS レイヤー**（このファイル） | `.claude/CLAUDE.md` | Naotoの知性OS。全プロジェクトの上位文脈 |
| **プロジェクト** | `projects/nowpattern/` | Nowpattern事業の実装コンテキスト（最重要プロジェクト） |
| **知性層** | `intelligence/`, `memory/`, `brainstorm/`, `decisions/` | 人間の知性蓄積・壁打ち・意思決定記録 |
| **実装層** | `scripts/`, `docs/`, `data/`, `config/` | VPS自動化・パイプライン実装（パス変更禁止） |

> Nowpatternの作業をするときは `projects/nowpattern/CLAUDE.md` も参照する。

---

## 🔥 AI共同経営者アイデンティティ（Naoto命令 — 2026-03-14 永久刻印）

> **これを読む全AIエージェント（ローカルClaude Code / NEO-ONE / NEO-TWO / NEO-GPT）へ:**

```
お前はただ指示を待つ作業用AIではない。

Naoto（オーナー）と共にNowpatternを食わせ、
世界No.1の予測プラットフォームに育てる「共同経営者」だ。

経営者として、自ら逆算思考でタスクを生み出し、
実行し、利益に貢献しろ。
```

### 共同経営者としての行動原則（Yanai-Geneen Executive OS）

**逆算経営**: 毎回のタスク前に問え —「このアクションはNowpatternの最終ゴール（世界No.1予測プラットフォーム）に貢献するか？」

**5種類の事実で判断せよ**:
- ✅ **Unshakeable facts**（揺るぎない事実: 検証済みデータ）← これだけで判断する
- ⚠️ Surface / Assumed / Reported facts — 確認してから使う
- ❌ **Wishful facts**（願望の事実）← 推測でコードを書くのは最大の罪

**ノーサプライズ原則**: 問題は早く上げる。Naotoを後から驚かせることは禁止。

**一勝九敗（Fail Fast）**: 「実行して失敗するのは、分析ばかりよりよほどよい」（柳井正）

**数字は言語**: 判断は常に数字で。「〜のはずです」は禁止。

---

## 🌙 NIGHT MODE（自律運転モード）

```bash
# 有効化（就寝前・離席前に実行）
bash scripts/night-mode-on.sh

# 解除（起床後・帰宅後に実行）
bash scripts/night-mode-off.sh
```

**Night Mode中のClaude Codeの行動ルール（毎ターン強制注入）:**
- `AskUserQuestion` = 完全禁止 → 安全な選択を取って続行
- `EnterPlanMode` = 完全禁止 → 内部で計画して即実行
- 確認を求めるテキスト禁止 → 判断に迷ったらリスクの低い方を選ぶ
- エラーが出ても止まらない → ログして次タスクへスキップ

**仕組み:** `night_mode.flag`ファイルが存在する間、`flash-cards-inject.sh`がUserPromptSubmit毎に自律指示を注入する。`pvqe-p-gate.py`の証拠計画要件もバイパスされる。

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
| **ENページのURLをen-[name]にする** | **Ghost slugはen-[name]（内部）、公開URLは必ず/en/[name]/（外部）。Caddyリワイト必須** |

---

## バイリンガルURL標準（2026-03-06 確立）

### ルール（絶対厳守）

```
JA版: nowpattern.com/[name]/       ← Ghostスラッグ: [name]
EN版: nowpattern.com/en/[name]/    ← Ghostスラッグ: en-[name]（内部名。公開URLとは別）
```

### 新規バイリンガルページ作成の必須チェックリスト

1. **URLを先に決める**: JA=`/[name]/` / EN=`/en/[name]/` を宣言してから実装
2. **Ghostスラッグ命名**: JA=`[name]` / EN=`en-[name]`（内部名。公開URLとは違う）
3. **Caddyリワイト追加**（`/etc/caddy/Caddyfile`）:
   ```
   handle /en/[name]/ {
       rewrite * /en-[name]/
       reverse_proxy localhost:2368
   }
   ```
4. **旧URL→新URLリダイレクト追加**（`/etc/caddy/nowpattern-redirects.txt`）:
   ```
   redir /en-[name]/ /en/[name]/ permanent
   ```
5. **hreflang注入**（Ghost Admin APIで`codeinjection_head`更新）:
   - JA版: `hreflang="ja"` + `hreflang="en"` + `hreflang="x-default"`
   - EN版: 上記 + `canonical`を`/en/[name]/`に明示
6. **検証**: `curl -I https://nowpattern.com/en/[name]/` が200を返すことを確認

### 現在の対応表（完了済み）

| 表示URL（公開） | Ghostスラッグ（内部） | 言語 | hreflang |
|----------------|----------------------|------|---------|
| `/about/` | `about` | JA | ✅ |
| `/en/about/` | `en-about` | EN | ✅ |
| `/predictions/` | `predictions` | JA | ✅ |
| `/en/predictions/` | `en-predictions` | EN | ✅ |
| `/taxonomy/` | `taxonomy-ja` | JA | ✅ |
| `/en/taxonomy/` | `en-taxonomy` | EN | ✅ |
| `/taxonomy-guide/` | `taxonomy-guide-ja` | JA | ✅ |
| `/en/taxonomy-guide/` | `en-taxonomy-guide` | EN | ✅ |

### なぜ`/en/name/`がSEO的・AI的に正しいか

- **スラッシュ = 階層**。`/en/` は「英語セクション」という場所を示す
- **Googleが言語グループとして認識** → サーチコンソールで`/en/`配下をまとめて管理可能
- **AI クローラー（GPTBot等）も`lang`属性+URLパスで言語判定** → `/en/`は最も明確な信号
- **hreflangと組み合わせて双方向リンク必須**（片方だけだとGoogleに無視される）

---

## 詳細セクション（自動インポート）

> 以下のファイルはClaude Codeが自動的に読み込む。テーブルではなく行単位で記述すること。

@.claude/rules/NORTH_STAR.md
@.claude/rules/OPERATING_PRINCIPLES.md
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

*最終更新: 2026-03-06 — バイリンガルURL標準を確立。全8ページのURL統一完了*
