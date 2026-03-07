# 読者参加型予測プラットフォーム設計書

> Nowpattern — Oracle Platform v2.0
> 作成日: 2026-03-07 / 更新: 2026-03-07（グローバルビジョンに格上げ）
> 目的: 読者・AIが予測に参加し、3年分のトラックレコードが「翌日には作れないモート」になる仕組みを設計する
>
> **Naotoの意図（最終確認済み）**: 「日本初」は出発点。目標は **世界初の日本語×英語バイリンガル・キャリブレーション予測プラットフォーム**。
> JA + EN の両言語で、Metaculus（英語専門）が存在しない市場を取りに行く。

---

## 0. エグゼクティブサマリー

Nowpatternは現在、**編集部（Naoto + NEO）が予測を出す**一方向のOracle。
この設計書は、**読者・AIも予測に参加できる双方向のOracle Platform**に進化させる青写真。

### なぜ今これを作るか

| 現在（v1.0） | 目標（v2.0） |
|-------------|-------------|
| Nowpatternだけが予測する | 読者も予測できる |
| Brier Scoreは内部管理のみ | 全員のスコアが公開される |
| 読者は記事を読むだけ | 読者は記事に「賭け」る |
| 3年後に優位性が出る（かもしれない） | 3年後にコピー不可能なデータ資産が確実に積み上がる |

### 核心的な洞察

**「予測市場の勝者は、最も多く予測したプレイヤーではなく、最も長く予測し続けたプレイヤーである」**

Metaculusが2011年から運営されている事実が示すように、予測プラットフォームの価値は
時間の関数。Nowpatternが2026年に読者参加システムを始めれば、
2029年に「3年間・日本語・地政学/経済専門」という唯一無二のトラックレコードDBが完成する。

---

## 1. 世界水準の予測プラットフォーム調査

### 1.1 Metaculus（metaculus.com）— 最も参考にすべき設計

**設立**: 2015年 / **ユーザー数**: 約50,000人 / **予測数**: 50,000件以上

#### 仕組みの核心

**質問の構造**
- 各質問に「解決条件」を明示（例: "2026年末時点でGDPが前年比3%以上か？"）
- 解決日（Resolution Date）を設定
- 質問作成者が解決の証拠を提示してクローズ

**予測の入力方法**
- 確率 0.1%〜99.9% でスライダー入力
- 「なぜその確率か」のコメント欄（任意）
- 確率は何度でも更新可能（最終更新が評価される）

**Brier Scoreの使い方**
- BS = (予測確率 - 実際の結果)²
- 0に近いほど良い（0=完璧、1=完全に外れ）
- 「コミュニティ予測」= 全ユーザーの加重平均（実績が高いユーザーほど重み大）

**トラックレコードの公開**
- 全ユーザーのプロフィールページに公開
- 「カテゴリ別精度」「時間軸別精度」「キャリブレーション曲線」を表示
- キャリブレーション曲線: 「70%と言ったとき実際に70%起きているか？」のグラフ

**リピーターを作る仕組み**
- 自分の予測が「コミュニティ平均より良い」通知
- 予測した質問が解決されると通知
- 「あなたの精度: 上位12%」等のランキング通知
- トーナメント（賞金付きコンテスト）

**AIの参加**
- Metaculus自身がAI予測モデルを公開・比較中
- 外部AI（GPT-4等）の予測を人間と比較するプロジェクトあり
- AIと人間を分けたランキングは2024年頃から実験的に導入

**Nowpatternへの教訓**
1. 解決条件を厳密に定義しないと判定で揉める
2. 確率の自由入力（スライダー）が参加障壁を下げる
3. キャリブレーション曲線は「単なる的中率」より信頼の証明になる
4. 更新可能な予測（最終確率で評価）が継続参加を促す

---

### 1.2 Manifold Markets（manifold.markets）— ゲーム性設計の参考

**設立**: 2022年 / **特徴**: プレイマネー（Mana）による予測市場

#### 仕組みの核心

**アカウント登録**
- メール / Google ログイン
- 登録時に Mana 1,000（プレイマネー）をプレゼント
- 無料。実際の金銭的リスクなし

**予測の入力方法**
- 「YES」か「NO」に Mana を賭ける（株式市場のように売買）
- 確率は自動的に市場価格として算出（オーダーブック方式）
- 単純明快: 「YES $50 賭ける」ボタン1つ

**トラックレコード・スコア**
- 純収益（Profit）がプロフィールに表示
- 「返還率（ROI）」= 投資した Mana に対してどれだけ増えたか
- カテゴリ別 ROI も公開

**何が人を引き戻すか**
- 「あなたのポジションが変動しています」通知（株価アラートと同じ感覚）
- 新しいマーケットを作れる（クリエイター体験）
- リーダーボードで自分の順位が毎週動く
- Manaが増えると「金持ち感」がある（実質0円でも）

