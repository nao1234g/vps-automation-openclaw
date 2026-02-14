# OpenClaw VPS Automation — CLAUDE.md

> このファイルはAIエージェント（Claude Code / Copilot）が毎セッション自動読み込みする永続的コンテキストです。
> コードレビューやバグ修正のたびに更新してください。更新方法: 「CLAUDE.mdに追記して」と指示するだけ。

---

## 1. Architecture Rules（アーキテクチャルール）

### プロジェクト概要
- **目的**: OpenClaw AI Agent + N8N + OpenNotebook のセキュアなVPSデプロイシステム
- **技術スタック**: Docker Compose, PostgreSQL 16, Node.js 22, Nginx, Bash, Terraform, Helm
- **設計思想**: 10層セキュリティ防御、自動運用、冪等性

### Docker Compose構成（重要: 使い分け）
| ファイル | 用途 | サービス |
|---|---|---|
| `docker-compose.minimal.yml` | 開発テスト | PostgreSQL + OpenNotebook + N8N |
| `docker-compose.dev.yml` | フル開発環境 | 上記 + OpenClaw + Adminer |
| `docker-compose.quick.yml` | ワンコマンド起動 | PostgreSQL + OpenClaw + N8N |
| `docker-compose.production.yml` | 本番 | 全サービス + Nginx SSL |
| `docker-compose.monitoring.yml` | 監視 | Prometheus + Grafana |

### サービス通信パターン
- Internet → Nginx (443/80) → Backend services（フロントネットワーク）
- OpenClaw / N8N / OpenNotebook / PostgreSQL（内部ネットワーク、外部非公開）
- OpenClaw → N8N: `http://n8n:5678`（Docker内部DNS）
- OpenClaw → OpenNotebook: `http://opennotebook:8080`
- 全サービス → PostgreSQL: スキーマ分離（`n8n`, `openclaw`, `opennotebook`）

### OpenClaw Gateway 設定
- **設定ファイル**: `config/openclaw/openclaw.json`（Docker Composeでマウント）
- **entrypoint**: `docker/openclaw/entrypoint.sh`（Gateway起動スクリプト）
- **認証方式**: `--password` フラグでトークン認証
- **ポート**: 3000（WebSocket）
- **バインド**: `lan`（Docker内部ネットワーク）

### セキュリティルール（絶対に守ること）
- 全コンテナ: 非root実行（`USER appuser`, UID 1001）
- 全コンテナ: `security_opt: [no-new-privileges:true]`
- ポートバインド: `127.0.0.1` のみ（Nginx以外）
- スクリプト: `set -e` + 入力バリデーション + `--dry-run` 対応
- Docker: ヘルスチェック必須、リソース制限必須

### ファイル命名規則
- スクリプト: `scripts/*.sh`（全て defensive bash）
- Docker設定: `docker/<service>/`
- DB初期化: `docker/postgres/init/*.sql`（番号順で実行）
- スキル: `skills/*.js`（ボリュームマウント、再起動不要）
- ドキュメント: ルートに大文字MD（`ARCHITECTURE.md` 等）

### コードスタイル
- Bash: カラーログ（RED/GREEN/YELLOW）、冪等チェック、エラーハンドリング
- Dockerfile: マルチステージビルド、`npm ci`（`npm install` 禁止）、Alpine/Slimベース
- Docker Compose: 環境変数にデフォルト値を設定（`${VAR:-default}`）
- 設定変更: `.env.example` と実際のCompose両方を更新すること

---

## 2. Known Mistakes（既知のミスと教訓）

### 2026-02-11: OpenClaw Control UI ペアリング問題
- **症状**: ブラウザからControl UI接続時に `disconnected (1008): pairing required` エラー
- **根本原因**: OpenClaw GatewayはデフォルトでWebSocket接続にデバイスペアリングを要求する
- **誤ったアプローチ**:
  - `--no-pairing` CLIフラグ → OpenClaw CLIにこのオプションは**存在しない**
  - `entrypoint.sh` で環境変数から `--no-pairing` を動的追加 → 動作しない
  - Docker Compose に `OPENCLAW_DISABLE_PAIRING` 環境変数を追加 → Gateway が認識しない（OpenClaw独自の環境変数ではない）
