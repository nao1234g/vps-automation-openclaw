# Nao Intelligence — 実装ロードマップ（Track 7）
> 作成: 2026-03-26 | セッション継続（完全書き直し）
> 目的: 12の具体アイテムを3層（今すぐ/次に検証/保留）に分類する。
> 原則: 実装可能性で切る。「いつかやる」はロードマップではない。

---

## ゴール（逆算の起点）

```
3年後:
  - Brier Score < 0.10（Superforecasterレベル）
  - セッション引き継ぎ精度 > 80%（現状54%）
  - 読者 Leaderboard 稼働中
  - 全エージェントが同じ学習ベースを共有

90日の問い: このゴールに向けて、今から何を止め、何を加速するか？
```

---

## ティア1: 今すぐやる（今週中・承認不要）

> **基準**: VPS SSH で完結 / リスクが可逆 / Naoto承認不要 / 1日以内に完了可能

---

### #1: Reflexion logging（反省の構造化保存）

**何をするか**: NEO-ONE/TWO の Reflexion 出力（セッション後の自己反省テキスト）を `/opt/shared/observer_log/YYYY-MM-DD.json` に JSON 形式で自動保存するよう session-end フックを更新する。

**現状**: Reflexion prompt は昨夜追加済み。しかし反省テキストが構造化保存されていない。
**完了基準**: `observer_log/` の当日ファイルに `"type": "reflexion"` エントリが1件以上存在する。
**担当**: ローカルCC → VPS NEO CLAUDE.md 更新
**承認**: 不要

---

### #2: Prediction DB connection（予測記事の相互参照）

**何をするか**: Ghost 記事と `prediction_db.json` の prediction_id が正しく連携しているかを確認し、ORACLE STATEMENT セクションのリンクが全件 `/predictions/#[id_lowercase]` 形式になっているかを audit スクリプトで検証する。

**現状**: UUID ghost_url バグは修正済み（69件）。しかし新規記事でのリンク形式を継続確認していない。
**完了基準**: `prediction_link_audit.py` の実行で broken_link = 0件。
**担当**: VPS SSH で確認スクリプト実行
**承認**: 不要

---

### #3: X swarm 安定化確認

**何をするか**: `x_swarm_dispatcher.py` の稼働状態を確認し、4フォーマット（LINK/NATIVE/RED-TEAM/REPLY）の比率が設計通り（20/30/20/30%）になっているかを1週間分のログで検証する。DLQ に滞留しているアイテムがあれば処理する。

**現状**: swarm 稼働中だが比率・DLQ 状態の最終確認が未実施。
**完了基準**: `x_dlq.json` の滞留件数 < 5件。直近24時間の投稿比率が ±5% 以内。
**担当**: VPS SSH
**承認**: 不要

---

### #4: Execution replay（タスクログの比較可能化）

**何をするか**: `/opt/shared/task-log/` の直近30日分を集計し、タスクカテゴリ別の「エラー件数」「修正回数」「完了時間」を `task_performance_summary.json` に書き出すスクリプトを作成する。

**現状**: task-log は蓄積されているが横断分析がない。タイプ4学習（実行改善）の検証に必要。
**完了基準**: `task_performance_summary.json` が生成され、カテゴリ別の基準値が取れる。
**担当**: ローカルCC → VPS スクリプト作成
**承認**: 不要

---

### #5: Memory correction（MEMORY.md の精度向上）

**何をするか**: MEMORY.md の「PROJECT LIVE STATE」セクションをVPSの実態で上書き更新する。SHARED_STATE.md と乖離しているエントリを修正する。特に記事数（1315件）・Brier Score（0.1776）・各サービス状態を最新化する。

**現状**: MEMORY.md のカウンターが手動更新になっており、前回セッションの値が残っている場合がある。
**完了基準**: MEMORY.md の主要数値が SHARED_STATE.md と一致している。
**担当**: ローカルCC
**承認**: 不要

---

## ティア2: 次に検証（今週〜来週・一部承認必要）

> **基準**: 効果の仮定がある / 実装に1〜3日かかる / Before/Afterの測定が必要

---

### #6: Task/project memory（タスク横断記憶）

**何をするか**: 長期タスク（複数セッションにまたがるプロジェクト）の進捗状態を `task_ledger.json` で追跡し、session-start.sh 起動時に「前回のどこまで完了したか」を自動表示する仕組みを強化する。

**現状**: task_ledger.json は存在するが、session-start.sh での活用が限定的。
**仮定**: タスク状態を session-start に注入するとコンテキスト復元精度が向上する（未測定）。
**完了基準**: session-start.sh 起動時に「未完了タスク: XX件、直近完了: XX」が表示される。
**担当**: ローカルCC
**承認**: 不要

---

### #7: ClaimReview schema（SEO強化）

