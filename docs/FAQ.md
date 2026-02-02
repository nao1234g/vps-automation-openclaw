# よくある質問（FAQ）

OpenClaw VPS プロジェクトに関するよくある質問と回答

## 📋 目次

- [一般的な質問](#一般的な質問)
- [セットアップ・インストール](#セットアップインストール)
- [運用・メンテナンス](#運用メンテナンス)
- [トラブルシューティング](#トラブルシューティング)
- [セキュリティ](#セキュリティ)
- [パフォーマンス](#パフォーマンス)
- [データ管理](#データ管理)
- [カスタマイズ](#カスタマイズ)

---

## 一般的な質問

### Q1: OpenClaw VPS とは何ですか？

**A**: OpenClaw VPS は、OpenClaw AIエージェント、N8N、OpenNotebookをセキュアなDocker環境に簡単にデプロイするための完全自動化ツールキットです。10層のセキュリティ防御、監視統合、自動バックアップなどの機能を提供します。

### Q2: どのような環境で使用できますか？

**A**: 以下の環境で使用できます：
- VPS（ConoHa、AWS、DigitalOcean等）
- クラウドサーバー
- 専用サーバー
- ローカル開発環境（テスト用）

**推奨OS**: Ubuntu 22.04 LTS / 24.04 LTS

### Q3: 最低限必要なスペックは？

**A**:
- **最低要件**: CPU 2コア、RAM 4GB、SSD 40GB
- **推奨スペック**: CPU 4コア、RAM 8GB、SSD 80GB

詳細は [README.md](../README.md#-システム要件) を参照してください。

### Q4: 商用利用できますか？

**A**: はい。MITライセンスのため、商用利用可能です。ただし、OpenClawやN8N等の各コンポーネントのライセンスも確認してください。

### Q5: どのくらいのコストがかかりますか？

**A**:
- **VPS費用**: 月額500円〜2,000円程度（プロバイダーによる）
- **Anthropic API**: 使用量に応じた従量課金
- **その他**: SSL証明書（Let's Encryptは無料）

---

## セットアップ・インストール

### Q6: インストールにどのくらい時間がかかりますか？

**A**: 約5〜15分です。
- セットアップウィザード: 5分
- Dockerイメージダウンロード: 5〜10分（回線速度による）
- 初回起動: 2〜3分

### Q7: Docker/Docker Composeは手動でインストール必要ですか？

**A**: いいえ。`setup.sh` スクリプトが自動的にインストールします。

### Q8: SSH鍵認証の設定は必須ですか？

**A**: 本番環境では**必須**です。セキュリティ上、パスワード認証のみの運用は推奨しません。

詳細: [docs/SSH_KEY_SETUP.md](SSH_KEY_SETUP.md)

### Q9: SSL証明書は自動で取得されますか？

**A**: セットアップウィザードでドメインを指定すれば、Let's Encrypt証明書を自動取得できます。手動設定も可能です。

詳細: [docker/nginx/ssl/README.md](../docker/nginx/ssl/README.md)

### Q10: カスタムドメインなしでも使えますか？

**A**: はい。IPアドレスでアクセス可能です。ただし、SSL/TLS証明書の取得にはドメインが必要です。

---

## 運用・メンテナンス

### Q11: バックアップは自動で実行されますか？

**A**: Cronジョブを設定すれば自動実行されます。

```bash
# Cronジョブに追加
0 3 * * * /opt/vps-automation-openclaw/scripts/backup.sh
```

詳細: [OPERATIONS_GUIDE.md](../OPERATIONS_GUIDE.md#バックアップ)

### Q12: バックアップデータはどこに保存されますか？

**A**: デフォルトでは `/opt/backups/openclaw/` に保存されます。

バックアップ内容:
- PostgreSQLダンプ
- Dockerボリューム
- 設定ファイル
- システム情報

### Q13: 自動アップデートは有効にすべきですか？

**A**: セキュリティパッチの自動適用は**推奨**です。ただし、メジャーバージョンアップグレードは手動で実施することを推奨します。

```bash
# 自動セキュリティアップデート有効化（setup.shで設定済み）
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Q14: ログはどこに保存されますか？

**A**: `logs/` ディレクトリに保存されます。
- `logs/openclaw/`
- `logs/n8n/`
- `logs/opennotebook/`

### Q15: ディスク容量が不足したらどうすればいいですか？

**A**:
```bash
# ディスク使用状況確認
df -h

# Dockerの不要なデータ削除
docker system prune -a --volumes

# 古いバックアップ削除
find /opt/backups/openclaw/ -mtime +30 -delete

# ログローテーション設定確認
sudo logrotate -d /etc/logrotate.conf
```

---

## トラブルシューティング

### Q16: コンテナが起動しません

**A**: 以下を確認してください：

```bash
# 1. ログ確認
docker compose -f docker-compose.production.yml logs <service>

# 2. ポート競合確認
sudo lsof -i :3000  # OpenClaw
sudo lsof -i :5432  # PostgreSQL

# 3. 設定ファイル確認
cat .env

# 4. リソース確認
docker stats --no-stream
```

詳細: [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)

### Q17: "permission denied" エラーが出ます

**A**: ディレクトリのパーミッションを修正してください。

```bash
sudo chown -R 1000:1000 data/
sudo chown -R 1000:1000 logs/
docker compose -f docker-compose.production.yml restart
```

### Q18: データベース接続エラーが発生します

**A**:
```bash
# 1. PostgreSQLが起動しているか確認
docker compose -f docker-compose.production.yml ps postgres

# 2. 接続テスト
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -c "SELECT version();"

# 3. .env の POSTGRES_PASSWORD を確認
cat .env | grep POSTGRES_PASSWORD

# 4. ネットワーク接続確認
docker compose -f docker-compose.production.yml exec openclaw \
  ping postgres
```

### Q19: Grafanaにアクセスできません

**A**:
```bash
# 1. 監視スタックが起動しているか確認
docker compose -f docker-compose.monitoring.yml ps

# 2. ポート確認
curl http://localhost:3001

# 3. ログ確認
docker compose -f docker-compose.monitoring.yml logs grafana

# 4. 監視スタック再起動
docker compose -f docker-compose.monitoring.yml restart grafana
```

### Q20: N8Nワークフローが実行されません

**A**:
```bash
# 1. N8Nログ確認
docker compose -f docker-compose.production.yml logs n8n

# 2. ワークフローがアクティブか確認
# N8N UIで該当ワークフローのステータスを確認

# 3. 実行履歴確認
# N8N UI → Executions で失敗理由を確認

# 4. 環境変数確認
docker compose -f docker-compose.production.yml exec n8n env
```

---

## セキュリティ

### Q21: セキュリティスキャンはどのくらいの頻度で実行すべきですか？

**A**: **週次**を推奨します。Cronジョブで自動化してください。

```bash
# Cronジョブに追加
0 2 * * 0 /opt/vps-automation-openclaw/scripts/security_scan.sh --all
```

### Q22: ファイアウォール設定は自動で行われますか？

**A**: はい。`setup.sh` が以下を自動設定します：
- UFW有効化
- 必要なポートのみ開放（22, 80, 443）
- Fail2ban設定

### Q23: パスワードはどのように管理すべきですか？

**A**:
```bash
# 強力なパスワード生成
openssl rand -base64 32

# .env ファイルのパーミッション制限
chmod 600 .env

# パスワード管理ツール使用を推奨（1Password, Bitwarden等）
```

### Q24: 定期的にパスワード変更すべきですか？

**A**: はい。3〜6ヶ月ごとの変更を推奨します。

```bash
# 1. .env でパスワード更新
nano .env

# 2. サービス再起動
docker compose -f docker-compose.production.yml restart

# 3. バックアップ
sudo ./scripts/backup.sh
```

### Q25: 2要素認証（2FA）は設定できますか？

**A**: 各サービスで設定可能です：
- **N8N**: N8N UIで2FA有効化
- **Grafana**: Grafana UIで2FA設定
- **SSH**: Google Authenticator等を使用

---

## パフォーマンス

### Q26: パフォーマンスベンチマークはどう実行しますか？

**A**:
```bash
# 簡易ベンチマーク（5分）
./scripts/benchmark.sh --quick

# 完全ベンチマーク（30分）
./scripts/benchmark.sh --full

# レポート確認
./scripts/benchmark.sh --report
```

### Q27: メモリ使用率が高い場合の対処法は？

**A**:
```bash
# 1. メモリ使用状況確認
docker stats --no-stream

# 2. コンテナのリソース制限確認
cat docker-compose.production.yml | grep -A 5 "resources:"

# 3. スワップ設定確認
swapon --show

# 4. 不要なコンテナ停止
docker compose -f docker-compose.production.yml stop <service>
```

詳細: [PERFORMANCE.md](../PERFORMANCE.md)

### Q28: PostgreSQLのパフォーマンスチューニングは？

**A**: [PERFORMANCE.md](../PERFORMANCE.md#データベース最適化) を参照してください。

主な設定項目:
- `shared_buffers`: メモリの25%
- `effective_cache_size`: メモリの50-75%
- `work_mem`: 適切なサイズに調整
- インデックスの最適化

### Q29: Nginxのキャッシュ設定はありますか？

**A**: はい。`docker/nginx/nginx.conf` でキャッシュ設定をカスタマイズできます。

```nginx
# キャッシュディレクティブ
proxy_cache_valid 200 10m;
proxy_cache_valid 404 1m;
```

### Q30: CPU使用率が常に高い場合は？

**A**:
```bash
# 1. CPUを多く使用しているコンテナ特定
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}"

# 2. リソース制限設定
# docker-compose.production.yml で調整

# 3. ログレベル下げる（DEBUG → INFO）
# .env で LOG_LEVEL=info に設定

# 4. 不要なサービス停止
```

---

## データ管理

### Q31: データベースのバックアップから復元する方法は？

**A**:
```bash
# 1. バックアップディレクトリ確認
ls -lh /opt/backups/openclaw/

# 2. 復元スクリプト実行
sudo ./scripts/restore.sh /opt/backups/openclaw/backup_20240201_030000

# 3. サービス再起動
docker compose -f docker-compose.production.yml restart
```

詳細: [OPERATIONS_GUIDE.md](../OPERATIONS_GUIDE.md#データ復元)

### Q32: データベースサイズを確認するには？

**A**:
```bash
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -c "\
    SELECT \
      datname, \
      pg_size_pretty(pg_database_size(datname)) AS size \
    FROM pg_database \
    WHERE datname IN ('openclaw', 'n8n', 'opennotebook');"
```

### Q33: 古いデータを削除する方法は？

**A**:
```bash
# PostgreSQLに接続
docker compose -f docker-compose.production.yml exec postgres \
  psql -U openclaw -d openclaw

# 例: 90日以上古いデータを削除
DELETE FROM chat_history WHERE timestamp < NOW() - INTERVAL '90 days';

# VACUUM実行（ディスク領域回収）
VACUUM FULL;
```

### Q34: データを他のVPSに移行できますか？

**A**: はい。[docs/MIGRATION.md](MIGRATION.md) を参照してください。

簡単な手順:
1. 旧VPSでバックアップ: `./scripts/backup.sh`
2. バックアップファイルを新VPSに転送
3. 新VPSでセットアップ: `./setup.sh`
4. 復元: `./scripts/restore.sh <backup_path>`

### Q35: サンプルデータを投入できますか？

**A**: はい。開発環境用のサンプルデータがあります。

```bash
# サンプルデータ投入
docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U openclaw -d openclaw < scripts/seed_data.sql
```

---

## カスタマイズ

### Q36: ポート番号を変更できますか？

**A**: はい。`docker-compose.production.yml` で変更できます。

```yaml
services:
  openclaw:
    ports:
      - "8080:3000"  # ホストポート:コンテナポート
```

### Q37: 開発環境でホットリロードを有効にするには？

**A**: `docker-compose.override.yml.example` をコピーして使用してください。

```bash
# コピー
cp docker-compose.override.yml.example docker-compose.override.yml

# 編集
nano docker-compose.override.yml

# 起動（override.ymlは自動読み込み）
docker compose up -d
```

### Q38: カスタムN8Nノードを追加できますか？

**A**: はい。
```bash
# カスタムノードディレクトリ作成
mkdir -p local/n8n/custom-nodes

# docker-compose.override.yml でマウント
# volumes:
#   - ./local/n8n/custom-nodes:/home/node/.n8n/custom

# N8N再起動
docker compose restart n8n
```

### Q39: 独自のGrafanaダッシュボードを追加できますか？

**A**: はい。
```bash
# ダッシュボードJSONファイルを配置
cp my-dashboard.json docker/grafana/dashboards/

# Grafana再起動
docker compose -f docker-compose.monitoring.yml restart grafana
```

詳細: [docker/grafana/dashboards/README.md](../docker/grafana/dashboards/README.md)

### Q40: 環境変数を増やすには？

**A**: `.env` ファイルに追加してください。

```bash
# .env に追加
echo "MY_CUSTOM_VAR=value" >> .env

# docker-compose.production.yml で参照
# environment:
#   - MY_CUSTOM_VAR=${MY_CUSTOM_VAR}

# 再起動
docker compose -f docker-compose.production.yml restart
```

---

## その他

### Q41: コミュニティやサポートはありますか？

**A**:
- **GitHub Issues**: https://github.com/nao1234g/vps-automation-openclaw/issues
- **貢献方法**: [CONTRIBUTING.md](../CONTRIBUTING.md)

### Q42: バグを見つけた場合はどうすればいいですか？

**A**: GitHub Issuesで報告してください。

テンプレート: [.github/ISSUE_TEMPLATE/bug_report.md](../.github/ISSUE_TEMPLATE/bug_report.md)

### Q43: 新機能をリクエストできますか？

**A**: はい。GitHub Issuesで機能リクエストを作成してください。

テンプレート: [.github/ISSUE_TEMPLATE/feature_request.md](../.github/ISSUE_TEMPLATE/feature_request.md)

### Q44: プルリクエストを送る方法は？

**A**: [CONTRIBUTING.md](../CONTRIBUTING.md) を参照してください。

手順:
1. リポジトリをフォーク
2. Featureブランチ作成
3. 変更をコミット
4. プルリクエスト作成

### Q45: ドキュメントに誤りを見つけました

**A**: プルリクエストで修正を送っていただけると助かります！または、Issueで報告してください。

---

## さらに詳しい情報

- [README.md](../README.md) - プロジェクト概要
- [DEPLOYMENT.md](../DEPLOYMENT.md) - デプロイメントガイド
- [OPERATIONS_GUIDE.md](../OPERATIONS_GUIDE.md) - 運用マニュアル
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - トラブルシューティング
- [SECURITY_CHECKLIST.md](../SECURITY_CHECKLIST.md) - セキュリティチェックリスト
- [PERFORMANCE.md](../PERFORMANCE.md) - パフォーマンス最適化
- [ARCHITECTURE.md](../ARCHITECTURE.md) - アーキテクチャ詳細

---

<div align="center">

**❓ 質問が解決しない場合は [GitHub Issues](https://github.com/nao1234g/vps-automation-openclaw/issues) で質問してください！ 💬**

</div>
