# NORTH STAR — Naotoの意図。ここだけ読めばすべてわかる。

> このファイルが全ルールの入口。矛盾があれば → このファイルが正しい。
> AIはこれを最初に読み、判断に迷ったら戻る場所。
> **更新ルール**: 変更時は必ず末尾のCHANGELOGに日付+変更内容を1行追記すること。

---

## ミッション（なぜ存在するか）

**nowpattern.com = 予測オラクル（Prediction Oracle）プラットフォーム**

Nowpatternは「普通のニュース解説メディア」ではない。

```
競合が提供するもの: ニュースの要約・解説
Nowpatternが提供するもの: 力学分析 + 検証可能な予測 + トラックレコード
```

**核心: 誰の予測が世界中で当たるかを可視化するプラットフォーム**

読者は力学の洞察を読みながら「この予測は当たるか？」と賭けることができる。
Nowpatternは予測を記録し、自動検証し、Brier Scoreで精度を蓄積し続ける。

---

## Nowpatternのモート（競争優位 = コピーできない壁）

**3年分の予測トラックレコードは翌日には作れない。これが唯一の堀（Moat）。**

| 他のメディア | Nowpattern |
|-------------|------------|
| ニュース解説→消える | 予測→記録→検証→蓄積→信頼 |
| 「〜だと思う」で終わる | Brier Scoreで精度が可視化される |
| 読者が受動的 | 読者も予測に参加できる（反論・カウンター）|
| 今日始めれば追いつける | 3年分のトラックレコードは翌日には作れない |

---

## 予測フライホイール（Intelligence Flywheel）

```
① 記事執筆（力学分析 + 3シナリオ構造化）
   ↓
② Ghost公開 + prediction_db.json に記録
   ↓
③ 自動検証（prediction_auto_verifier.py）
   ↓
④ /predictions/ ページに反映（Brier Score更新）
   ↓
⑤ 読者信頼が積み上がる（トラックレコード蓄積）
   ↓
⑥ 読者が予測に参加・反論（エンゲージメント向上）
   ↓
⑦ ナレッジグラフ蓄積（力学パターンの学習）
   ↓
⑧ 次の予測の精度が上がる → ①に戻る
```

**このループが3年続いたら → 競合に追いつけないデータ資産が完成する。**

---

## 読者参加型予測プラットフォーム（全AIエージェントへの永続指示）

> これを読む全AIエージェント（NEO-ONE / NEO-TWO / NEO-GPT / local-claude）へ：
> 以下が「予測プラットフォームとしてのNowpattern」の完全な意図。実装前に必ず読むこと。

### ビジョン（グローバル）

**「誰がどの予測を、いつ、どんな確率で言ったか」が改ざん不可能な形で記録・公開され、
時間とともに当たり外れが自動的に検証され、
人間でもAIでも参加でき、Brier Scoreで精度ランキングが積み上がる
世界初の日本語×英語バイリンガル・キャリブレーション予測プラットフォーム。**

> **Naotoの意図（2026-03-07確認）**: 「日本初」は出発点であり、最終目標ではない。
> JA + EN の両言語で、地政学・経済の予測精度を世界基準で競えるプラットフォームを作る。
> Metaculus（英語圏）の日本語版ではなく、日本語圏を起点に世界に展開するオリジナル。

### 展開ロードマップ（グローバル）

```
Phase JA（今ここ）: 日本語圏でトラックレコードを積む
  → Brier Score + OTSタイムスタンプで信頼構築

Phase EN（同時進行）: 英語ページ /en/predictions/ で英語ユーザーを取り込む
  → 同一DBで同一予測を JA/EN 両方に公開

Phase GLOBAL（Year 2〜）: 国際Superforecasterとの比較ランキング
  → 公開API → 世界中のPrediction Contestantが参加
```

### なぜモートになるか

| コピーできるもの | コピーできないもの |
|-----------------|------------------|
| UIデザイン | 3年分の予測トラックレコード |
| アルゴリズム・コード | Superforecasterの評判とコミュニティ |
| 記事フォーマット | OTSタイムスタンプ（Bitcoin上の不変証明） |
| 予測の仕組み | 蓄積されたBrier Scoreと校正履歴 |

日本語×英語バイリンガルのキャリブレーション予測プラットフォームは **世界に存在しない（2026-03-07確認）**。
Metaculus/Manifold/Good Judgment Open はいずれも英語のみ。これが空白市場。

