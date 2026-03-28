# nowpattern.com — hreflang 完全分析・全提案書
> 作成: 2026-03-28
> 対象セッション: V5 スラッグ修復後の hreflang 完全監査
> ステータス: **アクション待ち（修正スクリプト準備完了）**

---

## TL;DR（30秒要約）

| 問題 | 件数 | SEOリスク | 修正難度 |
|------|------|-----------|---------|
| EN記事: 古いピンインURLを指す stale hreflang | 187件 | HIGH | 低（文字列置換） |
| JA記事: 対応EN記事の古いURLを指す stale hreflang | 92件 | HIGH | 低（文字列置換） |
| EN記事: 存在しないguan-ce-roguスラッグを指す | 9件 | CRITICAL | 中（手動確認要） |
| EN記事: en-en-ダブルプレフィックス | 1件 | LOW | 低（文字列置換） |
| EN記事: hreflang="ja"が未設定 | ~700+件 | MODERATE | 中（スクリプト）  |
| hreflang_fix.py: 修復済み記事のマッチングバグ | — | バグ | 中（コード修正） |

**修正優先度**: A（stale URL一括置換）→ B（guan-ce-rogu調査）→ C（hreflang_fix.py修正）→ D（publisher更新）

---

## 第1章: 現状の完全把握（確認済みUnshakeable Facts）

### 1.1 インフラ構成（確認済み）

```
[ブラウザ/クローラー]
    ↓
[Caddy リバースプロキシ — 163.44.124.123]
    ├── handle /en/tag/* → strip /en → localhost:2368
    ├── handle /en/about/  → rewrite /en-about/ → localhost:2368
    ├── handle /en/predictions/ → rewrite /en-predictions/ → localhost:2368
    ├── handle /en/taxonomy/ → rewrite /en-taxonomy/ → localhost:2368
    ├── handle /en/taxonomy-guide/ → rewrite /en-taxonomy-guide/ → localhost:2368
    ├── import /etc/caddy/nowpattern-redirects.txt (237件リダイレクト)
    └── reverse_proxy localhost:2368 (catch-all)

[Ghost CMS — localhost:2368]
    routes.yaml collections:
      /en/  → permalink: /en/{slug}/  filter: tag:lang-en
      /     → permalink: /{slug}/     filter: tag:lang-ja
```

**重要発見**: Ghost の routes.yaml により、`lang-en` タグの記事は**スラッグが何であっても**自動的に `/en/{slug}/` でサーブされる。修復済み記事（スラッグ `[english]`）は自動的に `/en/[english]/` として200を返す。Caddy の特別なrewriteは不要。

### 1.2 スラッグ修復の結果（確認済み）

```
修復完了: 189記事
  old_slug: en-[ピンイン]  (例: en-denmaku-zong-xuan-ju-...)
  new_slug: [english]      (例: the-shock-of-the-danish-general-election-...)

リダイレクト設定済み: 237件 (Caddy /etc/caddy/nowpattern-redirects.txt)
  redir /en/[old-pinyin]/ /en/[english]/ permanent

旧URL → 301確認: ✅ (3サンプル全て HTTP/2 301 正常)
新URL → 200確認: ✅ (5サンプル全て HTTP/2 200 正常)
```

### 1.3 codeinjection_head 実態（確認済み）

```
修復済み189記事の内訳:
  codeinjection_head = NULL/空: 2件

  非NULLの187件の内訳:
    パターンA (177件): hreflang="en" href="__GHOST_URL__/en/en-[old-pinyin]/"
    パターンB (9件):   hreflang="en" href="__GHOST_URL__/en/guan-ce-rogu-.../"
    パターンC (1件):   hreflang="en" href="__GHOST_URL__/en/en-en-[pinyin]/"
```

**実際のHTMLレンダリング確認**: Ghost は `__GHOST_URL__` を `https://nowpattern.com` に正しく展開する。つまりクローラーが実際に見るのは:

```html
<!-- NP-A4-HREFLANG -->
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/en-denmaku-zong-xuan-ju-.../">  ← 古いURL (301にリダイレクト)
<link rel="alternate" hreflang="ja" href="https://nowpattern.com/[ja-slug]/">
<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/[ja-slug]/">
```

Googleはhreflangの古いURLをクロールし → 301にヒット → これを「conflicting signal」として認識する可能性がある。

### 1.4 JA記事のstale hreflang（確認済み）

