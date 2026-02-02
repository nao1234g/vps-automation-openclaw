# Disaster Recovery Guide

OpenClaw VPS 環境の災害復旧ガイド

このドキュメントでは、予期せぬ障害からシステムを復旧するための手順を説明します。

## 📋 目次

- [概要](#概要)
- [事前準備](#事前準備)
- [障害シナリオと対応](#障害シナリオと対応)
- [復旧手順](#復旧手順)
- [定期テスト](#定期テスト)
- [連絡体制](#連絡体制)

---

## 概要

### 災害復旧計画（DRP）の目的

- **RTO (Recovery Time Objective)**: 目標復旧時間 - 2時間以内
- **RPO (Recovery Point Objective)**: 目標復旧時点 - 24時間以内（日次バックアップの場合）

### 対象範囲

- VPSサーバー障害
- データベース障害
- アプリケーション障害
- ネットワーク障害
- セキュリティインシデント

---

## 事前準備

### 1. バックアップ戦略

#### 自動バックアップの設定

```bash
# Cronジョブに追加
sudo crontab -e

# 日次バックアップ（午前3時）
0 3 * * * /opt/vps-automation-openclaw/scripts/backup.sh

# 週次フルバックアップ（日曜午前2時）
0 2 * * 0 /opt/vps-automation-openclaw/scripts/backup.sh --full
```

#### オフサイトバックアップ

**重要**: 同じVPS内だけでなく、別の場所にもバックアップを保管してください。

```bash
# AWS S3へのバックアップ
aws s3 sync /opt/backups/openclaw/ s3://your-backup-bucket/openclaw/

# rsyncで別サーバーへ
rsync -avz --delete /opt/backups/openclaw/ \
  backup-server:/backups/openclaw/

# Google Driveへのバックアップ（rclone使用）
rclone sync /opt/backups/openclaw/ gdrive:openclaw-backups/
```

### 2. バックアップ内容の確認

```bash
# バックアップディレクトリ構造
/opt/backups/openclaw/
├── backup_20240201_030000/
│   ├── postgres_dump.sql          # PostgreSQL ダンプ
│   ├── volumes/                   # Dockerボリューム
│   │   ├── openclaw_data.tar.gz
│   │   ├── n8n_data.tar.gz
│   │   └── opennotebook_data.tar.gz
│   ├── configs/                   # 設定ファイル
│   │   ├── .env
│   │   ├── nginx.conf
│   │   └── docker-compose.yml
│   └── system_info.txt            # システム情報
```

### 3. ドキュメント整備

以下の情報を安全な場所（パスワードマネージャー等）に保管:

- [ ] VPSプロバイダーのログイン情報
- [ ] SSH秘密鍵のバックアップ
- [ ] `.env` ファイルのバックアップ
- [ ] ドメインレジストラ情報
- [ ] APIキー・トークン一覧
- [ ] 緊急連絡先リスト

### 4. 復旧テスト環境の準備

```bash
# テスト用VPSを別途用意（推奨）
# または、ローカル環境で復旧手順をテスト
```

---

## 障害シナリオと対応

### シナリオ1: VPSサーバー完全障害

**症状**:
- サーバーにSSH接続できない
- Webサービスにアクセスできない
- プロバイダーから障害通知

**緊急対応**:

1. **状況確認**
   ```bash
   # 別の場所から接続テスト
   ping your-vps-ip
   ssh user@your-vps-ip

   # プロバイダーのコントロールパネルで確認
   # - サーバーステータス
   # - ネットワーク状態
   # - ディスク状態
   ```

2. **プロバイダーへの連絡**
   - サポートチケット作成
   - 障害内容と影響範囲を報告
   - 復旧見込み時間を確認

3. **新規VPSへの切り替え判断**
   - 復旧見込み > 2時間 → 新規VPSセットアップ
   - 復旧見込み < 2時間 → 待機

**復旧手順**: [新規VPSへの復旧](#新規vpsへの復旧) を参照

---

### シナリオ2: データベース破損

**症状**:
- PostgreSQLが起動しない
- データベース接続エラー
- データ不整合エラー

**緊急対応**:

1. **エラーログ確認**
   ```bash
   docker compose -f docker-compose.production.yml logs postgres
   ```

2. **PostgreSQL修復試行**
   ```bash
   # コンテナ内でPG修復
   docker compose -f docker-compose.production.yml exec postgres \
     pg_resetwal -f /var/lib/postgresql/data

   # 再起動
   docker compose -f docker-compose.production.yml restart postgres
   ```

3. **修復失敗時: バックアップからの復元**
   ```bash
   # 最新バックアップを確認
   ls -lht /opt/backups/openclaw/

   # 復元実行
   sudo ./scripts/restore.sh /opt/backups/openclaw/backup_20240201_030000
   ```

**復旧手順**: [データベース復旧](#データベース復旧) を参照

---

### シナリオ3: ディスク容量不足

**症状**:
- "No space left on device" エラー
- コンテナが起動しない
- 書き込みエラー

**緊急対応**:

1. **ディスク使用状況確認**
   ```bash
   df -h
   du -sh /var/lib/docker
   du -sh /opt/backups
   ```

2. **即座に容量確保**
   ```bash
   # Dockerの不要なデータ削除
   docker system prune -a --volumes

   # 古いバックアップ削除（30日以上前）
   find /opt/backups/openclaw/ -mtime +30 -delete

   # ログファイル削除
   sudo journalctl --vacuum-time=7d
   sudo truncate -s 0 /var/log/*.log
   ```

3. **ディスク拡張検討**
   ```bash
   # VPSプロバイダーのコントロールパネルでディスク拡張
   # または、より大きなプランへの移行
   ```

---

### シナリオ4: セキュリティ侵害

**症状**:
- 不審なログイン試行
- 予期しないプロセス実行
- データ改ざん
- Fail2banアラート多数

**緊急対応**:

1. **即座にネットワーク隔離**
   ```bash
   # 全ての受信接続をブロック
   sudo ufw deny in

   # または、VPSコントロールパネルでネットワーク無効化
   ```

2. **調査**
   ```bash
   # 不審なプロセス確認
   ps aux | grep -v "\[" | sort -rnk 3 | head

   # ネットワーク接続確認
   sudo netstat -tulpn

   # 最近の変更ファイル確認
   find / -mtime -1 -type f 2>/dev/null | head -50

   # ログ確認
   sudo journalctl -xe
   sudo grep -i "failed\|error" /var/log/auth.log
   ```

3. **セキュリティスキャン実行**
   ```bash
   ./scripts/security_scan.sh --all

   # Rootkit検出
   sudo rkhunter --check
   ```

4. **影響範囲の特定**
   - 侵入経路の特定
   - 漏洩データの確認
   - 改ざんファイルのリストアップ

**復旧手順**:
- **侵害が確認された場合**: [完全再構築](#完全再構築) を実施
- **誤検知の場合**: ファイアウォールを元に戻す

---

### シナリオ5: アプリケーション障害

**症状**:
- 特定サービスが応答しない
- 500エラー頻発
- タイムアウトエラー

**緊急対応**:

1. **サービス状態確認**
   ```bash
   docker compose -f docker-compose.production.yml ps
   docker compose -f docker-compose.production.yml logs --tail=100
   ```

2. **サービス再起動**
   ```bash
   # 特定サービスのみ
   docker compose -f docker-compose.production.yml restart openclaw

   # 全サービス
   docker compose -f docker-compose.production.yml restart
   ```

3. **リソース確認**
   ```bash
   docker stats --no-stream
   free -h
   df -h
   ```

4. **設定ファイル確認**
   ```bash
   # .env の内容確認
   cat .env

   # docker-compose.yml の構文チェック
   docker compose -f docker-compose.production.yml config
   ```

---

## 復旧手順

### 新規VPSへの復旧

**所要時間**: 約1-2時間

#### Step 1: 新規VPSのプロビジョニング（15分）

```bash
# 1. VPSプロバイダーで新規サーバー作成
# - OS: Ubuntu 22.04 LTS / 24.04 LTS
# - スペック: 最低 2vCPU, 4GB RAM, 40GB SSD

# 2. SSH接続テスト
ssh root@new-vps-ip
```

#### Step 2: バックアップファイルの転送（10-30分）

```bash
# 旧VPSからバックアップを取得（可能な場合）
scp -r old-vps:/opt/backups/openclaw/backup_20240201_030000 ./

# または、オフサイトバックアップから取得
aws s3 sync s3://your-backup-bucket/openclaw/backup_20240201_030000 ./backup/
# または
rclone copy gdrive:openclaw-backups/backup_20240201_030000 ./backup/
```

#### Step 3: OpenClaw VPSのセットアップ（5-10分）

```bash
# リポジトリクローン
cd /opt
sudo git clone https://github.com/nao1234g/vps-automation-openclaw.git
cd vps-automation-openclaw

# セットアップウィザード実行
sudo ./setup.sh

# 質問に答える:
# - ドメイン名
# - SSL証明書設定
# - 自動アップデート設定
```

#### Step 4: 環境変数の復元（2分）

```bash
# バックアップから.envを復元
sudo cp /path/to/backup/configs/.env .env
sudo chmod 600 .env

# 内容確認
cat .env
```

#### Step 5: データ復元（10-20分）

```bash
# 復元スクリプト実行
sudo ./scripts/restore.sh /path/to/backup/backup_20240201_030000

# 復元内容確認
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -c "\l"
```

#### Step 6: サービス起動（3-5分）

```bash
# サービス起動
docker compose -f docker-compose.production.yml up -d

# ヘルスチェック
./scripts/health_check.sh
```

#### Step 7: DNS切り替え（5-60分、TTL依存）

```bash
# ドメインレジストラでAレコードを更新
# 旧IP → 新IP

# 伝播確認
dig your-domain.com
nslookup your-domain.com

# SSL証明書再取得（必要な場合）
sudo certbot certonly --standalone -d your-domain.com
```

#### Step 8: 動作確認（10分）

```bash
# 各サービスにアクセス
curl https://your-domain.com/health
curl https://your-domain.com/n8n
curl https://your-domain.com/opennotebook

# ログ確認
docker compose -f docker-compose.production.yml logs --tail=50

# リソース確認
docker stats --no-stream
```

---

### データベース復旧

**所要時間**: 約30分

#### 方法1: バックアップからの完全復元

```bash
# 1. PostgreSQLコンテナ停止
docker compose -f docker-compose.production.yml stop postgres

# 2. 既存データ削除
sudo rm -rf data/postgres/*

# 3. バックアップから復元
sudo tar -xzf /path/to/backup/volumes/postgres_data.tar.gz -C data/postgres/

# 4. 権限修正
sudo chown -R 1000:1000 data/postgres/

# 5. PostgreSQL起動
docker compose -f docker-compose.production.yml up -d postgres

# 6. 接続確認
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -c "SELECT version();"
```

#### 方法2: SQLダンプからの復元

```bash
# 1. PostgreSQL起動
docker compose -f docker-compose.production.yml up -d postgres

# 2. 既存データベース削除（注意！）
docker compose -f docker-compose.production.yml exec postgres \
  psql -U postgres -c "DROP DATABASE openclaw;"

# 3. データベース再作成
docker compose -f docker-compose.production.yml exec postgres \
  psql -U postgres -c "CREATE DATABASE openclaw OWNER openclaw;"

# 4. SQLダンプからリストア
cat /path/to/backup/postgres_dump.sql | \
  docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U openclaw -d openclaw

# 5. 整合性確認
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -d openclaw -c "\dt"
```

---

### 完全再構築

**セキュリティ侵害後の完全再構築**

**所要時間**: 約2-3時間

#### Phase 1: 証拠保全（30分）

```bash
# 1. 侵害されたシステムのスナップショット作成
# VPSコントロールパネルでスナップショット作成

# 2. ログ収集
sudo tar -czf incident_logs_$(date +%Y%m%d).tar.gz \
  /var/log/ \
  data/*/logs/

# 3. メモリダンプ（オプション）
sudo dd if=/dev/mem of=/tmp/memory_dump.bin

# 4. 証拠を安全な場所へ転送
scp incident_logs_*.tar.gz safe-location:/forensics/
```

#### Phase 2: 新規VPSセットアップ（1時間）

```bash
# 新規VPSで完全にクリーンなセットアップ
# [新規VPSへの復旧] の手順に従う

# ただし、以下の追加対策を実施:
```

#### Phase 3: セキュリティ強化（30分）

```bash
# 1. 全てのパスワード変更
# .env ファイルの全パスワードを新規生成
openssl rand -base64 32  # 各サービス用

# 2. SSHキー再生成
ssh-keygen -t ed25519 -C "new-key-after-incident"

# 3. APIキー/トークン再発行
# - Anthropic API Key
# - Telegram Bot Token
# - その他全ての外部サービストークン

# 4. 2要素認証の有効化
# - N8N
# - Grafana
# - SSH (Google Authenticator)

# 5. セキュリティスキャン
./scripts/security_scan.sh --all
```

#### Phase 4: 監視強化（30分）

```bash
# 1. Fail2ban設定強化
sudo nano /etc/fail2ban/jail.local
# maxretry = 3 に変更
# bantime = 3600 に延長

# 2. アラート設定追加
# Prometheusアラートルールを厳格化

# 3. ログ監視設定
# 重要なログを外部サーバーに転送

# 4. 侵入検知システム（IDS）導入検討
sudo apt install aide
sudo aideinit
```

---

## 定期テスト

### 月次復旧訓練

```bash
# 1. バックアップからテスト環境への復元
# 2. データ整合性確認
# 3. アプリケーション動作確認
# 4. 復旧時間の測定
# 5. 手順書の更新
```

### 復旧訓練チェックリスト

- [ ] バックアップファイルが存在する
- [ ] バックアップからの復元が成功する
- [ ] 全サービスが正常に起動する
- [ ] データが最新の状態に近い
- [ ] 復旧時間がRTO以内
- [ ] 手順書が最新

---

## 連絡体制

### 緊急連絡先

```markdown
## 障害対応チーム

### 第一連絡先
- 氏名: [担当者名]
- 電話: [電話番号]
- Email: [メールアドレス]

### 第二連絡先（エスカレーション）
- 氏名: [担当者名]
- 電話: [電話番号]
- Email: [メールアドレス]

## 外部サービス

### VPSプロバイダー
- サービス名: [プロバイダー名]
- サポート: [サポートURL/電話]
- アカウントID: [アカウント番号]

### ドメインレジストラ
- サービス名: [レジストラ名]
- サポート: [サポートURL]
- アカウントID: [アカウント番号]

### バックアップストレージ
- サービス名: [ストレージサービス名]
- アカウント: [アカウント情報]
```

---

## 事後対応

### インシデントレポート作成

```markdown
# インシデントレポート

## 基本情報
- 発生日時: YYYY-MM-DD HH:MM
- 検知日時: YYYY-MM-DD HH:MM
- 復旧日時: YYYY-MM-DD HH:MM
- 影響範囲: [影響を受けたサービス]

## 原因
- 根本原因: [詳細]
- トリガー: [直接的な原因]

## 対応内容
1. [実施した対応1]
2. [実施した対応2]

## 影響
- データ損失: [有無と内容]
- サービス停止時間: [時間]
- ユーザー影響: [影響内容]

## 再発防止策
1. [対策1]
2. [対策2]

## 学んだこと
- [教訓1]
- [教訓2]
```

---

## 参考資料

- [OPERATIONS_GUIDE.md](../OPERATIONS_GUIDE.md) - 運用マニュアル
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - トラブルシューティング
- [SECURITY_CHECKLIST.md](../SECURITY_CHECKLIST.md) - セキュリティチェックリスト
- [FAQ.md](FAQ.md) - よくある質問

---

<div align="center">

**🚨 定期的な復旧訓練で、万が一に備えましょう！ 🛡️**

</div>