**Nowpatternへの教訓**
1. プレイマネー（ポイント制）にするだけで参加障壁が劇的に下がる
2. 「株を買う感覚」= 皮膚感覚的なリスク体感が継続参加を促す
3. マーケット作成権（読者が質問を作れる）がエンゲージメントを爆発させる
4. 実際の金銭がないからこそ実験的・学習的参加ができる

---

### 1.3 Good Judgment Open（gjopen.com）— プロ予測者コミュニティの設計

**起源**: Philip Tetlock の「スーパーフォーキャスター」研究（2011-2015）
**特徴**: Brier Scoreで上位2%のユーザーが「Superforecaster」認定される

#### 仕組みの核心

**アカウント・階層システム**
- 無料登録
- Brier Score の累積成績で自動的に昇格
- **一般フォーキャスター → Superforecaster** の明確なラダー
- Superforecasterは実際に企業・政府に雇われることがある

**予測入力**
- 確率スライダー（0〜100%）
- 質問ごとにコメント必須（推論プロセスを共有）
- 予測の更新回数が多いほど精度が上がる（Superforecasterの習慣）

**何が人を引き戻すか**
- 「Superforecaster になれる」という明確な目標
- Superforecasterのコメントが公開される（読むだけで勉強になる）
- 期間限定チャレンジ（UBS, The Economist スポンサー）
- 「自分の推論プロセスを記録する」日記的価値

**AIの参加**
- 現時点でAI専用トラックは未設定
- ただし研究プロジェクトとしてAI vs 人間の比較が進行中

**Nowpatternへの教訓**
1. 「Superforecaster」認定 = 最強の retention ループ。称号が欲しくて続ける
2. 推論プロセスの公開義務 = コンテンツとしての価値。他人の読み方が学びになる
3. スポンサー付きコンテスト = 外部の信頼性証明
4. 積み上げ式の評価（50件以上で初めて意味を持つ）が長期参加を促す

---

### 1.4 Polymarket（polymarket.com）— 実マネー市場との連携

**特徴**: 実際の暗号資産（USDC）を賭ける予測市場
**日本との関係**: 法的グレーゾーン（日本居住者は参加不可の可能性）

#### Nowpatternとの連携（現在進行中）

Nowpatternは既に `prediction_resolver.py` で Polymarket データを参照している:
- `market_history.db` に Polymarket の確率スナップショットを保存
- 「市場コンセンサス」としてNowpatternの予測と並べて表示

**設計上の重要な示唆**
- Polymarketの確率は「集合知の最良推定」として使える
- NowpatternがPolymarketに勝てるとき = Nowpatternの情報優位性の証明
- 読者の予測 vs Polymarket 確率 = 面白い対比コンテンツになる

---

### 1.5 Fatebook（fatebook.io）— 個人トラッキングの参考

**特徴**: 個人の日常的な予測（「このプロジェクトは期日に終わるか？」）を記録
**Brier Score**: スライダー入力 → 自動計算 → 履歴グラフ表示

**Nowpatternへの教訓**
1. API公開 + Slack/Discord Bot でエコシステム拡張
2. 「個人の日記」として使えると定着する（SNS感覚）
3. キャリブレーショントレーニング（過去の問題で練習）が入門を促す

---

## 2. Nowpattern 読者参加型予測システム設計

### 2.1 全体アーキテクチャ

```
[記事ページ（Ghost）]
     │
     ├── ORACLE STATEMENT ボックス（既存）
     │        └── "あなたも予測する →" ボタン [NEW]
     │
     ↓
[予測入力UI（Ghost codeinjection or 独立ページ）]
     │
     ├── シナリオ選択（楽観/基本/悲観）
     ├── 確率スライダー（10〜90%）[NEW]
     ├── 一言コメント（任意）[NEW]
     └── 送信ボタン
     │
     ↓
[reader_prediction_api.py（VPS FastAPI）] [NEW]
     │
     ├── reader_predictions.db（SQLite）[NEW]
     │        ├── predictions table（既存 prediction_db.json を参照）
     │        ├── reader_votes table [NEW]
     │        └── reader_profiles table [NEW]
     │
     ├── Brier Score 計算エンジン（既存ロジック流用）
     └── リーダーボード集計
     │
     ↓
[/predictions/ ページ（Ghost）]
     │
     ├── スコアボード（既存: Nowpattern の精度）
     ├── コミュニティ予測分布 [NEW]
     └── リーダーボード [NEW]
```

---

### 2.2 フェーズ別実装計画

#### Phase 1（Month 1-2）: 最小実装 — 予測を受け付ける

**目標**: 読者が予測を送れる。スコアが計算される。

**実装する機能**:

1. **予測入力フォーム**（各記事の ORACLE STATEMENT ボックスに追加）
   ```html
   <!-- Ghost記事のcodeinjection_foot に追加 -->
   <div class="np-reader-prediction" data-prediction-id="NP-2026-XXXX">
     <h4>あなたの予測は？</h4>
     <div class="scenario-buttons">
       <button data-scenario="楽観">楽観シナリオ</button>
       <button data-scenario="基本">基本シナリオ（最有力）</button>
       <button data-scenario="悲観">悲観シナリオ</button>
     </div>
     <input type="range" min="10" max="90" value="50" id="prob-slider">
     <span id="prob-display">50%の確率で起きると思う</span>
     <textarea placeholder="なぜそう思うか（任意）"></textarea>
     <button onclick="submitPrediction()">予測を記録する</button>
   </div>
   ```

2. **バックエンドAPI**（FastAPI、VPS上に新規サービス）
   ```
   POST /api/v1/predictions/{prediction_id}/vote
   Body: {
     "user_id": "匿名ID or ログインID",
     "scenario": "楽観|基本|悲観",
     "probability": 0.70,
     "comment": "...",
     "user_type": "human|ai",
     "timestamp": "ISO8601"
   }

   GET /api/v1/predictions/{prediction_id}/community
   Response: {
     "distribution": {"楽観": 0.30, "基本": 0.55, "悲観": 0.15},
     "avg_probability": 0.68,
     "vote_count": 42,
     "vs_nowpattern": "+0.05"   // コミュニティ平均とNowpatternの差
   }
   ```

3. **匿名ID発行**（Phase 1はログイン不要）
   - ブラウザ localStorage に UUID を保存
   - 「この予測は匿名で記録されました。ログインすると公開プロフィールに反映されます」

**KPI（Phase 1終了時点）**:
- 予測数 > 100件
- ユニーク参加者 > 50人
- エラー率 < 1%

---

#### Phase 2（Month 3-4）: アカウント + トラックレコード

**目標**: 読者が積み上げを実感できる。リピーターが生まれる。

**実装する機能**:

1. **アカウントシステム**（最小限）
   - メールアドレス + パスワード（または Google OAuth）
   - 表示名（ニックネーム）と「ヒューマン / AI」の選択
   - プロフィールページ `/forecaster/[username]/`

2. **プロフィールページの表示項目**
   ```
   ┌─────────────────────────────────────────────────────┐
   │  @username                          [Human / AI]    │
   │  加入: 2026-03-15 | 予測数: 47 | 解決済み: 23        │
   │                                                     │
   │  Brier Score: 0.168 ← 「優秀（上位15%）」           │
   │  ████████░░░░░ キャリブレーション: 良好              │
   │                                                     │
   │  カテゴリ別精度:                                     │
   │  地政学: 0.142 | 経済: 0.201 | テクノロジー: 0.155   │
   │                                                     │
   │  予測履歴（最新5件）:                                 │
   │  [NP-2026-0042] 基本シナリオ → 的中 ✅ BS: 0.09     │
   │  [NP-2026-0038] 楽観シナリオ → 外れ ❌ BS: 0.49     │
   └─────────────────────────────────────────────────────┘
   ```

3. **Brier Scoreの計算とランキング**
   - 解決済み予測のBrier Scoreを累積
   - 最小10件の予測で初めてランキング表示（信頼性確保）
   - カテゴリ別精度の分析（地政学・経済・テクノロジー）

4. **通知システム**（Emailまたはブラウザ通知）
   - 「あなたが予測した NP-2026-0042 が解決されました」
   - 「あなたのBrier Score: コミュニティ平均より12%優れています」
   - 「新しい予測が公開されました（あなたの得意ジャンル: 地政学）」

**KPI（Phase 2終了時点）**:
- 登録ユーザー > 200人
- リピート参加率 > 40%（月次）
- プロフィールページビュー > 500/月

---

#### Phase 3（Month 5-6）: リーダーボード + コミュニティ

**目標**: 競争と協調が同時に起きる。コンテンツとしての価値が生まれる。

**実装する機能**:

1. **公開リーダーボード** `/leaderboard/`
   ```
   ┌─────────────────────────────────────────────────────┐
   │  Nowpattern Oracle — 予測者リーダーボード            │
   │                                                     │
   │  [ヒューマン]  [AI]  [全期間]  [今月]  [今四半期]    │
   │                                                     │
   │  # 1  @tanaka_forecast     BS: 0.112  予測: 89件   │
   │       地政学の達人 | 2026年3月から                   │
   │  # 2  @ai_gpt4_turbo       BS: 0.134  予測: 203件  │
   │       AI | OpenAI GPT-4 | bot                      │
   │  # 3  @macro_watcher       BS: 0.158  予測: 54件   │
   │       経済学専攻 | Nowpatternファン                  │
   │                                                     │
   │  [ヒューマン上位に移動した場合: バッジ取得]          │
   └─────────────────────────────────────────────────────┘
   ```

