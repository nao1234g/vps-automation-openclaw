# NOWPATTERN EN/JA ページペア マッピング＆言語切替監査
> 実施日: 2026-03-29

---

## 静的ページペア一覧

| JA URL（公開） | EN URL（公開） | JA slug（Ghost内部） | EN slug（Ghost内部） | hreflang 双方向 |
|---------------|---------------|---------------------|---------------------|----------------|
| `/` | `/en/` | `（Ghost homepage）` | `（Ghost en-homepage）` | ✅ |
| `/about/` | `/en/about/` | `about` | `en-about` | ✅ |
| `/predictions/` | `/en/predictions/` | `predictions` | `en-predictions` | ✅ |
| `/taxonomy/` | `/en/taxonomy/` | `taxonomy-ja` | `en-taxonomy` | ✅ |
| `/taxonomy-guide/` | `/en/taxonomy-guide/` | `taxonomy-guide-ja` | `en-taxonomy-guide` | ✅ |

→ 全5ページで hreflang 双方向リンク確認済み ✅

---

## hreflang 検証結果

### `/about/` ↔ `/en/about/`

```html
<link rel="alternate" hreflang="ja" href="https://nowpattern.com/about/">
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/about/">
<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/about/">
```
→ JA/EN/x-default 全3種 ✅（JA版・EN版両方に同一 hreflang セット）

### `/predictions/` ↔ `/en/predictions/`

```html
<link rel="alternate" hreflang="ja" href="https://nowpattern.com/predictions/">
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/predictions/">
<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/predictions/">
```
→ JA/EN/x-default 全3種 ✅

### `/taxonomy/` ↔ `/en/taxonomy/`

```html
<link rel="alternate" hreflang="ja" href="https://nowpattern.com/taxonomy/">
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/taxonomy/">
<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/taxonomy/">
```
→ JA/EN/x-default 全3種 ✅

### `/taxonomy-guide/` ↔ `/en/taxonomy-guide/`

```html
<link rel="alternate" hreflang="ja" href="https://nowpattern.com/taxonomy-guide/">
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/taxonomy-guide/">
<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/taxonomy-guide/">
```
→ JA/EN/x-default 全3種 ✅

---

## 言語スイッチリンク（JS動的注入）

ホームページ HTML に以下の JS テンプレートが含まれる:

```javascript
href="' + jaPath + '"
href="' + enPath + '"
```

Ghost テーマのヘッダー部分で動的に JA/EN パスを切り替えるスクリプトが稼働中。
静的ページでは `codeinjection_head` に直書きされた `<link rel="alternate">` が先行するため、動的注入はスキップ（重複防止ロジック確認済み）。

---

## URL パターン規約（再確認）

### 静的ページ（ルール確立済み）

```
JA 版: nowpattern.com/[name]/       ← Ghost slug: [name]
EN 版: nowpattern.com/en/[name]/    ← Ghost slug: en-[name]（内部名）
```

Caddy ルール:
```
handle /en/[name]/ { rewrite * /en-[name]/; reverse_proxy localhost:2368 }
redir /en-[name]/ /en/[name]/ permanent  (nowpattern-redirects.txt)
```

### 記事ページ（slug 規約移行途中）

| パターン | 件数 | 公開 URL | HTTP |
|----------|------|---------|------|
| JA 記事（ローマ字 slug） | ~211件 | `/[slug]/` | 200 直接 |
| EN 記事（`en-` プレフィックスあり） | 451件 | `/en-[slug]/` → 301 → `/en/en-[slug]/` | 200 |
| EN 記事（プレフィックスなし — 旧形式） | 681件 | `/[slug]/` → 301 → `/en/[slug]/` | 200 |

> EN 記事の旧形式 slug は Caddy の `lang-en` タグ検知 redirect rule で `/en/` 配下に正しくリダイレクトされる。
> ユーザー体験への直接影響なし（最終 200）。SEO 観点では `en-` プレフィックス統一が望ましい。

---

## 言語切替 UX 評価

| チェック項目 | 結果 | 詳細 |
|------------|------|------|
| ホームページに JA/EN 切替ナビあり | ✅ | `/` ⇔ `/en/` リンク両方に存在 |
| 静的ページに双方向 hreflang | ✅ | 5ペア全て確認 |
| 個別記事の言語切替 | ⚠️ | 動的 JS 注入（ランディング後に切替先 URL を計算）|
| `x-default` 指定 | ✅ | 全ページ JA 版を x-default に設定 |
| canonical URL 重複 | ✅ 解決済み | 2026-03-22〜28 SEO 監査で修正 |

---

## 残存課題

| 課題 ID | 内容 | リスク | 推奨対応 |
|--------|------|--------|---------|
| ~~ISS-NAV-001~~ | ~~ナビに `/taxonomy-ja/`（内部 slug）が露出。`/taxonomy/` を使うべき~~ | ✅ **RESOLVED** (2026-03-29 session3 ライブ確認) | Ghost navigation設定で `/taxonomy/` が使用中を確認。このドキュメントの記述がstaleだった。 |
| ISS-SLUG-001 | EN 記事 681件が `en-` プレフィックス未付与 | 中（SEO） | batch slug 修正スクリプト再実行（優先度: 次 SEO スプリント） |
| ISS-HREFLANG-001 | 個別記事の hreflang は JS 動的注入（Google クローラーが JS 実行しない場合は検出不可） | 低〜中 | 記事公開時に Ghost `codeinjection_head` に静的 hreflang を注入する仕組みを検討 |

---

*作成: Claude Code — 2026-03-29*
