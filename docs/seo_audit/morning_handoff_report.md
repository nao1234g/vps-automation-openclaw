# Nowpattern SEO監査 — 朝次ハンドオフレポート
> 作成日: 2026-03-27 | 担当: local-claude (SEO Audit Session 2日目)
> 対象: Naoto + NEO-ONE + NEO-TWO

---

## 🎯 TL;DR (30秒で読む)

**このセッションで完了したこと:**
1. ✅ 全タグページ (`/tag/*`) noindex 拡張 → 59件全カバー確認済み
2. ✅ CWV / PageSpeed 測定完了 → EN予測ページが5.27MB/9.48秒の致命的問題を発見
3. ✅ 世界3エージェントによる競合調査完了 (Metaculus/Polymarket/Google AI policy/マネタイズ)
4. ✅ 全提案書 + ロードマップ作成完了

**Naotoが今すぐ判断すべきこと:**
- 🔴 **EN予測ページネーション実装の承認** (LEVEL 2)
- 🔴 **xmrig 除去状態確認** (VPSで `ps aux | grep xmrig` 実行)
- 🟡 **Google Search Console に nowpattern.com 登録** (まだなら)

---

## このセッションで実施した修正

### Fix 4: 全タグページ noindex 拡張 ✅ 完了・検証済み

**内容:** `/etc/caddy/Caddyfile` の `@internal_tags` を拡張
```caddy
# 変更前: 特定パターンリスト
@internal_tags path /tag/p-* /tag/event-* /tag/lang-* /tag/deep-pattern/ /tag/nowpattern/ /tag/genre-*

# 変更後: 全タグページを一括カバー
@internal_tags path /tag/*
```

**検証結果:**
```
curl -sI https://nowpattern.com/tag/geopolitics/ | grep -i robots
→ x-robots-tag: noindex, follow ✅
```

**効果:** 59件の全タグページがnoindex化。クロールバジェット最適化。

---

## 発見された重要問題

### 🔴 Problem 1: EN予測ページ 5.27MB / TTFB 9.48秒

**測定値:**
```
URL: https://nowpattern.com/en/predictions/
TTFB:  9,480ms  (目標: < 800ms)
Size:  5,269,893 bytes (5.27MB)
Divs:  31,335個
```

**根本原因:** `prediction_page_builder.py` が 1,006件全予測を単一 HTML に書き出している

**Core Web Vitals 推定:**
```
LCP: ~12-15秒 (目標: < 2.5秒) → POOR
TTFB: 9.48秒 (目標: < 0.8秒) → POOR
→ Google SEO 評価: 致命的欠陥ページ
```

**対照 (JA予測ページ):** TTFB 146ms / 340KB → ✅ 正常
理由: JA予測は件数が少ない or 別の生成ロジック

**修正案:**
```python
# 案A (最速・2日): URLパラメータページネーション
/en/predictions/?page=1 → 50件ずつ
prediction_page_builder.py に --page オプション追加

# 案B (中期・1週間): カテゴリ別サブページ
/en/predictions/geopolitics/ → 地政学予測
/en/predictions/economics/   → 経済予測
(SEO効果が高い)

# 案C (最優秀・1ヶ月): lazy load
初回ロード: タイトル + 確率のみ → 詳細はクリックで展開
```

**→ 承認が必要 (LEVEL 2)**

### 🔴 Problem 2: Google E-E-A-T 著者不明問題

**Google 2026 March Core Update** の核心:
- 「著者不明のAI記事」= Scaled Content Abuse として低評価
- Nowpatternは現在全記事が著者不明 または AI著者

**修正 (無料・半日):**
```
1. Ghost Admin → 著者「Nowpattern AI Research」作成
   bio: "Brier Score 0.1776の予測精度 (1,006件ベース)"
2. Ghost Admin API で全記事に著者を紐付け
3. Naoto のプロフィールも著者として追加
```

### 🟡 Problem 3: /tournament/ 500エラー

- Ghost DB では `published` + `public` で存在確認済み
- Ghostのテンプレートレンダリングエラーが原因と推定
- 調査コマンド: `journalctl -u ghost-nowpattern.service | grep -i tournament`

### 🟡 Problem 4: ENホームページ「(Page 1)」タイトル

- `<title>Nowpattern (Page 1)</title>` が検索結果に表示
- Ghost テーマ `default.hbs` の修正で対処可能

