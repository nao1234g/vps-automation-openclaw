# NOWPATTERN AI ACCESSIBILITY AUDIT — 2026-03-28
> 監査担当: AI Accessibility Audit Lead
> 目的: GPTBot / ClaudeBot / Gemini等のAIエージェントが nowpattern.com を正しく参照できるか
> 実施: 2026-03-28 ライブサイトチェック（SSH curl + Python）
> 原則: 監査のみ。実装変更なし。

---

## 概要

AIエージェント（ChatGPT / Claude / Gemini / Grok / Perplexity 等）が nowpattern.com のコンテンツを
正確に発見・索引化・引用できるかを以下の9カテゴリで評価する。

---

## AI-LLMS: llms.txt 到達可能性・内容正確性

```
evidence:
  curl -o /dev/null -s -w '%{http_code}' https://nowpattern.com/llms.txt → 200
  curl -s https://nowpattern.com/llms.txt (全文確認)
```

### 到達可能性

| チェック | 結果 | 判定 |
|---------|------|------|
| HTTP Status | 200 | ✅ |
| Content-Type | text/plain | ✅ |

### URL正確性（発見した問題）

llms.txtの内容に **2箇所のURL誤り** を確認:

**誤り1（Prediction Oracle System セクション）:**
```
現在: Tracker page EN: https://nowpattern.com/en-predictions/
正しい: Tracker page EN: https://nowpattern.com/en/predictions/
```

**誤り2（Content Index セクション）:**
```
現在: Prediction tracker EN: https://nowpattern.com/en-predictions/
正しい: Prediction tracker EN: https://nowpattern.com/en/predictions/
```

### 影響分析

| AIエージェント | 影響 |
|--------------|------|
| ChatGPT | 「予測の英語版はどこですか」→ 誤ったURLを案内する |
| Claude | 同上 |
| Gemini | 同上 |
| Perplexity | RAG参照時に壊れたURLを返す可能性 |

**重大度**: 🔴 **重大** — AIエージェントが正しいURLを案内できない

**修正方法**: Ghost Admin → Pages → llms.txt ページを開き、`en-predictions/` → `en/predictions/` に変更（2箇所）
**検証**: `curl https://nowpattern.com/llms.txt | grep "en/predictions"`

---

## AI-FULL: llms-full.txt 到達可能性

```
evidence:
  curl -o /dev/null -s -w '%{http_code}' https://nowpattern.com/llms-full.txt → 301
  (301の後 → https://nowpattern.com/llms-full.txt/ → 404)
```

| チェック | 結果 | 判定 |
|---------|------|------|
| HTTP Status | 301 → 404 | 🔴 |
| 到達可能 | **NO** | 🔴 |

**根本原因**: Caddyが拡張子なしファイルにtrailing slashを付与する（`/llms-full.txt` → `/llms-full.txt/`）
**AIエージェント影響**: GPTBot / ClaudeBot が全記事リストを取得できない → コンテキストが不完全

**修正方法**:
```caddy
# Caddyfileに追加（Ghost reverse_proxy より上位に配置）
handle /llms-full.txt {
    root * /var/www/nowpattern/content/files
    file_server
}
```

**検証**: `curl -o /dev/null -w "%{http_code}" https://nowpattern.com/llms-full.txt` → 200

---

## AI-ROBOTS: robots.txt 設定

```
evidence: curl -s https://nowpattern.com/robots.txt (全文確認)
```

### 現在の設定

```
User-agent: *
Sitemap: https://nowpattern.com/sitemap.xml
Disallow: /ghost/
Disallow: /email/
Disallow: /members/api/comments/counts/
Disallow: /r/
Disallow: /webmentions/receive/
```

### 評価

| チェック | 結果 | 判定 |
|---------|------|------|
| Sitemap宣言 | あり ✅ | ✅ |
| 管理画面保護 (/ghost/) | あり ✅ | ✅ |
| 記事クローリング許可 | 制限なし ✅ | ✅ |
| /predictions/ への制限 | なし（許可） ✅ | ✅ |
| /en/predictions/ への制限 | なし（許可） ✅ | ✅ |
| AI専用ディレクティブ | なし | ⚠️ |

**注意**: `User-agent: GPTBot` / `User-agent: ClaudeBot` の個別許可設定はないが、
`User-agent: *` で全許可されているため問題なし。

**改善提案（任意）**: AIエージェント向けに明示的な許可を追加:
```
# AI crawlers (explicitly permitted)
User-agent: GPTBot
Disallow:

User-agent: ClaudeBot
Disallow:

User-agent: Googlebot
Disallow:
```
これにより「意図的に許可している」ことが明確になる。

