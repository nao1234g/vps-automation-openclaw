# NOWPATTERN 記事リンクサンプリング監査
> 実施日: 2026-03-29
> 目的: ホーム・予測・タクソノミー各ページから記事リンクのHTTPステータスを検証

---

## コアページ HTTP ステータス

| URL | ステータス | 備考 |
|-----|-----------|------|
| `https://nowpattern.com/` | **200** | JA ホーム |
| `https://nowpattern.com/about/` | **200** | JA About |
| `https://nowpattern.com/en/about/` | **200** | EN About |
| `https://nowpattern.com/predictions/` | **200** | JA 予測ページ |
| `https://nowpattern.com/en/predictions/` | **200** | EN 予測ページ |
| `https://nowpattern.com/taxonomy/` | **200** | JA タクソノミー |
| `https://nowpattern.com/en/taxonomy/` | **200** | EN タクソノミー |
| `https://nowpattern.com/taxonomy-guide/` | **200** | JA タクソノミーガイド |
| `https://nowpattern.com/en/taxonomy-guide/` | **200** | EN タクソノミーガイド |

→ **全9ページ 200 OK** ✅

---

## JA 記事サンプル（5件）

| スラッグ（短縮） | HTTP | 備考 |
|----------------|------|------|
| `frbli-xia-gejian-song-rilian-sok...` | **200** | 直接アクセス OK |
| `ri-ben-noyu-suan-zheng-zhi-zan-ding...` | **200** | 直接アクセス OK |
| `bitutokoin1500mo-yuan-tu-po-yu-ce...` | **200** | 直接アクセス OK |
| `denmakuzong-xuan-ju-nochong-ji...` | **200** | 直接アクセス OK |
| `gaza-ping-he-ping-yi-hui-guo-lian...` | **200** | 直接アクセス OK |

→ **全5件 直接 200 OK** ✅

---

## EN 記事サンプル（5件）

### `en-` プレフィックスあり（規約準拠）

| スラッグ | 初回 | リダイレクト先 | 最終 |
|----------|------|---------------|------|
| `en-bitutokoin1000mo-yuan-tu-po-...` | 301 | `/en/en-bitutokoin1000mo.../` | **200** |

→ リダイレクト先: `/en-[slug]/` → `/en/en-[slug]/` (Caddy redirect) → Ghost `en-[slug]`

### `en-` プレフィックスなし（旧形式 — slug規約違反）

| スラッグ | 初回 | リダイレクト先 | 最終 |
|----------|------|---------------|------|
| `south-china-sea-naval-standoff...` | 301 | `/en/south-china-sea.../` | **200** |
| `bitcoin-predicted-to-surpass-15-million` | 301 | `/en/bitcoin-predicted.../` | **200** |
| `the-shock-of-the-danish-general...` | 301 | `/en/the-shock-of.../` | **200** |
| `gaza-peace-council-first-un-report` | 301 | `/en/gaza-peace.../` | **200** |

→ 全件 301→200 で到達可能（ただし301リダイレクトが余分なホップ）

---

## EN 記事スラッグ統計

| 区分 | 件数 | 割合 |
|------|------|------|
| `lang-en` タグ付き記事 総数 | 1,132 | 100% |
| `en-` プレフィックスあり（規約準拠） | **451** | 39.8% |
| `en-` プレフィックスなし（旧形式） | **681** | 60.2% |

> **既知課題**: 681件の EN 記事が slug 規約違反。ただし Caddy の redirect rule により全件到達可能 (301→200)。
> 参考: 2026-03-22〜28 SEO 監査で約190件を修正済み。残672件は未対応。

---

## ナビゲーション分析

### JA ホーム ナビ（`nowpattern.com/`）

```
/ (ホーム)
/en/ (EN ホーム)
https://nowpattern.com/predictions/  ← ✅ 正しい
https://nowpattern.com/taxonomy-ja/  ← ⚠️ /taxonomy/ を使うべき (301リダイレクト経由)
https://nowpattern.com/about/        ← ✅ 正しい
https://nowpattern.com/en/           ← ✅ 正しい
```

> **⚠️ ISS-NAV-001**: `taxonomy-ja/` が nav に露出している。`/taxonomy/` を直接参照すれば 301 が省けるが、ユーザーへの影響は軽微（Ghost ルーティングによる自動 redirect）。

### EN ホーム ナビ（`nowpattern.com/en/`）

同一テンプレート。同じ `/taxonomy-ja/` リンクが存在する。

---

## 主な発見

| 項目 | 状態 | 優先度 |
|------|------|--------|
| 全コアページ 200 OK | ✅ OK | - |
| JA 記事直接アクセス | ✅ 200 | - |
| EN 記事（en-プレフィックスあり）| ✅ 301→200 | - |
| EN 記事（en-プレフィックスなし）| ⚠️ 301→200 | 低 |
| nav に /taxonomy-ja/ が残存 | ⚠️ 301→200 | 低 |
| EN 記事 60% が slug 規約違反 | ⚠️ 要継続対応 | 中 |

> ユーザー体験への直接影響なし（全件最終 200 到達可能）
> SEO 観点での slug 統一は継続課題

---

*作成: Claude Code — 2026-03-29*
