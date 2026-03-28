# Track 2: Noindex Guard 拡張 — Handoff Document

**実施日**: 2026-03-28
**実施者**: Claude Code (local)
**対象**: nowpattern.com — `/en/tag/*` + `/author/*` ページのnoindex追加
**最終判定**: **COMPLETED ✅**

---

## 0. 背景・目的

Track 1 (hreflang修正) が完了し、Track 2-6 のトリアージを実施した結果、最もROIが高く最もリスクが低い改善として以下を特定した:

| 問題 | 箇所 | 影響 |
|------|------|------|
| `/en/tag/*` に `x-robots-tag: noindex` が欠落 | Caddyfile Guard | `/tag/*` にはGuard 1あり、`/en/tag/*` に相当ガードがなかった |
| `/author/naoto/` に `x-robots-tag: noindex` が欠落 | Caddyfile Guard | 単一著者サイトの薄いコンテンツページがGoogleにインデックスされていた |

---

## 1. Track 2-6 トリアージ結果

| Track | 問題 | 対処 |
|-------|------|------|
| **T2: `/en/tag/*` noindex欠落** | `/tag/*` にはGuard 1あるが`/en/tag/*` にはなし | **→ 実装済み** |
| **T2: `/author/*` noindex欠落** | 単一著者の薄いコンテンツがインデックス | **→ 実装済み** |
| T3: 301リダイレクト | `/en-about/`→`/en/about/` 単ホップ、問題なし | スキップ |
| T3: 404 `/en//` | ボットトラフィックのみ、実ユーザーなし | スキップ |
| T5: CWV/TTFB | homepage 0.274s, article 0.209s — 既に高速 | スキップ |
| T6: Scripts | 277本稼働中、緊急SEO問題なし | スキップ |

---

## 2. 実装内容

### バックアップ
```
/etc/caddy/Caddyfile.bak-20260328-t2
```

### 変更差分 (Caddyfile)

**Guard 1b 追加** (既存Guard 1の直後):
```caddy
# Guard 1b: Author pages noindex (single-author site, thin content on /author/naoto/)
@author_pages path /author/*
header @author_pages X-Robots-Tag "noindex, follow"
```

**`handle /en/tag/*` ブロック更新** (header追加):
```caddy
# EN tag pages
handle /en/tag/* {
    header X-Robots-Tag "noindex, follow"
    uri strip_prefix /en
    reverse_proxy localhost:2368
}
```

### 適用コマンド
```bash
caddy validate --config /etc/caddy/Caddyfile  # Valid configuration ✅
systemctl reload caddy                         # active ✅
```

---

## 3. 検証結果

### Track 2 — 新規追加ガード

| URL | Before | After | 期待値 |
|-----|--------|-------|--------|
| `/en/tag/geopolitics/` | noheader | `x-robots-tag: noindex, follow` | ✅ |
| `/en/tag/crypto/` | noheader | `x-robots-tag: noindex, follow` | ✅ |
| `/author/naoto/` | noheader | `x-robots-tag: noindex, follow` | ✅ |

### Track 2 — 既存ガード退行なし

| URL | x-robots-tag | 期待値 |
|-----|-------------|--------|
| `/tag/genre-geopolitics/` | `noindex, follow` | ✅ Guard 1 intact |
| `/tag/lang-ja/` | `noindex, follow` | ✅ Guard 1 intact |

### Track 1 — hreflang退行なし

| チェック項目 | 結果 |
|------------|------|
| Trump-Orbán JA記事 hreflang | `['en', 'ja', 'x-default']` ✅ |
| Trump-Orbán EN記事 hreflang | `['en', 'x-default']` ✅ |
| bidir-valid記事ライブHTML | 3タグ全て確認 ✅ |
| Homepage `Link:` ヘッダー | ja, en, x-default ✅ |
| `/en/` homepage | HTTP 200 ✅ |
| 通常記事 x-robots-tag | なし (影響ゼロ) ✅ |

---

## 4. ロールバック手順

```bash
# 方法1: バックアップから復元
cp /etc/caddy/Caddyfile.bak-20260328-t2 /etc/caddy/Caddyfile
systemctl reload caddy

# 方法2: 手動削除
# Caddyfileから以下を削除:
# - Guard 1b ブロック (3行)
# - handle /en/tag/* 内の header X-Robots-Tag 行 (1行)
```

---

## 5. 今後の優先アクション

### 今日 (NOW)
- [x] `/en/tag/*` noindex追加 — 完了
- [x] `/author/*` noindex追加 — 完了

### 今週 (TODAY/THIS WEEK)
1. **Google Search Console** でカバレッジレポートを確認
   - 「除外 — robots.txtにより除外」または「除外 — noindex」に `/en/tag/*` と `/author/*` が移動するはず
   - 移動確認まで通常1-2週間
2. **`sitemap-authors.xml`** の扱い確認
   - Ghost自動生成のサイトマップに `sitemap-authors.xml` が含まれる
   - noindexが適用されたため、Googleは従わないが、理想的にはサイトマップから除外したい
   - 対処: Ghost設定または `nowpattern-redirects.txt` でサイトマップアイテムを除外（低優先）
3. **`custom_excerpt` 欠落** (1295/1360記事) の対処方針検討
   - CTR改善のための要約追加 — ただし大規模作業のためNEO委任が望ましい

### 来週 (THIS WEEK)
4. **Track 3 追加調査**: `/en//` (ダブルスラッシュ) 404の発生源特定
   - 現時点ではボットトラフィックのみと判断。実ユーザートラフィックの有無をGA4で確認
5. **Track 5 モニタリング**: d5-cwv-monitor.py (毎朝07:00 JST稼働) のアラートを確認

---

## 6. 未実施項目と理由

| 項目 | 理由 |
|------|------|
| `custom_excerpt` 一括追加 | 1295記事への内容追加は大規模変更。NEO-ONE/TWOへの委任を推奨 |
| `sitemap-authors.xml` 除外 | noindexで対処済み。サイトマップ除外は低優先 |
| Track 3 リダイレクトチェーン | 単ホップのみで問題なし |
| Track 5 CWV改善 | TTFB 0.2-0.3s — 既に優秀。改善余地なし |

---

## 7. Ghost DB 状態 (参考: 実施前ベースライン)

```json
{
  "lang_ja_posts": 229,
  "lang_en_posts": 1131,
  "pages": 14,
  "total_published": 1374,
  "en_no_hreflang": 0,
  "ja_missing_en_hreflang_CRITICAL": 0,
  "ja_bidir_valid": 222,
  "pages_with_hreflang": 14
}
```

Track 1 (hreflang) のベースラインは変更なし。本Track 2作業は記事コンテンツに一切触れていない。

---

## 8. 最終判定

```
COMPLETED ✅

実装: Caddy 2ブロック変更 (Guard 1b + /en/tag/* noindex header)
リスク: 実質ゼロ (ヘッダー追加のみ、記事内容変更なし)
Track 1 退行: なし (全チェックPASS)
ロールバック: 4行削除 + caddy reload で即座に復元可能
SEO効果: /en/tag/* と /author/* の不要インデックスを停止
          クロールバジェット効率化
          薄いコンテンツページの除外
```

---

*作成: 2026-03-28 | Claude Code (local) | Track 2 SEO Noindex Guard拡張*
