# PRIVACY POLICY — Private/Public 境界設計

> **このファイルは「何が private で何が public か」の唯一の定義。**
> 全 AI エージェント・全スクリプト・全 hook がこのファイルを参照する。
> 変更時は末尾 CHANGELOG に追記すること。

---

## 3層ゾーン分類

### ZONE 0: ULTRA PRIVATE（絶対非公開）

git に入れない。OneDrive 同期からも除外推奨。

| パス | 内容 | 理由 |
|------|------|------|
| `.env`, `.env.local`, `.env.*.local` | API キー・トークン・DB 接続 | 秘密情報 |
| `secrets.txt` | 秘密ハッシュ | 秘密情報 |
| `.claude/memory/` | AI セッション記録・ChromaDB | 思考履歴 |
| `.claude/state/` | AI 実行状態・失敗記録 | 内部状態 |
| `.claude/projects/` | Claude Code プロジェクト状態 | 内部状態 |
| `.claude/plans/` | Claude Code 計画ファイル | 内部状態 |
| `*.credentials.json` | OAuth トークン | 秘密情報 |
| `*.pem`, `*.key` | SSL 証明書・秘密鍵 | 秘密情報 |

### ZONE 1: PRIVATE（git 管理するが public repo には置かない）

repo が public の間は .gitignore で除外する。repo が private になれば解除可能。

| パス | 内容 | 理由 |
|------|------|------|
| `founder_memory/` | 創業者の意思決定記録・哲学 | 経営戦略 |
| `brainstorm/` | 壁打ちセッション記録 | 未確定アイデア |
| `decisions/` | 意思決定ログ | 経営判断 |
| `intelligence/` | 市場・競合分析 | 戦略情報 |
| `docs/NOWPATTERN_STRATEGY_*.md` | 四半期戦略書 | 事業戦略 |
| `docs/NOWPATTERN_STRATEGIC_PROPOSALS.md` | 戦略提案書 | 事業戦略 |
| `docs/KNOWN_MISTAKES.md` | エラー履歴（170KB） | 知的資産 |
| `docs/BACKLOG.md` | 機能ロードマップ | 競争優位 |
| `.claude/rules/infrastructure.md` | VPS IP・NEO 設定 | インフラ秘密 |

### ZONE 2: PUBLIC（公開可能）

git 管理 + public repo に置いて問題ない。

| パス | 内容 |
|------|------|
| `scripts/` | 自動化スクリプト（配信生成エンジン） |
| `apps/` | Web アプリケーション |
| `prediction_engine/` | 予測アルゴリズム |
| `.claude/hooks/` （state/ 除く） | ガードエンジン |
| `.claude/rules/` （infrastructure.md 除く） | 運用原則 |
| `docker-compose*.yml` | インフラ定義 |
| `config/` （APIキーが .env 参照であること） | 設定テンプレート |

---

## PUBLIC_OK ルール

**明示的な `PUBLIC_OK` 承認がない限り、ZONE 0/1 のデータを public surface に含めてはならない。**

### public surface の定義

- Ghost CMS に投稿される記事・ページ
- X (@nowpattern) に投稿されるツイート
- note に投稿される記事
- Substack に配信されるニュースレター
- /predictions/ ページの HTML
- GitHub にプッシュされるコミット
- API レスポンス（reader_prediction_api 等）
- sitemap.xml, RSS feed, robots.txt

### 混入禁止パターン

以下の内容が public surface に含まれている場合、自動ブロックする:

```
BLOCKED_PATTERNS:
  - founder_memory/ 配下のファイル内容
  - brainstorm/ 配下のファイル内容
  - decisions/ 配下のファイル内容
  - intelligence/ 配下のファイル内容
  - .claude/memory/ 配下のファイル内容
  - .claude/state/ 配下のファイル内容
  - docs/*STRATEGY* のファイル内容
  - docs/KNOWN_MISTAKES.md の内容
  - docs/BACKLOG.md の内容
  - secrets.txt の内容
  - .env の内容（API キー・トークン）
  - Naoto の個人メールアドレス
  - VPS の IP アドレス（163.44.124.123）
  - Telegram Bot Token
  - OAuth トークン
```

### AI エージェントへの強制

