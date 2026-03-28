# NOWPATTERN 72時間実装プラン — 2026-03-28
> source: TOP10_ACTIONS + GAP_ANALYSIS
> 対象: 2026-03-28 〜 2026-03-31（72時間）
> 原則: 可逆・即効・最大ROI

---

## 前提条件

- **VPS SSH接続**: root@163.44.124.123
- **全作業は可逆** — バックアップなしの変更は禁止
- **実施後は必ず検証** — curl/サイト確認まで完了して「完了」
- **Naoto不在時はNight Mode** — 自律実行可能なタスクのみ実施

---

## H+0〜H+3（今日中、約3時間）— 設定ミス修正

### H+0:00 — llms.txt URL修正（5分）
**担当:** NEO-ONE または ローカルClaude Code

```bash
# Ghost Admin APIで更新
curl -X PATCH https://nowpattern.com/ghost/api/admin/pages/{en-predictions-page-id}/ \
  -H "Authorization: Ghost {ADMIN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"pages":[{"custom_excerpt":"..."}]}'

# または Ghost Admin UI:
# https://nowpattern.com/ghost/#/editor/page/{id}
# llms.txt ページを開き、en-predictions/ → en/predictions/ に修正
```

**検証:**
```bash
curl https://nowpattern.com/llms.txt | grep "en/predictions"
# "en/predictions/" が含まれていれば OK
```

---

### H+0:10 — Caddy gzip有効化（10分）
**担当:** ローカルClaude Code または NEO-ONE

```bash
ssh root@163.44.124.123 "
  cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak-$(date +%Y%m%d)
  # nowpattern.comブロック内の先頭に 'encode zstd gzip' を追加
"
```

**Caddyfile変更後の構造:**
```
nowpattern.com {
    encode zstd gzip          # ← この1行を追加
    reverse_proxy ...
    ...
}
```

**Caddy reload:**
```bash
caddy reload --config /etc/caddy/Caddyfile
```

**検証:**
```bash
curl -I -H "Accept-Encoding: gzip" https://nowpattern.com/predictions/ | grep -i "content-encoding"
# "content-encoding: gzip" が返れば OK
```

---

### H+0:25 — llms-full.txt 404修正（15分）
**担当:** NEO-ONE または ローカルClaude Code

```bash
ssh root@163.44.124.123 "
# まずllms-full.txtの実際の場所を確認
find /var/www/nowpattern -name 'llms-full.txt' 2>/dev/null
ls /var/www/nowpattern/content/files/ | grep llms
"
```

**場所が判明したらCaddyfileに追加:**
```
handle /llms-full.txt {
    root * /var/www/nowpattern/content/files
    file_server
}
```
※パスはllms-full.txtの実際の場所に合わせる

**検証:**
```bash
curl -o /dev/null -w "%{http_code}" https://nowpattern.com/llms-full.txt
# 200 が返れば OK
```

---

### H+0:45 — X PORTFOLIO REPLY→0%（30分）
**担当:** NEO-ONE（VPS作業）

```bash
ssh root@163.44.124.123 "
cp /opt/shared/scripts/x_swarm_dispatcher.py /opt/shared/scripts/x_swarm_dispatcher.py.bak-$(date +%Y%m%d-%H%M)
"
```

**変更内容（x_swarm_dispatcher.py）:**
```python
# BEFORE
PORTFOLIO = {
    "LINK":     0.20,
    "NATIVE":   0.30,
    "RED_TEAM": 0.20,
    "REPLY":    0.30,
}

# AFTER
PORTFOLIO = {
    "LINK":     0.35,  # +15%
    "NATIVE":   0.40,  # +10%
    "RED_TEAM": 0.25,  # +5%
    "REPLY":    0.00,  # DISABLED: 403 "not part of conversation" 全件発生
}
```

**検証（次のcronサイクル後）:**
```bash
# 5分後に確認
tail -20 /opt/shared/logs/x_swarm_dispatcher.log
# "Successfully posted: LINK" や "NATIVE" が見えれば OK
```

---

### H+1:15 — np-scoreboard / np-resolved ID追加（30分）
**担当:** NEO-ONE（VPS作業）

```bash
ssh root@163.44.124.123 "
cp /opt/shared/scripts/prediction_page_builder.py /opt/shared/scripts/prediction_page_builder.py.bak-$(date +%Y%m%d)
"
```

**変更箇所の特定:**
```bash
grep -n 'scoreboard\|resolved' /opt/shared/scripts/prediction_page_builder.py | head -20
```

**変更内容:**
- スコアボードのdivに `id="np-scoreboard"` を追加
- 解決済みセクションのdivに `id="np-resolved"` を追加

**ページ再生成:**
```bash
cd /opt/shared/scripts && python3 prediction_page_builder.py
```

**検証:**
```bash
curl -s https://nowpattern.com/predictions/ | grep -c 'id="np-scoreboard"'
# 1 が返れば OK
curl -s https://nowpattern.com/predictions/ | grep -c 'id="np-resolved"'
# 1 が返れば OK
```

---

### H+1:45 — Ghost portal_plans修正（1時間）
**担当:** Naoto（Stripe接続が必要なため）

**ステップ1: Stripe接続（Naotoが実施）**
```
1. https://stripe.com でアカウントログイン（または新規作成）
2. Ghost Admin: https://nowpattern.com/ghost/#/settings/members/
3. "Connect with Stripe" ボタンをクリック
4. Stripe OAuthフローを完了
```

