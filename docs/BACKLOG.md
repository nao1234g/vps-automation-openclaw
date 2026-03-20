# BACKLOG — 因果律から導いた全穴埋めタスク一覧

> **セッションをまたいで追跡する永続タスクリスト。**
> - 完了したら `[ ]` → `[x]` に変える
> - 削除禁止（履歴として残す）
> - 追加方法: このファイルを直接 Edit するか、「バックログに追加: タスク名」と指示
> - **最終目標**: H3が完了したら、ミスが起きる前に自動修正・自動学習するシステムが完成する

---

## カテゴリ説明（因果律ベース）

| カテゴリ | なぜ必要か |
|---------|-----------|
| **A: 記事生成** | 記事がゼロになる原因はコードバグ。バグを自動検知・自動修正しなければ止まり続ける |
| **B: コンテンツ品質** | 公開後に品質チェックしなければ低品質記事が蓄積してMoatを傷つける |
| **C: Oracle/予測** | 予測トラックレコードが唯一のMoat。検証が止まればMoatが崩壊する |
| **D: 配信パイプライン** | X/note/Substackが止まっても誰も気づかなければ波及力（E）がゼロになる |
| **E: ECC/学習ループ** | VPS上のNEOには同じミスを防ぐフックがない。ローカルで学んだことがVPSに伝わらない |
| **F: 自律修復** | 人間（Naoto）の承認なしに直せるものは直す。Telegramは「直しました」報告のみ |
| **G: インフラ監視** | SSL/disk/Docker/OAuthが壊れると全パイプラインが停止する |
| **H: セッション継続性** | セッションをまたいで状態が引き継がれなければ、毎回同じ確認が必要になる |

---

## A: 記事生成の完全自動修復

- [x] **A1: known_fixes.json作成** (2026-03-04)
  - VPS: `/opt/shared/scripts/known_fixes.json`
  - エラー署名→自動修正コマンドのマッピング（5パターン登録済み）

- [x] **A2: generate.py AttributeError修正** (2026-03-04)
  - `dynamics_sections`/`scenarios`ループに`isinstance(s, dict)`チェック追加
  - `grep -c 'isinstance(s, dict)'` → 3件確認済み
  - ⚠️ 2026-03-19監査: `generate.py` はVPS上に現存しない（統合または名称変更済み）

- [x] **A3/F1: self-healer.py作成（自律修復エンジン）** (2026-03-04)
  - VPS: `/opt/shared/scripts/self-healer.py`
  - 15分ごとcron: 記事生成・サービス・disk・SSLを自動チェック
  - known_fixes.jsonと照合して自動パッチ → 「直しました」Telegram通知
  - cron: `*/15 * * * *`

- [x] **A4: 記事200本/日カウント監視** (2026-03-04)
  - VPS: `/opt/shared/scripts/article-count-monitor.py`
  - cron: `0 8 * * *` — Ghost DBで前日JP/EN記事数確認
  - JP<100またはEN<100でTelegram警告

- [x] **A5: EN翻訳パイプライン停止検知** (2026-03-04)
  - VPS: `/opt/shared/scripts/en-translation-monitor.py`
  - cron: `0 * * * *` — JP記事の2時間以上EN未公開を検知
  - 3件以上でTelegram通知

---

## B: コンテンツ品質の自動監査

- [x] **B1: 公開後article_validator.py自動実行cron** (2026-03-04)
  - VPS: `/opt/shared/scripts/content-quality-monitor.py` に統合
  - cron: `0 4 * * *` — article_validator.py実行 + FAILをTelegram通知

- [x] **B2: VPS上のfact-checker相当機能** (2026-03-04)
  - `/opt/CLAUDE.md`に4段階検証ルール追記（Python SCP方式で書き込み）
  - STEP 1: 確認 / STEP 2: 既知ミス確認 / STEP 3: 変更後検証 / STEP 4: ミス記録
  - ⚠️ 2026-03-19監査: `/opt/CLAUDE.md` は2026-03-14に退役済み（→ `.retired-20260314`）。各NEOエージェント個別のCLAUDE.mdに継承。

