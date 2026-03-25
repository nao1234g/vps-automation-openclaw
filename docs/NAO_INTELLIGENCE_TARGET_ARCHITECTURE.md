# Nao Intelligence — ターゲットアーキテクチャ（Track 4）
> 作成: 2026-03-26 | Track 4 完全版（前版を上書き）
> 目的: 世界最高水準を基準に「現実実装可能性で切った」設計。各層を役割/入力/出力/更新契機/自動化範囲/推奨実装候補で定義。
> 原則: 推測は書かない。実装可能なもののみ記載。

---

## 設計原則

```
1. 層は独立して存在できる（他層が落ちても層単体で機能する）
2. 自動化範囲は明示する（「自動化できる」と「すべき」は別）
3. 推奨実装候補は「現行 → Phase 2 → Phase 3」の順で記載
4. 各層のスコアは現在値/目標値で追跡する
```

---

## 全体マップ（9層 + セーフティ横断層）

```
┌──────────────────────────────────────────────────────────────────┐
│  L0: 目的・意図層（Purpose/Intention）— 全層の基底               │
├──────────────────────────────────────────────────────────────────┤
│  L1: センサー・世界状態層（World State）                         │
├──────────────────────────────────────────────────────────────────┤
│  L2: 記憶エンジン層（Memory Engine）                             │
├──────────────────────────────────────────────────────────────────┤
│  L3: 推論エンジン層（Reasoning Engine）                          │
├──────────────────────────────────────────────────────────────────┤
│  L4: 予測エンジン層（Prediction Engine）                         │
├──────────────────────────────────────────────────────────────────┤
│  L5: 実行エンジン層（Execution Engine）                          │
├──────────────────────────────────────────────────────────────────┤
│  L6: 評価層（Evaluation）                                        │
├──────────────────────────────────────────────────────────────────┤
│  L7: 反省・学習層（Reflection/Learning）                         │
├──────────────────────────────────────────────────────────────────┤
│  L8: インターフェース・公開層（Interface/Publishing）            │
├──────────────────────────────────────────────────────────────────┤
│  LA: セーフティ・監査層（Safety/Audit）— 全層に横断             │
└──────────────────────────────────────────────────────────────────┘
```

---

## L0: 目的・意図層（Purpose/Intention Layer）

> **スコア: 現在 55 / 目標 85**

| 項目 | 内容 |
|------|------|
| **役割** | Naotoのビジョン・戦略・優先順位を全エージェントに統一して伝達する。「何のために動くか」の根拠を維持する |
| **入力** | NORTH_STAR.md, CLAUDE.md, この会話のNaoto指示, 承認済みプロポーザル（pending_approvals.json） |
| **出力** | 各エージェントへの目標注入（system_prompt）、当日優先タスクリスト（SHARED_STATE.md）、意思決定基準の伝播 |
| **更新契機** | セッション開始時（自動）、CLAUDE.md変更時（手動）、Naotoからの新方針指示時 |
| **自動化範囲** | セッション開始時の自動注入（session-start.sh）。NORTH_STAR.md更新は north-star-guard.py が保護（AI自動変更禁止） |
| **推奨実装候補** | 現行: CLAUDE.md @import chain + session-start.sh → Phase 2: Mem0による意図記憶化（セッション間継続） |

**現行ギャップ:** セッションをまたぐと意図が薄れる。MEMORY.md精度54%が最大のボトルネック。

---

## L1: センサー・世界状態層（World State Layer）

> **スコア: 現在 40 / 目標 75**

| 項目 | 内容 |
|------|------|
| **役割** | 地政学・経済・市場の現在状態をリアルタイムに取得・構造化し、予測の文脈として維持する |
| **入力** | Hey Loopニュース（1日4回）、Polymarket市場データ（日次21:30 UTC）、RSS（4ブログ）、Grok API（朝1回）、Google Search Console |
| **出力** | SHARED_STATE.md更新、prediction_dbのmarket_consensus自動更新、記事生成の文脈データ |
| **更新契機** | Hey Loop cron（00/06/12/18 JST）、polymarket_sync.py cron（21:30 UTC）、GSC週次取得 |
| **自動化範囲** | データ取得・保存は全自動。世界モデルの解釈・構造化はGeminiによる週次分析（evolution_loop内） |
| **推奨実装候補** | 現行: Hey Loop + polymarket_sync.py → Phase 1: ClaimReview/schema自動マーキング → Phase 3: Zep/Graphiti（時系列知識グラフ） |

