# VERIFICATION_LOG — 2026-03-29 Session 5

> Phase 0 包括ライブチェックの証跡。セッション5開始時の全項目確認。
> 前セッション（session4）からの回帰がないかを確認し、13仮説を分類する。

---

## 目的

Session 5 は「comprehensive re-audit pass」として実施。
Session 4 の TERMINAL STATE からの再起動後、全仮説をライブVPSで再確認し、
**OPEN_CURRENT = 0 → STATE D (TERMINAL_WAIT)** を証明する。

---

## 1. DLQ 確認

```
コマンド: python3 -c "import json; dlq=json.load(open('/opt/shared/scripts/x_dlq.json')); print('DLQ:', len(dlq) if isinstance(dlq,list) else dlq)"
結果: DLQ: 0
```

**判定**: ✅ 回帰なし

---

## 2. ghost_url 4件確認

```
コマンド: python3 -c "import json; db=json.load(open('/opt/shared/scripts/prediction_db.json')); bad=[p for p in db['predictions'] if 'ghost_url' in p and p['ghost_url'] and '/en/' in str(p.get('ghost_url',''))]; print('JA-pointing EN ghost_url:', len(bad)); [print(p['prediction_id'], p['ghost_url'][:60]) for p in bad[:5]]"
結果: JA-pointing EN ghost_url: 0
     (NP-2026-0020/21/25/27 は全て JA URL → session2修正が維持されている)
```

**判定**: ✅ 回帰なし

---

## 3. Ghost nav 設定

```
コマンド: sqlite3 /var/www/nowpattern/content/data/ghost.db "SELECT value FROM settings WHERE key='navigation';"
結果: /taxonomy/ (ISS-NAV-001 session1修正が維持)
```

**判定**: ✅ 回帰なし

---

## 4. prediction_db.json 状態

```
コマンド: python3 -c "import json; db=json.load(open('/opt/shared/scripts/prediction_db.json')); from collections import Counter; cnt=Counter(p.get('status') for p in db['predictions']); print(cnt); print('total:', len(db['predictions']))"
結果:
  total: 1115
  AWAITING_EVIDENCE: 1023
  OPEN: 35
  RESOLVED: 52
  EXPIRED_UNRESOLVED: 5
```

**判定**: ✅ RESOLVED=52 (session3以降変化なし、正常)

---

## 5. ライブスキーマ確認（全7ページ）

```
コマンド: SSH経由でcurl + Python JSON-LD解析（7ページ並列チェック）
```

| ページ | schemas | scoreboard ID | resolved ID | hreflang count |
|--------|---------|--------------|-------------|----------------|
| homepage | WebSite, NewsMediaOrganization | - | - | 0 (static) |
| /predictions/ (JA) | NewsMediaOrganization, Dataset, FAQPage | ✅ | ✅ | 5 (JS) |
| /en/predictions/ (EN) | Article, NewsMediaOrganization, CollectionPage, Dataset, FAQPage | ✅ | ✅ | 5 (JS) |
| /about/ (JA) | Article, NewsMediaOrganization, WebPage | - | - | 5 (JS) |
| /en/about/ (EN) | Article, NewsMediaOrganization, WebPage | - | - | 5 (JS) |
| /taxonomy/ (JA) | Article, NewsMediaOrganization, WebPage | - | - | 5 (JS) |
| /en/taxonomy/ (EN) | Article, NewsMediaOrganization, WebPage | - | - | 5 (JS) |

**注**: hreflang は全ページJS注入（ISS-HREFLANG-001 backlog設計懸念）。static `<link>` タグなし。

**判定**: ✅ 全スキーマ正常。ISS-003/012 修正が維持されている。

---

## 6. robots.txt AI directives

```
curl https://nowpattern.com/robots.txt
確認項目: GPTBot, anthropic-ai, Diffbot, Bytespider, CCBot, omgili → 全て Disallow: /
```

**判定**: ✅ ISS-015 CONFIRMED LIVE

---

## 7. llms.txt / llms-full.txt

| 項目 | 確認コマンド | 結果 |
|------|------------|------|
| llms.txt HTTP status | curl -I https://nowpattern.com/llms.txt | 200 OK ✅ |
| llms-full.txt HTTP status | curl -I https://nowpattern.com/llms-full.txt | 200 OK ✅ |
| llms-full.txt gzip | content-encoding header | gzip ✅ |

