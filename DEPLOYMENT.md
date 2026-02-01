# デプロイメントガイド

OpenClaw VPS環境のデプロイ手順書です。

## 📋 前提条件

### VPSサーバー要件
- Ubuntu 22.04 LTS or 24.04 LTS
- 最低スペック: 2GB RAM, 2 vCPU, 40GB SSD
- 推奨スペック: 4GB RAM, 4 vCPU, 80GB SSD
- グローバルIPアドレス
- ドメイン名（SSL証明書用、オプション）

### ローカル環境
- SSH クライアント
- Git
- テキストエディタ

## 🚀 デプロイ手順

### Step 1: VPSへのSSH接続

```bash
# SSH鍵認証で接続
ssh -i ~/.ssh/your_key root@your_vps_ip

# または公開鍵を登録済みの場合
ssh root@your_vps_ip
```

### Step 2: リポジトリのクローン

```bash
# プロジェクトディレクトリに移動
cd /opt

# リポジトリをクローン
git clone https://github.com/YOUR_USERNAME/vps-automation-openclaw.git
cd vps-automation-openclaw
```

### Step 3: 初期セットアップ

```bash
# セットアップスクリプトを実行
sudo ./setup.sh
```

セットアップウィザードが以下を対話的に設定します:
1. VPSセキュリティ設定（UFW, Fail2ban）
2. SSH鍵認証の確認
3. Dockerのセキュアインストール
4. 環境変数の設定
5. SSL証明書の取得（オプション）
6. Cron自動化の設定

### Step 4: 環境変数の設定

`.env`ファイルを編集して必要な環境変数を設定:

```bash
nano .env
```

**必須設定項目:**

```bash
# Database
POSTGRES_PASSWORD=<ランダムな強力なパスワード>

# LLM Providers
ANTHROPIC_API_KEY=<AnthropicのAPIキー>
OPENAI_API_KEY=<OpenAIのAPIキー>
ZHIPUAI_API_KEY=<ZhipuAIのAPIキー>

# Telegram Bot
TELEGRAM_BOT_TOKEN=<TelegramのBotトークン>
TELEGRAM_CHAT_ID=<TelegramのチャットID>

# N8N
N8N_PASSWORD=<N8Nの管理者パスワード>
N8N_ENCRYPTION_KEY=<ランダムな32文字>

# OpenNotebook
OPENNOTEBOOK_API_KEY=<ランダムな32文字>

# Security
SESSION_SECRET=<ランダムな32文字>
JWT_SECRET=<ランダムな32文字>

# SSL/Domain (オプション)
DOMAIN_NAME=<your-domain.com>
SSL_EMAIL=<your-email@example.com>
```

**パスワード生成:**
```bash
openssl rand -base64 32
```

保存後、パーミッションを設定:
```bash
chmod 600 .env
```

### Step 5: データディレクトリの作成

```bash
# データディレクトリを作成
sudo mkdir -p data/{postgres,openclaw,n8n,opennotebook,opennotebook_uploads}
sudo mkdir -p logs/{openclaw,n8n,opennotebook}

# パーミッション設定
sudo chown -R 1000:1000 data logs
```

### Step 6: 本番環境のデプロイ

```bash
# 本番用Docker Composeで起動
docker compose -f docker-compose.production.yml up -d
```

### Step 7: ヘルスチェック

```bash
# すべてのサービスが正常に起動したか確認
docker compose -f docker-compose.production.yml ps

# ヘルスチェックスクリプトを実行
./scripts/health_check.sh
```

### Step 8: アクセス確認

#### HTTPSアクセス（SSL証明書設定済みの場合）
```bash
https://your-domain.com/          # OpenClaw
https://your-domain.com/n8n/      # N8N
https://your-domain.com/notebook/ # OpenNotebook
```

#### HTTPアクセス（SSL未設定の場合）
```bash
http://your_vps_ip/          # OpenClaw
http://your_vps_ip/n8n/      # N8N
http://your_vps_ip/notebook/ # OpenNotebook
```

## 🔒 SSL証明書の取得（後から設定する場合）

```bash
sudo ./scripts/setup_ssl.sh your-domain.com your-email@example.com
```

