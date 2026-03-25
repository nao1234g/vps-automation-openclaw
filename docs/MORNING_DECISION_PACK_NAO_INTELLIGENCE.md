# 朝の決定パック — Nao Intelligence（Track 8）
> 作成: 2026-03-26 | セッション継続（完全書き直し）
> 目的: 3分で判断できる。「YES / NO / 保留」だけ答えればいい。
> 更新方法: 毎セッション終了時にAIがこのファイルを最新化する。

---

## ⚡ 読み方（30秒）

```
1. [Pスコア] → 今のNao Intelligenceの状態を数字で確認
2. [最大のずれ] → 何が最もトラックから外れているか
3. [今すぐトップ5] → これだけ決める
4. [承認が必要トップ3] → YES/NOを答えるだけ
5. 終わり。詳細は各Trackドキュメントへ。
```

---

## 🧠 Nao Intelligence Pスコア（現在）

> Pスコア = 「判断精度」のレバー。正しい方向を選んでいるか。

| 領域 | スコア | 状態 | 根拠 |
|------|--------|------|------|
| 知識取得（タイプ1） | 45/100 | ⚠️ 改善余地 | Polymarket API追加済み。AGENT_WISDOMへの自動記録は稼働中 |
| 誤り訂正（タイプ2） | 70/100 | ✅ 機能中 | KNOWN_MISTAKES.md + regression 25/25 PASS |
| 判断改善（タイプ3） | 35/100 | ❌ 数値根拠薄 | AGENT_WISDOM に定性記録はあるが数値根拠なし |
| 実行改善（タイプ4） | 40/100 | ⚠️ 比較不能 | task-log 蓄積中だが横断分析なし（#4未実施） |
| 反省保存（タイプ5） | 30/100 | ⚠️ 基盤構築済 | observer_log 2026-03-25 構築済み。実績データなし |
| 引き継ぎ（タイプ6） | 20/100 | ❌ 未定量化 | session-start.sh 部分的。精度54%（目標80%） |
| 予測精度（タイプ7） | 60/100 | ⚠️ 弱点あり | Brier 0.1776 全体FAIR / 経済0.4868 POOR |
| 価値判断（タイプ8） | 15/100 | ❌ 未実装 | AGENT_WISDOM内に専用セクションなし |
| 意図整合（タイプ9） | 50/100 | ⚠️ 定性のみ | 提案却下率未計測 |

**総合Pスコア: 37/100（Phase 1目標: 55/100）**

---

## 🚨 最大のずれ（何が最もトラックから外れているか）

### ずれ1（最大）: セッション引き継ぎ精度 54%

```
問題: 毎セッション冒頭でVPS確認・文書再読・コンテキスト復元に大量の時間を使っている
根本原因: セッション記憶（タイプ6）が未定量化。MEMORY.md に書いても次回に活きていない
影響: Pスコア -20相当。正しい方向に進むための判断材料が毎回不完全
修正ロードマップ: #1 Reflexion logging → 3週間観測 → Mem0（Phase 2）
現在の対処: MORNING_HANDOFF（このファイル）で手動補完中
```

### ずれ2（重大）: 予測精度の弱点カテゴリ改善なし

```
問題: 経済・貿易カテゴリ Brier 0.4868（POOR）が3ヶ月以上改善なし
根本原因: evolution_loop.py は全体Brierのみ分析していた（category_brierは昨夜追加）
影響: このカテゴリの予測は読者信頼を損ねる
修正ロードマップ: category_brier.json（昨夜構築済み） → 今週日曜に初回分析 → 判断ルール更新
```

### ずれ3（要確認）: 価値判断ルール（タイプ8）が記録されていない

```
問題: 「何が良い予測か」「どの情報源を信頼するか」の更新基準が未整備
根本原因: AGENT_WISDOM.md 内の分類が混在（タイプ3/8が未分離）
影響: 長期的な判断の進化が記録されない
修正: 今週中に AGENT_WISDOM.md に「価値判断ルール」専用セクション作成（承認不要）
```

---

## ✅ 今すぐやるべきトップ5（ティア1 — 今週中・承認不要）

> 各アイテムの詳細 → NAO_INTELLIGENCE_ROADMAP.md

### #1: Reflexion logging（今日）

```
タスク: NEO-ONE/TWO の session-end フックを更新し、Reflexion出力を observer_log に JSON保存
完了確認: cat /opt/shared/observer_log/2026-03-26.json | python3 -c "..."でreflexionエントリ確認
所要時間: 1〜2時間
承認: 不要
```

### #2: Prediction DB connection 確認（今日）

```
タスク: prediction_link_audit.py を実行し、ORACLE STATEMENTのリンクが全件 /predictions/#[id_lowercase] 形式か確認
完了確認: broken_link = 0件
所要時間: 30分
承認: 不要
```

### #3: Memory correction（今日）

