# VPS調査指示書（Claude Code用）

> この指示をClaude Code（VPS上）にそのまま貼り付けてください。

---

## 指示

あなたはConoHa VPS（IP: 163.44.124.123）上で動作しているClaude Codeです。
このVPSで動いているOpenClaw + N8N + Telegramボットの**現状を完全に把握**してください。

以下の調査を順番に実行し、最後に「調査結果レポート」をまとめてください。

---

## 調査項目

### 1. Docker環境の全体像
```bash
# 動いているコンテナ一覧（名前・イメージ・状態・ポート）
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

# 停止中も含めた全コンテナ
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'

# docker compose のプロジェクト一覧
docker compose ls

# 使われているネットワーク
docker network ls
```

### 2. OpenClawの設定ファイル（最重要）
```bash
# OpenClawコンテナの名前を特定
docker ps --filter "name=openclaw" --format '{{.Names}}'

# コンテナ内の openclaw.json を表示（実際に使われている設定）
docker exec <OpenClawコンテナ名> cat /home/appuser/.openclaw/openclaw.json 2>/dev/null || \
docker exec <OpenClawコンテナ名> cat /root/.openclaw/openclaw.json 2>/dev/null || \
echo "openclaw.json が見つかりません"

# コンテナ内の全設定ファイルを探す
docker exec <OpenClawコンテナ名> find / -name "openclaw.json" -o -name "config.json" 2>/dev/null | head -20

# OpenClawの環境変数（APIキーやTelegramトークン）
docker exec <OpenClawコンテナ名> env | grep -iE 'TELEGRAM|ANTHROPIC|GOOGLE|OPENAI|GEMINI|OPENCLAW|MODEL|AGENT' | sort
```

### 3. Telegramボットの接続状況
```bash
# OpenClawのログからTelegram関連のメッセージを探す
docker logs <OpenClawコンテナ名> 2>&1 | grep -i telegram | tail -30

# Telegramボットの起動ログ
docker logs <OpenClawコンテナ名> 2>&1 | grep -iE 'telegram|bot|channel|plugin' | tail -30

# 最新のログ50行（エラーがないか確認）
docker logs <OpenClawコンテナ名> --tail 50 2>&1
```

### 4. エージェント設定の確認
```bash
# 利用可能なエージェント一覧（ログから確認）
docker logs <OpenClawコンテナ名> 2>&1 | grep -iE 'agent|model|gemini|claude|jarvis' | tail -30

# プラグイン一覧
docker logs <OpenClawコンテナ名> 2>&1 | grep -iE 'plugin|enabled|disabled|channel' | tail -30
```

### 5. Docker Composeの構成
```bash
# OpenClawのデプロイに使われたdocker-compose.ymlを探す
find / -name "docker-compose*.yml" -o -name "docker-compose*.yaml" 2>/dev/null | head -20

# 各 docker-compose.yml の中身を表示
# 見つかったファイルをそれぞれ cat で表示

# .env ファイルを探す（APIキーの値は伏せて、変数名だけ報告）
find / -name ".env" -path "*/openclaw*" -o -name ".env" -path "*/opt/*" 2>/dev/null | head -10
```

### 6. Caddy（リバースプロキシ）の設定
```bash
# Caddyの設定ファイル
cat /etc/caddy/Caddyfile 2>/dev/null || echo "Caddyfile not found"

# Caddy がコンテナで動いているか、ホストで動いているか
systemctl status caddy 2>/dev/null | head -10
docker ps --filter "name=caddy" --format '{{.Names}} {{.Status}}' 2>/dev/null
```

### 7. SSHとユーザー設定
```bash
# 現在のユーザー
whoami

# SSH可能なユーザー一覧（authorized_keysがあるユーザー）
for dir in /home/*/ /root/; do
  if [ -f "${dir}.ssh/authorized_keys" ]; then
    echo "User: $(basename $dir) -> authorized_keys あり"
  fi
done

# SSH設定（rootログインの可否）
grep -E 'PermitRootLogin|PasswordAuthentication|AllowUsers' /etc/ssh/sshd_config 2>/dev/null

# 一般ユーザー一覧
cat /etc/passwd | grep -E '/bin/(bash|sh|zsh)' | cut -d: -f1
```

### 8. ディスクとリソース状況
```bash
# ディスク使用量
df -h /

# Docker のディスク使用量
docker system df

# メモリ使用量
free -h
```

---

## レポート形式

調査が完了したら、以下の形式でレポートをまとめてください：

```
=== VPS調査レポート ===

【1. 動いているサービス】
- コンテナ名: xxx / イメージ: xxx / 状態: xxx

【2. OpenClawの設定】
- 設定ファイルの場所: xxx
- 設定されているエージェント: （名前とモデル名を列挙）
- Telegram接続: 有/無 （トークンの有無）

【3. Telegramボット】
- 動作状況: 動いている / エラーあり
- 使用モデル: xxx
- エラーがあれば内容を記載

【4. docker-compose構成】
- 使用ファイルのパス: xxx
- このリポジトリとの差異: xxx

【5. Caddy設定】
- 設定内容のサマリー

【6. SSHアクセス】
- 利用可能なユーザー名: xxx
- rootログイン: 可/不可

【7. 問題点と推奨アクション】
- 問題1: xxx → 対策: xxx
- 問題2: xxx → 対策: xxx
```

---

## 重要な注意

- APIキーやパスワードの**実際の値**はレポートに含めないこと（「設定あり」「未設定」だけで十分）
- `docker exec` のコンテナ名は、手順1で確認した実際の名前に置き換えること
- エラーが出たコマンドは、エラー内容もレポートに含めること