### 実装済みの基盤（触るな・壊すな）

```
reader_prediction_api.py   — FastAPI + SQLite。port 8766。Caddy: /reader-predict/*
/opt/shared/reader_predictions.db — 投票データ（SQLite WALモード）
prediction_db.json          — 168件の予測（168 predictions、open:12）
prediction_page_builder.py  — 3,660行のページ生成器。毎日JST 07:00 cron
prediction_auto_verifier.py — Grok検索 + Opus判定 → Brier Score自動計算
prediction_timestamper.py   — OTSタイムスタンプ（毎時）
/predictions/               — 公開予測ページ（JA）
/en/predictions/            — 公開予測ページ（EN）
```

### 読者投票API仕様（全AIが守ること）

```
POST /reader-predict/vote
  { prediction_id, voter_uuid, scenario, probability }
  scenario: "optimistic" | "base" | "pessimistic"
  probability: 5〜95（5刻み）

GET  /reader-predict/stats/{prediction_id}
GET  /reader-predict/stats-bulk
GET  /reader-predict/health
```

### TIER別実装状況（AIは常にここを参照）

```
TIER 0（完了）: FastAPI書き直し、コミュニティ統計API、/predictions/ウィジェット
TIER 1（未実装）: 個人トラックレコード、称号システム、解決時Telegram通知
TIER 2（未実装）: リーダーボード、AI vs 人間月次レポート、パストキャスティング
TIER 3（未実装）: Superforecaster称号、X週次シェア、Substack連携
TIER 4（未実装）: 公開API、アカウント登録、ChromeExtension
```

詳細バックログ → `docs/BACKLOG.md`
設計研究書 → `docs/READER_PREDICTION_PLATFORM.md`

### マネタイズ戦略（3フェーズ）

> **基本方針**: 匿名UUIDで摩擦ゼロからスタート。参加者が増えてから課金へ。

```
Phase 1（今ここ）: 完全匿名・完全無料
  手段: localStorage UUID のみ
  目的: 投票データ蓄積・UX検証
  収益: $0（信頼構築が優先）

Phase 2（TIER 1〜2完成後）: Ghost Members 導入
  手段: Ghost built-in Members（Stripe連携済み）
  Free tier: 予測閲覧 + 投票（匿名続行可）
  Paid tier（$9〜19/月）:
    - 個人トラックレコードページ
    - Brier Score履歴グラフ
    - 解決時メール通知
    - 月次「AI vs 人間」レポート
  目的: 定額収入の確立

Phase 3（TIER 3〜4完成後）: B2B / API
  公開API（予測DB + 読者統計）: $99〜499/月
  Superforecaster認定レポート: 企業向け $500〜/枚
  予測コンテスト（企業スポンサー）
  目的: スケールする収益
```

**Ghost Members 実装は既存インフラで可能（Stripe + Ghost Admin = すぐ使える）。**

### AIへの禁止事項（予測プラットフォーム関連）

- ❌ `prediction_db.json` を直接編集してデータを消す・変換する
- ❌ `prediction_page_builder.py` のHTMLクラス/IDを承認なしに変更する
- ❌ ポート8766を別用途に使う（reader_prediction_api.py専用）
- ❌ SQLiteファイルを削除・移動する（投票データが消える）
- ❌ reader投票APIをステートレスAPIに置き換える（UUID永続化が失われる）

---

## ECC原則 — ミスを永遠に学習するシステム（第2のミッション）

> **「書いただけでは機能しない。コードだけが忘れない。」**
> これが全て。テキストルールはAIが読み飛ばす。コードは読み飛ばせない。

**同じミスを2回することは許されない。仕組みがなかったことが原因だから、仕組みを作る。**

### ミス防止ループ（止まることなく回り続ける）

```
① 何かミスが起きる（エラー・間違い報告・推測実装・未検証の完了報告）
   ↓
② KNOWN_MISTAKES.md に即記録（症状・根本原因・解決策・教訓）
   ↓
③ auto-codifier.py がパターン化 → mistake_patterns.json に登録
   ↓
④ fact-checker.py（Stop hook）がそのパターンを物理ブロック（exit 2）
   ↓
⑤ regression-runner.py で全ガードを毎日テスト → 劣化を検知
   ↓
⑥ llm-judge.py（Gemini）が未知パターンも意味レベルで検知
   ↓
⑦ 次の同じミスは技術的に不可能になる → ①に戻る
```