**何をするか**: `prediction_db.json` に登録された予測に対応する Ghost 記事に `ClaimReview` JSON-LD スキーマを自動付与するスクリプトを作成し、テスト記事1件でリッチリザルト確認を行う。

**現状**: 構造化データなし。Google がNowpatternの予測記事を「単なる記事」として扱っている。
**仮定**: ClaimReview schema がクリック率向上に貢献する（SEO 仮定 — 効果は測定後に判断）。
**完了基準**: Google リッチリザルトテストでエラーゼロ + Search Console で Claim 認識される。
**担当**: ローカルCC → VPS スクリプト作成
**承認**: 不要（テスト記事1件のみ、本番一括適用は V4 で別途）

---

### #8: Evaluation/benchmark loop（評価ループの定量化）

**何をするか**: `evolution_loop.py` に Calibration bias 計算（過信/過小信の定量化）を追加し、毎週日曜の Brier 分析レポートに「カテゴリ別信頼区間」と「bias 方向（over/under）」を含める。

**現状**: category_brier.json は生成済み。Calibration bias の数値化が未実装。
**完了基準**: 毎週日曜の Telegram レポートに `bias: over/under XX%` が含まれる。
**担当**: ローカルCC → VPS evolution_loop.py 更新
**承認**: 不要

---

### #9: World knowledge update loop（世界モデルの自動更新）

**何をするか**: `polymarket_sync.py`（日次）と `hey_loop.py`（6時間ごと）から取得した情報を `world_model_update.json` に集約し、prediction_db の `market_consensus` フィールドを自動更新するパイプラインを確立する。

**現状**: polymarket_sync.py は昨夜デプロイ済みだが prediction_db への自動反映が未実装。
**完了基準**: `prediction_db.json` の `market_consensus.last_updated` が毎日更新される。
**担当**: ローカルCC → VPS パイプライン結合
**承認**: 不要

---

## ティア3: 保留（Phase 2以降・承認必要）

> **基準**: 高コスト / 外部サービス / データ主権リスク / Naoto承認必須

---

### #10: User/operator memory（Mem0 導入）

**何をするか**: VPS に Mem0（self-hosted）をデプロイし、NEO-ONE のセッション終了時に重要コンテキストを自動保存、次回セッション開始時に関連記憶を注入する。

**保留理由**: VPS外部へのデータ送信リスク（cloud版）。Self-hosted版の動作確認が先。
**承認必要事項**: Naoto に「会話データの外部サービス保存を許可するか」を確認
**前提条件**: docker stats でリソース余裕確認 + self-hosted Mem0 の動作検証
**期待効果**: セッション引き継ぎ精度 54% → 80%

---

### #11: ASMR-type orchestration（エージェント間協調の高度化）

**何をするか**: NEO-ONE → NEO-TWO への自動タスク委譲プロトコルを設計する。NEO-ONE がタスクを判断し「このタスクはNEO-TWOに適している」と判断したら自動でTelegramキューに追加する仕組み。

**保留理由**: NEO-ONE/TWO の単独稼働の安定性が先。協調前に個別の信頼性確保が必要。
**承認必要事項**: 委譲ルールの設計をNaotoが確認
**期待効果**: 並列処理率の向上 + NEO-ONE の認知負荷軽減

---

### #12: Multi-Agent Reflexion（品質の引き上げ）

**何をするか**: NEO-ONE が予測を生成し、NEO-TWO が批評し、NEO-ONE が修正する反省ループ。批評のプロンプトと手順を設計・実装する。

**保留理由**: 単独 Reflexion の効果測定（#1完了後3週間）が先。Multi-Agent は複雑性が高い。
**承認必要事項**: 不要（効果確認後に自動実施可能）
**前提条件**: #1（Reflexion logging）完了 + 3週間のBrier Score追跡データ

---

## 実装依存関係

```
#5 Memory correction（今週）
  ↓ 基盤
#1 Reflexion logging（今週）→ 3週間後 → #12 Multi-Agent Reflexion（保留）
#2 Prediction DB connection（今週）→ #7 ClaimReview schema（来週）
#3 X swarm確認（今週）
#4 Execution replay（今週）→ #6 Task memory（来週）
#9 World knowledge loop（来週）→ #10 Mem0（保留）
#8 Evaluation loop（来週）→ 毎週自動改善
```

---

## KPI目標（逆算）

| KPI | 現在 | ティア1完了時 | ティア2完了時 | ティア3完了時 |
|-----|------|------------|------------|------------|
| Brier Score | 0.1776 | 0.1700 | 0.1550 | 0.1300 |
| セッション引き継ぎ精度 | 54% | 60% | 70% | 80% |
| Reflexion保存率 | 0% | 80% | 90% | 95% |
| market_consensus更新率 | 部分 | 60% | 85% | 95% |
| タスク横断追跡 | 手動 | 半自動 | 自動 | 自動 |

---

*「ロードマップは優先順位のリストである。全部やることではなく、何をやらないかを決めることが本質。」*
