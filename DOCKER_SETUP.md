# OpenClaw VPS + Docker セットアップガイド

## 🏗️ 構成概要

```
あなたのPC (ローカル)
    ↓ SSH Tunnel (暗号化)
ConoHa VPS (第1層隔離)
    ↓ Docker Network (第2層隔離)
    ├── OpenClaw Container (AI Agent)
    ├── N8N Container (Workflow Automation)
    ├── OpenNotebook Container (Knowledge Management)
    ├── PostgreSQL Container (Database)
    └── Nginx Container (Reverse Proxy - Optional)
```

## 🚀 クイックスタート

### 1. VPSにSSH接続

```bash
ssh root@YOUR_VPS_IP
```

### 2. セットアップスクリプトをダウンロード＆実行

```bash
wget https://raw.githubusercontent.com/nao1234g/vps-automation-openclaw/main/scripts/setup_docker.sh
chmod +x setup_docker.sh
./setup_docker.sh
```

### 3. 環境変数を設定

```bash
cd /opt/openclaw-docker
sudo nano .env
```

**必須項目：**
- `ANTHROPIC_API_KEY` または `ZHIPUAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `POSTGRES_PASSWORD`（デフォルトから変更）

### 4. Docker Composeで起動

```bash
cd /opt/openclaw-docker
sudo docker compose up -d --build
```

**初回ビルドは10-15分かかります。**

### 5. ログを確認

```bash
sudo docker compose logs -f openclaw
```

### 6. ローカルPCからSSH Tunnelで接続

**別のターミナルで実行：**
```bash
ssh -L 3000:localhost:3000 \
    -L 5678:localhost:5678 \
    -L 8080:localhost:8080 \
    root@YOUR_VPS_IP
```

### 7. ブラウザでアクセス

- **OpenClaw**: http://localhost:3000
- **N8N**: http://localhost:5678 (admin / your_password)
- **OpenNotebook**: http://localhost:8080

---

## 🔧 Docker操作コマンド

### コンテナの起動/停止

```bash
# 起動
sudo docker compose up -d

# 停止
sudo docker compose down

# 再起動
sudo docker compose restart

# 特定のサービスのみ再起動
sudo docker compose restart openclaw
```

### ログの確認

```bash
# 全サービスのログ
sudo docker compose logs -f

# OpenClawのログのみ
sudo docker compose logs -f openclaw

# 最新100行のみ表示
sudo docker compose logs --tail=100 openclaw
```

### ステータス確認

```bash
# コンテナの状態
sudo docker compose ps

# リソース使用状況
sudo docker stats
```

### データのバックアップ

```bash
# 停止
sudo docker compose down

# ボリュームをバックアップ
sudo tar czf openclaw-backup-$(date +%Y%m%d).tar.gz \
  /var/lib/docker/volumes/openclaw-docker_*

# 再起動
sudo docker compose up -d
```

### データの復元

```bash
sudo docker compose down
sudo tar xzf openclaw-backup-YYYYMMDD.tar.gz -C /
sudo docker compose up -d
```

---

## 🛡️ セキュリティ機能

### 二重隔離構造

1. **第1層: VPS隔離**
   - 専用VPSサーバーで物理的に隔離
   - SSH鍵認証のみ許可
   - ファイアウォールで22番ポートのみ開放

2. **第2層: Docker隔離**
   - コンテナ間は独立したネットワーク
   - 全サービスは `127.0.0.1` のみバインド
   - 外部からは直接アクセス不可

### アクセス制御

```yaml
# docker-compose.yml の設定
ports:
  - "127.0.0.1:3000:3000"  # ローカルホストのみ
```

これにより：
- ✅ VPS外部から直接アクセス不可
- ✅ SSH Tunnel経由でのみアクセス可能
- ✅ 他のコンテナからは内部DNSでアクセス

---

## 🎯 カスタムスキルの追加

### 1. スキルファイルを作成

```bash
cd /opt/openclaw-docker/skills
sudo nano my-custom-skill.js
```

### 2. スキルを実装

```javascript
module.exports = {
  name: "my_custom_skill",
  description: "カスタム機能の説明",
  
  async execute({ param1, param2 }) {
    // 実装
    return {
      success: true,
      message: "処理完了"
    };
  }
};
```

### 3. OpenClawコンテナを再起動

```bash
sudo docker compose restart openclaw
```

---

## 📊 リソース制限

### メモリ・CPU制限

```yaml
# docker-compose.yml
services:
  openclaw:
    mem_limit: 2g      # 最大2GB
    cpus: 1.5          # 最大1.5コア
```

### 推奨スペック

| サービス | RAM | CPU | ストレージ |
|---------|-----|-----|-----------|
| OpenClaw | 2GB | 1.5 | 10GB |
| N8N | 1GB | 1.0 | 5GB |
| OpenNotebook | 1GB | 1.0 | 5GB |
| PostgreSQL | 512MB | 0.5 | 10GB |
| **合計** | **4.5GB** | **4.0** | **30GB** |

**推奨VPSプラン：**
- CPU: 4コア以上
- RAM: 8GB以上
- ストレージ: 50GB以上

---

## 🐛 トラブルシューティング

### Q1: コンテナが起動しない

```bash
# ログを確認
sudo docker compose logs openclaw

# エラーメッセージを確認して修正
sudo docker compose down
sudo docker compose up -d --build
```

### Q2: SSH Tunnelが切断される

```bash
# autossh を使用して自動再接続
sudo apt install autossh

autossh -M 0 -N \
  -L 3000:localhost:3000 \
  -L 5678:localhost:5678 \
  -L 8080:localhost:8080 \
  root@YOUR_VPS_IP
```

### Q3: ディスク容量が不足

```bash
# 未使用のDockerイメージを削除
sudo docker system prune -a

# 未使用のボリュームを削除
sudo docker volume prune
```

---

## 📚 参考資料

- [Docker公式ドキュメント](https://docs.docker.com/)
- [Docker Compose リファレンス](https://docs.docker.com/compose/)
- [OpenClaw GitHub](https://github.com/Sh-Osakana/open-claw)
- [N8N ドキュメント](https://docs.n8n.io/)

