# Nao Intelligence — 現状把握（Track 1）
> 作成: 2026-03-25 | LEFT_EXECUTOR
> 目的: Nao Intelligence の現在地を偽りなく把握する。"できている感じ" ではなく、何が実際に動いていて何が動いていないかを確認する。

---

## 1. Nao Intelligence とは何か（定義の確認）

Nao Intelligence は、Naoto Nakamura が構築する **個人知性OS（Personal Intelligence Operating System）** である。

単なるツール集合ではない。以下の3つの複利機構を同時に回し続けるシステムとして設計されている。

```
複利機構①: 世界理解の蓄積（World Model の精緻化）
  → 毎日のニュース分析・力学抽出・パターン認識が積み上がる

複利機構②: 予測精度の改善（Prediction Intelligence の校正）
  → 予測→記録→検証→Brier Score更新→次の予測が改善される

複利機構③: 実行品質の改善（Execution Intelligence の再利用）
  → 失敗→KNOWN_MISTAKES記録→次回は同じミスを犯さない
```

Nowpattern は、この OS が世界に価値を提示する **公開面の一つ** にすぎない。

---

## 2. 現在の構成要素マップ

### 2.1 エージェント層（実行者）

| エージェント | 役割 | 動作環境 | 実際の稼働状況 |
|------------|------|---------|------------|
| **NEO-ONE** | CTO・戦略立案・記事執筆(JP) | VPS（/opt/claude-code-telegram/） | ✅ 稼働中（neo-telegram.service） |
| **NEO-TWO** | 補助・並列タスク・翻訳 | VPS（/opt/claude-code-telegram-neo2/） | ✅ 稼働中（neo2-telegram.service） |
| **NEO-GPT** | 技術デバッグ・バックアップ | VPS（/opt/neo3-codex/） | ✅ 稼働中（neo3-telegram.service） |
| **Jarvis** | ローカルOrchestration | VPS（OpenClaw、port経由） | ✅ 稼働中（@openclaw_nn2026_bot） |
| **Claude Code（Local）** | ローカル開発・設計・戦略 | Windows PC（このセッション） | ✅ セッション中のみ |

**構造的問題**: エージェント間のリアルタイム通信がない。NEO-ONEとNEO-TWOはTelegramを通じて指示を受け取るが、エージェント同士が直接通信するchannelが存在しない。

### 2.2 記憶層（Memory Systems）— 現状

| 記憶の種類 | 現在の実装 | ファイル/システム | 評価 |
|-----------|-----------|----------------|------|
| **Session Memory** | コンテキストウィンドウ | （なし） | ⚠️ セッション間で完全消滅 |
| **Operator Memory** | 静的ファイル | `.claude/CLAUDE.md`, `MEMORY.md` | ⚠️ 手動更新。精度54%（MemoryBench比較） |
| **Task Memory** | JSONファイル | `.claude/state/task_ledger.json` | ⚠️ 部分的。構造が浅い |
| **World Knowledge** | Markdownファイル | `/opt/shared/AGENT_WISDOM.md`, `SHARED_STATE.md` | ⚠️ 30分更新。検索機能なし |
| **Prediction Memory** | JSONファイル | `/opt/shared/scripts/prediction_db.json` | ✅ 982件、Brier追跡あり。最も完成度が高い |
| **Execution Memory** | Markdownファイル | `docs/KNOWN_MISTAKES.md` | ⚠️ 手動記録依存。検索・参照機能なし |
| **Reflection Memory** | 週次Python実行 | `evolution_loop.py`（日曜09:00 JST） | ⚠️ 週1回、浅い。Brier分析のみ |

### 2.3 知識取得層（World Intelligence Gathering）

| システム | 実装状況 | 実際の効果 |
|---------|---------|-----------|
| **Hey Loop** | ✅ 1日4回（00/06/12/18 JST）| Reddit/HN/Gemini/Grokからの情報収集 |
| **News Analyst Pipeline** | ✅ 1日3回（10/16/22 JST）| 記事生成のトリガー |
| **X Algorithm Monitor** | ✅ 毎朝09:00 JST | X戦術の最適化 |
| **Evolution Loop** | ✅ 毎週日曜09:00 JST | 予測分析→AGENT_WISDOM更新 |
| **Google Search Console** | ✅ intelligence scriptあり | SEO状況の把握 |

### 2.4 公開面（Publishing Surfaces）

