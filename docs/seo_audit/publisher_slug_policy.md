# Publisher スラッグポリシー（2026-03-28 確立）

## 背景

EN記事の公開URL（スラッグ）が日本語ローマ字（ピンイン）になっていた問題を根本修正した際に確立したポリシー。

## ルール

### EN記事のスラッグ生成

**必須**: EN記事を投稿する際は、英語タイトルからASCIIのみのクリーンなスラッグを生成して `slug` パラメータで渡す。Ghost自動生成に任せてはいけない。

**理由**: Ghost CMSはスラッグを自動生成する際に、日本語文字列をローマ字変換（ピンイン）するため、`en-nan-sinahai-nomi-...` のような読者に無意味なURLになる。

### スラッグ生成関数

```python
def _title_to_en_slug(title: str) -> str:
    """Generate clean ASCII English slug from title for Ghost API."""
    if not title:
        return ''
    s = title.lower()
    s = re.sub(r'[^\w\s-]', '', s)   # ASCII以外を除去
    s = re.sub(r'[\s_]+', '-', s)     # スペース/アンダースコアをハイフンに
    s = re.sub(r'-+', '-', s)          # 連続ハイフンを1つに
    s = s.strip('-')
    if len(s) > 80:
        s = s[:80].rsplit('-', 1)[0]   # 単語境界で80文字に切る
    return s or 'article'
```

### 実装場所

**ファイル**: `/opt/shared/scripts/nowpattern_publisher.py`

`publish_deep_pattern()` 内:
```python
_pub_slug = _title_to_en_slug(title) if _pub_lang == "en" else ""
ghost_result = post_to_ghost(
    title=title,
    html=html,
    tag_objects=tag_objects,
    ghost_url=ghost_url,
    admin_api_key=admin_api_key,
    status=status,
    featured=True,
    codeinjection_foot=jsonld,
    language=_pub_lang,
    slug=_pub_slug,      # ← EN記事のときのみ英語スラッグを指定
)
```

`post_to_ghost()` 内:
```python
if slug:
    post_payload["slug"] = slug
```

### JA記事のスラッグ

JA記事はスラッグを明示的に渡さない（`slug=""`）。Ghost が日本語タイトルからローマ字変換したスラッグを生成するが、JA記事のURLは `/{slug}/` 形式なので問題ない。

### 重複スラッグ

Ghost CMS が同名スラッグが存在する場合に `-2`, `-3` などを自動的に末尾に付与する。`_title_to_en_slug()` は重複チェックを行わないが、Ghost API側で処理される。

## URL標準（CLAUDE.mdのバイリンガルURL標準に従う）

```
JA版: nowpattern.com/{slug}/           Ghostスラッグ: {slug}
EN版: nowpattern.com/en/{en-slug}/     Ghostスラッグ: {en-slug}（en-プレフィックスなし）
```

**重要**: 修正後の新規EN記事スラッグは `en-` プレフィックスを付けない。例:
- ✅ `us-china-military-standoff`（正しい）
- ❌ `en-us-china-military-standoff`（不要なen-プレフィックス）

既存の `en-about`、`en-predictions` 等の固定ページスラッグはCaddy rewriteで管理しており、別ルール。

## 検証方法

新規EN記事を1件公開後:
```bash
ssh root@163.44.124.123 "
  sqlite3 /var/www/nowpattern/content/data/ghost.db \
  \"SELECT slug, title FROM posts WHERE status='published' ORDER BY created_at DESC LIMIT 1\"
"
```

スラッグが英語単語のハイフン区切りになっていれば正常。

---

*作成: 2026-03-28 | 担当: LEFT_EXECUTOR*
