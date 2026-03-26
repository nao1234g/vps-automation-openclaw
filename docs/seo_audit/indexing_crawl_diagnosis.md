# インデックスとクロール診断レポート
> 作成日: 2026-03-26 | nowpattern.com SEO Audit

---

## サイト構成概要

| 項目 | 数値 |
|------|------|
| 公開記事数（published） | **1,342件** |
| 日本語記事（lang-ja） | **215件** |
| 英語記事（lang-en） | **1,111件** |
| その他（タグなし等） | **16件** |
| ドラフト | 31件 |
| タグ総数 | 70件 |

---

## 現在のURL構造

### 記事 URL パターン
```
JA記事: https://nowpattern.com/{slug}/
EN記事: https://nowpattern.com/en/{slug}/

※ ENスラッグは2種類存在:
  - en-{base-slug}  （617件）← 翻訳記事
  - {slug-without-en-prefix}  （494件）← 直接英語執筆記事
```

### 固定ページ URL（Caddy rewrite 経由）
| 公開URL | Ghostスラッグ | hreflang |
|---------|-------------|---------|
| `/about/` | `about` | ja ↔ /en/about/ |
| `/en/about/` | `en-about` | en ↔ /about/ |
| `/predictions/` | `predictions` | ja ↔ /en/predictions/ |
| `/en/predictions/` | `en-predictions` | en ↔ /predictions/ |
| `/taxonomy/` | `taxonomy-ja` | ja ↔ /en/taxonomy/ |
| `/en/taxonomy/` | `en-taxonomy` | en ↔ /taxonomy/ |
| `/taxonomy-guide/` | `taxonomy-guide-ja` | ja ↔ /en/taxonomy-guide/ |
| `/en/taxonomy-guide/` | `en-taxonomy-guide` | en ↔ /taxonomy-guide/ |

---

## クロールバジェット問題

### 問題1: 内部タクソノミータグページのインデックス

**影響ページ（例）**:
```
/tag/genre-geopolitics/
/tag/genre-economy/
/tag/event-election/
/tag/p-geopolitics-economy-dynamics/
/tag/lang-ja/
/tag/lang-en/
/tag/deep-pattern/
/tag/nowpattern/
```

**状態**: Fix 1（Guard 1拡張）で対処済み
```
X-Robots-Tag: noindex, follow
```

### 問題2: ドラフト記事URLの漏洩

現在のドラフト31件は通常Google botには見えないが、SNS等で共有された場合に漏洩リスクがある。Ghost の Ghost Admin API は `published` のみを返すが、スラッグが予測可能な場合（`en-{existing-slug}`）は直接アクセス可能。

**リスクレベル**: 低（現状31件のみ）

---

## sitemapの状態

Ghost が自動生成する sitemap を使用:
```
https://nowpattern.com/sitemap.xml
```

**確認済み**:
- robots.txt に Sitemap ディレクティブあり ✅
- `/sitemap.xml` が存在する（Ghost 自動生成）✅

**懸念点**:
- sitemap に内部タクソノミータグページが含まれる可能性
- EN記事の sitemap エントリが `/en/{slug}/` 形式で正しく生成されているか未確認

---

## robots.txt 現状

```
User-agent: *
Sitemap: https://nowpattern.com/sitemap.xml
Disallow: /ghost/
Disallow: /email/
Disallow: /members/api/comments/counts/
Disallow: /r/
Disallow: /webmentions/receive/
```

**設計判断**: `/tag/*` は意図的に Disallow なし。理由はnoindexヘッダー方式を採用しているため
（Disallow を設定するとnoindexヘッダーをGoogleが読めない）。

---

## ページ別HTTPステータス確認（2026-03-26実施）

| URL | ステータス |
|-----|-----------|
| `https://nowpattern.com/` | 200 ✅ |
| `https://nowpattern.com/en/` | 200 ✅ |
| `https://nowpattern.com/predictions/` | 200 ✅ |
| `https://nowpattern.com/en/predictions/` | 200 ✅ |
| `https://nowpattern.com/tag/genre-geopolitics/` | 200 + noindex ✅ |

---

## 発見された課題（対処必要）

### 課題1: EN記事の hreflang ペアリング完全性

**1,111件のEN記事のうち、JA対訳がない「ソロ」記事が多数存在**。

- 翻訳ペア（JA↔EN）: 約617件
- EN単独記事: 約494件

単独EN記事には `hreflang="en"` + `x-default` のみを設定（JA参照なし）。
これは正しい実装（ペアがない場合に誤った参照を作るより良い）。

### 課題2: ページネーションページ

Ghost の `/page/2/`, `/en/page/2/` 等のページネーションに hreflang が注入されていない。
これはコンテンツページではないため、優先度低。

### 課題3: タグページ（表示用）

`/tag/nowpattern/`（全記事一覧）は noindex にしているが、これが意図的かどうか確認が必要。
`nowpattern` タグは全記事に付与されるため、ページ品質は高い可能性がある。

---

## 推奨アクション（優先度順）

1. **[完了]** genre-* noindex（Fix 1）
2. **[進行中]** 全記事 hreflang 注入（Fix 2: 670/1342完了）
3. **[完了]** ホームページ hreflang（Fix 3）
4. **[未着手]** Search Console でインデックス状況を定期確認
5. **[検討]** `/tag/nowpattern/` の noindex 解除（全記事ハブとして価値がある可能性）

---

*作成: 2026-03-26 | Session: SEO Audit*