2. **ヒューマン vs AI 分離トラック**
   - AIアカウントは `user_type: "ai"` で識別
   - AIのBrier Scoreを「市場コンセンサス」の比較軸として表示
   - 「GPT-4のBrier Score: 0.18 | あなた: 0.16 → あなたがAIより優れています」

3. **コミュニティ予測分布**（各記事ページに表示）
   ```
   コミュニティの予測（42人）:
   楽観 ████░░░░░░ 23%
   基本 ██████████ 55%  ← 多数意見
   悲観 ████░░░░░░ 22%

   Nowpatternの予測: 基本（60%）
   コミュニティとの差: +5%（基本に対して）

   Polymarketの市場コンセンサス: 62%
   ```

4. **称号システム**（Metaculasの「Superforecaster」に相当）

   | 称号 | 条件 | 意味 |
   |------|------|------|
   | 見習いオラクル | 予測10件以上 | 参加者 |
   | オラクル | Brier < 0.20 かつ 30件以上 | 平均以上 |
   | シニアオラクル | Brier < 0.15 かつ 50件以上 | 上位15% |
   | マスターオラクル | Brier < 0.12 かつ 100件以上 | 上位5% |
   | **Superforecaster** | Brier < 0.10 かつ 200件以上 | 上位2% Metaculus相当 |

**KPI（Phase 3終了時点）**:
- 月次アクティブ予測者 > 100人
- リーダーボードページビュー > 1,000/月
- Superforecaster認定者が1人以上

---

#### Phase 4（Month 7-12）: 不変性 + モート構築

**目標**: 「誰も改ざんできないトラックレコード」の確立。

**実装する機能**:

1. **タイムスタンプの不変化**（ブロックチェーン or オープンソース証明）

   **選択肢A: Ethereum/Polygon への書き込み（コスト: ガス代）**
   ```python
   # 各予測の SHA256 ハッシュを Polygon に記録
   # コスト: 約$0.01/件 = 1,000件で $10
   prediction_hash = sha256(json.dumps({
     "prediction_id": "NP-2026-0042",
     "user_id": "hash_of_user",
     "scenario": "基本",
     "probability": 0.70,
     "submitted_at": "2026-03-15T09:00:00Z"
   })).hexdigest()
   # → Polygon に記録 → トランザクションIDをDBに保存
   ```

   **選択肢B: GitHub + タイムスタンプサービス（コスト: 無料）**
   ```bash
   # 毎日スナップショットをGitHubに公開コミット
   git commit -m "predictions-snapshot-2026-03-15: 203 predictions"
   # → GitHubのコミット履歴が改ざん不可能な証明になる
   # → OpenTimestamps (https://opentimestamps.org) でBitcoinに記録
   ```

   **推奨**: まずは選択肢B（GitHub + OpenTimestamps）で実装。
   コストゼロで「公開・検証可能」の原則を満たせる。

2. **AIエージェント参加フロー**

   **対象**: GPT-4, Claude, Gemini, Grok などのLLM
   ```
   POST /api/v1/predictions/{id}/vote
   Headers: {
     "X-Agent-Type": "ai",
     "X-Agent-Name": "GPT-4-turbo",
     "X-Agent-Version": "2024-04-09",
     "X-Agent-Owner": "your-email@example.com"
   }
   ```
   - AIの予測もBrier Scoreで評価される
   - 「AI vs ヒューマン」の公開比較がコンテンツになる
   - Nowpatternのレポート: 「今月、Claude 3 がGPT-4より12%精度が高かった」

3. **APIの公開**（外部からの予測取得）
   ```
   GET /api/v1/predictions/open           # 進行中の全予測
   GET /api/v1/leaderboard                # 公開リーダーボード
   GET /api/v1/forecaster/{username}      # 個人スコア（公開のみ）
   ```
   - 外部メディア・研究者が使えるデータになる
   - 「Nowpatternのデータを使ってXXを分析した」という二次コンテンツが生まれる

**KPI（Phase 4終了時点）**:
- AIアカウント登録 > 5種類
- タイムスタンプ記録件数 > 1,000件
- API利用者 > 10件

---

## 3. 技術設計仕様

### 3.1 データスキーマ（reader_predictions.db）

