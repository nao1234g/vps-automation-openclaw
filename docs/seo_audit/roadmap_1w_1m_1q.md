# Nowpattern SEO + Growth ロードマップ
> 作成日: 2026-03-27 | 統合: SEO監査 + 競合調査 + 世界実装例
> 基準: Metaculus/Polymarket/Kalshi/Good Judgment を参照した世界標準ロードマップ

---

## 今週 (3/27 - 4/3): 致命的障害の除去

### P0: 緊急 (本日中に判断必要)

| # | タスク | 担当 | リスク | 承認 |
|---|---|---|---|---|
| W-1 | **EN予測ページ ページネーション (50件/ページ)** | NEO-ONE | LEVEL 2 | Naoto承認必要 |
| W-2 | **xmrig 完全除去確認** | Naoto (手動) | 0 | - |
| W-3 | **Google Safe Browsing 確認** | Naoto | 0 | - |

### P1: 今週中

| # | タスク | 担当 | 工数 | 期待値 |
|---|---|---|---|---|
| W-4 | 著者プロフィール作成 + 全記事紐付け | NEO-ONE | 4h | E-E-A-T 修復 |
| W-5 | /tournament/ 500エラー 根本修正 | NEO-ONE | 2-4h | コンテンツ復旧 |
| W-6 | ENホームタイトル "(Page 1)" 修正 | NEO-ONE | 2h | 検索結果改善 |
| W-7 | Brier Score バッジ → /predictions/ ヒーロー追加 | NEO-ONE | 1h | 差別化信号 |
| W-8 | implemented_low_risk_fixes.md に Fix 4 追記 | local-claude | 30min | ドキュメント整合 |

### 技術修正詳細

**W-1: EN予測ページネーション (LEVEL 2 — 承認後実装)**
```python
# 実装案A (最速): prediction_page_builder.py --page オプション追加
# /en/predictions/ → ?page=1 (1-50件), ?page=2 (51-100件)
# TTFB: 9.48s → 推定 0.5-1.0s
# Size: 5.27MB → 推定 300-500KB
```

**W-4: 著者プロフィール設定**
```bash
# Ghost Admin で著者作成後、API で全記事に紐付け
# 著者名: "Nowpattern AI Research"
# bio: "Brier Score 0.1776の予測精度 (1,006件)"
```

---

## 今月 (4月): 成長加速フェーズ

### 技術SEO

| # | タスク | 工数 | KPI変化予測 |
|---|---|---|---|
| M-1 | 個別予測 permalink 実装 | 5日 | +1,006 SEOページ |
| M-2 | schema.org Dataset 実装 | 1日 | AI Overview採用率向上 |
| M-3 | hreflang 自動注入 Webhook 化 | 2日 | 新記事 100% hreflang |
| M-4 | sitemap.xml からタグページ除外 | 1日 | クロールバジェット最適化 |
| M-5 | JA ホーム TTFB 改善 (414ms → 300ms以下) | 2h | CWV Good判定 |
| M-6 | カテゴリ別予測サブページ設計 | 3日 | ロングテールKW獲得 |

**M-1: 個別予測 permalink 詳細**
```
現在: /predictions/#np-2026-0042 (アンカーリンク)
変更後: /predictions/np-2026-0042/ (独立URL)
        /en/predictions/np-2026-0042/ (EN版)

SEO効果:
- 1,006件 × 2言語 = 最大2,012個の独立インデックスページ
- 各ページが「[イベント名] 予測」ロングテールKWをターゲット
- 解決後: "did [X] happen" で再インデックス (3ステージSEOライフサイクル)
```

### コンテンツ戦略

| # | タスク | 工数 | KPI変化予測 |
|---|---|---|---|
| M-7 | 解決投稿 自動化 (X + Ghost記事更新) | 2日 | 的中事例のバックリンク獲得 |
| M-8 | GSC 登録 + 基準値記録 (Naoto実施) | 1h | 測定基準確立 |
| M-9 | "トラックレコード" キーワードページ作成 | 1日 | 低競争KWランキング |
| M-10 | EN/JA 記事比率モニタリング開始 | 設定のみ | スケールドコンテンツ誤検知防止 |

### 予測プラットフォーム

| # | タスク | 工数 | KPI変化予測 |
|---|---|---|---|
| M-11 | 読者投票リーダーボード TIER 1 (個人スコアページ) | 3日 | リテンション向上 |
| M-12 | X Poll + 予測連動投稿 フォーマット確立 | 1日 | X エンゲージメント向上 |
| M-13 | Polymarket Delta → 速報記事 自動化 | 2日 | タイムリーコンテンツ |