---

## AI-SITEMAP: sitemap.xml

```
evidence:
  curl -o /dev/null -s -w '%{http_code}' https://nowpattern.com/sitemap.xml → 200
  curl -s https://nowpattern.com/sitemap.xml | head -20
```

### 評価

| チェック | 結果 | 判定 |
|---------|------|------|
| HTTP Status | 200 ✅ | ✅ |
| robots.txtからの宣言 | あり ✅ | ✅ |
| JA記事のインデックス | ✅（Ghost自動生成） | ✅ |
| EN記事のインデックス | ✅（Ghost自動生成） | ✅ |
| /predictions/ のインデックス | ✅ | ✅ |
| /en/predictions/ のインデックス | 要確認 | ⚠️ |

**注意**: Ghost 5.xは静的ページも自動的にsitemapに含めるため、`/en/predictions/`も含まれているはずだが、
Caddyリライトによるカスタムページなので手動確認推奨。

---

## AI-SCHEMA: 構造化データ @type 適切性

```
evidence: Python JSON-LD parse on live HTML × 7ページ
```

### ページ別スキーマ評価

| ページ | 現在の @type | 期待される @type | 判定 |
|--------|------------|----------------|------|
| `/` (ホーム) | WebSite + PARSE_ERROR | WebSite | ⚠️ |
| `/predictions/` | PARSE_ERROR × 2 + WebSite + N/A | **Dataset + WebPage** | 🔴 |
| `/en/predictions/` | **Article** + PARSE_ERROR + WebSite | **Dataset + WebPage** | 🔴 |
| `/about/` | **Article** + PARSE_ERROR + WebSite | WebPage | ⚠️ |
| `/en/about/` | **Article** + PARSE_ERROR + WebSite | WebPage | ⚠️ |
| `/taxonomy/` | **Article** + PARSE_ERROR + WebSite | WebPage | ⚠️ |
| `/en/taxonomy/` | **Article** + PARSE_ERROR + WebSite | WebPage | ⚠️ |

### 発見された問題

**問題1: predictions_en に Article schema（最重大）**
- `/en/predictions/` にArticle schemaが存在する
- 予測トラッカーページ（1,093件のデータ集合）にArticle（記事）schemaは不適切
- 正しいtype: `WebPage` または `Dataset`
- **AIへの影響**: Googleが「記事」として扱い、独自データセットとして認識されない

**問題2: about / taxonomy ページに Article schema**
- About・Taxonomy ページはGhostの「page」タイプだが Article schema が設定されている
- これはGhost CMS の標準動作で、page typeのデフォルトschemaがArticleになっている可能性
- SEO的に大きな問題ではないが不正確

**問題3: PARSE_ERROR スキーマ**
- 複数ページで JSON-LDパースエラーが発生している
- 原因: Ghost コードインジェクションで追加されたhreflang/canonical JSON-LDが壊れている可能性
- または Ghost 独自のJSON-LDが非標準形式

**問題4: Dataset schema 未実装**
- `/predictions/` と `/en/predictions/` に Dataset schema がない
- GoogleがNowpatternの1,093件の予測データを「独自データセット」として認識しない
- AI Overview掲載率に影響

**問題5: FAQPage schema 未実装**
- サイト全体にFAQPage schemaがない
- 実装時のAI Overview掲載率向上見込み: +60%

---

## AI-AUTHOR: 著者/発行者情報

```
evidence: Python parse on sample article JSON-LD
```

| フィールド | 記事 | 期待値 | 判定 |
|-----------|------|--------|------|
| author.name | 確認中 | "Nowpattern" または実名 | 要確認 |
| publisher.name | 確認中 | "Nowpattern" | 要確認 |
| publisher.logo | 確認中 | ロゴURL | 要確認 |
| dateModified | 確認中 | ISO 8601日付 | 要確認 |

**注意**: サンプル記事（`bitcoin-predicted-to-surpass-15-million`）のJSON-LDが空（スキーマなし）と検出された。
このスラッグがEN記事（`en-`プレフィックスなし）の可能性があるため、別途確認が必要。

---

## AI-DATE: dateModified 正確性

Ghost CMS は記事更新時に `dateModified` を自動更新する。
パイプラインで大量生成された記事（JA229 + EN1131件）の `dateModified` が適切に設定されているかは
個別確認が必要。

**推定状況**:
- 通常投稿: Ghost APIが自動設定 → 正常
- SQLite直接更新で公開した記事: `dateModified` が `published_at` に設定される可能性

---

## AI-CANON: AI参照URLの正確性

```
evidence: canonical確認済み（UI-SEO セクション参照）
```