**判定**: ✅ REQ-001/004/005 CONFIRMED LIVE

---

## 8. Homepage hreflang 詳細確認

```
curl https://nowpattern.com/ → grep hreflang
```

**結果**:
- Static `<link rel="alternate" hreflang="...">` タグ: **0件**
- JS コード内 hreflang 記述: 7行（`link.hreflang = lang`, `el.hreflang = hl` 等）
- ISS-HREFLANG-001 の設計確認: hreflang は JavaScript injection で実装

**判定**: ISS-010 は「JSによるhreflangが機能している」で RESOLVED。
hreflang の静的 vs 動的は ISS-HREFLANG-001 として backlog に記録済み。回帰なし。

---

## 9. Prediction Page Builder 最終確認

```
crontab: 0 22 * * * prediction_page_builder.py --force --update
         30 22 * * * prediction_page_builder.py --force --lang en --update
最終実行: 2026-03-28 22:01 UTC (= JST 07:01 Mar 29)
ログ: Ghost page /en-predictions/ updated OK
E2E: [OK] E2Eテスト全PASS — UIが正常に動作しています
SyntaxError: 0件
```

**判定**: ✅ Builder 正常稼働。Session1修正（_build_claimreview_ld literal newline）が維持。

---

## Phase 1: 13仮説 分類結果

| # | 仮説内容 | 分類 | 証拠 |
|---|---------|------|------|
| 1 | FAQPage/Dataset regression | STALE_HYPOTHESIS_CLOSED | Section 5 ライブ確認 |
| 2 | block-aware regex EN共存 | STALE_HYPOTHESIS_CLOSED | EN_pred = [CollectionPage+Dataset+FAQPage] |
| 3 | REQ-011 PARSE_ERROR active | STALE_HYPOTHESIS_CLOSED | CURRENT_TRUTH docs + 0件grep確認済み |
| 4 | broken links 10件 block | STALE_HYPOTHESIS_CLOSED | 全URL HTTP 200、--force 意図的設計 |
| 5 | Ghost nav /taxonomy-ja/ | STALE_HYPOTHESIS_CLOSED | Section 3 live DB確認 |
| 6 | EN記事hreflang JA欠如 | STALE_HYPOTHESIS_CLOSED | session3 Trump-Orbán修正済み |
| 7 | REQ-002 Stripe | BLOCKED | 外部依存、変化なし |
| 8 | ISS-003 CollectionPage | STALE_HYPOTHESIS_CLOSED | EN_pred schemas live確認 |
| 9 | ISS-012 WebPage 4ページ | STALE_HYPOTHESIS_CLOSED | 全4ページ WebPage live確認 |
| 10 | WebSite duplicate | STALE_HYPOTHESIS_CLOSED | homepage WebSite=1のみ |
| 11 | robots.txt AI directives | STALE_HYPOTHESIS_CLOSED | Section 6 live確認 |
| 12 | ghost_url 4件 regression | STALE_HYPOTHESIS_CLOSED | Section 2 regression=0 |
| 13 | session-end.sh/py機能 | OUT_OF_SCOPE | SEOタスクスコープ外 |

**OPEN_CURRENT = 0件 → Phase 2 実装スキップ → STATE D (TERMINAL_WAIT)**

---

## Phase 2: 実装

**実装なし** — OPEN_CURRENT = 0のため Phase 2 は不要。

---

## Phase 3: Builder Durability確認

Section 9 の確認により:
- E2E PASS ✅
- SyntaxError 0件 ✅
- EN_pred = [CollectionPage + Dataset + FAQPage] 共存 ✅
- block-aware regex 正常動作 ✅

**Builder durability confirmed.**

---

## 最終判定

**STATE D: TERMINAL_WAIT**

session1〜session5 を通じて nowpattern.com の全20 SEO issues を確認:
- **RESOLVED: 19件**（session1〜4で実装・確認）
- **BLOCKED: 1件**（ISS-008 Stripe — 外部依存）
- **Session5: 実装なし（全仮説がstale/blocked/out-of-scope）**

---

*作成: 2026-03-29 session5 | Engineer: Claude Code (local)*
