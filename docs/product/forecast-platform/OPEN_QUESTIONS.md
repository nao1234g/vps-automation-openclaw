# OPEN_QUESTIONS.md — 未解決論点

> 作成: 2026-03-29 | ステータス: ChatGPT / Naoto レビュー待ち
> ここにある論点が解決されるまで、関連するフィーチャーの実装をブロックする。

---

## OQ-001: Leaderboard の「AI」はどう扱うか ← 最重要

**論点**: 現在 `neo-one-ai-player` が 1115/1121 票を持っている。
- オプション A: AI を leaderboard から除外し「人間のみ」ランキングにする
- オプション B: AI をそのまま参加させ「AI vs 人間」の比較を可視化する（"AIを倒せ"ナラティブ）
- オプション C: AI を別カテゴリとして表示する（AIレーン + 人間レーン）

**Naoto への質問**: AI は leaderboard に表示すべきか？「倒す相手」として見せるほうが参加意欲が高まるか？

**影響範囲**: leaderboard ページの実装方針、CTAコピー

---

## OQ-002: 対抗予想に「理由」は必須か任意か

**論点**: `explanation TEXT` フィールドを任意にするか必須にするか。
- 任意: 摩擦が低い。精度追跡のみ目的なら理由は不要
- 必須（100文字以上）: 対抗予想の質が上がる。将来的に AI がリバタル学習できる

**研究データ**: Metaculus は確率投票でコメント任意。コメント投稿者の再訪問率が2倍（外部リサーチより）

**暫定決定**: 任意（max 200文字）。必須化は Phase 2 で検討。

---

## OQ-003: UUID の永続化はどうするか

**論点**: 現在のシステムは localStorage UUID のみ。
- ブラウザクリア → UUID リセット → トラックレコード消失
- シークレットモード → 別 UUID → 精度追跡不可
- これを解決しないとリーダーボードが機能しない

**解決策候補**:
- A: Ghost Members bridge（email登録でUUID固定）→ Phase 1.5
- B: ローカルストレージのみで我慢（Phase 1）
- C: Cookie ではなくデバイスフィンガープリント（プライバシー問題あり）

**暫定決定**: Phase 1 は localStorage で我慢。Phase 1.5 で Ghost Members bridge を実装。

---

## OQ-004: Brier Index vs 生 Brier Score の表示方針

**論点**: 現在 prediction_page_builder.py はスコアボードに raw Brier Score を表示。
- raw Brier: 0.0=完璧、1.0=最悪 → 一般ユーザーには非直感的
- Brier Index: 100%=完璧、0%=最悪 → 直感的だが既存表示を変更する必要あり

**解決方針**: /predictions/ の公開表示は Brier Index に切り替え。内部計算は raw Brier を維持。

**ブロッカー**: prediction_page_builder.py の HTML クラス/IDを変更すると凍結ベースラインに抵触。計算式変更のみか、HTML変更も含むか確認が必要。

**ChatGPT への質問**: 既存の HTML 構造を変えずに Brier Index を表示する最もシンプルな方法は？

---

## OQ-005: 「同一 voter_uuid = 1票制限」の緩和はするか

**論点**: 現在 reader_votes に `UNIQUE(prediction_id, voter_uuid)` 制約あり。
- 1ユーザーが同じ予測を複数回「更新」できない
- Metaculus は更新可能（確率の変更を時系列で記録）

**決定候補**:
- A: UNIQUE制約のまま（変更しない）→ 最初の投票が記録
- B: UPDATE を許可し、probability_history に変更履歴を追記

**影響**: option B は probability_history の設計変更が必要（prediction_db.json 側の仕組みとは別に reader_votes 側の履歴管理）

---

## OQ-006: Polymarket との比較表示はどうするか

**論点**: prediction_db.json には `market_consensus.probability` (Polymarket) が入っている。
- 「Nowpattern: 70% / Polymarket: 65% / 読者: 58%」という3者比較が可能
- Polymarket データの鮮度（daily sync vs realtime）

**現状**: `polymarket_sync.py` が日次 cron で動いている（21:30 UTC）。データ鮮度は最大24時間遅れ。

**ChatGPT への質問**: 予測ページに「3者比較」を表示するとき、データ鮮度の差異をユーザーにどう明示すべきか？

---

## OQ-007: 解決済み予測のリーダーボード表示期間

**論点**: 解決済み N = 52 件（全 1097 件中）。
- 現在はほとんどが `resolving` ステータス（解決日前）
- N≥5 の条件では人間投票者がほぼゼロ（6票しかない）
- Phase 1 の段階では N≥5 条件を n≥1 に緩和すべきか？

**暫定決定**: Phase 1 は表示条件を N≥1 に緩和。N≥5 は Phase 2 で戻す。

---

## OQ-008: 週次 X 投稿の自動化スクリプト

**現状**: X 自動投稿は `x-auto-post.py` が動作中だが leaderboard 専用投稿は未実装。
**必要な確認**: 既存スクリプトを改修するか、新規スクリプトを作成するか。
**影響**: content-rules.md の4フォーマット（LINK/NATIVE/RED-TEAM/REPLY）比率への影響

---

## OQ-009: Counter-Forecast の `rebuttals` フィールドとの関係

**論点**: prediction_db.json に `rebuttals: []` が既存。reader_votes の explanation フィールドと役割が重複する可能性。
- `rebuttals`: AI / NEO が生成したカウンター論点を格納するフィールド（予定）
- `reader_votes.explanation`: 読者が自分の投票理由を書く場所

**暫定方針**: 役割を分離する。`rebuttals` = AI が生成するカウンター論点。`explanation` = 読者の投票理由。同一 prediction_id に対して両方が共存する設計。

**ChatGPT への確認**: この分離は適切か？将来的に rebuttals と reader explanation を統合して「論点の質の比較」ができる設計にすべきか？
