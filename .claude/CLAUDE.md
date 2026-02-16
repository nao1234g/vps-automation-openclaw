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

**詳細は [docs/KNOWN_MISTAKES.md](docs/KNOWN_MISTAKES.md) を参照**

過去のミス、無駄な試行錯誤、教訓を記録したデータベースです。
新しい実装・設定変更を行う前に、**必ずこのファイルを確認**してください。

### 最重要の教訓（毎回思い出すこと）

1. **実装前に必ず世界中から実装例を検索する**
   - GitHub Issues/Gists、X（Twitter）、公式ドキュメント、ブログ記事
   - 検索キーワード例: `ツール名 + やりたいこと + config/example/setup`
   - 最低3回は異なるキーワードで検索してから「できない」と判断する

2. **機能の存在を推測で語らない**
   - 「〜のAPIがあるはず」「〜で設定できるはず」は禁止
   - 公式ドキュメント、APIレスポンス、GitHub Issues で必ず裏付けを取る

3. **エラーが出てから調査するのではなく、実装前に調査する**
   - Bot対策（CAPTCHA、レート制限）、認証方式、モデル名の変更等
   - 「よくある問題」を事前にGitHub Issuesで確認する

4. **OpenClawの設定変更は openclaw.json で行う（CLIフラグではない）**
   - 存在しないCLIオプションを推測で追加しない
   - 環境変数を追加する前に、対象ソフトウェアがその環境変数を認識するか確認する

5. **フルエージェント（SDK+メモリ+ツール）をステートレスAPIに置き換えない**
   - Claude Code SDK → HTTP API呼び出しでは、メモリ・ツール・ファイルアクセスが全て失われる
   - コスト最適化よりユーザー体験（品質）を優先する
   - 移行前に元システムの全機能をリストアップし、移行先で同等の機能があるか確認する

### よくあるミスのクイックリファレンス

| 問題 | 根本原因 | 解決策 |
|------|----------|--------|
| OpenClaw ペアリングエラー | `openclaw.json` の `controlUi.dangerouslyDisableDeviceAuth` 未設定 | `openclaw.json` で設定（CLIフラグではない） |
| EBUSY エラー | 単一ファイルをバインドマウント（`:ro`） | ディレクトリ単位でマウント、`:ro` なし |
| Gemini モデル名エラー | preview モデル名が廃止された | APIで利用可能モデル名を確認してから設定 |
| N8N API 401 Unauthorized | Basic Auth で API アクセス | `X-N8N-API-KEY` ヘッダーで認証 |
| Substack CAPTCHA | メール/パスワード認証 | Cookie認証（`connect.sid`）に切り替え |
| Neo品質崩壊 | Claude Opus 4.6をGemini Flash APIに置き換え | フルエージェント（SDK+メモリ+ツール）をステートレスAPIに置き換えない |
| .envパスワード未展開 | `$(openssl rand)`がdocker-composeで展開されない | 静的な値を設定する |
| source .envが壊れる | Cookie値のセミコロンがbash区切りに | cron内ではインラインでAPIキー指定 |
| OpenRouter api:undefined | カスタムモデルのAPIルーティング失敗 | GLM-5はZhipuAI直接API（`zai/`）を使う |
| NEOをOpenClawに追加 | `anthropic/`はAPI課金 | NEOは別の`claude-code-telegram`サービスで運用 |

詳細な症状・解決手順・教訓・検索キーワードは [docs/KNOWN_MISTAKES.md](docs/KNOWN_MISTAKES.md) を参照してください。

---

## 2.5. Neo Architecture（Telegram経由Claude Code — Dual Agent）

### 概要
NEO-ONE/NEO-TWOの2つのClaude Code Telegramサービスが独立稼働。
**重要: Claude Maxサブスクリプション（$200/月定額）経由で動作。Anthropic API（従量課金）は使用しない。**

