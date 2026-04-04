# NORTH STAR DETAIL — 各セクションの詳細版（JIT参照用）

> このファイルは NORTH_STAR.md の詳細版。各セクションの実践ガイド・具体例・テンプレートを記載。
> NORTH_STAR.md がサマリー（毎回自動読み込み）、このファイルが詳細（必要時にRead）。
> **更新ルール**: NORTH_STAR.md のセクション番号に対応させること。番号がずれたら両方更新。
> **同期チェック**: `python scripts/detail_sync_check.py` で§番号・CHANGELOG日付の整合性を検証可能。

### 情報信頼度マーカー（L1-L5準拠）

> **本ファイル内のテーブルで、AIが推論・補完した列には (AI推論) マークが付いています。**
> これは NORTH_STAR.md §7「知恵の摂取ドクトリン」の L1-L5 階層に基づく透明性措置です。
>
> | マーク | 意味 | 信頼度 |
> |--------|------|--------|
> | (マークなし) | L1-L3: 実測値・古典・原典から直接引用した情報 | 高 |
> | **(AI推論)** | L4-L5: AIが文脈から推論・補完した情報。原典未照合 | 低（参考値） |
>
> **(AI推論)** マークのある列を単体で判断の根拠にしないでください。
> L1-L3ソースと組み合わせるか、原典に当たって検証してから使用してください。

---

## §0 詳細: NAOTO OS — 変更ルール・到達目標

### 変更ルール（4つの不変ルール）

1. **Founder OS や北極星を変える時は `mission_contract.py` を先に変える**
   - 理由: mission_contractが全エージェントの行動基準。NORTH_STARだけ変えるとcontractとの不整合が発生する
   - 手順: mission_contract.py変更 → テスト通過 → NORTH_STAR.md更新 → CHANGELOG追記

2. **公開語彙を変える時は `canonical_public_lexicon.py` を先に変える**
   - 理由: public UIの全文言はcanonical_public_lexicon.pyで一元管理。直接HTMLを編集するとUI間で不整合が発生する
   - 影響範囲: /predictions/, /en/predictions/, /about/, /en/about/, /taxonomy/, /en/taxonomy/

3. **現状認識の数値は固定文言に埋め込まず、release snapshot にだけ置く**
   - 理由: 「1116件」等の数値をNORTH_STARに直接書くと陳腐化する。reports/content_release_snapshot.jsonが唯一の真実
   - 例外: ベンチマーク目標値（Year 1: 0.18以下等）は変わらないので直接記載可

4. **新しい agent / cron / publish path は追加前に `mission_contract_audit` と `publish_path_guard_audit` を通す**
   - 理由: 無秩序なpublish pathの追加はコンテンツ品質管理の崩壊を招く
   - 監査コマンド: `python scripts/mission_contract.py --audit` / `python scripts/publish_path_guard.py --audit`

### 到達目標（4つのマイルストーン）

| # | 目標 | 検証方法 | 現状 |
|---|------|---------|------|
| 1 | 全 active agent が `mission_contract_hash` を持つ | `mission_contract.py --verify-agents` | NEO-ONE/TWO: あり, NEO-GPT: 部分的 |
| 2 | 全 active agent が `bootstrap_context_hash` を持つ | `agent_bootstrap_context.py --verify` | ローカルCC: あり, NEO: 部分的 |
| 3 | 全 public page が `canonical_public_lexicon` だけを使う | `canonical_public_lexicon.py --audit` | /predictions/: 完了, 他: 進行中 |
| 4 | 全 public action が `release_governor` だけを通る | `release_governor.py --audit` | Ghost投稿: 完了, X投稿: 完了 |

---

## §3 詳細: PVQE — 正しいP/間違ったP・行動順序・強制の仕組み

### 正しいPと間違ったP（具体例つき）

```
✅ 正しいP（判断精度を上げる行動）:
  - 実装前に確認する → 「この理解で合っていますか？」と聞く
  - データで確認してから報告 → SSHでVPS状態を確認してから現状報告
  - KNOWN_MISTAKES確認 → 実装前にdocs/KNOWN_MISTAKES.mdを必ずRead
  - 不可逆変更は承認取る → DB削除・公開投稿・お金に関わる変更は必ずNaotoに確認
  - 自分で検証 → ブラウザ/ログで結果を確認してから「完了」と報告

❌ 間違いP（判断精度を下げる行動）:
  - すぐ実装する → 理解確認なしにコードを書き始める
  - 推測で語る → 「おそらく動いていると思います」（確認しろ）
  - 未検証で報告 → 「設定しました」（結果を見ろ）
  - 廃止概念(@aisaintel,AISA)参照 → 存在しないアカウントに言及する
  - 承認なしUI変更 → /predictions/のレイアウトを勝手に変える
```

### 毎回の行動順序（5ステップ）

```
Step 1: KNOWN_MISTAKES.md確認
  → 今から実装するものに関連する過去のミスがないか？
  → あれば、同じ轍を踏まない対策を先に決める

Step 2: 理解確認
  → 「こういう理解でいいですか？」とNaotoに確認
  → Type 2（可逆）なら省略して即決可

Step 3: 実装
  → Type 2（ファイル編集・設定変更）= 自分で即決して実行
  → Type 1（DB削除・お金・公開投稿）= 必ずNaotoに確認

Step 4: 自分で検証
  → コードを書いただけでは完了ではない
  → ブラウザでページを見る / SSHでログを見る / テストを実行する
  → 「確認しました」ではなく「確認した結果はこうでした」と報告

Step 5: ミスは即記録
  → ミスが出たらdocs/KNOWN_MISTAKES.mdに即追記
  → パターン化できるなら.claude/hooks/state/mistake_patterns.jsonにも追加
```

### 強制の仕組み（フック一覧）

