# hreflang 実装アーキテクチャ
> 作成日: 2026-03-26 | nowpattern.com バイリンガルSEO設計

---

## 全体設計方針

nowpattern.com は JA/EN バイリンガルサイト。hreflang の実装は3層に分かれている。

```
Layer 1: Caddy HTTP Link ヘッダー（ホームページ専用）
Layer 2: Ghost codeinjection_head インライン <link> タグ（固定ページ 8件）
Layer 3: a4-hreflang-injector.py による一括注入（全記事 1,342件）
```

---

## Layer 1: Caddyfile（ホームページ）

**対象**: `https://nowpattern.com/` と `https://nowpattern.com/en/` のみ

**実装場所**: `/etc/caddy/Caddyfile`

```caddy
handle / {
    header Link "<https://nowpattern.com/>; rel=alternate; hreflang=ja, \
                  <https://nowpattern.com/en/>; rel=alternate; hreflang=en, \
                  <https://nowpattern.com/>; rel=alternate; hreflang=x-default"
    reverse_proxy localhost:2368
}
handle /en/ {
    header Link "<https://nowpattern.com/>; rel=alternate; hreflang=ja, \
                  <https://nowpattern.com/en/>; rel=alternate; hreflang=en, \
                  <https://nowpattern.com/>; rel=alternate; hreflang=x-default"
    reverse_proxy localhost:2368
}
```

**なぜ HTTPヘッダーか**: Ghost テンプレートのホームページには `codeinjection_head` フィールドがないため。

---

## Layer 2: Ghost codeinjection_head（固定ページ）

**対象**: 8件の固定バイリンガルページ

| ページ | canonical | hreflang設定 |
|--------|-----------|-------------|
| `/about/` | `/about/` | ja + en(/en/about/) + x-default |
| `/en/about/` | `/en/about/` | en + ja(/about/) + x-default |
| `/predictions/` | `/predictions/` | ja + en(/en/predictions/) + x-default |
| `/en/predictions/` | `/en/predictions/` | en + ja(/predictions/) + x-default |
| `/taxonomy/` | `/taxonomy/` | ja + en(/en/taxonomy/) + x-default |
| `/en/taxonomy/` | `/en/taxonomy/` | en + ja(/taxonomy/) + x-default |
| `/taxonomy-guide/` | `/taxonomy-guide/` | ja + en(/en/taxonomy-guide/) + x-default |
| `/en/taxonomy-guide/` | `/en/taxonomy-guide/` | en + ja(/taxonomy-guide/) + x-default |

---

## Layer 3: a4-hreflang-injector.py（記事）

**対象**: 全1,342記事（JA 215件 + EN 1,111件 + その他 16件）

**スクリプトパス**: `/opt/shared/scripts/a4-hreflang-injector.py`

### 動作フロー

```
1. Ghost Admin API で全published記事を取得
2. JA記事のスラッグ → 対応ENスラッグを探す
   パターン: slug="horumuzukai-..." → 対応: slug="en-horumuzukai-..."
3. ペアが見つかった場合: JA/EN双方に互いを指すhreflangを注入
4. ペアが見つからない場合: ソロhreflangを注入
5. codeinjection_head にマーカー + <link>タグを追記
```

### 注入されるHTML

**JA記事（ENペアあり）**:
```html
<!-- NP-A4-HREFLANG -->
<link rel="alternate" hreflang="ja" href="__GHOST_URL__/{ja-slug}/">
<link rel="alternate" hreflang="en" href="__GHOST_URL__/en/{en-slug}/">
<link rel="alternate" hreflang="x-default" href="__GHOST_URL__/{ja-slug}/">
```

**EN記事（JAペアあり）**:
```html
<!-- NP-A4-HREFLANG -->
<link rel="alternate" hreflang="en" href="__GHOST_URL__/en/{en-slug}/">
<link rel="alternate" hreflang="ja" href="__GHOST_URL__/{ja-slug}/">
<link rel="alternate" hreflang="x-default" href="__GHOST_URL__/{ja-slug}/">
```

**ソロ記事（ペアなし）**:
```html
<!-- NP-A4-HREFLANG -->
<link rel="alternate" hreflang="{ja|en}" href="__GHOST_URL__/.../">
<link rel="alternate" hreflang="x-default" href="__GHOST_URL__/.../">
```

### `__GHOST_URL__` プレースホルダー

Ghost が `codeinjection_head` をレンダリングする際、`__GHOST_URL__` を実際のドメイン
（`https://nowpattern.com`）に自動置換する。これによりハードコーディングを避けている。

### 重複防止

`<!-- NP-A4-HREFLANG -->` マーカーが存在する記事はスキップ。
リセットは以下で実行:
```bash
# Ghost Admin API で codeinjection_head からマーカーを削除
python3 /opt/shared/scripts/a4-hreflang-reset.py
```

---

## URL設計の根拠

### なぜ `/en/en-{slug}/` がURIとして正しいか

Ghost routes.yaml:
```yaml
collections:
  /en/:
    permalink: /en/{slug}/
    filter: tag:lang-en
```

この設定は「lang-en タグが付いた記事のスラッグを `/en/` プレフィックスで配信する」という意味。
ENスラッグが `en-horumuzukai-...` の場合、URLは `/en/en-horumuzukai-.../` となる。

**実証**:
```
https://nowpattern.com/en/en-irans-degraded-deterrence-.../ → HTTP 200 ✅
https://nowpattern.com/en/the-3-hours-of-hormuz-.../ → HTTP 200 ✅
```

---

## Google推奨ルールへの準拠確認

| ルール | 状態 |
|--------|------|
| 双方向リンク（JA→EN, EN→JA） | ✅ 実装済み |
| 自己参照（hreflang="ja" が自分自身を指す） | ✅ 実装済み |
| `x-default` の設定 | ✅ JA版を指す |
| absolute URL（相対URLは不可） | ✅ `__GHOST_URL__`が展開される |
| `canonical` との矛盾なし | ✅ canonical は各言語版を指す |

---

*作成: 2026-03-26 | Session: SEO Audit*
