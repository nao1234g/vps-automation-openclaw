# NOWPATTERN HOMEPAGE LINK AUDIT — 2026-03-28
> 監査者: Homepage Link Audit Officer
> 方法: WebFetch (live page fetch) + curl HEAD (HTTP status) + SSH VPS直接確認
> 監査対象: nowpattern.com ホームページ + EN版 + 主要ハブページ全6ページ
> 実施日: 2026-03-28
> 原則: 実装なし。監査と記録のみ。

---

## 凡例

| 記号 | 意味 |
|------|------|
| 🔴 P1 | 重大バグ（即日対応） |
| 🟠 P2 | 高優先度（1週間以内） |
| 🟡 P3 | 中優先度（2週間以内） |
| 🟢 P4 | 低優先度（任意） |
| ✅ | 正常（200 OK） |
| ⚠️ | 要注意（301 redirect 不必要）|
| ❌ | バグ（404 / 誤リダイレクト） |

---

## ホームページ（JA） — https://nowpattern.com/

### ナビゲーションリンク

| リンクテキスト | href | HTTP | 判定 | 備考 |
|--------------|------|------|------|------|
| Nowpattern（ロゴ） | https://nowpattern.com/ | 200 | ✅ | ホームへ正常 |
| 予測トラッカー | https://nowpattern.com/predictions/ | 200 | ✅ | 正常 |
| 力学で探す | https://nowpattern.com/taxonomy-ja/ | 301→/taxonomy/ | ⚠️ | **[P2] 不要301。/taxonomy/に直すべき** |
| About | https://nowpattern.com/about/ | 200 | ✅ | 正常 |
| EN | https://nowpattern.com/en/ | 200 | ✅ | 正常 |
| Sign in | #/portal/signin | — | ✅ | Ghost Portal（正常） |
| Subscribe | #/portal/signup | — | ✅ | Ghost Portal（正常） |

### 言語切り替えバー

| テキスト | href | HTTP | 判定 |
|---------|------|------|------|
| JA | / | 200 | ✅ 現在地（正常） |
| EN | /en/ | 200 | ✅ 正常 |

### 記事リンク（Latest Articles — ホームページ掲載10件）

| # | 記事タイトル（冒頭40文字） | HTTP | 判定 |
|---|------------------------|------|------|
| 1 | ビットコイン1500万円突破予測 — 機関投資家… | 200 | ✅ |
| 2 | デンマーク総選挙の衝撃 — グリーンランド防衛が招… | 200 | ✅ |
| 3 | ガザ「平和評議会」国連初報告 — 正統性なき統治… | 200 | ✅ |
| 4 | 南シナ海の米中軍事対峙 — 対立の螺旋が偶発衝突… | **404** | ❌ **[P1] 存在しないslug** |
| 5 | 北朝鮮ミサイル再開 — 対立の螺旋が迫る日本防衛… | 200 | ✅ |
| 6 | 日本DeFi規制法案 — 「規制の捕獲」が暗号資産… | 200 | ✅ |
| 7 | ビットコイン1000万円突破へ — 機関マネー流入… | 200 | ✅ |
| 8 | FRB利下げ凍結の深層 — 中東リスクとインフレ… | 200 | ✅ |
| 9 | EU・豪州FTA妥結 — トランプ関税が加速させた… | 200 | ✅ |
| 10 | 台湾海峡の軍事緊張 — 対立の螺旋が日米同盟… | 200 | ✅ |

**404 URL**: `/nan-sinahai-nomi-zhong-jun-shi-dui-zhi-dui-li-noluo-xuan-gaou-fa-chong-tu-risukuwolin-jie-dian-heya-sishi-ang-gerugou-zao/`
**Ghost DB確認**: このslugはDBに存在しない。同トピックの別slugは存在する（南シナ海記事4件）。

### ページネーション

| テキスト | href | HTTP | 判定 |
|---------|------|------|------|
| See all | /page/2/ | 200 | ✅ |

### CTAボタン

