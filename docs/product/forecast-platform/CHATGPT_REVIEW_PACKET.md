# CHATGPT_REVIEW_PACKET.md — ChatGPT 向けレビューパケット

> 作成: 2026-03-29 | ステータス: READY FOR REVIEW
> 設計者: Claude Code (claude-sonnet-4-6) + Naoto
> このパケットは「ChatGPT に渡して往復しやすい成果物」として設計されている。

---

## コンテキスト: Nowpatternとは

nowpattern.com は日本語×英語バイリンガルの「予測オラクル・プラットフォーム」。
ニュース記事に紐づく構造化予測（1097件）を保有し、Brier Score で精度を追跡している。

**現在の状態（facts）**:
- 記事数: 1331件 published（JA:211 + EN:1104）+ 17件 draft
- 予測DB: 1097件、avg Brier Score 0.1828（FAIR水準）
- 読者投票: 1121票中 1115票が AI プレイヤー。**実人間は約6票のみ**
- 既存インフラ: 投票API(port 8766) + Brier 計算 + leaderboard + top-forecasters + Ghost Members（1名）

---

## 設計済み内容（確定）

### 1. 参加最小単位
既存の確率投票スライダー（シナリオ選択 + 5〜95%、5刻み）を最小参加単位とする。
理由: 登録不要・Brier Scoreable・既に実装済み。

### 2. Counter-Forecast（対抗予想）の設計方針
「同一 prediction_id・同一 resolution_question に対して、異なる確率を投票する」形式を採用。
コメント型・派生予想型は不採用（比較不可能・解決基準がずれるため）。

```
実装: reader_votes テーブルに explanation TEXT カラムを追加（additive migration）
     ALTER TABLE reader_votes ADD COLUMN explanation TEXT;
```

### 3. スコアリング
- 公開: **Brier Index** (1-√Brier)×100% ← 0-100%スケールで一般ユーザーに理解しやすい
- 非公開: raw Brier（内部計算に使用）
- Log Score は非公開（過剰ペナルティで参加を萎縮させる）
- 最小表示条件: N≥5 の resolved 予測（Phase 1 は N≥1 に緩和予定）

### 4. タイトルシステム（Phase 2）
| タイトル | 条件 |
|---------|------|
| Forecaster | 参加すれば全員 |
| Analyst | Brier Index top 20%, N≥10 |
| Oracle | Brier Index top 5%, N≥50 |

### 5. 解決通知 = 最高ROIのループクローザー
UUID → email bridge（Ghost Members）→ 解決時メール送信が最優先。
ただし Phase 1.5（1000人到達後）に実装予定。

### 6. 収益化ラダー
Phase 1（今）: 完全無料
Phase 2: Ghost Members Free（名前付きプロフィール）+ Paid $9-19/月（高度分析・通知・トーナメント）
Phase 3: Enterprise API $99-499/月 + Superforecaster認定

### 7. Week 1 実装タスク（低リスク・即実行）
1. `ALTER TABLE reader_votes ADD COLUMN explanation TEXT;` — VPS 実行済み予定
2. `reader_prediction_api.py` VoteRequest に `explanation: Optional[str] = None` 追加
3. `prediction_page_builder.py` に FEATURE_FLAGS 追加（全フラグ False）
4. Leaderboard Ghost ページ作成（Static HTML + /reader-predict/top-forecasters）

---

## ChatGPT に聞きたいこと（未解決論点）

### Q1: leaderboard の AI 表示方針 ← 最重要

現在 `neo-one-ai-player` が投票の 99.5% を占める。
3つのオプションについて意見を聞かせてほしい:

- **A) AI を除外**: 人間のみランキング。クリーンだが「倒す相手」が消える
- **B) AI を参加させる**: "AIを倒せ" ナラティブが維持できる。ただし AIが圧倒的に上位に来る可能性
- **C) 別レーン表示**: AIレーン + 人間レーン。"AI vs 人間" の対決図式を可視化

**質問**: どのオプションが最も参加モチベーションを高めるか？また他のプラットフォームでの成功事例はあるか？

---

### Q2: Brier Index への切り替えタイミングと見せ方

現在のスコアボードは raw Brier を表示している（HTML ID/CSS クラスは凍結済み）。
- Brier Index (1-√Brier)×100% に切り替えたい
- HTML 構造を変えずに計算式だけ変えることは可能（Python側で処理）
- ただし既存ユーザーへの変更説明が必要

**質問**:
1. HTML 構造を変えずに数値だけ変えることの UX 問題はあるか？
2. 既存の Brier 表示との互換性をどう保つか（例: ツールチップ等）