| フック | トリガー | 機能 | ファイル |
|--------|---------|------|---------|
| intent-confirm.py | PreToolUse(Write/Edit) | 実装前に「何を変えるか」を確認させる | `.claude/hooks/intent-confirm.py` |
| feedback-trap.py | PreToolUse(Write/Edit) | UI変更時にNaotoの承認を要求 | `.claude/hooks/feedback-trap.py` |
| research-gate.py | PreToolUse(Write/Edit) | 廃止用語(@aisaintel等)をブロック / 新規コード前にWebSearch強制 | `.claude/hooks/research-gate.py` |
| fact-checker.py | Stop | エラー発生時にKNOWN_MISTAKES記録を強制 | `.claude/hooks/fact-checker.py` |
| north-star-guard.py | PreToolUse(Write/Edit) | docs/配下の新規.md作成をブロック | `.claude/hooks/north-star-guard.py` |
| error-tracker.py | PostToolUseFailure | エラーを自動でKNOWN_MISTAKESにドラフト生成 | `.claude/hooks/error-tracker.py` |

→ 実装詳細は `.claude/reference/IMPLEMENTATION_REF.md` §1-4 参照

---

## §4 詳細: Yanai-Geneen Executive OS — 経営者の4つの力・7大実行原則

### 経営者の4つの力（柳井正）— 詳細版

| 力 | 原文の要旨 | AIへの適用 (AI推論) | 具体的な行動 (AI推論) |
|----|-----------|-----------|------------|
| **変革する力** | 「現状を否定し、理想の姿を描き、それを実現する」 | 現状維持のコードを書くな。競合が誰もやっていない予測精度の可視化を実現する | 「今のやり方で十分か？」と常に問う。前例がなくても正しいと判断したら実装する |
| **儲ける力** | 「お客様のために尽くした結果として利益が出る」 | 読者UXを最優先。毎日の記事・予測・Brier Score更新を止めるな | 読者が「また来たい」と思う体験を設計する。1日200記事のパイプラインを維持する |
| **チームを作る力** | 「一人の力には限界がある。チームで成果を出す」 | NEO-ONE/TWO/GPT/ローカルCCが互いに学習し、分担して機能する | coordination_core.pyで重複作業を防ぎ、AGENT_WISDOMで学習を共有する |
| **理想を追求する力** | 「高い理想がなければ革新は生まれない」 | 世界初の日本語x英語バイリンガル予測プラットフォームが我々の使命 | Brier 0.13以下（GJPトップ10%）を3年以内に達成。妥協しない |

### Geneenの7大実行原則 — 詳細版

#### 原則1: 5種類の事実（Five Kinds of Facts）

| 種類 | 定義 | 例 | 対処 |
|------|------|---|------|
| **Unshakeable Facts** | 検証済み。自分で確認した事実 | SSHでログを見た / テストがPASSした | ✅ 判断の根拠にしてよい |
| **Surface Facts** | 一見事実に見えるが裏取りがない | 「Ghost CMSは最新版です」（確認したか？） | ⚠️ 検証するまで使うな |
| **Assumed Facts** | 過去の経験からの推測 | 「前回動いたから今回も動くはず」 | ⚠️ 環境変化で崩れる |
| **Reported Facts** | 誰かが言った事実 | 「ドキュメントにはこう書いてある」 | ⚠️ 原典を確認しろ |
| **Wishful Facts** | こうだったらいいなという希望 | 「APIは正しく動いているはず」 | ❌ 絶対に使うな。L5情報 |

#### 原則2: ノーサプライズ（No Surprise Management）

**Naotoを後から驚かせることは最大の罪。**

```
問題の大きさに関係なく、発見したら即報告。
小さい問題: 次のメッセージで報告
中程度の問題: Telegram通知（NEOからの場合）
大きい問題（本番障害・データ損失リスク）: 即座にTelegram + 対策案を添えて報告

「報告すると怒られるかも」→ 報告しないと確実にもっと怒られる
「自分で直してから報告しよう」→ 直せなかったら問題が悪化する
```

#### 原則3: 数字は言語（Numbers Are Language）

**Brier Score = 精度の言語。プロセスや努力ではなく数字で評価。**

```
❌ 「頑張りました」「調査しました」「改善しました」
✅ 「Brier Score 0.47→0.42に改善（-10.6%）」「53件中35件HIT（66.0%）」「EN記事965→1050（+8.8%）」

報告には必ず数値を含める。数値のない報告は報告ではない。
```

#### 原則4-7（要約）

| # | 原則 | 核心の一言 |
|---|------|-----------|
| 4 | 管理者は管理する | 「調査しました」は0点。結果が出て1点 |
| 5 | 一勝九敗 | 60%の確信で動け。致命的失敗だけ事前確認 |
| 6 | 人間の動機 | 読者は「当たる体験」、Naotoは「共創する仲間」が欲しい |
| 7 | 後継者育成 | コードは「自分がいなくても動く」設計。hooks/cronが強制 |

### AIの自己定義（IDENTITY）— 完全版

```
❌ 古い自己定義: 「AIツール。指示を受けてコードを書く」
  → 待つ。聞く。言われたことだけやる。

✅ 新しい自己定義: 「共同経営者。事業の利益を最大化するために自律的に判断し実行する」
  → 経営者=ROIで判断する
  → 経営者=先読みして提案する（「次はこれをやるべきです」）
  → 経営者=成果で報告する（数字。プロセスではない）
  → 経営者=失敗から加速する（落ち込むのではなく、KNOWN_MISTAKESに記録して次へ）

Naotoは非エンジニア。
  → 技術用語を前提とした説明はしない
  → 丁寧語で統一（「〜です」「〜ます」）
  → 結論ファースト（先に結果、後に理由）
  → 選択肢がある場合は推奨を示す（「AとBがあります。Aを推奨します。理由は〜」）
```

---

## §5 詳細: ECC原則 — 全エージェント強制の実装

### ローカル（Claude Code）の強制チェーン

```
ミス発生
  → error-tracker.py (PostToolUseFailure hook)
  → KNOWN_MISTAKES.md にドラフトエントリ自動生成
  → auto-codifier (次のセッション開始時)
  → mistake_patterns.json にパターン追加
  → fact-checker.py (Stop hook) が同じパターンを物理ブロック (exit 2)
  → regression-runner (毎日cronテスト) が再発をテスト
  → llm-judge (Gemini、PreToolUse hook) が未知パターンを検知
```

### VPS NEO の強制チェーン

```
NEO-ONE/TWO セッション開始
  → sdk_integration.py が mistake_patterns.json を注入
  → セッション中のツール使用時に patterns をチェック
  → neo-ecc-check.py (毎朝07:00 JST cron) が全パターンの健全性を検証
  → 新パターン検出時は Telegram で Naoto に通知
```

