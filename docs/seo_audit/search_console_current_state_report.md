# Google Search Console 現状レポート
> 作成日: 2026-03-26 | nowpattern.com SEO Audit

---

## 重要な前提

**現セッションでは Search Console への直接アクセスは実施していない。**
このレポートは以下の情報に基づく:
- Ghost SQLite DB から取得した記事数・タグ情報
- VPS での HTTP ステータス確認（curl）
- `robots.txt` / Caddyfile の直接確認
- `a4-hreflang-injector.py` のログ分析

実際の GSC データ（インデックス数・クロール統計・検索パフォーマンス）は
Naoto が Google Search Console にログインして確認すること。

---

## 推定インデックス状況

### 期待インデックス数

| URL パターン | 記事数 | インデックス可否 |
|------------|--------|----------------|
| JA 記事 `/{slug}/` | 215件 | ✅ インデックス可能 |
| EN 記事 `/en/{slug}/` | 1,111件 | ✅ インデックス可能 |
| タグなし記事 | 16件 | ✅ インデックス可能 |
| 固定ページ（/about/, /predictions/ 等） | 8件 | ✅ インデックス可能 |
| `/tag/genre-*` | 13件 | ❌ noindex（修正済み） |
| `/tag/event-*` | 19件 | ❌ noindex |
| `/tag/p-*` | 16件 | ❌ noindex |
| `/tag/lang-*` | 2件（lang-ja, lang-en） | ❌ noindex |
| `/tag/deep-pattern/` | 1件 | ❌ noindex |
| `/tag/nowpattern/` | 1件 | ❌ noindex（全記事インデックスハブ。後で再考推奨） |
| ドラフト | 537件 | ❌ Ghost が非公開 |

**期待最大インデックス数: 1,342 + 8 = 1,350件**

---

## Search Console 確認チェックリスト（Naoto 実施事項）

### 即座に確認すべき項目

```
1. カバレッジレポート
   サイドバー → 「インデックス作成」→「ページ」

   確認事項:
   □ インデックス済みページ数（目標: 700件以上）
   □ 「除外」のページ数と理由
   □ 「クロール済み - 現在インデックスなし」の件数
   □ 「検出済み - 現在インデックスなし」の件数
```

```
2. 国際ターゲティング（hreflang確認）
   サイドバー → 「国際ターゲティング」→「言語」タブ

   確認事項:
   □ hreflang エラー数（0であるべき）
   □ 代替ページの数（JA ↔ EN ペアが正しく認識されているか）
```

```
3. サイトマップ
   サイドバー → 「サイトマップ」

   確認事項:
   □ https://nowpattern.com/sitemap.xml が送信済みか
   □ 送信ページ数 vs 登録ページ数の一致
   □ エラーがないか
```

```
4. ページエクスペリエンス
   サイドバー → 「ページエクスペリエンス」

   確認事項:
   □ Core Web Vitals のステータス（良好/要改善/不良）
   □ /predictions/ ページの個別評価
```

---

## 現在の技術的状態（2026-03-26 確認済み）

### sitemap

```
https://nowpattern.com/sitemap.xml → Ghost 自動生成
```

Ghost の sitemap には以下が含まれる:
- 全 published 記事
- 固定ページ
- タグページ（内部タクソノミータグを含む可能性）

**懸念**: Ghost の sitemap が `/tag/genre-*` 等の noindex ページを含む場合、
Google は「サイトマップに含まれているのに noindex」という矛盾を検知する。
これは SEO ペナルティにならないが、クロールバジェットの浪費になる。

**推奨**: GSC の「サイトマップ」で登録件数を確認し、Ghost 公式 sitemap から
noindex ページを除外するカスタム sitemap の作成を検討する（優先度: 低）。

### robots.txt 現状

```
https://nowpattern.com/robots.txt:

User-agent: *
Sitemap: https://nowpattern.com/sitemap.xml
Disallow: /ghost/
Disallow: /email/
Disallow: /members/api/comments/counts/
Disallow: /r/
Disallow: /webmentions/receive/
```

`/tag/*` を Disallow していない設計は**意図的かつ正しい**。
理由: Disallow にすると Google が noindex ヘッダーを読めなくなる。

---

## hreflang 注入進捗（2026-03-26 08:44 JST）

| 指標 | 数値 |
|------|------|
| 処理済み記事数 | 737/1342（55%） |
| JA-EN ペアリング済み | 約617件 |
| EN ソロ（JA対訳なし） | 約494件 |
| 注入スクリプト PID | 1481476（稼働中） |

完了後、GSC 国際ターゲティングレポートで確認すること（反映まで1〜2週間）。

---

## 検索パフォーマンスの基準値設定

GSC でアクセスできる場合、以下の基準値を記録すること:

```
確認日: 2026-03-26
クリック数（過去28日）: ____
表示回数（過去28日）: ____
平均CTR: ____%
平均掲載順位: ____
インデックス済みページ数: ____
```

この数値を月次で追跡し、SEO 施策の効果を測定する。

---

## 次のアクション（優先度順）

| 優先度 | タスク | 担当 | 期限 |
|--------|--------|------|------|
| P1 | GSC にログインして現状基準値を記録 | Naoto | 今週 |
| P1 | 国際ターゲティングで hreflang エラーを確認 | Naoto | hreflang注入完了後1週間 |
| P2 | サイトマップ送信済みか確認 | Naoto | 今週 |
| P3 | カバレッジレポートでインデックス除外ページの理由確認 | Naoto | 今月 |
| P4 | /tag/nowpattern/ の noindex 解除検討 | 要討議 | 来月 |

---

*作成: 2026-03-26 | Session: SEO Audit*