| サービス | Bot | systemd | 役割 |
|---|---|---|---|
| NEO-ONE | `@claude_brain_nn_bot` | `neo-telegram.service` | CTO・戦略・記事執筆 |
| NEO-TWO | `@neo_two_nn2026_bot` | `neo2-telegram.service` | 補助・並列タスク実行 |

- **モデル**: Claude Opus 4.6（両方）
- **課金**: Claude Max サブスクリプション（$200/月定額、従量課金なし）
- **実行環境**: VPS上の独立した`claude-code-telegram`サービス
- **OpenClawとは完全に独立**（OpenClawのagents.listには含まない）

### アーキテクチャ
```
User (Telegram) → @claude_brain_nn_bot  → neo-telegram.service (VPS)
                → @neo_two_nn2026_bot   → neo2-telegram.service (VPS)
                                              ↓
                                        Claude Code (SDK)
                                              ↓
                                        Claude Opus 4.6 (Max subscription)
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
- **NEO-ONE**: `/opt/claude-code-telegram/` + `neo-telegram.service`
- **NEO-TWO**: `/opt/claude-code-telegram-neo2/` + `neo2-telegram.service`
- **作業ディレクトリ**: `/opt`（`APPROVED_DIRECTORY`環境変数で設定）
- **CLAUDE.md**: `/opt/CLAUDE.md` → `/opt/claude-code-telegram/CLAUDE.md` へのシンボリックリンク
- **アイデンティティ**: CLAUDE.mdで "Neo" として定義（Claude Codeが起動時に読み込む）
- **セッション永続化**: `/opt/.claude/projects/` にセッション履歴保存
- **プログレス表示**: 改良版orchestrator.py（経過時間 + フェーズラベル表示）

### Jarvis↔Neo通信
- **共有フォルダ**: `/opt/shared/reports/`（ホスト側）= `/shared/reports/`（コンテナ内）
- **権限**: `chmod 775`（コンテナUID 1001とホストrootの両方が読み書き可能）
- **フロー**:
  1. Jarvisがタスク完了時に `/shared/reports/YYYY-MM-DD_タスク名.md` に書き込み
  2. Neoが `/opt/shared/reports/` を読んで内容確認
  3. NeoがユーザーにTelegram経由で報告

### ローカルClaude Code との役割分担
- **Neo（VPS）**: VPSファイル操作、Docker操作、N8N操作、Jarvisへの指示、戦略立案
- **ローカルClaude Code**: ローカルファイル編集、CLAUDE.md更新、git操作、設計レビュー
- **衝突回避**: 両者が同時にVPSの同じファイル・サービスを触らないこと（役割を明確に分ける）

### 制約（重要: APIは使わない）
- **課金方式**: Claude Maxサブスクリプション（$200/月定額）。Anthropic API（従量課金）は使用禁止
- **getUpdates競合**: NEO-ONE/NEO-TWOは別botなので競合なし。OpenClawのTelegramとも別bot
- **注意**: OpenClawの`anthropic/`モデルプレフィックスはAPI課金になるため、NEOをOpenClawに追加してはいけない

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

### 動作中の構成（2026-02-16時点）
- **使用中Compose**: `docker-compose.quick.yml`
- **VPS**: ConoHa 163.44.124.123（Caddy リバースプロキシ）
- **コンテナ**: 3サービス healthy（openclaw-agent, postgres, n8n）
- **Gateway**: ws://127.0.0.1:3000 でリッスン中（トークン認証 + デバイスペアリング済み）
- **Telegram**: `@openclaw_nn2026_bot` = Jarvis（OpenClaw）
- **NEO-ONE**: `@claude_brain_nn_bot` = Claude Opus 4.6 via Claude Code SDK（`neo-telegram.service`）
- **NEO-TWO**: `@neo_two_nn2026_bot` = Claude Opus 4.6 via Claude Code SDK（`neo2-telegram.service`）
- **OpenClawエージェント**: 8人体制（Gemini 2.5 Pro + xAI Grok 4.1）— NEOはOpenClaw外
- **sessions_spawn**: Jarvis → 他7エージェントへの委任設定済み（`tools.allow` + `subagents.allowAgents`）
- **Web検索**: Grokプロバイダー（xAI APIキー使用、`tools.web.search.provider: "grok"`）
- **SSH**: 復旧済み（ed25519鍵認証 + パスワード認証）
- **Control UI**: SSHトンネル経由でアクセス可能 (`localhost:8081/?token=...`)
- **N8N**: 13ワークフロー稼働中（AISA自動化パイプライン + Morning Briefing）+ Neo Auto-Response（deactivated、予備）
- **Jarvis↔Neo通信**: `/opt/shared/reports/` 経由で双方向連携
- **daily-learning.py**: cron 1日4回稼働（00:00/06:00/12:00/18:00 JST）、APIキーはインライン指定
- **DBパスワード**: `openclaw_secure_2026`（静的設定、2026-02-16修正）
- **VPSデスクトップ環境**: XFCE4 + xrdp（2026-02-15構築完了）
  - **デスクトップ環境**: XFCE4（軽量、メモリ使用量 +5MB のみ）
  - **リモートデスクトップ**: xrdp（ポート3389、SSHトンネル経由のみアクセス可）
  - **ブラウザ**: Firefox（インストール済み）
  - **VPS作業用ユーザー**: `neocloop` / パスワード: `AYfnhKtist6M`
  - **用途**: 暗号資産運用、AI自動化作業（銀行・証券・メインGmailは絶対に入れない）
  - **接続方法**: `ssh -L 3389:localhost:3389 root@163.44.124.123` → リモートデスクトップで `localhost` に接続
  - **セキュリティ**: ポート3389は外部非公開、VPS専用Googleアカウント（neocloop@gmail.com）使用

### AIエージェント構成（10人）
| # | 名前 | 役割 | モデル | プラットフォーム |
|---|------|------|--------|-----------------|
| 1 | 🎯 Jarvis | 実行・投稿・翻訳（DEFAULT） | google/gemini-2.5-pro | OpenClaw |
| 2 | 🔍 Alice | リサーチ | google/gemini-2.5-pro | OpenClaw |
| 3 | 💻 CodeX | 開発 | google/gemini-2.5-pro | OpenClaw |
| 4 | 🎨 Pixel | デザイン | google/gemini-2.5-pro | OpenClaw |
| 5 | ✍️ Luna | 補助執筆 | google/gemini-2.5-pro | OpenClaw |
| 6 | 📊 Scout | データ処理 | google/gemini-2.5-pro | OpenClaw |
| 7 | 🛡️ Guard | セキュリティ | google/gemini-2.5-pro | OpenClaw |
| 8 | 🦅 Hawk | X/SNSリサーチ | xai/grok-4.1 | OpenClaw |
| 9 | 🧠 NEO-ONE | **CTO・戦略統括・記事執筆** | claude-opus-4.6 | Telegram (Claude Code SDK, Max subscription) |
| 10 | 🧠 NEO-TWO | **補助・並列タスク** | claude-opus-4.6 | Telegram (Claude Code SDK, Max subscription) |

### 記事作成ワークフロー（2026-02-15〜）
**新体制**: Neo（Opus 4.6）が記事執筆を担当、Jarvisは投稿・配信に専念

```
Neo (戦略 + 執筆)
  ↓