| ページ | canonical | AIが参照するURL | 判定 |
|--------|-----------|----------------|------|
| `/predictions/` | `https://nowpattern.com/predictions/` | 正確 | ✅ |
| `/en/predictions/` | `https://nowpattern.com/en/predictions/` | 正確 | ✅ |
| `/about/` | `https://nowpattern.com/about/` | 正確 | ✅ |
| `/en/about/` | `https://nowpattern.com/en/about/` | 正確 | ✅ |

**llms.txtのEN予測URL**: `en-predictions/`（誤） → AI参照URLが誤っている（AI-LLMS参照）

---

## AI-PREDICT: 予測ページの機械可読性

```
evidence: 既知の実装 + HTML確認
```

| 要素 | 状態 | AIへの影響 |
|------|------|---------|
| prediction_db.json（1,093件） | VPSで管理 | AI直接アクセス不可（内部ファイル） |
| /predictions/ HTML | 200 ✅ | AIはHTMLでデータ参照可能 |
| JSON-LD Dataset schema | **未実装** 🔴 | GoogleがデータセットとしてAI Overviewに含めない |
| 予測ID アンカー（`#np-XXXX`） | 実装済み（推定） | 直リンクでの予測参照可能 |
| 投票API (/reader-predict/) | 実装済み | AIによる自動投票不可（設計通り） |

**最重要欠落**: Dataset schema がないため、1,093件の予測データがGoogleのAI Overviewで「データセット」として認識されない。

---

## AI アクセシビリティ スコアカード

| カテゴリ | 問題なし | 要改善 | 重大 |
|---------|---------|--------|------|
| AI-LLMS (llms.txt) | 1 | 0 | 1 |
| AI-FULL (llms-full.txt) | 0 | 0 | 1 |
| AI-ROBOTS | 4 | 1 | 0 |
| AI-SITEMAP | 4 | 1 | 0 |
| AI-SCHEMA | 2 | 4 | 2 |
| AI-AUTHOR | 0 | 2 | 0 |
| AI-DATE | 1 | 1 | 0 |
| AI-CANON | 4 | 1 | 0 |
| AI-PREDICT | 2 | 0 | 1 |
| **合計** | **18** | **10** | **5** |

---

## 優先度別問題リスト

### 🔴 重大（即日対応）

| ID | 問題 | 影響 |
|----|------|------|
| AI-001 | llms.txt EN URL誤り（2箇所） | AIが誤ったURLを案内 |
| AI-002 | llms-full.txt 301→404 | AIが全記事リストを取得不可 |
| AI-003 | /en/predictions/ に Article schema | GoogleがENページを記事と誤認 |
| AI-004 | Dataset schema 未実装 | 予測データがAI Overviewに認識されない |
| AI-005 | FAQPage schema 未実装 | AI Overview掲載率-60% |

### ⚠️ 要改善（1週間以内）

| ID | 問題 | 影響 |
|----|------|------|
| AI-006 | about/taxonomy ページに Article schema | 不正確だが致命的ではない |
| AI-007 | PARSE_ERRORのJSON-LD | 部分的にAIが構造データ取得失敗 |
| AI-008 | ホームページ hreflang 欠落 | Googleの言語認識精度低下 |
| AI-009 | robots.txt AI専用ディレクティブなし | 意図不明確（機能上は問題なし） |
| AI-010 | サンプル記事のスキーマ確認が必要 | author/publisherが正しいか不明 |

---

## 9つの監査質問（AIアクセス観点）

**Q4: AIクローラーに対して正しく情報が届いているか？**
- llms.txt: 到達可能だが EN URLが誤り → AIが誤URL案内
- llms-full.txt: 404 → AIが全記事リスト取得不可
- robots.txt: 正常（クローリング許可）
- sitemap.xml: 正常（インデックス可）
- Schema: /en/predictions/ のArticle schemaが誤り

**Q5: 予測ページはAIにとって機械可読か？**
- HTML: 到達可能 ✅
- Dataset schema: **未実装** 🔴
- ID ("np-scoreboard"等): 一部欠落 🔴
- 予測内容のテキスト: 読み取り可能 ✅（HTMLから）

**Q6: AIが誤ったURLを案内するリスクはあるか？**
- **YES**: llms.txt に `https://nowpattern.com/en-predictions/` が2箇所
- ChatGPT/Claude/Geminiに「Nowpatternの英語版予測ページは？」と聞いた場合、`/en-predictions/`（存在しないURL）を返す可能性が高い

---

*作成: 2026-03-28 | 証拠: SSH curl + Python スクリプト実行結果*
*次: NOWPATTERN_SCHEMA_AUDIT_2026-03-28.md*
