# Track 3: sitemap-news.xml 旧URL修正 — Handoff Document (FINAL)

**実施日**: 2026-03-28
**実施者**: Claude Code (local)
**対象**: nowpattern.com — `b2-news-sitemap.py` URL生成ロジック修正
**最終判定**: **COMPLETED ✅**

---

## 0. Executive Summary

| 項目 | 内容 |
|------|------|
| **Track** | Track 3 — sitemap-news.xml |
| **問題** | sitemap-news.xmlに旧フォーマットURL（`/en-bitutokoin1000mo.../`）が残存 → 2ホップリダイレクトチェーン |
| **真の根本原因** | `b2-news-sitemap.py`（毎時cron）が lang-en 記事でも `/{slug}/` を生成。静的ファイル修正は毎時上書きされる |
| **修正** | `b2-news-sitemap.py` の URL生成ロジックを修正（lang-en → `/en/{slug}/`、en-prefix → redirects.txt参照） |
| **リスク** | 低（スクリプト修正・バックアップあり・完全可逆） |
| **Track 1/2/5 退行** | なし |

---

## 1. 調査で判明した構造

### sitemap-news.xml の正体

```
/var/www/nowpattern-static/sitemap-news.xml = 静的ファイル
  ← 毎時 0 * * * * /usr/bin/python3 /opt/shared/scripts/b2-news-sitemap.py で上書き生成
  ← Caddy: handle /sitemap-news.xml { root * /var/www/nowpattern-static; file_server; }
```

**静的ファイルを直接編集しても毎時上書きされる。修正はスクリプトに施す必要があった。**

### Ghost routes.yaml による URL体系

```yaml
collections:
  /en/:
    permalink: /en/{slug}/
    filter: tag:lang-en    # lang-en 記事 → /en/{slug}/ が正規パーマリンク
  /:
    permalink: /{slug}/
    filter: tag:lang-ja    # lang-ja 記事 → /{slug}/ が正規パーマリンク
```

### 旧フォーマット記事（en- prefix Ghost slug）のリダイレクトチェーン

```
旧フォーマット Ghost slug: en-bitutokoin1000mo-yuan-tu-po-nogou-...
  ↓
b2-news-sitemap.py が生成: https://nowpattern.com/en-bitutokoin1000mo-yuan-tu-po-nogou-.../
  ↓ (2ホップリダイレクト)
Step 1: /en-bitutokoin.../ → Caddy catch-all → Ghost がサービス
Step 2: /en/en-bitutokoin.../ → nowpattern-redirects.txt line 67 → /en/the-structure-behind.../
  ↓
最終正規URL: https://nowpattern.com/en/the-structure-behind-bitcoin-surpassing-10-million/ → 200 OK
```

---

## 2. Track 3/4/6 トリアージ結果

| Track | 問題 | リスク | ROI | 決定 |
|-------|------|--------|-----|------|
| **T3: sitemap-news.xml 旧URL** | lang-en URL全件誤り（`/en/`なし）＋旧prefix1件 | **低** | **高** | **→ 実装済み** |
| T4: custom_excerpt欠落 | 1295/1360件(95%) | 低 | 高 | スコープ過大→NEO委任 |
| T6: ghost_webhook inactive | QA自動化停止 | 低 | SEOなし | スキップ |

---

## 3. 実装内容

### バックアップ

```
/tmp/b2-news-sitemap-bak-20260328-t3fix.py  (VPS tmpに保存)
```

### 変更ファイル

`/opt/shared/scripts/b2-news-sitemap.py` — URL生成ロジックを全面修正

### 変更内容

**変更前（旧ロジック）:**
```python
def generate_sitemap(articles):
    for art in articles:
        slug = art["slug"]
        url = f"{BASE_URL}/{slug}/"  # BUG: lang-en記事も /{slug}/ で生成
```

**変更後（新ロジック）:**
```python
REDIRECT_FILE = "/etc/caddy/nowpattern-redirects.txt"

def load_en_redirect_map(redirect_file=REDIRECT_FILE):
    """Parse redirects.txt: /en/en-{slug}/ -> /en/{canonical}/"""
    redirect_map = {}
    with open(redirect_file, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3 and parts[0] == "redir" and parts[1].startswith("/en/en-"):
                redirect_map[parts[1]] = parts[2]
    return redirect_map

def build_url(art, redirect_map):
    slug = art["slug"]
    if art["lang"] == "en":
        if slug.startswith("en-"):
            # 旧フォーマット: /en/en-{slug}/ -> redirects.txt -> canonical URL
            redirect_key = f"/en/{slug}/"
            if redirect_key in redirect_map:
                return f"{BASE_URL}{redirect_map[redirect_key]}"
            else:
                return f"{BASE_URL}/en/{slug}/"  # fallback
        else:
            # 新フォーマット: Ghost permalink = /en/{slug}/
            return f"{BASE_URL}/en/{slug}/"
    else:
        # JA記事: Ghost permalink = /{slug}/
        return f"{BASE_URL}/{slug}/"

def generate_sitemap(articles):
    redirect_map = load_en_redirect_map()
    seen_urls = set()
    for art in articles:
        url = build_url(art, redirect_map)
        if url in seen_urls:
            continue  # 重複URL除去
        seen_urls.add(url)
        # ... XML生成 ...
```

---

## 4. 検証結果

### Track 3 — sitemap-news.xml 修正確認