- [x] **B3: 文字数・セクション自動監査** (2026-03-04)
  - content-quality-monitor.py に統合
  - 6マーカー（np-fast-read等）確認 + 2000文字未満チェック

- [x] **B4: 重複記事検知** (2026-03-04)
  - content-quality-monitor.py に統合
  - タイトル重複 + スラッグ重複をGhost DBで検知

- [x] **B5: タグ監査cron稼働確認** (2026-03-04)
  - content-quality-monitor.py に統合
  - `crontab -l | grep tag-audit` で確認 + 未登録警告

---

## C: Oracle/予測システムの完全性保証

- [x] **C1: prediction_auto_verifier.py監視** (2026-03-04)
  - VPS: `/opt/shared/scripts/oracle-monitor.py` に統合
  - cron: `0 7 * * *` — ログ鮮度確認（26h以内）+ エラー検知
  - 初回テスト: verifier.logにTraceback検知 → アラート送信確認

- [x] **C2: /predictions/ページ再構築失敗検知** (2026-03-04)
  - oracle-monitor.py に統合（prediction_page.log + prediction_page_en.log確認）
  - ログが26h以上更新なし or ERROR検知でTelegram通知

- [x] **C3: 新規予測追加の検証** (2026-03-05)
  - VPS: `/opt/shared/scripts/prediction-update-checker.py`
  - cron: `*/30 * * * *` — prediction_db.jsonハッシュ変化を検知、5分後Ghost更新確認

- [x] **C4: Brier Score計算の正確性確認** (2026-03-05)
  - VPS: `/opt/shared/scripts/brier-score-validator.py`
  - cron: `0 9 1 * *` — 月1回、差0.01以上でTelegram通知

- [x] **C5: Polymarket自動更新監視** (2026-03-05)
  - VPS: `/opt/shared/scripts/polymarket-staleness-checker.py`
  - cron: `0 10 * * 1` — 週次月曜、2週間以上更新なしカードをTelegram通知

---

## D: 配信パイプライン全体監視

- [x] **D1: X投稿停止検知** (2026-03-04)
  - VPS: `/opt/shared/scripts/pipeline-monitor.py` に統合
  - cron: `0 21 * * *` — X投稿cron状態確認 + ログカウント

- [x] **D2: noteキューオーバーフロー検知** (2026-03-04)
  - pipeline-monitor.py に統合 — note-queue.json件数確認
  - 100件超でTelegram警告

- [x] **D3: Substack投稿確認** (2026-03-04)
  - pipeline-monitor.py に統合 — `docker ps --filter name=substack`
  - コンテナ停止でTelegram警告

- [x] **D4: パイプライン健全性ダッシュボード** (2026-03-04)
  - pipeline-monitor.py が毎日21:00に✅/⚠サマリー送信
  - Ghost記事数・X cron・noteキュー・Substackを一括報告

---

## E: VPS ECCパイプライン（学習ループ）

- [x] **E1: VPSスクリプトエラー→KNOWN_MISTAKES自動キャプチャ** (2026-03-04)
  - VPS: `/opt/shared/scripts/vps-error-capture.py`
  - cron: `0 * * * *` — 6ログファイルをスキャン、MD5重複排除
  - `/opt/shared/KNOWN_MISTAKES_VPS.md`に自動追記

- [x] **E2: NEOミスのキャプチャ** (2026-03-04)
  - VPS: `/opt/shared/scripts/neo-mistake-capture.py`
  - cron: `0 3 * * *` — `/opt/shared/task-log/*.md`スキャン
  - 失敗パターンをAGENT_WISDOM.mdに追記

- [x] **E3: ローカル→VPS 知識同期** (確認: session-end.py step 4で実装済み)
  - `session-end.py` の step 4 でSCP同期済み
  - AGENT_WISDOM.md + mistake_patterns.json を毎セッション終了時にVPSへ

