# N8N + OpenClaw 自動化セットアップガイド

## 📁 作成されたファイル

```
vps-automation-openclaw/
├── n8n-workflows/
│   ├── note-article-workflow.json  # Note記事自動生成ワークフロー
│   ├── x-autopost-workflow.json    # X自動投稿ワークフロー
│   └── prompts.md                  # コンテンツ生成用プロンプト集
└── scripts/
    └── install-n8n.sh              # N8Nインストールスクリプト
```

---

## 🚀 セットアップ手順

### Phase 1: N8Nインストール（VPSで実行）

ConoHa Webコンソールで以下を実行：

```bash
# インストールスクリプトをダウンロード＆実行
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/install-n8n.sh | bash
```

または手動で：

```bash
# Dockerでn8n起動
docker run -d --name n8n --restart always -p 5678:5678 \
  -e GENERIC_TIMEZONE=Asia/Tokyo \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n

# ファイアウォール開放
ufw allow 5678/tcp && ufw reload

# Caddyにリバースプロキシ追加
echo 'n8n.163.44.124.123.nip.io { reverse_proxy localhost:5678 }' >> /etc/caddy/Caddyfile
systemctl restart caddy
```

---

### Phase 2: N8N初期設定

1. ブラウザで https://n8n.163.44.124.123.nip.io/ にアクセス
2. 管理者アカウント作成
3. ワークフローをインポート

---

### Phase 3: ワークフロー設定

1. N8Nダッシュボード → Settings → Credentials
2. 以下を追加：
   - OpenClaw Token
   - X (Twitter) API credentials
   - Note API token (取得できれば)

3. ワークフローをインポート
   - note-article-workflow.json
   - x-autopost-workflow.json

4. 各ワークフローを有効化

---

## 📋 必要なAPI情報

| サービス | 必要な情報 |
|----------|-----------|
| OpenClaw | `3a1edd1b045a08c835ff743c02f26ca7` |
| X | API Key, API Secret, Access Token, Access Token Secret |
| Note | ログイン情報（API非公開のためブラウザ自動化が必要かも） |

---

## ⚠️ 注意事項

- NoteはPublic APIがないため、手動投稿が必要になる可能性あり
- X Free APIは月1,500投稿まで
- 自動化は段階的にテストすること