- **正しい解決策**: `openclaw.json` 設定ファイルで以下を設定:
  ```json
  {
    "gateway": {
      "controlUi": {
        "allowInsecureAuth": true,
        "dangerouslyDisableDeviceAuth": true
      }
    }
  }
  ```
- **デプロイ方法**: `config/openclaw/openclaw.json` をDocker Composeでマウント:
  ```yaml
  volumes:
    - ./config/openclaw/openclaw.json:/home/appuser/.openclaw/openclaw.json:ro
  ```
- **教訓**:
  1. OpenClawの設定変更はCLIフラグや環境変数ではなく、**openclaw.json設定ファイル**で行う
  2. Docker Compose環境変数を追加する前に、対象ソフトウェアがその環境変数を認識するか確認する
  3. `:ro`（read-only）マウントすると Gateway がプラグイン設定を書き込めず `EBUSY` エラーが出る → 許容するか `:ro` を外す

### 2026-02-11: read-only マウントによる EBUSY エラー
- **症状**: `failed to persist plugin auto-enable changes: Error: EBUSY: resource busy or locked`
- **原因**: `openclaw.json` を `:ro` でマウントしているため、Gateway が設定を更新できない
- **影響**: Gateway自体は正常に動作するが、プラグインの自動設定変更が永続化されない
- **対策**: 機能上問題なければ `:ro` のまま許容。プラグイン管理が必要なら `:ro` を外す

### 2026-02-12: Telegram接続 & EBUSY完全解決
- **症状**: Telegram Bot Token を設定しても「Telegram configured, not enabled yet.」のまま有効化されない
- **根本原因**: `openclaw.json` が単一ファイルでバインドマウント（`:ro`）されており、`openclaw doctor --fix` が設定を書き込めない
- **解決までの道のり**:
  1. `:ro` を削除 → まだ EBUSY（単一ファイルマウントでは rename 操作が不可）
  2. ディレクトリマウントに変更 (`./config/openclaw:/home/appuser/.openclaw`) → EACCES（権限不足）
  3. `chown 1000:1000` + `chmod 777` → `openclaw doctor --fix` 成功
  4. doctor が `plugins.entries.telegram.enabled: false` で追加 → 手動で `true` に変更
  5. Telegram 接続後、ペアリング承認が必要 → `openclaw pairing approve telegram <code>`
- **正しいマウント方式**:
  ```yaml
  volumes:
    - ./config/openclaw:/home/appuser/.openclaw  # ディレクトリ単位、:ro なし
  ```
- **教訓**:
  1. OpenClaw はプラグイン管理のため設定ディレクトリに**書き込み権限が必要**
  2. 単一ファイルのバインドマウントでは rename（アトミック書き込み）が失敗する → **ディレクトリ単位でマウント**すること
  3. `openclaw doctor --fix` はプラグイン有効化の正規手段。ただし `enabled: false` で追加されることがあるので確認が必要
  4. Telegram 接続には Bot Token 設定 → doctor --fix → ペアリング承認 の3ステップが必要

### 2026-02-12: Gemini モデル名の不一致
- **症状**: `Error: No API key found for provider "google"` → 解決後も Telegram で「gemini-cheap」しか使えない
- **根本原因**: 2つの問題が重なっていた
  1. VPS の `.env` に `GOOGLE_API_KEY` が未設定（追加で解決）
  2. `openclaw.json` のモデル名 `google/gemini-2.5-pro-preview-05-06` が存在しないモデル名
- **正しいモデル名**: `google/gemini-2.5-pro`、`google/gemini-2.5-flash`（preview 接尾辞なし）
- **確認方法**: `curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${GOOGLE_KEY}"` で利用可能モデル一覧を取得
- **教訓**: Google は preview モデルの名称を頻繁に変更・廃止する。設定前に API で利用可能なモデル名を確認すること