**現行ギャップ:** market_consensusの自動更新率が低い（Polymarket sync開始直後）。ニュースが記事に活用される割合が未測定。

---

## L2: 記憶エンジン層（Memory Engine Layer）

> **スコア: 現在 20 / 目標 85** — **最大のボトルネック**

| 項目 | 内容 |
|------|------|
| **役割** | 短期〜長期の記憶を階層化管理し、関連記憶をセッション開始時に自動注入する。セッション消滅問題を構造的に解決する |
| **入力** | セッションログ、Observer Log（/opt/shared/observer_log/）、タスク完了報告、エラーログ、KNOWN_MISTAKES.md |
| **出力** | セッション開始時の記憶注入（MEMORY.md）、AGENT_WISDOM.md更新、KNOWN_MISTAKES更新、task/project memory |
| **更新契機** | セッション終了時（session-end.py 自動）、エラー発生時（error-tracker.py 自動）、週次Reflectorサイクル（日曜） |
| **自動化範囲** | セッション終了時の記録（自動）、週次統合（evolution_loop 自動）。Mem0/Zep導入・管理は承認後に自動化 |
| **推奨実装候補** | 現行: MEMORY.md + AGENT_WISDOM.md + Observer Log → Phase 2: Mem0（エピソード記憶 L3）→ Phase 3: Zep/Graphiti（意味記憶 L6） |

**6階層記憶モデル（現状→目標）:**

| 層 | 名称 | 現在 | 目標実装 |
|----|------|------|---------|
| L1 | 作業記憶（会話内） | Claude context | そのまま |
| L2 | セッション記憶 | MEMORY.md（54%精度） | Mem0自動同期 |
| L3 | エピソード記憶 | 存在しない | Mem0（Phase 2） |
| L4 | 意味記憶 | AGENT_WISDOM.md（手動） | Observer自動記録 |
| L5 | 手続き記憶 | KNOWN_MISTAKES.md | auto-codifier自動化 |
| L6 | 世界モデル | 静的テキスト | Zep/Graphiti（Phase 3） |

---

## L3: 推論エンジン層（Reasoning Engine Layer）

> **スコア: 現在 35 / 目標 70**

| 項目 | 内容 |
|------|------|
| **役割** | 世界状態と記憶から因果推論・力学パターン抽出を行い、予測と記事の根拠を生成する |
| **入力** | AGENT_WISDOM.md（L4記憶）、世界状態（L1）、Reflexionログ、過去の予測パターン、Extended Thinking |
| **出力** | 力学分析（記事NOW PATTERNセクション）、予測の根拠と確率、Calibration判断、カテゴリ別Brier改善提案 |
| **更新契機** | 記事生成時、予測生成時、Reflexion後（セッション終了）、週次evolution_loop |
| **自動化範囲** | Extended Thinking活用（複雑予測：地政学・経済）。推論品質はBrier Scoreで自動計測。判断の最終確認は人間 |
| **推奨実装候補** | 現行: Claude Opus 4.6 → Phase 1: Extended Thinking適用 → Phase 3: Multi-Agent Reflexion（NEO-ONE→NEO-TWO批評ループ） |

**現行ギャップ:** 経済・貿易カテゴリBrier 0.4868（POOR）。推論に市場データが統合されていない。Extended Thinking未適用。

---

## L4: 予測エンジン層（Prediction Engine Layer）

> **スコア: 現在 55 / 目標 80**

| 項目 | 内容 |
|------|------|
| **役割** | 力学分析から検証可能な確率予測を生成し、prediction_dbに記録・追跡する。Brier Scoreを主KPIとする |
| **入力** | 推論エンジン出力、世界状態（Polymarket含む）、過去のBrierパターン、Calibration履歴 |
| **出力** | prediction_db.json新規予測（追記のみ）、/predictions/と/en/predictions/ページ更新、Oracle Statement |
| **更新契機** | 記事生成時（NEO）、weekly evolution_loop後（精度改善）、auto_verifier実行時（解決検知） |
| **自動化範囲** | 予測生成（NEO自動）、自動検証（prediction_auto_verifier.py）、ページ更新（07:00 JST cron）。確率値の遡及変更は禁止 |
| **推奨実装候補** | 現行: prediction_db.json + auto_verifier + page_builder → Phase 2: Calibration Curve月次 → Phase 3: 読者Leaderboard |

