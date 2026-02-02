# Development Guide

## 🚀 開発環境クイックスタート

### 最小構成（PostgreSQL + OpenNotebook）

```bash
# 最小構成の起動
docker compose -f docker-compose.minimal.yml up -d

# ログ確認
docker compose -f docker-compose.minimal.yml logs -f

# 停止
docker compose -f docker-compose.minimal.yml down
```

**アクセス先:**
- OpenNotebook: http://localhost:8080
- PostgreSQL: localhost:5432

### 完全開発環境（全サービス）

```bash
# 開発環境の起動
make dev

# または手動で
docker compose -f docker-compose.dev.yml up -d

# ログ確認
docker compose -f docker-compose.dev.yml logs -f

# 停止
docker compose -f docker-compose.dev.yml down
```

**アクセス先:**
- OpenClaw: http://localhost:3000
- N8N: http://localhost:5678 (admin / dev_admin_password_change_in_prod)
- OpenNotebook: http://localhost:8080
- PostgreSQL: localhost:5432

## 🔍 ヘルスチェック

```bash
# OpenNotebook
curl http://localhost:8080/health | jq .

# PostgreSQL
docker compose -f docker-compose.minimal.yml exec postgres psql -U openclaw -c "SELECT version();"

# データベーススキーマ確認
docker compose -f docker-compose.minimal.yml exec postgres psql -U openclaw -c "\dn"
```

## 🛠️ 開発ワークフロー

### 1. スキルの開発（OpenClaw）

```bash
# skills/ディレクトリにスキルを追加
vim skills/my-custom-skill.js

# OpenClawコンテナが自動的にリロード（開発モード）
docker compose -f docker-compose.dev.yml restart openclaw
```

### 2. データベーススキーマの変更

```bash
# docker/postgres/init/01-init.sql を編集

# データベースを再作成（開発環境のみ）
docker compose -f docker-compose.minimal.yml down -v
docker compose -f docker-compose.minimal.yml up -d
```

### 3. ログの確認

```bash
# すべてのログ
docker compose -f docker-compose.minimal.yml logs -f

# 特定のサービス
docker compose -f docker-compose.minimal.yml logs -f opennotebook

# ログファイル
tail -f logs/opennotebook/*.log
```

## 🧪 テスト

### API テスト

```bash
# OpenNotebook ヘルスチェック
curl http://localhost:8080/health

# OpenNotebook ノートブック一覧
curl http://localhost:8080/api/v1/notebooks

# PostgreSQL接続テスト
docker compose -f docker-compose.minimal.yml exec postgres \
  psql -U openclaw -c "SELECT * FROM opennotebook.notebooks LIMIT 5;"
```

## 🐛 デバッグ

### コンテナ内部アクセス

```bash
# OpenNotebook
docker compose -f docker-compose.minimal.yml exec opennotebook sh

# PostgreSQL
docker compose -f docker-compose.minimal.yml exec postgres sh
```

### ログレベルの変更

```bash
# .envファイルを編集
LOG_LEVEL=debug

# コンテナ再起動
docker compose -f docker-compose.minimal.yml restart opennotebook
```

## 📊 パフォーマンス監視

```bash
# リソース使用状況
docker stats

# 特定のコンテナ
docker stats openclaw-opennotebook-minimal openclaw-postgres-minimal
```

## 🧹 クリーンアップ

```bash
# コンテナ停止とボリューム削除
docker compose -f docker-compose.minimal.yml down -v

# すべてのDocker リソースをクリーンアップ
docker system prune -a --volumes

# ログファイルのクリーンアップ
rm -rf logs/*
```

## 📝 トラブルシューティング

### OpenNotebookが起動しない

```bash
# ログ確認
docker compose -f docker-compose.minimal.yml logs opennotebook

# コンテナ再ビルド
docker compose -f docker-compose.minimal.yml build --no-cache opennotebook
docker compose -f docker-compose.minimal.yml up -d opennotebook
```

### PostgreSQLに接続できない

```bash
# PostgreSQLの状態確認
docker compose -f docker-compose.minimal.yml ps postgres

# 接続テスト
docker compose -f docker-compose.minimal.yml exec postgres \
  psql -U openclaw -c "SELECT 1;"
```

### ポート競合

```bash
# 使用中のポートを確認
sudo lsof -i :8080
sudo lsof -i :5432

# 別のポートを使用
# docker-compose.minimal.ymlのportsを変更
```

## 🔐 セキュリティノート

開発環境では以下のセキュリティ制約が緩和されています：

- ✅ ポートが0.0.0.0にバインド（外部からアクセス可能）
- ✅ デバッグモードが有効
- ✅ 詳細なログ出力
- ⚠️ **本番環境では必ずdocker-compose.production.ymlを使用してください**

## 📚 次のステップ

- [ARCHITECTURE.md](ARCHITECTURE.md) - システムアーキテクチャ
- [DEPLOYMENT.md](DEPLOYMENT.md) - 本番デプロイメント
- [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) - 運用ガイド