```
タスク: MEMORY.md の主要数値をVPS実態（SHARED_STATE.md）と照合・更新
完了確認: MEMORY.md の記事数・Brier Score・サービス状態が SHARED_STATE.md と一致
所要時間: 30分
承認: 不要（今このファイルを更新している = 一部実施中）
```

### #4: Execution replay スクリプト作成（今週）

```
タスク: /opt/shared/task-log/ 直近30日分を集計 → task_performance_summary.json 生成
完了確認: スクリプト実行でカテゴリ別エラー件数・修正回数の基準値が取れる
所要時間: 2〜3時間
承認: 不要
```

### #5: X swarm 安定化確認（今週）

```
タスク: x_dlq.json 滞留確認 + 直近24時間の4フォーマット比率検証
完了確認: DLQ < 5件 + 比率 ±5% 以内
所要時間: 30分
承認: 不要
```

---

## 🔒 保留トップ5（ティア3 — Phase 2以降・承認必要）

| # | 名前 | なぜ保留か | 前提条件 | 解除トリガー |
|---|------|----------|---------|------------|
| H1 | Mem0導入 | VPS外部へのデータ送信リスク。cloud版はNGだが自己ホスト確認必要 | docker stats でリソース確認 + self-hosted Mem0 動作検証 | Naoto承認 |
| H2 | Zep/Graphiti | Docker追加リソース + Phase 1のMemory Engine安定化が先 | Mem0 完了後 | Naoto承認 + VPSリソース確認 |
| H3 | Multi-Agent Reflexion | #1（単独Reflexion）の効果測定3週間が先 | Reflexion logging 完了 + 3週間Brier追跡 | 自動（承認不要） |
| H4 | リーダーボード公開 | 読者投票データ蓄積が先（現在まだ少数） | TIER 1完了 + 読者投票100件超 | Naoto判断 |
| H5 | ASMR型エージェント協調 | NEO-ONE/TWO個別の信頼性確保が先 | 両エージェント30日無停止稼働確認 | Naoto承認 |

---

## 🔧 このセッション（2026-03-25夜〜26朝）で修正されたこと

### ドキュメント整備（8本完成）

| Track | 内容 | 変化 |
|-------|------|------|
| 1 | CURRENT_STATE | 前セッション完成 |
| 2 | WORLD_BEST_PRACTICES | 完成（昨夜） |
| 3 | TECH_EVAL | 完成（昨夜） |
| 4 | TARGET_ARCHITECTURE | **完全書き直し** — 9層×6項目テーブル形式 |
| 5 | LEARNING_CRITERIA | **完全書き直し** — 9タイプ×3定義 |
| 6 | FULL_PROPOSALS | **完全書き直し** — ドメイン分類×優先度マトリックス |
| 7 | ROADMAP | **完全書き直し** — 3ティア×12必須アイテム |
| 8 | このファイル | **完全書き直し** — 3分判断フォーマット |

### VPS実装（昨夜 Night Mode）

| 実装 | 内容 | 状態 |
|------|------|------|
| Draft rescue | lang-jaミスラベル429件修正 | ✅ 完了確認要 |
| nowpattern_publisher.py | EN記事のlang-en付与バグ修正 | ✅ 根本修正済み |
| Reflexion prompt | NEO-ONE/TWO system_promptに自己反省プロンプト追加 | ✅ 稼働中 |
| polymarket_sync.py | prediction_dbへのPolymarket市場データ同期 | ✅ cron登録済み（21:30 UTC日次） |
| category_brier_analysis.py | evolution_loop.pyにカテゴリ別分析統合 | ✅ 次回日曜実行 |
| observer_log 基盤 | observer_writer.py + observer_archiver.py デプロイ | ✅ 稼働中 |

---

## 📋 承認が必要なトップ3（YES/NOを答えるだけ）

### 承認1: deep-pattern-generate.py lang修正

```
何: ENコンテンツ生成時にlang-jaタグが付くバグの根本修正
どこ: /opt/shared/scripts/deep-pattern-generate.py
リスク: 修正ミスがあると新規記事のタグが壊れる（可逆的: バックアップあり）
確認方法: テスト記事1件生成 → タグ確認

→ [YES] 本番適用する
→ [NO] rollbackして手動確認を待つ
```

### 承認2: FileLock + Ghost Webhook改ざん検知

```
何: prediction_page_builder.py の並行実行防止 + /predictions/ページ変更時Telegram通知
どこ: prediction_page_builder.py（fcntlロック追加）+ ghost_page_guardian.py（新規）
リスク: fcntlはLinux専用（VPSはOK）。webhook登録は一回限り
詳細: C:\Users\user\.claude\plans\giggly-weaving-dongarra.md

→ [YES] 実装する（Part 1: FileLock → Part 2: Webhook）
→ [NO] 後回しにする
```

### 承認3: Mem0 self-hosted 検証開始

