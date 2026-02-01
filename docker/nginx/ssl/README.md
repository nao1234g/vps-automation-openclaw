# SSL証明書ディレクトリ

## 📖 概要

このディレクトリには、NginxのSSL/TLS証明書ファイルを配置します。

## 🔒 必要なファイル

- `fullchain.pem` - 完全な証明書チェーン
- `privkey.pem` - 秘密鍵

## 🚀 セットアップ方法

### 方法1: Let's Encryptで自動取得（推奨）

```bash
sudo ./scripts/setup_ssl.sh your-domain.com your-email@example.com
```

自動的に証明書を取得し、このディレクトリに配置します。

### 方法2: 既存の証明書をコピー

```bash
# Let's Encrypt証明書をコピー
sudo cp /etc/letsencrypt/live/your-domain/fullchain.pem docker/nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain/privkey.pem docker/nginx/ssl/
sudo chmod 644 docker/nginx/ssl/fullchain.pem
sudo chmod 600 docker/nginx/ssl/privkey.pem
```

### 方法3: 自己署名証明書を生成（開発環境のみ）

```bash
cd docker/nginx/ssl

# 自己署名証明書を生成
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout privkey.pem \
  -out fullchain.pem \
  -subj "/C=JP/ST=Tokyo/L=Tokyo/O=OpenClaw/CN=localhost"

# パーミッション設定
chmod 644 fullchain.pem
chmod 600 privkey.pem
```

⚠️ **注意**: 自己署名証明書は開発環境でのみ使用してください。本番環境では必ずLet's Encryptなどの信頼された認証局の証明書を使用してください。

## 📋 証明書の確認

### 証明書情報の確認

```bash
openssl x509 -in docker/nginx/ssl/fullchain.pem -text -noout
```

### 有効期限の確認

```bash
openssl x509 -in docker/nginx/ssl/fullchain.pem -noout -dates
```

### 秘密鍵の確認

```bash
openssl rsa -in docker/nginx/ssl/privkey.pem -check
```

## 🔄 証明書の更新

Let's Encrypt証明書は90日ごとに更新が必要です。

### 自動更新（Cron）

setup.shで自動更新が設定されている場合、毎週日曜日に自動的にチェックされます。

### 手動更新

```bash
# 更新チェック
sudo certbot renew

# 強制更新
sudo certbot renew --force-renewal

# Nginx再起動
docker compose -f docker-compose.production.yml restart nginx
```

## 🔒 セキュリティ

- **秘密鍵の保護**: privkey.pemのパーミッションは600（所有者のみ読み取り可）
- **バックアップ**: 証明書と秘密鍵は安全な場所にバックアップ
- **Git除外**: .gitignoreで証明書ファイルは除外されています

## 📚 参考リンク

- [Let's Encrypt公式サイト](https://letsencrypt.org/)
- [Certbot公式ドキュメント](https://certbot.eff.org/)
- [SSL Labs SSL Test](https://www.ssllabs.com/ssltest/)