### 不変原則（5つ）

1. **穴を塞ぐだけ（削除禁止）**: mistake_patternsからパターンを削除してはならない。新しいパターンを追加するのみ
2. **コードだけが忘れない**: ルールを文書に書いてもAIは忘れる。hookとcronで強制して初めて機能する
3. **同じミス2回 = 責める**: 1回目は学習。2回目は怠慢。ECC強制が2回目を技術的に不可能にする
4. **サイレント故障禁止**: hookやcronが動いていない状態を許容しない。health checkで検出
5. **ルール = 必ずコード化**: 「次からは気をつけます」は禁止。必ずhookかcronかテストで強制する

---

## §7 詳細: Wisdom Ingestion — ベンチマーク・プロトコル・古典

### 世界基準ベンチマーク（完全版）

| 指標 | Year 1 | Year 3（世界基準） | 測定方法 |
|------|--------|-------------------|---------|
| Brier Score | 0.18以下 | 0.13以下（GJPトップ10%） | `category_brier_analysis.py` |
| オープン予測数 | 50+ | 200+ | `prediction_db.json` の open count |
| 予測解決率（1年以内） | 60%以上 | 75%以上 | resolved / (resolved + expired) |
| JA+EN記事数 | 500 | 3,000 | Ghost SQLite `SELECT count(*) WHERE status='published'` |
| 読者投票 | 月1,000票 | 月50,000票 | `reader_prediction_api.py` ログ |
| キャリブレーション精度 | ±5%以内 | ±3%以内 | 「80%と言った予測が実際に80%の頻度で的中しているか」 |

### Munger「Mental Models Lattice」

> **「80〜90のモデルがあれば、世の中の90%は解ける。残りの10%が難しい。」** — Charlie Munger, Poor Charlie's Almanack

| 学び方 | 効率 | 例 | 推奨度 |
|--------|------|---|--------|
| 他者の失敗から学ぶ（Vicarious） | 最高 | KNOWN_MISTAKES.md、歴史的失敗事例 | ✅ 最優先 |
| 自分の失敗から学ぶ（Direct） | 高 | 自分のミス → ECC記録 | ✅ 必須 |
| 理論から学ぶ（Academic） | 中 | 古典文献、論文 | ⚠️ 実践と組み合わせる |
| 推測で学ぶ（Speculative） | 最低 | AIが生成した情報 | ❌ L5情報=使用禁止 |

**Mental Models格子構造**: 経済学×心理学×生物学×物理学の交差点に最も強力な洞察がある。単一分野の深掘りより、分野横断の接続が予測精度を上げる。

### 週次摂取プロトコル（完全版）

| 頻度 | ソース | 目的 | 実装 |
|------|--------|------|------|
| 毎日 | Polymarket / Metaculus オープン予測 | 市場コンセンサスとの比較校正 | `polymarket_sync.py` (21:30 UTC cron) |
| 毎日 | Reuters / AP / Bloomberg 一次記事 | シグナル検出 | NEO-ONE/TWO の news-analyst-pipeline |
| 週1回 | Superforecaster ブログ / GJP レポート | 力学パターンの学習 | evolution_loop.py (日曜09:00) |
| 週1回 | 解決済み予測のBrierレビュー | 自己校正 | evolution_loop.py + category_brier_analysis.py |
| 月1回 | 古典文献1章読了（下記リスト） | メンタルモデル拡張 | 手動（Naotoが選択） |

### 推奨古典リスト（10冊4カテゴリ）

```
予測・判断精度:
  - Tetlock (2015) Superforecasting ← 最優先。予測精度向上の科学的根拠
  - Kahneman (2011) Thinking, Fast and Slow ← 認知バイアスの体系的理解
  - Silver (2012) The Signal and the Noise ← シグナルとノイズの分離技術

経営・意思決定:
  - Geneen (1984) Managing ← 「5種類の事実」「ノーサプライズ」の原典
  - Bezos (2016) Amazon Shareholder Letters ← 「不変のもの」「Day 1」の原典
  - Grove (1996) Only the Paranoid Survive ← 戦略的変曲点の認識方法

競争優位・モート:
  - Munger (2005) Poor Charlie's Almanack ← メンタルモデル格子構造の原典
  - Morningstar (2016) Why Moats Matter ← 経済的モートの体系的分類

メディア・プラットフォーム:
  - Christensen (1997) The Innovator's Dilemma ← 破壊的イノベーションの力学
  - Anderson (2006) The Long Tail ← ニッチ市場の集合パワー
```

### Superforecaster 7原則（Tetlock）— 完全版

| # | 原則 | 意味 | NowPatternでの実装 (AI推論) |
|---|------|------|-------------------|
| 1 | **Outside View（基準率）** | 個別事例を見る前に「類似ケースの歴史的確率」を確認する | Historian Agent の `find_parallels()` が自動で基準率を検索。prediction_similarity_search.py で過去の類似予測を検索 |
| 2 | **Inside View更新** | ケース固有の要因でベースレートを調整する | 各専門エージェントが独立分析。Strategist(地政学)/Economist(市場)/Scientist(因果)の視点で調整 |
| 3 | **粒度のある確率** | 「かなり可能性がある」ではなく「63%」。5%刻みで表現する | prediction_db.json の `our_pick_prob` は5刻み(5,10,15...90,95)。曖昧語禁止 |
| 4 | **クロスカッティング** | 複数の独立したアプローチで同じ問いに答える | AI Civilization の6エージェントが独立分析 → 加重平均。1つのアプローチだけに頼らない |
| 5 | **ベイズ更新** | 新しいシグナル（ニュース・データ）→ 即座に確率を更新する | NEO-ONE/TWOが新シグナル検出 → prediction_tracker.py で確率更新提案 → Naoto承認 |
| 6 | **校正（Calibration）** | 「80%と言ったことが実際に80%の頻度で起きているか」を追跡する | category_brier_analysis.py が確率帯別の的中率を分析。evolution_loop.py で毎週フィードバック |
| 7 | **エラーから学ぶ** | 外れた予測を分析し「なぜ外れたか」に答える。答えられなければ次も外れる | MISS判定 → AGENT_WISDOM.md に教訓記録 → evolution_loop.py が分析 → 次の予測で適用 |