---

## 競合調査サマリー (3エージェント調査結果)

### 予測プラットフォーム市場

| プラットフォーム | 月間訪問 | 収益/評価額 | Brier Score |
|---|---|---|---|
| Polymarket | **17.1M** | $9B評価 | N/A (市場型) |
| Kalshi | - | **$22B評価、$260M収益/年** | N/A |
| Metaculus | ~2M | グラント ($5.5M/年) | **0.084 (EXCELLENT)** |
| **Nowpattern** | 不明 | **$0** | **0.1776 (FAIR)** |

### Google AI Policy 2026

- March 2026 Core Update: 50-500記事/日のAIコンテンツを "Scaled Content Abuse" として標的
- E-E-A-T 2026: Experience が #1 シグナル → Brier Score が武器になる
- **ClaimReview スキーマ: Google が2025年に非推奨化** → Article + Dataset に移行必要
- EN/JA比率 5:1 は "翻訳規模" 検出のリスクあり

### マネタイズ世界実績

| モデル | 収益 | 適用可能時期 |
|---|---|---|
| Substack 有料 ($9/月) | 1,000人×3%×$9 = $270/月 | 今すぐ可能 |
| Ghost Members | 3,000人×3%×$9 = $810/月 | UU 3,000人達成後 |
| B2B API | $99-499/月/企業 | 1年後 (実績積み上げ後) |
| 機関向けレポート | $500-2,000/件 | 1年後 |

**重要:** Metaculus はグラント中心で収益化が弱い。Substack Newsletter × Ghost Members の組み合わせがNowpatternに最適なモデル。

---

## NEO-ONEへの指示

NEO-ONE が次にやること (優先順位順):

```
1. 著者プロフィール作成 + 全記事紐付け
   → Ghost Admin API を使用
   → 著者名: "Nowpattern AI Research"
   → 全1,342記事に紐付け

2. /tournament/ 500エラー調査
   → journalctl で Ghost エラーログ確認
   → テーマファイルのレンダリングエラーを特定・修正

3. ENホームタイトル "(Page 1)" 修正
   → Ghostテーマ default.hbs 確認・修正

4. Brier Score バッジ → /predictions/ ページ追加
   → prediction_page_builder.py の JA版ヒーローセクションに追記

(Naoto承認後:)
5. EN予測ページネーション実装 (案A: --page オプション)
```

---

## 完成したドキュメント一覧

| ファイル | 内容 | 作成日 |
|---|---|---|
| `implemented_low_risk_fixes.md` | Fix 1-3 実施記録 (Fix 4 追記必要) | 2026-03-26 |
| `indexing_crawl_diagnosis.md` | インデックス・クロール診断 | 2026-03-26 |
| `hreflang_architecture.md` | hreflang 3層設計書 | 2026-03-26 |
| `quality_and_trust_risk_map.md` | 品質リスクマップ | 2026-03-26 |
| `search_console_current_state_report.md` | GSC確認ガイド | 2026-03-26 |
| `template_level_prevention_plan.md` | テンプレートレベル予防プラン | 2026-03-26 |
| `final_priority_recommendations.md` | 最終優先度レコメンデーション | 2026-03-26 |
| `pagespeed_cwv_report.md` | CWV/PageSpeed 計測レポート | **2026-03-27** |
| `roadmap_1w_1m_1q.md` | 今週/今月/今四半期ロードマップ | **2026-03-27** |
| `morning_handoff_report.md` | このファイル | **2026-03-27** |

---

## 測定値ログ (CWV 参照用)

```
測定日時: 2026-03-27
測定場所: VPS内部 (163.44.124.123)

テンプレート     DNS   SSL    TTFB     Total   Size    評価
JA ホーム      1ms   66ms   414ms    423ms   128KB   ⚠️ 要改善
EN ホーム      2ms   46ms   309ms    314ms   110KB   ⚠️ ギリギリGood
JA 記事       1ms   62ms   215ms    222ms   144KB   ✅ 良好
EN 記事       1ms   40ms   215ms    225ms   142KB   ✅ 良好
JA 予測       1ms   63ms   146ms    151ms   340KB   ✅ 良好
EN 予測       1ms   35ms  9,480ms  9,544ms 5,270KB  🔴 致命的
```

---

*作成: 2026-03-27 | SEO監査セッション2日目完了 → 朝次ハンドオフ*
