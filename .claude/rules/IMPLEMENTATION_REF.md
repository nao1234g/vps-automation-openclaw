# IMPLEMENTATION REFERENCE — 技術実装の参照書

> このファイルは技術的な実装詳細の参照書。フック・インフラ・デザインシステムの全情報。
> 哲学は NORTH_STAR.md、行動規範は OPERATING_PRINCIPLES.md を参照。
> 「書いただけでは実行されない。すべての原則は、コード・フック・スクリプトで強制される。」

---

## 1. 強制タイプの定義

| タイプ | 説明 | 違反時 |
|---|---|---|
| **A型: 物理ブロック** | exit 2でツール実行を完全停止 | 技術的に不可能（人間の意思不要） |
| **B型: 自動実行** | cronまたはhookが自動で実行 | 人間が忘れても動く |
| **C型: 人間判断** | 情報は自動収集、判断はNaoto | Telegram経由で提案のみ |

---

## 2. PVQE × 強制実装マップ

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

### 人間判断（C型）— 自動化不可の意思決定

| 判断事項 | 情報の自動準備 | Naotoの役割 |
|---|---|---|
| コンテンツ戦略の方向性 | Hey Loop毎日レポート | GO/NO GO |
| 予算・有料API承認 | コスト見積もり自動生成 | 承認のみ |
| 新プラットフォーム参入 | リサーチ自動収集 | 最終判断 |
| Type 1判断（不可逆な変更） | リスク自動評価 | 承認のみ |

---

## 3. ECC Pipeline（ミス防止自己進化システム）

> NORTH_STAR ECC原則の実装。これが「穴を塞ぐ」仕組みの実体。

| ステップ | タイプ | 実装 | ファイル |
|---|---|---|---|
| ミス発生 → KNOWN_MISTAKES.md 自動記録 | **B型** | PostToolUseFailure + 手動記録 | `.claude/hooks/error-tracker.py` |
| KNOWN_MISTAKES.md 更新 → パターン自動登録 | **B型** | PostToolUse(Edit/Write)でauto-codifier起動 | `.claude/hooks/auto-codifier.py` |
| 出力前にパターン照合 → 物理ブロック | **A型** | Stop hookでfact-checker起動（exit 2） | `.claude/hooks/fact-checker.py` |
| 未知パターンを意味レベルで検知 | **A型** | PreToolUse(Edit/Write)でGemini判定（exit 1） | `.claude/hooks/llm-judge.py` |
| 全ガードの劣化を毎日テスト | **B型** | regression-runner.py（46/46 PASS確認済み、T033） | `.claude/hooks/regression-runner.py` |
| 実装前に証拠計画を要求 | **A型** | PreToolUse(Edit/Write)でpvqe_p.json確認 | `.claude/hooks/pvqe-p-gate.py` |
| 証拠計画の実行を完了前に確認 | **A型** | Stop hookで実行済みBashを確認 | `.claude/hooks/pvqe-p-stop.py` |
| SSH前にVPS健全性チェック | **A型** | PreToolUse(Bash)でVPS状態確認 | `.claude/hooks/vps-ssh-guard.py` |

**現在のガード数: 36パターン（mistake_patterns.json）/ regression 46/46 PASS（T033 2026-03-29）**
**双方向パリティ確認: km⊆mp + mp⊆km（HG-15 + HG-19）/ フロアゲート: 45 ≥ 44（HG-21）**

---

## 4. 閉ループ設計（すべてのB型はこの構造を持つ）

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

---

## 5. 実装状況

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
✅ 完了: Hard Gate 19 (MP_KM_REVERSE_PARITY) + Hard Gate 21 (BASELINE_FLOOR_GATE) — 46/46 PASS (2026-03-29 T033)
✅ 完了: 7件のdocs-state gap全修正（km⊆mp + mp⊆km 双方向パリティ達成）(2026-03-29 T033)
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

## 6. VPS・Docker構成

- **VPS**: ConoHa 163.44.124.123（Caddy リバースプロキシ）
- **Compose**: `docker-compose.quick.yml`（現在使用中、`/opt/openclaw/`）
- **DB**: PostgreSQL 16 / `openclaw_secure_2026`
- **OpenClaw設定**: `config/openclaw/openclaw.json`（CLIフラグは不可）

### Docker Compose ファイル使い分け

| ファイル | 用途 |
|---|---|
| `docker-compose.quick.yml` | **本番（現在使用中）** |
| `docker-compose.dev.yml` | フル開発環境 |
| `docker-compose.minimal.yml` | 開発テスト用（PostgreSQL + OpenNotebook + N8N） |