```
全 AI エージェント（ローカル Claude Code / NEO-ONE / NEO-TWO / NEO-GPT）は:

1. 記事生成時に ZONE 0/1 のファイルを「ソース」として引用しない
2. X 投稿に ZONE 0/1 の内容を含めない
3. Telegram 通知に ZONE 0/1 のファイル内容をそのまま貼り付けない
   （サマリー・数値のみ許可）
4. git commit 前に private-leak-checker.py を実行する
5. 「壁打ちで話した内容」を記事に反映する場合、PUBLIC_OK 承認を得る
```

---

## パイプライン安全性（確認済み）

以下の公開物生成パイプラインは ZONE 0/1 からの読み込みがないことを確認済み（2026-03-25 監査）:

| パイプライン | 入力ソース | ZONE 0/1 参照 |
|------------|-----------|--------------|
| `nowpattern_publisher.py` | `nowpattern_taxonomy.json` | なし |
| `prediction_page_builder.py` | `prediction_db.json`, `embed_data.json` | なし |
| `x-auto-post.py` | CLI 引数 | なし |
| `x_swarm_dispatcher.py` | CLI 引数 | なし |
| `substack_notes_poster.py` | `prediction_db.json` | なし |

---

## Claude Code テレメトリ / データ送信経路

Claude Code はユーザーの会話コンテキストを以下の外部エンドポイントに送信する:

| 送信先 | 内容 | 制御方法 |
|--------|------|---------|
| **Anthropic API** (`api.anthropic.com`) | 全プロンプト + コンテキスト | Claude Max 利用に必須（停止不可） |
| **Statsig** (`featureassets.org`, `prodregistryv2.org`) | 使用状況メトリクス | `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` |
| **Sentry** (`sentry.io`) | エラーレポート | `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` |
| **Undocumented** (`142.251.x.x` Google IP) | 不明 | `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` |

### 推奨設定

```bash
# 非必須のテレメトリを無効化（Windows 環境変数 or .bashrc に追加）
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

### データ保持期間（Anthropic公式）

- **通常会話**: 30 日間保持（training toggle OFF の場合）
- **training toggle ON**: 最大 5 年間保持
- **`/feedback` コマンド**: 送信された全トランスクリプトは 5 年間保持（toggle 関係なし）

### .claudeignore ファイル

`.claudeignore` は Claude Code の公式機能で、指定されたファイルを Claude のコンテキストから除外する。
本リポジトリでは ZONE 0/1 ファイルを `.claudeignore` に登録し、Claude が読み込めないようにしている。

- ファイル: `/.claudeignore`（リポジトリルート）
- 構文: `.gitignore` と同一
- 効果: Claude Code の Read/Write/Edit ツールがこれらのファイルにアクセスできなくなる

---

## OneDrive 同期リスク

リポジトリが `C:\Users\user\OneDrive\デスクトップ\` 配下にあるため、全ファイルが Microsoft クラウドに同期されている。

### 影響を受けるファイル

- `.claude/memory/` — AI セッション記録・ChromaDB
- `.claude/state/` — AI 実行状態（failure_memory.json 等）
- `founder_memory/`, `brainstorm/`, `decisions/`, `intelligence/`

### 対処方法

→ `docs/HIGH_RISK_RUNBOOK.md` の「操作4」を参照

---

## 多層防御アーキテクチャ

```
Layer 1: .gitignore          — ZONE 0/1 ファイルの新規追加をブロック
Layer 2: .claudeignore       — Claude Code からの読み込みをブロック
Layer 3: pre-commit hook     — private-leak-checker.py がコミットをブロック
Layer 4: private-leak-checker.py — CRITICAL/HIGH 違反を検出・ブロック
Layer 5: PRIVACY_POLICY.md   — ゾーン分類・ルールの定義（このファイル）
Layer 6: HIGH_RISK_RUNBOOK.md — 高リスク操作の手順書（オーナー判断）
```

**Layer 1-4 はコードで強制。Layer 5-6 はドキュメント（参照用）。**

---

## CHANGELOG

| 日付 | 変更内容 |
|------|---------|
| 2026-03-25 | 初版。3 層ゾーン分類・PUBLIC_OK ルール・混入禁止パターンを定義 |
| 2026-03-25 | v2: Claude Code テレメトリ棚卸し、.claudeignore、OneDrive リスク、多層防御アーキテクチャ追加 |