- [x] **E4: デプロイ前cronテスト** (2026-03-05)
  - VPS: `/opt/shared/scripts/pre-deploy-check.sh`
  - 構文チェック + 危険パターン検出 + cron式検証 + --dry-run実行

- [x] **E5: VPSリグレッションランナー** (2026-03-05)
  - VPS: `/opt/shared/scripts/regression-runner.py`
  - cron: `0 3 * * 0` — 毎週日曜03:00、article_validator/prediction_page_builder/nowpattern_publisherのスモークテスト

---

## F: 自律修復の完成

- [x] **F1/A3: self-healer.py** (Aカテゴリと同一 — 上記A3を参照)

- [x] **F2: 非systemdスクリプトの自動再起動** (2026-03-05)
  - VPS: `/opt/shared/scripts/hung-process-killer.py`
  - cron: `*/30 * * * *` — x-auto-post/note-auto-post/nowpattern-generator の実行時間上限超過で SIGKILL

- [x] **F3: NEO自律診断ループ** (2026-03-05)
  - VPS: `/opt/shared/scripts/neo-morning-diagnosis.py`
  - cron: `0 7 * * *` — 毎朝07:00 JST、記事数/サービス/disk/cron確認、問題あれば自己修復+Telegram報告

- [x] **F4: 修復後の検証** (2026-03-05)
  - VPS: `/opt/shared/scripts/repair-verifier.py`
  - cron: `*/30 * * * *` — サービス連続停止2回で「修復効果なし」通知、3回で known_fixes.json 無効化

---

## G: インフラ監視

- [x] **G1: SSL有効期限監視** (2026-03-04)
  - self-healer.pyの`check_ssl()`として実装
  - 14日以内: Telegram警告 / テスト: 74日残で正常動作確認

- [x] **G2: disk使用率監視＋自動クリーンアップ** (2026-03-04)
  - self-healer.pyの`check_disk()`として実装
  - 80%超: 古いログ自動削除 / 90%超: Telegram緊急通知
  - テスト: 29%使用で正常動作確認

- [x] **G3: NEO OAuthトークン更新失敗検知** (2026-03-04)
  - VPS: `/opt/shared/scripts/infra-monitor.py` に統合
  - cron: `30 * * * *` — /root/.claude/.credentials.json鮮度確認（8h上限）
  - テスト: 2.5h以内で正常確認

- [x] **G4: 外部VPS死活監視** (2026-03-05)
  - ローカル: `scripts/vps_health_monitor.ps1`
  - Windowsタスクスケジューラ登録済み（5分間隔）
  - ICMP + TCP port 22、3回連続失敗でTelegram緊急通知
  - 設定ファイル: `~/.claude/vps_monitor_config.json`

- [x] **G5: Dockerコンテナリソース監視** (2026-03-04)
  - infra-monitor.py に統合（G3と同一スクリプト）
  - docker stats + docker ps (unhealthy検知)
  - テスト: 全5コンテナ正常、CPU最大2%、MEM最大23%

---

## H: セッション間継続性

- [x] **H1: session-start.sh差分ベース状態検知** (2026-03-04)
  - `h1-vps-diff.py` + session-start.sh に追加
  - VPSスナップショット比較（記事数・サービス状態・cronジョブ数）
  - session-end.py が終了時にスナップショット保存

- [x] **H2: NORTH_STAR未解決事項の自動表示** (確認: session-start.sh lines 87-99で実装済み)
  - BACKLOG.md未完了タスクを件数+一覧表示（セッション開始時に自動）
  - `grep -c "^- \[ \]"` でカウント → 全件リストアップ

