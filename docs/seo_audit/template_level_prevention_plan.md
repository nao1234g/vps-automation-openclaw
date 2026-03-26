# テンプレートレベル SEO 予防プラン
> 作成日: 2026-03-26 | nowpattern.com SEO Audit

---

## このドキュメントの目的

**「修正するより、最初から正しく作る」**

今回のSEO監査で見つかった問題の多くは、記事・ページ生成時に正しいメタデータを
最初から付与していれば発生しなかった。このドキュメントは「今後の記事生成パイプラインに
組み込むべき SEO チェック項目」を定義する。

---

## 問題1: 新規記事に hreflang が付与されない

### 現状の問題

`a4-hreflang-injector.py` は**既存記事への一括注入ツール**である。
新規記事が Ghost に投稿されるたびに自動実行されないため、新記事には hreflang がない。

### 解決策（推奨）

**Option A: Ghost Webhook で自動注入（推奨）**

```
Ghost 記事公開（post.published）
  → VPS Webhook Server（port 8769）
      → a4-hreflang-injector.py --slug={slug} --lang=ja
```

実装済みの Ghost Webhook Server (port 8769) を利用して、
新記事公開時に `a4-hreflang-injector.py --slug={slug}` を自動実行する。

**実装コスト**: 低（既存 webhook_server.py に処理を追加するだけ）

**Option B: nowpattern_publisher.py に hreflang 注入を統合**

記事を Ghost API で公開するとき、`codeinjection_head` に hreflang を直接含める。

```python
# nowpattern_publisher.py 修正案
def build_hreflang_html(slug, lang, paired_slug=None):
    """hreflang リンクタグを生成"""
    if lang == 'ja' and paired_slug:
        return f"""<!-- NP-A4-HREFLANG -->
<link rel="alternate" hreflang="ja" href="__GHOST_URL__/{slug}/">
<link rel="alternate" hreflang="en" href="__GHOST_URL__/en/{paired_slug}/">
<link rel="alternate" hreflang="x-default" href="__GHOST_URL__/{slug}/">"""
    elif lang == 'en':
        ja_slug = slug[3:] if slug.startswith('en-') else None
        if ja_slug:
            return f"""<!-- NP-A4-HREFLANG -->
<link rel="alternate" hreflang="en" href="__GHOST_URL__/en/{slug}/">
<link rel="alternate" hreflang="ja" href="__GHOST_URL__/{ja_slug}/">
<link rel="alternate" hreflang="x-default" href="__GHOST_URL__/{ja_slug}/">"""
    # ソロ（ペアなし）
    return f"""<!-- NP-A4-HREFLANG -->
<link rel="alternate" hreflang="{lang}" href="__GHOST_URL__/{'' if lang == 'ja' else 'en/'}{slug}/">
<link rel="alternate" hreflang="x-default" href="__GHOST_URL__/{'' if lang == 'ja' else 'en/'}{slug}/">"""
```

**実装コスト**: 中（publisher.py の修正 + テスト）

**推奨**: Option A（既存インフラ活用）を採用し、Webhook で自動注入する。

---

## 問題2: EN 記事に lang-en タグが付かない

### 現状（修正済み）

2026-03-25 に `nowpattern_publisher.py` に `language=_pub_lang` を追加して修正済み。
ただし過去の 519件のEN draft にはタグが正しく付いていない可能性がある（rescue.py で修正済み）。

### 予防策（新規記事向け）

```python
# nowpattern_publisher.py（修正済み — 確認用）
tags_for_api = [
    {"name": "nowpattern"},
    {"name": "deep-pattern"},
    {"name": "日本語" if lang == "ja" else "English"},  # ← lang-ja / lang-en タグ
    # ... その他のタクソノミータグ
]
```

**確認**: `article_validator.py` が公開前に lang タグの存在を検証していることを確認する。

---

## 問題3: EN 記事の canonical URL が JA に向く

### 現状（修正済み）

2026-03-22 に `canonical_url` API フィールドを使って修正済み。

### 予防策

```python
# nowpattern_publisher.py（修正済み — 確認用）
post_data = {
    "slug": slug,
    "canonical_url": f"https://nowpattern.com/en/{slug}/" if lang == "en" else None,
    # codeinjection_head には hreflang のみ（canonical は canonical_url フィールドで設定）
}
```