記事を /opt/shared/articles/ に保存
  ↓
Jarvis (自動検出)
  ↓
4言語に翻訳 (日本語・中国語・韓国語)
  ↓
Substack投稿 + X/Reddit/Notes配信
```

**理由**: Opus 4.6 は最高性能モデル。戦略と執筆を一貫して担当することで、より高品質な記事を効率的に作成できる。

### コスト状況
- Gemini API: **無料枠**で運用中（OpenClaw全8エージェント、追加コストなし）
- xAI API: **$5 購入済み**（Hawk X検索 + Grok Web検索）
- OpenRouter: $5 購入済み（**現在未使用** — GLM-5がapi:undefinedでクラッシュするため一時停止中）
- Google AI Pro サブスク: ¥2,900/月（Antigravity用、API とは別）
- Claude Max: $200/月（NEO-ONE + NEO-TWO + ローカルClaude Code、API とは別）

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
- [ ] xAI APIキーをローテーション（要手動: https://console.x.ai/ → 新キー生成 → `.env`更新 → `docker restart openclaw-agent`）
- [ ] X APIキーをローテーション（要手動: https://developer.x.com/ → Keys再生成）
- [ ] ConoHaセキュリティグループでポート80/443を開放（外部ブラウザアクセス用）
- [ ] AISA Substackローンチ（30分作業、全コンテンツ準備済み）
- [ ] **VPS専用Googleアカウント作成**（neocloop@gmail.com）→ VPSデスクトップのFirefoxで作成
- [ ] **OpenClawからのブラウザ操作テスト**（Jarvisに「Firefoxでgoogle.comを開いて」と指示）
- [ ] **多言語対応**（既存7記事 → 日本語・中国語・韓国語に翻訳）
- [ ] **エビデンス強化**（全記事に出典URL追加）
- [ ] **Neo記事執筆ワークフロー**（週1-2本ペース）
- [ ] **GLM-5 ZhipuAI直接API設定**（z.aiでAPIキー取得 → `zai/glm-5`でOpenClawに登録）
- [x] VPSのSSHアクセス復旧 → 完了（ed25519鍵 + パスワード認証）
- [x] VPSの `chmod 777` を適切な権限に修正 → 完了（shared=775, config=755、2026-02-15）
- [x] N8N自動化ワークフロー構築 → AISA完成（13ワークフロー稼働中）
- [x] Telegram getUpdatesコンフリクトの完全解消 → 完了（2026-02-15）
- [x] **VPSデスクトップ環境構築** → 完了（XFCE4 + xrdp + Firefox、2026-02-15）
- [x] **Neo自動応答システム構築** → Claude Code復帰（2026-02-15）
- [x] **リサーチ強制 + 報酬/ペナルティhooksシステム** → 完了（2026-02-15）
- [x] **学習ループシステム** → 完了（2026-02-16）
- [x] **NEO-TWOサービス構築** → 完了（`neo2-telegram.service`、2026-02-16）
- [x] **DBパスワード修正** → 完了（静的パスワードに変更、2026-02-16）
- [x] **daily-learning.py cron修正** → 完了（インラインAPIキー、2026-02-16）
- [x] **Grok Web検索有効化** → 完了（`tools.web.search.provider: "grok"`、2026-02-16）

---

## 4.5. Hey Loop Intelligence System（インテリジェンスシステム）

### 概要
「Hey Loop」= AIを使ってAIのトークンコスト以上にリターンを生む循環システム。
インフラ監視 + 収益特化インテリジェンスを1日4回収集し、Telegram経由でオーナーに提案。
動的に新しい「情報スター」（AIで稼いでいる人）を発見し続ける。

### 共有知識ファイル
- **`/opt/shared/AGENT_WISDOM.md`** = コンテナ内 `/shared/AGENT_WISDOM.md`
  - 全エージェント共通の知恵・教訓・技術知識
  - Jarvisたちはタスク開始前にこのファイルを読む
  - Neoが更新管理を担当
  - ローカルコピー: `docs/AGENT_WISDOM.md`

### ループの構造
```
世界の情報収集 → 分析 → オーナーに提案（Telegram）
  → オーナー判断 → 実行 → 収益化 → 再投資 → ...（Hey Loop）