### Docker セキュリティルール
- 全コンテナ: 非root実行（UID 1001）+ `no-new-privileges:true`
- ポートバインド: `127.0.0.1` のみ（Caddy以外）
- 変更後の検証: `docker compose config` → `docker compose up -d --build` → `docker logs --tail 20`

---

## 7. NEOアーキテクチャ（Telegram Claude Code Dual Agent）

**重要: Claude Max（$200/月定額）経由。Anthropic API（従量課金）は使用しない。**

| サービス | Bot | systemd | 役割 |
|---|---|---|---|
| NEO-ONE | `@claude_brain_nn_bot` | `neo-telegram.service` | CTO・戦略・記事執筆 |
| NEO-TWO | `@neo_two_nn2026_bot` | `neo2-telegram.service` | 補助・並列タスク |
| NEO-GPT | OpenAI Codex CLI | `neo3-telegram.service` | バックアップ |

- 作業ディレクトリ: `/opt`（`APPROVED_DIRECTORY`環境変数）
- permission_mode: `bypassPermissions`（両方）
- OAuthトークン: ローカルPC → VPS SCPコピー（Windowsタスクスケジューラ、4時間ごと）
- **制約**: OpenClawの`anthropic/`モデルはAPI課金 → NEOをOpenClawに追加してはいけない

---

## 8. ローカルClaude Code との役割分担

- **Neo（VPS）**: VPSファイル操作、Docker操作、記事執筆
- **ローカルClaude Code**: ローカルファイル編集、CLAUDE.md更新、git操作
- **衝突回避**: 両者が同時に同じVPSファイルを触らない

---

## 9. Hey Loop（インテリジェンス収集 + Telegram報告）

**スケジュール（1日4回 JST）**: 00:00 / 06:00 / 12:00 / 18:00

| データソース | 内容 | コスト |
|---|---|---|
| Reddit (Infra/Revenue) | r/selfhosted, r/SaaS等 | 無料 |
| Hacker News | トップ50記事 | 無料 |
| Gemini + Google Search | 14トピックローテーション | 無料 |
| Grok + X | AIビルダー収益報告 | $5クレジット（朝1回のみ） |

**共有知識**: `/opt/shared/AGENT_WISDOM.md` — タスク開始前に全エージェントが読む
**タスクログ**: `/opt/shared/task-log/YYYY-MM-DD_agent_タスク名.md`

---

## 10. 主要パス一覧

| パス | 用途 |
|---|---|
| `/opt/claude-code-telegram/CLAUDE.md` | NEO-ONE 実効指示書（46KB、neocloop所有） |
| `/opt/claude-code-telegram-neo2/CLAUDE.md` | NEO-TWO 実効指示書（38KB、neocloop所有） |
| ~~`/opt/CLAUDE.md`~~ | 退役済み (2026-03-14) → `.retired-20260314` に移動 |
| `/opt/shared/SHARED_STATE.md` | 30分ごと自動更新（最新状態の真実） |
| `/opt/shared/AGENT_WISDOM.md` | 全エージェント共有知識 |
| `/var/www/nowpattern/content/data/ghost.db` | Ghost CMS SQLite DB |
| `config/openclaw/openclaw.json` | OpenClaw設定（CLIフラグではなくここで変更） |

---

## 11. 予測ページ デザインシステム（凍結ベースライン）

> **このセクションが prediction_page_builder.py の「見た目の真実」。**
> Vibe Code Tip #4: デザインシステムを先に定義し、それ以外の変更を禁止する。
> 変更するには「UIレイアウト変更を承認する」フローが必要。

### カラーパレット（変更禁止）

| 用途 | 色コード | 使用箇所 |
|------|----------|---------|
| 私たちの予測（青） | `#2563eb` | テキスト強調、予測値 |
| 成功・的中（緑） | `#16a34a` / `#22c55e` | hit, optimistic outcome |
| 失敗・外れ（赤） | `#dc2626` / `#ef4444` | miss, pessimistic outcome |
| 正確率（黄） | `#fbbf24` | accuracy % |
| Polymarket（紫） | `#6366f1` | 市場確率 |
| 言語スイッチ・アクティブ（ゴールド） | `#b8860b` | JA/ENタブ |
| スコアボード背景（黒） | `#111` | 4列グリッド |
| カード背景（白） | `#fff` | 全カード |
| ラベル文字（グレー） | `#888` | セクションタイトル |
| ボーダー | `#333` | スコアボード内区切り線 |

### タイポグラフィ（変更禁止）

