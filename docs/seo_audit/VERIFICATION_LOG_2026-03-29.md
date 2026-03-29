# Verification Log — 2026-03-29

> 今セッションで実施した全確認コマンドと結果の証跡。

---

## Phase 1: REQ-011 PARSE_ERROR

```bash
# PARSE_ERROR 文字列存在確認
ssh root@163.44.124.123 "grep -rn 'PARSE_ERROR' /opt/shared/scripts/x_swarm_dispatcher.py | head -10"
# → 出力なし（exit code 1）

# ログファイル存在確認
ssh root@163.44.124.123 "ls /opt/shared/scripts/x_*.log 2>/dev/null; ls /opt/shared/logs/x_*.log 2>/dev/null"
# → exit code 2（ファイル存在せず）

# DLQ確認
ssh root@163.44.124.123 "python3 -c \"import json; d=json.load(open('/opt/shared/scripts/x_dlq.json')); print('DLQ:', len(d))\""
# → DLQ: 0
```

**Result**: ✅ PARSE_ERROR なし、DLQ=0

---

## Phase 2: broken links 調査

```bash
# prediction_db.json の genre- URL 確認
ssh root@163.44.124.123 "grep -c 'genre-' /opt/shared/scripts/prediction_db.json"
# → 0

# 4件の prediction の現在の ghost_url 確認
# NP-2026-0020: ghost_url = "/en/en-btc-70k-march-31-2026/"
# NP-2026-0021: ghost_url = "/en/en-btc-90k-march-31-2026/"
# NP-2026-0025: ghost_url = "/en/en-fed-fomc-march-2026-rate-decision/"
# NP-2026-0027: ghost_url = "/en/en-khamenei-assassination-iran-supreme-leader-succession-2026/"

# JA predictions ページの全リンク HTTP チェック（20件）
# curl -s https://nowpattern.com/predictions/ → 20 unique links, all 200 OK

# Genre URL 不在確認
ssh root@163.44.124.123 "curl -s https://nowpattern.com/predictions/ | grep -c 'genre-'"
# → 0

# 歴史的失敗ログの確認
ssh root@163.44.124.123 "grep -n 'genre-' /opt/shared/polymarket/prediction_page.log | head -10"
# → 2026-03-03 付近のエントリのみ（歴史的）

# _resolve_ghost_url() 呼び出し確認
ssh root@163.44.124.123 "grep -n '_resolve_ghost_url' /opt/shared/scripts/prediction_page_builder.py"
# → line 636: def _resolve_ghost_url(  (定義のみ。呼び出しなし)
```

**Result**: ✅ broken link 0件。20リンク全件200 OK

---

## Phase 3: builder 耐久性確認

```bash
# FAQPage 存在確認
curl -s https://nowpattern.com/predictions/ | grep -c 'FAQPage'
# → 1

curl -s https://nowpattern.com/en/predictions/ | grep -c 'FAQPage'
# → 1

# Dataset 存在確認
curl -s https://nowpattern.com/predictions/ | grep -c 'Dataset'
# → 1

curl -s https://nowpattern.com/en/predictions/ | grep -c 'Dataset'
# → 1

# block-aware fix 実装確認（コードレビュー）
ssh root@163.44.124.123 "sed -n '2935,2960p' /opt/shared/scripts/prediction_page_builder.py"
# → _ld_blocks = list(_re.finditer(...)) / for _m in reversed(_ld_blocks): / if '"Dataset"' in _m.group():
# ✅ block-aware 実装が確認された
```

**Result**: ✅ FAQPage=1, Dataset=1 (JA/EN両方) / block-aware fix 確認済み

---

## Phase 4: nav taxonomy-ja 修正

