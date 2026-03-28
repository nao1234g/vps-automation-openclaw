# EN記事スラッグ在庫レポート（Slug Inventory Report）

> 生成日: 2026-03-28 | 担当: LEFT_EXECUTOR
> 証跡: Ghost SQLite DB直接クエリ + slug_repair2.py実行結果

---

## サマリー

| 指標 | 数値 |
|------|------|
| EN published記事総数 | 1,130件 |
| クリーンスラッグ（en-プレフィックスなし） | **680件**（60.2%） |
| en-プレフィックス残存 | **450件**（39.8%） |
| 今回修正件数（ピンイン→英語） | **189件** |
| 修正失敗件数 | 0件 |

---

## 640件初期見積り vs 190件実検出の差分説明

### 経緯

| フェーズ | 数値 | 内容 |
|---------|------|------|
| **修正前** | 640件 | en-プレフィックス付き記事の総数（初期視認見積り） |
| **is_bad_slug() 判定** | 190件 | 実際に「悪い」（ピンイン/判読不能）と判定されたもの |
| **修正後** | 450件 | en-プレフィックスが残存する記事 |

### 640 = 450 + 190 の検証

```
修正後en-prefix残存: 450件
+ slug_repair2.py修正分: 189件（report） + 1件（事前テスト） = 190件
= 640件（修正前の総en-prefix数）  ← 初期見積りと一致 ✅
```

### is_bad_slug()の判定基準

`slug_repair2.py`の`is_bad_slug()`関数は以下の条件で「修正要」と判定:
1. `guan-ce-rogu-`プレフィックス → **常に悪い**（ゼロ件残存）
2. `en-`プレフィックス かつ タイトルとのトークン重複率 **< 30%** → 悪い

450件の残存記事は`en-`プレフィックスを持つが、英語ワードの重複率が30%以上あるため「悪い」と判定されなかった。これらは段階的対応の対象（Phase 2）。

---

## スラッグ状態別内訳

```sql
-- 実行クエリ（Ghost SQLite, 2026-03-28 確認）
SELECT
  CASE WHEN p.slug LIKE 'en-%' THEN 'en-prefix'
       WHEN p.slug LIKE 'guan-ce-rogu-%' THEN 'guan-ce-rogu'
       ELSE 'clean' END as status,
  COUNT(*) as cnt
FROM posts p
JOIN posts_tags pt ON p.id=pt.post_id
JOIN tags t ON pt.tag_id=t.id
WHERE t.slug='lang-en' AND p.status='published' AND p.type='post'
GROUP BY 1
```

| 状態 | 件数 | 説明 |
|------|------|------|
| `clean`（en-プレフィックスなし） | 680 | 正常。Google推奨URL形式 |
| `en-prefix`（en-付き・英語含む） | 450 | 英語コンテンツあり。Phase 2対象 |
| `guan-ce-rogu`（純ピンイン） | 0 | 全件修正済み ✅ |
| **合計** | **1,130** | |

---

## 修正完了証跡

### slug_repair_report.json

```
/opt/shared/reports/slug_repair_report.json
  generated_at: 2026-03-28T01:04:32.885677+00:00
  total_repaired: 189
  total_failed: 0
```

### 修正サンプル（上位3件）

| 旧スラッグ（ピンイン） | 新スラッグ（英語） |
|----------------------|------------------|
| `en-denmakuzong-xuan-ju-nochong-ji-...` | `the-shock-of-the-danish-general-election-the-collapse-of` |
| `en-gaza-ping-he-ping-yi-hui-guo-lian-...` | `gaza-peace-council-first-un-report` |
| `en-nan-sinahai-nomi-zhong-jun-shi-...` | `us-china-military-standoff-in-the-south-china` |

### HTTPステータス確認

| URL | 期待 | 実測 |
|-----|------|------|
| `/en/en-denmakuzong-...` (旧) | 301 | **301** ✅ |
| `/en/en-bitutokoin1500mo-...` (旧) | 301 | **301** ✅ |
| `/en/the-shock-of-the-danish-...` (新) | 200 | **200** ✅ |
| `/en/gaza-peace-council-...` (新) | 200 | **200** ✅ |
| `/en/us-china-military-...` (新) | 200 | **200** ✅ |

---

## 残存課題（Phase 2）

### en-プレフィックス付き450件

これらは英語ワードを含むが`en-`プレフィックスが残存。
現在のURL: `nowpattern.com/en/en-some-english-slug/`（二重の `/en/en-`）
理想のURL: `nowpattern.com/en/some-english-slug/`

**影響**: URLに`/en/en-`が含まれ、`/en/`セクションを示すパスが冗長。
**SEOリスク**: 中程度。現在は301リダイレクトなし（直接アクセス可能なURLのため）。
**対応方針**: Phase 2として別セッションで対応。is_bad_slug()閾値を0%に変更して再実行可能。

### 内部リンク（コンテンツ内旧スラッグ参照）

**2026-03-28 current_run SSHスキャン（SQLite + lexical JSON直接解析）による確定値:**

| 種別 | 件数 | 状態 | evidence_source |
|------|------|------|-----------------|
| **URL link**（`href`/`url`フィールド内の旧スラッグ） | **0件** | ✅ 実際のハイパーリンクなし | current_run |
| **text mention**（本文テキスト内での文字列一致） | **182 docs / 322 occurrences** | クリック不可のテキスト言及。SEO影響なし | current_run |

**⚠️ 差分説明（current_run vs historical_reference）**

| セッション | text mention値 | スキャン手法 |
|-----------|--------------|------------|
| 前セッション（historical_reference） | 41件 | スキャンロジック詳細不明 |
| current_run（このセッションSSH確認） | 182 docs / 322 occurrences | 189件の旧スラッグ全件を1,130 lexical JSONに対して直接照合 |

**共通確定事実（両セッション一致）**: URL link = **0件** ← この事実が対処方針の根拠。text mention件数のズレに関わらず結論は変わらない。

**差分の理由（推定）**: historical_referenceのスキャンロジックは不明。current_runは `slug_repair_report.json` の189件全old_slugを全1,130記事lexical JSONに対して網羅的に走査した。

**注**: 前セッション報告の「59件」は別スコープ（全言語・全タグ）での概算値。

**対処不要の理由**: text mentionはHTMLとして`<a href>`を持たない。読者がクリックしても旧URLへのナビゲーションは発生しない。301リダイレクトが必要なアクティブリンクは**ゼロ**（URL link=0 は current_run で確認済み）。

---

## Publisher修正状況（新規記事への再発防止）

| 確認項目 | 結果 |
|---------|------|
| `_title_to_en_slug()` 関数存在 | ✅ line 385 |
| `_pub_slug`変数でEN記事にのみ適用 | ✅ line 838 |
| `post_to_ghost(slug=_pub_slug)` | ✅ line 849 |
| syntax check | ✅ OK |
| 最新記事スラッグ確認（top 10） | ✅ 全件en-プレフィックスなし |

---

*生成: 2026-03-28 | LEFT_EXECUTOR | 証跡: Ghost SQLite + curl確認済み*
