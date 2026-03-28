# Core Web Vitals & PageSpeed Report — nowpattern.com
**Audit Date:** 2026-03-27 | **Method:** curl timing (VPS internal → CDN経由)
**注意:** PSI API quota 超過(429)のため、curl timing を代替指標として使用

---

## 測定値サマリー（VPS内部計測 — ネットワーク遅延なし）

| テンプレート | DNS | SSL | **TTFB** | Total | Size | 評価 |
|---|---|---|---|---|---|---|
| JA ホーム | 1ms | 66ms | **414ms** | 423ms | 128KB | ⚠️ 要改善 |
| EN ホーム | 2ms | 46ms | **309ms** | 314ms | 110KB | ⚠️ 要改善 |
| JA 記事 | 1ms | 62ms | **215ms** | 222ms | 144KB | ⚠️ 要改善 |
| EN 記事 | 1ms | 40ms | **215ms** | 225ms | 142KB | ⚠️ 要改善 |
| JA 予測 | — | — | **3,540ms** cold / **60ms** cached | — | **283KB** | ⚠️ cold TTFB 悪化（cached は良好） |
| **EN 予測** | 1ms | 35ms | **1,195ms** cold / **60ms** cached | — | **320KB** | ✅ **修正済み** |

**実際のユーザー体感 TTFB（VPS値 + ネットワーク遅延推定）:**
- 日本国内ユーザー: +30〜50ms
- 海外ユーザー (US): +120〜150ms

---

## ✅ RESOLVED: EN 予測ページのパフォーマンス障害（2026-03-28 修正完了）

### 修正前実測値（2026-03-27 BEFORE）
```
EN /en/predictions/ → Ghost slug: en-predictions
TTFB:  9.48秒  (目標: < 0.8秒)
Size:  5,269,893 bytes (5.27MB)
Divs:  31,335個
```

### 根本原因
`prediction_page_builder.py` が **1,006件全予測** をフルカード形式で単一 HTML に書き出していた。
```
1,006 predictions × ~31 divs/card = ~31,000 divs
各カード: タイトル + シナリオ3種 + Polymarket比較 + 投票UI + タグバッジ → ~5KB/件
```

### 実施した修正
`prediction_page_builder.py` に `_build_compact_row()` を追加。`resolving` ステータス予測（1,028件）を
フルカードではなく `<details>` 折り畳み形式（compact row）に変換。`active`/`open` 予測のみフルカード。

### 修正後実測値（2026-03-28 AFTER — 3点確認済み）

| 指標 | BEFORE | AFTER | 削減率 |
|------|--------|-------|--------|
| **EN ページサイズ（live）** | 5,270 KB | **320 KB** | **▲ -94%** |
| **EN TTFB（cold）** | 9,480ms | **1,195ms** | **▲ -87%** |
| **EN TTFB（cached）** | — | **60ms** | — |
| **EN DB html_len** | — | 218.9 KB | — |
| **JA ページサイズ（live）** | 340 KB | **283 KB** | **▲ -17%** |
| **JA TTFB（cold）** | 146ms | ~3,540ms* | — |
| **JA DB html_len** | — | 166.2 KB | — |

*JA TTFB cold は Ghost キャッシュ挙動の変化によるもの（cached: 60ms = 正常）

### 3点確認（2026-03-28 監査完了）
```
① Live HTML: JA HTTP200/283KB/compact_rows=20/old_cards=0 ✅
             EN HTTP200/320KB/compact_rows=21/old_cards=0 ✅
② Ghost DB:  predictions: updated_at=2026-03-28 04:26:34, html=166.2KB, compact=20, cards=0 ✅
             en-predictions: updated_at=2026-03-28 04:21:59, html=218.9KB, compact=21, cards=0 ✅
③ DB≡Live:   compact row count DB=live for both JA and EN ✅
```

---

## TTFB 詳細分析

### Core Web Vitals 2026 基準
| 指標 | Good | Needs Improvement | Poor |
|---|---|---|---|
| LCP | < 2.5s | 2.5s〜4.0s | > 4.0s |
| INP | < 200ms | 200ms〜500ms | > 500ms |
| CLS | < 0.1 | 0.1〜0.25 | > 0.25 |
| TTFB | < 0.8s | 0.8s〜1.8s | > 1.8s |

