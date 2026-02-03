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
# 最小構成（開発用）
# ============================================
minimal: setup-dirs ## 最小構成（PostgreSQL + OpenNotebook + N8N）を起動
	@echo "🚀 最小構成を起動..."
	docker compose -f docker-compose.minimal.yml up -d
	@echo "✓ 起動完了"
	@echo ""
	@echo "アクセス先:"
	@echo "  - OpenNotebook: http://localhost:8080/health"
	@echo "  - N8N:          http://localhost:5678 (admin / dev_admin_password_change_in_prod)"
	@echo "  - PostgreSQL:   localhost:5432"

minimal-logs: ## 最小構成のログを表示
	docker compose -f docker-compose.minimal.yml logs -f

minimal-down: ## 最小構成を停止
	docker compose -f docker-compose.minimal.yml down

minimal-clean: ## 最小構成を完全削除（ボリュームも削除）
	docker compose -f docker-compose.minimal.yml down -v

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
# E2Eテスト
# ============================================
e2e-install: ## E2Eテストの依存関係をインストール
	@echo "📦 E2Eテストの依存関係をインストール..."
	cd tests/e2e && npm install
	cd tests/e2e && npx playwright install --with-deps
	@echo "✓ インストール完了"

e2e-test: ## E2Eテストを実行
	@echo "🧪 E2Eテストを実行..."
	cd tests/e2e && npm test
	@echo "✓ テスト完了"

e2e-test-ui: ## E2EテストをUIモードで実行
	cd tests/e2e && npm run test:ui

e2e-test-headed: ## E2Eテストをブラウザ表示で実行
	cd tests/e2e && npm run test:headed

e2e-report: ## E2Eテストレポートを表示
	cd tests/e2e && npm run report

# ============================================
# 負荷テスト
# ============================================
load-test: ## 標準負荷テストを実行
	@echo "🔥 負荷テストを実行..."
	k6 run tests/load/k6-config.js
	@echo "✓ テスト完了"

load-test-spike: ## スパイクテストを実行
	@echo "🔥 スパイクテストを実行..."
	k6 run tests/load/spike-test.js

load-test-stress: ## ストレステストを実行
	@echo "🔥 ストレステストを実行..."
	k6 run tests/load/stress-test.js

load-test-soak: ## ソークテスト（長時間）を実行
	@echo "🔥 ソークテストを実行（約2時間）..."
	k6 run tests/load/soak-test.js

load-test-quick: ## クイック負荷テスト（5 VUs, 30秒）
	@echo "🔥 クイック負荷テストを実行..."
	k6 run --vus 5 --duration 30s tests/load/k6-config.js

# ============================================
# Terraform (IaC)
# ============================================
tf-init: ## Terraformを初期化
	@echo "🏗️  Terraformを初期化..."
	cd terraform && terraform init
	@echo "✓ 初期化完了"

tf-plan: ## Terraformプランを表示
	@echo "📋 Terraformプランを表示..."
	cd terraform && terraform plan

tf-apply: ## Terraformを適用（インフラ作成）
	@echo "🚀 Terraformを適用..."
	cd terraform && terraform apply

tf-destroy: ## Terraformリソースを削除（危険）
	@echo "⚠️  警告: 全インフラリソースを削除します"
	@read -p "続行しますか？ (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	cd terraform && terraform destroy

tf-output: ## Terraform出力を表示
	cd terraform && terraform output

tf-validate: ## Terraform設定を検証
	cd terraform && terraform validate

# ============================================
# Helm (Kubernetes)
# ============================================
helm-deps: ## Helm依存関係を更新
	@echo "📦 Helm依存関係を更新..."
	cd helm/openclaw && helm dependency update
	@echo "✓ 更新完了"

helm-install: ## Helm Chartをインストール
	@echo "🚀 Helm Chartをインストール..."
	helm install openclaw helm/openclaw -n openclaw --create-namespace
	@echo "✓ インストール完了"

helm-upgrade: ## Helm Chartをアップグレード
	@echo "⬆️  Helm Chartをアップグレード..."
	helm upgrade openclaw helm/openclaw -n openclaw
	@echo "✓ アップグレード完了"