| 公開面 | 実装状況 | 日次量 |
|--------|---------|-------|
| **Nowpattern.com（Ghost）** | ✅ 稼働 | 200記事/日（JP100+EN100）|
| **X（@nowpattern）** | ⚠️ 不安定（本日修正済み）| 目標100投稿/日 |
| **note** | ✅ cron稼働 | 3〜5本/日（キュー空） |
| **Substack** | ✅ コンテナ稼働 | 1〜2本/日 |
| **/predictions/** | ✅ 毎日07:00 JST自動更新 | 982件追跡中 |

### 2.5 自己防御・品質管理層

| システム | 実装状況 | 評価 |
|---------|---------|------|
| **Hooks（20パターン）** | ✅ 稼働 | 物理ブロック機能あり |
| **Article Validator** | ✅ 稼働 | タクソノミー違反を自動ブロック |
| **Ghost Webhook Server** | ✅ 稼働（port 8769）| 記事品質監査 |
| **Service Watchdog** | ✅ 30分cron | 全9サービスの死活監視 |
| **Regression Runner** | ✅ 25/25 PASS | ガード劣化防止 |
| **QA Sentinel** | ✅ 稼働 | 記事品質スコアリング |

---

## 3. 実際の到達点と未実装の分離

### ✅ 実際に動いているもの（Unshakeable facts）

```
- 200記事/日の自動生成・公開（Ghost CMS）
- 予測追跡（982件 → Brier Score 0.1825）
- 3体のVPS常駐エージェント（NEO-ONE/TWO/GPT）
- 週次自己進化ループ（evolution_loop.py）
- 20パターンの物理ブロックガード
- 読者投票API（port 8766）
- ClaimReview schema（本日実装完了）
- X swarm（本日ログ問題修正完了）
```

### ⚠️ 部分実装・不安定なもの

```
- X投稿（cron設定はあるが長期間停止していた → 本日修正）
- Memory system（ファイルベース、精度54%止まり）
- エージェント間通信（Telegramのみ、直接通信なし）
- EN記事生成（lang-jaタグ付与バグ → 2026-03-25修正済み）
- Draft rescue（424件のEN→JAミスラベル → 修正スクリプトあり）
```

### ❌ 設計のみ・未実装のもの

```
- エピソード記憶（各セッションの経験の永続化）
- リアルタイム矛盾検知（古い知識と新しい知識の衝突処理）
- タスク/プロジェクトメモリ（進行中プロジェクトの状態管理）
- 実行リプレイ（過去の実行手順を再利用する仕組み）
- Reflection logging（何を学んだかの構造的記録）
- World model の明示的なグラフ構造
- クロスエージェントメモリ同期（リアルタイム）
- Mem0/Mastra OM等の外部記憶システムとの統合
- 読者個人メモリ（Phase 2への準備だが未着手）
```

---

## 4. 各領域の強弱マップ

```
強い（世界水準の30〜50%）:
  ✅ 予測システム（prediction_db + Brier）
  ✅ 自己防御システム（hooks + validator）
  ✅ コンテンツ生成量（200記事/日）

弱い（世界水準の10〜20%）:
  ❌ Memory system（ファイルベース、精度54%）
  ❌ エージェント間通信・協調
  ❌ Reflection loop の深さ（週1回、浅い）

存在しない:
  ❌ World model の明示的グラフ
  ❌ Episodic memory の永続化
  ❌ 実行リプレイ
  ❌ リアルタイム矛盾検知
```

---

## 5. 各コンポーネントの位置づけ

| コンポーネント | Nao Intelligence における役割 | 現状の問題 |
|-------------|----------------------------|-----------|
| **NEO-ONE** | 戦略知性・記事生成 | 記憶が揮発する（セッション間引き継ぎなし） |
| **NEO-TWO** | 実行知性・並列処理 | NEO-ONEとの記憶共有なし |
| **NEO-GPT** | 技術バックアップ | 翻訳に使えない（Claude Max外）|
| **Jarvis** | ローカルOrchestration | memory精度54%（ファイルベース） |
| **Claude Code** | 設計・実装 | セッション間記憶なし（MEMORY.md依存）|
| **Nowpattern** | 公開面・予測検証面 | データ生成と知識フィードバックが弱い |
| **prediction_db** | 予測メモリの核心 | 他システムへのフィードバックが手動 |
| **AGENT_WISDOM.md** | 共有知識ベース | Markdownファイル、検索不能 |
| **KNOWN_MISTAKES.md** | 実行学習記録 | 手動記録依存、参照時に検索できない |

---

## 6. 最大の構造的問題（根本課題）

現在の Nao Intelligence の最大の問題は、**記憶の断絶（Memory Fragmentation）** である。

```
問題1: セッション間記憶なし
  → 毎セッション、Claude Code は MEMORY.md を読むだけ
  → 過去の判断・失敗・学習が次のセッションに引き継がれない

問題2: エージェント間記憶共有なし
  → NEO-ONEが学んだことがNEO-TWOに届かない
  → 同じミスを別エージェントが繰り返す

問題3: World model が分散・静的
  → AGENT_WISDOM.md + SHARED_STATE.md は静的Markdown
  → 「3ヶ月前の記事が今週の記事と矛盾している」を検知できない

問題4: 実行と反省が分離
  → 実行ログ（task-log/）と反省（KNOWN_MISTAKES.md）が別管理
  → 実行から自動的に学習が生成されない

問題5: 予測と知識が分離
  → prediction_db.json の解決済み予測が AGENT_WISDOM.md に自動反映されない
  → Brier Score 改善に向けた知識更新が週1回（evolution_loop）のみ
```

---

## 7. 現状スコア（世界最高水準を100とした場合の推定）

| 能力領域 | 現状スコア | 根拠 |
|---------|-----------|------|
| 知識取得 | 35/100 | Hey Loopは動いているが、取得した知識の構造化・検索が弱い |
| 記憶精度 | 20/100 | MemoryBench基準で54%（ファイルベース）。ASMR比で約1/5 |
| 予測精度 | 55/100 | Brier 0.1825（FAIR）。目標は0.15以下（GOOD） |
| 実行品質 | 40/100 | 200記事/日は動いているが、品質ばらつきあり |
| 反省・改善 | 25/100 | 週1回の浅い反省のみ。リアルタイム反省なし |
| エージェント協調 | 15/100 | Telegramベースのみ。直接通信・共有メモリなし |
| 世界モデル | 20/100 | 静的Markdownのみ。構造的世界理解なし |
| 公開面 | 50/100 | Nowpatternは稼働中。読者エンゲージメントは発展途上 |

**総合評価: 32/100（世界最高水準比）**

---

*このドキュメントは事実確認ベース。推測には「（推定）」と明記。*
*次ステップ: NAO_INTELLIGENCE_WORLD_BEST_PRACTICES.md（Track 2）*