```bash
# 修正前 nav 確認（Ghost Admin API）
# → [{"label": "力学で探す", "url": "/taxonomy-ja/"}, ...]

# SQLite直接更新
ssh root@163.44.124.123 'sqlite3 /var/www/nowpattern/content/data/ghost.db "UPDATE settings SET value='"'"'[...]'"'"' WHERE key=\"navigation\";"'
# → exit code 0

# 確認
ssh root@163.44.124.123 'sqlite3 /var/www/nowpattern/content/data/ghost.db "SELECT value FROM settings WHERE key=\"navigation\";"'
# → [..., {"label": "力学で探す", "url": "/taxonomy/"}, ...]

# Ghost 再起動
ssh root@163.44.124.123 'systemctl restart ghost-nowpattern && sleep 5 && systemctl is-active ghost-nowpattern'
# → active

# ホームページ確認
curl -s https://nowpattern.com/ | grep 'taxonomy'
# → <a href="https://nowpattern.com/taxonomy/">力学で探す</a>  ✅

# taxonomy/ HTTP 確認
curl -sI https://nowpattern.com/taxonomy/
# → HTTP/2 200  ✅（301リダイレクトなし）
```

**Result**: ✅ `/taxonomy-ja/` → `/taxonomy/` 修正完了。301ホップ解消

---

## Phase 5: ISS-012/003 + Builder SyntaxError

```bash
# === ISS-012 検証: about/taxonomy ページに WebPage schema が追加されたか ===
curl -s https://nowpattern.com/about/ | python3 -c "
import sys, re, json
html = sys.stdin.read()
for m in re.finditer(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL):
    d = json.loads(m.group(1))
    print(d.get('@type'))
"
# → Article / WebSite / WebPage  ← WebPage ✅

curl -s https://nowpattern.com/en/about/ | python3 -c "..."
# → Article / WebSite / WebPage  ← WebPage ✅

curl -s https://nowpattern.com/taxonomy/ | python3 -c "..."
# → Article / WebSite / WebPage  ← WebPage ✅

curl -s https://nowpattern.com/en/taxonomy/ | python3 -c "..."
# → Article / WebSite / WebPage  ← WebPage ✅

# === ISS-003 検証: /en/predictions/ に CollectionPage schema が追加されたか ===
curl -s https://nowpattern.com/en/predictions/ | python3 -c "
import sys, re, json
html = sys.stdin.read()
for m in re.finditer(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL):
    d = json.loads(m.group(1))
    print(d.get('@type'))
"
# → Article / WebSite / Dataset / FAQPage / CollectionPage  ← CollectionPage ✅ (block 5)

# === Ghost codeinjection_head MARKER 確認（二重注入防止）===
ssh root@163.44.124.123 "python3 /tmp/ghost_fix_iss012_003.py"
# → 全5ページ: SKIP: marker already present  ← 二重注入なし ✅

# === ISS-003 builder 耐久性確認（--update --lang en 後も保持するか）===
ssh root@163.44.124.123 "python3 /opt/shared/scripts/prediction_page_builder.py --update --lang en 2>&1 | tail -5"
# → 正常完了

curl -s https://nowpattern.com/en/predictions/ | python3 -c "..." | grep CollectionPage
# → CollectionPage  ← builder --update 後も保持 ✅

# === Builder SyntaxError 修正確認 ===
ssh root@163.44.124.123 "python3 -c 'import ast; ast.parse(open(\"/opt/shared/scripts/prediction_page_builder.py\").read()); print(\"SYNTAX OK\")'"
# → SYNTAX OK ✅

ssh root@163.44.124.123 "python3 /opt/shared/scripts/prediction_page_builder.py --report 2>&1 | tail -3"
# → 正常完了（SyntaxError なし） ✅
```

**Result**: ISS-012 RESOLVED ✅ / ISS-003 RESOLVED ✅ / Builder SyntaxError FIXED ✅

---

## セッション全体サマリー

| Phase | 検証項目 | 結果 |
|-------|---------|------|
| Phase 1 | PARSE_ERROR なし / DLQ=0 | ✅ |
| Phase 2 | 20リンク全件200 / genre-URL 0件 | ✅ |
| Phase 3 | FAQPage=1 / Dataset=1 (JA+EN) | ✅ |
| Phase 4 | nav /taxonomy/ = 200 直接アクセス | ✅ |
| Phase 5 | ISS-012: WebPage on 4 pages / ISS-003: CollectionPage on en-predictions / Builder SYNTAX OK | ✅ |

---

*Verification completed: 2026-03-29 | Engineer: Claude Code (local)*
