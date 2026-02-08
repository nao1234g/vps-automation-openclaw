# Notion自動整理ワークフロー セットアップガイド

## 📋 概要
毎日21時にNotionの未整理ページをAIが自動でカテゴリ・タグ付けする。

---

## 🔧 事前準備

### 1. Notion API トークン取得

1. https://www.notion.so/my-integrations にアクセス
2. 「+ New integration」をクリック
3. 名前: 「N8N Auto Organize」
4. 「Submit」→ **Internal Integration Token** をコピー

### 2. Notionデータベース設定

使用するデータベースに以下のプロパティを追加：

| プロパティ名 | タイプ |
|-------------|--------|
| Category | Select |
| Tags | Multi-select |
| Status | Select（未整理/整理済み） |

### 3. データベースIDを取得

データベースページのURLから取得：
```
https://www.notion.so/xxxxxx?v=yyyyy
                    ^^^^^^
                    これがDatabase ID
```

### 4. インテグレーションを接続

データベース右上「...」→「Add connections」→ 作成したインテグレーションを追加

---

## 🔧 N8N設定

### 1. Credentials追加

N8N → Settings → Credentials → Add New

- Type: **Notion API**
- Token: 取得したInternal Integration Token

### 2. 環境変数設定

N8N → Settings → Variables

| 変数名 | 値 |
|--------|-----|
| NOTION_DATABASE_ID | データベースID |
| GEMINI_API_KEY | あなたのGemini APIキー |

### 3. ワークフローインポート

1. N8N → Workflows → Import from file
2. `notion-auto-organize.json` を選択
3. Credentials を設定
4. 「Active」にする

---

## ✅ 動作確認

1. データベースに未整理ページを追加
2. ワークフローを手動実行
3. カテゴリ/タグが自動で設定されればOK

---

## 📊 カテゴリ一覧

| カテゴリ | 説明 |
|----------|------|
| 仕事 | 業務関連 |
| アイデア | 思いつき・構想 |
| 学習 | 勉強ノート |
| プロジェクト | 進行中の企画 |
| メモ | 雑記 |
| その他 | 分類不能 |