| テキスト | href | セクション | 判定 |
|---------|------|-----------|------|
| Subscribe（JA） | #/portal/signup | Hero | ✅ |
| Subscribe（EN） | #/portal/signup | Hero（EN表示） | ✅ |
| 予測トラッカーを見る | /predictions/ | Disclaimer | ✅ |
| View Prediction Track Record | /en/predictions/ | Disclaimer（EN） | ✅ |
| Polymarket で見る → | https://polymarket.com/ | Live Panel | ✅ |

### フッターリンク

| テキスト | href | HTTP | 判定 | 備考 |
|---------|------|------|------|------|
| タクソノミーガイド | https://nowpattern.com/taxonomy-guide-ja/ | 301→/taxonomy/ | ❌ **[P1] 誤リダイレクト** |
| Ghost | https://ghost.org/ | 200 | ✅ |

---

## ホームページ（EN） — https://nowpattern.com/en/

### ナビゲーションリンク

| リンクテキスト | href | HTTP | 判定 | 備考 |
|--------------|------|------|------|------|
| Nowpattern（ロゴ） | https://nowpattern.com/ | 200 | ✅ | JA版ホームへ（EN版へのロゴリンクが欲しい） |
| 予測トラッカー | https://nowpattern.com/predictions/ | 200 | ⚠️ | **[P2] EN版なのにJAページへ** |
| 力学で探す | https://nowpattern.com/taxonomy-ja/ | 301→/taxonomy/ | ⚠️ | **[P2] EN版でJA表記 + 不要301** |
| About | https://nowpattern.com/about/ | 200 | ⚠️ | **[P3] EN版でJA aboutへ** |
| EN（現在地） | https://nowpattern.com/en/ | 200 | ✅ | 正常 |

**注**: ENページでJavaScriptが動作すると一部リンクが変換されるが、HTML baseline はすべてJA向け。JS失敗時に完全にJA版にリダイレクトされるリスク。

### 記事リンク（EN Latest Articles — 10件）

| # | 記事タイトル | HTTP | 判定 |
|---|------------|------|------|
| 1 | The Structure Behind Bitcoin Surpassing 10 Million | 200 | ✅ |
| 2 | Bitcoin Predicted to Surpass ¥15 Million | 200 | ✅ |
| 3 | The Shock of the Danish General Election | 200 | ✅ |
| 4 | Gaza "Peace Council" - First UN Report | 200 | ✅ |
| 5 | US-China Military Standoff in the South China | 200 | ✅ |
| 6 | North Korea Resumes Missile Launches | 200 | ✅ |
| 7 | Bitcoin's ¥15M Breach | 200 | ✅ |
| 8 | South China Sea Standoff | 200 | ✅ |
| 9 | Japan's DeFi Regulation Bill | 200 | ✅ |
| 10 | Russia's Tactical Nuclear Gambit | 200 | ✅ |

**注**: Article #1のURL `/en/en-bitutokoin1000mo-...` は301→`/en/the-structure-behind-bitcoin-surpassing-10-million/` にリダイレクト。URL生成バグあり（後述）。

---

## /predictions/ — 予測トラッカー（JA）

### ナビゲーション・構造

| 要素 | 状態 | 備考 |
|------|------|------|
| nav links | ✅ 全200 | /taxonomy-ja/は⚠️301 |
| id="np-scoreboard" | ✅ **存在する** | 213件、11的中、65%的中率 |
| id="np-resolved" | ❌ **存在しない** | np-tracking-listのみ。[P1] アンカーリンク破損 |
| 言語切替 → EN | /en/predictions/ | 200 ✅ |
| 記事リンクサンプル | 10件中10件200 | ✅ |

### 記事リンクサンプル（/predictions/ から）

| URL | HTTP |
|-----|------|
| /gong-kai-qi-ye-btcbao-you-200mo-... | 200 ✅ |
| /aiezientoga-mai-iwu-woshi-... | 200 ✅ |
| /eu-vs-mi-guo-tetukuzhan-... | 200 ✅ |
| /du-wa-nodu-tokuremurin-... | 200 ✅ |
| /ziyunebuno6shi-jian-... | 200 ✅ |
| /toranpujia-zu-noan-hao-... | 200 ✅ |
| /zui-gao-cai-guan-shui-pan-jue-... | 200 ✅ |
| /toranpugatong-shang-fa-... | 200 ✅ |
| /nasa-mars-ai-autonomous-driving/ | 200 ✅ |
| /vuitarituku-ainobao-zou-... | 200 ✅ |

