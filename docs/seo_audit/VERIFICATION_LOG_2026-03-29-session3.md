# VERIFICATION_LOG — 2026-03-29 Session 3

> Phase 0 全VPS live確認の証跡。全コマンドと結果を記録。

---

## 1. Schema Type Check（codeinjection_head）

### コマンド
```python
import sqlite3, re, json
db = sqlite3.connect('/var/www/nowpattern/content/data/ghost.db')
cur = db.cursor()
for slug in ['predictions', 'en-predictions', 'about', 'en-about', 'taxonomy-ja', 'en-taxonomy']:
    cur.execute('SELECT codeinjection_head FROM posts WHERE slug=?', (slug,))
    ...
```

### 結果
| slug | スキーマ @type一覧 | 状態 |
|------|-----------------|------|
| `predictions` | ClaimReview×5(@graph), Dataset, FAQPage, ClaimReview×5(@graph) | ✅ 正常 |
| `en-predictions` | Dataset, FAQPage, CollectionPage | ✅ 正常 |
| `about` | WebPage (×2: MARKER+実body, WebSite nested) | ✅ 正常 |
| `en-about` | WebPage | ✅ 正常 |
| `taxonomy-ja` | WebPage | ✅ 正常 |
| `en-taxonomy` | WebPage | ✅ 正常 |

**注**: `predictions`の`@type=NO_TYPE`（@graph型）スキーマ=ClaimReview×5。prediction_page_builder.pyが生成する予測ClaimReviewスキーマ。正常。

### WebPage=2の理由（about等）
- Schema 1: `<!-- ISS-012: WebPage schema -->` マーカーコメント行（JSON-LDでない）
- Schema 2: 実際の `"@type": "WebPage"` JSON-LD
- WebSite=1: `isPartOf: {"@type": "WebSite"}` として WebPage内にネスト → 独立したWebSite宣言ではない。期待通り。

---

## 2. Builder Page HTML ID Check

### コマンド
```python
for slug in ['predictions', 'en-predictions']:
    cur.execute("SELECT html FROM posts WHERE slug=?", (slug,))
    ...
    for id_ in ['np-scoreboard', 'np-resolved', 'np-tracking-list']:
        print(id_, id_ in html)
```

### 結果
| page | np-scoreboard | np-resolved | np-tracking-list |
|------|--------------|-------------|-----------------|
| predictions (JA) | ✅ True | ✅ True | ✅ True |
| en-predictions (EN) | ✅ True | ✅ True | ✅ True |

---

## 3. ghost_url 4件確認（NP-0020/21/25/27）

### 結果
| prediction_id | ghost_url | 判定 |
|--------------|-----------|------|
| NP-2026-0020 | `https://nowpattern.com/fed-fomc-march-2026-rate-decision/` | ✅ JA URL |
| NP-2026-0021 | `https://nowpattern.com/btc-90k-march-31-2026/` | ✅ JA URL |
| NP-2026-0025 | `https://nowpattern.com/khamenei-assassination-iran-supreme-leader-succession-2026/` | ✅ JA URL |
| NP-2026-0027 | `https://nowpattern.com/btc-70k-march-31-2026/` | ✅ JA URL |

Session 2で修正済み。回帰なし。

---

## 4. ナビゲーション設定確認

```python
cur.execute("SELECT value FROM settings WHERE key='navigation'")
```

**結果**: `/taxonomy/` が使用中（`/taxonomy-ja/` は露出していない）
→ ISS-NAV-001 は **RESOLVED**（EN_JA_LINK_MAPPINGドキュメントの記述が stale だった）

---

## 5. DLQ確認

```python
dlq = json.load(open('/opt/shared/scripts/x_dlq.json'))
# isinstance(dlq, list) → True
# len(dlq) = 0
```

**結果**: DLQ = 0件 ✅

---

## 6. robots.txt AI Directives確認

```bash
curl -s https://nowpattern.com/robots.txt | grep -A5 "AI Training"
```

**結果**: `User-agent: GPTBot` + `User-agent: anthropic-ai` + `User-agent: Diffbot` 等、AI Training Crawlersセクション存在確認 ✅
→ ISS-015 **RESOLVED**（回帰なし）

---

## 7. Builder Log確認

```bash
tail -20 /opt/shared/logs/page_rebuild.log
tail -5 /opt/shared/logs/page_rebuild_ja_195414.log
tail -5 /opt/shared/logs/page_rebuild_en_195632.log
```

**結果**:
- JA予測ページ: `Ghost page /predictions/ updated OK` ✅
- EN予測ページ: `Ghost page /en-predictions/ updated OK` ✅

**NP-0007 warning について**:
- `page_rebuild.log`に`⚠️ NO ARTICLE: NP-2026-0007 — ghost_url missing`が現れるが…
- 現行の`prediction_page_builder.py`にはこのメッセージのコードが存在しない（バックアップ版のみ）
- NP-2026-0007の`ghost_url`はprediction_db.jsonに設定済み（`/eugaappleni2...`）
- Ghost DBに対応スラッグが`published`で存在確認
- → **古いbuilder版実行時の stale log entry**。現行ビルドでは発生しない。

---

## 8. Block-aware Regex確認

```bash
grep -n "block-aware\|_ld_blocks\|_update_dataset_in_head" \
  /opt/shared/scripts/prediction_page_builder.py | head -5
```

**結果**:
- Line 2995: `def _update_dataset_in_head(api_key, slug, stats, lang="ja", predictions=None):`
- Line 3010: `# Remove existing Dataset AND FAQPage blocks (block-aware finditer, re-inject both)`
- Line 3011: `_ld_blocks = list(_re.finditer(` — `</script>`境界で止まるblock-aware実装

→ greedy regex退行リスク: **なし** ✅

---

## 9. EN_JA_LINK_MAPPING ISS-NAV-001 stale確認

ドキュメント`docs/NOWPATTERN_EN_JA_LINK_MAPPING_2026-03-29.md`のISS-NAV-001は「課題 OPEN」として記載されているが、ライブ確認では既に修正済み（`/taxonomy/`使用中）。
→ ドキュメントが **stale**。実態は RESOLVED。

---

## 総括

| チェック項目 | 結果 |
|------------|------|
| predictions/en-predictions schema types | ✅ 全正常 |
| 予測ページHTML ID (np-scoreboard等) | ✅ 全存在 |
| ghost_url 4件 | ✅ JA URL確認 |
| nav /taxonomy/ | ✅ 正常 |
| DLQ | ✅ 0件 |
| robots.txt AI directives | ✅ 存在 |
| Builder最終実行 JA/EN | ✅ OK |
| block-aware regex | ✅ 実装済み |
| ClaimReview @graph スキーマ | ✅ builder正常動作（期待通り） |
| NP-0007 warning | ✅ stale log（現行builderでは発生しない） |

*作成: 2026-03-29 Session 3 | Engineer: Claude Code (local)*
