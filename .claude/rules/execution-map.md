# Execution Map — OPERATING_PRINCIPLES → 実装対応表

> 「書いただけでは実行されない。すべての原則は、コード・フック・スクリプトで強制される。」
> 更新日: 2026-02-23

---

## 強制タイプの定義

| タイプ | 説明 | 違反時 |
|---|---|---|
| **A型: 物理ブロック** | exit 2でツール実行を完全停止 | 技術的に不可能（人間の意思不要） |
| **B型: 自動実行** | cronまたはhookが自動で実行 | 人間が忘れても動く |
| **C型: 人間判断** | 情報は自動収集、判断はNaoto | Telegram経由で提案のみ |

---

## PVQE × 強制実装マップ

### P（判断精度）— 正しく判断するための強制

| 原則 | タイプ | 実装 | ファイル |
|---|---|---|---|
| 実装前に世界中の実装例を検索 | **A型** | 新規コード作成・大規模編集をBLOCK | `.claude/hooks/research-gate.py:104` |
| 廃止済み用語（@aisaintel等）を参照しない | **A型** | 禁止用語を含む編集をBLOCK | `.claude/hooks/research-gate.py:22` |
| ミスを記録する | **B型** | エラー発生時にKNOWN_MISTAKES.mdに自動記録 | `.claude/hooks/error-tracker.py:84` |
| セッション開始時にVPS最新状態を把握 | **B型** | SessionStartでVPS状態を自動注入 | `.claude/hooks/session-start.sh:41` |

### V（改善速度）— 速く改善するための強制

| 原則 | タイプ | 実装 | ファイル |
|---|---|---|---|
| エラー→KNOWN_MISTAKESへ即記録 | **B型** | PostToolUseFailureで自動ドラフト生成 | `.claude/hooks/error-tracker.py` |
| セッション終了時にAGENT_WISDOMを更新 | **B型** | SessionEndでVPS AGENT_WISDOMに書き込み | `.claude/hooks/session-end.py` |
| 同じミスを繰り返さない | **A型** | KNOWN_MISTAKESに既存パターンがあれば-3警告 | `.claude/hooks/error-tracker.py:69` |

### Q（行動量）— 多く実行するための強制

| 原則 | タイプ | 実装 | ファイル |
|---|---|---|---|
| Hey Loopを1日4回実行 | **B型** | VPS cron（00:00/06:00/12:00/18:00 JST） | VPS: `crontab -l` |
| news-analyst-pipelineを1日3回実行 | **B型** | VPS cron（10:00/16:00/22:00 JST） | VPS: `crontab -l` |
| パイプライン失敗を自動検知・通知 | **B型** | 閉ループチェックスクリプト（毎時） | `scripts/closed-loop-check.sh` |

### E（波及力）— 広く伝えるための強制

| 原則 | タイプ | 実装 | ファイル |
|---|---|---|---|
| コンテンツ生成後に自動配信 | **B型** | NEO→Ghost→note/Substack自動投稿 | VPS: `note-auto-post.py` |
| 毎日Telegramでオーナーに報告 | **B型** | daily-learning.py がレポート送信 | VPS: `daily-learning.py` |
| 戦略的方向性の提案 | **C型** | Hey Loopが情報収集→Telegram提案（判断はNaoto） | VPS: `daily-learning.py` |

---

## 人間判断（C型）— 自動化不可の意思決定

| 判断事項 | 情報の自動準備 | Naotoの役割 |
|---|---|---|
| コンテンツ戦略の方向性 | Hey Loop毎日レポート | GO/NO GO |
| 予算・有料API承認 | コスト見積もり自動生成 | 承認のみ |
| 新プラットフォーム参入 | リサーチ自動収集 | 最終判断 |
| Type 1判断（不可逆な変更） | リスク自動評価 | 承認のみ |

---

## ECC Pipeline（ミス防止自己進化システム）— 2026-03-04 追加

> NORTH_STAR ECC原則の実装。これが「穴を塞ぐ」仕組みの実体。

| ステップ | タイプ | 実装 | ファイル |
|---|---|---|---|
| ミス発生 → KNOWN_MISTAKES.md 自動記録 | **B型** | PostToolUseFailure + 手動記録 | `.claude/hooks/error-tracker.py` |
| KNOWN_MISTAKES.md 更新 → パターン自動登録 | **B型** | PostToolUse(Edit/Write)でauto-codifier起動 | `.claude/hooks/auto-codifier.py` |
| 出力前にパターン照合 → 物理ブロック | **A型** | Stop hookでfact-checker起動（exit 2） | `.claude/hooks/fact-checker.py` |
| 未知パターンを意味レベルで検知 | **A型** | PreToolUse(Edit/Write)でGemini判定（exit 1） | `.claude/hooks/llm-judge.py` |
| 全ガードの劣化を毎日テスト | **B型** | regression-runner.py（25/25 PASS確認済み） | `.claude/hooks/regression-runner.py` |
| 実装前に証拠計画を要求 | **A型** | PreToolUse(Edit/Write)でpvqe_p.json確認 | `.claude/hooks/pvqe-p-gate.py` |
| 証拠計画の実行を完了前に確認 | **A型** | Stop hookで実行済みBashを確認 | `.claude/hooks/pvqe-p-stop.py` |
| SSH前にVPS健全性チェック | **A型** | PreToolUse(Bash)でVPS状態確認 | `.claude/hooks/vps-ssh-guard.py` |

