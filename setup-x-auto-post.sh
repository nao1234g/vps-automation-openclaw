#!/bin/bash
# AISA X自動投稿セットアップスクリプト
set -e

echo "🔐 VPSにSSH接続中..."

# 公開鍵を登録
echo "📝 SSH公開鍵を登録中..."
ssh-copy-id -i ~/.ssh/conoha_ed25519.pub root@163.44.124.123

echo "✅ SSH鍵登録完了！"

# auth_tokenを保存
echo "🔑 auth_tokenを保存中..."
ssh -i ~/.ssh/conoha_ed25519 root@163.44.124.123 "echo 'd4603995f4d2379ed8d6c22be7d144ddecb7f122' > /opt/.x-cookie && chmod 600 /opt/.x-cookie"

# x-auto-post.jsをアップロード
echo "📤 スクリプトをアップロード中..."
scp -i ~/.ssh/conoha_ed25519 scripts/x-auto-post.js root@163.44.124.123:/opt/x-auto-post.js

# Puppeteerがインストールされているか確認
echo "🔍 Puppeteerを確認中..."
ssh -i ~/.ssh/conoha_ed25519 root@163.44.124.123 "cd /opt && npm list puppeteer || npm install puppeteer"

# テスト投稿を実行
echo "🚀 テスト投稿を実行中..."
ssh -i ~/.ssh/conoha_ed25519 root@163.44.124.123 "cd /opt && node x-auto-post.js --cookie 'd4603995f4d2379ed8d6c22be7d144ddecb7f122' --tweet '🚀 AISA is now live! Asia'\''s leading crypto intelligence newsletter covering Japan, Korea, Hong Kong & Singapore. Subscribe: https://aisaintel.substack.com'"

echo "🎉 完了！"
