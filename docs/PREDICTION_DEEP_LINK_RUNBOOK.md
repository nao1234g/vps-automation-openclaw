# Prediction Deep Link — 運用ランブック

> 作成日: 2026-03-28
> 対象: nowpattern.com の `/predictions/#np-XXXX` アンカーリンクシステム
> 詳細な修正経緯: `docs/PREDICTION_DEEP_LINK_FIX_REPORT.md`

---

## システム概要

記事末尾の Oracle Statement（予測ボックス）にあるリンクが、
`/predictions/` ページの特定予測カードへ直接アンカーで飛ぶ仕組み。

```
読者クリック: https://nowpattern.com/predictions/#np-2026-0042
  ↓
/predictions/ ページ読み込み
  ↓
JS: window.location.hash を検出 → <details id="np-2026-0042"> を自動展開 + スクロール
```

---

## アンカーID規則（変更禁止）

| ルール | 例 |
|--------|----|
| DBの `prediction_id` を **小文字** に変換 | `NP-2026-0042` → `np-2026-0042` |
| `<details id="np-2026-0042">` 形式 | ページHTML側 |
| `href="https://nowpattern.com/predictions/#np-2026-0042"` | 記事CTA側 |

**⚠️ 大文字(`#NP-`)は必ず失敗する。必ず lowercase を使うこと。**

---

## 日常チェック — 素早い健全性確認

```bash
# 1. lint を手動実行（bare oracle CTAが0件か確認）
ssh root@163.44.124.123 "python3 /opt/shared/scripts/lint_prediction_links.py"
# → OK: "Bare oracle CTAs found: 0"

# 2. /predictions/ ライブページのアンカー数を確認
ssh root@163.44.124.123 "python3 /tmp/ws3_final.py"
# → dq（ダブルクォート形式）アンカーが 21 件以上あること（2026-03-29以降の新形式）
# ⚠️ sq（シングルクォート）は日次で変動する（予測の追加・解決による）。dq=21 が安定しているかが回帰なしの指標。

# 3. lintクーロンのログを確認
ssh root@163.44.124.123 "tail -20 /opt/shared/logs/lint_oracle_cta.log"
```

---

## ケース別対処手順

### Case 1: lint で bare oracle CTAが検出された

**症状:** Telegramに「⚠️ [REGRESSION] Oracle CTA 未アンカーリンク検出」アラートが届く

**対処手順:**

```bash
# 1. どの記事が対象か確認
ssh root@163.44.124.123 "python3 /opt/shared/scripts/lint_prediction_links.py 2>&1 | head -40"

# 2. マイグレーションスクリプトで一括修正
ssh root@163.44.124.123 "python3 /opt/shared/scripts/migrate_prediction_links.py --dry-run"
# → AFFECTED: X records (dry-run)

# 3. 問題なければ実際に実行
ssh root@163.44.124.123 "python3 /opt/shared/scripts/migrate_prediction_links.py"

# 4. 再度 lint で確認
ssh root@163.44.124.123 "python3 /opt/shared/scripts/lint_prediction_links.py"
```

**根本原因候補:**
- 新しい記事に古いテンプレート（アンカーなし）が使われた
- NEO が Oracle Statement を古い形式で書いた
- `nowpattern_article_builder.py` の `track_url` が変更された

---

### Case 2: /predictions/ のアンカー数が突然減った

**症状:** `lint_prediction_links.py` はPASSだが、アンカー数が前回より大幅に減少

**対処手順:**

```bash
# 1. アンカー数を確認
ssh root@163.44.124.123 "python3 -c \"
import urllib.request, ssl, re, json
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request('https://nowpattern.com/predictions/', headers={'User-Agent':'curl'})
with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
    html = r.read().decode()
ids_sq = re.findall(r\\\"id='(np-2026-[^']+)'\\\", html)
ids_dq = re.findall(r'id=\\\"(np-2026-[^\\\"]+)\\\"', html)
print('Anchors:', len(set(ids_sq+ids_dq)))
\""

# 2. prediction_page_builder.py を手動で再実行
ssh root@163.44.124.123 "python3 /opt/shared/scripts/prediction_page_builder.py --lang ja --force"

# 3. 再カウント
# → 200+ になればOK
```

**根本原因候補:**
- `prediction_db.json` のデータが減った
- `prediction_page_builder.py` のビルドロジックが変更された
- Ghost CMS の lexical フィールドが手動で上書きされた

---

### Case 3: ブラウザで `#np-2026-XXXX` が動作しない

**症状:** ブラウザで `/predictions/#np-2026-0042` を開いても予測カードに飛ばない

**チェックリスト:**

1. **アンカーが存在するか確認:**
   ```bash
   # HTML内にそのIDが存在するか
   ssh root@163.44.124.123 "python3 -c \"
   import urllib.request, ssl
   ctx = ssl.create_default_context()
   ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
   req = urllib.request.Request('https://nowpattern.com/predictions/', headers={'User-Agent':'curl'})
   with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
       html = r.read().decode()
   target = \\\"id='np-2026-0042'\\\"  # ← 確認したいID
   print('FOUND' if target in html or target.replace(\\\"'\\\", '\\\"') in html else 'NOT FOUND')
   \""
   ```

