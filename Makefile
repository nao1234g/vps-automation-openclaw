.PHONY: help setup dev prod up down restart logs health backup restore scan clean test validate

# デフォルトターゲット
.DEFAULT_GOAL := help

# 環境変数
ENV_FILE := .env
COMPOSE_PROD := docker-compose.production.yml
COMPOSE_DEV := docker-compose.dev.yml

# ============================================
# ヘルプ
# ============================================
help: ## このヘルプメッセージを表示
	@echo "OpenClaw VPS - Makefile コマンド"
	@echo ""
	@echo "使用方法: make [TARGET]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ============================================
# セットアップ
# ============================================
setup: ## 初期セットアップ（VPS、Docker、SSL）
	@echo "🚀 初期セットアップを開始..."
	sudo ./setup.sh

setup-dirs: ## 必要なディレクトリを作成
	@echo "📁 ディレクトリを作成..."
	mkdir -p data/{postgres,openclaw,n8n,opennotebook,opennotebook_uploads}
	mkdir -p logs/{openclaw,n8n,opennotebook}
	mkdir -p security-reports
	sudo chown -R 1000:1000 data logs
	@echo "✓ ディレクトリ作成完了"

setup-env: ## .envファイルを作成（.env.exampleから）
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "📝 .envファイルを作成..."; \
		cp .env.example $(ENV_FILE); \
		chmod 600 $(ENV_FILE); \
		echo "✓ .envファイル作成完了"; \
		echo "⚠️  .envファイルを編集して環境変数を設定してください"; \
	else \
		echo "⚠️  .envファイルは既に存在します"; \
	fi

validate-env: ## 環境変数をバリデーション
	@echo "🔍 環境変数をチェック..."
	@./scripts/validate_env.sh

# ============================================
# 開発環境
# ============================================
dev: setup-dirs ## 開発環境を起動
	@echo "🔧 開発環境を起動..."
	docker compose -f $(COMPOSE_DEV) up -d
	@echo "✓ 開発環境起動完了"
	@echo ""
	@echo "アクセス先:"
	@echo "  - OpenClaw: http://localhost:3000"
	@echo "  - N8N: http://localhost:5678"
	@echo "  - OpenNotebook: http://localhost:8080"
	@echo "  - Adminer: http://localhost:8081"

dev-logs: ## 開発環境のログを表示
	docker compose -f $(COMPOSE_DEV) logs -f

dev-down: ## 開発環境を停止
	docker compose -f $(COMPOSE_DEV) down

dev-clean: ## 開発環境を完全削除（ボリュームも削除）
	docker compose -f $(COMPOSE_DEV) down -v

# ============================================
# 本番環境
# ============================================
prod: setup-dirs validate-env ## 本番環境を起動
	@echo "🚀 本番環境を起動..."
	docker compose -f $(COMPOSE_PROD) up -d
	@echo "✓ 本番環境起動完了"

prod-logs: ## 本番環境のログを表示
	docker compose -f $(COMPOSE_PROD) logs -f

prod-down: ## 本番環境を停止
	docker compose -f $(COMPOSE_PROD) down

prod-restart: ## 本番環境を再起動
	docker compose -f $(COMPOSE_PROD) restart

# ============================================
# 共通操作
# ============================================
up: prod ## 本番環境を起動（prodのエイリアス）

down: prod-down ## 本番環境を停止（prod-downのエイリアス）

restart: prod-restart ## 本番環境を再起動（prod-restartのエイリアス）

logs: prod-logs ## 本番環境のログを表示（prod-logsのエイリアス）

ps: ## コンテナの状態を表示
	docker compose -f $(COMPOSE_PROD) ps

# ============================================
# 運用タスク
# ============================================
health: ## ヘルスチェックを実行
	@echo "🏥 ヘルスチェックを実行..."
	@./scripts/health_check.sh

backup: ## バックアップを実行
	@echo "💾 バックアップを実行..."
	@sudo ./scripts/backup.sh

backup-db: ## データベースのみバックアップ
	@echo "💾 データベースバックアップを実行..."
	@sudo ./scripts/backup.sh --db-only

restore: ## バックアップから復元（使用方法: make restore BACKUP=/path/to/backup）
	@if [ -z "$(BACKUP)" ]; then \
		echo "❌ エラー: BACKUPパスを指定してください"; \
		echo "使用例: make restore BACKUP=/opt/backups/openclaw/backup_20240101_120000"; \
		exit 1; \
	fi
	@echo "🔄 バックアップから復元..."
	@sudo ./scripts/restore.sh $(BACKUP)