---

### Q3: `rebuttals[]` フィールドと `reader_votes.explanation` の役割分担

prediction_db.json に `rebuttals: []` フィールドが既存（空配列）。
現在の設計:
- `rebuttals`: AI（NEO-ONE/TWO）が生成するカウンター論点を格納
- `reader_votes.explanation`: 読者が自分の投票理由を書く場所

**質問**:
1. この2フィールドの役割分担は適切か？
2. 将来的に両者を統合して「AI論点 vs 読者論点の品質比較」ができる設計にすべきか？
3. rebuttals の活性化（現在 empty）と reader explanation のどちらを先に実装すべきか？

---

### Q4: 1000人到達前に Phase 2 機能を部分実装することのリスク

現在の設計: Phase 2（Ghost Members bridge / 有料ティア）は「1000人到達後」に実装。
しかし Ghost Members のインフラは既に存在している。

**懸念点**: 早期に有料ティアを設定すると、無料ユーザーへの印象が悪くなるか？
**質問**:
1. 投票数が少ない段階で名前付きプロフィール機能（無料）だけを先行リリースするメリット/デメリットは？
2. 「1000人の壁」をどう越えるか？最初のトラフィックをどこから引くか？

---

### Q5: 週次 X 投稿のフォーマット

Leaderboard 結果を毎週月曜に X (@nowpattern) で投稿したい。
現在の X 投稿ルール: X Premium 加入済み（最大25,000文字）、4フォーマット混在

**提案フォーマット案**:
```
📊 今週の予測バトル結果

🥇 [Forecaster #XXXX]: Brier Index 84.2% (N=7)
🥈 [Forecaster #YYYY]: Brier Index 78.5% (N=5)
🤖 AI (neo-one): Brier Index 57.3% (N=1097)

人間がAIを上回っています！
あなたも予測に参加 → nowpattern.com/predictions/

#Nowpattern #予測 #BrierScore
```

**質問**: このフォーマットは参加意欲を高めるか？改善点があれば教えてほしい。

---

## 実装済みインフラのサマリー（触るな・壊すな）

| コンポーネント | 場所 | 状態 |
|---|---|---|
| Anonymous UUID 投票 | reader_prediction_api.py / reader_votes テーブル | ✅ 稼働中 |
| Brier Score 計算 | reader_prediction_api.py (per-voter) | ✅ 稼働中 |
| AI vs Readers leaderboard | GET /reader-predict/leaderboard | ✅ 稼働中 |
| Top-forecasters ranking | GET /reader-predict/top-forecasters | ✅ 稼働中 |
| My-tracker / My-stats | GET /reader-predict/my-tracker/{uuid} | ✅ 稼働中 |
| prediction_db.json (1097件) | /opt/shared/scripts/prediction_db.json | ✅ 稼働中 |
| rebuttals field | prediction_db.json 各予測 | ✅ スキーマあり（空配列） |
| probability_history + OTS | prediction_db.json 各予測 | ✅ 稼働中 |
| Ghost Members インフラ | ghost.db / members テーブル | ✅ 存在（1名のみ） |
| prediction_tournament.py | 四半期トーナメント | ✅ 稼働中（quarterly） |

---

## 未実装のギャップ（Week 1 で埋める予定）

| ギャップ | 優先度 | 実装難易度 |
|---------|--------|-----------|
| reader_votes.explanation フィールド | **最高** | 低（additive migration） |
| VoteRequest explanation 対応 | **最高** | 低 |
| FEATURE_FLAGS in prediction_page_builder.py | 高 | 最低 |
| Leaderboard Ghost ページ | 高 | 中 |
| Brier Index 表示切り替え | 中 | 低 |
| UUID → email bridge | 中 | 中（Phase 1.5） |
| 解決時通知 | 中 | 中（Phase 1.5） |

---

## 参考: 設計に参照した外部事例

| プラットフォーム | 参照した機能 |
|----------------|------------|
| Metaculus | 確率スライダー、medals システム、コメント統合 |
| Good Judgment Open | Superforecaster タイトル（稀少性）、3段階認定 |
| Manifold Markets | 季節リーグ、プレイマネー方式 |
| Google 内部予測市場 | Counter-forecast UI（唯一の先例） |
| Polymarket | コメント・論点の重要性（エンゲージメントの源泉） |

---

*最終更新: 2026-03-29 | 次レビュー: ChatGPT → OPEN_QUESTIONS.md Q1〜Q5 回答後*