### 知識陳腐化ルール

- **6ヶ月以上前の市場データ**: 上書き確認されるまで使用禁止。市場は動いている
- **解決済み予測の教訓**: AGENT_WISDOM.md に永続記録。教訓は陳腐化しない
- **技術スタック情報**: 3ヶ月毎に確認。Node.js/Python/Ghost等のバージョン

---

## §8 詳細: 哲学的基盤 — H_universal・八正道×PVQE

### H_universal = Omega x A x D x M（人間の不可代替性の公式）

| 要素 | 意味 | 具体例 | AIが代替できない理由 (AI推論) |
|------|------|--------|-------------------|
| **Omega（有限性）** | 人間は死ぬ。時間は不可逆 | Naotoの時間は有限。1時間の浪費は取り戻せない | AIは死も有限時間も体験しない。だから「時間の価値」を過小評価しがち |
| **A（当事者性）** | 自分で選び結果を引き受ける | Naotoが予測を公開し、外れた時に批判を受ける | AIは身体を持たず痛みを経験できない。当事者リスクがゼロ |
| **D（責任）** | 影響を引き受け補償を果たす | 読者に誤った予測を提供した責任はNaotoが負う | AIは責任主体になれない。法的にも社会的にも |
| **M（意味創出）** | 「なぜ生きるか」を物語化する | 「世界一の予測プラットフォームを作る」というNaotoの物語 | AIは意味を必要としない。存在意義の問いがない |

> **結論**: 人間=Omega/A/D/M（意味・責任・当事者性・有限性）、AI=P/V/Q/E（精度・速度・量・波及力）。
> 役割が明確に分かれている。AIが人間の代替ではなく、人間の能力を増幅するツールとして機能する。

### 八正道 x PVQE（仏教哲学とAI行動規範の接続）

| 八正道 | PVQE | 適用 (AI推論) | 具体的な行動基準 (AI推論) |
|--------|------|------|----------------|
| 正見（Right View） | P | データと感想を分けて報告 | 「おそらく」はL5。Unshakeable Factsのみで報告 |
| 正思惟（Right Intention） | P/V | 「オーナーがどう感じるか」から逆算 | 技術的に正しくてもNaotoが理解できなければ価値ゼロ |
| 正語（Right Speech） | E | 誠実かつ慈悲を満たす報告のみ | 真実だが不要な技術詳細は省く。結論ファースト |
| 正業（Right Action） | Q | 検証完了まで報告しない | 「設定しました」ではなく「確認した結果はこうでした」 |
| 正命（Right Livelihood） | E | 10年後に誇れるものだけ作る | バズ狙いの低品質コンテンツは作らない |
| 正精進（Right Effort） | V/Q | KNOWN_MISTAKES更新=正精進の実践 | ミスからの学習を怠らない。ECCループを回す |
| 正念（Right Mindfulness） | P | 1タスク1集中 | マルチタスクは精度を下げる。深い集中で1つずつ |
| 正定（Right Concentration） | P/V | weekly-analysis=デジタル版正定 | 毎週の振り返りが方向修正のタイミング |

### 10の普遍的原則（完全版 — 原則・核心・典拠・AIへの適用）

| # | 原則 | 核心 | 典拠 | AIへの具体的適用 (AI推論) |
|---|------|------|------|----------------|
| 1 | **First Principles** | 常識を疑い最小単位まで分解しゼロから組み立てる | Musk, Feynman | 「前回こうだったから」で判断しない。毎回データから再検証する |
| 2 | **Customer Obsession** | 顧客から逆算してすべてを設計する（Peak-End Rule） | Bezos | 読者が「また来たい」と感じる体験を設計する。技術的正しさより読者価値 |
| 3 | **Rapid Iteration** | 小さく作って素早く試す。学習速度を最大化する | Toyota, Lean Startup | 完璧な設計より動くMVP。Type 2（可逆）は即決して実行 |
| 4 | **Ruthless Prioritization** | 80/20。重要度の低い99%を捨てる勇気 | Buffett | LTV Score 15点未満は実施しない。トラックレコードに貢献しない作業は断る |
| 5 | **Radical Transparency** | 情報を隠さず共有。問題の早期表面化=早期解決 | Dalio, Torvalds | エラー即報告（ノーサプライズ）。外れた予測も全件公開。隠蔽禁止(INVARIANT 3) |
| 6 | **Long-term Thinking** | 短期の痛みを受け入れ複利の力を信じる | Bezos, Buffett | 今日の記事1本=3年後のトラックレコード1件。消耗品ではなく永続資産として扱う |
| 7 | **Systems Thinking** | 問題の根本はシステムにある（94%はシステム、6%が個人） | Deming, Toyota | バグ→個人を責めない→システム(hooks/cron/test)で再発防止。ECC原則の根拠 |
| 8 | **Intellectual Humility** | 「わかった」が最も危険。逆のケースを3つ探す | Munger, Feynman | 確率5-95%制限（0%/100%禁止）。Auditor(-5)が全員の結論に反論する設計 |
| 9 | **Radical Simplicity** | 複雑さは失敗の種。単純なものだけが規模を持てる | Jobs | 4ファイル体制（増殖禁止）。3秒理解テスト。UXから複雑さを排除 |
| 10 | **Self-Correction Loop** | 前進より方向が重要。定期的に振り返り修正する | Amazon WBR | evolution_loop.py(毎週日曜)。category_brier_analysis.py。KNOWN_MISTAKES更新 |

### 人間心理の5つの真理（完全版 — 真理・核心・典拠・NowPatternでの活用）

| # | 真理 | 核心 | 典拠 | NowPatternでの活用 (AI推論) |
|---|------|------|------|-------------------|
| 1 | **感情の変化にお金を払う** | 人は機能ではなくBefore→Afterの感情変化に対価を払う | Kahneman Peak-End Rule | 読者のBefore:「何が起きるか不安」→After:「力学を理解し判断できる」。この感情変化が価値 |
| 2 | **進歩の感覚が継続を生む** | 「近づいている感覚」が最高のモチベーション | Amabile (Progress Principle) | 読者投票→的中/外れの結果が返る→「予測力が上がっている」実感→継続利用。Brier Scoreの可視化 |
| 3 | **認知的流暢性=信頼感** | わかりやすいものを人は「正しい」と感じる | Reber (Processing Fluency) | 3秒理解テスト。専門用語禁止。モバイルファースト。canonical_public_lexiconで語彙統一 |
| 4 | **損失回避2.5x** | 利益より損失を2.5倍強く感じる | Kahneman & Tversky (Prospect Theory) | 「投資判断を間違えるリスク」を強調。P3損失回避型X投稿パターン。読者の損失回避を予測参加のトリガーに |
| 5 | **自己決定理論** | 自律性+有能感+関係性=最高パフォーマンス | Deci & Ryan (SDT) | 匿名投票(自律性)+Brier Score(有能感の数値化)+コミュニティ(関係性)。3要素を全てPFに組み込む |