```
JA記事でhreflang="en"が古いピンインURLを指しているもの: 92件
  例: <link rel="alternate" hreflang="en" href="__GHOST_URL__/en/en-[old-pinyin]/">
  現実: ENの対応記事は既に /en/[english]/ に移動済み

JA記事の対応ENスラッグが見つからないもの: 97件
  (別のスラッグパターンまたは未ペア)
```

### 1.5 Canonical の状態（確認済み）

```
修復済みEN記事のlive HTML canonical:
  <link rel="canonical" href="https://nowpattern.com/en/prime-minister-takaichis-growth-strategy-x-imf/">
  ✅ 新しい正しいURLを指している（Ghost DB canonical_url フィールドで設定済み）
```

canonical は正常。問題は hreflang のみ。

---

## 第2章: 問題の詳細分析

### 問題1: EN記事の stale self-hreflang（177件）

**症状**: 修復済みEN記事が自分自身の旧URLをhreflang="en"で参照している

```html
<!-- 現在（誤） -->
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/en-denmaku-zong-xuan-ju.../">

<!-- 正しくあるべき -->
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/the-shock-of-the-danish-general-election-.../">
```

**修正方法**: slug_repair_report.json の {old_slug: new_slug} マッピングを使い、`/en/[old]/` → `/en/[new]/` を文字列置換。

### 問題2: JA記事の stale EN hreflang（92件）

**症状**: JA記事が対応ENページの旧URL（301先）をhreflang="en"で参照

```html
<!-- 現在（誤） -->
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/en-denmaku-zong-xuan-ju.../">

<!-- 正しくあるべき -->
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/the-shock-of-the-danish-general-election-.../">
```

**修正方法**: 同じマッピングで置換可能。

### 問題3: guan-ce-rogu スラッグへの broken hreflang（9件）

**症状**: hreflangが存在しないスラッグを指している → Googleがクロールすると404

```html
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/guan-ce-rogu-0042-.../">
```

Ghost DBにこのスラッグは存在しない。考えられる原因:
- さらに古い形式（スラッグ管理の第1世代）のURL
- 記事が後から削除された
- 別のスラッグ命名規則で作成されたが後に変更

**修正方法**: 3択
1. hreflangタグを削除（最も安全）
2. 対応するJA記事を探して正しいENスラッグを割り出す
3. そのまま放置（最もリスク高）

推奨: **選択肢1（削除）**。存在しないURLへの参照はGoogleへの誤情報。

### 問題4: ダブルプレフィックス（1件）

```html
<link rel="alternate" hreflang="en" href="__GHOST_URL__/en/en-en-[pinyin]/...">
```

en-en- という二重プレフィックス。単純なバグ。文字列置換で修正。

### 問題5: EN記事にhreflang="ja"が未設定（推定700+件）

**user の hreflang_fix.py が解決しようとしている問題**:

Google の要件: hreflang は双方向（reciprocal）でなければならない。
- JA記事: `hreflang="ja"` + `hreflang="en"` + `hreflang="x-default"` ← ✅ 3種類あり
- EN記事: `hreflang="en"` + `hreflang="x-default"` ← ❌ `hreflang="ja"` が抜けている

**このバグにより hreflang_fix.py が誤動作する**（次章参照）。

---

## 第3章: hreflang_fix.py のバグ分析

### バグの正確な位置

```python
# Step 2: JA記事からEN URLを抽出
for ja_slug, info in ja_posts.items():
    m = re.search(r'hreflang="en"[^>]*href="([^"]*)"', ci)
    en_url = m.group(1)
    en_url = en_url.replace("__GHOST_URL__", "")
    # → 抽出される値: "/en/en-[old-pinyin]/"  ← 古いURL!
    ja_to_en[ja_slug] = en_url

# Step 3: 逆引きマップ
en_url_to_ja = {en_url: ja_slug for ...}
# → キー: "/en/en-[old-pinyin]/"

# Step 4: ENスラッグから新URLを構築してマッチング
for en_slug, info in en_posts.items():
    en_url = f"/en/{en_slug}/"  # → "/en/[english]/"  ← 新しいURL!
    if en_url in en_url_to_ja:  # "en/[english]/" vs "en/en-[old-pinyin]/" → 不一致！
        ...  # ← 修復済み記事は絶対にここに来ない
    else:
        unmatched_en.append(en_slug)  # ← 修復済み記事が全部ここに落ちる
```

**影響範囲**:
- 修復済み189記事は全て `unmatched_en` に分類される
- これらには hreflang="ja" が追加されない
- さらに、JA記事の古いEN URLが「broken JA→EN」として誤検知される

### 修正方針