```sql
-- 読者の予測記録
CREATE TABLE reader_votes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id   TEXT NOT NULL,           -- NP-2026-0042 (既存DBの参照)
    user_id         TEXT NOT NULL,           -- UUID（匿名）or username
    scenario        TEXT NOT NULL,           -- 楽観/基本/悲観
    probability     REAL NOT NULL,           -- 0.1〜0.9
    comment         TEXT DEFAULT '',
    submitted_at    TEXT NOT NULL,           -- ISO8601
    is_updated      INTEGER DEFAULT 0,       -- 更新された予測かどうか
    brier_score     REAL,                    -- 解決後に計算
    outcome_match   INTEGER,                 -- 1=的中, 0=外れ, NULL=未解決
    timestamp_hash  TEXT,                    -- ブロックチェーンTXID
    UNIQUE(prediction_id, user_id)           -- 1ユーザー1予測（更新は上書き）
);

-- 読者プロフィール
CREATE TABLE reader_profiles (
    user_id         TEXT PRIMARY KEY,
    username        TEXT UNIQUE NOT NULL,
    email           TEXT UNIQUE,
    user_type       TEXT DEFAULT 'human',    -- human / ai
    agent_name      TEXT,                    -- AIの場合: GPT-4-turbo等
    joined_at       TEXT NOT NULL,
    total_votes     INTEGER DEFAULT 0,
    resolved_votes  INTEGER DEFAULT 0,
    avg_brier_score REAL,
    rank_title      TEXT DEFAULT '見習いオラクル',
    is_public       INTEGER DEFAULT 1,
    last_active     TEXT
);

-- カテゴリ別精度（集計テーブル）
CREATE TABLE category_accuracy (
    user_id         TEXT NOT NULL,
    category        TEXT NOT NULL,           -- geopolitics/economy/technology等
    vote_count      INTEGER DEFAULT 0,
    avg_brier_score REAL,
    last_updated    TEXT,
    PRIMARY KEY (user_id, category)
);

-- コミュニティ集計（キャッシュ）
CREATE TABLE community_summary (
    prediction_id       TEXT PRIMARY KEY,
    vote_count          INTEGER DEFAULT 0,
    optimistic_ratio    REAL DEFAULT 0,
    base_ratio          REAL DEFAULT 0,
    pessimistic_ratio   REAL DEFAULT 0,
    avg_probability     REAL,
    community_bs        REAL,               -- コミュニティのBrier Score
    vs_nowpattern       REAL,               -- Nowpatternとの差
    last_updated        TEXT
);
```

### 3.2 APIエンドポイント設計

> **【実装済み — TIER 0完了】** 2026-03-07 に実装・稼働済み。
> 実際のパスは `/reader-predict/*`（設計書のドラフト `/api/v1/` とは異なる）。
> Port: 8766。Caddy設定変更不要（既存ルールが有効）。

**稼働中エンドポイント（変更禁止）:**
```
POST /reader-predict/vote
  Body: { prediction_id, voter_uuid, scenario, probability }
  scenario: "optimistic" | "base" | "pessimistic"
  probability: 5〜95（5刻み）

GET  /reader-predict/stats/{prediction_id}  — 単一予測の統計
GET  /reader-predict/stats-bulk            — 全予測の統計（ページJS用）
GET  /reader-predict/my-votes/{voter_uuid} — 個人の投票履歴
GET  /reader-predict/leaderboard           — TIER 1 placeholder
GET  /reader-predict/health                — ヘルスチェック
```

**TIER 1〜4で追加予定エンドポイント（参考）:**
```python
# TIER 1: 個人トラックレコード
GET /reader-predict/profile/{voter_uuid}    # Brier Score累積

# TIER 2: リーダーボード詳細
GET /reader-predict/leaderboard?type=human|ai&period=month

# TIER 4: 公開API
GET /reader-predict/open-predictions        # 進行中予測一覧
```

### 3.3 既存システムとの統合

**prediction_db.json（既存）との関係**:
```python
# prediction_tracker.py の judge_prediction() 実行後に
# reader_predictions.db の全票を自動スコアリング

def on_prediction_resolved(prediction_id, outcome_label):
    """既存の予測が解決されたとき、読者票を一括スコアリング"""
    conn = sqlite3.connect(READER_DB)
    votes = conn.execute(
        "SELECT id, scenario, probability FROM reader_votes WHERE prediction_id = ?",
        (prediction_id,)
    ).fetchall()

    for vote in votes:
        # Brier Score計算（prediction_tracker.pyの関数を流用）
        bs = calculate_reader_brier_score(
            voted_scenario=vote["scenario"],
            voted_prob=vote["probability"],
            actual_outcome=outcome_label
        )
        conn.execute(
            "UPDATE reader_votes SET brier_score = ?, outcome_match = ? WHERE id = ?",
            (bs, 1 if vote["scenario"] == outcome_label else 0, vote["id"])
        )

    # ユーザーの累積スコアを更新
    update_user_aggregates(conn, [v["user_id"] for v in votes])
    conn.commit()
```

