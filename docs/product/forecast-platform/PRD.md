# PRD: Nowpattern 参加型予測プラットフォーム

> 作成: 2026-03-29 | ステータス: DRAFT v1.0
> 設計責任: Claude Code (claude-sonnet-4-6) + Naoto
> ChatGPTレビュー待ち: DECISIONS.md の未解決論点を参照

---

## 0. ミッション

**「誰が一番うるさいか」ではなく「誰が一番当たるか」で序列が決まる予測プラットフォームへ。**

Nowpatternは既に1097件の構造化予測と、Brier Scoreによる精度追跡インフラを持つ。
このPRDは「AIだけが参加している予測市場」を「人間とAIが競い合う公開競技場」に変える設計書である。

---

## 1. 現状のrepo reality（設計の出発点）

### 既存インフラ（触るな・壊すな）

| コンポーネント | 場所 | 状態 |
|---|---|---|
| Anonymous UUID voting | reader_prediction_api.py / reader_votes table | ✅ 稼働中 |
| Brier Score計算 | 同上 (per-voter) | ✅ 稼働中 |
| AI vs Readers leaderboard | GET /reader-predict/leaderboard | ✅ 稼働中 |
| Top-forecasters ranking | GET /reader-predict/top-forecasters | ✅ 稼働中 |
| My-tracker / My-stats | GET /reader-predict/my-tracker/{uuid} | ✅ 稼働中 |
| prediction_db.json (1097件) | /opt/shared/scripts/prediction_db.json | ✅ 稼働中 |
| `rebuttals` field | prediction_db.json 各予測 | ✅ スキーマあり（空配列） |
| probability_history + OTS | prediction_db.json 各予測 | ✅ 稼働中 |
| Ghost Members infrastructure | ghost.db / members table | ✅ 存在（1人のみ登録） |
| prediction_tournament.py | 四半期トーナメント | ✅ 稼働中（quarterly） |

### 重大ギャップ（これが設計の核心）

```
reader_votes table: 1121 rows
  → neo-one-ai-player: 1115票 (99.5%)
  → real humans: 約6票 (0.5%)
```

**インフラは完成。参加者がゼロ。これが唯一の問題。**

### Extension Points（次に繋ぐポイント）

1. `rebuttals: []` → 対抗予想レコードの格納場所として使用可能
2. `reader_votes` table → `explanation` TEXT, `voter_name` TEXT, `ghost_member_id` TEXT カラム追加可能
3. Ghost Members → 既にemail/status/Stripe完備。UUID↔emailのブリッジが未実装
4. `/reader-predict/top-forecasters` → 名前付き表示のためにUUID→name変換が必要

---

## 2. プロダクト設計

### 2.1 参加最小単位: Forecast Card Vote

```
最小参加 = 既存予測カードへの確率投票
  → シナリオ選択 (楽観/基本/悲観)
  → 確率スライダー (5〜95%, 5刻み)
  → 送信 → 匿名UUIDで記録
```

**理由:** 登録不要・5秒で完了・既に動いている。
**ただし:**  投票結果が「匿名のForecaster #ABC123」として記録されるだけでは、ヒーロー化が起きない。
→ Phase 1.5でメール登録=名前付きプロフィールへのアップグレードパスを提供。

### 2.2 対抗予想UI: 対抗予想型（Counter-Forecast）

**採用: 対抗予想型（コメント型・派生型は不採用）**

```
コメント型   ❌ → 比較不可能。精度追跡できない
派生予想型   ❌ → 別の予測問題になる。比較基準がずれる
対抗予想型   ✅ → 同一予測問題・同一解決基準で確率だけ違う
```

**対抗予想の構造:**
```
元予測:  NP-2026-0042, our_pick_prob=70%, scenario=base
対抗予想: prediction_id=NP-2026-0042, voter_uuid=xxx, probability=30%, explanation="市場はこれを過剰評価している"
```

