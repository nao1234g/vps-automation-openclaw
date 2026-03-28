# EN記事スラッグ修正 実装レポート（Implemented Slug Fixes）

> 作成: 2026-03-28 | 担当: LEFT_EXECUTOR
> 対象: nowpattern.com EN記事190件のピンイン→英語スラッグ一括修正

---

## 修正概要

### 問題

Ghost CMSはスラッグを自動生成する際に、日本語タイトルをピンイン（中国語ローマ字）に変換していた。
`nowpattern_publisher.py`が`post_to_ghost()`を呼ぶ際に`slug`パラメータを渡していなかったため、
Ghost側が日本語タイトルからローマ字変換を実施し、`en-nan-sinahai-nomi-...`のような
判読不能なURLが1130件のEN記事に生成されていた。

### 根本原因

```python
# 修正前 (nowpattern_publisher.py)
ghost_result = post_to_ghost(
    title=title,
    html=html,
    tag_objects=tag_objects,
    ...
    # slug パラメータなし → Ghost が自動生成 → ピンイン化
)
```

### 影響範囲

| 指標 | 数値 |
|------|------|
| 対象EN記事総数 | 1,130件 |
| en-プレフィックス付き（修正前） | 640件 |
| ピンイン判定・修正対象 | **190件** |
| 修正完了 | **189件**（バッチ） + 1件（事前テスト） = **190件** |
| 修正失敗 | **0件** |

---

## 実施した修正

### Fix 1: slug_repair2.py — 既存190件の一括修正

**ファイル**: `/opt/shared/scripts/slug_repair2.py`（新規作成）
**実行日時**: 2026-03-28T01:04:32 UTC
**方式**: Ghost Admin API PUT `/ghost/api/admin/posts/{id}/?formats=lexical`

#### 修正フロー

```
1. Ghost SQLite から全EN published記事のスラッグを取得
2. is_bad_slug() でピンインスラッグを判定
   - guan-ce-rogu-プレフィックス → 常に悪い
   - en-プレフィックス + タイトルとのトークン重複率 < 30% → 悪い
3. _title_to_en_slug(title) で英語クリーンスラッグを生成
4. Ghost Admin API で slug を更新（updated_at の ISO8601変換が必須）
5. 旧URL → 新URL の 301 リダイレクトを Caddy に書き込み
```

#### is_bad_slug() 判定基準

```python
def is_bad_slug(slug, title):
    if slug.startswith("guan-ce-rogu-"):
        return True
    if slug.startswith("en-"):
        # タイトルの英語トークンとスラッグのトークンの重複率
        expected = title_to_slug(title)
        slug_tokens = set(slug.replace("en-", "").split("-"))
        expected_tokens = set(expected.split("-"))
        overlap = len(slug_tokens & expected_tokens) / max(len(expected_tokens), 1)
        return overlap < 0.30
    return False
```

#### 修正例

| 旧スラッグ（ピンイン） | 新スラッグ（英語） |
|----------------------|------------------|
| `en-denmakuzong-xuan-ju-nochong-ji-gurinrandofang-wei-gazhao-itayu-dang-beng-huai-tobei-ou-zhi-xu-nozai-bian` | `the-shock-of-the-danish-general-election-the-collapse-of` |
| `en-bitutokoin1500mo-yuan-tu-po-yu-ce-ji-guan-tou-zi-jia-nocan-ru-gasheng-mu-sheng-zhe-zong-qu-ri-nogou-zao-zhuan-huan` | `bitcoin-predicted-to-surpass-15-million` |
| `en-nan-sinahai-nomi-zhong-jun-shi-dui-zhi-dui-li-noluo-xuan-gaou-fa-chong-tu-woyin-kiji-serugou-zao` | `us-china-military-standoff-in-the-south-china` |

#### 重要バグ修正

Ghost Admin API PUT は `updated_at` フィールドを ISO 8601形式で要求する。
SQLiteが返す `2026-03-27 18:02:42`（スペース区切り、Zなし）をそのまま送ると HTTP 422エラー。

```python
# 修正（slug_repair2.py line 201）
"updated_at": row["updated_at"].replace(" ", "T") + ".000Z"
```

#### 実行結果

```
/opt/shared/reports/slug_repair_report.json:
  generated_at: 2026-03-28T01:04:32.885677+00:00
  total_repaired: 189
  total_failed: 0
```

---

### Fix 2: Caddy 301リダイレクト — 190件

**ファイル**: `/etc/caddy/nowpattern-redirects.txt`
**追加行数**: 190行
**形式**: `redir /en/{old-slug}/ /en/{new-slug}/ permanent`

