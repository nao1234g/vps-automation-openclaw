# VPS Telegram マルチエージェント設定 指示書

> この指示をVPS上のClaude Codeにそのまま貼り付けてください。
> 日本語で応答してください。

---

## 背景

OpenClawのTelegramで現在Jarvisしか応答しません。
OpenClawは「bindings」という仕組みで、Telegramのグループ（チャット）ごとに
異なるエージェントを割り当てることができます。

以下の手順で、Telegramグループ別のエージェントルーティングを設定してください。

---

## ステップ1: 現在の設定確認

```bash
# 現在のopenclaw.jsonを確認
docker exec openclaw-agent cat /home/appuser/.openclaw/openclaw.json 2>&1 | python3 -c "
import sys, json
data = json.load(sys.stdin)
agents = data.get('agents', {}).get('list', [])
print('=== 登録エージェント ===')
for a in agents:
    name = a.get('identity', {}).get('name', '?')
    aid = a.get('id', '?')
    default = ' (DEFAULT)' if a.get('default') else ''
    print(f'  {aid}: {name}{default}')
print()
bindings = data.get('bindings', [])
print(f'=== bindings数: {len(bindings)} ===')
for b in bindings:
    print(f'  {json.dumps(b, ensure_ascii=False)}')
"
```

---

## ステップ2: Telegramグループ情報の取得

オーナーが以下のTelegramグループを作成し、ボット（@openclaw_nn2026_bot）を追加済みです。
各グループでメッセージを1つ送信した後、以下のコマンドでグループIDを取得してください。

```bash
# Telegramボットの最近の更新情報を取得してグループIDを確認
TELEGRAM_TOKEN=$(docker exec openclaw-agent printenv TELEGRAM_BOT_TOKEN 2>/dev/null)

if [ -z "$TELEGRAM_TOKEN" ]; then
    # .envから取得を試みる
    TELEGRAM_TOKEN=$(grep TELEGRAM_BOT_TOKEN /opt/openclaw/.env 2>/dev/null | cut -d= -f2)
fi

if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "エラー: TELEGRAM_BOT_TOKENが見つかりません"
else
    echo "Telegram Bot Token: ${TELEGRAM_TOKEN:0:8}..."
    echo ""
    echo "=== 最近のチャット一覧 ==="
    curl -s "https://api.telegram.org/bot${TELEGRAM_TOKEN}/getUpdates?offset=-50" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if not data.get('ok'):
    print('APIエラー:', data)
    sys.exit(1)
results = data.get('result', [])
chats = {}
for r in results:
    msg = r.get('message') or r.get('my_chat_member', {})
    chat = msg.get('chat', {})
    cid = chat.get('id')
    if cid and cid not in chats:
        chats[cid] = {
            'id': cid,
            'type': chat.get('type', '?'),
            'title': chat.get('title', chat.get('first_name', '?')),
        }
if not chats:
    print('チャット情報がありません。各グループで何かメッセージを送ってから再実行してください。')
else:
    for c in chats.values():
        kind = '1対1' if c['type'] == 'private' else 'グループ'
        print(f'  [{kind}] {c[\"title\"]} -> ID: {c[\"id\"]}')
"
fi
```

---

## ステップ3: bindingsの設定

以下のPythonスクリプトで openclaw.json に bindings を追加します。

**重要**: ステップ2で取得したグループIDを使ってスクリプト内の `GROUP_IDS` を更新してください。
グループIDが取得できていない場合は、取得できたものだけ設定してください。

