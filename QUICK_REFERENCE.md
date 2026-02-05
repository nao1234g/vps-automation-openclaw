# クイックリファレンスカード

VPS運用でよく使うコマンドの早見表です。

## 🚀 セットアップ

```bash
# 完全自動セットアップ
sudo ./setup.sh
```

## 📊 日常運用

### ヘルスチェック
```bash
./scripts/health_check.sh
```

### バックアップ
```bash
# 完全バックアップ
sudo ./scripts/backup.sh

# データベースのみ
sudo ./scripts/backup.sh --db-only

# ボリュームのみ
sudo ./scripts/backup.sh --volumes-only
```

### セキュリティスキャン
```bash
# 完全スキャン
./scripts/security_scan.sh --all

# イメージのみ
./scripts/security_scan.sh --images-only

# システムのみ
./scripts/security_scan.sh --system-only
```

### メンテナンス
```bash
# プレビュー（削除なし）
sudo ./scripts/maintenance.sh --dry-run

# 実行
sudo ./scripts/maintenance.sh

# 積極的クリーンアップ
sudo ./scripts/maintenance.sh --aggressive
```

### OpenClaw ペアリング確認
```bash
# ペアリング状態確認
./scripts/check_openclaw_pairing.sh

# 詳細情報付き
./scripts/check_openclaw_pairing.sh --verbose
```

## 🐳 Docker操作

### コンテナ管理
```bash
# 起動
docker compose up -d

# 停止
docker compose down

# 再起動
docker compose restart

# 状態確認
docker compose ps

# ログ確認
docker compose logs -f
docker compose logs -f <サービス名>
```

### イメージ管理
```bash
# イメージ一覧
docker images

# イメージ更新
docker compose pull

# 未使用イメージ削除
docker image prune -a
```

### ボリューム管理
```bash
# ボリューム一覧
docker volume ls

# ボリューム詳細
docker volume inspect <ボリューム名>

# 未使用ボリューム削除
docker volume prune
```

## 🔒 セキュリティ

### UFW（ファイアウォール）
```bash
# 状態確認
sudo ufw status verbose

# ポート開放
sudo ufw allow <ポート>/tcp

# ルール削除
sudo ufw status numbered
sudo ufw delete <番号>

# 有効化/無効化
sudo ufw enable
sudo ufw disable
```

### Fail2ban
```bash
# 状態確認
sudo fail2ban-client status
sudo fail2ban-client status sshd

# バン解除
sudo fail2ban-client set sshd unbanip <IPアドレス>

# ログ確認
sudo tail -f /var/log/fail2ban.log
```

### SSL証明書
```bash
# 証明書情報
openssl x509 -in docker/nginx/ssl/fullchain.pem -text -noout

# 有効期限確認
openssl x509 -in docker/nginx/ssl/fullchain.pem -noout -dates

# 手動更新
sudo certbot renew

# 強制更新
sudo certbot renew --force-renewal
```

## 💾 バックアップ・復元

### バックアップ一覧
```bash
ls -lht /opt/backups/openclaw/
```

### 復元
```bash
# 完全復元
sudo ./scripts/restore.sh /opt/backups/openclaw/backup_YYYYMMDD_HHMMSS

# データベースのみ
sudo ./scripts/restore.sh --db-only <バックアップパス>

# ボリュームのみ
sudo ./scripts/restore.sh --volumes-only <バックアップパス>

# 確認なし（危険）
sudo ./scripts/restore.sh --force <バックアップパス>
```

## 🔍 監視・ログ

### システムリソース
```bash
# ディスク使用量
df -h
du -sh /var/lib/docker
du -sh /opt/backups

# メモリ使用量
free -h

# CPU使用率
top
htop

# プロセス確認
ps aux | grep docker
```

### ログ確認
```bash
# システムログ
sudo journalctl -f
sudo journalctl -u docker.service -f

# 本日のエラー
sudo journalctl -p err -S today

# Dockerログ
docker compose logs -f
docker compose logs --tail=100 <サービス名>

# Nginxログ
docker compose exec nginx tail -f /var/log/nginx/access.log
docker compose exec nginx tail -f /var/log/nginx/error.log
```

## 🛠️ トラブルシューティング

### コンテナデバッグ
```bash
# コンテナ内でコマンド実行
docker compose exec <サービス名> sh
docker compose exec <サービス名> bash

# コンテナ情報
docker inspect <コンテナ名>

# リソース使用状況
docker stats

# ネットワーク確認
docker network ls
docker network inspect <ネットワーク名>
```

### データベース
```bash
# PostgreSQL接続
docker compose exec db psql -U openclaw

# データベース一覧
docker compose exec db psql -U openclaw -c "\l"

# テーブル一覧
docker compose exec db psql -U openclaw -d openclaw -c "\dt"

# バキューム
docker compose exec db psql -U openclaw -c "VACUUM ANALYZE;"
```

### Nginx
```bash
# 設定テスト
docker compose exec nginx nginx -t

# リロード
docker compose exec nginx nginx -s reload

# アクセスログリアルタイム
docker compose exec nginx tail -f /var/log/nginx/access.log
```

## 📦 環境変数

### .env編集
```bash
nano .env
chmod 600 .env
```

### パスワード生成
```bash
# 32文字のランダム文字列
openssl rand -base64 32

# 64文字
openssl rand -base64 48

# pwgen使用（要インストール）
pwgen -s 32 1
```

## 🔄 アップデート

### システムアップデート
```bash
sudo apt update
sudo apt upgrade -y
```

### Dockerイメージ更新
```bash
docker compose pull
docker compose up -d
docker image prune -a
```

## 📞 緊急時

### 全サービス停止
```bash
docker compose down
```

### 全サービス強制停止
```bash
docker compose kill
```

### 復旧
```bash
# 最新バックアップから復元
LATEST=$(ls -t /opt/backups/openclaw/backup_* | head -1)
sudo ./scripts/restore.sh $LATEST
```

## 📚 ドキュメント

| ファイル | 内容 |
|---------|------|
| [QUICKSTART_SECURITY.md](QUICKSTART_SECURITY.md) | 5分セットアップ |
| [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) | セキュリティチェックリスト |
| [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) | 運用マニュアル |
| [docs/SSH_KEY_SETUP.md](docs/SSH_KEY_SETUP.md) | SSH設定ガイド |

## 🆘 ヘルプ

### コマンドヘルプ
```bash
# スクリプトヘルプ
./scripts/backup.sh --help
./scripts/restore.sh --help

# Dockerヘルプ
docker compose --help
docker --help
```

### サポート
- GitHub Issues: [vps-automation-openclaw/issues](https://github.com/nao1234g/vps-automation-openclaw/issues)
- ドキュメント: README.md

---

**印刷して手元に置いておくと便利です！**