- [x] **H3: セッション間タスク引き継ぎプロトコル** (2026-03-04)
  - session-end.py がhandoff.json保存（current_state.json存在かつアクティブなTodo存在時のみ、lines 168-179）
  - session-start.sh がhandoff.json読み込みと表示（handoff.json存在時のみ、lines 112-135）
  - 保存先: `.claude/hooks/state/handoff.json`（runtime artifact — 条件付き生成）
  - ⚠️ 2026-03-20再監査: 保存ロジック（session-end.py:168-179）・読み込みロジック（session-start.sh:112-135）ともに実装済み。handoff.jsonはruntime artifact — 前セッション終了時にアクティブなTodoがない場合は生成されない。[x]は「ロジック実装済み」として正当。

---

## 完了済み（アーカイブ）

- [x] **週次リサーチ実行** (2026-03-04)
- [x] **Google Search Console SEO修正 + AIO対応** (2026-03-04)
- [x] **python3フック全滅修正** (2026-03-04)
- [x] **VPS SSH 破壊的操作ガード実装** (2026-03-04)
- [x] **週次リサーチトリガー実装** (2026-03-04)
- [x] **FileLock + Ghost Webhook 改ざん検知** (2026-03-03)
- [x] **PVQE-P ゲート実装** (2026-03-03)
- [x] **VPS本番スクリプトクラッシュ検知** (2026-03-04) — zero-article-alert.py 30分cron
- [x] **A1: known_fixes.json作成** (2026-03-04)
- [x] **A2: generate.py AttributeError修正** (2026-03-04)

---

---

## I: 読者参加型予測プラットフォーム（2026-03-07〜）

> **ビジョン**: 誰がどの予測を、いつ、どんな確率で言ったか → Brier Scoreで精度が積み上がる日本初キャリブレーション予測プラットフォーム

### TIER 0（完了）

- [x] **I1: reader_prediction_api.py 作成（FastAPI + SQLite）** (2026-03-07)
  - VPS: `/opt/shared/scripts/reader_prediction_api.py`
  - POST /vote, GET /stats/{id}, GET /stats-bulk, GET /my-votes/{uuid}, GET /leaderboard
  - SQLite WALモード、UPSERT対応、旧JSONデータ自動移行
  - port 8766（Caddy: `/reader-predict/*` → 既存設定のまま）

- [x] **I2: systemdサービス更新（uvicorn起動）** (2026-03-07)
  - `/etc/systemd/system/reader-predict.service` を uvicorn起動に変更

- [x] **I3: /predictions/ コミュニティ投票ウィジェット** (2026-03-07)
  - Ghost page codeinjection_footにJS注入
  - stats-bulkで全予測の集計を一括取得、各カードにシナリオバー表示
  - 投票後にリアルタイムで分布更新

- [x] **I4: NORTH_STAR.md 予測プラットフォームミッション追記** (2026-03-07)
  - 全AIへの永続指示: ビジョン・モート・API仕様・TIER別状況・禁止事項

### TIER 1（未実装 — 1ヶ月以内）

- [ ] **I5: 読者Brier Score自動計算** (ローカル実装済み / VPSデプロイ未完了)
  - ✅ `scripts/reader_brier_calculator.py` — ローカル純粋Python計算モジュール。`calc_brier(prob, outcome)`, `calc_brier_bulk()`, `mean_brier()`, `verify_self_test()` 10/10 PASS
  - ✅ `scripts/vps_reader_brier_migration.py` — VPS側マイグレーションスクリプト。`--dry-run/--verbose/--notify` 対応
  - ⏳ VPSデプロイ: `scp scripts/vps_reader_brier_migration.py root@163.44.124.123:/opt/shared/scripts/` 後に `python3 /opt/shared/scripts/vps_reader_brier_migration.py --dry-run` で確認
  - ⏳ `reader_votes` テーブルへの `brier_score REAL / resolved_at TEXT / outcome REAL` カラム追加（VPS実行後）
  - 計算式: `(probability/100 - outcome)^2` — outcome: 的中=1.0, 外れ=0.0

- [x] **I6: 個人トラックレコードページ** (2026-03-11)
  - `/reader-predict/my-tracker/{uuid}` + `/reader-predict/my-stats/{uuid}` 追加済み
  - Ghost page `/my-predictions/` (JA) + `/en/my-predictions/` (EN) 公開済み
  - Caddy rewrite + redirect + hreflang 設定済み

