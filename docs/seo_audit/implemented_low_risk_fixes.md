# 実装済み低リスクSEO修正レポート
> 実施日: 2026-03-26 | 担当: local-claude (SEO Audit Session)

---

## 概要

このセッションで実装した3つの低リスクSEO修正。すべてナオトの事前確認済み。

---

## Fix 1: `genre-*` タグページのnoindex化

### 問題
- `/tag/genre-*` タグページ（例: `/tag/genre-geopolitics/`）が Googleにインデックスされる可能性があった
- これらは記事分類用の内部タクソノミータグであり、読者向けコンテンツではない
- 重複コンテンツ・低品質ページとして評価され、サイト全体のクロールバジェットを消費

### 修正内容
**ファイル**: `/etc/caddy/Caddyfile`

```caddy
# Guard 1: Internal taxonomy tags noindex
# p-*/event-*/lang-* are internal only. New tags auto-covered by pattern.
@internal_tags path /tag/p-* /tag/event-* /tag/lang-* /tag/deep-pattern/ /tag/nowpattern/ /tag/genre-*
header @internal_tags X-Robots-Tag "noindex, follow"
```

既存の `@internal_tags` マッチャーに `/tag/genre-*` を追加した。

### 検証
```
HTTP/2 200
x-robots-tag: noindex, follow
```
`curl -sI https://nowpattern.com/tag/genre-geopolitics/` → X-Robots-Tag: noindex, follow ✅

### robots.txt の設計判断
`Disallow: /tag/genre-*` を **追加しなかった**。理由:
- robots.txt の Disallow はクローラーがページを訪問できなくなる
- ページを訪問しないとnoindexヘッダーを読めない
- 結果: 永久にインデックスされたままになる可能性
- **正解**: noindexヘッダーをHTTPレスポンスで送る（クロールは許可、インデックスは拒否）

---

## Fix 2: `a4-hreflang-injector.py` バグ修正 + 全記事への一括注入

### 問題
- EN記事の canonical URL を正しく計算できていなかった
- `/en/about/` などの特殊ページは Caddy rewrite 経由でGhost slug `en-about` にマップされるが、
  一般記事は Ghost routes.yaml の `permalink: /en/{slug}/` で直接ルーティングされる
- 注入後に記事が更新されても hreflang が消えない問題

### 修正内容
**ファイル**: `/opt/shared/scripts/a4-hreflang-injector.py`

1. EN URL 生成ロジックを修正: Ghost routes.yaml の `permalink: /en/{slug}/` に従い、
   ENスラッグをそのままパスに使用（`en-` プレフィックスを保持）
2. `__GHOST_URL__` プレースホルダーを使用してドメインをハードコードしない
3. マーカー `<!-- NP-A4-HREFLANG -->` で注入済みかどうかを判定（重複防止）
4. `--lang=all` オプションで JA/EN 全記事を一括処理

### URL構造の確認（2026-03-26実証）
```
EN記事スラッグ（en-プレフィックスあり）: en-irans-degraded-deterrence-...
公開URL: https://nowpattern.com/en/en-irans-degraded-deterrence-.../ → HTTP 200 ✅

EN記事スラッグ（en-プレフィックスなし）: the-3-hours-of-hormuz-...
公開URL: https://nowpattern.com/en/the-3-hours-of-hormuz-.../ → HTTP 200 ✅
```

Ghost routes.yaml の動作: `permalink: /en/{slug}/` はスラッグをそのままURLに使用する。

### 注入後サンプル（JA記事にペアEN記事がある場合）
```html
<!-- NP-A4-HREFLANG -->
<link rel="alternate" hreflang="ja" href="__GHOST_URL__/horumuzuhai-xia-.../">
<link rel="alternate" hreflang="en" href="__GHOST_URL__/en/en-horumuzuhai-xia-.../">
<link rel="alternate" hreflang="x-default" href="__GHOST_URL__/horumuzuhai-xia-.../">
```

### 進捗状況（2026-03-26 09:xx JST時点）
- 処理済み: **670/1342** 記事（PID 1481476 稼働中）
- 完了予定: 当日中

---

## Fix 3: ホームページ + `/en/` hreflang（Caddyfile handle blocks）

### 問題
- トップページ `https://nowpattern.com/` と `https://nowpattern.com/en/` に
  互いを指す `rel=alternate hreflang` が存在しなかった
- Ghost CMS テンプレートが独自ヘッダーを挿入しないため、Caddy で対応が必要

### 修正内容
**ファイル**: `/etc/caddy/Caddyfile`

```caddy
# Guard 3: Homepage hreflang via handle blocks (2026-03-26 SEO fix v2)
handle / {
    header Link "<https://nowpattern.com/>; rel=alternate; hreflang=ja, <https://nowpattern.com/en/>; rel=alternate; hreflang=en, <https://nowpattern.com/>; rel=alternate; hreflang=x-default"
    reverse_proxy localhost:2368
}
handle /en/ {
    header Link "<https://nowpattern.com/>; rel=alternate; hreflang=ja, <https://nowpattern.com/en/>; rel=alternate; hreflang=en, <https://nowpattern.com/>; rel=alternate; hreflang=x-default"
    reverse_proxy localhost:2368
}
```

### 設計の注意点
- Caddy の `header` ディレクティブは既存ヘッダーを**追加**する（上書きしない）
- `handle /` ブロックは他のルートより前に配置（Caddy は first-match）
- `hreflang` 値はクォートなしで `ja` / `en` を使用（RFC 5988準拠）
- `x-default` は JA版を指す（メインターゲット市場が日本語圏のため）

### 検証
```bash
curl -sI https://nowpattern.com/ | grep -i link
# → link: <https://nowpattern.com/>; rel=alternate; hreflang=ja, ...
```

---

## 全修正のリスク評価

| 修正 | リスク | 影響範囲 | ロールバック |
|------|--------|---------|------------|
| Fix 1: genre-* noindex | 低 | /tag/genre-* のみ | Caddyfileから行削除 + caddy reload |
| Fix 2: hreflang注入 | 低 | 全記事 codeinjection_head | マーカー削除スクリプトで一括リセット可 |
| Fix 3: Homepage Link header | 低 | / と /en/ のみ | handleブロック削除 + caddy reload |

---

*作成: 2026-03-26 | Session: SEO Audit*