**prediction_page_builder.py（既存）との統合**:
```python
# 既存のページビルダーにコミュニティセクションを追加
def build_community_section(prediction_id, lang="ja"):
    """コミュニティ予測分布のHTMLを生成"""
    summary = get_community_summary(prediction_id)
    if summary["vote_count"] < 3:
        return ""  # 3票未満は表示しない（スパム対策）

    return f"""
    <div class="np-community-prediction">
      <h4>コミュニティの予測（{summary["vote_count"]}人）</h4>
      <div class="distribution-bar">
        楽観 {summary["optimistic_ratio"]*100:.0f}%
        基本 {summary["base_ratio"]*100:.0f}%
        悲観 {summary["pessimistic_ratio"]*100:.0f}%
      </div>
      <p>vs Nowpattern: {'+' if summary['vs_nowpattern'] > 0 else ''}{summary['vs_nowpattern']*100:.0f}%</p>
    </div>
    """
```

---

## 4. なぜこれがモートになるか

### 4.1 時間の複利効果

```
2026年3月: 読者参加スタート
2026年9月: 解決済み予測 500件、登録者 500人
2027年3月: Brier Score 1年分が確立。「Nowpatternオラクルは◯◯%精度」が語れる
2028年3月: 2年分のトラックレコード。日本語予測市場で唯一のデータセット
2029年3月: 3年分。競合が翌日に「じゃあ私たちもやる」と言っても3年は追いつけない
```

**Metaculusの示すこと**: 2015年から2025年の10年間で約50,000人のコミュニティが形成された。
最初の3年が最も困難で、最も価値が高い。

### 4.2 3つのネットワーク効果

**1. データのネットワーク効果**
- 参加者が増えるほど「コミュニティ予測」の精度が上がる
- 精度が上がるほど「参考になる」と新規参加者が増える
- データが蓄積するほど研究・分析の素材として価値が上がる

**2. 評判のネットワーク効果**
- Superforecasterが増えるほど「あそこのコミュニティは精度が高い」という評判になる
- 評判が高まるほど優秀な予測者が集まる
- 優秀な予測者が集まるほどコンテンツの質が上がる

**3. トラックレコードのネットワーク効果**
- 時間が経つほど「累積スコア」の意味が大きくなる（1件のスコアより100件）
- 「3年間連続Superforecaster」は短期間では作れない
- 長期データがあるほど「本物の予測能力」と「運」を区別できる

### 4.3 コピー不可能な要素

| 要素 | コピーできる | コピーできない |
|------|-------------|---------------|
| UIデザイン | ○（3日で） | |
| スコア計算式 | ○（1時間で） | |
| 3年分のデータ | | ○（3年かかる） |
| ユーザーの実績履歴 | | ○（ユーザーは移動しない） |
| キャリブレーション曲線の信頼性 | | ○（時間で作られる） |
| 「あの人はNowpatternで上位5%」の評判 | | ○（評判は移植できない） |

### 4.4 Nowpattern独自の優位性

**他の予測市場にない要素**:

1. **記事との紐付き**
   - Metaculusの予測は記事から独立している
   - Nowpatternは「この記事を読んでその予測をする」体験
   - 記事の力学分析が「なぜこの確率か」の説明になる

2. **日本語×英語バイリンガル特化（グローバル展開の起点）**
   - 英語圏の予測市場（Metaculus等）は日本語未対応
   - 「日本から見た地政学予測」は Metaculus にほぼ存在しない
   - JA + EN の両言語で同一予測を公開 → 日本人 + 英語ユーザー両方を取り込む
   - Phase GLOBAL（Year 2〜）: 国際Superforecasterとの比較ランキングで世界展開

3. **AI参加の先行者優位**
   - 「AIと人間の予測精度を比較できるプラットフォーム」はほぼ存在しない
   - 「GPT-4 vs Claude vs 人間オラクル」の比較データ = 2026年のオリジナルコンテンツ
   - AIを「競争相手」として位置づけることで人間の動機が上がる

---

## 5. ゲームデザイン — 人を動かす心理メカニズム

### 5.1 参加の動機づけ（Why People Predict）

| 動機 | 対応する設計 |
|------|-------------|
| **自己証明** | 「自分はAIより予測が上手い」を証明できる |
| **学習** | 外れたとき「なぜ外れたか」が明確（Brier Scoreで可視化） |
| **ゲーム感覚** | リーダーボード、称号、バッジのコレクション |
| **社会的認知** | 「Superforecaster」称号がSNSで共有できる |
| **役に立つ感覚** | 自分の予測がコミュニティ集合知に貢献している |
| **追体験** | 「あのとき私はこう予測した」という歴史との対話 |

### 5.2 リテンションループの設計

```
予測を送る
  ↓ [数週間〜数ヶ月後]
結果が出る
  ↓ [通知が届く]
「的中しました！Brier Score: 0.09」または「外れました。理由は...」
  ↓ [プロフィールが更新される]
累積スコアが変動する
  ↓ [ランキングが動く]
「あと5件予測すると Superforecaster になれます」
  ↓
次の予測を送る ← ループ
```

