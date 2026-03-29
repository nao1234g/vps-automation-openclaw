# NOWPATTERN SITEWIDE URL AUDIT — 2026-03-28
> 監査者: URL Quality Auditor
> 方法: curl HEAD + SSH VPS（Caddyfile + Ghost DB + redirects.txt）
> 実施日: 2026-03-28
> 原則: 実装なし。監査と記録のみ。

---

## URL正規化方針（CLAUDE.md標準）

```
JA版: nowpattern.com/[name]/          ← Ghost slug: [name]
EN版: nowpattern.com/en/[name]/       ← Ghost slug: en-[name]（Caddy rewrite経由）
```

**全公開URLは200を直接返すべき。301はSEO損失 + UX degradation。**

---

## ハブページURL全チェック

| URL | Ghost slug | HTTP | 判定 | 備考 |
|-----|-----------|------|------|------|
| https://nowpattern.com/ | — | 200 | ✅ | 正常 |
| https://nowpattern.com/en/ | — | 200 | ✅ | 正常 |
| https://nowpattern.com/predictions/ | predictions | 200 | ✅ | 正常 |
| https://nowpattern.com/en/predictions/ | en-predictions | 200 | ✅ | 正常 |
| https://nowpattern.com/about/ | about | 200 | ✅ | 正常 |
| https://nowpattern.com/en/about/ | en-about | 200 | ✅ | 正常 |
| https://nowpattern.com/taxonomy/ | taxonomy-ja | 200 | ✅ | /taxonomy-ja/から301経由 |
| https://nowpattern.com/en/taxonomy/ | en-taxonomy | 200 | ✅ | 正常 |
| https://nowpattern.com/taxonomy-guide/ | taxonomy-guide-ja | 200 | ✅ | 正常 |
| https://nowpattern.com/en/taxonomy-guide/ | en-taxonomy-guide | 200 | ✅ | 正常 |

---

## リダイレクトチェーン全記録

### 301リダイレクト一覧（不要なものは修正対象）