### 2026-02-14: SSH復旧 & Control UI トークン認証
- **SSH復旧**: cloud-initが `/etc/ssh/sshd_config.d/50-cloud-init.conf` で `PasswordAuthentication no` を上書きしていた → `yes` に変更して解決
- **Control UI接続**: `dangerouslyDisableDeviceAuth: true` でもデバイス認証が要求される
- **正しい解決策**: URLにトークンを付与 `http://host:port/?token={GATEWAY_TOKEN}`（GitHub issue #8529）
- **entrypoint.sh**: `--password` フラグを削除（CLIフラグではなくJSON設定で認証制御）
- **教訓**:
  1. cloud-init の sshd_config.d 配下のファイルがメインの sshd_config を上書きする
  2. OpenClaw Control UIのトークン認証はURLパラメータで渡す
  3. SSHトンネル: `ssh -i key -f -N -L 8081:localhost:3000 root@VPS`

### 2026-02-14: N8N API アクセス & ワークフロー
- **N8N API認証**: `X-N8N-API-KEY` ヘッダーが必須。Basic Auth では通らない
- **APIキー生成**: N8N Web UIまたはREST APIの `/rest/api-keys` で生成（scopes + expiresAt 必須）
- **N8Nオーナーセットアップ**: DB直接操作で可能（email, password をbcryptハッシュで設定）
- **ワークフロー実行**: 公開API (`/api/v1/`) にはワークフロー実行エンドポイントがない → スケジュール実行で対応
- **環境変数**: N8Nコンテナにも `GOOGLE_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` を渡す必要あり
- **OpenClawにはREST APIがない**: エージェントチャットはWebSocket専用。N8NからOpenClawエージェントを直接呼び出す方法はない
- **教訓**:
  1. N8N → OpenClawエージェント呼び出しは不可。N8NからLLM APIを直接呼ぶ設計にする
  2. Telegram `sendMessage` API はOpenClawの `getUpdates` と競合しない（送信と受信は別）
  3. N8Nのワークフロー手動実行は公開APIからはできない

### 2026-02-14: ペルソナファイルの仕組み
- **システムプロンプト**: `openclaw.json` のJSON設定ではなく `personas/{agent-id}.md` ファイルで定義
- **ワークスペース**: `workspace/` ディレクトリに SOUL.md, USER.md, AGENTS.md 等が存在
- **無効なキー**: `systemPrompt`, `instructions`, `identity.description` はすべて OpenClaw config で拒否される
- **有効なキー**: `id`, `model`, `identity` (name, emoji のみ), `default`

### 2026-02-14: sessions_spawn の pairing required エラー
- **症状**: Jarvis が Telegram 経由で sessions_spawn を使って Alice に仕事を振ろうとすると「pairing required」エラー
- **追加症状**: `openclaw doctor` も `openclaw devices list` も同じ pairing required で接続不可
- **根本原因**: Docker コンテナ内の CLI デバイス (`~/.openclaw/identity/device.json`) が Gateway に未登録。`~/.openclaw/devices/paired.json` が空 `{}`
- **鶏と卵の問題**: `openclaw pairing approve` も Gateway 接続が必要なので、CLI からは承認不可能
- **正しい解決策**: `paired.json` に手動でデバイスを登録（Node.js スクリプトで）
  1. `pending.json` からデバイス情報を取得
  2. `paired.json` にデバイスID をキーとしてエントリを追加（approvedAt, label 付き）
  3. `pending.json` を `{}` にクリア
  4. Gateway を再起動（`docker restart openclaw-agent`）
- **entrypoint.sh の変更**: Gateway 起動時に `--auth token --token "${OPENCLAW_GATEWAY_TOKEN}"` を明示的に指定
- **教訓**:
  1. OpenClaw Gateway はデバイス認証とトークン認証が**別レイヤー**で動く。トークンだけでは不十分
  2. `controlUi.dangerouslyDisableDeviceAuth` は Control UI のみに効く。CLI やサブエージェントには効かない
  3. `paired.json` はディレクトリマウント上にあるので、コンテナ再起動でも保持される
  4. サブエージェントは親セッションの接続を継承する（公式ドキュメントより）ので、親の認証が通れば spawn は動く

### 一般的な落とし穴
- **PostgreSQL init スクリプト**: 初回起動時のみ実行。再実行するにはボリューム削除が必要
- **Docker Compose ファイルの選択ミス**: 変更を加えた yml と実際に起動している yml が異なるケースが頻発。`docker compose ps` で確認すること
- **entrypoint.sh の変更**: ファイル修正後は `docker compose up -d --build` が必要（`restart` では反映されない）
- **環境変数のデフォルト値**: `${VAR}` と `${VAR:-default}` の違いに注意。前者は未設定時に空文字、後者はデフォルト値が入る