| 用途 | サイズ | ウェイト |
|------|--------|---------|
| スコアボード数字 | `2.6em` | `700` |
| セクションラベル | `0.75em` | `400`（letter-spacing: .08em） |
| 確率メイン表示 | `1.4em` | `700` |
| 確率ピル（小） | `0.95em` | `700` |
| タグラベル | `0.68em-0.72em` | `600` |
| Polymarketバッジ | `0.85em` | `700` |

### カードレイアウト（変更禁止）

```
┌────────────────────────────────────────┐
│  [LABEL: 0.75em #888 letter-spacing]   │  ← セクションタイトル
│                                        │
│ ┌──────────────────────────────────┐   │
│ │  background:#111  border-r:12px  │   │  ← スコアボード（4列グリッド）
│ │  [全] [的中] [外れ] [正確率]     │   │
│ │  2.6em 700 white                 │   │
│ └──────────────────────────────────┘   │
│                                        │
│ ┌──────────────────────────────────┐   │
│ │ bg:#fff br:12px sh:0 2px 8px    │   │  ← 予測カード
│ │ padding: 24px 28px               │   │
│ │ [タイトル]                        │   │
│ │ [私たちの予測 %] [市場の予測 %]  │   │
│ │ [シナリオ: 楽観/基本/悲観]       │   │
│ └──────────────────────────────────┘   │
└────────────────────────────────────────┘
```

**カード仕様:**
- `background: #fff`
- `border-radius: 12px`
- `padding: 24px 28px`
- `box-shadow: 0 2px 8px rgba(0,0,0,.08)`
- 確率表示: 3列フレックス（楽観/基本/悲観）

### スコアボード仕様

- `display:grid;grid-template-columns:repeat(4,1fr)`
- `background: #111`
- `border-radius: 12px`
- `padding: 20px 24px`
- 列間: `border-right: 1px solid #333`

### HTML ID / CSSクラス（変更禁止）

```
np-tracking-list  — 追跡中セクション外包wrapper
np-scoreboard     — スコアボード外包wrapper
np-resolved       — 解決済みセクション外包wrapper
```

---

## 12. デザイン アンチパターン（絶対禁止）

> Vibe Code Tip #5: 何をしてはいけないかをリストする。

### レイアウト系
- ❌ スコアボードを4列以外に変更する（2列、3列、6列も禁止）
- ❌ スコアボードの背景色を `#111` 以外にする
- ❌ カードの `border-radius` を12px以外にする
- ❌ カードの `padding` を `24px 28px` 以外にする
- ❌ 新しいセクションを追加する（未承認）
- ❌ 既存セクションの順序を変える（追跡中 → スコアボード → 解決済み）

### カラー系
- ❌ 成功色を赤に、失敗色を緑にする（意味が逆転する）
- ❌ 既存のカラーパレット外の色を追加する（未承認）
- ❌ Polymarketの紫（#6366f1）を別の色に変える

### テキスト系
- ❌ スコアボード数字のフォントサイズを `2.6em` から変える
- ❌ セクションラベルのフォントサイズを `0.75em` から変える
- ❌ `letter-spacing` を削除する

### HTML構造系
- ❌ `np-tracking-list` / `np-scoreboard` / `np-resolved` IDを変更・削除する
- ❌ テーブル要素（`<table>`, `<tr>`, `<td>`）を追加する
- ❌ カード外にフォームや入力要素を追加する

---

## 13. 変更可能なもの（承認不要）

- カード内の**テキストコンテンツ**（タイトル、説明文）
- 予測確率の**数値データ**
- 記事リンクのURL
- 言語切り替えリンクのテキスト
- エラーカードのメッセージ文言
- `--report` / `--dry-run` 等のCLIオプション追加

---

## 14. UI変更提案フロー（必須手順）

> Vibe Code Tip #1: ワイヤーフレームを先に。Tip #6: スクリーンショットを会話に使う。

```
Step 1: 変更内容のASCIIワイヤーフレームを表示する
        （上のカードレイアウト図のフォーマットを使う）

Step 2: 現在のスクリーンショットを参照する
        最新: ls /opt/shared/reports/page-history/ | tail -5

Step 3: 「before/after」を並べて示す（ASCII図で）

Step 4: 以下のコマンドを実行する:
        touch .claude/hooks/state/proposal_shown.flag

Step 5: Naotoに「UIレイアウト変更を承認する: [変更内容]」と発言を求める

Step 6: 承認を受けてから実装する
```

**このフローを飛ばした場合: `ui-layout-guard.py` が変更をブロックします。**
