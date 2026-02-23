# Hey Loop Intelligence System

> 「AIを使ってAIのトークンコスト以上にリターンを生む循環システム」
> インフラ監視 + 収益特化インテリジェンスを1日4回収集し、Telegram経由でオーナーに提案。

---

## ループの構造

```
世界の情報収集 → 分析 → オーナーに提案（Telegram）
  → オーナー判断 → 実行 → 収益化 → 再投資 → ... (Hey Loop)
```

## 3層の学習

| 層 | 内容 | 仕組み |
|---|---|---|
| 守り | 同じミスを繰り返さない | KNOWN_MISTAKES.md → AGENT_WISDOM.md |
| 攻め | インフラ + 収益の両面でリアルデータ収集 | daily-learning.py v3（5データソース、1日4回） |
| 伝播 | 全エージェント + オーナーに知識を共有 | /shared/ + Telegram自動通知 |

## 共有知識ファイル

- **`/opt/shared/AGENT_WISDOM.md`** = コンテナ内 `/shared/AGENT_WISDOM.md`
  - 全エージェント共通の知恵・教訓・技術知識
  - Jarvisたちはタスク開始前にこのファイルを読む
  - Neoが更新管理を担当
  - ローカルコピー: `docs/AGENT_WISDOM.md`

## 自動実行スケジュール（4回/日）

| 時刻 (JST) | UTC | 内容 |
|---|---|---|
| 00:00 | 15:00 | Night Scan — グローバル市場、オーバーナイトニュース |
| 06:00 | 21:00 | Morning Briefing — メインレポート + Grok X検索 |
| 12:00 | 03:00 | Midday Update — トレンド、新着投稿 |
| 18:00 | 09:00 | Evening Review — 1日のサマリー + アクション提案 |
| 毎週日曜 23:00 | 14:00 | 週次タスクログ分析（weekly-analysis.sh） |

## データソース

| ソース | 内容 | コスト |
|---|---|---|
| Reddit (Infra) | r/selfhosted, r/n8n, r/docker, r/PostgreSQL等 | 無料 |
| Reddit (Revenue) | r/AI_Agents, r/SideProject, r/SaaS等 | 無料 |
| Hacker News | トップ50記事 | 無料 |
| GitHub | インフラ + AI Builderリポジトリ | 無料 |
| Gemini + Google Search | 14トピックローテーション + 動的発見 | 無料 |
| Grok + X | AIビルダー収益報告 | $5クレジット（朝1回のみ） |

## トピックローテーション（14トピック = 3.5日サイクル）

**インフラ（7）**: AI Agent Architecture, Docker Security, N8N Advanced Patterns, LLM Cost Optimization, Content Automation Pipeline, PostgreSQL Performance, Telegram Bot Best Practices

**収益（7）**: AI Newsletter Revenue, AI Automation Agencies, AI SaaS Products, Content Monetization Strategies, AI Builder Case Studies, Multilingual AI Content Business, AI Agent Marketplace

## 各エージェントの責務

| エージェント | 役割 |
|---|---|
| Neo | 統括者。AGENT_WISDOM.md更新、学習レポートレビュー |
| Jarvis | タスク前に必読。タスク後にtask-logに記録 |
| ローカルClaude Code | CLAUDE.md + KNOWN_MISTAKES.md管理。VPSに同期 |
| Jarvis（OpenClaw 1体） | AGENT_WISDOM.mdを読んでから作業。新知見はtask-logに記録 |

## タスクログ

- 場所: `/opt/shared/task-log/`
- 形式: `YYYY-MM-DD_agent-name_short-description.md`
- テンプレート: `/shared/task-log/HOW_TO_LOG.md`
- 全エージェントがタスク完了後に記録する

## 学習結果の確認

- インテリジェンスダッシュボード: `/opt/shared/learning/DASHBOARD.md`
- 週次分析: `/opt/shared/reports/YYYY-MM-DD_weekly-learning-analysis.md`
- Telegram: オーナーのスマホに自動通知（1日4回）