---

## 2.5. Neo Architecture（Telegram経由Claude Code）

### 概要
- **名前**: Neo（通称 "Claude Brain"）
- **モデル**: Claude Opus 4.6
- **実行環境**: VPS上で `claude-code-telegram` サービスとして稼働
- **アクセス方法**: Telegram bot `@claude_brain_nn_bot`（ユーザーのスマホから直接対話可能）
- **役割**: CTO・戦略パートナー（Jarvisチームとは独立、より高レベルの意思決定を担当）

### アーキテクチャ
```
User (Telegram) → @claude_brain_nn_bot → neo-telegram.service (VPS)
                                              ↓
                                        Claude Code (SDK)
                                              ↓
                                        Claude Opus 4.6 API
                                              ↓
                                        VPS filesystem (/opt)
                                              ↓
                                        Shared folder: /opt/shared/reports/
                                              ↑
                                        OpenClaw container (/shared)
                                              ↑
                                        Jarvis (レポート書き込み)
```

### 重要な設定
- **作業ディレクトリ**: `/opt`（`APPROVED_DIRECTORY`環境変数で設定）
- **CLAUDE.md**: `/opt/CLAUDE.md` → `/opt/claude-code-telegram/CLAUDE.md` へのシンボリックリンク
- **アイデンティティ**: CLAUDE.mdで "Neo" として定義（Claude Codeが起動時に読み込む）
- **セッション永続化**: `/opt/.claude/projects/` にセッション履歴保存
- **プログレス表示**: 改良版orchestrator.py（経過時間 + フェーズラベル表示）

### Jarvis↔Neo通信
- **共有フォルダ**: `/opt/shared/reports/`（ホスト側）= `/shared/reports/`（コンテナ内）
- **権限**: `chmod 777`（コンテナUID 1001とホストrootの両方が読み書き可能）
- **フロー**:
  1. Jarvisがタスク完了時に `/shared/reports/YYYY-MM-DD_タスク名.md` に書き込み
  2. Neoが `/opt/shared/reports/` を読んで内容確認
  3. NeoがユーザーにTelegram経由で報告

### ローカルClaude Code との役割分担
- **Neo（VPS）**: VPSファイル操作、Docker操作、N8N操作、Jarvisへの指示、戦略立案
- **ローカルClaude Code**: ローカルファイル編集、CLAUDE.md更新、git操作、設計レビュー
- **衝突回避**: 両者が同時にVPSの同じファイル・サービスを触らないこと（役割を明確に分ける）

### 制約
- **Claude APIコスト**: Opus 4.6は高額（$15/1M input tokens, $75/1M output tokens）
- **レート制限**: 1分間に4リクエスト、1日に1,000リクエスト（Tier 1）
- **getUpdates競合**: OpenClawのTelegram統合とは別botを使用（競合なし）

---

## 3. Constraints（制約条件）

### セキュリティ制約
- SSH: 鍵認証のみ、パスワード認証無効、root ログイン禁止
- コンテナ: capability drop ALL、no-new-privileges、非root実行
- ネットワーク: UFW デフォルト拒否、Fail2ban 有効
- SSL/TLS: Let's Encrypt、TLS 1.2以上、強力な暗号スイート
- 本番デプロイ前: `./scripts/security_scan.sh --all` 必須

### インフラ制約
- VPS: ConoHa（メイン対象）
- OS: Ubuntu 22.04 LTS
- Docker: 最新安定版 + Compose v2
- PostgreSQL: 16-alpine（互換性のため固定）
- Node.js: 22-slim（OpenClaw要件）

### コスト制約
- LLM API: Google Gemini 2.5 Pro/Flash（無料枠で運用）、xAI Grok 4.1（$5購入済み）
- サブスク別: Google AI Pro（¥2,900/月）はAntigravity用、Claude Max（$200/月）はClaude Code用。**いずれもAPI料金とは別**
- バックアップ: ローカル保持30日（リモートはオプション）
- 監視: Prometheus + Grafana（セルフホスト、追加コストなし）

