# VPS運用ガイド

OpenClaw VPS環境の日常運用マニュアルです。

## 📋 目次

1. [日常運用タスク](#日常運用タスク)
2. [定期メンテナンス](#定期メンテナンス)
3. [監視とアラート](#監視とアラート)
4. [トラブルシューティング](#トラブルシューティング)
5. [緊急時対応](#緊急時対応)
6. [セキュリティ運用](#セキュリティ運用)

## 日常運用タスク

### 毎日実行推奨

#### ヘルスチェック
```bash
./scripts/health_check.sh
```

システムの健全性を確認:
- ディスク/メモリ使用率
- コンテナ状態
- セキュリティ設定
- SSL証明書有効期限
- バックアップ状態

#### バックアップ
```bash
sudo ./scripts/backup.sh
```

自動バックアップの内容:
- PostgreSQLデータベース
- Dockerボリューム
- 設定ファイル
- システム情報

**オプション:**
- `--db-only`: データベースのみ
- `--volumes-only`: ボリュームのみ
- `--config-only`: 設定のみ

### 毎週実行推奨

#### セキュリティスキャン
```bash
./scripts/security_scan.sh
```

実行内容:
- Trivyによる脆弱性スキャン
- Docker Bench Security監査
- システムセキュリティチェック

#### ログ確認
```bash
# システムエラー
sudo journalctl -p err -S today

# Dockerログ
docker compose logs --tail=100

# セキュリティスキャンレポート
ls -lh security-reports/
```

### 毎月実行推奨

#### システムメンテナンス
```bash
# プレビュー（削除なし）
sudo ./scripts/maintenance.sh --dry-run

# 実行
sudo ./scripts/maintenance.sh
```

実行内容:
- システムアップデート
- 未使用Dockerリソース削除
- ログローテーション
- ディスク使用状況確認

## 定期メンテナンス

### SSL証明書の更新

証明書は自動更新されますが、手動確認:

```bash
# 証明書情報確認
openssl x509 -in docker/nginx/ssl/fullchain.pem -noout -dates

# 手動更新
sudo certbot renew

# Nginx再起動
docker compose restart nginx
```

### データベースメンテナンス

#### バキューム（最適化）
```bash
docker compose exec db psql -U openclaw -c "VACUUM ANALYZE;"
```

#### データベースサイズ確認
```bash
docker compose exec db psql -U openclaw -c "\l+"
```

### Dockerイメージの更新

```bash
# イメージ更新確認
docker compose pull

# 更新があれば再起動
docker compose up -d

# 古いイメージ削除
docker image prune -a
```

## 監視とアラート

### リソース監視

#### ディスク使用率
```bash
df -h
du -sh /var/lib/docker
du -sh /opt/backups
```

**閾値:**
- 警告: 70%
- 危険: 85%

#### メモリ使用率
```bash
free -h
docker stats --no-stream
```

**閾値:**
- 警告: 80%
- 危険: 90%

#### CPU負荷
```bash
uptime
top -bn1 | head -20
```

### ログ監視

#### エラーログの確認
```bash
# 本日のエラー
sudo journalctl -p err -S today

# Dockerコンテナエラー
docker compose logs --tail=100 | grep -i error

# Nginxエラー
docker compose exec nginx cat /var/log/nginx/error.log | tail -50
```

### アラート設定（オプション）

#### ディスク容量アラート
```bash
# /etc/cron.daily/disk-alert
#!/bin/bash
USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$USAGE" -gt 85 ]; then
    echo "ALERT: Disk usage is ${USAGE}%" | mail -s "Disk Alert" admin@example.com
fi
```

## トラブルシューティング

### コンテナが起動しない

#### 1. ログを確認
```bash
docker compose logs <コンテナ名>
```

#### 2. 設定を確認
```bash
docker compose config
```

#### 3. ポート競合を確認
```bash
sudo ss -tuln | grep <ポート番号>
```

#### 4. リソース不足を確認
```bash
free -h
df -h
```

### データベース接続エラー

#### 1. コンテナ状態確認
```bash
docker compose ps db
```

#### 2. ログ確認
```bash
docker compose logs db
```

#### 3. 接続テスト
```bash
docker compose exec db psql -U openclaw -c "SELECT version();"
```

#### 4. パスワード確認
```bash
# .envファイルの確認
grep POSTGRES_PASSWORD .env
```

### SSL証明書エラー

#### 1. 証明書の確認
```bash
openssl x509 -in docker/nginx/ssl/fullchain.pem -text -noout
```

#### 2. 証明書の更新
```bash
sudo certbot renew --force-renewal
```

#### 3. Nginx設定のテスト
```bash
docker compose exec nginx nginx -t
```

### ディスク容量不足

#### 1. 容量の確認
```bash
df -h
du -sh /var/lib/docker/*
du -sh /opt/backups/*
```

#### 2. 未使用リソースの削除
```bash
# Dockerクリーンアップ
docker system prune -a --volumes

# 古いバックアップ削除
find /opt/backups -mtime +30 -delete

# ログ削除
sudo journalctl --vacuum-time=7d
```

## 緊急時対応

### サービス停止

#### 全コンテナ停止
```bash
docker compose down
```

#### 特定コンテナ停止
```bash
docker compose stop <コンテナ名>
```

### 復元手順

#### 1. 最新バックアップの確認
```bash
ls -lht /opt/backups/openclaw/ | head
```

#### 2. 復元実行
```bash
sudo ./scripts/restore.sh /opt/backups/openclaw/backup_YYYYMMDD_HHMMSS
```

#### 3. サービス確認
```bash
docker compose ps
./scripts/health_check.sh
```

### ロールバック

#### イメージのロールバック
```bash
# 以前のイメージを確認
docker images

# 特定バージョンに戻す
# docker-compose.ymlでイメージタグを指定
docker compose up -d
```

#### 設定のロールバック
```bash
# バックアップから復元
sudo ./scripts/restore.sh --config-only /opt/backups/openclaw/backup_YYYYMMDD_HHMMSS
```

### セキュリティインシデント対応

#### 1. 影響範囲の特定
```bash
# 不審なログを確認
sudo journalctl -S today | grep -i "failed\|error\|denied"

# 接続状況確認
sudo ss -tuln
sudo netstat -an
```

#### 2. 隔離
```bash
# 該当コンテナを停止
docker compose stop <コンテナ名>

# ネットワークから切断
docker network disconnect <ネットワーク名> <コンテナ名>
```

#### 3. ログの保存
```bash
# ログのアーカイブ
sudo journalctl > incident_$(date +%Y%m%d_%H%M%S).log
docker compose logs > docker_incident_$(date +%Y%m%d_%H%M%S).log
```

#### 4. 復旧
```bash
# クリーンな状態から再構築
docker compose down
sudo ./scripts/restore.sh <バックアップパス>
docker compose up -d
```

#### 5. シークレットのローテーション
```bash
# .envのパスワードを全て変更
nano .env

# 新しいパスワードを生成
openssl rand -base64 32

# コンテナ再作成
docker compose down
docker compose up -d
```

## セキュリティ運用

### 定期セキュリティタスク

#### 毎週
- [ ] セキュリティスキャン実行
- [ ] 脆弱性レポート確認
- [ ] システムログ確認
- [ ] 不審なアクセスのチェック

#### 毎月
- [ ] Docker Bench Security実行
- [ ] パスワード強度確認
- [ ] SSL証明書有効期限確認
- [ ] バックアップのテスト復元

#### 四半期
- [ ] 全システムの脆弱性診断
- [ ] アクセス権限の見直し
- [ ] インシデント対応計画の見直し
- [ ] セキュリティ設定の再確認

### セキュリティチェックリスト

定期的に確認:

- [ ] UFWが有効
- [ ] Fail2banが実行中
- [ ] SSH鍵認証のみ有効
- [ ] rootログイン無効
- [ ] SSL証明書が有効
- [ ] 全コンテナが非rootで実行
- [ ] シークレットが.envで管理
- [ ] バックアップが取得できている
- [ ] ログが正常に記録されている

### 推奨ツール

#### Fail2ban監視
```bash
# バン状況確認
sudo fail2ban-client status sshd

# バンを解除
sudo fail2ban-client set sshd unbanip <IPアドレス>
```

#### UFW管理
```bash
# ルール一覧
sudo ufw status numbered

# ルール追加
sudo ufw allow <ポート>/tcp

# ルール削除
sudo ufw delete <番号>
```

## パフォーマンス最適化

### Docker最適化

#### イメージレイヤーの最適化
```bash
# マルチステージビルドの使用
# Dockerfile.secure.template参照
```

#### ボリュームのクリーンアップ
```bash
docker volume prune
```

### データベース最適化

#### インデックスの確認
```bash
docker compose exec db psql -U openclaw -c "\di"
```

#### クエリパフォーマンス
```bash
docker compose exec db psql -U openclaw -c "EXPLAIN ANALYZE <クエリ>;"
```

## まとめ

### 運用のベストプラクティス

1. **自動化を活用**: Cronで定期タスクを自動化
2. **監視を怠らない**: 毎日のヘルスチェックを習慣化
3. **バックアップは頻繁に**: 毎日のバックアップを推奨
4. **セキュリティ第一**: 定期的なスキャンと更新
5. **ドキュメント化**: 変更履歴を記録

### 参考リンク

- [セキュリティチェックリスト](SECURITY_CHECKLIST.md)
- [クイックスタート](QUICKSTART_SECURITY.md)
- [SSH設定ガイド](docs/SSH_KEY_SETUP.md)

---

**ヘルプが必要な場合は [GitHub Issues](https://github.com/nao1234g/vps-automation-openclaw/issues) で質問してください。**