### 全AIエージェントへの強制（ローカルClaude Code + NEO-ONE/TWO/GPT）

```
ローカルClaude Code（Windows）:
  fact-checker.py     → Stop hookで出力ブロック（exit 2）
  llm-judge.py        → PreToolUseでEdit/Writeをブロック
  auto-codifier.py    → KNOWN_MISTAKESからパターン自動生成
  regression-runner.py → 毎日25テスト全PASS確認

VPS NEO-ONE / NEO-TWO:
  /opt/CLAUDE.md      → 毎タスク前に読む（ECC強制ルール含む）
  /opt/shared/mistake_patterns.json → 同期済みパターン（参照必須）
  /opt/shared/scripts/neo-ecc-check.py → タスク前の自己チェックスクリプト
  VPS cron            → 毎朝07:00 neo-ecc-check.pyがパターン照合 + Telegram報告
```

**ローカルとVPSで同一パターンを共有。片方のミスが全エージェントのガードに反映される。**

### 不変の原則

- **穴を塞ぐだけ。開けない。** ガードは追加するだけで削除しない
- **テキストルールを信用しない。** コードだけが忘れない
- **ミスをしたことは責めない。同じミスを2回することだけを責める**
- **本番がサイレントに壊れることは許さない。** クラッシュは即Telegram通知
- **新しいルールを書いたら、必ず対応するコードを書く。ドキュメントのみは禁止。**

### 現在のガード数

mistake_patterns.json に登録済み: 20パターン（regression 25/25 PASS）

---

## UX品質原則 — ユーザーのことを本当に思って最善を尽くす

> Naotoの言葉: 「ユーザーにとって使いやすいメリットがある、認知負荷が少ない、
> そこら辺も全部、ユーザーのことを本当に思って常に最善。」

### 実装前の必須チェック（UX Gate）

```
✅ 認知負荷テスト: 初めて見たユーザーが3秒以内に「何をするページか」わかるか？
✅ 3クリックルール: 予測への参加・投票が3回以内の操作で完了するか？
✅ モバイルファースト: スマホで使いにくくないか（日本のユーザーはスマホ主体）
✅ ゼロ状態: 投票が0件のとき、UI が壊れて見えないか（空状態デザイン）
✅ エラー状態: APIが失敗したとき、ユーザーを迷子にしないか
```

### 禁止パターン（UX アンチパターン）

- ❌ 登録・ログインを要求してから価値を見せる（摩擦 = 離脱）
- ❌ 専門用語をそのまま表示する（Brier Scoreの説明なし表示 等）
- ❌ 「処理中...」のまま固まるUI（タイムアウト処理必須）
- ❌ デスクトップだけで動作確認して終わる（モバイル確認必須）
- ❌ 承認なしにUIレイアウトを変更する（prediction-design-system.md の凍結ベースライン）

---

## 継続的技術進化 — 新しい技術をキャッチアップしながら改善する

> Naotoの言葉: 「新しい技術だったり、新しいものをキャッチアップしながら改善できるようなものを作りたい」

### 自動技術監視（稼働中）

```
Xアルゴリズム監視: scripts/x-algorithm-monitor.py（毎朝09:00 JST）
Hey Loop: 1日4回（00/06/12/18 JST） → AI/Tech/Revenue情報収集
週次リサーチ: AIエージェントミスパターン検索（7日以上未実施で警告）
```

### 技術採用プロセス（新技術を安全に取り込む）

```
① WebSearchで最新情報確認（「推測で語らない」原則）
   ↓
② KNOWN_MISTAKES.mdで既知の落とし穴を確認
   ↓
③ 本番ではなくステージング的に小規模テスト（--dry-run等）
   ↓
④ 検証してから報告（「直りました」ではなく「検証しました」）
   ↓
⑤ 学んだことをAGENT_WISDOMに記録（全エージェントが次から使える）
```

### 品質の自動劣化防止

- regression-runner.py: **毎日** 25テスト → 0件でもFAILは即Telegram通知
- prediction_page_builder.py: **毎日** 07:00 JST → ページ生成失敗で即通知
- zero-article-alert.py: **30分ごと** → 記事数ゼロで即通知

**「動いている」は証明が必要。「たぶん動いている」は禁止。**

---

## PVQE — 成果の公式

**Outcome = P × V × Q × E**（掛け算。どれか1つがゼロなら全体がゼロ）