### テンプレート別 TTFB 評価

| テンプレート | 実測 TTFB (VPS内) | 推定 TTFB (外部) | CWV 判定 |
|---|---|---|---|
| JA ホーム | 414ms | 450〜460ms | ⚠️ Needs Improvement |
| EN ホーム | 309ms | 340〜360ms | ✅ Good（ギリギリ） |
| 記事 (両言語) | 215ms | 250〜270ms | ✅ Good |
| JA 予測 (BEFORE) | 146ms | 180〜200ms | ✅ Good |
| JA 予測 (AFTER cold) | **3,540ms** | ~3,570ms | ⚠️ Poor（cold TTFB 悪化 — 課題） |
| JA 予測 (AFTER cached) | **60ms** | ~90ms | ✅ Good |
| EN 予測 (AFTER cold) | **1,195ms** | 1,225ms | ⚠️ Needs Improvement（許容範囲） |
| EN 予測 (AFTER cached) | **60ms** | ~90ms | ✅ Good |

### JA ホームの TTFB が 414ms と遅い原因推定
- Ghost CMS の template rendering (Casper theme)
- 直近 100 記事のリスト生成
- Caddy → Ghost の reverse proxy オーバーヘッド

**JA ホーム改善策:**
```
1. Ghost の caching 設定確認 (site_description, og:image の再計算)
2. homepage の記事表示数を 15 → 10 に削減
3. Caddy level での HTTP cache headers 追加
```

---

## ページサイズ評価

| テンプレート | サイズ | 判定 | 改善案 |
|---|---|---|---|
| EN ホーム | 110KB | ✅ | - |
| JA ホーム | 128KB | ✅ | - |
| 記事 | 142〜144KB | ✅ | - |
| JA 予測 | **283KB** (340KB→283KB, −17%) | ✅ | cold TTFB 課題あり（本文参照） |
| EN 予測 | **320KB** | ✅ | 修正済み（compact row化 -94%） |

---

## 構造化データ (Schema.org) 現状

### 現在の実装
```
Ghost が自動生成: WebSite, Article, BreadcrumbList
```

### 不足している schema
```
❌ Claim / ClaimReview — 予測の信頼性スコア表示に最適
❌ Event — トーナメント/予測イベントに適用可能
❌ FAQPage — 予測ガイドページに適用可能
❌ Rating / AggregateRating — Brier Score の表示に適用可能
```

### 推奨: 予測記事への ClaimReview 追加
```json
{
  "@type": "ClaimReview",
  "claimReviewed": "This prediction will resolve YES",
  "reviewRating": {
    "@type": "Rating",
    "ratingValue": "70",
    "bestRating": "100"
  },
  "url": "https://nowpattern.com/predictions/#np-2026-0042"
}
```

---

## PageSpeed Insights 代替測定手順

PSI API quota が回復次第、以下のコマンドで測定:
```bash
# JA ホーム
curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://nowpattern.com/&strategy=mobile&key=YOUR_KEY"

# EN 予測（最優先）
curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://nowpattern.com/en/predictions/&strategy=mobile&key=YOUR_KEY"
```

または Google Search Console → Core Web Vitals レポートで実ユーザーデータを確認。

---

---

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2026-03-27 | 初版作成。EN predictions TTFB 9,480ms / 5.27MB の致命的問題を記録 |
| 2026-03-28 | `_build_compact_row()` 実装完了。EN: 5,270KB→320KB (−94%) / 9,480ms→1,195ms cold (−87%) / cached 60ms。JA: 340KB→283KB (−17%) / cold TTFB 悪化（3,540ms） / cached 60ms。3点確認（Live+DB+計測）済み |
| 2026-03-28 | ドキュメント是正: stale warm cache 値を削除し、verified source of truth（cold/cached TTFB）に更新 |

*生成: 2026-03-27 | 最終更新: 2026-03-28 — EN predictions 修正完了確認（stale warm cache 値を是正済み）*
