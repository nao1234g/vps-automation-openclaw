# VPS エージェント動作確認 & Telegram設定 指示書

> この指示をVPS上のClaude Codeにそのまま貼り付けてください。

---

## 指示

以下の2つのタスクを順番に実行してください。

---

## タスク1: 7エージェントの動作確認

### 1-1. OpenClaw CLIでエージェント一覧を確認

```bash
# コンテナ内でエージェント一覧を確認
docker exec openclaw-agent openclaw gateway call agents.list 2>&1

# うまくいかない場合、設定ファイルから直接確認
docker exec openclaw-agent cat /home/appuser/.openclaw/openclaw.json 2>&1 | python3 -c "
import sys, json
data = json.load(sys.stdin)
agents = data.get('agents', {}).get('list', [])
for a in agents:
    name = a.get('identity', {}).get('name', 'unknown')
    model = a.get('model', 'unknown')
    default = ' (DEFAULT)' if a.get('default') else ''
    print(f'  {name} -> {model}{default}')
"
```

### 1-2. Gemini APIキーが実際に動くかテスト

```bash
# Google Gemini API の疎通テスト
GOOGLE_KEY=$(docker exec openclaw-agent printenv GOOGLE_API_KEY)
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${GOOGLE_KEY}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    models = data.get('models', [])
    gemini_models = [m['name'] for m in models if 'gemini' in m.get('name','').lower()]
    print(f'API疎通: OK ({len(gemini_models)}個のGeminiモデルが利用可能)')
    for m in gemini_models[:5]:
        print(f'  - {m}')
except Exception as e:
    print(f'API疎通: NG ({e})')
    print(sys.stdin.read() if hasattr(sys.stdin, 'read') else '')
" 2>&1
```

### 1-3. OpenClaw Gateway経由でJarvisに話しかけるテスト

```bash
# Gateway のWebSocket経由でテスト（curlでHTTP APIを試す）
# OpenClawのGatewayトークンを取得
GW_TOKEN=$(docker exec openclaw-agent printenv OPENCLAW_GATEWAY_TOKEN 2>/dev/null || grep OPENCLAW_GATEWAY_TOKEN /opt/openclaw/.env | cut -d= -f2)

echo "Gateway Token: ${GW_TOKEN:0:8}..."

# ヘルスチェック
curl -sf http://localhost:3000/ && echo "Gateway: 応答あり" || echo "Gateway: 応答なし"
```

### 1-4. ログからエラー確認

```bash
# 直近のログでエラーがないか確認
docker logs openclaw-agent --tail 50 2>&1 | grep -iE 'error|fail|warn|exception' || echo "エラーなし"
```

---

## タスク2: Telegram接続の調査と設定

### 2-1. 現在のTelegram設定状況を確認

```bash
# .env のTelegram設定を確認（値は伏せる）
grep -i telegram /opt/openclaw/.env 2>/dev/null | sed 's/=.*/=***/'

# OpenClaw設定内のTelegram/チャンネル設定を確認
docker exec openclaw-agent cat /home/appuser/.openclaw/openclaw.json 2>&1 | python3 -c "
import sys, json
data = json.load(sys.stdin)
# channels/telegram/messaging などのキーを探す
def find_telegram(d, path=''):
    if isinstance(d, dict):
        for k, v in d.items():
            if 'telegram' in k.lower() or 'channel' in k.lower() or 'messaging' in k.lower():
                print(f'  {path}.{k}: {json.dumps(v, indent=2, ensure_ascii=False)[:200]}')
            find_telegram(v, f'{path}.{k}')
find_telegram(data)
" 2>&1

# ログからTelegram関連を検索
docker logs openclaw-agent 2>&1 | grep -i telegram | tail -10 || echo "Telegramログなし"
```

### 2-2. OpenClawのTelegramチャンネル設定を追加

**注意**: この手順はTelegram Bot Tokenが必要です。
もし `.env` に `TELEGRAM_BOT_TOKEN` が空または未設定の場合、
「Telegram Bot Tokenが未設定です。BotFatherでボットを作成し、トークンを取得してください」
と報告して、このステップはスキップしてください。

Telegram Bot Tokenが設定されている場合のみ、以下を実行：

```bash
# 1. 現在のopenclaw.jsonを取得
docker exec openclaw-agent cat /home/appuser/.openclaw/openclaw.json > /tmp/openclaw_current.json

# 2. Telegramチャンネル設定を追加したバージョンを作成
# （openclaw.jsonの gateway セクションに telegram チャンネルを追加）
python3 << 'PYEOF'
import json

with open('/tmp/openclaw_current.json', 'r') as f:
    config = json.load(f)

# Telegram Bot Token を環境変数から取得する設定
# OpenClawはgateway.channels.telegramでTelegram接続を管理
if 'gateway' not in config:
    config['gateway'] = {}

if 'channels' not in config['gateway']:
    config['gateway']['channels'] = {}

config['gateway']['channels']['telegram'] = {
    "enabled": True
}

with open('/tmp/openclaw_updated.json', 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print("Telegram設定を追加しました")
print(json.dumps(config['gateway'].get('channels', {}), indent=2, ensure_ascii=False))
PYEOF

# 3. 更新した設定をコンテナにコピー
docker cp /tmp/openclaw_updated.json openclaw-agent:/home/appuser/.openclaw/openclaw.json

# 4. コンテナ再起動
cd /opt/openclaw && docker-compose -f docker-compose.quick.yml restart openclaw

# 5. 30秒待ってからログ確認
sleep 30
docker logs openclaw-agent --tail 30 2>&1 | grep -iE 'telegram|channel|bot'
```

### 2-3. docker-compose.quick.yml にTelegram環境変数が渡されているか確認

```bash
# docker-compose.quick.yml のTelegram関連設定を確認
grep -A2 -i telegram /opt/openclaw/docker-compose.quick.yml 2>/dev/null || echo "docker-compose.quick.ymlにTelegram設定なし"

# もしTELEGRAM_BOT_TOKEN環境変数がcomposeに定義されていない場合、
# openclaw サービスの environment セクションに以下を追加する必要がある:
# TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:-}
```

---

## レポート形式

```
=== エージェント & Telegram レポート ===

【エージェント動作確認】
- エージェント一覧: （7人の名前とモデル）
- Gemini API疎通: OK / NG
- Gateway応答: OK / NG
- エラー有無: なし / あり（内容）

【Telegram状況】
- Bot Token: 設定あり / 未設定
- openclaw.json内のTelegram設定: あり / なし
- Telegram接続ログ: 接続成功 / エラー / ログなし

【必要なアクション】
- （残っている作業があれば記載）
```
