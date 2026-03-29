# NOWPATTERN LINK FIX PROPOSALS — 2026-03-28
> 担当: Link Quality Engineer
> 依拠: HOMEPAGE_LINK_AUDIT / SITEWIDE_URL_AUDIT / CLICKPATH_REVIEW / HUMAN_UX_REVIEW (全4監査ドキュメント)
> 原則: 実装はしない。修正提案と実装手順書のみ。
> 実装前確認: CLAUDE.md「実装前に理解を確認する」原則に従い、実装セッションで改めて確認すること。

---

## 凡例

| 記号 | 意味 |
|------|------|
| 🔴 P1 | 重大（即日対応） |
| 🟠 P2 | 高優先度（1週間以内） |
| 🟡 P3 | 中優先度（2週間以内） |
| 🟢 P4 | 低優先度（任意） |
| CF | Caddyfile修正（`/etc/caddy/nowpattern-redirects.txt`） |
| GA | Ghost Admin修正（GUI操作） |
| PB | prediction_page_builder.py修正（VPSスクリプト） |
| NA | 作業なし（確認のみ） |

---

## FIX-001 — フッター「タクソノミーガイド」誤リダイレクト修正

| 項目 | 内容 |
|------|------|
| 優先度 | 🔴 P1 |
| 種別 | CF（Caddyfile 1行修正） |
| 影響範囲 | 全ページフッター（JA） |
| 難易度 | 極低（1分） |
| 効果 | 高（CP-07回遊率 0/10 → 10/10） |

### 問題の根本原因

```
# /etc/caddy/nowpattern-redirects.txt 現在の設定（誤り）
redir /taxonomy-guide-ja/ /taxonomy/ permanent    ← ❌ 誤: /taxonomy/ ではなく /taxonomy-guide/ が正解
```

フッター全ページのナビゲーションが `https://nowpattern.com/taxonomy-guide-ja/` にリンクしている。
このURLは `/taxonomy/` にリダイレクトされるが、ユーザーは「ガイド」を期待して「検索ページ」に着地する。

### 修正手順

```bash
# Step 1: バックアップ作成
ssh root@163.44.124.123 "cp /etc/caddy/nowpattern-redirects.txt /etc/caddy/nowpattern-redirects.txt.bak-$(date +%Y%m%d-%H%M)"

# Step 2: 1行修正
ssh root@163.44.124.123 "sed -i 's|redir /taxonomy-guide-ja/ /taxonomy/ permanent|redir /taxonomy-guide-ja/ /taxonomy-guide/ permanent|' /etc/caddy/nowpattern-redirects.txt"

# Step 3: 修正確認
ssh root@163.44.124.123 "grep taxonomy-guide-ja /etc/caddy/nowpattern-redirects.txt"
# 期待出力: redir /taxonomy-guide-ja/ /taxonomy-guide/ permanent

# Step 4: Caddy リロード
ssh root@163.44.124.123 "systemctl reload caddy"

# Step 5: 検証
curl -o /dev/null -w "%{redirect_url}\n" -s https://nowpattern.com/taxonomy-guide-ja/
# 期待出力: https://nowpattern.com/taxonomy-guide/
```

### 追加推奨（根本解決）

Ghost Admin でフッターナビゲーションのリンクを `/taxonomy-guide-ja/` → `/taxonomy-guide/` に変更することで、301を経由しない直接リンクになる。ただしCaddyfileの修正だけでも機能は回復する。

### ロールバック

```bash
ssh root@163.44.124.123 "cp /etc/caddy/nowpattern-redirects.txt.bak-$(date +%Y%m%d)* /etc/caddy/nowpattern-redirects.txt && systemctl reload caddy"
```

---

## FIX-002 — ホームページ404記事リンクの修正

| 項目 | 内容 |
|------|------|
| 優先度 | 🔴 P1 |
| 種別 | GA（Ghost Admin確認 + 対応） |
| 影響範囲 | ホームページ記事リスト1件 |
| 難易度 | 低（5〜10分） |
| 効果 | 中（ホームページの信頼性回復） |

### 問題の根本原因

ホームページに表示されている記事#4「南シナ海の米中軍事対峙 — 対立の螺旋が偶発衝突リスクをワープ...」のリンクが404を返す。

**確認済み404 URL**:
```
/nan-sinahai-nomi-zhong-jun-shi-dui-zhi-dui-li-noluo-xuan-gaou-fa-chong-tu-risukuwolin-jie-dian-heya-sishi-ang-gerugou-zao/
```

Ghost DBに同スラッグは存在しない。同トピック（南シナ海）の記事は4件別スラッグで存在する。
Ghost CMSのホームページ表示はフィーチャー設定またはタグフィルターに依存するため、このリンクは旧記事の残留か、スラッグ変更後の取り残し。