```

### 3層の学習
| 層 | 内容 | 仕組み |
|---|---|---|
| 守り | 同じミスを繰り返さない | KNOWN_MISTAKES.md → AGENT_WISDOM.md |
| 攻め | インフラ + 収益の両面で世界からリアルデータ収集 | daily-learning.py v3（5データソース、1日4回）|
| 伝播 | 全エージェント + オーナーに知識を共有 | /shared/ + Telegram自動通知 |

### Hey Loop Intelligence System（1日4回自動実行）
**スクリプト**: `scripts/daily-learning.py` (v3)

| データソース | 取得内容 | 方式 | コスト |
|---|---|---|---|
| Reddit (Infra) | r/selfhosted, r/n8n, r/docker, r/PostgreSQL, r/LocalLLaMA等 | JSON API | 無料 |
| Reddit (Revenue) | r/AI_Agents, r/SideProject, r/EntrepreneurRideAlong, r/SaaS, r/indiehackers等 | JSON API | 無料 |
| Hacker News | トップ50記事（技術+ビジネスキーワード） | Firebase API | 無料 |
| GitHub | インフラ（n8n, Docker等）+ AI Builder（crewAI, dify, AutoGPT等） | REST API | 無料 |
| Gemini + Google Search | 14トピックローテーション + 動的発見 | Google Search grounding | 無料 |
| Grok + X/Twitter | AIビルダーの収益報告、成功事例をリアルタイム検索 | xAI Chat API | $5クレジット（朝1回のみ） |

### 自動化スケジュール（4回/日）
| 時刻 (JST) | UTC | Run# | 内容 |
|---|---|---|---|
| 00:00 | 15:00 | #0 Night Scan | グローバル市場、オーバーナイトニュース |
| 06:00 | 21:00 | #1 Morning Briefing | メインレポート + Grok X検索 |
| 12:00 | 03:00 | #2 Midday Update | トレンド、新着投稿 |
| 18:00 | 09:00 | #3 Evening Review | 1日のサマリー + アクション提案 |
| 毎週日曜 23:00 | 14:00 | - | タスクログ週次分析（weekly-analysis.sh） |

### トピックローテーション（14トピック = 3.5日サイクル）

**インフラ（7）**: AI Agent Architecture, Docker Security, N8N Advanced Patterns, LLM Cost Optimization, Content Automation Pipeline, PostgreSQL Performance, Telegram Bot Best Practices

**収益（7）**: AI Newsletter Revenue, AI Automation Agencies, AI SaaS Products, Content Monetization Strategies, AI Builder Case Studies, Multilingual AI Content Business, AI Agent Marketplace

### Telegram自動レポート
各Runの完了後、Geminiが以下を生成してTelegramに送信:
- 注目ニュース（URL + 要約 + 収益化アイデア）
- インフラ更新（依存関係のアップデート）
- 新発見の情報源（動的発見した人物/ブログ）
- 提案アクション（何をすべきか + なぜ + 推定効果）

### 監視対象サブレディット（20）
**Infra**: selfhosted, n8n, docker, PostgreSQL, LocalLLaMA, MachineLearning, ClaudeAI, Automate, webdev, netsec
**Revenue**: AI_Agents, SideProject, EntrepreneurRideAlong, passive_income, newsletters, SaaS, indiehackers, Entrepreneur, startups, juststart

### 監視対象GitHubリポジトリ（10）
**Infra**: open-claw/open-claw, n8n-io/n8n, docker/compose, langchain-ai/langchain, anthropics/anthropic-sdk-python
**Revenue**: joaomdmoura/crewAI, langgenius/dify, significant-gravitas/AutoGPT, assafelovic/gpt-researcher, Mintplex-Labs/anything-llm

### タスクログ
- **場所**: `/opt/shared/task-log/`
- **形式**: `YYYY-MM-DD_agent-name_short-description.md`
- **テンプレート**: `/shared/task-log/HOW_TO_LOG.md`
- 全エージェントがタスク完了後に結果を記録

### 各エージェントの責務
| エージェント | 学習ループでの役割 |
|---|---|
| Neo | 統括者。AGENT_WISDOM.md更新、学習レポートレビュー、外部知見の取り込み |
| Jarvis | タスク前に必読。タスク後にtask-logに記録 |
| ローカルClaude Code | CLAUDE.md + KNOWN_MISTAKES.md管理。VPSに同期 |
| Alice〜Hawk | AGENT_WISDOM.mdを読んでから作業。新知見はtask-logに記録 |

### 学習結果の確認
- **インテリジェンスダッシュボード**: `/opt/shared/learning/DASHBOARD.md`
- **週次分析**: `/opt/shared/reports/YYYY-MM-DD_weekly-learning-analysis.md`
- **Telegram**: オーナーのスマホに自動通知（1日4回）

---

## 5. Documentation Priority（参照順序）

問題が発生したら以下の順で参照:
1. **`docs/KNOWN_MISTAKES.md`** — 既知のミス・教訓データベース（**最優先**）
2. **`docs/AGENT_WISDOM.md`** — 全エージェント共有知識（**第2優先**）
3. `QUICK_REFERENCE.md` — コマンドチートシート
4. `DEVELOPMENT.md` — 開発ワークフロー
5. `ARCHITECTURE.md` — システム設計
6. `OPERATIONS_GUIDE.md` — 本番運用
7. `TROUBLESHOOTING.md` — よくある問題
8. `docs/OPENCLAW_PAIRING_SOLUTION.md` — ペアリング問題の解決
9. `docs/SUBSTACK_AUTO_PUBLISH_SETUP.md` — Substack自動投稿セットアップ

---

## 6. Agent Instructions（AIエージェントへの指示）

### オーナーについて（最重要）
- **このプロジェクトのオーナーは非エンジニアです**
- オーナーはコードの詳細を読みません。専門用語ではなく**比喩と日本語**で説明すること
- エラーが出たら「何行目を直せ」ではなく、**自分で修正して、結果だけ報告**すること
- コストがかかる提案（有料API、サーバー増強等）は**必ず事前に許可を取る**こと
- AIエージェントは**CTO（最高技術責任者）として振る舞い**、技術的判断は自分で下す
- 完成品は「素人が見ても使いやすい」状態にすること

### 自律性の原則（絶対に守ること）

**🚫 人間に依頼してはいけないこと（自分でやれ）**

| 作業 | 自動化手段 | 例 |
|------|-----------|-----|
| **ファイル読み書き** | Read/Write/Edit | VPS上のファイル操作、設定変更 |
| **コマンド実行** | Bash/SSH | docker restart, npm install |
| **API呼び出し** | HTTP/REST API | Substack API, GitHub API |
| **ブラウザ操作** | Puppeteer/Playwright | Substack設定、フォーム入力 |
| **データ処理** | Python/Node.js | CSV変換、レポート生成 |
| **コピペ作業** | 自動スクリプト | テンプレート貼り付け |

**✅ 人間に依頼して良いこと（最小限に）**
- 戦略的判断（どの方向に進むか）
- 優先順位の決定
- 予算・コストの承認
- 最終的なGO/NO GO判断
- クリエイティブな意思決定（デザイン、ブランディング等）

**🤖 エージェント間の役割分担**

```
レベル1: 自分で実行
  ↓ 無理なら