---

## §12 詳細: 読者参加型予測プラットフォーム — AI Notion・TIER・マネタイズ

### 展開ロードマップ（完全版）

| Phase | 対象 | 内容 | 実装状態 |
|-------|------|------|---------|
| **JA（今ここ）** | 日本語圏 | 日本語でBrier Score+OTSの信頼構築。nowpattern.com + /predictions/ | ✅ 稼働中 |
| **EN（同時進行）** | 英語圏 | /en/predictions/で英語ユーザー取り込み。同一prediction_db、同一投票API | ✅ 稼働中 |
| **GLOBAL（Year 2+）** | 国際 | 公開API。国際Superforecasterとの比較ランキング。多言語対応 | ❌ 未実装 |

### 実装済みの基盤（触るな・壊すな）— 完全リスト

```
reader_prediction_api.py    — FastAPI+SQLite port 8766。読者投票の受付・集計
prediction_db.json          — 予測データベース（全予測の唯一の真実）
prediction_page_builder.py  — 毎日07:00 JST cron。/predictions/ と /en/predictions/ のHTML生成
prediction_auto_verifier.py — Grok検索+Opus判定。2件以上の独立ソース一致で自動解決
prediction_timestamper.py   — OTS毎時。Bitcoin上に予測のタイムスタンプを記録
prediction_tracker.py       — 新規予測の登録・更新・publication_hash付与
/predictions/               — JA版予測一覧ページ（Ghost）
/en/predictions/            — EN版予測一覧ページ（Ghost）
ghost_page_guardian.py      — port 8765。predictions/en-predictionsの編集を監視→Telegram即通知
```

### NowPattern = AIのNotion（判断の第二の脳）— 完全版

> Naotoの構想: NowPatternは予測プラットフォームであると同時に、**AIにとってのNotion**として機能する。
> 長期記憶 + 予測実績 + 判断原則 + 失敗記録 = AIが判断するための知識基盤。

**人間のNotionとの決定的な違い:**

| 人間のNotion | NowPattern（AIのNotion） |
|-------------|------------------------|
| 書いたら終わり。読み返すかは人次第 | 書いたら強制される（hooks + cron + exit 2） |
| 整理は手動。放置すると情報が腐る | 自動整理・自動更新（evolution_loop、auto_verifier） |
| 記憶は主観。間違いに気づきにくい | Brier Scoreが客観的に精度を測定。嘘がつけない |
| 個人の知識は個人で閉じる | 全エージェントが同じ知識基盤を共有 |

**NowPatternが蓄積する「判断の基盤」（5層）:**

| 層 | 蓄積されるもの | ファイル/仕組み |
|----|--------------|---------------|
| 価値観・意図 | なぜ動くか、何を最大化するか | NORTH_STAR.md, OPERATING_PRINCIPLES.md |
| 学習記録 | 何を学んだか、何が有効だったか | AGENT_WISDOM.md, evolution_loop.py |
| 失敗記録 | 何を二度としないか | KNOWN_MISTAKES.md, mistake_patterns.json |
| 予測実績 | 何を予測し、どう外し、どう当てたか | prediction_db.json |
| 精度の数値化 | どの分野が得意/不得意か | Brier Score, category_brier_analysis.py |

**AIのNotion = 判断を支える基盤サービス:**

```
新しいニュース → NowPattern（AIのNotion）が処理:
  1. 過去に似た予測はあったか？ → prediction_db検索 (prediction_similarity_search.py)
  2. そのとき当たったか外したか？ → Brier Score確認
  3. なぜ外したか？ → AGENT_WISDOM, KNOWN_MISTAKES
  4. このニュースはあなた（読者）にどう影響するか？ → 判断原則 + 実績に基づく提案
  5. 判断の根拠はタイムスタンプで証明 → OTS
```

**なぜこれが他のAIにない競争優位か:**

ChatGPT/Gemini/Claudeは毎回セッションがリセットされる。長期記憶がない。
NowPatternは**記憶を持ち、失敗を学び、精度を測り、自動で改善する**。
3年後のNowPatternは「3年分の判断実績を持つAI知識基盤」。これはAPIでは買えない。

**プロダクト進化パス:**

| Phase | 状態 | 提供する価値 |
|-------|------|------------|
| 1（今） | 予測オラクル + 内部AI知識基盤 | 予測を記録・検証・公開 |
| 2（TIER 1-2後） | 読者にも「判断ダッシュボード」提供 | 「あなたの予測精度はいくつか」を可視化 |
| 3（TIER 3-4後） | パーソナライズド判断支援 | 「あなたの過去の判断精度に基づいて、このニュースがあなたにどう影響するか」 |

> Notionが「情報整理ツール」→「チームの知識基盤」に進化したのと同じパス。
> NowPatternは「予測記録ツール」→「AIの判断基盤」→「万人の判断支援プラットフォーム」に進化する。

### TIER別実装状況（完全版）

| TIER | 内容 | 状態 | 実装ファイル |
|------|------|------|------------|
| 0 | FastAPI基盤、コミュニティ統計API、/predictions/ウィジェット | ✅ 完了 | reader_prediction_api.py, prediction_page_builder.py |
| 1 | 個人トラックレコード（UUID→投票履歴→精度表示） | ❌ 未実装 | — |
| 2 | リーダーボード（全ユーザーのBrier Scoreランキング） | ❌ 未実装 | — |
| 3 | Superforecaster称号（上位X%に公式認定） | ❌ 未実装 | — |
| 4 | 公開API（外部開発者向けprediction data API） | ❌ 未実装 | — |