### 修正手順

```bash
# Step 1: Ghost DBで南シナ海関連記事を確認
ssh root@163.44.124.123 "sqlite3 /var/www/nowpattern/content/data/ghost.db \"SELECT slug, title, status FROM posts WHERE title LIKE '%南シナ海%' ORDER BY published_at DESC LIMIT 10;\""

# Step 2: 404スラッグが旧記事の移行漏れかどうか確認
ssh root@163.44.124.123 "sqlite3 /var/www/nowpattern/content/data/ghost.db \"SELECT slug, title FROM posts WHERE slug LIKE '%nan-sinahai%';\""

# 対応A: 旧スラッグに301リダイレクト追加（正しい記事URLへ）
#   → redirects.txt に 1行追加: redir /nan-sinahai-nomi-*/  /[正しいslug]/ permanent

# 対応B: Ghost Admin でホームページに表示される記事を差し替え
#   → Ghost Admin → Posts → Featured記事設定を変更
```

**注意**: 対応Aの方がSEO的に安全（外部からリンクされている可能性があるため）。

---

## FIX-003 — `id="np-resolved"` セクション復元

| 項目 | 内容 |
|------|------|
| 優先度 | 🔴 P1 |
| 種別 | PB（prediction_page_builder.py修正） |
| 影響範囲 | /predictions/ と /en/predictions/ 両方 |
| 難易度 | 中（30〜60分） |
| 効果 | 高（解決済み予測の可視性回復 + アンカーリンク復元） |

### 問題の根本原因

ISSUE_MATRIX ISS-007 は「RESOLVED」と記録されているが、**ライブサイト確認でid="np-resolved"が現在も存在しない**ことを確認。

```bash
# 現在の状態確認（実証済み）
curl -s https://nowpattern.com/predictions/ | grep 'id="np-resolved"'
# → 出力なし（存在しない）

# 現在存在するID一覧
curl -s https://nowpattern.com/predictions/ | grep -oE 'id="np-[^"]*"'
# → id="np-tracking-list", id="np-search", id="np-pagination", id="np-cta-ja", id="np-cta-en"
```

解決済み予測（17件）を表示するセクションとそのIDが欠落しているため、Oracle Statement内の `nowpattern.com/predictions/#np-resolved` リンクが全て機能しない。

### 修正手順

```bash
# Step 1: バックアップ
ssh root@163.44.124.123 "cp /opt/shared/scripts/prediction_page_builder.py /opt/shared/scripts/prediction_page_builder.py.bak-fix003-$(date +%Y%m%d-%H%M)"

# Step 2: np-resolved セクション生成コードを確認・追加
ssh root@163.44.124.123 "grep -n 'np-resolved\|np-tracking-list\|resolved_html\|build_resolved' /opt/shared/scripts/prediction_page_builder.py | head -30"

# Step 3: 解決済み予測の件数確認
ssh root@163.44.124.123 "python3 -c \"import json; db=json.load(open('/opt/shared/scripts/prediction_db.json')); resolved=[p for p in db['predictions'] if p.get('status')=='resolved']; print(f'Resolved: {len(resolved)}件')\""

# Step 4: prediction_page_builder.py で解決済みセクションの生成ロジックを確認
# → resolved_predictionsリストが exists するか、generate_resolved_section() がcolls outputに含まれているか
# → `id="np-resolved"` が HTML output に書き出されているか

# Step 5: 修正後再生成
ssh root@163.44.124.123 "python3 /opt/shared/scripts/prediction_page_builder.py"

# Step 6: 検証
curl -s https://nowpattern.com/predictions/ | grep 'id="np-resolved"'
# 期待出力: <div id="np-resolved" ...>
```

**予測デザインシステム遵守**: `np-resolved` IDは `prediction-design-system.md` の凍結ベースラインに定義されている。セクション順序は「追跡中 → スコアボード → 解決済み」を維持すること。

---

## FIX-004 — EN Nav JS の /en-predictions/ → /en/predictions/ 修正

| 項目 | 内容 |
|------|------|
| 優先度 | 🟠 P2 |
| 種別 | PB or GA（EN予測ページのcodeinjection_head修正） |
| 影響範囲 | /en/predictions/ と他ENページのナビゲーション |
| 難易度 | 低（10分） |
| 効果 | 高（不要301消去 + EN UX改善） |

### 問題の根本原因

EN版ナビゲーションのJavaScriptオーバーライドが古いリダイレクトURLを参照している。