**ルール（CLAUDE.md / content-rules.md に追記推奨）**:
> Ghost ENページのcanonical標準: canonical_urlフィールドで設定、codeinjection_headにはhreflangのみ

---

## 問題4: タクソノミータグページのインデックス

### 現状（修正済み）

Guard 1 で `/tag/genre-*` 等に noindex を設定済み。

### 予防策（新規タグ追加時）

Caddyfile の Guard 1 は**パターンマッチング**を使用しているため、
新しい `genre-*` タグを追加しても自動的にカバーされる。

```caddy
@internal_tags path /tag/p-* /tag/event-* /tag/lang-* /tag/deep-pattern/ /tag/nowpattern/ /tag/genre-*
```

ただし、新しいパターン（例: `/tag/scenario-*`）を導入した場合は、Caddyfile への追加が必要。

**ルール**: `nowpattern_taxonomy.json` に新しいタクソノミーパターンを追加する際は、
同時に Caddyfile の Guard 1 にも対応するパターンを追加すること。

---

## 記事生成 SEO ゲートチェックリスト

新規記事生成スクリプト（NEO → publisher.py）に組み込むべき検証項目:

```python
# article_seo_gate.py（新規作成推奨）
def validate_seo(post_data, lang):
    errors = []

    # 1. タイトルの長さ（60文字以内が推奨）
    if len(post_data.get("title", "")) > 70:
        errors.append(f"タイトルが長すぎます: {len(post_data['title'])}文字（推奨: 60文字以内）")

    # 2. スラッグの品質（中国語ピンイン等を検知）
    slug = post_data.get("slug", "")
    if any(ord(c) > 127 for c in slug):
        errors.append(f"スラッグに非ASCII文字が含まれています: {slug}")

    # 3. メタ説明の長さ（155文字以内が推奨）
    meta_desc = post_data.get("custom_excerpt", "")
    if meta_desc and len(meta_desc) > 160:
        errors.append(f"メタ説明が長すぎます: {len(meta_desc)}文字（推奨: 155文字以内）")

    # 4. lang タグの存在確認
    tags = [t.get("slug", "") for t in post_data.get("tags", [])]
    expected_lang_tag = "lang-ja" if lang == "ja" else "lang-en"
    if expected_lang_tag not in tags:
        errors.append(f"lang タグが不足しています: {expected_lang_tag}")

    # 5. canonical_url（EN 記事は必須）
    if lang == "en" and not post_data.get("canonical_url"):
        errors.append("EN 記事に canonical_url が設定されていません")

    return errors
```

**このゲートを `nowpattern_publisher.py` の公開前チェックに組み込む。**

---

## 中国語ピンインスラッグ問題

### 現状

記事タイトルが中国語を含む場合、Ghost がピンインをスラッグ化することがある。
例: `horumuzukai-xia-de-...` → スラッグが判読不能になる。

### 影響

- URL が意味不明（SEO シグナル弱）
- hreflang の JA-EN ペアリングに影響しない（`en-` プレフィックスで照合するため）

### 対策（publisher.py 側）

```python
def sanitize_slug(title, lang):
    """日本語タイトルから SEO フレンドリーなスラッグを生成"""
    import re
    # 英数字・ハイフンのみ許可
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = slug.strip('-')
    if lang == 'en' and not slug.startswith('en-'):
        slug = f'en-{slug}'
    return slug[:80]  # 最大80文字
```

---

## 実装優先度マトリクス

| 問題 | 実装コスト | SEO 影響 | 優先度 | 推奨期限 |
|------|-----------|---------|--------|---------|
| 新規記事への hreflang 自動注入 | 低（Webhook 活用） | 高 | **P1** | 1週間以内 |
| SEO ゲートチェック組み込み | 中 | 中 | P2 | 今月中 |
| スラッグ品質改善 | 中 | 低 | P3 | 来月 |
| sitemap カスタマイズ（noindex除外） | 高 | 低 | P4 | 次回スプリント |

---

*作成: 2026-03-26 | Session: SEO Audit*
