# VPS 総合セットアップ指示書

> この指示をVPS上のClaude Codeにそのまま貼り付けてください。
> 日本語で応答してください。全ステップ完了後にレポートを出してください。

---

## 最初に必ずやること: tmux セッション

コンソール（Butterfly）は5〜10分で切断されます。
作業が消えないように、**最初に必ず tmux を起動してください。**

```bash
# tmux がインストールされているか確認、なければインストール
which tmux || apt install -y tmux

# 既存セッションがあればアタッチ、なければ新規作成
tmux attach -t work 2>/dev/null || tmux new -s work
```

以降の全ての作業は **tmux セッション内** で実行してください。
コンソールが切断されても、再接続後に `tmux attach -t work` で復帰できます。

---

## やること（3つ）

1. **SSH復旧** — sshdを直して、バタフライコンソールなしでアクセスできるようにする
2. **Control UI 外部公開** — スマホからブラウザで8人のAIエージェントにアクセスできるようにする
3. **Telegram動作確認** — ボットが動いているか確認

---

## ステップ1: 現状把握（まずこれを全部実行）

```bash
echo "=========================================="
echo "  VPS 総合ステータスチェック"
echo "=========================================="

echo ""
echo "=== 1. OS・ネットワーク ==="
hostname && ip addr show | grep 'inet ' | head -5

echo ""
echo "=== 2. Docker コンテナ ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>&1

echo ""
echo "=== 3. OpenClaw Gateway ==="
curl -sf http://localhost:3000/ > /dev/null && echo "応答: OK" || echo "応答: NG"

echo ""
echo "=== 4. SSH デーモン ==="
systemctl is-active sshd 2>/dev/null || systemctl is-active ssh 2>/dev/null || echo "停止中"
ss -tlnp | grep ':22' || echo "ポート22: 待ち受けなし"

echo ""
echo "=== 5. Caddy ==="
systemctl is-active caddy 2>/dev/null && echo "systemd: 稼働中" || echo "systemd: 停止"
docker ps --filter "name=caddy" --format '{{.Names}} {{.Status}}' 2>/dev/null | head -1
cat /etc/caddy/Caddyfile 2>/dev/null || echo "Caddyfile: なし"

echo ""
echo "=== 6. UFW ファイアウォール ==="
ufw status 2>/dev/null || echo "UFW: なし"

echo ""
echo "=== 7. ポート待ち受け ==="
ss -tlnp | grep -E ':22|:80|:443|:3000|:5678'

echo ""
echo "=== 8. Telegram 状態 ==="
docker logs openclaw-agent --tail 10 2>&1 | grep -iE 'telegram|connected|error' || echo "Telegram関連ログなし"

echo ""
echo "=== 9. SSH 設定ファイル ==="
cat /etc/ssh/sshd_config 2>/dev/null | grep -E '^(Port|PermitRootLogin|PubkeyAuth|PasswordAuth|AuthorizedKeys)' || echo "sshd_config: なし"

echo ""
echo "=== 10. SSH 鍵 ==="
ls -la /root/.ssh/ 2>/dev/null || echo "/root/.ssh/ なし"
ls -la /home/*/.ssh/ 2>/dev/null || echo "一般ユーザーの.ssh なし"
```

上記の結果を確認した上で、以下のステップ2〜4を状況に応じて実行してください。

---

## ステップ2: SSH復旧

### 2-1. sshdがインストールされているか確認

```bash
which sshd || apt install -y openssh-server
```

### 2-2. sshd_config を安全な設定にする

```bash
# 現在のsshd_configをバックアップ
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d)

# 設定を確認・修正（以下のポイントだけ確認）
# - Port 22（デフォルトでOK）
# - PermitRootLogin: prohibit-password または yes（鍵認証のみ許可）
# - PubkeyAuthentication yes
# - PasswordAuthentication: とりあえず yes にする（後で no にすべき）
```

重要: 現在の `/etc/ssh/sshd_config` を読んで、上記の設定値を確認してください。
`PasswordAuthentication` が `no` で鍵が設定されていない場合、`yes` に変更してください。

### 2-3. sshdを起動

```bash
systemctl enable ssh
systemctl start ssh
systemctl status ssh
```

### 2-4. ファイアウォールでSSHを許可

