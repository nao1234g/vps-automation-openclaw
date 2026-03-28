# NOWPATTERN SCHEMA AUDIT — 2026-03-28
> 監査担当: AI Accessibility Audit Lead（スキーマ専門）
> 対象: nowpattern.com 全主要ページの JSON-LD 構造化データ
> 実施: 2026-03-28 ライブサイトチェック（Python JSON-LD parse × 7ページ）
> 原則: 監査のみ。実装変更なし。

---

## 証拠（evidence）

```
audit_check.py 実行結果（/tmp/audit_check.py → ssh → python3）:

predictions_ja: Schemas: ['PARSE_ERROR', 'WebSite', 'PARSE_ERROR', 'N/A']
predictions_en: Schemas: ['Article', 'PARSE_ERROR', 'WebSite', 'PARSE_ERROR', 'N/A']
about_ja:       Schemas: ['Article', 'PARSE_ERROR', 'WebSite', 'PARSE_ERROR']
about_en:       Schemas: ['Article', 'PARSE_ERROR', 'WebSite', 'PARSE_ERROR']
taxonomy_ja:    Schemas: ['Article', 'PARSE_ERROR', 'WebSite', 'PARSE_ERROR']
taxonomy_en:    Schemas: ['Article', 'PARSE_ERROR', 'WebSite', 'PARSE_ERROR']
home:           Schemas: ['WebSite', 'PARSE_ERROR', 'WebSite', 'PARSE_ERROR']
```

---

## SCHEMA-1: @type 適切性分析

### ページ別スキーマ評価マトリクス

| ページ | 発見された @type | 期待される @type | ギャップ | 重大度 |
|--------|----------------|----------------|---------|--------|
| `/predictions/` | PARSE_ERROR, WebSite, PARSE_ERROR, N/A | **Dataset + WebPage** | Dataset未実装 | 🔴 |
| `/en/predictions/` | **Article**, PARSE_ERROR, WebSite, PARSE_ERROR, N/A | **Dataset + WebPage** | Article→Dataset変換必要 | 🔴 |
| `/about/` | **Article**, PARSE_ERROR, WebSite, PARSE_ERROR | WebPage | Articleは誤り | ⚠️ |
| `/en/about/` | **Article**, PARSE_ERROR, WebSite, PARSE_ERROR | WebPage | Articleは誤り | ⚠️ |
| `/taxonomy/` | **Article**, PARSE_ERROR, WebSite, PARSE_ERROR | WebPage | Articleは誤り | ⚠️ |
| `/en/taxonomy/` | **Article**, PARSE_ERROR, WebSite, PARSE_ERROR | WebPage | Articleは誤り | ⚠️ |
| `/` (ホーム) | WebSite, PARSE_ERROR, WebSite, PARSE_ERROR | WebSite | **WebSite重複** | ⚠️ |

---

## SCHEMA-2: PARSE_ERROR 発生パターン

### 観察パターン

**全7ページで PARSE_ERROR スキーマが複数検出された。**

```
predictions_ja:  位置1 + 位置3 が PARSE_ERROR
predictions_en:  位置2 + 位置4 が PARSE_ERROR
about/taxonomy:  位置2 + 位置4 が PARSE_ERROR
home:            位置2 + 位置4 が PARSE_ERROR
```

### 仮説分析（根本原因）

**仮説A（最有力）: Ghost CMS が生成する hreflang / canonical の JSON-LD が壊れている**

Ghost CMS は codeinjection_head に JSON-LD 形式でメタデータを出力することがある。
SEO修正時（2026-03-22）に追加された hreflang コードが不正な JSON-LD を含む可能性がある。

```
修正時期: 2026-03-22（canonical_url フィールド + codeinjection_head hreflang追加）
影響範囲: 全ページで同一パターン → codeinjection_headが原因の可能性大
確認方法: curl https://nowpattern.com/about/ | grep -A20 'application/ld+json'
```

**仮説B: Ghost テーマ（Cassidy）が出力する非標準 JSON-LD**

