# OpenClaw VPS — Nowpattern AI 自動化ハブ

<div align="center">

**AIが記事を書き、投稿し、学び続ける — 24時間無人コンテンツ自動化システム**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com/)
[![Security](https://img.shields.io/badge/Security-Hardened-success)](SECURITY_CHECKLIST.md)

</div>

---

## 現在の稼働状況（2026-02-23）

| レイヤー | サービス | 状態 | 役割 |
|---------|---------|------|------|
| コンテンツハブ | [nowpattern.com](https://nowpattern.com) | 稼働中 | Ghost CMS、記事公開 |
| AI執筆 | NEO-ONE `@claude_brain_nn_bot` | 稼働中 | Claude Opus 4.6 — 戦略・記事執筆 |
| AI補助 | NEO-TWO `@neo_two_nn2026_bot` | 稼働中 | Claude Opus 4.6 — 並列タスク |
| 実行エージェント | Jarvis（OpenClaw）`@openclaw_nn2026_bot` | 稼働中 | 投稿実行・翻訳・タスク委任 |
| ワークフロー | N8N（13本） | 稼働中 | RSSパイプライン + 監視 |
| 情報収集 | daily-learning.py | 稼働中 | 1日4回 Reddit/HN/GitHub収集 |

### コンテンツパイプライン

```
ニュース収集（JST 7/13/19時）
  ↓ 30分後
Gemini深層分析（7,000字+）
  ↓ 毎時0分
note（日本語）・Substack（英語）・X引用リポスト
  ↓ 同時
nowpattern.com（Ghost CMS）自動投稿
```

---

## 📖 概要

このリポジトリは、**Nowpattern.com** を中心とした AI コンテンツ自動化プラットフォームです。
NEO-ONE/TWO（Claude Opus 4.6）が戦略立案・記事執筆を担い、Jarvis（OpenClaw）が投稿を実行し、N8N 13ワークフローが24時間稼働します。
インフラは ConoHa VPS（163.44.124.123）上に Docker Compose で構成されています。

### AIエージェント（10人体制）

| # | 名前 | 役割 | モデル |
|---|------|------|--------|
| 1 | Jarvis | 実行・投稿・翻訳 | Gemini 2.5 Pro |
| 2–7 | Alice/CodeX/Pixel/Luna/Scout/Guard | 専門分業（リサーチ/開発/デザイン等） | Gemini 2.5 Pro |
| 8 | Hawk | X/SNSリサーチ | Grok 4.1 |
| 9 | NEO-ONE | CTO・戦略・記事執筆 | Claude Opus 4.6 |
| 10 | NEO-TWO | 補助・並列タスク | Claude Opus 4.6 |

### インフラ構成

| サービス | 説明 | ポート |
|---------|------|--------|
| **OpenClaw** | AIエージェント Gateway（Jarvis 他8人） | 3000 |
| **N8N** | ワークフロー自動化（13本稼働） | 5678 |
| **PostgreSQL** | 共有データベース | 5432 |
| **Ghost CMS** | nowpattern.com（systemd管理） | 2368 |
| **Caddy** | リバースプロキシ（SSL自動更新） | 80/443 |

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

## 🎯 自動化ワークフロー例

### 1. AISAコンテンツパイプライン（24時間稼働）

```
RSS収集 → Gemini深層分析 → note/Substack/X/Ghost 自動投稿
```

### 2. NEO記事執筆フロー

```
Telegram指示 → NEO-ONE（戦略立案+執筆） → Jarvis（投稿+翻訳） → nowpattern.com
```

### 3. VPS自動監視

```
N8N 15分ごと → ヘルスチェック → 異常時 Telegram通知
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

## 📚 主要ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | システム全体構成図 |
| [docs/ARTICLE_FORMAT.md](docs/ARTICLE_FORMAT.md) | Nowpattern記事フォーマット（Deep Pattern v5.0） |
| [docs/NOWPATTERN_TAXONOMY_v3.md](docs/NOWPATTERN_TAXONOMY_v3.md) | タクソノミー v3.0（ジャンル13×イベント19×力学16） |
| [docs/NEO_INSTRUCTIONS_V2.md](docs/NEO_INSTRUCTIONS_V2.md) | NEO執筆指示書 |
| [docs/KNOWN_MISTAKES.md](docs/KNOWN_MISTAKES.md) | 既知のミスDB（実装前に必読） |
| [n8n-workflows/README.md](n8n-workflows/README.md) | N8N 13ワークフロー一覧 |
| [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) | 日常運用マニュアル |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | コマンド早見表 |

## 🎨 拡張予定

- NAVER Blog韓国語自動投稿（アカウント作成待ち）
- Medium自動投稿（MEDIUM_TOKEN登録待ち）
- ドキュメント自動クリーンアップ（廃止検知 + アーカイブ提案）

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