**実装:** 既存の `reader_votes` テーブルが既にこれを実装済み。
不足しているのは: ① `explanation` フィールド、② UIでの「なぜ反論するか」の入力欄

### 2.3 期限設計: 原則同期限（推奨案）

```
原則: 対抗予想は原予測と同じ resolution_question / oracle_deadline を共有
  → 同一解決イベントで比較可能
  → Brier Score が同一基準で計算可能

例外: 別期限を希望する場合 → 新規予測 (prediction_id) として登録
  → 派生カードとして新しい prediction_id を発行
```

**最終推奨:** 同期限強制 + 「別の見方で投稿する」= 新規予測フロー（Phase 2）

### 2.4 スコア設計

| スコア | 公開/非公開 | 理由 |
|---|---|---|
| Brier Score (avg) | **公開** | 誰でも理解できる。0=完璧、1=最悪 |
| Resolved count (N) | **公開** | 信頼性の根拠。N<5は非表示 |
| Accuracy% (的中率) | **公開** | 一般向け補助指標 |
| Calibration curve | **公開** (Phase 2) | 70%で予測した時に何%当たるか |
| Log score | **非公開** (internal) | 過剰確信ペナルティが強すぎて萎縮させる |
| Difficulty adjustment | **非公開** (internal) | 将来のランキング改善に使用 |
| 直近90日スコア | **公開** (Phase 2) | 長期平均だけでは近況が見えない |

**ルール:** N≥5のresolved予測がある人のみLeaderboard表示。
**理由:** 1回の幸運でランキングに入れると、精度ではなくギャンブルになる。

### 2.5 ヒーロー化設計

```
Leaderboard:
  → 上位10人を名前付きで公開
  → 週次/月次でX投稿 (@nowpattern でシェア)
  → "AI vs 人間" の対決ナラティブ

バッジ (Phase 2):
  🎯 Calibration King: avg_brier < 0.10, N≥10
  📊 Volume Forecaster: N≥50 resolved
  ⚡ Contrarian: 市場確率<30%なのに的中
  🔥 Hot Streak: 直近10予測で8以上的中
  🌍 Domain Expert: ジャンル別上位10%
  🆕 Rising Star: 直近30日でleaderboard急上昇

ナラティブ:
  → "このAIを倒せる人間はいるか？"
  → "Forecaster #XXXXが3ヶ月連続でAIを上回っている"
```

---

## 3. 収益化ラダー

### Phase 1 (今): 完全無料・摩擦ゼロ
```
- 匿名UUID投票: 登録不要
- 目標: 最初の1000人間投票者
- 収益: $0（信頼構築が最優先）
```

### Phase 2 (1000人到達後): Ghost Members Free/Paid
```
Ghost Members Free (無料登録):
  - 名前付きプロフィール (/forecaster/[uuid])
  - 個人トラックレコードページ
  - 解決時メール通知
  - Leaderboardへの名前表示

Ghost Members Paid ($9〜19/月):
  - 高度なCalibration分析
  - 月次"AI vs 人間"レポートPDF
  - 早期アクセス (予測解決前の詳細分析)
  - Tournament参加権 (有料限定トーナメント)
```

### Phase 3 (有名化後): Enterprise / API
```
- 予測DB公開API: $99〜499/月
- Superforecaster認定レポート: $500〜/枚
- 企業スポンサードトーナメント
- ❌ 金融・賭け要素: 法的整理が完了するまで除外
```

---

## 4. MVP推奨（今すぐ vs 後で vs まだやらない）

### 今すぐ作るもの (Week 1-2)

| 機能 | 難易度 | レバレッジ | 理由 |
|---|---|---|---|
| 投票UIの視認性改善 | 低 | **最高** | 最大の問題は「UIが見えない」 |
| "AIを倒せ" CTAコピー | 低 | 高 | 参加動機の最大化 |
| `explanation` フィールド追加 (DB migration) | 低 | 中 | 対抗予想の最小実装 |
| leaderboard ページ公開 | 中 | 高 | ヒーロー化の起点 |
| X週次シェア (leaderboard結果) | 低 | 高 | E（波及力）直結 |

