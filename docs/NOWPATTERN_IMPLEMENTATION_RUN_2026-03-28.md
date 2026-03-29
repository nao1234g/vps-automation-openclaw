# NOWPATTERN IMPLEMENTATION RUN — 2026-03-28
> Round 3: 実装セッション。監査特定の修正点を優先順位通りに安全に最小差分で実施。
> 参照元: NOWPATTERN_FIX_PRIORITY_2026-03-28.md
> 証拠: curl 実行結果 + E2E テスト PASS

---

## 実施スコープ

| Issue ID | REQ | タイトル | 結果 |
|----------|-----|---------|------|
| ISS-001, ISS-009 | REQ-001 | llms.txt EN URL 修正（en-predictions/ → en/predictions/） | ✅ DONE |
| ISS-006, ISS-007 | REQ-003 | np-scoreboard / np-resolved ID 追加 + ページ再生成 | ✅ DONE |
| ISS-002 | REQ-004 | llms-full.txt 404 解消（Caddyfile handle block + ファイル作成） | ✅ DONE |
| ISS-011 | REQ-005 | gzip 圧縮有効化（encode zstd gzip） | ✅ DONE |
| ISS-010 | REQ-009 | ホームページ hreflang | ✅ ALREADY PASSING（hreflang ≥ 7） |
| ISS-018 | REQ-012 | 読者投票 API 疎通確認 | ✅ ALREADY PASSING（status: ok） |
| ISS-008 | REQ-002 | portal_plans / Stripe | 🚫 BLOCKED — Stripe未接続 |
| ISS-003〜005 | REQ-006/007/008 | Dataset + FAQPage schema | ✅ CLOSED (2026-03-29) `_build_dataset_ld()` + `_build_faqpage_ld()` 追加。JA/EN両ページ Dataset=1, FAQPage=1 確認済み。builder永続化済み（毎日cron保持） |
| ISS-017 | REQ-010 | X DLQ 82件解消 | ✅ CLOSED (2026-03-28) DLQ=0件確認済み。REQ-010調査で解消 |
| ISS-013 | REQ-011 | PARSE_ERROR 根本原因調査 | ✅ CLOSED (2026-03-29) 全7ページPython検証。PARSE_ERROR 0件確認済み |
| ISS-015 | — | robots.txt AI ディレクティブ確認 | ✅ ALREADY RESOLVED (2026-03-29) 静的ファイル `/var/www/nowpattern-static/robots.txt` に GPTBot/anthropic-ai: Disallow, ClaudeBot/PerplexityBot: Allow 確認済み。修正不要。 |
| — | — | prediction_page_builder.py `_build_error_card()` id属性追加 | ✅ DONE (2026-03-29) line 1379に `id="np-{pred_id.lower()}"` 追加。Oracle Guardian エラーカードのアンカーディープリンク対応。 |

---

## 実施タイムライン

| アクション | 対象 REQ |
|-----------|---------|
| REQ-001: llms.txt 静的ファイル（/var/www/nowpattern-static/）で修正。Python sed で2箇所置換。 | REQ-001 |
| REQ-009: 既にPASS（hreflang count ≥ 7）。修正不要と確認。 | REQ-009 |
| REQ-012: 既にPASS（reader-predict/health = ok）。修正不要と確認。 | REQ-012 |
| REQ-004+005: Python content.replace() で Caddyfile 修正（sed は改行処理で失敗したためPython採用）。llms-full.txt を Python で作成。 | REQ-004, REQ-005 |
| REQ-003: line-number-targeted Python スクリプト（/tmp/fix_ids.py）で4行修正。prediction_page_builder.py 再実行（E2E PASS）。 | REQ-003 |

---

## 変更ファイル一覧

| ファイル | ホスト | バックアップ | 変更内容 |
|---------|--------|------------|---------|
| `/var/www/nowpattern-static/llms.txt` | VPS | `llms.txt.bak-20260328` | `en-predictions/` → `en/predictions/`（2箇所） |
| `/var/www/nowpattern-static/llms-full.txt` | VPS | なし（新規作成） | 全記事リスト + AI指示書（約5407バイト） |
| `/etc/caddy/Caddyfile` | VPS | `Caddyfile.bak-20260328` | ① `encode zstd gzip` 追加、② llms-full.txt handle ブロック追加 |
| `/opt/shared/scripts/prediction_page_builder.py` | VPS | `prediction_page_builder.py.bak-20260328` | lines 903/931: `id="np-scoreboard"` 追加、lines 2524/2534: `id="np-resolved"` 追加 |
| `/opt/shared/scripts/prediction_page_builder.py` | VPS | `prediction_page_builder.py.bak-errorcard-20260329` | line 1379: `_build_error_card()` に `id="np-{pred_id.lower()}"` 追加（Oracle Guardian エラーカードのアンカーID対応） |

---

## 技術的発見・注意事項

### llms.txt は Ghost Page ではなく静的ファイル
FIX_PRIORITY の修正コマンドに「Ghost Admin → Pages → llms.txt で編集」と記載があったが、
実際には `/var/www/nowpattern-static/llms.txt` の静的ファイルとして Caddy が直接サーブしている。
Ghost Admin での編集ではなく、VPS ファイル直接編集で修正した。

### llms-full.txt の配置パス
FIX_PRIORITY 仕様書は `root * /var/www/nowpattern/content/files` と記述していた。
実際は `/var/www/nowpattern-static/` に配置した（既存 static file ディレクトリとの統一）。
Caddy の handle ブロックも `/var/www/nowpattern-static/` を参照するよう設定。機能上の問題なし。

### prediction_page_builder.py の split-string-literal 問題
`<div style="margin-bottom:24px;background:#fff;...">` は Python ソース上で2つの文字列リテラルに
分割されているため、grep で1行として検索すると 0 件になる。
行番号指定 + 部分文字列一致でターゲット4行を安全に修正した（line 903/931/2524/2534）。

### Caddyfile の編集方法
sed コマンドは改行処理で意図しない動作（`\tencode` が `tencode` になる等）が発生した。
Python の `content.replace()` を使用して安全に修正。

---

## ロールバック手順

```bash
# REQ-001 (llms.txt)
ssh root@163.44.124.123 "cp /var/www/nowpattern-static/llms.txt.bak-20260328 /var/www/nowpattern-static/llms.txt"

# REQ-004+005 (Caddyfile)
ssh root@163.44.124.123 "cp /etc/caddy/Caddyfile.bak-20260328 /etc/caddy/Caddyfile && systemctl reload caddy"

# REQ-003 (prediction_page_builder.py)
ssh root@163.44.124.123 "cp /opt/shared/scripts/prediction_page_builder.py.bak-20260328 /opt/shared/scripts/prediction_page_builder.py && python3 /opt/shared/scripts/prediction_page_builder.py"

# REQ-004 (llms-full.txt — 新規作成ファイルを削除)
ssh root@163.44.124.123 "rm /var/www/nowpattern-static/llms-full.txt"
```

---

*完了: 2026-03-28 | エンジニア: Claude Code (local)*
*参照: NOWPATTERN_FIX_PRIORITY_2026-03-28.md / NOWPATTERN_VERIFICATION_LOG_2026-03-28.md*
