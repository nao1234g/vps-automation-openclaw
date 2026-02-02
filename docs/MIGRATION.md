# Migration Guide

他のデプロイメント環境からOpenClaw VPSスタックへの移行ガイド

## 📋 目次

- [概要](#概要)
- [移行前の準備](#移行前の準備)
- [Docker Composeからの移行](#docker-composeからの移行)
- [Kubernetesからの移行](#kubernetesからの移行)
- [手動デプロイからの移行](#手動デプロイからの移行)
- [データ移行](#データ移行)
- [トラブルシューティング](#トラブルシューティング)

---

## 概要

このガイドでは、既存の環境から OpenClaw VPS スタックへの移行手順を説明します。

### 移行の利点

✅ **セキュリティ強化**: 10層のセキュリティ防御
✅ **自動化**: ワンコマンドでデプロイ・運用
✅ **監視統合**: Prometheus + Grafana による可視化
✅ **簡単なバックアップ**: 自動バックアップ・リストア機能
✅ **ドキュメント完備**: 19種類の詳細ドキュメント

---

## 移行前の準備

### 1. システム要件の確認

```bash
# 最低要件
CPU: 2コア
RAM: 4GB
Disk: 40GB SSD
OS: Ubuntu 22.04 LTS / 24.04 LTS

# 推奨スペック
CPU: 4コア
RAM: 8GB
Disk: 80GB SSD
```

### 2. 現在の環境のバックアップ

**重要**: 移行前に必ず現在の環境をバックアップしてください。

```bash
# データベースバックアップ
pg_dump -U <username> <database> > backup_$(date +%Y%m%d).sql

# ファイルバックアップ
tar -czf app_backup_$(date +%Y%m%d).tar.gz /path/to/app

# 設定ファイルバックアップ
cp -r /etc/nginx /backup/nginx_config
cp .env /backup/.env.backup
```

### 3. 環境変数の整理

現在使用している環境変数をリストアップ:

```bash
# 既存の環境変数をエクスポート
printenv | grep -E "POSTGRES|API|TOKEN|SECRET" > existing_env.txt
```

---

## Docker Composeからの移行

### 既存のDocker Compose環境から移行する場合

#### Step 1: 既存コンテナの停止とデータ抽出

```bash
# コンテナを停止（削除はしない）
docker compose down

# データボリュームのバックアップ
docker run --rm \
  -v your_postgres_volume:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_data.tar.gz /data

docker run --rm \
  -v your_app_volume:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/app_data.tar.gz /data
```

#### Step 2: OpenClaw VPSのセットアップ

```bash
# リポジトリをクローン
cd /opt
sudo git clone https://github.com/nao1234g/vps-automation-openclaw.git
cd vps-automation-openclaw

# セットアップウィザード実行
sudo ./setup.sh
```

#### Step 3: 環境変数の移行

既存の`.env`から必要な値をコピー:

```bash
# OpenClaw VPSの.envを編集
nano .env
```

以下の項目を既存環境から移行:

```env
# データベース設定
POSTGRES_PASSWORD=<既存のパスワード>

# API キー
ANTHROPIC_API_KEY=<既存のキー>
TELEGRAM_BOT_TOKEN=<既存のトークン>

# その他のシークレット
<必要に応じて追加>
```

#### Step 4: データの復元

```bash
# PostgreSQLデータ復元
cat postgres_data.tar.gz | docker compose -f docker-compose.production.yml exec -T postgres \
  tar xzf - -C /var/lib/postgresql/data

# または SQLダンプから復元
docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U openclaw < backup_20240201.sql
```

#### Step 5: サービス起動とヘルスチェック

```bash
# サービス起動
make prod

# ヘルスチェック
./scripts/health_check.sh
```

### docker-compose.ymlの設定対応表

| 既存設定 | OpenClaw VPS設定 | 場所 |
|---------|----------------|------|
| `ports` | `ports` | docker-compose.production.yml |
| `environment` | `.env` | .env ファイル |
| `volumes` | `volumes` | docker-compose.production.yml |
| `networks` | `frontend/backend` | docker-compose.production.yml |

---

## Kubernetesからの移行

### 既存のKubernetes環境から移行する場合

#### Step 1: Kubernetes リソースのバックアップ

```bash
# 全リソースをYAMLでエクスポート
kubectl get all -o yaml > k8s_backup.yaml

# ConfigMapとSecretをエクスポート
kubectl get configmap -o yaml > configmaps.yaml
kubectl get secret -o yaml > secrets.yaml
```

#### Step 2: データの抽出

```bash
# PostgreSQL PVCからデータをコピー
kubectl cp <postgres-pod>:/var/lib/postgresql/data ./postgres_data

# アプリケーションデータをコピー
kubectl cp <app-pod>:/app/data ./app_data
```

#### Step 3: Kubernetes設定の変換

Kubernetesの設定をDocker Compose形式に変換:

| Kubernetes | Docker Compose | 変換方法 |
|-----------|---------------|---------|
| Deployment | service | replicas=1の場合は単一サービス |
| Service | ports | ClusterIPポートをホストポートにマッピング |
| ConfigMap | .env | 環境変数として設定 |
| Secret | .env | Base64デコードして設定 |
| PersistentVolume | volumes | 名前付きボリュームに変換 |
| Ingress | nginx | nginx設定に変換 |

#### Step 4: リソース制限の移行

Kubernetes の `resources` を Docker Compose の `deploy.resources` に変換:

```yaml
# Kubernetes
resources:
  limits:
    cpu: "1"
    memory: "1Gi"
  requests:
    cpu: "500m"
    memory: "512Mi"

# ↓ Docker Compose (docker-compose.production.yml)
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

#### Step 5: OpenClaw VPSへの移行実行

```bash
# セットアップ
cd /opt/vps-automation-openclaw
sudo ./setup.sh

# データ復元
sudo cp -r postgres_data/* data/postgres/
sudo cp -r app_data/* data/openclaw/
sudo chown -R 1000:1000 data/

# 起動
make prod
```

---

## 手動デプロイからの移行

### systemd サービスとして実行している場合

#### Step 1: 現在のサービスを停止

```bash
# サービスを停止
sudo systemctl stop openclaw
sudo systemctl stop n8n
sudo systemctl stop postgres
```

#### Step 2: データのバックアップ

```bash
# PostgreSQLデータ
sudo pg_dumpall -U postgres > /tmp/postgres_full_backup.sql

# アプリケーションデータ
sudo tar -czf /tmp/openclaw_data.tar.gz /var/lib/openclaw
sudo tar -czf /tmp/n8n_data.tar.gz /home/n8n/.n8n
```

#### Step 3: OpenClaw VPSのインストール

```bash
cd /opt
sudo git clone https://github.com/nao1234g/vps-automation-openclaw.git
cd vps-automation-openclaw
sudo ./setup.sh
```

#### Step 4: データの移行

```bash
# PostgreSQL復元
docker compose -f docker-compose.production.yml up -d postgres
sleep 10
cat /tmp/postgres_full_backup.sql | \
  docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U openclaw

# アプリケーションデータ復元
sudo tar -xzf /tmp/openclaw_data.tar.gz -C data/openclaw/
sudo tar -xzf /tmp/n8n_data.tar.gz -C data/n8n/
sudo chown -R 1000:1000 data/
```

#### Step 5: 古いサービスの無効化

```bash
# systemdサービスを無効化
sudo systemctl disable openclaw
sudo systemctl disable n8n
sudo systemctl disable postgres

# サービスファイルを削除（オプション）
sudo rm /etc/systemd/system/openclaw.service
sudo rm /etc/systemd/system/n8n.service
sudo systemctl daemon-reload
```

---

## データ移行

### PostgreSQLデータベース移行

#### 方法1: SQL ダンプを使用（推奨）

```bash
# 1. 既存DBからダンプ
pg_dump -h old-host -U old-user -d old-db > dump.sql

# 2. 新環境で復元
docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U openclaw -d openclaw < dump.sql
```

#### 方法2: データディレクトリ直接コピー

```bash
# 1. 既存PostgreSQLを停止
sudo systemctl stop postgresql

# 2. データディレクトリをコピー
sudo cp -r /var/lib/postgresql/14/main/* /opt/vps-automation-openclaw/data/postgres/

# 3. 所有権変更
sudo chown -R 1000:1000 /opt/vps-automation-openclaw/data/postgres/

# 4. コンテナ起動
docker compose -f docker-compose.production.yml up -d postgres
```

### アプリケーションデータ移行

#### OpenClaw データ

```bash
# 既存データをコピー
sudo cp -r /path/to/existing/openclaw/data/* data/openclaw/
sudo chown -R 1000:1000 data/openclaw/
```

#### N8N ワークフロー移行

```bash
# N8N ワークフローディレクトリをコピー
sudo cp -r ~/.n8n/* data/n8n/
sudo chown -R 1000:1000 data/n8n/
```

### 設定ファイル移行

#### Nginx 設定

既存のNginx設定がある場合:

```bash
# 既存設定を参考にカスタマイズ
sudo cp /etc/nginx/sites-available/openclaw docker/nginx/conf.d/openclaw.conf

# 設定をリロード
docker compose -f docker-compose.production.yml restart nginx
```

---

## 移行後の確認

### チェックリスト

- [ ] 全サービスが起動している
  ```bash
  docker compose -f docker-compose.production.yml ps
  ```

- [ ] ヘルスチェックが成功する
  ```bash
  ./scripts/health_check.sh
  ```

- [ ] データベース接続が正常
  ```bash
  docker compose -f docker-compose.production.yml exec postgres \
    psql -U openclaw -c "SELECT version();"
  ```

- [ ] アプリケーションにアクセス可能
  ```bash
  curl http://localhost:3000/health  # OpenClaw
  curl http://localhost:5678/        # N8N
  curl http://localhost:8080/health  # OpenNotebook
  ```

- [ ] ログにエラーがない
  ```bash
  docker compose -f docker-compose.production.yml logs --tail=50
  ```

- [ ] バックアップが動作する
  ```bash
  sudo ./scripts/backup.sh
  ```

### パフォーマンス確認

```bash
# ベンチマーク実行
./scripts/benchmark.sh --quick

# リソース使用状況確認
docker stats --no-stream
```

---

## トラブルシューティング

### データベース接続エラー

**問題**: アプリケーションがPostgreSQLに接続できない

**解決策**:

```bash
# 1. PostgreSQLが起動しているか確認
docker compose -f docker-compose.production.yml ps postgres

# 2. 接続情報が正しいか確認
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -d openclaw -c "SELECT 1;"

# 3. ネットワーク接続を確認
docker compose -f docker-compose.production.yml exec openclaw \
  ping postgres
```

### ポート競合

**問題**: "port is already allocated"

**解決策**:

```bash
# 1. 競合しているプロセスを確認
sudo lsof -i :5432  # PostgreSQL
sudo lsof -i :3000  # OpenClaw
sudo lsof -i :5678  # N8N

# 2. 既存プロセスを停止
sudo systemctl stop postgresql
sudo systemctl stop openclaw

# 3. または docker-compose.production.yml でポートを変更
```

### パーミッションエラー

**問題**: "permission denied" エラー

**解決策**:

```bash
# データディレクトリの所有権を修正
sudo chown -R 1000:1000 data/
sudo chown -R 1000:1000 logs/

# 再起動
docker compose -f docker-compose.production.yml restart
```

### データが移行されていない

**問題**: データベースが空、またはデータが見つからない

**解決策**:

```bash
# 1. バックアップから再度復元
docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U openclaw -d openclaw < backup.sql

# 2. データディレクトリを確認
ls -la data/postgres/

# 3. ログを確認
docker compose -f docker-compose.production.yml logs postgres
```

---

## ロールバック手順

移行に問題がある場合、以下の手順で元の環境に戻せます:

```bash
# 1. OpenClaw VPS を停止
cd /opt/vps-automation-openclaw
docker compose -f docker-compose.production.yml down

# 2. 元のサービスを復元
sudo systemctl start postgresql
sudo systemctl start openclaw
sudo systemctl start n8n

# 3. データを復元（必要に応じて）
sudo pg_restore -U postgres -d openclaw /backup/postgres_backup.sql
```

---

## 移行後の最適化

### 1. セキュリティスキャン実行

```bash
./scripts/security_scan.sh --all
```

### 2. パフォーマンスチューニング

[PERFORMANCE.md](../PERFORMANCE.md) を参照して最適化:

- PostgreSQL 設定調整
- Nginx キャッシュ設定
- Docker リソース制限の最適化

### 3. 監視の設定

```bash
# 監視スタックを起動
docker compose -f docker-compose.production.yml \
               -f docker-compose.monitoring.yml up -d

# Grafana にアクセス
# http://localhost:3001
```

### 4. 自動バックアップの設定

```bash
# Cron ジョブに追加
sudo crontab -e

# 以下を追加
0 3 * * * /opt/vps-automation-openclaw/scripts/backup.sh
0 2 * * * /opt/vps-automation-openclaw/scripts/security_scan.sh --all
```

---

## 追加リソース

- [DEPLOYMENT.md](../DEPLOYMENT.md) - デプロイメントガイド
- [OPERATIONS_GUIDE.md](../OPERATIONS_GUIDE.md) - 運用マニュアル
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - トラブルシューティング
- [SECURITY_CHECKLIST.md](../SECURITY_CHECKLIST.md) - セキュリティチェックリスト

---

## サポート

移行に関する質問や問題がある場合:

- [GitHub Issues](https://github.com/nao1234g/vps-automation-openclaw/issues)
- [CONTRIBUTING.md](../CONTRIBUTING.md) - コミュニティへの参加方法

---

<div align="center">

**🚀 スムーズな移行をお祈りします！ 🔒**

</div>
