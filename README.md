# OpenClaw VPS - 完全自動化セキュアデプロイメント

<div align="center">

**🚀 VPSへOpenClaw AIエージェントをセキュアにデプロイ 🔒**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com/)
[![Security](https://img.shields.io/badge/Security-Hardened-success)](SECURITY_CHECKLIST.md)

</div>

---

## 📖 概要

このリポジトリは、**OpenClaw AIエージェント**（旧：Clawdbot/Moltbot）とN8N、OpenNotebookを**セキュアなDocker環境**にワンストップでデプロイするための完全自動化ツールキットです。

### ✨ 主な特徴

- 🔒 **10層のセキュリティ防御**: UFW/Fail2ban/非rootコンテナ/ネットワーク分離/SSL/TLS
- 🐳 **Docker Compose統合**: マイクロサービスアーキテクチャで分離された環境
- ⚡ **完全自動セットアップ**: 対話式ウィザードで5分でデプロイ完了
- 📊 **統合監視**: ヘルスチェック/セキュリティスキャン/自動バックアップ
- 🔄 **運用自動化**: Cronジョブによる定期メンテナンス/スキャン/バックアップ

---

## 🎯 対象ユーザー

- VPSでAIエージェントを安全に運用したい方
- Dockerでマイクロサービス環境を構築したい方
- セキュリティベストプラクティスを実践したい方
- N8N/OpenNotebook/OpenClawを統合したい方

---

## 📦 含まれるコンポーネント

| サービス | 説明 | ポート |
|---------|------|--------|
| **OpenClaw** | Claude APIベースのAIエージェント | 3000 |
| **N8N** | ワークフロー自動化プラットフォーム | 5678 |
| **OpenNotebook** | NotebookLMオープンソース版 | 8080 |
| **PostgreSQL** | 共有データベース | 5432 |
| **Nginx** | リバースプロキシ（SSL/TLS対応） | 80/443 |

---

## ⚠️ セキュリティ警告

OpenClawは**非常に強力な権限**を持つため、以下を**厳守**してください：

- ❌ **メイン使用PCへのインストールは危険**
- ❌ **公開サーバーでの運用は厳禁**
- ✅ **専用VPS環境の利用を強く推奨**
- ✅ **SSH鍵認証の設定は必須**
- ✅ **ファイアウォール(UFW)の有効化**
- ✅ **定期的なセキュリティスキャン実施**

このリポジトリは、**10層のセキュリティ防御**を自動的に設定します。

---

## 🚀 クイックスタート（5分セットアップ）

### 開発環境（最速）

```bash
# リポジトリをクローン
git clone https://github.com/nao1234g/vps-automation-openclaw.git
cd vps-automation-openclaw

# 環境変数を設定
cp .env.example .env
# .envを編集（開発環境ではデフォルト値でOK）

# 最小構成を起動（PostgreSQL + OpenNotebook）
make minimal

# ヘルスチェック
curl http://localhost:8080/health
```

**アクセス先:**
- OpenNotebook: http://localhost:8080
- PostgreSQL: localhost:5432

詳細は[DEVELOPMENT.md](DEVELOPMENT.md)を参照してください。

### VPS本番環境（完全セットアップ）

### 前提条件

- Ubuntu 22.04 LTS / 24.04 LTS
- 最低スペック: 2GB RAM, 2 vCPU, 40GB SSD
- SSH接続可能なVPS
- root権限

### Step 1: リポジトリをクローン

```bash
cd /opt
sudo git clone https://github.com/YOUR_USERNAME/vps-automation-openclaw.git
cd vps-automation-openclaw
```

### Step 2: 完全自動セットアップ

```bash
sudo ./setup.sh
```

**セットアップウィザードが以下を自動実行:**
1. ✅ VPSセキュリティ設定（UFW, Fail2ban, 自動更新）
2. ✅ SSH鍵認証の確認
3. ✅ Dockerのセキュアインストール
4. ✅ 環境変数の設定（`.env`）
5. ✅ SSL証明書の取得（オプション）
6. ✅ Cron自動化の設定

### Step 3: 環境変数を設定

```bash
nano .env
```

**必須項目を設定:**
```env
# Database
POSTGRES_PASSWORD=<強力なパスワード>

# LLM Providers
ANTHROPIC_API_KEY=<AnthropicのAPIキー>
TELEGRAM_BOT_TOKEN=<TelegramのBotトークン>

# パスワード生成: openssl rand -base64 32
```

### Step 4: デプロイ

```bash
# データディレクトリ作成
sudo mkdir -p data/{postgres,openclaw,n8n,opennotebook,opennotebook_uploads}
sudo mkdir -p logs/{openclaw,n8n,opennotebook}
sudo chown -R 1000:1000 data logs

# 本番環境デプロイ
docker compose -f docker-compose.production.yml up -d
```

### Step 5: ヘルスチェック

```bash
./scripts/health_check.sh
```

**✅ 完了！** ブラウザで `https://your-domain.com` または `http://your-vps-ip` にアクセス

---

## 📚 ドキュメント

| ドキュメント | 内容 |
|------------|------|
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | 📖 完全デプロイメントガイド |
| **[QUICKSTART_SECURITY.md](QUICKSTART_SECURITY.md)** | ⚡ 5分セキュリティセットアップ |
| **[SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)** | 🔒 セキュリティチェックリスト |
| **[OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md)** | 🛠️ 運用マニュアル |
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | 📋 コマンド早見表 |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | 🏗️ システムアーキテクチャ |
| **[docs/SSH_KEY_SETUP.md](docs/SSH_KEY_SETUP.md)** | 🔑 SSH設定ガイド |

---

## 🔧 運用タスク

### 日次

```bash
# バックアップ
sudo ./scripts/backup.sh

# ヘルスチェック
./scripts/health_check.sh
```

### 週次

```bash
# セキュリティスキャン
./scripts/security_scan.sh
```

### 月次

```bash
# システムメンテナンス
sudo ./scripts/maintenance.sh
```

---

## 🏗️ アーキテクチャ

### セキュリティ層

```
┌─────────────────────────────────────────┐
│  Layer 10: 監視・ログ                    │
│  - Trivy脆弱性スキャン                   │
│  - Docker Bench Security                │
│  - 自動バックアップ                       │
├─────────────────────────────────────────┤
│  Layer 9: ネットワーク分離                │
│  - Frontend: 172.28.1.0/24              │
│  - Backend: 172.28.2.0/24 (Internal)    │
├─────────────────────────────────────────┤
│  Layer 8: SSL/TLS暗号化                  │
│  - Let's Encrypt証明書                   │
│  - TLS 1.2/1.3のみ                       │
├─────────────────────────────────────────┤
│  Layer 7: アプリケーション防御             │
│  - セキュリティヘッダー                    │
│  - レート制限                             │
├─────────────────────────────────────────┤
│  Layer 6: コンテナセキュリティ             │
│  - 非rootユーザー実行                     │
│  - Capabilities制限                      │
│  - Read-onlyファイルシステム              │
├─────────────────────────────────────────┤
│  Layer 5: ファイアウォール                 │
│  - UFW（22/80/443のみ許可）              │
├─────────────────────────────────────────┤
│  Layer 4: 侵入防止                        │
│  - Fail2ban（SSH/HTTP）                  │
├─────────────────────────────────────────┤
│  Layer 3: アクセス制御                     │
│  - SSH鍵認証のみ                          │
│  - rootログイン無効化                      │
├─────────────────────────────────────────┤
│  Layer 2: システムセキュリティ              │
│  - 自動セキュリティアップデート             │
│  - 最小パッケージインストール               │
├─────────────────────────────────────────┤
│  Layer 1: 物理分離                        │
│  - 専用VPSサーバー                         │
└─────────────────────────────────────────┘
```

### ネットワーク構成

```
                    Internet
                       ↓
                   [Nginx:80/443]
                       ↓
         ┌─────────────┴─────────────┐
         ↓                           ↓
    [OpenClaw:3000]            [N8N:5678]
         ↓                           ↓
         └──────────┬────────────────┘
                    ↓
              [PostgreSQL:5432]
             (Backend Network - Internal)
```

---

## 🔒 セキュリティ機能

### 自動セキュリティスキャン

```bash
./scripts/security_scan.sh --all
```

**スキャン内容:**
- Trivyによるコンテナ脆弱性診断
- Docker Bench Securityによるベストプラクティス監査
- システムセキュリティチェック
- レポート生成（security-reports/）

### バックアップ・復元

```bash
# 完全バックアップ
sudo ./scripts/backup.sh

# バックアップから復元
sudo ./scripts/restore.sh /opt/backups/openclaw/backup_YYYYMMDD_HHMMSS
```

**バックアップ内容:**
- PostgreSQLデータベースダンプ
- Dockerボリューム（全サービス）
- 設定ファイル（.env、nginx.conf等）
- システム情報

---

## 🎯 連携ワークフロー例

### 1. 研究ノート自動作成

```
Telegram → OpenClaw → Web検索 → OpenNotebook → N8N → Slack通知
```

### 2. コード自動デプロイ

```
GitHub Issue → OpenClaw → コード修正 → PR作成 → N8N → レビュー依頼
```

### 3. VPSメンテナンス

```
Cron → N8N → OpenClaw → システム更新 → OpenNotebook → Telegram通知
```

---

## 🛠️ トラブルシューティング

### コンテナが起動しない

```bash
docker compose -f docker-compose.production.yml logs <サービス名>
docker compose -f docker-compose.production.yml ps
```

### データベース接続エラー

```bash
docker compose -f docker-compose.production.yml exec postgres psql -U openclaw -c "SELECT version();"
```

### ディスク容量不足

```bash
df -h
docker system prune -a --volumes
```

詳細は [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) を参照してください。

---

## 📊 システム要件

### 最低スペック
- CPU: 2コア
- RAM: 4GB
- ストレージ: 40GB SSD
- OS: Ubuntu 22.04 LTS

### 推奨スペック
- CPU: 4コア
- RAM: 8GB
- ストレージ: 80GB SSD
- OS: Ubuntu 24.04 LTS

---

## 🔄 アップデート手順

### アプリケーション更新

```bash
git pull origin main
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d
```

### Dockerイメージ更新

```bash
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d
docker image prune -a
```

---

## 📚 参考リソース

### 公式リポジトリ
- **OpenClaw**: https://github.com/Sh-Osakana/open-claw
- **N8N**: https://github.com/n8n-io/n8n
- **Docker**: https://docs.docker.com/

### ConoHa VPS公式ドキュメント
- [SSH接続方法](https://support.conoha.jp/v/vps_ssh/)
- [SSH Key登録](https://support.conoha.jp/v/sshkey/)
- [一般ユーザーのSSH鍵認証](https://support.conoha.jp/v/vpssshuser/)

### 動画ガイド
- Jun SuzukiさんのYouTube解説: https://www.youtube.com/watch?v=KDK40fNX4Ko

---

## 🎨 今後の拡張予定

- 🎤 Ibyスピーチ連携（高品質日本語TTS）
- 🎬 RemoTion統合（動画自動生成）
- 🤖 サブエージェント機能（複数LLM並列実行）
- 📊 ダッシュボード機能（進捗可視化）
- 🔍 分散トレーシング（OpenTelemetry統合）

---

## 🤝 貢献

プルリクエスト・Issue報告を歓迎します！

1. このリポジトリをフォーク
2. Featureブランチを作成（`git checkout -b feature/amazing-feature`）
3. 変更をコミット（`git commit -m 'Add amazing feature'`）
4. ブランチにプッシュ（`git push origin feature/amazing-feature`）
5. プルリクエストを作成

---

## 📝 ライセンス

MIT License

---

## 📧 サポート

質問・提案がある場合は、[GitHub Issues](https://github.com/nao1234g/vps-automation-openclaw/issues) を作成してください。

---

## ⚡ 免責事項

このガイドは教育目的で作成されています。セキュリティリスクを理解した上で、自己責任で使用してください。

---

<div align="center">

**🚀 安全で自動化されたVPS運用を始めましょう！ 🔒**

Made with ❤️ for the OpenClaw Community

</div>