- [x] **I7: 称号システム（基本5段階）** (2026-03-11)
  - 5段階: New Forecaster / Novice / Developing / Calibrated / Expert
  - `/reader-predict/my-stats/{uuid}` に `rank_label` 含む形で実装済み

- [x] **I8: NEO予測の自動参加** — 2026-03-11 完了
  - `neo_ai_player.py` を `/opt/shared/scripts/` に配置
  - `voter_uuid="neo-one-ai-player"` で242件バックフィル完了
  - 毎時cron (`0 * * * *`) で新規予測を自動ピックアップ

- [x] **I9: 解決時Telegram通知（読者統計付き）** — 2026-03-11 完了
  - `prediction_auto_verifier.py` に `get_reader_stats()` + `format_reader_stats_block()` 追加
  - 解決時Telegramに「👥コミュニティ予測」+「🤖NEO（AI）の予測」セクション追加

### TIER 2（未実装 — 2〜3ヶ月）

- [ ] **I10: リーダーボード公開ページ**
  - Brier Score上位20名（匿名UUID short形式）を /predictions/ に表示
  - UIレイアウト変更 → prediction-design-system.md の承認フロー必須

- [ ] **I11: AI vs 人間 月次レポート**
  - NEO（AI）vs 読者（人間）のBrier Score比較
  - Substack配信 + Xスレッド投稿

- [ ] **I12: パストキャスティング（過去問題練習）**
  - resolved予測を「練習問題」として提示 → Brier Scoreフィードバック
  - オンボーディング改善

- [ ] **I13: コメント機能**
  - `reader_votes` テーブルに `comment TEXT(280)` カラム追加
  - 投票後に上位3コメントを表示

- [ ] **I14: 週次Superforecaster X投稿**
  - `weekly_prediction_summary.py` 拡張（既存）
  - コミュニティ精度レポートを毎週月曜に@nowpattern投稿

### TIER 3（未実装 — 4〜6ヶ月）

- [ ] **I15: Substack「予測レター」連携**
  - 毎月コミュニティ集合知 vs AI予測比較レポートをSubstackで配信

- [ ] **I16: Nowpattern予測コンテスト（四半期）**
  - Brier Score最優秀者を選出・表彰（名誉）
  - メディア掲載・バイラル拡散目標

- [ ] **I17: AIエージェント公開参加**
  - GPT/Gemini等のAIが予測に参加できるAPIエンドポイント公開
  - 「AI vs Superforecaster vs 一般人」三つ巴比較

### TIER 4（未実装 — 6ヶ月以上）

- [ ] **I18: 公開API v1**
  - `nowpattern.com/api/v1/predictions` — 全予測データJSON公開
  - APIキー制（無料枠 + 高頻度有料）

- [ ] **I19: アカウント登録**
  - Ghost Members API連携、デバイス間トラックレコード同期

- [ ] **I20: Chrome Extension**
  - ニュースサイト閲覧中に関連Nowpattern予測をポップアップ表示

- [ ] **I21: OTS検証ページ**
  - `nowpattern.com/verify/` — Bitcoin timestamp証明を読者が検証

---

## J: 戦略的成長提案 (2026-03-15〜)

> **詳細**: `docs/NOWPATTERN_STRATEGIC_PROPOSALS.md`（37提案フル版）
> これらは「承認不要・今日着手可能」に分類されたもの。工数小〜中・可逆的変更のみ。

- [ ] **J1 (A2): 記事品質スコアリング自動化**
  - 各記事にBrier/engagement/誤情報リスクの3指標スコアを付与
  - article_validator.py を拡張して `quality_score` フィールドを追加
  - 目標: スコア70点未満は自動でDRAFT降格

- [ ] **J2 (B1): hreflang + JSON-LD 構造化データ強化**
  - JA/EN両ページのcodeinjection_headにArticle + BreadcrumbList JSON-LDを注入
  - hreflang属性の再確認・欠落補完（現在8ページ設定済み、全記事に拡張）
  - 目標: Google検索流入 +20〜40%

