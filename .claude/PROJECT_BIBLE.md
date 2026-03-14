# PROJECT_BIBLE.md — Nowpattern Persistent Intelligence OS
> **最高参照文書。NORTH_STAR.md の実装詳細版。**
> 矛盾があれば NORTH_STAR.md が正しい。このファイルは「どう実装するか」の詳細。
> 更新: 変更時は末尾の CHANGELOG に1行追記。

---

## 1. システム名称とミッション

**Nowpattern Persistent Intelligence OS (PIOS)**

世界初の日本語×英語バイリンガル・予測精度検証プラットフォームを構築・維持する
モデル非依存の自律型エグゼクティブOSである。

### 核心価値命題
```
競合が提供: ニュースの要約・解説（消える）
Nowpatternが提供: 力学分析 + 検証可能な予測 + トラックレコード（積み上がる）
```

---

## 2. システムアーキテクチャ（9層構造）

```
┌─────────────────────────────────────────────────────────┐
│  Layer 9: Executive / Self-Evolution                    │
│  evolution_loop.py | board_meeting.py                   │
├─────────────────────────────────────────────────────────┤
│  Layer 8: Agent Civilization                            │
│  NEO-ONE / NEO-TWO / NEO-GPT / local-claude            │
├─────────────────────────────────────────────────────────┤
│  Layer 7: Recovery / Resilience                         │
│  release_gate.py | self_healer.py | service_watchdog   │
├─────────────────────────────────────────────────────────┤
│  Layer 6: Observability                                 │
│  os_logger.py | pipeline_metrics.py                    │
├─────────────────────────────────────────────────────────┤
│  Layer 5: Evaluation / Brier Scoring                   │
│  prediction_registry.py | prediction_auto_verifier.py  │
├─────────────────────────────────────────────────────────┤
│  Layer 4: Research Intelligence                        │
│  daily_paper_ingest.py | daily_research_digest.py      │
│  promote_research_to_tasks.py                           │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Knowledge Engine                             │
│  knowledge_store.py | knowledge_ingestion.py           │
│  knowledge_timeline.json                               │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Failure Memory                               │
│  failure_memory.json | failure_capture.py              │
│  release_gate.py | post_edit_task_reconcile.py         │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Task Governance                              │
│  task_ledger.json | pre_edit_task_guard.py             │
│  active_task_id.txt                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 予測フライホイール（Intelligence Flywheel）

```
① 記事執筆（力学分析 + 3シナリオ）
   ↓
② Ghost公開 + prediction_db.json に記録（OTSタイムスタンプ）
   ↓
③ 自動検証（prediction_auto_verifier.py — Grok + Opus）
   ↓
④ /predictions/ ページ更新（Brier Score更新）
   ↓
⑤ 読者信頼蓄積（トラックレコード）
   ↓
⑥ 読者が予測に参加（エンゲージメント向上）
   ↓
⑦ ナレッジグラフ蓄積（力学パターン学習）
   ↓
⑧ 次の予測精度が上がる → ①に戻る
```

---

## 4. 主要コンポーネント索引

| コンポーネント | ファイル | 役割 | 実装状況 |
|---|---|---|---|
| Task Ledger | `.claude/state/task_ledger.json` | 全編集の前にタスク登録を強制 | ✅ |
| Pre Edit Guard | `scripts/guard/pre_edit_task_guard.py` | タスクなし編集を物理ブロック | ✅ |
| Post Edit Reconcile | `scripts/guard/post_edit_task_reconcile.py` | 編集後タスクループを閉鎖 | ✅ |
| Failure Memory | `.claude/state/failure_memory.json` | 全失敗の構造化記録 | ✅ |
| Failure Capture | `scripts/guard/failure_capture.py` | 失敗自動記録（PostToolUseFailure） | ✅ |
| Release Gate | `scripts/guard/release_gate.py` | デプロイ前 critical/high 失敗チェック | ✅ |
| Research Radar | `scripts/research/daily_paper_ingest.py` | arXiv/Semantic Scholar 日次取得 | ✅ |
| Research Digest | `scripts/research/daily_research_digest.py` | ダイジェスト生成（Telegram/Markdown） | ✅ |
| Research Promote | `scripts/research/promote_research_to_tasks.py` | 高関連度論文をタスク昇格 | ✅ |
| Knowledge Timeline | `.claude/state/knowledge_timeline.json` | 知識取り込み履歴 | ✅ |
| Prediction Registry | `prediction_engine/prediction_registry.py` | 予測DB管理（Brier Score計算） | ✅ |
| Evolution Loop | `loops/evolution_loop.py` | Brier→分析→AGENT_WISDOM週次更新 | ✅ |
| OS Logger | `observability/os_logger.py` | 構造化ロガー（JSON Lines） | ✅ |
| Pipeline Metrics | `observability/pipeline_metrics.py` | ステージ計測（p95レイテンシ） | ✅ |
| CivilizationOS | `run_civilization_os.py` | OSエントリポイント | ✅ |
| SystemScheduler | `system_scheduler.py` | タスクスケジューラ（interval_hours） | ✅ |

---

## 5. データファイル索引

| ファイル | 場所 | 更新頻度 | 不変性 |
|---|---|---|---|
| `prediction_db.json` | VPS `/opt/shared/` | 予測追加時 | APPEND ONLY（変更禁止） |
| `task_ledger.json` | `.claude/state/` | タスク毎 | 削除禁止（アーカイブのみ） |
| `failure_memory.json` | `.claude/state/` | エラー毎 | 削除禁止（resolve only） |
| `radar.json` | `data/research/` | 日次 | 90日ローテーション |
| `knowledge_timeline.json` | `.claude/state/` | 知識取り込み毎 | APPEND ONLY |
| `scheduler_state.json` | `data/` | 実行毎 | 上書きOK |
| `daily_metrics.json` | `data/` | パイプライン毎 | 90日ローテーション |
| `agent_wisdom_updates.json` | `data/` | 週次 | APPEND ONLY（52件） |

---

## 6. 環境別の差異

| 項目 | ローカル（Windows） | VPS（Ubuntu 22.04） |
|---|---|---|
| Python | `python`（python3は不可） | `python3` |
| prediction_db.json | `data/prediction_db.json` | `/opt/shared/prediction_db.json` |
| Telegram送信 | 環境変数必要 | `/opt/cron-env.sh` から読む |
| Claude接続 | Claude Max（OAuth） | Claude Max（OAuthトークンSCPコピー） |
| 記事生成 | 対象外 | NEO-ONE/TWO が担当 |

---

## 7. 禁止事項（絶対）

```
❌ prediction_db.json のデータ変更・削除
❌ NORTH_STAR.md / CLAUDE.md への自律的な書き込み
❌ task_ledger.json の done タスク削除
❌ failure_memory.json の failures 削除
❌ knowledge_timeline.json の runs 削除
❌ ポート 8766 を reader_prediction_api.py 以外で使用
❌ SQLiteファイル（reader_predictions.db）の削除・移動
❌ タスクIDなしの Edit/Write（pre_edit_task_guard.py がブロック）
```

---

## CHANGELOG

| 日付 | 変更内容 |
|---|---|
| 2026-03-14 | 初版。9層アーキテクチャ定義。全コンポーネント・データファイル索引。環境差異表。禁止事項。 |