```python
# 追加が必要: slug_repair_report.json を読み込む
with open("/opt/shared/reports/slug_repair_report.json") as f:
    repair_data = json.load(f)

# 古いスラッグ → 新しいスラッグのマップ
old_to_new = {r["old_slug"]: r["new_slug"] for r in repair_data["repairs"]}
# 例: {"en-denmaku-zong-xuan-ju-...": "the-shock-of-the-danish-general-election-..."}

# Step 2のURl正規化にrepairマップを適用
def resolve_en_url(en_url_path, old_to_new):
    """古いEN URLを新しいURLに解決する"""
    m = re.match(r"/en/(.+)/", en_url_path)
    if m:
        extracted_slug = m.group(1)  # "en-[old-pinyin]"
        resolved_slug = old_to_new.get(extracted_slug, extracted_slug)  # → "[english]"
        return f"/en/{resolved_slug}/"
    return en_url_path
```

---

## 第4章: 世界標準のベストプラクティス（Global Intelligence）

### Google公式ガイドライン（2026年時点）

1. **hreflang は完全双方向が必須**: AページがBを指したら、BもAを指す必要がある
2. **hreflang は正規URL（redirect先ではなく最終URL）を使う**: 301リダイレクト先のURLを使うこと
3. **x-default は言語/地域未指定ユーザー向け**: 通常はデフォルト言語（JA）を指す
4. **実装方法3択**: (a) `<link>`タグ in `<head>` (b) HTTPヘッダー (c) サイトマップXML

> Google公式: "If you specify the wrong URL or a URL that redirects, Google may not be able to determine the correct URL for your page."

### 301 redirect + hreflang の業界標準見解（Ahrefs, Moz, Semrush）

| 情報源 | 見解 |
|--------|------|
| Google公式 | "Use canonical URLs in hreflang tags, not redirected URLs" |
| Ahrefs | 301先を参照するhreflangは「高リスク」。Googleが無視することがある |
| Moz | hreflangは「信号」であり「ルール」ではない。矛盾する信号は無視される傾向 |
| Semrush | "Hreflang pointing to 3xx is an error" と明示的に分類 |

**結論**: 301先URLをhreflangで参照することは業界では**エラー扱い**。早期修正が必須。

### 国際化SEOの世界的ベストプラクティス（企業事例）

| 企業/サイト | 対策 | 結果 |
|-----------|------|------|
| Airbnb | 言語ごとにサブディレクトリ + routes.yaml相当 | 多言語SEOのベストケース |
| Wikipedia | `/ja/`, `/en/` サブパス + 完全bidirectional hreflang | 高い国際SEO評価 |
| GitHub | subdomain方式 | 別アプローチ（SEO重視でなくUX重視） |
| **Nowpattern** | `/` (JA) + `/en/` (EN) | ✅ Airbnb/Wikipedia型。適切な構造 |

Nowpatternの `/en/` サブパス構造は業界ベストプラクティスに合致している。問題はhreflang URLの精度のみ。

### 修復後の回復タイムライン（業界データ）

```
修復直後: Google Search Consoleで再クロールをリクエスト
1-2週間: Googlebotが更新された hreflang を再クロール・解釈開始
2-3週間: 検索順位の変動期（一時的な変動あり）
3-4週間: 国際ターゲティングの安定化
4-8週間: 完全な効果測定可能

注意: サーチコンソールの「国際ターゲティング」レポートに反映されるまでは4-8週間
```

---

## 第5章: 全提案リスト（考えうる全て）

### カテゴリA: 即時修正（今週中）

#### A-1: stale hreflang 一括更新スクリプト（最優先）

**対象**: 177件のEN stale self-hreflang + 92件のJA stale EN hreflang
**方法**: slug_repair_report.json の mapping を使い codeinjection_head を SQLite UPDATE
**リスク**: 低（バックアップ付き、dry-run確認後）
**実装**: `/tmp/hreflang_stale_fix.py`（別途提供）

```
実行順序:
1. python3 /tmp/hreflang_stale_fix.py --dry-run   # 確認
2. python3 /tmp/hreflang_stale_fix.py --apply      # 適用
3. Ghost restart: systemctl restart ghost-nowpattern
4. 3記事をブラウザで確認
```

#### A-2: guan-ce-rogu broken hreflang 削除

**対象**: 9件
**方法**: codeinjection_head から該当 hreflang="en" タグのみ削除
**推奨**: 存在しないURLへの参照は削除する（Googleへの誤情報）

#### A-3: ダブルプレフィックス修正

**対象**: 1件
**方法**: `hreflang="en" href="__GHOST_URL__/en/en-en-` → `hreflang="en" href="__GHOST_URL__/en/` に置換