| 発生元URL | リダイレクト先 | 種別 | 使われている場所 | 判定 |
|----------|-------------|------|----------------|------|
| /taxonomy-ja/ | /taxonomy/ | 301 | **全ページnav**（Ghost nav設定） | ⚠️ 不要301。nav直リンクを/taxonomy/に変更すべき |
| /taxonomy-en/ | /en/taxonomy/ | 301 | /taxonomy/の言語切替 | ⚠️ 不要301。/en/taxonomy/に直接リンクすべき |
| /taxonomy-guide-ja/ | /taxonomy/ | 301 | **全ページfooter** | ❌ **[P1] 誤リダイレクト先。/taxonomy-guide/が正解** |
| /taxonomy-guide-en/ | /en/taxonomy-guide/ | 301 | (未使用？) | ⚠️ 現在は正常方向。フッターリンク修正時に更新 |
| /en-predictions/ | /en/predictions/ | 301 | /en/*ページのJS nav override | ⚠️ 不要301。JS内URLを/en/predictions/に修正すべき |
| /en-taxonomy-guide/ | /en/taxonomy-guide/ | 301 | (未使用？) | ✅ リダイレクト方向は正常 |
| /en/en-btc-70k-march-31-2026/ | /en/will-bitcoin-exceed-70000-by/ | 301 | /en/predictions/記事リンク | ⚠️ [P3] /en/en-プレフィックスバグ |
| /en/en-btc-90k-march-31-2026/ | /en/will-btc-recover-90000-by-the/ | 301 | /en/predictions/記事リンク | ⚠️ [P3] 同上 |
| /en/en-fed-fomc-march-2026-rate-decision/ | /en/will-the-fed-cut-rates-at-the-march-202/ | 301 | /en/predictions/記事リンク | ⚠️ [P3] 同上 |
| /en/en-khamenei-assassination-... | /en/after-khameneis-assassination-... | 301 | /en/predictions/記事リンク | ⚠️ [P3] 同上 |

---

## 404発生URL一覧（確認済み）

| URL | 発見場所 | 内容 |
|-----|---------|------|
| /nan-sinahai-nomi-zhong-jun-shi-dui-zhi-dui-li-noluo-xuan-gaou-fa-chong-tu-risukuwolin-jie-dian-heya-sishi-ang-gerugou-zao/ | ホームページ 記事リンク#4 | Ghost DB に存在しないslug |

**Ghost DB確認**: 同トピック（南シナ海）の記事は4件存在するが、このslugは削除済みか移行漏れ。

---

## 特殊URL確認

### タグページ（taxonomy filter）

| URL | HTTP | 判定 |
|-----|------|------|
| /tag/genre-geopolitics/?lang=ja | 200 | ✅ |
| /tag/genre-geopolitics/?lang=en | 200 | ✅ |
| /tag/lang-en/ | 200 | ✅ |
| /tag/event-alliance/?lang=ja | 200 | ✅ |
| /tag/event-competition/?lang=ja | 200 | ✅ |
| /tag/event-cyber/?lang=ja | 200 | ✅ |

### ページネーション

| URL | HTTP | 判定 |
|-----|------|------|
| /page/2/ | 200 | ✅ |
| /en/page/2/ | 200 | ✅ |

### AI/クローラー用ファイル（既存監査済み）

| URL | HTTP | 判定 |
|-----|------|------|
| /llms.txt | 200 | ✅ RESOLVED (ISS-001/002) |
| /llms-full.txt | 200 | ✅ RESOLVED (ISS-002) |
| /robots.txt | 200 | ✅ |
| /sitemap.xml | （未確認） | — |
| /rss/ | 200 | ✅ |

---

## EN/JA URL ペア一覧（hreflang整合性）

| JA URL | EN URL | JA→EN switch | EN→JA switch | 判定 |
|--------|--------|-------------|-------------|------|
| / | /en/ | /en/ ✅ | / ✅ | ✅ |
| /predictions/ | /en/predictions/ | /en/predictions/ ✅ | /predictions/ ✅ | ✅ |
| /about/ | /en/about/ | /en/about/ ✅ | /about/ ✅ | ✅ |
| /taxonomy/ | /en/taxonomy/ | taxonomy-en/ ⚠️301 | taxonomy-ja/ ⚠️301 | ⚠️ 余計な301 |
| /taxonomy-guide/ | /en/taxonomy-guide/ | （フッターから到達不可）❌ | — | ❌ |

---

## Caddyfile リダイレクト設定の問題点

### 発見: taxonomy-guide-ja の誤設定

```
# /etc/caddy/nowpattern-redirects.txt 実際の設定（問題箇所）
redir /taxonomy-guide-ja/ /taxonomy/ permanent    ← ❌ 誤り: /taxonomy-guide/ が正解
redir /taxonomy-guide-en/ /en/taxonomy-guide/ permanent  ← ✅ 正常方向
```

**修正案**:
```diff
- redir /taxonomy-guide-ja/ /taxonomy/ permanent
+ redir /taxonomy-guide-ja/ /taxonomy-guide/ permanent
```

さらに根本解決は Ghost Admin のフッターナビゲーションを `/taxonomy-guide/` に変更し、301を経由しないようにすること。

---

## URL品質スコア

| カテゴリ | 合格 | 不合格 | スコア |
|---------|------|--------|-------|
| ハブページ直接アクセス | 10/10 | 0 | 100% |
| 記事リンク（JA home 10件） | 9/10 | 1 | 90% |
| 記事リンク（EN home 10件） | 10/10 | 0 | 100% |
| nav内リンク（不要301なし） | 5/7 | 2 | 71% |
| フッターリンク | 1/2 | 1 | 50% |
| **総合** | **35/39** | **4** | **90%** |

---

*作成: 2026-03-28 | 監査方法: curl HEAD × SSH Ghost DB × Caddyfile直接確認*
