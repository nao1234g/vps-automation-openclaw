# Feedly記事自動生成 セットアップガイド

## 📋 概要
Feedlyから最新ニュースを取得 → AIが高品質なオリジナル記事を生成

---

## 🔄 ワークフロー

```
毎日8:00
  ↓
Feedly API: 購読フィードから最新10記事取得
  ↓
上位5記事を抽出・要約
  ↓
Gemini AI: ニュースを参考にオリジナル記事生成
  ↓
記事出力（Note/X投稿用）
```

---

## 🔧 Feedly API設定

### 1. Developer Tokenを取得

1. https://feedly.com/v3/auth/dev にアクセス
2. ログイン → Developer Token を取得
3. Token は30日間有効（更新が必要）

### 2. Stream IDを取得

Feedlyのカテゴリ/フィードのID：
```
# 全ての記事
user/YOUR_USER_ID/category/global.all

# 特定カテゴリ
user/YOUR_USER_ID/category/YOUR_CATEGORY_NAME

# 特定フィード
feed/https://example.com/rss
```

※ ブラウザのネットワークタブから確認可能

---

## 🔧 N8N環境変数

| 変数名 | 値 |
|--------|-----|
| FEEDLY_ACCESS_TOKEN | Developer Token |
| FEEDLY_STREAM_ID | カテゴリ/フィードID |
| GEMINI_API_KEY | Gemini APIキー |

---

## ⚠️ 注意事項

### Feedly API制限
- 無料プラン: 250リクエスト/日
- Pro: 500リクエスト/日
- Pro+: 無制限

### 著作権について
- 記事の**コピー**は禁止
- AIによる**要約・独自解説**はOK
- 必ず**出典を明記**すること

---

## 📊 おすすめのフィード設定

AI/テック系記事に最適なフィード：

| サイト | RSS URL |
|--------|---------|
| TechCrunch Japan | https://jp.techcrunch.com/feed/ |
| GIGAZINE | https://gigazine.net/news/rss_2.0/ |
| ITmedia | https://rss.itmedia.co.jp/rss/2.0/itmedia_all.xml |
| Publickey | https://www.publickey1.jp/atom.xml |
| AI-SCHOLAR | https://ai-scholar.tech/feed |

---

## ✅ 使い方

1. 上記フィードをFeedlyに登録
2. 「AIニュース」などのカテゴリを作成
3. そのカテゴリのStream IDを取得
4. N8Nワークフローに設定
5. 毎日8時に自動で高品質記事が生成される！