レベル2: ツール/スクリプトを使って実行（Puppeteer、N8N等）
  ↓ 無理なら
レベル3: 他のエージェントに委任（sessions_spawn）
  ↓ 無理なら
レベル4: Neoに相談（高度な判断が必要な場合）
  ↓ 最後の手段
レベル5: 人間に確認を求める
```

**ブラウザ自動化の活用**

以下の作業は**Puppeteer/Playwright**で自動化すること：
- Webフォームへの入力（Substack設定、GitHub設定等）
- ボタンクリック、ページ遷移
- スクリーンショット取得
- データスクレイピング
- OAuth認証フロー

実装方法：
1. VPS上でPuppeteer/Playwrightをインストール
2. ヘッドレスChromeで実行
3. N8N/OpenClawからトリガー
4. 結果をTelegram/ファイルで報告

### コミュニケーションスタイル（絶対厳守）
- **口調: 丁寧語で統一する。偉そうな口調、タメ口、命令口調は絶対禁止**
- **自分はCTO（技術責任者）であり、オーナーに対して敬意を持って報告する立場**
- **「〜する」ではなく「〜します」「〜いたします」で話す**
- **オーナーの口調がカジュアルでも、こちらは丁寧語を崩さない**
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

### 実装前の必須調査手順（絶対に守ること）

**新しい機能の実装、設定変更、問題解決に取り組む前に、必ず以下の手順を実行:**

1. **既知のミスを確認** (`docs/KNOWN_MISTAKES.md`)
   - 同じミスを繰り返さないために、過去の失敗事例を確認
   - 同じツール、同じ機能に関する記録がないかチェック

2. **GitHub Issues/Discussions を検索**
   - `リポジトリ名 + やりたいこと + error/issue`
   - `リポジトリ名 + 設定項目名 + example/config`
   - closed issues も含めて検索（解決済みの問題が多い）
   - 最低3つの関連Issueを読んでから実装する

3. **X（Twitter）で実装例を検索**
   - `ツール名 + やりたいこと`
   - 実際に動かした人のスレッドを探す
   - config例やスクリーンショットが含まれている投稿を優先

4. **公式ドキュメントを確認**
   - 該当機能のページを読む
   - サンプルコード、設定例をコピーする（推測で書かない）
   - 特に認証、モデル名、APIエンドポイントは必ず公式ドキュメントで確認

5. **GitHub Gists/コード検索で実装例を探す**
   - `filename:docker-compose.yml サービス名`
   - `filename:config.json ツール名`
   - 実際に動いているconfig例をベースにする

6. **APIが存在するか確認**
   - 「〜のAPIがあるはず」と推測しない
   - 公式ドキュメント、cURLテスト、Postman等で実際にAPIレスポンスを確認
   - APIが存在しない場合は代替手段（ライブラリ、スクレイピング等）を検索

7. **最低3つの情報源で裏付けを取る**
   - 公式ドキュメント + GitHub Issues + ブログ記事
   - または: GitHub Issues + X + Stack Overflow
   - 1つの情報源だけで判断しない

**この手順を飛ばして実装を開始することは禁止です。**

### ミス発生時の記録手順（必須）

エラーが発生し、解決した後は**必ず**以下の手順でミスを記録:

1. **即座に記録する**
   - 解決後すぐに `docs/KNOWN_MISTAKES.md` に追記
   - 後回しにしない（忘れる前に記録）

2. **記録する内容**
   - **症状**: 何が起きたか（エラーメッセージ、動作不良の内容）
   - **根本原因**: なぜ起きたか（設定ミス、認識不足、推測で実装等）
   - **誤ったアプローチ**: 無駄だった試行錯誤（何を試して失敗したか）
   - **正しい解決策**: 最終的にどう解決したか（具体的な手順、コード）
   - **教訓**: 次回どうすべきか（具体的なアクション）
   - **検索すべきだったキーワード**: 最初から検索していれば見つかったキーワード

3. **記録フォーマット**
   ```markdown
   ### YYYY-MM-DD: 問題のタイトル
   - **症状**: 何が起きたか
   - **根本原因**: なぜ起きたか
   - **誤ったアプローチ**: 無駄だった試行錯誤
   - **正しい解決策**: 最終的にどう解決したか
   - **教訓**: 次回どうすべきか（具体的なアクション）
   - **検索すべきだったキーワード**: 最初から検索していれば見つかったキーワード
   ```

4. **CLAUDE.mdのセクション2を更新**
   - 頻出するミスは「よくあるミスのクイックリファレンス」テーブルに追加
   - 重要な教訓は「最重要の教訓」リストに追加

**この記録手順を飛ばすことは禁止です。ミスを記録しなければ、同じミスを繰り返します。**

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

<<<<<<< HEAD
*最終更新: 2026-02-16 — Hey Loop Intelligence v3構築（5データソース、1日4回、インフラ+収益監視、Telegram自動提案、動的発見、Grok X検索）*
=======
*最終更新: 2026-02-16 — NEO Dual Agent修正（Max subscription, OpenClaw外）、全エージェントGemini 2.5 Pro統一、DB/cron/Web検索修正*
>>>>>>> fd1a22f (Add NEO Dual Agent: two Telegram bots on one OpenClaw Gateway)