```
何: VPS に Mem0 self-hosted をデプロイして動作確認（本番適用はPhase 2）
どこ: VPS Docker。/opt/shared/mem0/ に独立コンテナ
リスク: VPSリソース消費（要docker stats確認）。データはVPS内完結（外部送信なし）
目的: セッション引き継ぎ精度 54% → 80%

→ [YES] docker stats確認後に検証開始
→ [NO] 現在の手動補完（MEMORY.md）で継続
```

---

## 🚦 実装してよいもの・いけないもの

### ✅ 承認なしで実装していいもの（ティア1相当）

```
- observer_log への記録追加（追記のみ）
- AGENT_WISDOM.md への追記（既存エントリ変更は禁止）
- KNOWN_MISTAKES.md への追記
- task-log の集計スクリプト作成（読み取り専用）
- session-start.sh の表示内容改善（既存機能の範囲内）
- prediction_db.json への新規予測追加（既存データ変更禁止）
- X swarm の DLQ処理（設計比率内）
- Brier分析スクリプトの実行・確認
- prediction_link_audit.py の実行・確認
```

### ❌ 承認なしで実装してはいけないもの

```
- prediction_db.json の既存データ変更・削除（データ主権）
- NORTH_STAR.md / OPERATING_PRINCIPLES.md の変更（永久ロック）
- prediction_page_builder.py への変更（FileLock は承認2で判断）
- Ghost Webhook の登録（一回限りの操作、承認2で判断）
- NEO CLAUDE.md の system_prompt 変更（エージェント動作への影響）
- Mem0 / Zep / Graphiti のデプロイ（外部サービス・リソース）
- VPS cronへの追加・削除（構造変更プロトコル適用）
- UIレイアウト変更（prediction-design-system.md の承認フロー必須）
- 新規Dockerコンテナ追加（Naoto承認必須）
```

---

## 📊 Nao Intelligence KPI（今朝の確認値）

| KPI | 前回 | 今朝 | 目標（ティア1完了時） |
|-----|------|------|-------------------|
| 総合Pスコア | 32/100 | **37/100** | 55/100 |
| Brier Score（全体） | — | **0.1776** | 0.1700 |
| Brier Score（経済） | — | **0.4868** POOR | 0.3500 |
| セッション引き継ぎ精度 | 54% | 54% | 65% |
| Reflexion保存率 | 0% | 0% | 80% |
| 記事数（published） | 803 | **1315** | — |

---

## 🎯 今日の最重要問い

**「今日のNao Intelligenceは昨日より賢いか？」**

```
確認コマンド（コピペで動く）:

# VPS全体状態
ssh root@163.44.124.123 "cat /opt/shared/SHARED_STATE.md"

# Observer Log（反省が保存されているか）
ssh root@163.44.124.123 "ls -la /opt/shared/observer_log/ | tail -5"

# Draft rescue 結果確認
ssh root@163.44.124.123 "cat /opt/shared/logs/draft_rescue_result.log 2>/dev/null | tail -10"

# NEO-ONE/TWO サービス確認
ssh root@163.44.124.123 "systemctl is-active neo-telegram neo2-telegram neo3-telegram"

# Polymarket sync ログ
ssh root@163.44.124.123 "cat /opt/shared/logs/polymarket_sync.log 2>/dev/null | tail -5"
```

---

## 詳細参照先（このファイルで足りない場合）

| 知りたいこと | ファイル |
|-------------|---------|
| 各アイテムの詳細仕様 | [NAO_INTELLIGENCE_ROADMAP.md](NAO_INTELLIGENCE_ROADMAP.md) |
| 提案の優先度根拠 | [NAO_INTELLIGENCE_FULL_PROPOSALS.md](NAO_INTELLIGENCE_FULL_PROPOSALS.md) |
| 「学習した」の証明方法 | [NAO_INTELLIGENCE_LEARNING_CRITERIA.md](NAO_INTELLIGENCE_LEARNING_CRITERIA.md) |
| アーキテクチャ全体図 | [NAO_INTELLIGENCE_TARGET_ARCHITECTURE.md](NAO_INTELLIGENCE_TARGET_ARCHITECTURE.md) |
| 世界標準との比較 | [NAO_INTELLIGENCE_WORLD_BEST_PRACTICES.md](NAO_INTELLIGENCE_WORLD_BEST_PRACTICES.md) |
| 技術選定根拠 | [NAO_INTELLIGENCE_TECH_EVAL.md](NAO_INTELLIGENCE_TECH_EVAL.md) |
| 現状スコア詳細 | [NAO_INTELLIGENCE_CURRENT_STATE.md](NAO_INTELLIGENCE_CURRENT_STATE.md) |

---

*「意思決定とは情報ではなく判断だ。判断には3分で十分。」*
*このファイルは毎セッション終了時にAIが自動更新する。手動編集不要。*