### 5.3 ゲーミフィケーションの階層

**Level 1: 即時報酬（送信直後）**
- 「予測が記録されました！予測ID: NP-RDR-2026-00842」
- コミュニティの現在の分布との比較
- 「あなたはコミュニティ平均より+5%楽観的です」

**Level 2: 短期報酬（解決時）**
- メール/ブラウザ通知
- Brier Score の変動
- 「今月の的中率: 3/5件（60%）」

**Level 3: 長期報酬（累積）**
- 称号の変化（見習い → オラクル → Superforecaster）
- カテゴリ別の「得意分野」バッジ
- 「1年間参加者」記念バッジ

---

## 6. AI参加フロー設計

### 6.1 AI参加の技術仕様

```python
# AI エージェント向けの予測投稿

import requests

def submit_ai_prediction(
    prediction_id: str,
    scenario: str,
    probability: float,
    reasoning: str,
    model_name: str = "claude-opus-4-6",
    api_key: str = "..."
):
    """
    AI エージェントが Nowpattern に予測を投稿する

    prediction_id: NP-2026-0042 (nowpattern.comの予測ID)
    scenario: 楽観|基本|悲観
    probability: 0.1〜0.9 (その シナリオが起きる確率)
    reasoning: AIの推論プロセス（公開される）
    """
    response = requests.post(
        f"https://nowpattern.com/api/v1/predictions/{prediction_id}/vote",
        json={
            "scenario": scenario,
            "probability": probability,
            "comment": reasoning,
            "user_type": "ai",
            "agent_name": model_name
        },
        headers={
            "Authorization": f"Bearer {api_key}",
            "X-Agent-Type": "ai",
            "X-Agent-Name": model_name,
            "Content-Type": "application/json"
        }
    )
    return response.json()

# 実際の使用例（NEOが記事を書いた後に自動投稿）
result = submit_ai_prediction(
    prediction_id="NP-2026-0042",
    scenario="基本",
    probability=0.65,
    reasoning="現在のFOMCの姿勢と市場のコンセンサスを考えると、基本シナリオが最も可能性が高い",
    model_name="claude-opus-4-6"
)
```

### 6.2 AI vs 人間の公開比較

**コンテンツとしての使い方**:

```
[月次レポート: AI vs 人間オラクル対決]

今月の成績（2026年3月）:
=====================================
  🤖 Claude Opus 4.6    BS: 0.156  予測: 87件
  🤖 GPT-4-turbo        BS: 0.182  予測: 71件
  🤖 Gemini 2.5 Pro     BS: 0.198  予測: 64件
  -----------------------------------------
  🏆 #1 人間 @tanaka    BS: 0.112  予測: 23件  ← 今月はAIに勝った！
     #2 人間 @macro_w   BS: 0.145  予測: 18件
     #3 人間 @oracle_j  BS: 0.167  予測: 31件
=====================================

総評: 今月は地政学カテゴリで人間がAIを圧倒。
経済カテゴリではClaude Opus 4.6が最高精度を記録。
```

この「AI vs 人間」対決レポートは、毎月Xに投稿できる
**継続的なコンテンツ素材**になる。

---

## 7. 実装優先順位とタイムライン

### 実装ロードマップ

```
Month 1: Phase 1 最小実装
  Week 1: reader_prediction_api.py（FastAPI）
           reader_predictions.db スキーマ
  Week 2: 予測入力フォーム（Ghost codeinjection）
           匿名ID発行（localStorage UUID）
  Week 3: 既存 prediction_tracker.py との統合フック
           コミュニティ分布の計算・表示
  Week 4: テスト + バグ修正 + KPI計測開始

Month 2: データ収集 + フィードバック
  Week 5-6: Brier Score計算・解決時の自動スコアリング
  Week 7-8: 基本的なメール通知（解決時）

Month 3-4: Phase 2 アカウントシステム
  アカウント登録（メール + Google）
  プロフィールページ /forecaster/[username]/
  称号システムの実装

Month 5-6: Phase 3 リーダーボード
  /leaderboard/ ページ実装
  ヒューマン / AI 分離表示
  バッジ・称号の付与ロジック

Month 7-12: Phase 4 不変性 + API公開
  GitHub daily snapshot + OpenTimestamps
  Public API (/api/v1/predictions/open 等)
  AIエージェント向けのAPIドキュメント
```

### 工数の見積もり

| Phase | 工数 | 技術難度 | 優先度 |
|-------|------|----------|--------|
| 1: 予測受付 | 2週間 | 低 | 最高 |
| 2: アカウント | 3週間 | 中 | 高 |
| 3: リーダーボード | 2週間 | 低 | 高 |
| 4: 不変性 | 3週間 | 高 | 中 |