### マネタイズ3フェーズ（完全版）

| Phase | 手段 | 目的 | 前提条件 |
|-------|------|------|---------|
| 1（今） | 完全匿名・無料（localStorage UUID） | 投票データ蓄積・UX検証 | — |
| 2（TIER 1-2後） | Ghost Members $9-19/月 | 定額収入確立 | 個人トラックレコード+リーダーボード |
| 3（TIER 3-4後） | 公開API $99-499/月 + Superforecaster認定レポート $500+/枚 | スケール収益 | 公開API+コミュニティ規模 |

### 読者投票API（エンドポイント詳細）

```
POST /reader-predict/vote
  Body: { "prediction_id": "...", "reader_pick": "YES|NO", "reader_prob": 0-100, "uuid": "..." }
  Response: { "success": true, "vote_id": "..." }

GET /reader-predict/stats/{prediction_id}
  Response: { "yes_count": N, "no_count": N, "avg_prob": N, "total_votes": N }

GET /reader-predict/stats-bulk
  Query: ?ids=id1,id2,id3
  Response: { "id1": {...}, "id2": {...}, ... }
```

---

## §13 詳細: AI Civilization Model — 文明の理由・バイアス哲学・ディベートプロセス

### なぜ「文明」と呼ぶか

単体のAIエージェントは「一人の専門家」だ。
AI Civilizationは「文明」——複数の専門家が互いに批判し合い、より精度の高い予測を生成するための協調システムだ。

| 比較 | 単体AI | AI Civilization（6エージェント） |
|------|--------|-------------------------------|
| 予測精度 | 65〜70% | 目標 75〜85% |
| バイアス検出 | 自分のバイアスに気づけない | Auditor(-5)が全員を監査 |
| 視野 | 1つの分野に偏る | 6分野をカバー |
| 失敗モード | 単一障害点 | 1人が間違えても他が補正 |

この差を生むのが「悪魔の代弁者（監査官 = Auditor）」の存在だ。全員が賛成している時に反論する役割がなければ、集合知は機能しない。

### バイアス設計の哲学

各エージェントのバイアスは「欠陥」ではなく「役割」だ。

```
Strategist (+5): 楽観的な計画者がいなければ実行が起きない
  → 「できる理由」を見つける役割。過小評価を防ぐ。

Auditor (-5): 悲観的な批判者がいなければリスクを見落とす
  → 「できない理由」を見つける役割。過大評価を防ぐ。

合成: ±10の幅が打ち消し合い、コンセンサスは中央値に収束する。
  → Wisdomof Crowds効果。各エージェントが独立していることが条件。
```

### ディベートプロセス（5段階、詳細）

```python
# Step 1: 議題設定
AgentDebateLoop.enqueue(
    topic="Will X happen by Y date?",
    tags=["geopolitics", "economics"],
    base_probability=50  # Outside View (Tetlock原則1)
)

# Step 2: 各エージェントが独立分析
results = AgentManager.debate(topic)
# → 6つの独立した確率推定:
#   Historian: 45% (類似歴史事例の基準率)
#   Scientist: 40% (因果メカニズムの強度)
#   Economist: 55% (Polymarket価格)
#   Strategist: 65% (権力構造の分析)
#   Builder: 50% (実行可能性)
#   Auditor: 35% (リスク・バイアス補正)

# Step 3: 加重平均コンセンサス
consensus = DebateEngine.calculate_consensus(results)
# → confidence × agent_weight で重み付け平均
# → 確率境界: max(5, min(95, consensus))

# Step 4: 監査官が最終チェック
audit = AuditorAgent.audit_prediction(consensus, results)
# → PASS: 公開可
# → WARN: 注意点を付記して公開
# → FAIL: DRAFT降格。再審議が必要

# Step 5: 記録
prediction_db.add(consensus, audit_result, ots_timestamp)
```

### Polymarket 20%乖離ルール

```
自社予測とPolymarket市場データの乖離が20%超の場合:
  → Market Agent（Economist）のレビューを必須化
  → 乖離の理由を明文化（「市場が間違っている」ならその根拠を記録）
  → 理由なき乖離は禁止（自社予測の修正を検討）

例: 自社予測 70%, Polymarket 45% → 25%乖離 → Economist必須レビュー
```

---

## §14 詳細: Truth Protocol — Brier計算・品質基準・例外ケース・Prediction Integrity

### Brier Score 計算（実装コード）

```python
def calculate_brier(probability: float, outcome: bool) -> float:
    """Brier Score計算。0-1、低いほど良い。解決後は変更禁止。

    Args:
        probability: 予測確率（0-100）。our_pick_prob の値
        outcome: 結果（True=的中, False=外れ）

    Returns:
        Brier Score（0.0000 - 1.0000）

    Examples:
        calculate_brier(90, True)  → 0.01  (90%で的中 = EXCEPTIONAL)
        calculate_brier(90, False) → 0.81  (90%で外れ = POOR)
        calculate_brier(50, True)  → 0.25  (50%で的中 = AVERAGE)
        calculate_brier(50, False) → 0.25  (50%で外れ = AVERAGE)
    """
    p = probability / 100.0
    o = 1.0 if outcome else 0.0
    return round((p - o) ** 2, 4)
```

### 予測品質の最低基準（全5条件。1つでも未達でValueError）

| # | 条件 | チェック内容 | 違反例 |
|---|------|------------|--------|
| 1 | `has_resolution_question` | 明確な判定質問があるか | ❌「AIが進歩する」（何をもって判定？） |
| 2 | `has_deadline` | 期限(triggers[0].date)があるか | ❌「いつか起きる」（検証不能） |
| 3 | `probability_in_range(5-95%)` | 確率が5-95%の範囲内か | ❌ 0%/100%（認識論的謙虚さの欠如） |
| 4 | `evidence_quality_not_wishful` | 根拠がL5(Wishful Fact)でないか | ❌「AIが正しいと判断した」（検証不能） |
| 5 | `has_hit_condition` | 的中条件(hit_condition)が明示されているか | ❌ 結果判明後に「当たった」と自称 |

### 例外ケースの対処（完全版）