```bash
ufw allow 22/tcp comment "SSH"
ufw status
```

### 2-5. 接続テスト

```bash
# ローカルから自分自身にSSH接続テスト
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 localhost echo "SSH OK" 2>&1 || echo "SSH接続失敗"

# ポート確認
ss -tlnp | grep ':22'
```

### 2-6. ユーザーとパスワードの確認

```bash
echo "=== ログイン可能なユーザー ==="
# rootのパスワード状態
passwd -S root 2>/dev/null

# 一般ユーザー一覧（UID 1000以上）
awk -F: '$3 >= 1000 && $3 < 65534 {print $1, "(UID:" $3 ")"}' /etc/passwd

# SSH鍵があるユーザー
for dir in /root /home/*; do
    user=$(basename $dir)
    if [ -f "$dir/.ssh/authorized_keys" ]; then
        keys=$(wc -l < "$dir/.ssh/authorized_keys")
        echo "$user: SSH鍵 ${keys}個"
    fi
done
```

---

## ステップ3: Control UI 外部公開

### 3-1. Caddyが動いているか確認・起動

```bash
# Caddyがインストールされているか
which caddy || {
    echo "Caddyをインストール..."
    apt update && apt install -y caddy
}

# Caddyが動いているか
systemctl is-active caddy || {
    echo "Caddyを起動..."
    systemctl enable caddy
    systemctl start caddy
}
```

### 3-2. Caddyfileを設定

現在の `/etc/caddy/Caddyfile` を読んで確認してください。

OpenClaw Control UI (`localhost:3000`) へのリバースプロキシが設定されていない場合、
以下の内容で `/etc/caddy/Caddyfile` を更新してください：

```
:80 {
    reverse_proxy localhost:3000
}
```

注意: IPアドレスやドメインではなく `:80` で待ち受けます（SSL証明書の問題を避けるため）。

設定変更後：
```bash
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
```

### 3-3. ファイアウォールでHTTP/HTTPSを許可

```bash
ufw allow 80/tcp comment "HTTP - Control UI"
ufw allow 443/tcp comment "HTTPS"
ufw status
```

### 3-4. アクセステスト

```bash
echo "=== アクセステスト ==="

echo "1. OpenClaw直接 (localhost:3000):"
curl -sf http://localhost:3000/ | head -c 100
echo ""

echo "2. Caddy経由 (localhost:80):"
curl -sf http://localhost:80/ | head -c 100
echo ""

echo "3. 外部IP:"
curl -sf --connect-timeout 5 http://163.44.124.123/ | head -c 100
echo ""

echo ""
echo "4. ポート状態:"
ss -tlnp | grep -E ':80|:443|:3000'
```

---

## ステップ4: Telegram確認

```bash
echo "=== Telegram ボット状態 ==="
docker logs openclaw-agent --tail 20 2>&1 | grep -iE 'telegram|bot|connected|pairing'

echo ""
echo "=== エージェント一覧 ==="
docker exec openclaw-agent cat /home/appuser/.openclaw/openclaw.json 2>&1 | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    agents = data.get('agents', {}).get('list', [])
    for a in agents:
        name = a.get('identity', {}).get('name', '?')
        model = a.get('model', '?')
        d = ' ★DEFAULT' if a.get('default') else ''
        print(f'  {name} ({model}){d}')
except Exception as e:
    print(f'エラー: {e}')
"
```

---

## レポート形式（必ずこの形式で報告してください）

```
=== VPS 総合セットアップ レポート ===

【tmux】
- セッション: 起動済み / 既存に接続 / 失敗

【SSH復旧】
- sshd状態: 稼働中 / 停止（理由）
- ポート22: 開放 / ブロック
- ログイン方法: ssh ユーザー名@163.44.124.123
- パスワード認証: 有効 / 無効
- 備考: （パスワードが分からない等あれば）

【Control UI 外部公開】
- Caddy: 稼働中 / 停止
- ファイアウォール: 80許可 / ブロック
- 外部アクセス: OK / NG
- アクセスURL: http://163.44.124.123
- 認証: トークン入力が必要 / 不要

【Telegram】
- ボット: 接続中 / 切断
- エージェント数: X人

【残課題】
- （あれば記載）
```
