# VPS Control UI 外部アクセス設定 指示書

> この指示をVPS上のClaude Codeにそのまま貼り付けてください。
> 日本語で応答してください。

---

## 目的

スマホのブラウザからOpenClaw Control UI にアクセスできるようにする。
Control UI では8人のAIエージェントをドロップダウンで自由に切り替えられる。

VPS IP: 163.44.124.123

---

## ステップ1: 現在の状態を確認

以下を全部実行して、結果をまとめて報告してください。

```bash
echo "=== 1. Docker コンテナ状態 ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>&1

echo ""
echo "=== 2. OpenClaw Gateway 応答テスト ==="
curl -sf http://localhost:3000/ && echo "→ 応答あり" || echo "→ 応答なし"

echo ""
echo "=== 3. Caddy 状態 ==="
systemctl is-active caddy 2>/dev/null && echo "→ systemdで稼働中" || echo "→ systemdでは動いていない"
docker ps --filter "name=caddy" --format '{{.Names}} {{.Status}}' 2>/dev/null | grep -q caddy && echo "→ Dockerで稼働中" || echo "→ Dockerでは動いていない"

echo ""
echo "=== 4. Caddyfile 内容 ==="
cat /etc/caddy/Caddyfile 2>/dev/null || echo "→ /etc/caddy/Caddyfile が見つかりません"

echo ""
echo "=== 5. UFW ファイアウォール状態 ==="
ufw status 2>/dev/null || echo "→ UFWが見つかりません"

echo ""
echo "=== 6. ポート待ち受け状態 ==="
ss -tlnp | grep -E ':80|:443|:3000|:5678' 2>/dev/null || echo "→ ss コマンド失敗"

echo ""
echo "=== 7. Telegram ボット状態 ==="
docker logs openclaw-agent --tail 5 2>&1 | grep -iE 'telegram|error' || echo "→ Telegram関連ログなし"
```

---

## ステップ2: 問題に応じて修正

### ケースA: Dockerコンテナが停止している場合

```bash
cd /opt/openclaw
docker compose -f docker-compose.quick.yml up -d
sleep 30
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

### ケースB: Caddyが停止している場合

```bash
# systemdの場合
systemctl start caddy
systemctl enable caddy
systemctl status caddy

# Dockerの場合
docker start caddy  # コンテナ名が違う場合は docker ps -a で確認
```

### ケースC: UFWでHTTPS(443)がブロックされている場合

```bash
# HTTP と HTTPS を許可
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"
ufw status
```

### ケースD: Caddyfileにリバースプロキシ設定がない場合

現在のCaddyfileを確認して、OpenClaw Control UI (localhost:3000) へのリバースプロキシが設定されているか確認してください。

設定されていない場合、以下のように設定してください：

```
# /etc/caddy/Caddyfile に追記または修正
163.44.124.123 {
    reverse_proxy localhost:3000
}

# N8Nも必要なら
n8n.163.44.124.123.nip.io {
    reverse_proxy localhost:5678
}
```

設定変更後：
```bash
caddy validate --config /etc/caddy/Caddyfile && caddy reload --config /etc/caddy/Caddyfile
# または
systemctl reload caddy
```

### ケースE: Caddyfileが存在しない場合

```bash
# Caddyがインストールされているか確認
which caddy || echo "Caddy未インストール"

# 未インストールの場合
apt update && apt install -y caddy

# Caddyfileを作成
cat > /etc/caddy/Caddyfile << 'EOF'
# OpenClaw Control UI
163.44.124.123 {
    reverse_proxy localhost:3000
}
EOF

# 起動
systemctl enable caddy
systemctl start caddy
```

---

## ステップ3: 外部アクセステスト

```bash
echo "=== 外部アクセステスト ==="

# ローカルからの応答確認
echo "1. localhost:3000 →"
curl -sf http://localhost:3000/ | head -c 200
echo ""

# Caddy経由のテスト
echo "2. Caddy経由 (127.0.0.1:80) →"
curl -sf http://127.0.0.1:80/ | head -c 200
echo ""

# 外部IPからのテスト（自分自身に対して）
echo "3. 外部IP (163.44.124.123) →"
curl -sf --connect-timeout 5 http://163.44.124.123/ | head -c 200
echo ""

echo ""
echo "=== ポート到達テスト ==="
timeout 3 bash -c 'echo > /dev/tcp/163.44.124.123/80' 2>/dev/null && echo "ポート80: 開いている" || echo "ポート80: 閉じている"
timeout 3 bash -c 'echo > /dev/tcp/163.44.124.123/443' 2>/dev/null && echo "ポート443: 開いている" || echo "ポート443: 閉じている"
timeout 3 bash -c 'echo > /dev/tcp/163.44.124.123/3000' 2>/dev/null && echo "ポート3000: 開いている" || echo "ポート3000: 閉じている"
```

---

## ステップ4: セキュリティ確認

Control UIを外部公開する際、トークン認証が有効になっているか確認してください。

```bash
echo "=== Control UI 認証設定 ==="
docker exec openclaw-agent cat /home/appuser/.openclaw/openclaw.json 2>&1 | python3 -c "
import sys, json
data = json.load(sys.stdin)
gw = data.get('gateway', {})
auth = gw.get('auth', {})
cui = gw.get('controlUi', {})
print(f'認証モード: {auth.get(\"mode\", \"なし\")}')
print(f'トークン設定: {\"あり\" if auth.get(\"token\") else \"なし\"}')
print(f'デバイス認証無効化: {cui.get(\"dangerouslyDisableDeviceAuth\", False)}')
print(f'非セキュア認証許可: {cui.get(\"allowInsecureAuth\", False)}')
"
```

認証が弱い場合は、最低限トークン認証が有効であることを確認してください（現在の設定で有効になっているはずです）。

---

## レポート形式（必ずこの形式で報告してください）

```
=== Control UI 外部アクセス設定 レポート ===

【コンテナ状態】
- openclaw-agent: 稼働中 / 停止
- openclaw-postgres: 稼働中 / 停止
- openclaw-n8n: 稼働中 / 停止

【Caddy状態】
- 稼働: はい / いいえ
- 方式: systemd / Docker / なし

【ファイアウォール】
- ポート80: 許可 / ブロック
- ポート443: 許可 / ブロック

【修正した内容】
- （何をしたか箇条書き）

【アクセステスト結果】
- localhost:3000 → OK / NG
- Caddy経由 → OK / NG
- 外部IP → OK / NG

【スマホからのアクセス方法】
- URL: （実際にアクセスできるURL）
- 認証: トークン入力が必要 / 不要

【Telegram ボット】
- 状態: 動作中 / 停止
```