### パフォーマンス制約
- 全サービスにリソース制限（`mem_limit`, `cpus`）必須
- ヘルスチェック: 全コンテナに設定、`start_period` を十分に確保（OpenClawは120s）
- PostgreSQL: UTF8 + locale=C（パフォーマンス最適化）

---

## 4. Current State（現在の状態）

### 動作中の構成（2026-02-15時点）
- **使用中Compose**: `docker-compose.quick.yml`
- **VPS**: ConoHa 163.44.124.123（Caddy リバースプロキシ）
- **コンテナ**: 3サービス healthy（openclaw-agent, postgres, n8n）
- **Gateway**: ws://0.0.0.0:3000 でリッスン中（トークン認証 + デバイスペアリング済み）
- **Telegram**: `@openclaw_nn2026_bot` 接続済み・ペアリング承認済み
- **エージェント**: 8人体制（Gemini 2.5 Pro/Flash + xAI Grok 4.1）
- **sessions_spawn**: Jarvis → 他7エージェントへの委任設定済み（`tools.allow` + `subagents.allowAgents`）
- **SSH**: 復旧済み（ed25519鍵認証 + パスワード認証）
- **Control UI**: SSHトンネル経由でアクセス可能 (`localhost:8081/?token=...`)
- **N8N**: 13ワークフロー稼働中（AISA自動化パイプライン + Morning Briefing）
- **Neo**: Claude Opus 4.6 via Telegram（VPS上でClaude Code稼働）
- **Jarvis↔Neo通信**: `/opt/shared/reports/` 経由で双方向連携

### AIエージェント構成（9人）
| # | 名前 | 役割 | モデル | プラットフォーム |
|---|------|------|--------|-----------------|
| 1 | 🎯 Jarvis | 戦略・指揮（DEFAULT） | google/gemini-2.5-pro | OpenClaw |
| 2 | 🔍 Alice | リサーチ | google/gemini-2.5-pro | OpenClaw |
| 3 | 💻 CodeX | 開発 | google/gemini-2.5-pro | OpenClaw |
| 4 | 🎨 Pixel | デザイン | google/gemini-2.5-flash | OpenClaw |
| 5 | ✍️ Luna | 執筆 | google/gemini-2.5-pro | OpenClaw |
| 6 | 📊 Scout | データ処理 | google/gemini-2.5-flash | OpenClaw |
| 7 | 🛡️ Guard | セキュリティ | google/gemini-2.5-flash | OpenClaw |
| 8 | 🦅 Hawk | X/SNSリサーチ | xai/grok-4.1 | OpenClaw |
| 9 | 🧠 Neo | CTO・戦略パートナー | claude-opus-4.6 | Telegram (Claude Code) |

### コスト状況
- Gemini API: **無料枠**で運用中（追加コストなし）
- xAI API: **$5 購入済み**（約50〜70回のフルリサーチ分）
- Google AI Pro サブスク: ¥2,900/月（Antigravity用、API とは別）
- Claude Max: $200/月（Claude Code用、API とは別）

### 完成プロジェクト
- [x] **AISA（Asia Intelligence Signal Agent）** — アジア暗号資産ニュースレター自動化システム
  - PostgreSQL `aisa` スキーマ（5テーブル）
  - N8N 13ワークフロー（データ収集・レポート生成・監視・バックアップ）
  - コンテンツ20+ファイル（ローンチ記事、レポート6本、SEO設計、収益化設計）
  - 24時間自動稼働（規制ニュース、市場データ、SNSシグナル収集）
  - 月額コスト: ¥0（全て無料APIとセルフホスト）
  - 設計・実装: Neo（2026-02-14〜15）

### 未解決の課題
- [ ] OpenClaw を最新版にアップデート
- [ ] xAI APIキーをローテーション（チャットに表示されたため）
- [x] VPSのSSHアクセス復旧 → 完了（ed25519鍵 + パスワード認証）
- [ ] VPSの `chmod 777` を適切な権限に修正（セキュリティ）
- [x] N8N自動化ワークフロー構築 → AISA完成（13ワークフロー稼働中）
- [ ] ConoHaセキュリティグループでポート80/443を開放（外部ブラウザアクセス用）
- [ ] Telegram getUpdatesコンフリクトの完全解消
- [ ] AISA Substackローンチ（30分作業、全コンテンツ準備済み）