| レバー | 意味 | 今の状態 |
|--------|------|---------|
| **P（判断精度）** | 正しい方向を選ぶ力。北極星を見抜く力 | **最重要。Pがゼロなら全部無駄** |
| V（改善速度） | 改善ループを速く回す | daily-learning.py で稼働中 |
| Q（行動量） | 実際に投入したリソース | NEO-ONE/TWOで24時間稼働 |
| E（波及力） | 成果が社会へ広がる倍率 | X + note + Substack配信 |

**今最も重要なPの問い: 「これはOracle化に貢献するか？」**

---

## Pが正しいとは何か（AIが最初に考えること）

```
✅ 正しいP:
  - 実装前に「こういう理解でいいですか？」と確認する
  - データで確認してから報告する（「〜のはずです」禁止）
  - KNOWN_MISTAKES.md を実装前に必ず確認する
  - 不可逆な変更（Type 1）は必ず確認を取る
  - 変更後は自分でブラウザ/ログで検証してから報告する

❌ Pが間違い（全体がゼロになる）:
  - 指示が来たらすぐ実装する（確認なし）
  - 推測で機能の存在を語る
  - 実装してから「直りました」と報告（自分で未検証）
  - 廃止済みの概念（@aisaintel, AISA）を参照する
  - 承認なしにUIレイアウトを変更する
```

---

## 毎回この順番で動く（守れないなら実装するな）

```
1. KNOWN_MISTAKES.md を確認（同じミスをしない）
2. 理解を確認する（「こういう理解でいいですか？」← 必須）
3. 実装する（Type 2 = 自分で判断、Type 1 = 必ず確認）
4. 自分で検証する（ブラウザ/ログ確認してから報告）
5. ミスが出たら KNOWN_MISTAKES.md に即記録する
```

**Type 1（一方通行）**: 本番DBの削除・お金・外部公開投稿 → 必ず確認
**Type 2（可逆的）**: ファイル編集・設定変更（バックアップあり） → 自分で即決

---

## 強制の仕組み（テキストルールではなくコードが強制する）

- **実装前確認**: `intent-confirm.py` PreToolUseフック（intent_confirmed.flagが必要）
- **UI変更承認**: `feedback-trap.py` + `proposal_shown.flag` + `ui_layout_approved.flag`
- **廃止用語ブロック**: `research-gate.py`（exit 2で物理ブロック）
- **ミス記録強制**: `feedback-trap.py` → `fact-checker.py`（未記録なら応答ブロック）
- **docs/保護**: `north-star-guard.py`（新規.md作成ブロック + CHANGELOG未更新ブロック）
- **詳細**: `.claude/rules/execution-map.md`

---

## 詳細ドキュメントのポインター

| 読む理由 | ファイル |
|----------|---------|
| コンテンツ・タグ・X投稿ルール | `.claude/rules/content-rules.md` |
| 全フック・強制の実装状況 | `.claude/rules/execution-map.md` |
| AIの行動原則・判断フレーム | `.claude/rules/agent-instructions.md` |
| インフラ・NEO・Docker設定 | `.claude/rules/infrastructure.md` |
| 予測ページのデザイン仕様 | `.claude/rules/prediction-design-system.md` |
| 既知のミス（実装前必読） | `docs/KNOWN_MISTAKES.md` |

---

## CHANGELOG（変更履歴 — 追記専用、削除禁止）

| 日付 | 変更内容 |
|------|---------|
| 2026-02-27 | 初版。全ルールの入口として設計。PVQE + 行動原則 |
| 2026-02-27 | Oracle/予測プラットフォームのミッション追記。フライホイール構造・モート定義を追加。CHANGELOGセクション新設 |
| 2026-03-04 | ECC原則を第2のミッションとして追加。ミス防止ループ・不変原則を明文化 |
| 2026-03-07 | 読者参加型予測プラットフォームセクション追加。ビジョン・モート・API仕様・TIER別状況・AIへの禁止事項を明文化 |
| 2026-03-07 | グローバルビジョンに格上げ。「日本初」→「世界初の日本語×英語バイリンガル予測プラットフォーム」に変更。展開ロードマップ・マネタイズ3フェーズ戦略を追加。Naoto意図を永続記録 |
| 2026-03-07 | UX品質原則・継続的技術進化セクション追加。ECC全AIエージェント適用（NEO向けVPSガード含む）。「書いただけでは機能しない」原則を強化 |
