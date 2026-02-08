# RSS記事自動生成 セットアップガイド（無料版）

## 📋 概要
複数のRSSフィードから最新ニュースを取得 → AIがオリジナル記事を生成

**Feedly不要・完全無料！**

---

## 🔄 ワークフロー構成

```
毎日8:00
  ↓
TechCrunch + GIGAZINE + Publickey（並列取得）
  ↓
記事を統合 → 上位5件を抽出
  ↓
Gemini AIがオリジナル記事を生成
  ↓
記事出力（Note/X投稿用）
```

---

## 📡 デフォルトRSSフィード

| サイト | RSS URL |
|--------|---------|
| TechCrunch Japan | https://jp.techcrunch.com/feed/ |
| GIGAZINE | https://gigazine.net/news/rss_2.0/ |
| Publickey | https://www.publickey1.jp/atom.xml |

---

## 🔧 N8Nセットアップ

### Step 1: 環境変数設定

N8N → Settings → Variables

| Name | Value |
|------|-------|
| GEMINI_API_KEY | あなたのGemini APIキー |

### Step 2: ワークフローインポート

1. N8N → Workflows → Import from file
2. `rss-article-workflow.json` を選択
3. 「Active」にする

---

## ✏️ フィードのカスタマイズ

自分の興味に合わせてRSSフィードを追加・変更できます：

### おすすめフィード

| ジャンル | サイト | RSS URL |
|---------|--------|---------|
| AI | AI-SCHOLAR | https://ai-scholar.tech/feed |
| 開発 | Zenn | https://zenn.dev/feed |
| スタートアップ | THE BRIDGE | https://thebridge.jp/feed |
| 仮想通貨 | CoinPost | https://coinpost.jp/feed |
| ビジネス | NewsPicks | なし（API必要） |

---

## 📊 Feedlyとの比較

| 項目 | RSS Feed Node | Feedly Pro |
|------|---------------|------------|
| 料金 | **無料** | $6/月 |
| 記事品質 | 同等 | 同等 |
| セットアップ | 簡単 | Token取得必要 |
| フィード管理 | N8N内で設定 | Feedly UIで管理 |

---

## ✅ 使い方

1. ワークフローをインポート
2. テスト実行
3. 毎日8時に自動で記事が生成される！
