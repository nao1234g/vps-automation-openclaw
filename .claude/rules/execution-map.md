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

## 実装状況

```
✅ 完了: 物理ブロック（廃止用語、研究なし新規コード）
✅ 完了: エラー自動記録（KNOWN_MISTAKES.md）
✅ 完了: セッション開始時VPS状態注入
✅ 完了: Hey Loop + news-analyst cron稼働
✅ 完了: AGENT_WISDOMセッション終了時更新
✅ 完了: 閉ループチェックスクリプト
✅ 完了: rules/ 7ファイル → CLAUDE.mdから正式@importで自動読み込み (2026-02-23)
✅ 完了: 「実装したつもり」防止 → fact-checker.py にWebファイル検証チェック追加 (2026-02-23)
✅ 完了: git pre-commit hook → APIキー漏洩防止 + KNOWN_MISTAKESリマインダー (2026-02-23)
✅ 完了: NEO SessionStart hook デプロイ済み (2026-02-23)
✅ 完了: llms.txt デプロイ済み (2026-02-23)
✅ 完了: EN URL統一 — Caddy /en/tag/* rewrite + codeinjection 10箇所修正 + タグ言語フィルタJS (2026-02-23)
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
