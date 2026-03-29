# DECISIONS.md — 設計決定ログ

> 作成: 2026-03-29 | ステータス: CONFIRMED
> 調査源: repo reality check (reader_prediction_api.py / prediction_db.json / ghost.db) + 外部リサーチ (Metaculus / GJOpen / Manifold / Google)
> 変更時は末尾 CHANGELOG に追記すること。

---

## D-001: 最小参加単位 = 既存確率投票スライダー

**決定**: 参加の最小単位は「既存の予測カードへの確率投票（シナリオ選択 + 5〜95%スライダー）」とする。

**根拠**:
- `reader_prediction_api.py` に既に実装済み。追加コスト0
- Brier Scoreによる精度追跡が技術的に可能
- Metaculus/GJOpen/Manifestoの全プラットフォームが同様の確率スライダーを最小参加単位として採用（外部リサーチ確認）
- 登録不要・5秒で完了・匿名UUID

**却下した選択肢**:
- ❌ 1クリックYes/No: Brier Scoreにならない。精度追跡不可
- ❌ コメント付き予測: 摩擦が高い。Phase 2以降
- ❌ 完全予測カード作成（Metaculus式）: パワーユーザー専用。Phase 2以降

---

## D-002: Counter-Forecast = 対抗予想型（確率だけ違う、同一問題）

**決定**: 対抗予想は「同一 prediction_id・同一 resolution_question に対して、異なる確率を投票する」形式とする。

**根拠**:
- 外部リサーチ: 既存プラットフォームでこれを綺麗に実装しているところは存在しない → 差別化ポイント
- `reader_votes` テーブルの既存構造が既にこの形式に対応
- Brier Score による精度比較が同一基準で可能
- `rebuttals: []` フィールドが prediction_db.json に既存（空配列）

**却下した選択肢**:
- ❌ コメント型: 精度追跡不可。比較不可能
- ❌ 派生予想型（新しい prediction_id 発行）: 解決基準がずれる。AI vs 人間比較ができない

**実装への接続**: `explanation TEXT` フィールドを reader_votes に追加するだけで最小実装可能

---

## D-003: 対抗予想の期限 = 原則同期限（原予測と同一 oracle_deadline）

**決定**: 対抗予想は原予測と同じ oracle_deadline / resolution_question を共有する。別期限を望む場合は新規予測として登録。

**根拠**:
- 同一解決イベントでのみ Brier Score の比較が意味を持つ
- 「AI vs 人間」の比較が明確になる（同じ問いに対して誰が正確だったか）

---

## D-004: 公開スコアリング体系

**決定**:

| スコア | 公開/非公開 | 表示方法 |
|--------|------------|---------|
| **Brier Index** (1-√Brier)×100% | **公開** | 0〜100% (高いほど優秀) |
| Resolved count (N) | **公開** | N件 |
| Accuracy% (的中率) | **公開** | 補助指標 |
| Raw Brier Score | 内部のみ | 計算に使用、非表示 |
| Log Score | **非公開** | 過剰ペナルティで萎縮させる |
| Calibration curve | Phase 2 | 後回し |

**根拠**: 外部リサーチより Brier Index (1-√Brier)×100% が0〜100%スケールで一般ユーザーに最も理解しやすい（Brier 0.0=100%、Brier 1.0=0%）。Nowpatternの現在の avg Brier 0.1828 → Brier Index ≈ 57%。

**最小表示条件**: N≥5 の resolved 予測がある場合のみ leaderboard に表示（1回の幸運でランキング入りを防ぐ）

---

## D-005: タイトルシステム（3段階）

**決定**: Phase 2 で以下の3段階タイトルを実装する。

| タイトル | 条件 | 備考 |
|---------|------|------|
| **Forecaster** | 1件以上の投票 | デフォルト参加者 |
| **Analyst** | Brier Index top 20%, N≥10 | 実力参加者 |
| **Oracle** | Brier Index top 5%, N≥50 | Nowpatternの最高称号 |

**根拠**: GJOpen の Superforecaster モデル（稀少性が称号の価値を生む）。Metaculus の Medals システム（複数カテゴリで認定）。

---

## D-006: ヒーロー化戦略

**決定**:
- Leaderboard: 上位10人を名前付きで公開（匿名の場合は "Forecaster #XXXXXX"）
- 週次: Leaderboard 結果を X (@nowpattern) でシェア
- ナラティブ: "このAIを倒せる人間はいるか？" / "Forecaster #XXXXが3ヶ月連続AIを上回っている"

**バッジ（Phase 2）**:
```
🎯 Calibration King: avg Brier Index ≥ 90%, N≥10
📊 Volume Forecaster: N≥50 resolved
⚡ Contrarian: 市場確率<30%なのに的中
🔥 Hot Streak: 直近10予測で8以上的中
🌍 Domain Expert: ジャンル別上位10%
🆕 Rising Star: 直近30日でleaderboard急上昇
```

---

## D-007: 解決通知 = 最優先のループクローザー

**決定**: Phase 1.5 の最優先実装は「解決時通知」。UUID → email bridge がその前提条件。

**根拠**: 外部リサーチより「解決通知は全プラットフォームで最もリエンゲージメント効果が高い単一機能」。現在の reader_prediction_api.py には通知パスが存在しない（UUID のみ保存）。

**実装への接続**: Ghost Members bridge (voter_uuid + email 登録フロー) → 解決時メール送信。

---

## D-008: 収益化ラダー

**決定**: Phase 1 → Phase 2 → Phase 3 の段階的展開。

| Phase | 条件 | 手段 | 目標 |
|-------|------|------|------|
| **1 (今)** | 常に無料 | 匿名UUID | 最初の1000人間投票者 |
| **2** | 1000人到達後 | Ghost Members (Stripe連携済み) | 月次定額収入 |
| **3** | 有名化後 | B2B API / Superforecaster認定 | スケールする収益 |

**Ghost Members 価格設定**:
- Free: 名前付きプロフィール + 解決通知
- Paid ($9〜19/月): 高度分析 + 月次レポート + Tournament参加権

---

## D-009: 「AIを倒せ」ナラティブ

**決定**: 参加 CTA のコピーを "Cast your prediction" から "AIに対抗する" / "AIを倒せ" に変更する。

**根拠**: 競争的フレーミングは参加動機を最大化する。現在のUIには目立つ CTA が存在しない（最大の参加ブロッカー）。

---

## CHANGELOG

| 日付 | 変更内容 |
|------|---------|
| 2026-03-29 | 初版。PRD.md + 外部リサーチ (Metaculus/GJOpen/Manifold) から9決定事項を確定 |