```bash
# グループIDをここに設定（ステップ2の結果から）
# 形式: "エージェントID:グループID" のペア
# グループIDが分からないエージェントは省略可（Jarvisがデフォルトで応答）

python3 << 'PYEOF'
import json, os

# 現在の設定を読み込み
config_path = '/tmp/openclaw_current.json'
os.system('docker exec openclaw-agent cat /home/appuser/.openclaw/openclaw.json > ' + config_path)

with open(config_path, 'r') as f:
    config = json.load(f)

# === ここにグループIDを設定 ===
# ステップ2で取得したグループIDに置き換えてください
# 例: {"hawk-xresearch": -1001234567890, "alice-research": -1009876543210}
# グループIDは負の数です（通常 -100 で始まる）
GROUP_IDS = {
    # "hawk-xresearch": ここにHawkグループのID,
    # "alice-research": ここにAliceグループのID,
    # "codex-developer": ここにCodeXグループのID,
    # "luna-writer": ここにLunaグループのID,
    # "pixel-designer": ここにPixelグループのID,
    # "scout-data": ここにScoutグループのID,
    # "guard-security": ここにGuardグループのID,
}

# コメントアウトされていない（実際に値が設定された）エントリだけ使用
GROUP_IDS = {k: v for k, v in GROUP_IDS.items() if v is not None}

if not GROUP_IDS:
    print("警告: グループIDが設定されていません。")
    print("ステップ2を先に実行して、グループIDを取得してください。")
    print("取得後、このスクリプトのGROUP_IDS辞書にIDを設定して再実行してください。")
else:
    # bindings を構築
    bindings = []

    # 各グループ用のbinding
    for agent_id, group_id in GROUP_IDS.items():
        bindings.append({
            "agentId": agent_id,
            "match": {
                "channel": "telegram",
                "peer": {
                    "kind": "group",
                    "id": str(group_id)
                }
            }
        })

    # デフォルト: 1対1チャットやマッチしないものはJarvisが対応
    bindings.append({
        "agentId": "jarvis-cso",
        "match": {
            "channel": "telegram"
        }
    })

    config["bindings"] = bindings

    # 保存
    output_path = '/tmp/openclaw_updated.json'
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("=== bindings設定完了 ===")
    for b in bindings:
        agent = b['agentId']
        peer = b.get('match', {}).get('peer', {})
        if peer:
            print(f"  {agent} <- グループID: {peer.get('id')}")
        else:
            print(f"  {agent} <- デフォルト（1対1チャット等）")

    # コンテナにコピー
    os.system(f'docker cp {output_path} openclaw-agent:/home/appuser/.openclaw/openclaw.json')
    print("\n設定をコンテナにコピーしました。")

PYEOF
```

---

## ステップ4: コンテナ再起動と確認

```bash
# コンテナ再起動
cd /opt/openclaw && docker compose -f docker-compose.quick.yml restart openclaw

# 起動を待つ（60秒）
echo "起動待ち..."
sleep 60

# ヘルスチェック
curl -sf http://localhost:3000/ && echo "Gateway: 応答あり" || echo "Gateway: 応答なし"

# エラー確認
echo ""
echo "=== 最新ログ ==="
docker logs openclaw-agent --tail 30 2>&1 | grep -iE 'error|binding|telegram|agent|route' || echo "特筆すべきログなし"

# binding設定の確認
echo ""
echo "=== 設定確認 ==="
docker exec openclaw-agent cat /home/appuser/.openclaw/openclaw.json 2>&1 | python3 -c "
import sys, json
data = json.load(sys.stdin)
bindings = data.get('bindings', [])
print(f'bindings数: {len(bindings)}')
for b in bindings:
    agent = b.get('agentId', '?')
    match = b.get('match', {})
    peer = match.get('peer', {})
    if peer:
        print(f'  {agent} <- {peer.get(\"kind\", \"?\")} ID: {peer.get(\"id\", \"?\")}')
    else:
        channel = match.get('channel', '?')
        print(f'  {agent} <- デフォルト ({channel})')
"
```

---

## レポート形式

```
=== Telegram マルチエージェント設定 レポート ===

【グループID取得結果】
- 検出されたチャット: （一覧）

【bindings設定】
- 設定されたルート数: X
- 各エージェントの割り当て: （一覧）

【再起動結果】
- Gateway応答: OK / NG
- エラー: なし / あり（内容）

【テスト結果】
- 1対1チャットでJarvisが応答: OK / 未テスト
- グループチャットで指定エージェントが応答: OK / 未テスト / 該当なし

【次のアクション】
- （残っている作業があれば記載）
```