scan: ## セキュリティスキャンを実行
	@echo "🔒 セキュリティスキャンを実行..."
	@./scripts/security_scan.sh --all

scan-images: ## Dockerイメージスキャン
	@echo "🔒 Dockerイメージスキャンを実行..."
	@./scripts/security_scan.sh --images-only

maintenance: ## システムメンテナンスを実行
	@echo "🛠️  メンテナンスを実行..."
	@sudo ./scripts/maintenance.sh

maintenance-dry: ## メンテナンス（ドライラン）
	@echo "🛠️  メンテナンス（ドライラン）を実行..."
	@sudo ./scripts/maintenance.sh --dry-run

# ============================================
# テスト・検証
# ============================================
test: validate ## デプロイメント検証を実行（validateのエイリアス）

validate: ## デプロイメント検証を実行
	@echo "✅ デプロイメント検証を実行..."
	@./scripts/validate_deployment.sh

validate-compose: ## Docker Compose設定を検証
	@echo "🔍 Docker Compose設定を検証..."
	@docker compose -f $(COMPOSE_PROD) config > /dev/null
	@echo "✓ Docker Compose設定は正常です"

# ============================================
# SSL証明書
# ============================================
ssl: ## SSL証明書を取得（使用方法: make ssl DOMAIN=example.com EMAIL=admin@example.com）
	@if [ -z "$(DOMAIN)" ] || [ -z "$(EMAIL)" ]; then \
		echo "❌ エラー: DOMAINとEMAILを指定してください"; \
		echo "使用例: make ssl DOMAIN=example.com EMAIL=admin@example.com"; \
		exit 1; \
	fi
	@echo "🔐 SSL証明書を取得..."
	@sudo ./scripts/setup_ssl.sh $(DOMAIN) $(EMAIL)

ssl-renew: ## SSL証明書を更新
	@echo "🔐 SSL証明書を更新..."
	@sudo certbot renew

# ============================================
# クリーンアップ
# ============================================
clean: ## 未使用Dockerリソースを削除
	@echo "🧹 未使用Dockerリソースを削除..."
	docker system prune -f
	@echo "✓ クリーンアップ完了"

clean-all: ## 全Dockerリソースを削除（危険：データも削除されます）
	@echo "⚠️  警告: 全Dockerリソースとボリュームを削除します"
	@read -p "続行しますか？ (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker compose -f $(COMPOSE_PROD) down -v
	docker system prune -af --volumes
	@echo "✓ 全リソース削除完了"

clean-logs: ## ログファイルを削除
	@echo "🧹 ログファイルを削除..."
	rm -rf logs/*
	mkdir -p logs/{openclaw,n8n,opennotebook}
	sudo chown -R 1000:1000 logs
	@echo "✓ ログ削除完了"

# ============================================
# 開発ツール
# ============================================
shell-openclaw: ## OpenClawコンテナに入る
	docker compose -f $(COMPOSE_PROD) exec openclaw sh

shell-postgres: ## PostgreSQLコンテナに入る
	docker compose -f $(COMPOSE_PROD) exec postgres psql -U openclaw

shell-n8n: ## N8Nコンテナに入る
	docker compose -f $(COMPOSE_PROD) exec n8n sh

shell-opennotebook: ## OpenNotebookコンテナに入る
	docker compose -f $(COMPOSE_PROD) exec opennotebook sh

# ============================================
# Git操作
# ============================================
git-status: ## Git状態を表示
	@git status

git-pull: ## 最新コードを取得
	@echo "🔄 最新コードを取得..."
	git pull origin main
	@echo "✓ 更新完了"

git-update: git-pull prod-down prod ## 最新コードで本番環境を更新

# ============================================
# 情報表示
# ============================================
info: ## システム情報を表示
	@echo "OpenClaw VPS - システム情報"
	@echo ""
	@echo "Docker バージョン:"
	@docker --version
	@echo ""
	@echo "Docker Compose バージョン:"
	@docker compose version
	@echo ""
	@echo "実行中のコンテナ:"
	@docker compose -f $(COMPOSE_PROD) ps
	@echo ""
	@echo "ディスク使用量:"
	@df -h / | tail -1
	@echo ""
	@echo "メモリ使用量:"
	@free -h | grep Mem

# ============================================
# ワンライナー
# ============================================
quick-deploy: setup-env setup-dirs prod health ## クイックデプロイ（全自動）

quick-update: git-pull prod-down prod health ## クイック更新（全自動）
