# トラブルシューティングガイド

OpenClaw VPS環境でよくある問題とその解決方法をまとめています。

## 📋 目次

1. [セットアップ時の問題](#セットアップ時の問題)
2. [コンテナ起動の問題](#コンテナ起動の問題)
3. [データベース接続の問題](#データベース接続の問題)
4. [ネットワークの問題](#ネットワークの問題)
5. [パフォーマンスの問題](#パフォーマンスの問題)
6. [セキュリティの問題](#セキュリティの問題)
7. [バックアップ・復元の問題](#バックアップ復元の問題)

---

## セットアップ時の問題

### Q1: `setup.sh`が失敗する

**症状:**
```bash
./setup.sh
bash: ./setup.sh: Permission denied
```

**解決方法:**
```bash
# 実行権限を付与
chmod +x setup.sh

# root権限で実行
sudo ./setup.sh
```

### Q2: .envファイルが見つからない

**症状:**
```
Error: .env file not found
```

**解決方法:**
```bash
# .env.exampleからコピー
cp .env.example .env

# または Makefileを使用
make setup-env

# .envを編集
nano .env
```

### Q3: Docker Composeのバージョンエラー

**症状:**
```
ERROR: The Compose file is invalid
```

**解決方法:**
```bash
# Docker Composeバージョン確認
docker compose version

# v2が必要（v1の場合はアップグレード）
sudo apt update
sudo apt install docker-compose-plugin
```

---

## コンテナ起動の問題

### Q4: コンテナが起動しない

**診断手順:**
```bash
# 1. コンテナ状態確認
docker compose -f docker-compose.production.yml ps

# 2. ログ確認
docker compose -f docker-compose.production.yml logs <サービス名>

# 3. 設定検証
docker compose -f docker-compose.production.yml config
```

**よくある原因:**

#### ポート競合
```bash
# ポート使用状況確認
sudo ss -tuln | grep ':80\|:443\|:5432'

# 競合プロセスを停止
sudo systemctl stop apache2  # 例: Apache
sudo systemctl stop nginx    # 例: システムのNginx
```

#### メモリ不足
```bash
# メモリ使用状況確認
free -h

# 不要なコンテナを停止
docker container prune
```

#### 権限エラー
```bash
# データディレクトリの権限修正
sudo chown -R 1000:1000 data logs
```

### Q5: PostgreSQLが起動しない

**症状:**
```
FATAL: password authentication failed
```

**解決方法:**
```bash
# 1. .envのパスワード確認
grep POSTGRES_PASSWORD .env

# 2. ボリュームを削除して再作成
docker compose -f docker-compose.production.yml down -v
sudo rm -rf data/postgres/*
docker compose -f docker-compose.production.yml up -d postgres

# 3. ログ確認
docker compose -f docker-compose.production.yml logs postgres
```

### Q6: Nginxが起動しない

**症状:**
```
nginx: [emerg] cannot load certificate
```

**解決方法:**
```bash
# SSL証明書ファイルの確認
ls -l docker/nginx/ssl/

# 自己署名証明書を生成（開発環境）
cd docker/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout privkey.pem \
  -out fullchain.pem \
  -subj "/C=JP/ST=Tokyo/L=Tokyo/O=OpenClaw/CN=localhost"
chmod 644 fullchain.pem
chmod 600 privkey.pem

# Let's Encrypt証明書を取得（本番環境）
make ssl DOMAIN=your-domain.com EMAIL=your-email@example.com
```

---

## データベース接続の問題

### Q7: アプリがデータベースに接続できない

**診断手順:**
```bash
# 1. PostgreSQLコンテナが実行中か確認
docker compose -f docker-compose.production.yml ps postgres

# 2. データベース接続テスト
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -c "SELECT version();"

# 3. ネットワーク確認
docker network ls | grep backend
docker network inspect vps-automation-openclaw_backend
```

**解決方法:**
```bash
# 環境変数を確認
docker compose -f docker-compose.production.yml exec openclaw env | grep DATABASE

# DATABASE_URLが正しいか確認
# 例: postgresql://openclaw:password@postgres:5432/openclaw
```

### Q8: データベースが応答しない

**症状:**
```
could not connect to server: Connection refused
```

**解決方法:**
```bash
# 1. PostgreSQLのヘルスチェック
docker compose -f docker-compose.production.yml exec postgres pg_isready

# 2. max_connectionsを確認
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -c "SHOW max_connections;"

# 3. 接続数を確認
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -c "SELECT count(*) FROM pg_stat_activity;"

# 4. 必要に応じて再起動
docker compose -f docker-compose.production.yml restart postgres
```

---

## ネットワークの問題

### Q9: コンテナ間通信ができない

**診断手順:**
```bash
# 1. ネットワーク一覧
docker network ls

# 2. コンテナのネットワーク接続確認
docker compose -f docker-compose.production.yml exec openclaw \
  ping -c 3 postgres

# 3. DNSリゾルブ確認
docker compose -f docker-compose.production.yml exec openclaw \
  nslookup postgres
```

**解決方法:**
```bash
# ネットワークを再作成
docker compose -f docker-compose.production.yml down
docker network prune
docker compose -f docker-compose.production.yml up -d
```

### Q10: 外部からアクセスできない

**診断手順:**
```bash
# 1. ファイアウォール確認
sudo ufw status

# 2. ポート確認
sudo ss -tuln | grep ':80\|:443'

# 3. Nginxステータス
docker compose -f docker-compose.production.yml exec nginx nginx -t
```

**解決方法:**
```bash
# UFWでポート開放
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload

# Nginxリロード
docker compose -f docker-compose.production.yml restart nginx
```

---

## パフォーマンスの問題

### Q11: システムが遅い

**診断手順:**
```bash
# 1. リソース使用状況
docker stats --no-stream

# 2. ディスクI/O
iostat -x 1 5

# 3. ログサイズ確認
du -sh logs/*
sudo journalctl --disk-usage
```

**解決方法:**
```bash
# 1. 未使用リソースのクリーンアップ
make clean

# 2. ログローテーション
sudo journalctl --vacuum-time=7d
sudo ./scripts/maintenance.sh

# 3. リソース制限の調整（docker-compose.production.yml）
# memory: 2G → 4G に変更など
```

### Q12: データベースが遅い

**診断手順:**
```bash
# 1. スロークエリログ確認
docker compose -f docker-compose.production.yml logs postgres | grep "duration"

# 2. インデックス確認
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -c "\di"

# 3. バキューム実行
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -c "VACUUM ANALYZE;"
```

---

## セキュリティの問題

### Q13: セキュリティスキャンで脆弱性が検出された

**対応手順:**
```bash
# 1. 詳細レポート確認
cat security-reports/trivy_scan_*.txt

# 2. イメージを更新
docker compose -f docker-compose.production.yml pull

# 3. 再ビルド
docker compose -f docker-compose.production.yml build --no-cache

# 4. 再スキャン
make scan
```

### Q14: 不審なログイン試行がある

**対応手順:**
```bash
# 1. Fail2banステータス確認
sudo fail2ban-client status sshd

# 2. バンされたIP確認
sudo fail2ban-client get sshd banned

# 3. ログ確認
sudo grep "Failed password" /var/log/auth.log | tail -20

# 4. 必要に応じてIP許可リスト設定
sudo ufw allow from <trusted-ip> to any port 22
```

---

## バックアップ・復元の問題

### Q15: バックアップが失敗する

**診断手順:**
```bash
# 1. ディスク容量確認
df -h /opt/backups

# 2. 権限確認
ls -la /opt/backups/openclaw/

# 3. 手動バックアップ実行
sudo ./scripts/backup.sh --db-only
```

**解決方法:**
```bash
# 1. ディスク容量を確保
sudo ./scripts/maintenance.sh

# 2. バックアップディレクトリ作成
sudo mkdir -p /opt/backups/openclaw
sudo chown -R $(whoami):$(whoami) /opt/backups

# 3. 古いバックアップを削除
find /opt/backups/openclaw -mtime +30 -delete
```

### Q16: 復元が失敗する

**対応手順:**
```bash
# 1. バックアップファイルの整合性確認
tar -tzf /opt/backups/openclaw/backup_*/volumes.tar.gz | head

# 2. PostgreSQLダンプ確認
head /opt/backups/openclaw/backup_*/postgres_dump.sql

# 3. 段階的復元
# 3.1 データベースのみ
sudo ./scripts/restore.sh --db-only /opt/backups/openclaw/backup_YYYYMMDD_HHMMSS

# 3.2 ボリュームのみ
sudo ./scripts/restore.sh --volumes-only /opt/backups/openclaw/backup_YYYYMMDD_HHMMSS
```

---

## よくあるエラーメッセージ

### ERROR: Network not found

**解決方法:**
```bash
docker compose -f docker-compose.production.yml down
docker network prune
docker compose -f docker-compose.production.yml up -d
```

### ERROR: Volume is in use

**解決方法:**
```bash
# すべてのコンテナを停止
docker compose -f docker-compose.production.yml down

# 強制削除
docker volume rm <ボリューム名> --force
```

### ERROR: Bind for 0.0.0.0:XXX failed

**解決方法:**
```bash
# ポート使用プロセスを特定
sudo lsof -i :XXX

# プロセスを停止
sudo systemctl stop <サービス名>
```

---

## デバッグコマンド集

### ログ関連
```bash
# すべてのログ
docker compose -f docker-compose.production.yml logs

# 特定サービスのログ
docker compose -f docker-compose.production.yml logs -f postgres

# 最後の100行
docker compose -f docker-compose.production.yml logs --tail=100

# エラーのみ
docker compose -f docker-compose.production.yml logs | grep -i error
```

### コンテナ情報
```bash
# コンテナ一覧
docker ps -a

# コンテナ詳細
docker inspect <コンテナ名>

# リソース使用状況
docker stats

# プロセス一覧
docker compose -f docker-compose.production.yml top
```

### ネットワーク情報
```bash
# ネットワーク一覧
docker network ls

# ネットワーク詳細
docker network inspect <ネットワーク名>

# コンテナのIPアドレス
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <コンテナ名>
```

---

## サポート

問題が解決しない場合:

1. **ログを収集**
   ```bash
   docker compose -f docker-compose.production.yml logs > debug.log
   ./scripts/health_check.sh > health.log
   ```

2. **GitHub Issueを作成**
   - [Issues](https://github.com/nao1234g/vps-automation-openclaw/issues)
   - ログファイルを添付
   - 環境情報（OS、Dockerバージョン）を記載

3. **コミュニティに質問**
   - Discord
   - Telegram

---

**💡 Tip**: 問題が発生したら、まず`make health`と`make validate`を実行して全体的な状態を確認しましょう。
