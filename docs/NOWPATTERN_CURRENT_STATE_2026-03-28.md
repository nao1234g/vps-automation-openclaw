# NOWPATTERN CURRENT STATE — 2026-03-28
> source: current_system_state (SSH確認済み) + current_repo_state
> 作成: 2026-03-28 | 確認方法: SSH/VPS直接確認、Ghost SQLite、prediction_db.json、reader_predictions.db

---

## 1. プラットフォーム基本情報

| 項目 | 値 | 確認方法 |
|------|-----|---------|
| URL | https://nowpattern.com | curl HTTP 200 |
| CMS | Ghost 5.130.6 (CLI 1.28.4) | ghost version |
| ホスティング | ConoHa VPS 163.44.124.123 / Ubuntu 22.04 | SSH |
| リバースプロキシ | Caddy | Server: Caddy ヘッダー |
| DB | SQLite (Ghost CMS) | /var/www/nowpattern/content/data/ghost.db |
| Ghostバージョン | **5.130.6** (6.0ではない) | cat package.json |

---

## 2. コンテンツ状況

| 指標 | 値 |
|------|-----|
| 総published記事数 | 1,374 |
| Draft数 | 88 |
| 日本語 (lang-ja) | 229 |
| 英語 (lang-en) | 1,131 |
| 言語比率 | EN 82% / JA 18% |
| 総タグ数 | 70 |
| 記事生成ペース | ~16件/日 (2026-03-27実績) |
| 生成cron | 3回/日 (23:30/05:30/11:30 JST) |

---

## 3. 予測システム状態

| 指標 | 値 |
|------|-----|
| prediction_db 総件数 | 1,093 |
| status: active | 8 |
| status: open | 5 |
| status: resolving | 1,028 |
| status: resolved | 52 |
| 平均 Brier Score (resolved) | **0.1828** (FAIR水準) |
| hit_rate | 75.7% |
| 弱点カテゴリ | 暗号資産(0.3334 POOR), 経済・貿易(0.4868 POOR) |
| Polymarket マッチ数 | **2件** (Jaccard係数ベース、精度低) |

---

## 4. 読者・会員状況

| 指標 | 値 | 評価 |
|------|-----|------|
| Ghost Members 合計 | 1 | 危機的 |
| 有料会員 | 0 | 収益ゼロ |
| 無料会員 | 1 | |
| reader votes 総数 | 1,099 | |
| ユニーク投票者 | **7人** | 危機的 |
| paid tier 設定 | Nowpattern Premium $9/月 | DBには存在 |
| portal_plans 設定 | ["free"] | **有料プランが非表示** |
| Stripe連携 | 未設定 (stripe_products: 0件) | |

---

## 5. X (Twitter) 自動投稿状況

| 指標 | 値 | 評価 |
|------|-----|------|
| 今日の投稿数 | **1/100** | 完全停止 |
| DLQ件数 | **79件** | |
| DLQ内フォーマット | REPLY 100% | |
| エラー内訳 | 403: 75件 / 429: 4件 | |
| 403エラー理由 | "Quoting this post is not allowed because you have not been mentioned" | X API仕様 |
| 投稿cron | */5 * * * * (5分毎) | 稼働中だが全失敗 |
| DLQ retry cron | */30 * * * * | 稼働中だが全失敗 |

---

## 6. サービス稼働状況

| サービス | 状態 |
|---------|------|
| Ghost CMS | OK |
| NEO-ONE | OK |
| NEO-TWO | OK |
| NEO-GPT | OK |
| openclaw-umami | Up 13 days |
| openclaw-substack-api | Up 7 days (healthy) |
| openclaw-n8n | Up 13 days (healthy) |
| openclaw-postgres | Up 13 days (healthy) |
| reader_prediction_api | OK (port 8766, v2.0.0) |

---

## 7. UI・UX状態

### 主要ページHTTPステータス（全200OK）
- / (ホーム): 200
- /predictions/: 200
- /en/predictions/: 200
- /en/about/: 200
- /about/: 200
- /taxonomy/: 200
- /en/taxonomy/: 200

### predictions ページ UI要素チェック
| 要素 | JA | EN |
|------|----|----|
| 言語切り替え | ✅ | ✅ |
| reader vote widget | ✅ | ✅ |
| np-tracking-list ID | ✅ | ✅ |
| **np-scoreboard ID** | **❌ 欠落** | **❌ 欠落** |
| **np-resolved ID** | **❌ 欠落** | — |
| Brier Score表示 | ✅ | ✅ |
| filter/category | ✅ | ✅ |
| hreflang | ✅ | ✅ |
| canonical | ✅ | ✅ |

### ページサイズ・パフォーマンス
| ページ | サイズ | TTFB | gzip |
|--------|-------|------|------|
| ホーム | 125 KB | 0.42s | ❌ 非圧縮 |
| /predictions/ | 282 KB | 0.19s | ❌ 非圧縮 |
| /en/predictions/ | 320 KB | 0.20s | ❌ 非圧縮 |

---

## 8. スキーマ・AIアクセシビリティ

| 確認項目 | 状態 |
|---------|------|
| ホーム: WebSite schema | ✅ |
| ホーム: NewsMediaOrganization | ✅ |
| 記事: Article schema | ✅ (author/datePublished/dateModified全あり) |
| 記事: NewsArticle + SpeculativeArticle | ✅ |
| 予測ページ: Dataset schema | ❌ **欠落** |
| 予測ページ: FAQ schema | ❌ **欠落** |
| EN /predictions/: Article schema (不適切) | ⚠️ WebPage/CollectionPageが正しい |
| llms.txt | ✅ HTTP 200 (内容充実) |
| **llms.txt EN URL誤り** | **❌ en-predictions/ → en/predictions/** |
| **llms-full.txt** | **❌ 301→404 (壊れている)** |
| robots.txt | ✅ GPTBot/ClaudeBot不ブロック |
| sitemap.xml | ✅ (pages/posts/authors/tags) |

---

## 9. 現在の強み

1. **1,374記事の規模** — EN 1,131記事は英語圏のAIクローラーに対して十分な量
2. **予測トラックレコード** — 52件解決済み、Brier 0.1828 (FAIR) — 世界的に希少な日本語予測メディア
3. **Deep Pattern v6.0フォーマット** — 全np-マーカー完備、構造化コンテンツ
4. **バイリンガル対応** — JA/EN同時公開、hreflang/canonical正常
5. **自動検証システム** — prediction_auto_verifier.py稼働中
6. **llms.txt充実** — AIエージェントへの詳細な指示書が存在
7. **reader_prediction_api v2.0** — 投票インフラ稼働中

---

## 10. 現在の弱み・ボトルネック

1. **X投稿完全停止** — REPLY 403で1/100投稿
2. **収益ゼロ** — 0有料会員、Ghost portal_plans未設定
3. **読者エンゲージメント極小** — 7人しか投票していない
4. **gzip非圧縮** — 無駄な帯域消費
5. **np-scoreboard/np-resolved ID欠落** — デザインシステム違反
6. **llms.txt URL誤り** — AIアシスタントが間違ったURLを案内
7. **Polymarketマッチ2件のみ** — 市場比較データが弱い
8. **Ghost 5.130.6** — 6.0のActivityPub/ネイティブアナリティクスが使えない
9. **Dataset/FAQ schema欠落** — AIO掲載率に損失