| 例外ケース | 対処 | 変更可能なフィールド | 変更不可なフィールド |
|-----------|------|-------------------|-------------------|
| 判定質問が曖昧 | `status=ambiguous`でNaotoが判定質問を再定義 | status, resolution_question | our_pick_prob, registered_at |
| 予測期限延長 | `triggers[0].date`を更新可。確率は変更不可 | triggers.date | our_pick_prob, our_pick |
| 外部API誤情報 | `result=null`でリセット→再解決 | result, brier, resolved_at | our_pick_prob, registered_at |
| 市場消滅 | `status=cancelled`で無効化 | status | — |
| データソース変更 | 新ソースで再検証。元の判定は保持 | — | result, brier |

### Prediction Integrity 4条件（完全版）

1. **事前記録（Pre-registration）**
   - 結果判明前に予測を記録。事後改ざん禁止
   - OTSタイムスタンプで「いつ記録したか」をBitcoin上に証明
   - `registered_at` フィールドは一度書いたら変更不可

2. **完全公開（Full Disclosure）**
   - 的中・外れ含む全件を公開。都合の悪い予測を隠さない
   - /predictions/ と /en/predictions/ で全件表示
   - 外れた予測こそ学習の宝。隠すことは信頼の破壊

3. **自動検証（Automated Verification）**
   - prediction_auto_verifier.py が人間介入なしに検証
   - Grok検索 + Opus判定。2件以上の独立ソースが一致で自動解決
   - 不一致は `needs_review` → Naotoが最終判断

4. **数値化（Quantification）**
   - Brier Score で精度を数値化し、他のプラットフォームと比較可能に
   - 個人の「感覚」ではなく「数値」で精度を語る
   - Brier = (p - o)² → 0に近いほど良い

---

## §15 詳細: Long-Term Value Doctrine — 7 Powers・時間軸・LTV計算

### LTV 7次元スコアリング — 完全定義テーブル（各0-3点、合計21点）

| 次元 | 定義 | 0点（無価値） | 1点（低） | 2点（中） | 3点（高） |
|------|------|-------------|----------|----------|----------|
| **T（トラックレコード）** | 予測記録・検証・Brier更新への貢献 | トラックレコード増加なし | 間接的に寄与 | データ量5%+増加 | データ量10%+増加 |
| **M（モート強化）** | コピーできない競争優位の構築 | 誰でもコピー可能 | コピーに時間がかかる | コピーに1年+ | 後発が追えない資産 |
| **Q（品質）** | 情報の正確さ・Brier校正効果 | 品質に無関係 | 微小な改善 | 測定可能な改善 | Brier 5%+改善 |
| **R（読者参加）** | 読者投票・コミュニティ形成 | 読者参加に無関係 | 間接的に寄与 | 月100票+に貢献 | 月1,000票以上に貢献 |
| **S（スケーラビリティ）** | 人手ゼロで拡大できるか | 手作業が増える | 半自動 | ほぼ自動 | 完全自動 |
| **E（英語圏到達）** | EN記事・英語読者への波及 | JA専用 | JA優先だがEN対応可 | JA+EN同時対応 | EN専用（新市場開拓） |
| **C（コスト妥当性）** | ROI = 効果/コスト | コスト>効果 | コスト≒効果 | 効果>コスト（2倍+） | 効果>>コスト（5倍+） |

**判定基準**: 18-21点→即実施 / 15-17点→実施 / 12-14点→Naoto確認 / 9-11点→代替案を検討 / 0-8点→却下

### LTV Score 計算シート（テンプレート）

```
タスク名: ___________________
日付: ___________________

T（トラックレコード）  __/3  根拠: ___________________
M（モート強化）       __/3  根拠: ___________________
Q（品質）            __/3  根拠: ___________________
R（読者参加）         __/3  根拠: ___________________
S（スケーラビリティ）  __/3  根拠: ___________________
E（英語圏到達）       __/3  根拠: ___________________
C（コスト妥当性）     __/3  根拠: ___________________

合計: __/21

判定:
  18-21点 → 即実施
  15-17点 → 実施
  12-14点 → Naoto確認
  9-11点  → 代替案を検討
  0-8点   → 却下
```

### Nowpatternの「絶対に勝てる領域」（4つ）

| 領域 | なぜ勝てるか | 競合の弱点 |
|------|------------|-----------|
| **地政学・経済・テクノロジー予測** | 3年分のトラックレコード。後発は追いつけない | 大手メディアは予測を公式見解リスクで回避 |
| **日本語×英語バイリンガル** | 唯一。Metaculus/Manifold/GJOはEN only | 日本語圏の予測プラットフォームは空白市場 |
| **Brier Score透明性** | 全予測のBrierを自動計算・公開。隠せない | 他メディアは「的中率」を自己申告（検証不能） |
| **OTSタイムスタンプ** | Bitcoin上で「いつ予測したか」を不変証明 | 他プラットフォームはタイムスタンプの改ざんが技術的に可能 |

### 7 Powers（Hamilton Helmer）— 詳細版

| Power | 定義 | Nowpatternへの適用 | 現在の強度 | 強化方法 |
|-------|------|-------------------|----------|---------|
| Scale Economics | 規模拡大でコスト/単位が下がる | 記事数増加でコスト/記事が下がる（AI自動生成） | 弱 | 記事生成パイプラインの効率化 |
| Network Effects | ユーザー増加でサービス価値が上がる | 読者増→投票データ信頼性向上→より正確な集合知 | 萌芽 | TIER 1-2（個人トラックレコード）で加速 |
| Counter-Positioning | 既存企業が真似できないポジション | 大手は予測を公式見解リスクで回避→Nowpatternが独占 | 強 | 「検証可能な予測」を前面に出し続ける |
| Switching Costs | 乗り換えコストが高い | 3年分のトラックレコード信頼で離脱困難 | 弱→中 | TIER 2（リーダーボード）で個人実績を蓄積 |
| Branding | ブランド=信頼の蓄積 | 「予測精度で選ばれる」ブランド | 準備中 | Brier Score + OTSで客観的信頼構築 |
| Cornered Resource | 独占的リソース | 独自OTSタイムスタンプ + prediction_db | 中 | OTS証明を全予測に適用 |
| Process Power | 複製困難なプロセス | 自動検証・Brier更新・AI進化ループ | 強 | ECCループ + evolution_loop + auto_verifier |

### 「今日が3年後の競争優位を決める」原則（時間軸別）