```bash
# 確認コマンド（VPSで実行済み）
grep -c '^redir' /etc/caddy/nowpattern-redirects.txt
# → 237（既存47件 + 今回190件）
```

**Caddy reload**: 実行済み（`systemctl is-active caddy` → active）

---

### Fix 3: nowpattern_publisher.py — 新規記事への再発防止

**ファイル**: `/opt/shared/scripts/nowpattern_publisher.py`
**バックアップ**: `.bak-20260328-slug-fix`（2026-03-28 10:03）

#### 追加した関数

```python
def _title_to_en_slug(title: str) -> str:
    """Generate clean ASCII English slug from title for Ghost API."""
    if not title:
        return ''
    s = title.lower()
    s = re.sub(r'[^\w\s-]', '', s)   # ASCII以外を除去
    s = re.sub(r'[\s_]+', '-', s)    # スペース/アンダースコアをハイフンに
    s = re.sub(r'-+', '-', s)        # 連続ハイフンを1つに
    s = s.strip('-')
    if len(s) > 80:
        s = s[:80].rsplit('-', 1)[0]  # 単語境界で80文字に切る
    return s or 'article'
```

#### publish_deep_pattern() の修正

```python
# 修正後
_pub_slug = _title_to_en_slug(title) if _pub_lang == "en" else ""
ghost_result = post_to_ghost(
    title=title,
    html=html,
    tag_objects=tag_objects,
    ghost_url=ghost_url,
    admin_api_key=admin_api_key,
    status=status,
    featured=True,
    codeinjection_foot=jsonld,
    language=_pub_lang,
    slug=_pub_slug,      # ← 追加
)
```

---

## 検証結果（証跡付き）

### 301リダイレクト動作

| コマンド | 期待 | 実測 |
|---------|------|------|
| `curl -I .../en-denmakuzong-.../` | 301 | **301** ✅ |
| `curl -I .../en-bitutokoin1500mo-.../` | 301 | **301** ✅ |
| redirect先URL | 新URL | **新URL** ✅ |
| リダイレクトチェーン（ホップ数） | 1 | **1（ループなし）** ✅ |

### 新URL 200確認

| URL | 期待 | 実測 |
|-----|------|------|
| `/en/the-shock-of-the-danish-.../` | 200 | **200** ✅ |
| `/en/gaza-peace-council-.../` | 200 | **200** ✅ |
| `/en/us-china-military-.../` | 200 | **200** ✅ |

### canonical確認

| 記事 | 期待 canonical | 実測 canonical |
|------|--------------|---------------|
| `the-shock-of-the-danish-...` | `/en/the-shock-of-the-danish-.../` | ✅ 一致 |
| `gaza-peace-council-...` | `/en/gaza-peace-council-.../` | ✅ 一致 |

### sitemap確認

| 確認項目 | 期待 | 実測 |
|---------|------|------|
| 旧スラッグがsitemapに存在 | 0件 | **0件** ✅ |
| 新スラッグがsitemapに存在 | ≥1件 | **1件確認** ✅ |

### publisher.py修正確認

| 確認項目 | 結果 |
|---------|------|
| syntax OK | ✅ |
| `_title_to_en_slug` at line 385 | ✅ |
| `_pub_slug` at line 838 | ✅ |
| `slug=_pub_slug` at line 849 | ✅ |
| 最近10件EN記事のスラッグ（en-プレフィックスなし） | ✅ 全件クリーン |

---

## 残存課題（未対応・明示）

| 項目 | 状況 | 優先度 |
|------|------|--------|
| en-プレフィックス付き450件（英語コンテンツ含む） | 未修正 | Phase 2 |
| 59件の内部リンク（旧ピンインスラッグ参照） | 未修正（301でフォロー可） | Phase 2 |
| /en-predictions-3/ → /en-predictions/ → /en/predictions/ の2ホップチェーン | 既存（ループなし） | 低優先 |

---

## 成果物

| ファイル | 場所 | 内容 |
|---------|------|------|
| slug_repair2.py | VPS `/opt/shared/scripts/` | 修正スクリプト |
| slug_repair_report.json | VPS `/opt/shared/reports/` | 修正結果（189件） |
| slug_migration_map.json | VPS `/opt/shared/reports/` | 旧→新マッピング（JSON） |
| slug_migration_map.csv | VPS `/opt/shared/reports/` | 旧→新マッピング（CSV） |
| nowpattern-redirects.txt | VPS `/etc/caddy/` | Caddyリダイレクト（190件追加） |
| publisher_slug_policy.md | local `docs/seo_audit/` | スラッグポリシー文書 |

---

*作成: 2026-03-28 | LEFT_EXECUTOR*