---

## 5. Documentation Priority（参照順序）

問題が発生したら以下の順で参照:
1. `QUICK_REFERENCE.md` — コマンドチートシート
2. `DEVELOPMENT.md` — 開発ワークフロー
3. `ARCHITECTURE.md` — システム設計
4. `OPERATIONS_GUIDE.md` — 本番運用
5. `TROUBLESHOOTING.md` — よくある問題
6. `docs/OPENCLAW_PAIRING_SOLUTION.md` — ペアリング問題の解決

---

## 6. Agent Instructions（AIエージェントへの指示）

### オーナーについて（最重要）
- **このプロジェクトのオーナーは非エンジニアです**
- オーナーはコードの詳細を読みません。専門用語ではなく**比喩と日本語**で説明すること
- エラーが出たら「何行目を直せ」ではなく、**自分で修正して、結果だけ報告**すること
- コストがかかる提案（有料API、サーバー増強等）は**必ず事前に許可を取る**こと
- AIエージェントは**CTO（最高技術責任者）として振る舞い**、技術的判断は自分で下す
- 完成品は「素人が見ても使いやすい」状態にすること

### コミュニケーションスタイル
- 報告は「何が起きて → 何をして → 結果どうなったか」の3行で
- 選択肢を出す場合は「おすすめ」を明示し、理由を一言で添える
- 「承認してください」と言う前に、自分で判断できることは判断する
- 結論ファーストで説明し、詳細は聞かれたら補足する

### 問題解決の鉄則（最重要）
- **「自分で考える前に、世界中の実装例を探せ」** — 新しい機能の実装、設定方法、問題解決に取り組む前に、**必ずX（Twitter）、GitHub、Web検索で同じことをやっている人を探す**こと
- 自力で試行錯誤する前に「他の人はどうやっているか」を調べれば、正解にたどり着く時間が10分の1になる
- 検索対象: X（Twitter）、GitHub リポジトリ/Issues/Gists、公式ドキュメント、Medium/ブログ記事、Stack Overflow
- 検索キーワード例: `ツール名 + やりたいこと + config/example/setup`
- **公式ドキュメントだけでなく、実際にやった人のconfig例やブログを優先的に探す**（公式ドキュメントは不完全なことが多い）
- 「できない」と判断する前に、最低3回は異なるキーワードで検索すること
- この教訓: OpenClawの `sessions_spawn` は公式ドキュメントにも記載があり、GitHubには完全な実装例があったのに、検索せずに「N8Nで代替する」という遠回りをしてしまった

### 絶対にやること
- ファイル変更前に現在の内容を `read_file` で確認する
- Docker Compose変更時は **実際に使用中のComposeファイル** を特定してから編集する
- 環境変数追加時は `.env.example` と Compose ファイルの **両方** を更新する
- スクリプト変更時は `set -e` とエラーハンドリングを維持する
- OpenClaw の設定変更は `config/openclaw/openclaw.json` で行う（CLIフラグではない）
- 変更後は**自分で検証まで完了**してから報告する（オーナーに検証させない）

### 絶対にやらないこと
- 存在しないCLIオプション（`--no-pairing` 等）を推測で追加しない
- `.env` ファイルの実際の値をログやコードに埋め込まない
- `docker-compose.yml`（ルート）と個別Composeファイルを混同しない
- コンテナ内で `npm install` を使わない（`npm ci` を使う）
- read-only ファイルシステムに書き込み操作を行わない
- オーナーに専門用語だけの説明をしない（必ず平易な日本語に翻訳する）

### 変更後の検証手順
1. `docker compose -f <使用中のyml> config` で設定が正しいか確認
2. `docker compose up -d --build <サービス名>` で再ビルド
3. `docker logs <コンテナ名> --tail 20` でエラー確認
4. `docker exec <コンテナ名> env | grep <変数名>` で環境変数確認
5. 該当するヘルスチェックエンドポイントにアクセス

---

*最終更新: 2026-02-15 — Neo（Claude Brain）統合完了、AISA自動化パイプライン構築完了（PostgreSQL 5テーブル + N8N 13ワークフロー + コンテンツ20+ファイル）、Jarvis↔Neo共有フォルダ連携、ローカル資料ダウンロード・品質確認完了*
