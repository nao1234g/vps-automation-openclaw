# SEO Handoff: sitemap-news.xml → Sitemap Index 追加

**実施日**: 2026-03-28
**実施者**: Claude Code (ローカル)
**ステータス**: COMPLETED + VERIFIED

---

## 概要

`/sitemap.xml`（Ghostが動的に提供するsitemap index）に `sitemap-news.xml` が含まれていなかった。
Googleニュース向けのnews sitemapをGSCで送信するには、このsitemap indexから参照されている必要がある。

**Before**: sitemap.xml に4エントリ（pages, posts, authors, tags）
**After**: sitemap.xml に5エントリ（上記 + **sitemap-news.xml**）

---

## 実施内容（最小差分）

### 1. 静的 sitemap.xml を作成・配置

```bash
# ファイルパス
/var/www/nowpattern-static/sitemap.xml

# 内容
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="//nowpattern.com/sitemap.xsl"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://nowpattern.com/sitemap-pages.xml</loc></sitemap>
<sitemap><loc>https://nowpattern.com/sitemap-posts.xml</loc></sitemap>
<sitemap><loc>https://nowpattern.com/sitemap-authors.xml</loc></sitemap>
<sitemap><loc>https://nowpattern.com/sitemap-tags.xml</loc></sitemap>
<sitemap><loc>https://nowpattern.com/sitemap-news.xml</loc></sitemap>
</sitemapindex>
```

### 2. Caddyfile に `handle /sitemap.xml` を追加

```caddy
# /etc/caddy/Caddyfile — /sitemap-news.xml ブロックの直後に挿入
handle /sitemap.xml {
    root * /var/www/nowpattern-static
    file_server
    header Content-Type "application/xml; charset=utf-8"
}
```

**重要**: `handle` はGhostの `reverse_proxy localhost:2368` より先に評価されるため、
Ghostの動的sitemap.xmlを静的ファイルで上書きする形になる。

### 3. Caddy reload

```bash
caddy validate --config /etc/caddy/Caddyfile  # → Valid configuration
systemctl reload caddy
```

---

## バックアップ

```
/tmp/Caddyfile_bak_20260328_b.txt  (3570 bytes — 変更前のバックアップ)
```

**ロールバック手順** (30秒):

```bash
cp /tmp/Caddyfile_bak_20260328_b.txt /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
rm /var/www/nowpattern-static/sitemap.xml
```

---

## Live Verify（2026-03-28 実測値）

| チェック項目 | 結果 |
|---|---|
| `curl https://nowpattern.com/sitemap.xml` → 5エントリ | ✅ |
| `content-type: application/xml; charset=utf-8` | ✅ |
| `sitemap-pages.xml`: 200 | ✅ |
| `sitemap-posts.xml`: 200 | ✅ |
| `sitemap-authors.xml`: 200 | ✅ |
| `sitemap-tags.xml`: 200 | ✅ |
| `sitemap-news.xml`: 200 | ✅ |

---

## 最終リグレッションチェック（Phase 4）

| Track | 項目 | 値 | 判定 |
|---|---|---|---|
| Track 1 | lang-ja posts | 229 | ✅ INTACT |
| Track 1 | lang-en posts | 1131 | ✅ INTACT |
| Track 1 | pages | 14 | ✅ INTACT |
| Track 1 | posts w/o hreflang | 0 | ✅ INTACT |
| Track 1 | pages w/o hreflang | 0 | ✅ INTACT |
| Track 2 | /en/tag/geopolitics/ noindex | true | ✅ INTACT |
| Track 2 | /author/naoto/ noindex | true | ✅ INTACT |
| Track 2 | /tag/lang-ja/ noindex | true | ✅ INTACT |
| Track 3 | sitemap-news.xml old en- prefix | 0 | ✅ INTACT |
| Track 3 | sitemap-news.xml /en/ prefix | 14 | ✅ INTACT |
| Track 5 | d5-cwv-monitor @ 23:00 UTC | true | ✅ INTACT |
| Track 5 | prediction_page_builder @ 22:00 UTC | true | ✅ INTACT |

---

## GSC Handoff Package（Candidate E）

### sitemap-news.xml を GSC に手動送信する手順

1. **Google Search Console** (https://search.google.com/search-console) にログイン
2. プロパティ `nowpattern.com` を選択
3. 左メニュー「サイトマップ」をクリック
4. 「新しいサイトマップの追加」に以下を入力して送信:
   ```
   https://nowpattern.com/sitemap-news.xml
   ```
5. ステータスが「成功」になることを確認（通常数分〜数時間）

### sitemap.xml（index）も更新されたことを確認させる

sitemap.xmlを再送信する必要は**ない**（既にGSCに登録済みの場合）。
ただし、初回または再送信したい場合:
```
https://nowpattern.com/sitemap.xml
```

### Track 3 修正済みURL（旧 en- prefix → /en/ prefix）の再クロール依頼

Track 3で修正したENページのURLは正しく `/en/[slug]/` 形式になった。
古いインデックス（`/en-[slug]/`）が残っている場合は以下で解決:

1. GSC「URL検査」に旧URLを入力:
   - 例: `https://nowpattern.com/en-about/`
2. 「インデックス登録をリクエスト」ボタンをクリック（優先クロール依頼）
3. または sitemap-pages.xml に `/en/about/` があることを確認（既存）

---

## 未解決 Candidate（次セッション検討）

### Candidate A: custom_excerpt（meta description）一括設定
- **状況**: 1295/1360記事（95.2%）がcustom_excerptなし
- **SEO影響**: Googleがランダム本文をスニペットとして使用 → CTR低下リスク
- **承認待ち**: 1295件のGhost API PATCH が必要（bulk write）
- **推奨アプローチ**: NEO-ONEに記事単位でexcerptを生成させてバッチ投入（1日50件ずつ）

### Candidate C: 旧 en- prefix URL 重複整理
- **状況**: en- prefix slugを持つpublished記事が452件
- **詳細調査必要**: これらのGhostスラッグが `/en-[slug]/` として公開URLになっているか、
  Caddyでリダイレクト済みか、を確認してから判断
- **承認待ち**: Ghost DB直接変更 or API PATCH大量 → Type 1操作

### Candidate D: Operational Hardening（Ghost Webhook強化）
- **状況**: ghost-webhook-server 稼働中（since 2026-03-10）
- **DEFER理由**: SEO緊急度低。現状問題なし

---

## 次回セッション開始時のベースライン

```python
# python3 /tmp/final_regression.py で確認
# 期待値:
{
  "track1": {"lang_ja": 229, "lang_en": 1131, "pages": 14, "posts_no_hreflang": 0, "pages_no_hreflang": 0},
  "track2": {"/en/tag/geopolitics/": true, "/author/naoto/": true, "/tag/lang-ja/": true},
  "track3": {"total_locs": 21, "old_en_prefix": 0, "en_slash_prefix": 14},
  "track4_b": {"sitemap_xml_locs": 5, "sitemap_news_in_index": true},  ← NEW
  "track5": {"d5_cwv_23h": true, "builder_22h": true}
}
```

---

*作成: 2026-03-28 | SEO Maintenance Cycle 完了 | 次回: Candidate A approval pack 作成*