2. **大文字/小文字を確認:** 必ず `np-` (小文字) で始まること

3. **JS がページに存在するか:**
   ```bash
   ssh root@163.44.124.123 "grep -c 'window.location.hash' /opt/shared/scripts/prediction_page_builder.py"
   # → 1 以上
   ```

4. **Ghost DB を確認:**
   ```bash
   ssh root@163.44.124.123 "python3 -c \"
   import sqlite3, json, re
   con = sqlite3.connect('/var/www/nowpattern/content/data/ghost.db')
   lex = json.loads(con.execute(\\\"SELECT lexical FROM posts WHERE slug='predictions'\\\").fetchone()[0])
   html = lex['root']['children'][0]['html']
   print('Hash JS in DB:', 'window.location.hash' in html)
   \""
   ```

---

### Case 4: 新しい予測を追加した後

新しい予測を `prediction_db.json` に追加したら:

```bash
# /predictions/ ページを再ビルド（日次cronが07:00 JSTに自動実行するが、即時反映したい場合）
ssh root@163.44.124.123 "python3 /opt/shared/scripts/prediction_page_builder.py --lang ja --force && python3 /opt/shared/scripts/prediction_page_builder.py --lang en --force"

# 新しい予測のアンカーが追加されたか確認
ssh root@163.44.124.123 "python3 -c \"
import urllib.request, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request('https://nowpattern.com/predictions/', headers={'User-Agent':'curl'})
with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
    html = r.read().decode()
print('FOUND' if 'id=\\'np-2026-XXXX\\'' in html else 'NOT FOUND')  # XXXXを実際のIDに置換
\""
```

---

### Case 5: Oracle Guardian カード（赤いエラーカード）

Oracle Guardian カードは `prediction_db.json` に必須フィールドが不足している予測に表示される赤いカード。
これらも `/predictions/#np-XXXX` アンカーを持つ（本セッションで修正済み）。

```bash
# Oracle Guardian カードのアンカーを確認
ssh root@163.44.124.123 "python3 -c \"
import urllib.request, ssl, re
ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request('https://nowpattern.com/predictions/', headers={'User-Agent':'curl'})
with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
    html = r.read().decode()
# OGカードのid検索（境界色 #EF4444 が特徴）
og_ids = re.findall(r\"id='(np-[^']+)' style=.?border:2px solid #EF4444\", html)
og_ids += re.findall(r'id=\"(np-[^\"]+)\" style=.?border:2px solid #EF4444', html)
print('Oracle Guardian anchors:', len(og_ids))
print(og_ids)
\""
# → 15程度が正常
```

Oracle Guardian カードが大量に増えた場合 → `prediction_db.json` のデータ品質確認が必要。

---

## 重要ファイル一覧

| ファイル | 役割 |
|----------|------|
| `/opt/shared/scripts/prediction_page_builder.py` | /predictions/ ページ生成。anchor IDを生成する |
| `/opt/shared/scripts/migrate_prediction_links.py` | 記事リンクの一括マイグレーション |
| `/opt/shared/scripts/lint_prediction_links.py` (v5) | JA oracle CTAのlintチェック |
| `/opt/shared/scripts/lint_oracle_cta_cron.py` | 週次lintラッパー（Telegram通知付き） |
| `/opt/shared/scripts/nowpattern_article_builder.py` | 新規記事生成（line 1145 に future guard） |
| `/opt/shared/logs/lint_oracle_cta.log` | 週次lintログ |

---

## バックアップ

| パス | 内容 |
|------|------|
| `/opt/shared/scripts/prediction_page_builder.py.bak-20260328-anchors` | Workstream C適用前 |
| `/opt/shared/scripts/prediction_page_builder.py.bak-20260328-og-anchor` | Oracle Guardian修正前 |
| `/opt/shared/scripts/prediction_page_builder.py.bak-errorcard-20260329` | Oracle Guardian id再適用前（2026-03-29 WS4 再パッチ） |

---

## 設計判断メモ

**なぜ小文字に統一するか:**
HTMLのid属性はcase-sensitiveなため、`NP-2026-0042` と `np-2026-0042` は別のIDとして扱われる。
DBの `prediction_id` は大文字（`NP-`）なので、コード側で必ず `.lower()` してIDを生成する。

**なぜEN汎用CTAはlintしないか:**
EN記事には「View all predictions」「→ 全予測を見る」などの汎用ナビゲーションリンクがあり、
これらは `/en/predictions/` にアンカーなしでリンクしており、それは正常。
Oracle CTAとは異なる意味なので、lint v5はJA oracle CTA（`予測に参加`等）のみをチェックする。

---

*作成: 2026-03-28 | Claude Code (claude-sonnet-4-6)*