**現行ギャップ:** resolved=37件/982件（3.8%）。カテゴリ別精度の弱点（経済・暗号資産）が改善未着手。

---

## L5: 実行エンジン層（Execution Engine Layer）

> **スコア: 現在 45 / 目標 70**

| 項目 | 内容 |
|------|------|
| **役割** | 指示を実際のアクション（記事生成・投稿・設定変更）に変換し、結果を検証・ログに記録する |
| **入力** | タスク指示（Telegram/この会話）、KNOWN_MISTAKES.md、タクソノミー、記事テンプレートv6.0、approval_queue |
| **出力** | Ghost記事公開（200本/日）、X投稿（100投稿/日）、VPS設定変更、task-log記録（/opt/shared/task-log/） |
| **更新契機** | NEOへの指示受領時、cronジョブ起動時 |
| **自動化範囲** | 記事生成・投稿・X配信は全自動。構造変更（Level 2/3）は承認必須。Execution Replayは未実装 |
| **推奨実装候補** | 現行: NEO-ONE/TWO + cron → Phase 2: Execution Replay（失敗タスク自動再試行）+ タスク/プロジェクト記憶 |

**現行ギャップ:** タスク失敗時の自動再試行なし。execution replayなし。task/project memoryなし（前回の続きから再開できない）。

---

## L6: 評価層（Evaluation Layer）

> **スコア: 現在 30 / 目標 65**

| 項目 | 内容 |
|------|------|
| **役割** | 実行結果・予測精度・システム健全性を数値評価し、改善すべき箇所を特定する |
| **入力** | Brier Score履歴、記事QA結果、エラー率、regression-runner結果、カテゴリ別パフォーマンス |
| **出力** | category_brier.json、QAレポート（Telegram）、Calibration Report、regression 25/25 PASS確認 |
| **更新契機** | 予測解決時（auto_verifier自動）、記事公開時（QA Sentinel自動）、週次（evolution_loop）、日次（regression-runner） |
| **自動化範囲** | Brier計算・QA実行・regression全自動。カテゴリ別分析とCalibration解釈はGeminiで自動化（evolution_loop内） |
| **推奨実装候補** | 現行: category_brier_analysis.py + QA Sentinel → Phase 2: Calibration Curve（月次）+ Weekly Calibration Report自動生成 |

**現行ギャップ:** カテゴリ別Brier分析は作成済みだが初回レポート未出力（次の日曜が初回）。Calibration biasの定量化未着手。

---

## L7: 反省・学習層（Reflection/Learning Layer）

> **スコア: 現在 25 / 目標 65**

| 項目 | 内容 |
|------|------|
| **役割** | 評価結果から学習パターンを抽出し、AGENT_WISDOMとKNOWN_MISTAKESを更新して全エージェントに反映する |
| **入力** | evaluation結果（L6）、Observer Log（/opt/shared/observer_log/）、KNOWN_MISTAKES.md、Brier履歴、Reflexion出力 |
| **出力** | AGENT_WISDOM.md自己学習ログ更新、KNOWN_MISTAKES新パターン登録、evolution_log.json記録、Reflexion出力保存 |
| **更新契機** | セッション終了時（observer_writer.py自動）、週次（evolution_loop自動）、エラー発生時（error-tracker.py自動） |
| **自動化範囲** | Observer Log記録（自動）、週次Reflector統合（自動）、auto-codifier（自動）。長期パターン化の品質確認は人間 |
| **推奨実装候補** | 現行: observer_writer.py + evolution_loop.py + auto-codifier → Phase 2: NEO-TWO Observer Log同期 + Reflexion出力の構造化保存 |

**現行ギャップ:** Reflexion出力が保存されていない（プロンプト追加済み、ログ未保存）。Observer Log形式が未統一。

---

## L8: インターフェース・公開層（Interface/Publishing Layer）

> **スコア: 現在 50 / 目標 70**