**ステップ2: portal_plans更新（接続後に実行）**
```bash
ssh root@163.44.124.123 "
sqlite3 /var/www/nowpattern/content/data/ghost.db \
  \"UPDATE settings SET value='[\\\"free\\\",\\\"monthly\\\",\\\"yearly\\\"]' WHERE key='portal_plans';\"
"
```

**ステップ3: Ghost再起動**
```bash
ssh root@163.44.124.123 "systemctl restart ghost-nowpattern"
```

**検証:**
```bash
# Ghostポータルに有料プランが表示されるか確認
curl -s https://nowpattern.com/ | grep -i "portal"
# または Ghost Admin > Members > Tiers で確認
```

---

## H+3〜H+24（今日〜明日）— AI・SEOスキーマ実装

### Dataset schema追加（2時間）
**担当:** NEO-ONE

1. `/opt/shared/scripts/prediction_page_builder.py` を確認
2. `_build_page_html()` の `<head>` セクションに以下を追加:

```python
dataset_schema = json.dumps({
    "@context": "https://schema.org",
    "@type": "Dataset",
    "name": "Nowpattern Prediction Tracker",
    "description": f"Structured predictions with Brier Score tracking. {total_count} predictions.",
    "url": "https://nowpattern.com/predictions/",
    "creator": {
        "@type": "Organization",
        "name": "Nowpattern",
        "url": "https://nowpattern.com"
    },
    "dateModified": datetime.now().strftime("%Y-%m-%d"),
    "variableMeasured": "Brier Score prediction accuracy"
})
head_html += f'<script type="application/ld+json">{dataset_schema}</script>'
```

**検証:**
```bash
curl -s https://nowpattern.com/predictions/ | python3 -c "
import sys, json
html = sys.stdin.read()
# JSON-LDを抽出して確認
import re
matches = re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL)
for m in matches:
    data = json.loads(m)
    print(data.get('@type'))
"
# 'Dataset' が出力されれば OK
```

---

### FAQPage schema追加（2時間）
**担当:** NEO-ONE または Naoto（Ghost Admin操作）

**Ghost Admin > Code Injection > Site Header に追加:**
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Nowpatternの予測精度はどのくらいですか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "現在のBrier Scoreは平均0.1828（FAIR水準）。52件の予測が解決済みで、的中率75.7%。Brier Score 0.20以下を目標としています。"
      }
    },
    {
      "@type": "Question",
      "name": "予測に参加するにはどうすればいいですか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "/predictions/ ページで各予測に対して「楽観/基本/悲観」シナリオと確率を投票できます。登録不要で参加可能です。"
      }
    },
    {
      "@type": "Question",
      "name": "予測はどのように検証されますか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "prediction_auto_verifier.pyが定期的に各予測の解決状況を確認し、Brier Scoreを自動計算します。予測は改ざん防止のためOTSタイムスタンプで記録されます。"
      }
    }
  ]
}
</script>
```

---

## H+24〜H+72（2〜3日目）— DLQ変換とPolymarket改善

### DLQ 79件 NATIVE変換（2時間）
**担当:** NEO-ONE（P-001完了後）

```python
# /opt/shared/scripts/x_dlq_to_native.py（新規作成）
import json
from datetime import datetime

with open('/opt/shared/scripts/x_dlq.json', 'r') as f:
    dlq = json.load(f)

# REPLY形式をNATIVE形式に変換
converted = []
for item in dlq:
    if item.get('format') == 'REPLY':
        item['format'] = 'NATIVE'
        item['converted_from'] = 'REPLY'
        item['converted_at'] = datetime.now().isoformat()
        # リプライ先URLを削除
        item.pop('reply_to_tweet_url', None)
        converted.append(item)

# x_queue.jsonに追加
with open('/opt/shared/scripts/x_queue.json', 'r') as f:
    queue = json.load(f)

queue.extend(converted)

with open('/opt/shared/scripts/x_queue.json', 'w') as f:
    json.dump(queue, f, ensure_ascii=False, indent=2)

print(f"変換完了: {len(converted)}件をNATIVEキューに追加")
```

---

## 72時間完了チェックリスト

```
[ ] llms.txt EN URL修正            → curl確認でen/predictions/が含まれる
[ ] Caddy gzip有効化               → content-encoding: gzip が返る
[ ] llms-full.txt 404修正          → HTTP 200が返る
[ ] X PORTFOLIO REPLY→0%           → x_swarm.log でNATIVE/LINK投稿が確認できる
[ ] np-scoreboard ID追加           → predictions/ でid="np-scoreboard"が1件確認
[ ] Ghost portal_plans修正         → Ghost Portal UIに月額プランが表示される
[ ] Dataset schema追加             → Rich Results Test でDataset validated
[ ] FAQPage schema追加             → Rich Results Test でFAQPage validated
[ ] DLQ 79件NATIVE変換             → x_dlq.json が空になる
```

---

## リスク管理

| リスク | 確率 | 対処 |
|--------|------|------|
| Caddy reload後にサイトダウン | 低 | bak取得済み。`caddy reload`は自動ロールバックあり |
| Ghost SQLite更新でDB破損 | 極低 | 変更前に `cp ghost.db ghost.db.bak` |
| X投稿が再度403になる | 低 | LINK/NATIVEは外部ツイートへのリプライなので403リスクなし |
| Stripe接続でGhost再起動必要 | 中 | 低トラフィック時間帯（深夜JST）に実施 |

---

*最終更新: 2026-03-28 | 実装開始可能: 即時*