- [ ] **J3 (B2): X引用リポスト品質フィルタ強化**
  - x_swarm_dispatcher.pyにQuality Scoreフィルタ追加
  - エンゲージメント率<0.5%の記事はREPLY/QRT対象外に除外
  - 目標: 低品質投稿をゼロにしてエンゲージメント品質向上

- [ ] **J4 (B3): Substack週次テンプレート統一**
  - Substack配信記事のテンプレートを「予測要約+コミュニティ統計」形式に標準化
  - weekly_prediction_summary.py から自動生成
  - 目標: 解除率 -30%（テンプレート統一で読者の期待値を固定）

- [ ] **J5 (C2): 予測DB品質基盤強化**
  - prediction_db.jsonの全168件を品質監査（resolution_question・our_pick・確率の整合性チェック）
  - 空フィールド・矛盾データを検出してTelegram通知する audit_prediction_db.py 作成
  - 目標: Moat基盤の信頼性を100%に維持

- [ ] **J6 (C4): 予測パフォーマンス内部統計トラッキング**
  - カテゴリ別・トピック別・時期別のBrier Score分析ダッシュボードをTelegramレポート化
  - evolution_log.jsonのデータを集計してweakspot_tracker.py作成
  - 目標: 弱点トピック（Brier>0.25）を毎週特定して改善

- [ ] **J7 (I-プラットフォームI: 読者投票UIモバイル最適化)**
  - 現在の投票ウィジェットをモバイル（iPhone/Android）でテストし、タップ領域・フォントサイズを調整
  - Ghost codeinjection_foot のJSを更新（CSSメディアクエリ強化）
  - 目標: モバイル投票完了率 +30%

---

---

## K: 予測プラットフォーム世界No.1化（2026-03-17〜）

> **リサーチ根拠**: Metaculus 40K users・Polymarket $21.5B vol・Superforecaster Brier=0.081・GPT-4.5=0.101
> **現状**: 予測DB 476件（open:12, resolving:411, resolved:6）、Brier Score 0.2171（6件のみ）
> **目標**: Brier Score 0.20→0.15→0.081（Superforecaster水準）＋読者参加型プラットフォーム完成

- [x] **K1: wrong_lang自動修正cron + NEO CLAUDE.md修正** (2026-03-18 確認済)
  - VPS: `fix_prediction_links_auto.py` cron `55 6 * * *`（prediction_page_builder前に実行）
  - NEO CLAUDE.md に「EN予測のghost_urlは必ず `/en/[slug]/` 形式」ルール追加済み
  - 目標: wrong_lang:34の根本解決（新規追加も自動防止）

- [x] **K2: Brier Scoreスコアボード表示追加** (2026-03-18 確認済)
  - prediction_page_builder.py スコアボードに「Brier Score」表示追加済み
  - 世界基準との比較ゲージ（Superforecaster 0.081 / GPT-4.5 0.101）実装済み
  - 目標: Nowpatternの予測精度を読者に可視化 → 信頼構築

- [x] **K3-pre: prediction_auto_verifier.py JSONパースエラー修正** (2026-03-18)
  - 症状: `Opus error: Expecting ',' delimiter: line 1 column 151` が毎実行ゼロ件判定を引き起こしていた
  - 原因: `re.search(r'\{[^}]+\}')` がJSONフィールド内の `}` 文字で途中切れ
  - 修正: 3段階フォールバック（コードフェンス除去 → greedy `{.*}` → flat `{[^{}]*}`）
  - VPS: `/opt/shared/scripts/prediction_auto_verifier.py` 直接パッチ済み
  - 検証: `test_verifier.py` でJSONパース成功確認済み
  - 期待効果: 次回cron（毎日09:00 JST）から正常に判定開始

