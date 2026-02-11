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

### 一般的な落とし穴
- **PostgreSQL init スクリプト**: 初回起動時のみ実行。再実行するにはボリューム削除が必要
- **Docker Compose ファイルの選択ミス**: 変更を加えた yml と実際に起動している yml が異なるケースが頻発。`docker compose ps` で確認すること
- **entrypoint.sh の変更**: ファイル修正後は `docker compose up -d --build` が必要（`restart` では反映されない）
- **環境変数のデフォルト値**: `${VAR}` と `${VAR:-default}` の違いに注意。前者は未設定時に空文字、後者はデフォルト値が入る

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
- LLM API: Anthropic Claude（メイン）、Gemini Flash（コスパ重視）
- バックアップ: ローカル保持30日（リモートはオプション）
- 監視: Prometheus + Grafana（セルフホスト、追加コストなし）

### パフォーマンス制約
- 全サービスにリソース制限（`mem_limit`, `cpus`）必須
- ヘルスチェック: 全コンテナに設定、`start_period` を十分に確保（OpenClawは120s）
- PostgreSQL: UTF8 + locale=C（パフォーマンス最適化）

---

## 4. Current State（現在の状態）

### 動作中の構成（2026-02-11時点）
- **使用中Compose**: `docker-compose.quick.yml`
- **コンテナ**: 5サービス全て healthy（openclaw-agent, postgres, nginx, n8n, opennotebook）
- **OpenClaw版**: v2026.2.2-3（最新 v2026.2.9 が利用可能）
- **Gateway**: ws://0.0.0.0:3000 でリッスン中
- **Control UI**: 接続成功（webchat connected）
- **既知の警告**: trusted proxy 設定で `172.28.0.1`（Dockerブリッジ）が未信頼扱い

### 未解決の課題
- [ ] OpenClaw を v2026.2.9 にアップデート
- [ ] trusted proxy 警告の解消（`gateway.trustedProxies` に Docker ブリッジ追加）
- [ ] EBUSY エラーの対応方針決定（`:ro` を外すか許容するか）
- [ ] `entrypoint.sh` 内の不要なペアリング関連コードのクリーンアップ

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

*最終更新: 2026-02-11 — ペアリング問題の教訓を記録、プロジェクト全体のコンテキストを構造化*
