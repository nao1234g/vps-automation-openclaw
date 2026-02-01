# VPS セキュリティ クイックスタートガイド

ConoHa VPSなどの新しいVPSサーバーに、セキュアにDockerをセットアップするための手順書です。

## 🎯 前提条件

- Ubuntu 20.04 LTS以降のVPS
- rootまたはsudo権限を持つユーザー
- ローカルマシンでSSH鍵ペアを生成済み

## ⚡ 5分で完了するセキュアセットアップ

### Step 1: VPSに接続

```bash
# 初回接続（パスワード認証）
ssh root@<VPSのIPアドレス>
```

### Step 2: このリポジトリをクローン

```bash
cd /opt
git clone https://github.com/<your-repo>/vps-automation-openclaw.git
cd vps-automation-openclaw
```

### Step 3: VPSセキュリティ設定を実行

```bash
# VPS初期セキュリティ設定
sudo ./scripts/setup_vps_security.sh
```

**実行内容:**
- システムアップデート
- UFWファイアウォール設定（SSH, HTTP, HTTPS許可）
- Fail2banインストール（SSH攻撃対策）
- 自動セキュリティアップデート有効化

**所要時間:** 約3-5分

### Step 4: SSH鍵認証の設定

⚠️ **重要**: この手順を完了する前に、パスワード認証を無効化しないでください。

#### 4-1. ローカルマシンで公開鍵をコピー

```bash
# ローカルマシンで実行
cat ~/.ssh/id_rsa.pub
```

#### 4-2. VPSに公開鍵を追加

```bash
# VPSで実行
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
# ↑ ローカルマシンの公開鍵を貼り付け

chmod 600 ~/.ssh/authorized_keys
```

#### 4-3. SSH鍵認証をテスト

**新しいターミナルを開いて**テスト（既存のセッションは閉じないこと）:

```bash
# ローカルマシンから新しいターミナルで
ssh root@<VPSのIPアドレス>
```

パスワードを聞かれずにログインできればOK。

#### 4-4. SSH設定を強化

鍵認証が確認できたら:

```bash
# VPSで実行
sudo nano /etc/ssh/sshd_config
```

以下を設定:
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
```

SSH再起動:
```bash
sudo systemctl restart sshd
```

### Step 5: Dockerのセキュアインストール

```bash
# Dockerセキュリティ設定
sudo ./scripts/setup_docker_security.sh
```

**実行内容:**
- Docker公式リポジトリからインストール
- daemon.json セキュリティ設定
- Docker Bench Security インストール
- Trivy（脆弱性スキャナー）インストール

**所要時間:** 約5-7分

### Step 6: セキュリティスキャン実行

```bash
# セキュリティスキャン
./scripts/security_scan.sh --system-only
```

## 🔒 セキュリティ状態の確認

### ファイアウォール確認
```bash
sudo ufw status verbose
```

期待される出力:
```
Status: active
To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

### Fail2ban確認
```bash
sudo fail2ban-client status sshd
```

### Docker確認
```bash
docker --version
docker compose version
sudo systemctl status docker
```

### セキュリティ監査
```bash
sudo /opt/docker-bench-security/docker-bench-security.sh
```

## 📦 アプリケーションのデプロイ

セキュアなテンプレートを使用:

```bash
# セキュアなDocker Composeテンプレートをコピー
cp docker/docker-compose.secure.template.yml docker-compose.yml

# 環境変数ファイルを作成
cp .env.example .env
nano .env  # 実際の値を設定

# .envのパーミッション設定
chmod 600 .env
```

docker-compose.ymlを編集してアプリケーション設定を追加:

```bash
nano docker-compose.yml
```

起動:
```bash
docker compose up -d
```

## 🔍 定期的なメンテナンス

### 週次: セキュリティスキャン
```bash
./scripts/security_scan.sh
```

### 月次: システムメンテナンス
```bash
sudo ./scripts/maintenance.sh
```

### 自動化（cron設定）
```bash
# cronジョブを追加
sudo crontab -e
```

以下を追加:
```cron
# 毎週日曜日 2:00 AM にセキュリティスキャン
0 2 * * 0 /opt/vps-automation-openclaw/scripts/security_scan.sh --all

# 毎月1日 3:00 AM にメンテナンス
0 3 1 * * /opt/vps-automation-openclaw/scripts/maintenance.sh
```

## 🚨 トラブルシューティング

### SSH接続ができなくなった

1. ConoHaコントロールパネルからコンソールにアクセス
2. `/etc/ssh/sshd_config` を確認
3. 設定を戻して `sudo systemctl restart sshd`

### Dockerが起動しない

```bash
# Dockerログを確認
sudo journalctl -u docker.service -f

# daemon.jsonの構文確認
sudo cat /etc/docker/daemon.json | jq .

# Dockerを再起動
sudo systemctl restart docker
```

### UFWで接続がブロックされる

```bash
# 特定のポートを許可
sudo ufw allow <ポート番号>/tcp

# UFWを一時的に無効化（テスト用）
sudo ufw disable
```

## 📚 次のステップ

1. [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) で詳細なセキュリティ設定を確認
2. SSL/TLS証明書の設定（Let's Encrypt）
3. バックアップ戦略の実装
4. 監視・アラートの設定
5. ログ集約システムの導入

## ⚠️ セキュリティ上の注意

- [ ] rootログインは必ず無効化
- [ ] SSH鍵認証のみを使用
- [ ] 定期的にセキュリティスキャンを実施
- [ ] シークレットをgitにコミットしない
- [ ] 定期的にバックアップを取得
- [ ] アクセスログを定期的に確認

## 📞 サポート

問題が発生した場合:

1. [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) を確認
2. [GitHub Issues](https://github.com/<your-repo>/vps-automation-openclaw/issues) で質問
3. セキュリティインシデントの場合は速やかに対処

---

**セキュリティは一度の設定では終わりません。定期的なメンテナンスと監視を忘れずに！**