- [x] **K3: resolving→resolved自動バックフィル** (2026-03-18 完了)
  - `judge_with_opus` に YES/NO 判定パス追加（空 scenarios 対応）
  - `determine_hit_miss` / `calculate_brier_score` も空 scenarios ケース対応
  - `regenerate_predictions_page` の `article_title` KeyError 修正
  - 手動バックフィル実行: resolved 8件 → **19件**（+11件）
  - 完了時点（2026-03-18）の平均 Brier Score: **0.2197**（正確率 13/17 = 76%）
  - 次回 cron（毎日 00:00 UTC）から全 overdue を自動処理
  - ⚠️ 2026-03-20再監査: K3実装は正常稼働中。2026-03-19に自動verifier cronが3件を追加解決したが全てMISS（avg Brier=0.9546）。Brier悪化はK3完了後の運用上の新規解決による変化であり、K3実装の問題ではない。現在 resolved **22件**、avg Brier **0.3199**。evolution_loop.py の週次分析対象。

- [x] **K4: X RED-TEAMテンプレート更新** (2026-03-18 確認済)
  - x_swarm_dispatcher.py の RED-TEAM フォーマットを「YES-派/NO-派 構造」に刷新済み
  - Poll（YES / NO / まだわからない / 分析を読む）自動付与実装済み
  - 目標: 返信率10倍（X Algorithm: Replies=150×weight）

- [x] **K5: Ghost Members有効化** (2026-03-18 確認済)
  - portal_button=true / portal_plans=["free"] 設定済み
  - サインアップCTA: 「予測に参加（無料）」に更新済み
  - Paid tier（Stripe）: STRIPE_PUBLISHABLE_KEY/SECRET_KEY 取得後に設定

- [x] **K6: Schema.org Claimタグ全記事注入** (2026-03-18 確認済)
  - prediction_db.json に対応するClaimReview/Prediction JSON-LDを全記事に注入
  - VPS: 429件はNEOが注入済み。残り36件を `/tmp/k6_inject_missing.py` で注入完了（合計465/655件）
  - 予測記事（prediction_db.json ghost_url対応）: 578件中578件注入済み（100%）
  - 目標: Google/Perplexity/ChatGPT検索でNowpatternの予測が引用される

- [x] **K7: /api/predictions/ エンドポイント追加** (2026-03-18 確認済)
  - reader_prediction_api.py に `GET /api/predictions/` 実装済み（bak_k7_20260317）
  - 目標: AI/機械トラフィック（web traffic 50%超）からの参照獲得

- [x] **K8: Dual forecast NEO-ONE×TWO実装** (2026-03-18 確認済)
  - ai_vs_ai_predictor.py に dual_forecast ensemble 実装済み
  - ensemble_pick / ensemble_prob フィールドで出力
  - 目標: 単一モデル比 Brier Score -25%改善（アンサンブル効果）

- [x] **K9: 四半期予測トーナメント実装** (2026-03-17)
  - `/opt/shared/scripts/prediction_tournament.py` 作成・本番実行済み
  - Ghost pages: nowpattern.com/tournament/ + /en/tournament/ → 200 OK確認
  - Caddy routing: /en/tournament/ → /en-tournament/ 設定済み
  - cron: `0 0 1 1,4,7,10 *` (四半期初日00:00 UTC) 設定済み
  - 2026Q1結果: 解決済み7件、参加者3人、AI Brier=0.2042
  - 目標: バイラル拡散 + Metaculus競合読者の取り込み ✅

---

*最終更新: 2026-03-20 — 包括的SSOT監査完了 + 再監査完了。A〜H全カテゴリ + I1-I9 + K1-K9をVPS SSH・Ghost DB・systemd・crontab・APIエンドポイント・Caddy設定で全件照合。訂正: I5→[ ]（唯一の[x]誤記）、A2/B2に運用注記追加、H3にruntime artifact注記追加、K3に2026-03-19 Brier劣化記録追加。他全[x]は実装・配線・本文記述が一致。NEO-TWO DOWN状態も実態と一致（SHARED_STATE.md 整合）。*
