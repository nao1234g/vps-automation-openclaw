# N8N + OpenClaw 自動化セットアップガイド

## 📁 ファイル構成

```
vps-automation-openclaw/
├── n8n-workflows/
│   ├── note-article-workflow.json      # Note記事自動生成
│   ├── x-autopost-workflow.json        # X自動投稿
│   ├── weekly-report-workflow.json     # 週次レポート生成
│   ├── multi-theme-workflow.json       # マルチテーマローテーション
│   ├── theme-config.md                 # テーマ設定ドキュメント
│   ├── prompts.md                      # プロンプト集
│   └── README.md                       # このファイル
├── scripts/
│   ├── install-n8n.sh                  # N8Nインストール
│   ├── security-hardening.sh           # セキュリティ強化
│   └── install-skills.sh               # スキルインストール
└── .env                                # 環境変数
```

---

## 🔗 アクセス情報

| サービス | URL |
|----------|-----|
| OpenClaw | https://163.44.124.123.nip.io/ |
| N8N | https://n8n.163.44.124.123.nip.io/ |
| Telegram | @openclaw_nn2026_bot |

---

## 🚀 ワークフロー一覧

| ワークフロー | 実行タイミング | 内容 |
|-------------|---------------|------|
| 毎日記事生成 | 毎日9:00 | AIがブログ記事を自動生成 |
| 週次レポート | 毎週月曜9:00 | AI/テック業界のトレンドまとめ |
| マルチテーマ | 毎日9:00 | 7テーマからランダム選択 |

---

## 🔒 セキュリティ

VPSで実行：
```bash
bash scripts/security-hardening.sh
```

---

## 📦 スキル追加

VPSで実行：
```bash
bash scripts/install-skills.sh
```