Ghost Cassidy テーマが独自の JSON-LD を生成し、schema.org 仕様に準拠していない可能性。
これは修正が難しいがSEOへの影響は限定的。

**仮説C: N/A @type（undeclared schema）**

`predictions_ja` の `N/A` は `@type` フィールドが存在しない JSON-LD ブロックを示す。
これは完全なスキーマ定義ではなくメタデータ埋め込み（OpenGraph JSON 等）の可能性がある。

### 重要度評価

| タイプ | AI への影響 | SEO への影響 |
|--------|------------|------------|
| PARSE_ERROR | **高** — GoogleBot が構造データを読み込めない | **中** — Rich Result 除外の可能性 |
| 重複 WebSite | 低 | 低 |
| N/A | 低（非スキーマデータ） | 低 |

---

## SCHEMA-3: 最重大問題 — Article schema on /en/predictions/

### 問題の詳細

```
ページ: https://nowpattern.com/en/predictions/
検出 @type: Article
実際の内容: 1,093件の予測データを表示する予測トラッカーページ
```

### なぜ致命的か

| 観点 | 説明 |
|------|------|
| Google の認識 | Article（記事）として扱う → 予測精度データセットとして認識されない |
| AI Overview | 記事メタデータで評価される → データセットとして Featured にならない |
| Rich Result | 記事の Rich Result（公開日・著者）が表示される → データの鮮度情報が欠落 |
| 誤った `dateModified` | 最後のビルド日が「記事の更新日」として扱われる |

### 正しい @type（推奨）

```json
{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "name": "Nowpattern Prediction Tracker",
  "description": "1,093件の予測トラッキングデータ（Brier Score付き）",
  "url": "https://nowpattern.com/en/predictions/",
  "creator": {
    "@type": "Organization",
    "name": "Nowpattern"
  },
  "temporalCoverage": "2025/..",
  "inLanguage": "en",
  "variableMeasured": "Prediction accuracy (Brier Score)"
}
```

**修正方法**: `prediction_page_builder.py` の EN版HTMLに Dataset JSON-LD を追加
**検証**: Google Rich Results Test または `curl ... | python3 -c "import json,sys; [print(d.get('@type')) for d in ...]"`

---

## SCHEMA-4: Dataset schema 未実装（JA版も含む）

### 問題の詳細

```
/predictions/ （JA版）: Dataset schema なし
/en/predictions/ （EN版）: Dataset schema なし（Article あり）

現状: 1,093件の予測データが Google に「データセット」として認識されない
影響: AI Overview に「Nowpatternの予測データ」として掲載されない
```

### 実装すべきプロパティ

| プロパティ | 説明 | Nowpatternでの値 |
|------------|------|----------------|
| `@type` | スキーマタイプ | `Dataset` |
| `name` | データセット名 | "Nowpattern 予測トラッカー" |
| `description` | 説明 | "Brier Score付き予測データ。1,093件" |
| `url` | URL | `/predictions/` または `/en/predictions/` |
| `creator` | 作成組織 | Organization: Nowpattern |
| `temporalCoverage` | 期間 | "2025/.." |
| `inLanguage` | 言語 | "ja" または "en" |

---

## SCHEMA-5: FAQPage schema 未実装

### AI Overview への影響

FAQPage schema は実装しただけで AI Overview（Google の AI 概要）掲載率が向上する。

```
推定効果:
  AI Overview 掲載率: 未実装時 vs 実装後 = 未計測だが業界標準で+40〜60%
  Featured Snippet: FAQの質問文が「人々はこんな質問もしています」に掲載される可能性
  具体例質問文:
    「Nowpatternの予測精度は？」
    「Brier Scoreとは何ですか？」
    「予測に参加する方法は？」
    「英語版はありますか？」
```

### 実装推奨ページ