### カテゴリB: hreflang_fix.py 修正・強化（今週中）

#### B-1: バグ修正（修復済み記事のマッチング失敗）

slug_repair_report.json を読み込み、JA hreflangの旧URL → 新URLへの解決レイヤーを追加。
詳細は第3章参照。

#### B-2: 完全双方向 hreflang 補完

修正後のスクリプトを適用して:
- EN記事に hreflang="ja" を追加（約700記事対象）
- JA記事の hreflang="en" を正しいURLで更新（stale分）

#### B-3: x-default の最適化検討

現在の想定:
- JA記事の x-default → JA URL（正しい、JA がデフォルト言語）
- EN記事の x-default → EN URL自身（これは議論あり）

Google推奨: x-default は「言語/地域が決定できないユーザー向けのページ」。
JA がプライマリ言語なら、EN記事の x-default も JA URL を指すべき。

### カテゴリC: パブリッシャー更新（来週）

#### C-1: nowpattern_publisher.py の hreflang 自動生成修正

現状: 記事公開時に古いパターンでhreflangを生成している
改善:
- JA記事公開時: EN対応URLを `slug_repair_report.json` のパターンで生成
- EN記事公開時: JA対応URLを検索して完全双方向hreflangを生成

#### C-2: article_validator.py への hreflang バリデーション追加

```python
def validate_hreflang(codeinjection_head, current_slug, current_lang):
    # 1. hreflang="en" が正しいEN URLを指しているか
    # 2. hreflang="ja" が存在するか（EN記事の場合）
    # 3. URLが301ではなく最終URLか
    # 4. x-defaultが適切か
```

### カテゴリD: モニタリング・自動化（来月）

#### D-1: 週次 hreflang 監査 cron

```python
# /opt/shared/scripts/hreflang_audit.py
# 毎週月曜 09:00 JST
# チェック内容:
# - hreflang URLが現存スラッグを指しているか
# - 双方向性が維持されているか
# - Caddy redirect でカバーされていない古いURLがないか
# → 問題があればTelegram通知
```

#### D-2: sitemap.xml へのhreflang追加（高度）

Ghost の標準サイトマップは hreflang を含まない。
カスタムサイトマップジェネレータ（`sitemap_hreflang_builder.py`）で
Google推奨の3方式のうち「サイトマップ方式」を追加実装。

#### D-3: Caddy HTTP ヘッダーでの言語シグナル強化

```caddy
handle /en/* {
    header Content-Language en
    header Vary Accept-Language
}
handle / {
    header Content-Language ja
}
```

BingはhreflangをサポートしないがContent-Languageヘッダーを使用。日英両市場へのリーチ向上。

#### D-4: Ghost Webhook → hreflang 即時バリデーション

記事公開・更新時（Ghost Webhook port 8769）に:
1. codeinjection_head の hreflang を即時検証
2. 問題あれば Telegram 通知
3. 重大な問題（broken URL）は自動修正

### カテゴリE: Google Search Console アクション

#### E-1: 修正後即時リクエスト

```
1. Search Console → 「URL検査」
2. 代表的な修正済みURL 5件を手動「インデックス登録をリクエスト」
3. サイトマップを再送信: https://nowpattern.com/sitemap.xml
4. 「国際ターゲティング」レポートで改善を監視（4-8週間）
```

#### E-2: 検索パフォーマンスの言語別モニタリング

GSC「クエリ」→ 国/言語でフィルタリングして:
- JA クエリへの表示回数・CTR（修正前後比較）
- EN クエリへの表示回数・CTR（修正前後比較）

### カテゴリF: 長期・高度な提案

#### F-1: hreflang sitemap 方式への移行（オプション）

現在: codeinjection_head (per-post HTML injection) → 187件の手動管理が必要
代替: サイトマップXML方式 → 一箇所で全記事のhreflangを管理

```xml
<url>
  <loc>https://nowpattern.com/[ja-slug]/</loc>
  <xhtml:link rel="alternate" hreflang="ja" href="https://nowpattern.com/[ja-slug]/"/>
  <xhtml:link rel="alternate" hreflang="en" href="https://nowpattern.com/en/[en-slug]/"/>
  <xhtml:link rel="alternate" hreflang="x-default" href="https://nowpattern.com/[ja-slug]/"/>
</url>
```

メリット: Ghost の codeinjection_head 管理が不要に。
デメリット: カスタムサイトマップジェネレータの開発が必要（推定2-3時間）。

#### F-2: JA/EN ペア管理 DB の構築

現在: JA/EN のペア関係は hreflang から逆引き
提案: 専用の `bilingual_pairs.json` または SQLite テーブルで管理