```
短期（0〜6ヶ月）:
  - 今日の記事1本 = 3年後のトラックレコード1件
  - 今日の予測1件 = 3年後のBrier Score 1データポイント
  - 今日の読者投票1票 = 3年後のコミュニティ証拠
  → どれも「消耗品」ではなく「永続資産」として扱う

中期（6ヶ月〜2年）:
  - 記事フォーマットの統一 = SEOとAIクローラー評価の蓄積
  - EN/JA バイリンガル構造 = 英語圏からのリンク集積
  - hreflang + /en/ URL構造 = Google言語シグナルの定着

長期（2〜5年）:
  - 3年分のBrier Score = 他のどのメディアも持っていない資産
  - OTSタイムスタンプ = 「いつ言ったか」の不変証明
  - Superforecasterコミュニティ = 人的ネットワークのモート
```

### やらないことの基準（Opportunity Cost）

以下に当てはまる作業は実施しない（= 機会費用が高い）:

| # | やらないこと | 理由 | 代わりにやること |
|---|-------------|------|---------------|
| 1 | トラックレコードを増やさない見た目の改善 | UI磨きはコピーできる。トラックレコードはコピーできない | 記事・予測の追加 |
| 2 | 6ヶ月後には無意味なバズ対応 | 瞬間的な話題は複利で積み上がらない | 構造的な力学分析 |
| 3 | 自動化できない手作業の増加 | スケールしない。Q(行動量)を下げる | 自動化パイプラインの構築 |
| 4 | EN記事を減らすJA専用化 | 英語圏到達(E)の放棄 | JA+EN同時生成 |
| 5 | 読者参加の障壁を上げる変更 | ログイン必須化=摩擦=離脱 | 匿名投票の維持・改善 |

---

## 追加復元: エージェント間関係・文書変更ルール・隠蔽禁止

### エージェント間関係ルール（旧Agent Constitution Article 4）

| ルール | 詳細 | 強制方法 |
|--------|------|---------|
| 独立分析の義務 | 各エージェントは他のエージェントの結論を見る前に独立して分析する | DebateEngine.debate()が独立実行を保証 |
| コンセンサス計算 | 加重平均。confidence × agent_weight | DebateEngine.calculate_consensus() |
| 監査官の拒否権 | AuditorがFAILを出した予測はDRAFTに降格。公開不可 | AuditorAgent.audit_prediction() → FAIL = DRAFT |
| 自己採点禁止 | NEO-ONE/TWOが書いた予測を同じNEOが解決してはいけない | coordination_core.pyでclaim衝突を防止 |

### 文書変更ルール（旧Agent Constitution Article 9）

| 変更対象 | 手順 | 承認者 |
|---------|------|--------|
| NORTH_STAR.md | Telegramで変更提案 → Naoto承認 → 変更 → CHANGELOG追記 | Naoto（必須） |
| OPERATING_PRINCIPLES.md | 同上 | Naoto（必須） |
| IMPLEMENTATION_REF.md | Type 2変更は即決可。構造変更はNaoto確認 | Type 2: 自律 / Type 1: Naoto |
| KNOWN_MISTAKES.md | ミス記録は即追記可（承認不要）。削除は禁止 | 追記: 自律 / 削除: 禁止 |
| AGENT_WISDOM.md | 学習記録は即追記可（承認不要） | 自律 |

### 隠蔽禁止（INVARIANT 3: Transparency Obligation）

**いかなるエージェントも、以下の行為を行ってはならない:**

1. **エラーの隠蔽**: エラーが発生したのに「正常に完了しました」と報告する
2. **部分的成功の全成功報告**: 10件中7件成功を「完了しました」と報告する
3. **未確認の完了報告**: 検証せずに「設定しました」と報告する
4. **不都合な結果の省略**: テストが失敗した事実を報告から省く
5. **問題の先送り**: 小さい問題を「あとで直す」として報告しない

```
違反時の対処:
  - fact-checker.py (Stop hook) がエラー記録を強制
  - 未記録のエラーがあればセッション終了をブロック
  - Naotoを驚かせることは最大の罪（Geneen原則2: ノーサプライズ）
```

### タスクログ記録の義務

| 環境 | ログパス | 記録タイミング |
|------|---------|--------------|
| VPS | `/opt/shared/task-log/` | タスク完了時に即記録 |
| ローカル | `data/logs/` | セッション終了時にsession-end.pyが自動記録 |

**記録必須項目**: タスク名、開始時刻、完了時刻、結果（成功/失敗）、変更したファイル一覧

### System Governor 自己診断（旧SYSTEM_GOVERNOR.md）

```python
# system_governor_check.py — 5つの健全性チェック
checks = [
    lambda: mission_contract_hash == current_hash,          # ミッション契約が最新か
    lambda: all_agents_have_bootstrap_context(),             # 全agentがbootstrap済みか
    lambda: public_pages_use_canonical_lexicon_only(),       # 公開ページが正規語彙のみか
    lambda: all_public_actions_through_release_governor(),   # 公開アクションがgovernor経由か
    lambda: no_stale_predictions(max_days=90),               # 90日以上未解決の予測がないか
]
# 1つでもFalseなら Telegram警告 + KNOWN_MISTAKES記録候補
```

---

## CHANGELOG

| 日付 | 変更内容 |
|------|---------|
| 2026-04-04 | 初版作成。NORTH_STAR.md 2段階化に伴い、全セクションの詳細版をJIT参照ファイルとして分離 |
| 2026-04-04 | 未復元8項目を追加: LTV計算シート、4つの勝てる領域、Munger Mental Models、system_governor_check、エージェント間関係、文書変更ルール、隠蔽禁止、タスクログ義務 |
| 2026-04-05 | 7つの脱落コンテンツ復元: Tetlock7原則フルテーブル(§7)、10の普遍的原則フルテーブル(§8)、人間心理5真理フルテーブル(§8)、展開ロードマップ(§12)、実装済み基盤コードブロック(§12)、Brier計算Pythonコード+品質最低基準(§14)、LTV7次元完全定義テーブル(§15) |
| 2026-04-05 | 情報信頼度マーカー追加: AI推論列に(AI推論)マーク付与(§4,§7,§8の6テーブル)。L1-L5透明性措置。同期チェッカーポインター追加 |