## 📊 運用タスク

### 日次

#### バックアップ
```bash
sudo ./scripts/backup.sh
```

#### ヘルスチェック
```bash
./scripts/health_check.sh
```

### 週次

#### セキュリティスキャン
```bash
./scripts/security_scan.sh
```

### 月次

#### システムメンテナンス
```bash
sudo ./scripts/maintenance.sh
```

## 🛠️ トラブルシューティング

### コンテナが起動しない

```bash
# ログを確認
docker compose -f docker-compose.production.yml logs <サービス名>

# 設定の確認
docker compose -f docker-compose.production.yml config

# 再起動
docker compose -f docker-compose.production.yml restart <サービス名>
```

### データベース接続エラー

```bash
# PostgreSQL接続テスト
docker compose -f docker-compose.production.yml exec postgres psql -U openclaw -c "SELECT version();"

# パスワード確認
grep POSTGRES_PASSWORD .env

# データベースログ確認
docker compose -f docker-compose.production.yml logs postgres
```

### ディスク容量不足

```bash
# ディスク使用状況確認
df -h

# Dockerクリーンアップ
docker system prune -a --volumes

# 古いバックアップ削除
find /opt/backups -mtime +30 -delete
```

### Nginxエラー

```bash
# Nginx設定テスト
docker compose -f docker-compose.production.yml exec nginx nginx -t

# Nginxログ確認
docker compose -f docker-compose.production.yml logs nginx

# Nginx再起動
docker compose -f docker-compose.production.yml restart nginx
```

## 🔄 アップデート手順

### アプリケーションコードの更新

```bash
# 最新コードを取得
git pull origin main

# コンテナを再ビルド
docker compose -f docker-compose.production.yml build

# 再起動
docker compose -f docker-compose.production.yml up -d
```

### Dockerイメージの更新

```bash
# イメージを更新
docker compose -f docker-compose.production.yml pull

# 再起動
docker compose -f docker-compose.production.yml up -d

# 古いイメージを削除
docker image prune -a
```

## 🆘 緊急時対応

### 全サービス停止

```bash
docker compose -f docker-compose.production.yml down
```

### バックアップからの復元

```bash
# 最新バックアップを確認
ls -lht /opt/backups/openclaw/ | head

# 復元実行
sudo ./scripts/restore.sh /opt/backups/openclaw/backup_YYYYMMDD_HHMMSS
```

### 完全再起動

```bash
# すべてのコンテナを停止
docker compose -f docker-compose.production.yml down

# ボリュームも削除する場合（注意！）
docker compose -f docker-compose.production.yml down -v

# 再起動
docker compose -f docker-compose.production.yml up -d
```

## 📚 参考ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [README.md](README.md) | プロジェクト概要 |
| [QUICKSTART_SECURITY.md](QUICKSTART_SECURITY.md) | 5分セットアップ |
| [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) | セキュリティチェックリスト |
| [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) | 運用マニュアル |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | コマンド早見表 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | システムアーキテクチャ |
| [docs/SSH_KEY_SETUP.md](docs/SSH_KEY_SETUP.md) | SSH設定ガイド |

## ✅ デプロイチェックリスト

デプロイ前の確認事項:

- [ ] VPSのスペックが要件を満たしている
- [ ] SSHキー認証が設定済み
- [ ] `.env`ファイルがすべて設定済み
- [ ] データディレクトリが作成済み
- [ ] UFW/Fail2banが設定済み
- [ ] Dockerがインストール済み

デプロイ後の確認事項:

- [ ] すべてのコンテナが正常起動
- [ ] ヘルスチェックが全てPASS
- [ ] HTTPSでアクセス可能（SSL設定済みの場合）
- [ ] N8Nにログイン可能
- [ ] OpenNotebookにアクセス可能
- [ ] バックアップが正常に動作
- [ ] Cronジョブが設定済み

## 🎉 デプロイ完了

おめでとうございます！OpenClaw VPS環境のデプロイが完了しました。

安全で自動化されたVPS運用をお楽しみください！

---

**サポートが必要な場合は [GitHub Issues](https://github.com/nao1234g/vps-automation-openclaw/issues) で質問してください。**