| 項目 | 内容 |
|------|------|
| **役割** | 生成したコンテンツと予測を読者・外部世界に届け、エンゲージメントと信頼を蓄積する |
| **入力** | 記事データ（Ghost）、prediction_db（予測）、X投稿キュー、Substack配信リスト |
| **出力** | Ghost公開（200本/日）、X投稿（100投稿/日）、Substack配信（1-2本/日）、/predictions/ページ |
| **更新契機** | 記事生成完了時（NEO自動）、prediction_page_builder cron（07:00 JST）、X swarm cron |
| **自動化範囲** | 記事公開・X配信・ページ更新は全自動。コンテンツ方針・UI変更は承認必須 |
| **推奨実装候補** | 現行: nowpattern_publisher.py + x-auto-post.py + prediction_page_builder.py → Phase 2: 読者Leaderboard → Phase 3: Ghost Members有料化 |

**現行ギャップ:** X投稿の安定性（DLQ再試行）が未確認。Substack自動化の投稿間隔管理が不十分。

---

## LA: セーフティ・監査層（Safety/Audit Layer）

> **スコア: 現在 40 / 目標 75** — **全層に横断する保護層**

| 項目 | 内容 |
|------|------|
| **役割** | システム全体の安全性・整合性・規則準拠を監視し、逸脱を即座に検知・通知・ブロックする |
| **入力** | 全サービスのステータス、記事タグ検査結果、Ghost Webhook、エラーログ、predictions整合性 |
| **出力** | Telegram通知（アラート）、regression結果（25/25 PASS）、zero-article-alert、fact-checker.pyブロック |
| **更新契機** | 30分ごと（service_watchdog）、記事公開時（Ghost Webhook→QA Sentinel）、日次（regression-runner 07:00 JST） |
| **自動化範囲** | 死活監視・アラート通知・ECC物理ブロックは全自動。セキュリティ対応・根本修正は人間承認必須 |
| **推奨実装候補** | 現行: service_watchdog.py + regression-runner.py + fact-checker.py → 計画中: ghost_page_guardian.py（/predictions/改ざん検知） |

---

## スコアサマリー（現在 vs 目標）

| 層 | 現在 | 目標 | ギャップ | 最優先改善 |
|----|------|------|---------|-----------|
| L0 目的・意図 | 55 | 85 | -30 | セッション間意図継続性（Mem0） |
| L1 世界状態 | 40 | 75 | -35 | Polymarket sync定着 + ClaimReview |
| **L2 記憶エンジン** | **20** | **85** | **-65** | **Mem0導入（Phase 2最優先）** |
| L3 推論 | 35 | 70 | -35 | Extended Thinking + Multi-Agent Reflexion |
| L4 予測 | 55 | 80 | -25 | Calibration Curve + カテゴリ強化 |
| L5 実行 | 45 | 70 | -25 | Execution Replay + タスク記憶 |
| L6 評価 | 30 | 65 | -35 | Calibration Report週次自動化 |
| **L7 反省・学習** | **25** | **65** | **-40** | **Observer統一 + Reflexion保存** |
| L8 公開 | 50 | 70 | -20 | X swarm安定化 |
| LA セーフティ | 40 | 75 | -35 | ghost_page_guardian + FileLock |
| **総合** | **32** | **75** | **-43** | **L2記憶が最大ボトルネック** |

---

## 実装依存関係

```
Phase 1（今週〜今月）:
  ✅ Reflexion prompt（L7） — NEO-ONE/TWO追加済み
  ✅ Polymarket sync（L1） — polymarket_sync.py稼働
  ✅ Category Brier（L6） — category_brier_analysis.py稼働
  ✅ Observer Log基盤（L7） — observer_writer.py稼働
  → Extended Thinking設定（L3）← 今日承認待ち
  → ClaimReview/schema（L1）← Week 2
  → Reflexion出力の構造化保存（L7）← Week 2
  → X swarm安定化（L8）← Week 2

Phase 2（来月）:
  → Mem0導入（L2）← L7 Observer Log統一が先
  → Calibration Curve（L6）← L4データ蓄積が先
  → Execution Replay（L5）← L5の記録整備が先
  → NEO-TWO Observer Log同期（L7）

Phase 3（3ヶ月後）:
  → Zep/Graphiti（L2 L6）← L1/L2の安定後
  → Multi-Agent Reflexion（L3）← Phase 2完了後
  → 読者Leaderboard（L8）← prediction_db蓄積後
```

---

*世界水準との差は「記憶（L2: -65）」と「反省・学習（L7: -40）」の2層に集中している。この2層を優先的に強化することがNao Intelligence総合スコア32→75の最短経路。*