### Phase 1.5 (Month 2-3)

- メール登録 → UUID紐付け (Ghost Members bridge)
- 名前付き個人ページ (/forecaster/{uuid})
- 解決時メール通知

### Phase 2 (Month 4+)

- バッジシステム
- Calibration chart
- Paid tier ($9/月)
- 公開API

### まだやらない

- ユーザー生成予測 (モデレーション問題)
- リアルマネートーナメント (法的整理必要)
- コメント欄 (対抗予想型で代替)
- 外部ソーシャルログイン (Ghost Members で十分)

---

## 5. 実装計画

### Week 1: 最小参加体験の改善

1. **DB migration**: `reader_votes` に `explanation TEXT` カラム追加
   - 非破壊的 additive change
   - `ALTER TABLE reader_votes ADD COLUMN explanation TEXT;`

2. **API追加**: POST /reader-predict/vote に `explanation` フィールド対応
   - VoteRequest model に `explanation: Optional[str] = None` 追加
   - max 200文字バリデーション

3. **feature flag**: prediction_page_builder.py に `COUNTER_FORECAST_ENABLED = True/False`
   - UIを feature flag で on/off できるようにする

4. **Leaderboard page**: /leaderboard/ Ghost page作成
   - Static HTML + JS で /reader-predict/top-forecasters を表示
   - "AI vs あなた" のスコアボード

### Week 2: 参加CTAの強化

5. **投票UIのコピー改善**: "Cast your prediction" → "AIに対抗する" or "予測参加"
6. **X週次投稿**: leaderboard結果 + "今週のNo.1 Forecaster" を毎週月曜投稿

### Month 2: アカウント

7. **Ghost Members bridge**: UUID → email登録フロー
8. **個人ページ**: /forecaster/{uuid} の実装

---

## 6. 技術要件

### DB schema (additive changes only)

```sql
-- reader_votes に explanation 追加 (non-breaking)
ALTER TABLE reader_votes ADD COLUMN explanation TEXT;
ALTER TABLE reader_votes ADD COLUMN voter_display_name TEXT;  -- Phase 1.5
ALTER TABLE reader_votes ADD COLUMN ghost_member_id TEXT;     -- Phase 1.5

-- INDEX
CREATE INDEX IF NOT EXISTS idx_voter_display ON reader_votes(voter_display_name);
```

### API endpoints (新規 + 拡張)

```
既存 (触るな):
  POST /reader-predict/vote
  GET  /reader-predict/stats/{prediction_id}
  GET  /reader-predict/stats-bulk
  GET  /reader-predict/leaderboard
  GET  /reader-predict/top-forecasters
  GET  /reader-predict/my-tracker/{voter_uuid}
  GET  /reader-predict/my-stats/{voter_uuid}

新規追加 (Week 1):
  PATCH /reader-predict/vote/{prediction_id}/{voter_uuid}/explanation
    → explanation を後から追加/更新できる

新規追加 (Phase 1.5):
  POST  /reader-predict/register-name
    → voter_uuid + display_name + email → ghost_member bridge
  GET   /reader-predict/forecaster/{voter_uuid}
    → 個人プロフィールデータ
```

### Feature flags (prediction_page_builder.py)

```python
FEATURE_FLAGS = {
    "COUNTER_FORECAST_UI": False,      # Week 1で True に
    "LEADERBOARD_PAGE": False,         # Week 1で True に
    "NAMED_PROFILES": False,           # Phase 1.5で True に
    "RESOLUTION_NOTIFICATIONS": False,  # Phase 2で True に
}
```

---

*PRD v1.0 — 2026-03-29 | 次レビュー: ChatGPT → DECISIONS.md 論点確認後*