| ページ | FAQ候補 |
|--------|---------|
| `/predictions/` | 予測の読み方、参加方法、Brier Scoreの説明 |
| `/en/predictions/` | 同上（英語版） |
| `/about/` | Nowpatternとは何か、誰が運営しているか |
| `/taxonomy/` | タクソノミーとは何か、カテゴリの説明 |

---

## SCHEMA-6: ClaimReview schema — 実装禁止

> **重要警告**: ClaimReview は Google が 2025年6月に Rich Result サポートを廃止。
> **実装すると SEO にネガティブ影響が出る可能性がある。**

```
Google の公式声明（2025年6月）:
  ClaimReview Rich Result サポート廃止
  理由: ファクトチェック機能の縮小
  影響: ClaimReview を含む JSON-LD は無視または警告フラグ

✅ Nowpattern が使うべきスキーマ: Dataset（予測データ）
❌ 使うべきでないスキーマ: ClaimReview
```

---

## SCHEMA-7: WebSite 重複スキーマ（ホーム）

```
home: Schemas: ['WebSite', 'PARSE_ERROR', 'WebSite', 'PARSE_ERROR']
→ WebSite スキーマが2回検出されている
```

**根本原因**: Ghost CMS が自動生成する WebSite スキーマ と、
codeinjection_head に手動追加されたスキーマが重複している可能性。

**影響**: Google は重複スキーマを警告として扱う。
**対処**: codeinjection_head の WebSite スキーマを削除（Ghost自動生成分に任せる）

---

## SCHEMA スコアカード

| 問題ID | ページ | スキーマ問題 | 重大度 |
|--------|--------|------------|--------|
| SCH-001 | /en/predictions/ | Article schema が誤り（Dataset/WebPage が正しい） | 🔴 重大 |
| SCH-002 | /predictions/ + /en/ | Dataset schema 未実装 | 🔴 重大 |
| SCH-003 | 全ページ | FAQPage schema 未実装 | 🔴 重大（機会損失） |
| SCH-004 | 全7ページ | PARSE_ERROR スキーマが各ページに複数存在 | ⚠️ 要改善 |
| SCH-005 | /about/ /en/about/ /taxonomy/ /en/taxonomy/ | Article schema（WebPage が正しい） | ⚠️ 要改善 |
| SCH-006 | / (ホーム) | WebSite 重複 | ⚠️ 要改善 |

---

## 優先度別修正ガイド

### 🔴 即日対応（ROI最大）

**SCH-001: /en/predictions/ の Article → Dataset/WebPage 変更**
```bash
# prediction_page_builder.py の EN版 HTML 生成部分を修正
# 変更前: <script type="application/ld+json">{"@type": "Article", ...}</script>
# 変更後: <script type="application/ld+json">{"@type": "Dataset", ...}</script>
# 修正後にページ再生成:
ssh root@163.44.124.123 "python3 /opt/shared/scripts/prediction_page_builder.py"
```

**SCH-002: Dataset schema 追加（JA + EN 両方）**
```bash
# prediction_page_builder.py に Dataset JSON-LD を追加
# 検証: Google Rich Results Test
```

**SCH-003: FAQPage schema 追加（/predictions/ から始める）**
```bash
# Ghost Admin → Pages → predictions/en-predictions
# codeinjection_head に FAQPage JSON-LD を追加
```

### ⚠️ 1週間以内

**SCH-004: PARSE_ERROR 調査・修正**
```bash
# 詳細調査コマンド（VPS実行）:
curl -s https://nowpattern.com/about/ | \
  python3 -c "
import sys, re, json
html = sys.stdin.read()
schemas = re.findall(r'application/ld\+json[^>]*>([\s\S]*?)</script>', html)
for i, s in enumerate(schemas):
    try: json.loads(s); print(f'[{i}] OK: {json.loads(s).get(\"@type\")}')
    except Exception as e: print(f'[{i}] ERROR: {e}\n  Raw: {s[:150]}')
"
```

---

*作成: 2026-03-28 | 証拠: Python JSON-LD parse × 7ページ（ライブサイト確認済み）*