helm-uninstall: ## Helm Chartをアンインストール
	@echo "🗑️  Helm Chartをアンインストール..."
	helm uninstall openclaw -n openclaw
	@echo "✓ アンインストール完了"

helm-template: ## Helmテンプレートをレンダリング
	helm template openclaw helm/openclaw -n openclaw

helm-lint: ## Helm Chartをリント
	helm lint helm/openclaw

helm-dev: ## 開発環境用にインストール
	helm install openclaw-dev helm/openclaw \
		-n openclaw-dev --create-namespace \
		-f helm/openclaw/values-development.yaml

helm-prod: ## 本番環境用にインストール
	helm install openclaw-prod helm/openclaw \
		-n openclaw-prod --create-namespace \
		-f helm/openclaw/values-production.yaml

# ============================================
# GitOps (ArgoCD)
# ============================================
argocd-install: ## ArgoCDをインストール
	@echo "🔄 ArgoCDをインストール..."
	kubectl create namespace argocd || true
	kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
	@echo "✓ インストール完了"
	@echo "初期パスワード取得: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"

argocd-project: ## ArgoCDプロジェクトを作成
	@echo "📁 ArgoCDプロジェクトを作成..."
	kubectl apply -f gitops/argocd/project.yaml
	@echo "✓ プロジェクト作成完了"

argocd-app: ## ArgoCDアプリケーションを作成
	@echo "📱 ArgoCDアプリケーションを作成..."
	kubectl apply -f gitops/argocd/application.yaml
	@echo "✓ アプリケーション作成完了"

argocd-appset: ## ArgoCDアプリケーションセットを作成（複数環境）
	@echo "📱 ArgoCDアプリケーションセットを作成..."
	kubectl apply -f gitops/argocd/applicationset.yaml
	@echo "✓ アプリケーションセット作成完了"

argocd-notifications: ## ArgoCD通知を設定
	kubectl apply -f gitops/argocd/notifications.yaml

argocd-port-forward: ## ArgoCDダッシュボードにアクセス
	@echo "🌐 ArgoCD: https://localhost:8080"
	kubectl port-forward svc/argocd-server -n argocd 8080:443

# ============================================
# 監視・コスト
# ============================================
status: ## システムステータスダッシュボードを表示
	@./scripts/status_dashboard.sh

status-watch: ## システムステータスを監視（自動更新）
	@./scripts/status_dashboard.sh --watch

cost: ## 日次コストレポートを表示
	@./scripts/cost_tracker.sh --daily

cost-monthly: ## 月次コストレポートを表示
	@./scripts/cost_tracker.sh --monthly

cost-forecast: ## コスト予測を表示
	@./scripts/cost_tracker.sh --forecast

cost-alert: ## 予算アラートをチェック
	@./scripts/cost_tracker.sh --alert

verify-backup: ## バックアップを検証
	@echo "🔍 バックアップを検証..."
	@sudo ./scripts/verify_backup.sh --quick

verify-backup-full: ## バックアップをフル検証（テスト復元含む）
	@echo "🔍 バックアップをフル検証..."
	@sudo ./scripts/verify_backup.sh --full

benchmark: ## パフォーマンスベンチマークを実行
	@echo "📊 ベンチマークを実行..."
	@./scripts/benchmark.sh

seed-data: ## サンプルデータを生成
	@echo "🌱 サンプルデータを生成..."
	@./scripts/seed_data.sh

# ============================================
# ドキュメント
# ============================================
docs-serve: ## ドキュメントサーバーを起動（Pythonの簡易サーバー）
	@echo "📚 ドキュメントサーバーを起動: http://localhost:8000"
	python3 -m http.server 8000 --directory docs

docs-api: ## OpenAPI仕様書を表示
	@echo "📖 API仕様書: docs/openapi.yaml"
	@cat docs/openapi.yaml

# ============================================
# ワンライナー
# ============================================
quick-deploy: setup-env setup-dirs prod health ## クイックデプロイ（全自動）

quick-update: git-pull prod-down prod health ## クイック更新（全自動）

test-all: validate e2e-test load-test-quick ## 全テストを実行

deploy-k8s: helm-deps helm-install ## Kubernetesにデプロイ

deploy-gitops: argocd-project argocd-appset ## GitOpsでデプロイ