| チェック項目 | 結果 |
|------------|------|
| 旧URL（`/en-bitutokoin.../`）がサイトマップから消えた | ✅ |
| EN記事が全件 `/en/{slug}/` 形式になった | ✅ (14件) |
| JA記事が `/{slug}/` 形式のまま | ✅ (7件) |
| 重複URL除去が機能（dedup: 1件スキップ） | ✅ |
| サイトマップ loc件数: 21件（重複除去後） | ✅ |
| `en-` prefix URL残存なし | ✅ 0件 |
| EN URL 3件 HTTP 200確認 | ✅ 全件 200 |
| 毎時cron継続動作（`0 * * * *`） | ✅ |

### Track 1 — hreflang退行なし

| チェック項目 | 結果 |
|------------|------|
| lang_ja posts | 229 (delta=0 from baseline) ✅ |
| lang_en posts | 1131 (delta=0 from baseline) ✅ |

### Track 2 — noindex退行なし

| URL | x-robots-tag | 期待値 |
|-----|-------------|--------|
| `/en/tag/geopolitics/` | `noindex, follow` | ✅ |
| `/tag/lang-ja/` | `noindex, follow` | ✅ Guard 1 intact |

### Track 5 — cron退行なし

```
0 22 * * * prediction_page_builder.py (JA)
30 22 * * * prediction_page_builder.py (EN)
0 23 * * * d5-cwv-monitor.py  ← T5-FIX 2026-03-28 (23:00 UTC confirmed)
0 * * * * b2-news-sitemap.py  ← T3-FIX 毎時動作中
```

---

## 5. ロールバック手順

```bash
# 方法1: バックアップから復元
ssh root@163.44.124.123
cp /tmp/b2-news-sitemap-bak-20260328-t3fix.py /opt/shared/scripts/b2-news-sitemap.py
python3 /opt/shared/scripts/b2-news-sitemap.py
# 確認
curl -s https://nowpattern.com/sitemap-news.xml | grep 'en-bitutokoin' | wc -l

# 方法2: git revert (スクリプトがgit管理下の場合)
ssh root@163.44.124.123
cd /opt/shared && git log scripts/b2-news-sitemap.py
```

---

## 6. 今後の優先アクション

### NOW（完了）
- [x] `b2-news-sitemap.py` の URL生成ロジック修正
- [x] バックアップ作成
- [x] 手動実行・ライブ確認（HTTP 200）
- [x] Track 1/2/5 退行チェック: PASS

### 今日 (TODAY)
1. **Search Consoleでsitemap-news.xmlをURL検査**
   - Google Search Consoleにアクセス → URL検査 → `https://nowpattern.com/sitemap-news.xml`
   - 「Googleにインデックスをリクエスト」を実行（任意）

### 今週 (THIS WEEK)
2. **Track 4: custom_excerpt欠落（1295/1360件）の対処方針を決定**
   - CTRへの影響大（Googleがexcerptをmeta descriptionに使用）
   - NEO-ONE/TWOへの委任が望ましい（記事1記事ずつAIで要約生成）
3. **sitemap-news.xmlのsitemap indexへの追加を検討**
   - 現在 sitemap.xml（index）に未掲載（pages/posts/authors/tags の4件のみ）
   - 追加することでGoogle News クロールがより確実になる

---

## 7. 未実施項目と理由

| 項目 | 理由 |
|------|------|
| custom_excerpt 一括追加 | 1295件の内容追加は大規模変更。NEO委任推奨 |
| ghost_webhook_server 再起動 | SEO直接影響なし。別途対処 |
| sitemap-news.xmlをsitemap indexに追加 | Ghostのsitemap.xml再生成が必要。別途対処 |
| en-bitutokoin...旧記事のdraft化 | 2記事が同一公開URLに解決するGhost DB問題。別途NEO委任 |

---

## 8. Ghost DB 状態（参考: 実施後ベースライン）

```json
{
  "lang_ja_posts": 229,
  "lang_en_posts": 1131,
  "total_published": 1360
}
```

`b2-news-sitemap.py` 修正内容: URL生成ロジックのみ変更。記事コンテンツ・Ghost DB・Caddyに一切触れていない。

---

## 9. 最終判定

```
Track 1: CLOSED ✅ (前セッション完了・退行なし: JA=229, EN=1131)
Track 2: COMPLETED ✅ (前セッション完了・退行なし: x-robots-tag全件確認)
Track 5: COMPLETED ✅ (前セッション完了・退行なし: cron 23:00 UTC確認)
Track 3: COMPLETED ✅

実装: b2-news-sitemap.py URL生成ロジック修正
  - lang-en 記事: /en/{slug}/ (Ghost routes.yaml準拠)
  - en- prefix 旧フォーマット: redirects.txt でカノニカルURL参照
  - 重複URL: deduplication で除去
リスク: 低 (バックアップあり、毎時cron継続、完全可逆)
Track 1/2/5 退行: なし (全チェックPASS)
ロールバック: cp 1コマンドで即座に復元可能

SEO効果:
  - sitemap-news.xml の全EN記事が正規 /en/{slug}/ パーマリンクで掲載
  - 旧フォーマットURL（2ホップリダイレクト）を完全排除
  - Google/Bingのクロール効率向上
  - 毎時cronの恒久修正（次回以降も正しく生成）
```

---

*作成: 2026-03-28 | Claude Code (local) | Track 3 b2-news-sitemap.py URL Fix (FINAL)*