```javascript
// 現在の設定（/en/predictions/ ページ内インラインスクリプト）
var pred = document.querySelector('.nav-yu-ce-toratuka a');
if (pred) pred.setAttribute('href', 'https://nowpattern.com/en-predictions/');
//                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
//                                    これは /en/predictions/ に301リダイレクト → 不要な301
```

### 修正手順

```bash
# Step 1: EN版 予測ページ（en-predictions）のcodeinjection_head確認
ssh root@163.44.124.123 "sqlite3 /var/www/nowpattern/content/data/ghost.db \"SELECT codeinjection_head FROM posts WHERE slug='en-predictions';\" | head -50"

# Step 2: /en-predictions/ を /en/predictions/ に変更
# Ghost Admin → Pages → /en/predictions/ → Code Injection → Header
# または SQLite直接更新:
ssh root@163.44.124.123 "sqlite3 /var/www/nowpattern/content/data/ghost.db \"UPDATE posts SET codeinjection_head=REPLACE(codeinjection_head, 'nowpattern.com/en-predictions/', 'nowpattern.com/en/predictions/') WHERE slug='en-predictions';\""

# Step 3: 他のENページ（taxonomy、about等）も同様に確認・修正
ssh root@163.44.124.123 "sqlite3 /var/www/nowpattern/content/data/ghost.db \"SELECT slug, INSTR(codeinjection_head, 'en-predictions/') as has_old FROM posts WHERE slug LIKE 'en-%' AND INSTR(codeinjection_head, 'en-predictions/') > 0;\""

# Step 4: Ghost 再起動（必須）
ssh root@163.44.124.123 "systemctl restart ghost-nowpattern"

# Step 5: 検証
curl -s https://nowpattern.com/en/predictions/ | grep 'en-predictions'
# 期待出力: 0件（古いURLが消えている）
```

---

## FIX-005 — Nav「力学で探す」直リンク修正

| 項目 | 内容 |
|------|------|
| 優先度 | 🟡 P3 |
| 種別 | GA（Ghost Admin ナビゲーション設定） |
| 影響範囲 | 全ページナビゲーション |
| 難易度 | 低（5分） |
| 効果 | 低（301を1件削減） |

### 問題の根本原因

Ghost Admin のナビゲーション設定で「力学で探す」リンクが `/taxonomy-ja/` になっている。
このURLは `/taxonomy/` に301リダイレクトされるが、直接 `/taxonomy/` にリンクすべき。

### 修正手順

```
Ghost Admin → Settings → Navigation →
「力学で探す」のURL: /taxonomy-ja/ → /taxonomy/ に変更して保存
```

```bash
# 検証
curl -o /dev/null -w "%{http_code}\n" -s https://nowpattern.com/taxonomy/
# 期待出力: 200
```

---

## FIX-006 — EN article リンクの /en/en- プレフィックス修正

| 項目 | 内容 |
|------|------|
| 優先度 | 🟡 P3 |
| 種別 | PB（prediction_page_builder.py URL生成ロジック） |
| 影響範囲 | /en/predictions/ 内のEN記事リンク |
| 難易度 | 中（30分） |
| 効果 | 中（P3だが301が4件削減、UX改善） |

### 問題の根本原因

/en/predictions/ ページ内の記事リンクが `/en/en-[slug]/` になっている。
正しくは `/en/[slug]/`（`en-` プレフィックスは Ghost 内部スラッグ名であり、公開URLには含まれない）。

```
現在: /en/en-btc-70k-march-31-2026/ → 301 → /en/will-bitcoin-exceed-70000-by/
正しい: /en/will-bitcoin-exceed-70000-by/ → 200（直接）
```

### 修正手順

```bash
# Step 1: prediction_page_builder.py の EN記事URL生成部分を確認
ssh root@163.44.124.123 "grep -n 'en/en-\|/en-\|en_slug\|en_url\|article_url' /opt/shared/scripts/prediction_page_builder.py | head -30"

# Step 2: prediction_db.json の EN記事URLフィールドを確認
ssh root@163.44.124.123 "python3 -c \"
import json
db = json.load(open('/opt/shared/scripts/prediction_db.json'))
for p in db['predictions'][:5]:
    if p.get('article_url_en'):
        print(p['prediction_id'], p['article_url_en'])
\""

# Step 3: URL生成ロジックを修正（en-[slug] → EN URLはGhost APIのURLフィールドから取得するよう変更）
# 具体的な修正箇所は Step 1 の grep 結果を参照

# Step 4: 再生成・検証
ssh root@163.44.124.123 "python3 /opt/shared/scripts/prediction_page_builder.py"
curl -s https://nowpattern.com/en/predictions/ | grep '/en/en-' | wc -l
# 期待出力: 0
```

