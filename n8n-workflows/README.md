# N8N ワークフロー

> 最終更新: 2026-02-23
> VPS（163.44.124.123）で **13ワークフロー** 稼働中

---

## 🔗 アクセス情報

| サービス | URL / 識別子 |
|----------|-----|
| N8N | https://n8n.nowpattern.com/ |
| OpenClaw (Jarvis) | Telegram: @openclaw_nn2026_bot |
| NEO-ONE | Telegram: @claude_brain_nn_bot |

---

## 🚀 稼働中ワークフロー（13本）

VPS上で稼働中のワークフローは `ssh root@163.44.124.123` → N8N管理画面で確認。

### AISAコンテンツパイプライン（9本）
| ワークフロー | 実行タイミング | 内容 |
|-------------|---------------|------|
| RSS収集 | 毎日 7/13/19時 JST | rss-news-pipeline.py起動 |
| 深層分析 | 毎日 7:30/13:30/19:30時 JST | analyze_rss.py（Gemini深層分析） |
| note投稿 | 毎時0分 | note-auto-post.py（日本語） |
| Substack投稿 | 毎時0分 | Substack自動投稿（英語） |
| X投稿 | 毎時0分 | rss-post-quote-rt.py（X引用リポスト） |
| ニュース分析 | 毎日 10/16/22時 JST | news-analyst-pipeline.py（6プラットフォーム） |
| Ghost投稿 | ニュース分析後 | nowpattern-ghost-post.py |
| 週次分析 | 毎週日曜 23時 JST | weekly-analysis.sh（タスクログ集計） |
| Morning Briefing | 毎朝 | Telegramで要約配信 |

### システム監視（4本）
| ワークフロー | 実行タイミング | 内容 |
|-------------|---------------|------|
| ヘルスチェック | 15分ごと | コンテナ・サービス状態監視 |
| DB自動バックアップ | 毎日深夜 | PostgreSQLダンプ保存 |
| 閉ループチェック | 毎時 | パイプライン稼働確認 + Telegram通知 |
| セキュリティスキャン | 毎週日曜 | Trivy + Docker Bench |

---

## 📁 ローカルファイル構成

```
n8n-workflows/
├── theme-config.md     # テーマ設定
├── prompts.md          # プロンプト集
├── rss-setup.md        # RSS設定ガイド
└── README.md           # このファイル
```

---

## 🔒 N8N API認証

```
Header: X-N8N-API-KEY: <APIキー>
```
（Basic Auth は使わない — KNOWN_MISTAKES参照）