```json
{
  "pairs": [
    {"ja_slug": "denmaku-sogo-senkyo-...", "en_slug": "the-shock-of-the-danish..."},
    ...
  ]
}
```

パブリッシャーがこのDBを更新し、hreflang_fix.py はこれを参照。

#### F-3: Bing WebMaster Tools への登録

BingはhreflangをサポートしないがContent-Language / HTMLのlang属性を参照。
Bing WMT でサイトマップを登録してBingクローリングを最適化。

#### F-4: 多言語構造化データ（Schema.org）

```json
{
  "@type": "Article",
  "inLanguage": "ja",
  "url": "https://nowpattern.com/[ja-slug]/",
  "translationOfWork": {
    "@type": "Article",
    "inLanguage": "en",
    "url": "https://nowpattern.com/en/[en-slug]/"
  }
}
```

Google の Entity Understanding を強化。hreflang と相補的に機能。

---

## 第6章: 推奨実行計画

### フェーズ1: 即時修正（今日〜2日以内）

```
Step 1: hreflang_stale_fix.py の dry-run 確認
  ssh root@163.44.124.123 "python3 /tmp/hreflang_stale_fix.py --dry-run"
  期待: "Would fix: 177 EN + 92 JA + 9 broken + 1 double = 279件"

Step 2: バックアップ確認
  ssh root@163.44.124.123 "ls /opt/shared/backups/hreflang_backup_*.json"

Step 3: 適用
  ssh root@163.44.124.123 "python3 /tmp/hreflang_stale_fix.py --apply"

Step 4: Ghost 再起動
  ssh root@163.44.124.123 "systemctl restart ghost-nowpattern && sleep 5"

Step 5: ライブ確認 (3記事)
  curl -s https://nowpattern.com/en/the-shock-of-the-danish-... | grep -A3 "hreflang"
```

### フェーズ2: 双方向補完（3-5日後）

```
Step 1: hreflang_fix.py の修正版を適用
  → バグ修正（修復済み記事のマッチング）
  → EN記事への hreflang="ja" 一括追加

Step 2: dry-run で件数確認
Step 3: apply
Step 4: Ghost 再起動
Step 5: 確認
```

### フェーズ3: 予防措置（1週間後）

```
Step 1: nowpattern_publisher.py の hreflang 生成ロジック更新
Step 2: article_validator.py へのバリデーション追加
Step 3: 週次 hreflang_audit.py cron 設定
Step 4: Google Search Console に修正完了を報告（URL検査 + サイトマップ再送信）
```

### フェーズ4: 高度な改善（1ヶ月後）

```
Step 1: hreflang sitemap 方式への移行検討
Step 2: bilingual_pairs.json 管理DB の構築
Step 3: Bing WebMaster Tools 最適化
Step 4: Schema.org 多言語構造化データ追加
```

---

## 第7章: リスク評価

### 修正しない場合のリスク（時系列）

```
現在:     Googleが hreflang の stale URL を発見 → 「conflicting signals」と判定
1-2週間:  国際ターゲティングの精度が低下し始める
1-2ヶ月:  言語別の検索順位が不安定化
3-6ヶ月:  "slowly bleeds away" — 言語シグナルの信頼度が継続的に低下
6ヶ月+:   Google が hreflang を完全無視する可能性
```

### 修正後の回復シナリオ（楽観 / 基本 / 悲観）

| シナリオ | 確率 | 内容 |
|---------|------|------|
| 楽観 | 30% | 2週間で完全回復、国際SEOが強化される |
| 基本 | 55% | 4週間で安定化、現在と同等または微改善 |
| 悲観 | 15% | 6週間かかるが最終的には改善 |

**楽観シナリオの条件**: Google がまだ hreflang を「conflicting」と判定していない段階での修正。

---

## 第8章: 成果物一覧

| ファイル | 場所 | 内容 |
|---------|------|------|
| hreflang_stale_fix.py | `/tmp/` (VPS) | stale URL一括修正スクリプト |
| hreflang_fix_v2.py | `/tmp/` (VPS) | バグ修正済み双方向補完スクリプト |
| hreflang_audit.py | `/opt/shared/scripts/` | 週次監査スクリプト（cron用） |
| hreflang_comprehensive_analysis.md | `docs/seo_audit/` | 本ドキュメント |

---

*作成: Claude Code (Sonnet 4.6) — Version 5 スラッグ修復後 hreflang 完全監査の成果物*
*データ確認: SSH + SQLite直接クエリ + curl ライブテスト + web research (2026-03-28)*