---

## FIX-007 — フッターリンク拡充

| 項目 | 内容 |
|------|------|
| 優先度 | 🟡 P3 |
| 種別 | GA（Ghost Admin フッターナビゲーション） |
| 影響範囲 | 全ページフッター |
| 難易度 | 低（10分） |
| 効果 | 中（フッタースコア 2/10 → 7/10） |

### 追加すべきリンク（推奨）

| テキスト | リンク先 |
|---------|---------|
| X @nowpattern | https://x.com/nowpattern |
| Subscribe（無料） | #/portal/signup |
| 予測トラッカー | /predictions/ |
| Taxonomy Guide | /taxonomy-guide/ |

### 修正手順

```
Ghost Admin → Settings → Secondary Navigation（フッター）→
以下を追加:
  X @nowpattern → https://x.com/nowpattern
  Subscribe → #/portal/signup
  予測を見る → /predictions/
（タクソノミーガイドは FIX-001 適用後に動作確認してから追加）
```

---

## FIX-008 — ホームページHero価値提案テキスト追加

| 項目 | 内容 |
|------|------|
| 優先度 | 🟡 P3 |
| 種別 | GA（Ghost Admin ホームページ or Theme設定） |
| 影響範囲 | ホームページ（JA + EN） |
| 難易度 | 低〜中（テーマ変更の場合は高） |
| 効果 | 中（3秒テスト 6/10 → 8/10） |

### 問題

Heroセクション最上部のSubscribeボタンより前に、サービスの価値提案テキストがない。
初見ユーザーが「何のサイトか」を理解する前に購読を求められている。

### 修正案

```html
<!-- Hero上部に挿入するテキスト案 -->
<p class="site-tagline">
  予測精度を公開する、世界初のバイリンガル予測プラットフォーム
</p>
```

**EN版**:
```html
<p class="site-tagline">
  The world's first bilingual prediction platform with a public track record.
</p>
```

**実装方法**: Ghost Theme の `default.hbs` か `home.hbs` を修正するか、ホームページのcodeinjection_headでCSS+HTMLを注入。

---

## FIX-009 — 「タクソノミー」ラベルを直感的に変更

| 項目 | 内容 |
|------|------|
| 優先度 | 🟢 P4 |
| 種別 | GA（Ghost Admin ナビゲーション） |
| 影響範囲 | ナビゲーション + /taxonomy/ ページタイトル |
| 難易度 | 低 |
| 効果 | 低（認知負荷の軽微な改善） |

### 変更案

| 現在 | 提案 |
|------|------|
| 力学で探す（ナビ） | テーマで探す |
| タクソノミー（ページ内ラベル） | ジャンル・テーマで探す |

---

## 修正サマリー

| FIX-ID | 優先度 | 種別 | 難易度 | 修正時間 | 効果 | 依存関係 |
|--------|--------|------|--------|---------|------|---------|
| FIX-001 | 🔴 P1 | CF | 極低（1分） | 5分 | 高 | なし |
| FIX-002 | 🔴 P1 | GA | 低（10分） | 15分 | 中 | なし |
| FIX-003 | 🔴 P1 | PB | 中（60分） | 60分 | 高 | なし |
| FIX-004 | 🟠 P2 | PB/GA | 低（10分） | 15分 | 高 | なし |
| FIX-005 | 🟡 P3 | GA | 低（5分） | 5分 | 低 | なし |
| FIX-006 | 🟡 P3 | PB | 中（30分） | 45分 | 中 | なし |
| FIX-007 | 🟡 P3 | GA | 低（10分） | 10分 | 中 | FIX-001 |
| FIX-008 | 🟡 P3 | GA/Theme | 低〜中 | 30分 | 中 | なし |
| FIX-009 | 🟢 P4 | GA | 低（5分） | 5分 | 低 | なし |

**合計推定作業時間（P1〜P2のみ）**: 95分

---

## ISS-007 ステータス訂正

> **重要**: NOWPATTERN_ISSUE_MATRIX_2026-03-28.md の ISS-007 は `✅ RESOLVED` と記録されているが、
> 2026-03-28 ライブサイト確認で `id="np-resolved"` が **現在も存在しない**ことが確認された。
> ISSUE_MATRIX の ISS-007 ステータスを `RESOLVED` → `OPEN` に訂正が必要。

```bash
# 確認コマンド（任意）
curl -s https://nowpattern.com/predictions/ | grep 'id="np-resolved"'
# 期待: 0件（存在しない）
```

---

*作成: 2026-03-28 | 情報源: Round 3 監査ドキュメント4件 + VPS SSH確認済み*
*FIX-001〜003 は P1 として即日実施推奨*