---

## /en/predictions/ — Prediction Tracker（EN）

### ナビゲーション・構造

| 要素 | 状態 | 備考 |
|------|------|------|
| nav baseline HTML | ⚠️ JA text | JS overrideあり |
| JS nav override | `/en-predictions/`を使用 | **[P2] 301発生 → /en/predictions/にすべき** |
| 言語切替 → JA | /predictions/ | 200 ✅ |
| EN記事リンク | 4件 301リダイレクト | **[P3] /en/en-プレフィックス** |

### EN記事リンクサンプル（/en/predictions/ から）

| URL | HTTP | リダイレクト先 |
|-----|------|-------------|
| /en/en-btc-70k-march-31-2026/ | 301 | /en/will-bitcoin-exceed-70000-by/ ✅ |
| /en/en-btc-90k-march-31-2026/ | 301 | /en/will-btc-recover-90000-by-the/ ✅ |
| /en/en-fed-fomc-march-2026-rate-decision/ | 301 | /en/will-the-fed-cut-rates-at-the-march-202/ ✅ |
| /en/en-khamenei-assassination-... | 301 | /en/after-khameneis-assassination-... ✅ |

---

## /about/ と /en/about/

| 要素 | JA /about/ | EN /en/about/ |
|------|-----------|--------------|
| HTTP status | 200 ✅ | 200 ✅ |
| 言語切替 | /en/about/ → 200 ✅ | /about/ → 200 ✅ |
| フッター | /taxonomy-guide-ja/ ❌ | /en-predictions/ ⚠️(301) |
| X リンク | https://x.com/nowpattern ✅ | https://x.com/nowpattern ✅ |
| Prediction CTA | /predictions/ ✅ | /en-predictions/ ⚠️(301) |

---

## /taxonomy/ と /en/taxonomy/

| 要素 | JA /taxonomy/ | EN /en/taxonomy/ |
|------|--------------|-----------------|
| HTTP status | 200 ✅（/taxonomy-ja/ 301から） | 200 ✅ |
| 言語切替（HTMLソース） | taxonomy-en/ → 301→/en/taxonomy/ ⚠️ | /taxonomy-ja/ → 301→/taxonomy/ ⚠️ |
| タグリンク（genre/event） | 200 ✅ | 200 ✅ |

---

## バグ集計（ページ別）

| ページ | 404 | 誤リダイレクト | その他バグ |
|--------|-----|-------------|----------|
| / (JA home) | 1件 | 1件 | — |
| /en/ (EN home) | 0件 | nav全てJA | JS依存 |
| /predictions/ | 0件 | — | id="np-resolved"なし |
| /en/predictions/ | 0件 | JS: /en-predictions/ | EN article /en/en- slugs |
| /about/ | 0件 | フッター誤redirect | — |
| /en/about/ | 0件 | CTA→/en-predictions/ | — |
| /taxonomy/ | 0件 | lang switch→taxonomy-en/ | — |
| /en/taxonomy/ | 0件 | lang switch→taxonomy-ja/ | — |

**合計: 1件404 / 5件以上の誤リダイレクト / 1件id欠落**

---

## 注記

- Ghost CMS v5.130.6、Caddy reverse proxy使用
- Caddy redirects.txt にて /taxonomy-guide-ja/ → /taxonomy/ が意図的に設定されているが、これは誤り
- JSによる言語切替はClient-side動作のため、クローラー・スクリーンリーダーへの影響あり
- 実装はしない。修正提案は NOWPATTERN_LINK_FIX_PROPOSALS_2026-03-28.md 参照

*作成: 2026-03-28 | 監査方法: WebFetch + curl HEAD + SSH DB確認*
