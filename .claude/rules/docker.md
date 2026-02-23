# Docker / Compose ルール

## Docker Compose ファイル使い分け
| ファイル | 用途 | サービス |
|---|---|---|
| `docker-compose.minimal.yml` | 開発テスト | PostgreSQL + OpenNotebook + N8N |
| `docker-compose.dev.yml` | フル開発環境 | 上記 + OpenClaw + Adminer |
| `docker-compose.quick.yml` | 本番（現在使用中） | PostgreSQL + OpenClaw + N8N + substack-api |
| `docker-compose.production.yml` | 本番フル | 全サービス + Nginx SSL |
| `docker-compose.monitoring.yml` | 監視 | Prometheus + Grafana |

**現在使用中**: `docker-compose.quick.yml`（`/opt/openclaw/`）

## サービス通信パターン
- Internet → Caddy (443/80) → Backend services
- OpenClaw / N8N / PostgreSQL（内部ネットワーク、外部非公開）
- OpenClaw → N8N: `http://n8n:5678`（Docker内部DNS）
- 全サービス → PostgreSQL: スキーマ分離（`n8n`, `openclaw`）

## OpenClaw Gateway 設定
- **設定ファイル**: `config/openclaw/openclaw.json`（Docker Composeでマウント）
- **entrypoint**: `docker/openclaw/entrypoint.sh`
- **認証方式**: `--password` フラグでトークン認証
- **ポート**: 3000（WebSocket）、`lan`バインド

## コードスタイル
- Bash: カラーログ（RED/GREEN/YELLOW）、冪等チェック、`set -e` 必須
- Dockerfile: マルチステージビルド、`npm ci`（`npm install` 禁止）、Alpine/Slimベース
- Docker Compose: 環境変数にデフォルト値（`${VAR:-default}`）
- 設定変更: `.env.example` と実際のCompose両方を更新すること

## セキュリティルール
- 全コンテナ: 非root実行（`USER appuser`, UID 1001）
- 全コンテナ: `security_opt: [no-new-privileges:true]`
- ポートバインド: `127.0.0.1` のみ（Caddy以外）
- 全サービス: ヘルスチェック必須、リソース制限必須（`mem_limit`, `cpus`）

## 変更後の検証手順
1. `docker compose -f <yml> config` で設定確認
2. `docker compose up -d --build <service>` で再ビルド
3. `docker logs <container> --tail 20` でエラー確認
4. `docker exec <container> env | grep <VAR>` で環境変数確認