---

## 今四半期 (2026 Q2: 4-6月): モートの確立

### マネタイズ開始

| # | タスク | 達成条件 | 収益試算 |
|---|---|---|---|
| Q-1 | Ghost Members 導入 (Stripe接続) | 月間UU 3,000+ かつ Brier ≤ 0.20 | $810-4,500/月 |
| Q-2 | 週次「オラクルニュースレター」開始 | - | ブランド構築 |
| Q-3 | Substack プレミアム版 (48h先行) | Ghost Members 50人以上 | +$270-1,350/月 |

**Ghost Members 価格設定:**
```
Free tier: 予測閲覧 + 投票 (匿名)
Paid tier: $9/月 / $89/年
  特典:
  - 解決通知メール
  - 個人 Brier Score ページ
  - 48時間先行公開 (週1-2本ディープレポート)
  - "サポーター" バッジ
```

### プラットフォーム拡張

| # | タスク | 工数 | 期待値 |
|---|---|---|---|
| Q-4 | 「第1回 Nowpatternオラクルコンペ」開催 | 1ヶ月準備 | SNS拡散 + ユーザー獲得 |
| Q-5 | OTSタイムスタンプ バッジ表示 (改ざん証明) | 2日 | 信頼性差別化 |
| Q-6 | カテゴリ別予測サブページ 実装 | 1週間 | SEOカバレッジ拡大 |
| Q-7 | Brier Score カテゴリ別 公開 | 1日 | 弱点/強みの透明化 |

**Q-4: オラクルコンペ設計案**
```
名称: 「第1回 Nowpatternオラクルコンペ 2026」
参加: 無料、匿名OK (localStorage UUID)
期間: 3ヶ月 (例: 7/1 - 9/30 2026)
賞金: 5,000円相当 × 3名 (Ghost Membersプレミアム1年)
評価: Brier Score (同じ基準で公平)
効果: X拡散 + 予測参加者が読者化
参照: Bridgewater × Metaculus 2026 ($30,000 prize pool)
```

### SEO 継続施策

| # | タスク | 工数 | 期待値 |
|---|---|---|---|
| Q-8 | 機関向け公開APIドキュメント作成 | 3日 | B2B開拓準備 |
| Q-9 | PWA 化 (プッシュ通知対応) | 1週間 | モバイルエンゲージメント |
| Q-10 | Google AI Overview 最適化コンテンツ | 継続 | AI Overview採用 |

---

## KPI / 効果測定スケジュール

| 時期 | 確認内容 | 目標値 | 手段 |
|---|---|---|---|
| **2週間後 (4/10)** | hreflang エラー数 (GSC) | 0件 | Google Search Console |
| **1ヶ月後 (4/27)** | インデックス数 (GSC) | 1,000件以上 | Google Search Console |
| **1ヶ月後 (4/27)** | EN予測TTFB | < 1.0s | curl timing |
| **2ヶ月後 (5/27)** | 個別予測ページのインデックス | 500件以上 | GSC Coverage |
| **3ヶ月後 (6/27)** | 月間クリック数 / 表示回数 | 基準値比 +30% | GSC Performance |
| **3ヶ月後 (6/27)** | 読者投票参加者 | 500件以上 | reader_predictions.db |
| **6ヶ月後 (9/27)** | Ghost Members 購読者 | 50人以上 | Ghost Admin |
| **6ヶ月後 (9/27)** | 月間収益 | $450以上 | Stripe Dashboard |

---

## 競合ベンチマーク (目標値の根拠)

| 指標 | Nowpattern現在 | Nowpattern目標 | Metaculus | Polymarket |
|---|---|---|---|---|
| Brier Score | 0.1776 | **0.15** (6ヶ月) | 0.084 (elite) | N/A |
| 予測件数 | 1,006 | 2,000 (12ヶ月) | 60,000 | 数万 |
| 月間訪問者 | 不明 | 5,000 (3ヶ月) | 2M | 17.1M |
| 収益 | $0 | $450/月 (6ヶ月) | グラント中心 | 手数料 |
| 言語 | JA + EN | JA + EN | EN only | EN only |

**Nowpatternのユニークポジション:**
JA+EN バイリンガル × キャリブレーション × 1,006件記録 =
世界に存在しない空白市場

---

*作成: 2026-03-27 | 統合: SEO監査 + 競合調査 (Metaculus/Polymarket/Kalshi/Good Judgment/Bridgewater) + Google E-E-A-T 2026政策 + Substack/The Information マネタイズデータ*