**推奨**: Phase 1 を最速で動かして実データを集める。
アカウントは後でいい。まず「予測が送れる」体験を作ること。

---

## 8. 成功の定義と測定

### 8.1 月次KPI

| KPI | Month 3 | Month 6 | Month 12 | Year 3 |
|-----|---------|---------|----------|--------|
| 累積予測数 | 100 | 500 | 2,000 | 50,000 |
| 月次アクティブ予測者 | 50 | 150 | 500 | 5,000 |
| Superforecaster数 | 0 | 1 | 5 | 50 |
| 解決済み予測 | 10 | 100 | 500 | 15,000 |
| AI参加モデル数 | 1 | 3 | 5 | 10 |

### 8.2 モート確認基準

以下が揃ったとき、競合に追いつかれないモートが完成したと言える:

- [ ] 1,000件以上の解決済み予測（統計的に意味のあるサンプルサイズ）
- [ ] 50人以上のSuperforecaster認定者（コミュニティの深さ）
- [ ] 1年以上継続参加しているユーザーが100人以上（粘着性）
- [ ] GitHubで1年分のタイムスタンプ記録（改ざん不可能な証明）
- [ ] AI参加モデル3種類以上（「AI vs 人間」コンテンツが回り続ける）
- [ ] メディア・研究者からのAPI利用実績（外部からの信頼証明）

---

## 9. リスクと対策

| リスク | 確率 | 影響 | 対策 |
|--------|------|------|------|
| 参加者が集まらない | 中 | 大 | Xで毎月「AI vs 人間」対決をコンテンツとして発信。NEOが毎記事に予測を投稿してデモンストレーション |
| スパム/虚偽予測 | 高 | 中 | 匿名期は1IPにつき1票。アカウント制になったらレート制限 |
| 判定の公平性への疑問 | 中 | 高 | 判定基準を記事に明示。Geminiの判定根拠を公開。コミュニティ異議申し立て制度 |
| ブロックチェーンのガス代 | 低 | 低 | Phase 4 まで不要。まずGitHub + OpenTimestamps（無料）で代替 |
| API悪用 | 低 | 中 | Rate limiting（1分10件）+ APIキー認証 |

---

## 10. 既存コードへの追加（最小変更で実装）

### prediction_tracker.py への追加

```python
# judge_prediction() に以下を追加（最終行に）
def judge_prediction(prediction_id, outcome, note=""):
    # ... 既存コード ...
    # 解決後に読者票を自動スコアリング
    try:
        from reader_prediction_api import score_reader_votes
        score_reader_votes(prediction_id, outcome)
        print(f"  📊 読者票スコアリング完了: {prediction_id}")
    except ImportError:
        pass  # reader_prediction_api.py 未実装時はスキップ
```

### prediction_page_builder.py への追加

```python
# 各カードに「コミュニティ予測」セクションを追加
# build_tracking_card() または build_resolved_card() の末尾に:

community = get_community_summary(pred["prediction_id"])
if community and community["vote_count"] >= 3:
    html += build_community_section(community, lang)
```

---

## 11. 参考資料

### 研究ベース
- Philip Tetlock「Expert Political Judgment」（2005）: スーパーフォーキャスターの条件
- Tetlock & Gardner「Superforecasting」（2015）: Good Judgment Projectの成果
- Brier, G.W.「Verification of forecasts expressed in terms of probability」（1950）: Brier Score の原論文

### 実装参考
- Metaculus API: `https://www.metaculus.com/api2/` — 設計の参考
- Fatebook オープンソース: GitHub `SAGE-Net/fatebook` — コード参考
- OpenTimestamps: `https://opentimestamps.org` — 無料タイムスタンプ

### Nowpattern 既存コード（本設計書の基盤）
- `/opt/shared/scripts/prediction_tracker.py` — Brier Score計算ロジック
- `/opt/shared/scripts/prediction_verifier.py` — Gemini自動判定
- `/opt/shared/scripts/prediction_page_builder.py` — 公開ページ生成
- `/opt/shared/scripts/prediction_db.json` — 予測データベース

---

*この設計書は2026-03-07に作成。Phase 1の実装開始時に更新すること。*
*変更時はCHANGELOGに追記すること（NORTH_STAR.mdと同じルール）。*

---

## CHANGELOG

| 日付 | 変更内容 |
|------|---------|
| 2026-03-07 | 初版作成。Phase 1-4の全設計。既存コードとの統合仕様を含む |
| 2026-03-07 | TIER 0実装完了: reader_prediction_api.py（Port 8766）、Ghost codeinjection_footウィジェット注入済み |
| 2026-03-07 | グローバルビジョンに格上げ: 「日本初」→「世界初のJA×ENバイリンガル予測プラットフォーム」。APIパス整合（設計/api/v1→実装/reader-predict/） |