**現在のガード数: 20パターン（mistake_patterns.json）/ regression 25/25 PASS**

---

## 実装状況（2026-03-04更新）

```
✅ 完了: 物理ブロック（廃止用語、研究なし新規コード）
✅ 完了: エラー自動記録（KNOWN_MISTAKES.md）
✅ 完了: セッション開始時VPS状態注入
✅ 完了: Hey Loop + news-analyst cron稼働
✅ 完了: AGENT_WISDOMセッション終了時更新
✅ 完了: 閉ループチェックスクリプト
✅ 完了: rules/ 7ファイル → CLAUDE.mdから正式@importで自動読み込み (2026-02-23)
✅ 完了: 「実装したつもり」防止 → fact-checker.py にWebファイル検証チェック追加 (2026-02-23)
✅ 完了: ECC Pipeline全段 — auto-codifier + llm-judge + pvqe-p + regression-runner (2026-03-04)
✅ 完了: regression-runner.py 25/25 PASS (2026-03-04)
✅ 完了: VPS FileLock + Ghost Webhook改ざん検知 (2026-03-04)
✅ 完了: VPS本番スクリプトのクラッシュ検知（0記事アラート）— zero-article-alert.py 30分cron (2026-03-04)
✅ 完了: Article Health DB (SQLite) + QA Sentinel バッチ — 151件監査、88タスク委譲 (2026-03-08)
✅ 完了: Ghost Webhook Server (port 8769) — 記事公開0.1秒後にQA自動実行 (2026-03-08)
✅ 完了: Hive Mind v2.0 双方向同期 — merge_wisdom.py + session-start.sh pull + VPS hourly aggregator (2026-03-08)
✅ 完了: Gateway Gates 5-7 — CJK汚染/最小長/必須セクション → DRAFT降格 (2026-03-08)
✅ 完了: service_watchdog.py 30分cron — 全9サービスの死活監視 (2026-03-08)
✅ 完了: logrotate /etc/logrotate.d/nowpattern — 5MB超で自動ローテーション (2026-03-08)
✅ 完了: QA処刑権 — overall_ok=0記事をGhost APIで即DRAFT降格 + Telegramレポートに⚰️表示 (2026-03-08)
✅ 完了: Webhook post.edited — タグ変更検知 → lang-ja/lang-en整合性チェック + Ghost DB登録済み (2026-03-08)
✅ 完了: Visual E2E統合 — check_single_article() + Playwright DOM/console.error確認 + 記事公開後非同期起動 (2026-03-08)
✅ 完了: AI Red-Teaming MVP — ai_redteam.py 独立モジュール + ghost_webhook_server.py lazy import (2026-03-09)
✅ 完了: Alert Triage — send_telegram(level="info"|"alert") QA PASS→ログのみ, QA FAIL→Telegram (2026-03-09)
✅ 完了: Dev-Time Approval Queue — pending_approvals.json + approval_utils.py + session-start.sh自動表示 (2026-03-09)
✅ 完了: SOTA & ROI Watcher — model_intel_bot.py 週1回cron(月曜JST09:00) + pending_approvals.jsonにエンキュー (2026-03-09)
✅ 完了: Prime Directive 刻印 — AGENT_WISDOM.md + /opt/CLAUDE.md 最上段にROI最大化原則 (2026-03-09)（※ /opt/CLAUDE.md は 2026-03-14 退役済み → AGENT_WISDOM.mdへの刻印は現存）
✅ 完了: NEO Queue Dispatcher — neo_queue_dispatcher.py 15分cron + slug単位でNEO-ONE/TWO交互割当 + 88件Pending解消 (2026-03-09)
✅ 完了: AI Red-Teaming 全稼働 — redteam_backfill.py 103件np-oracle記事に一括登録 + Dispatcherが15分ごと配送 (2026-03-09)
✅ 完了: Self-Evolving Architecture — evolution_loop.py 毎週日曜JST09:00 + Gemini Brier分析 + AGENT_WISDOM.md自己書き換え初回実証済み (2026-03-09)
✅ 完了: The Eternal Directives（永遠の三原則）— NORTH_STAR.md ミッション直下に刻印。north-star-guard.py強化でAI自律書き換え禁止 (2026-03-09)
✅ 完了: 原則11 Evolutionary Ecosystem — OPERATING_PRINCIPLES.md に追記。自然淘汰ループの哲学的根拠を明文化 (2026-03-09)
✅ 完了: evolution_log.json — 自己進化の監査証跡を永続記録（52週ローテ）+ session-start.sh毎起動時に進化サマリー表示 (2026-03-09)
❌ 未完了: Medium自動投稿（MEDIUM_TOKEN待ち）
❌ 未完了: NAVER Blog自動投稿（SMS認証待ち）
```

---

## 閉ループ設計（すべてのB型はこの構造を持つ）

```
[観測] hooks/cron が状態を検知
  ↓
[判断] スクリプト が条件を評価
  ↓
[実行] API/ファイル操作 を実行
  ↓
[検証] レスポンス/ログ を確認
  ↓
[記録] KNOWN_MISTAKES / task-log に書き込み
  ↓
[改善] AGENT_WISDOM / CLAUDE.md を更新
  ↑__________________________________|
```

*このファイル自体がB型: session-start.sh が毎回読み込む（VPS接続成功時）*
