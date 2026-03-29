# NOWPATTERN IMPLEMENTED FIXES — 2026-03-28
> 実装済み各修正の詳細記録（before / after / evidence / rollback）
> Round 3 実施分のみ。REQ-001/003/004/005 + 確認済みPASS(REQ-009/012)。

---

## FIX-001: llms.txt EN URL 修正

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-001 |
| **issue_ids** | ISS-001, ISS-009 |
| **why_now** | ROI=10（最高スコア）。AI クローラーが誤URLを案内している。5分で完了。 |
| **evidence_before** | `curl -s https://nowpattern.com/llms.txt \| grep en-predictions` → 2件ヒット（誤URL） |
| **exact_change** | `/var/www/nowpattern-static/llms.txt` の `en-predictions/` を `en/predictions/` に2箇所置換 |
| **evidence_after** | `curl -s https://nowpattern.com/llms.txt \| grep en/predictions/` → 2件ヒット ✅ |
| **backup** | `/var/www/nowpattern-static/llms.txt.bak-20260328` |
| **rollback** | `cp llms.txt.bak-20260328 llms.txt` |
| **blast_radius** | llms.txt のみ。AIクローラーへの影響（即時改善）。 |
| **implementation_note** | 修正コマンドに「Ghost Admin → Pages → llms.txt」とあったが、実際は静的ファイル。VPS 直接編集で対応。 |

---

## FIX-003: np-scoreboard / np-resolved ID 追加（2026-03-29 完了）

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-003 |
| **issue_ids** | ISS-006, ISS-007 |
| **why_now** | ROI=8。アンカーリンク復活。X シェアでスコアボード直リンク可能（E 間接支援）。 |
| **evidence_before** | `curl -s https://nowpattern.com/predictions/ \| grep -c 'id="np-scoreboard"'` → 0 |
| **root_cause** | `ui_guard.py`（cron `*/5 * * * *`）が LAYOUT_FUNCTIONS キーワード（`np-scoreboard`, `np-resolved`, `border-radius` 等）を監視。承認フラグ未作成時は自動的にベースラインへ差し戻す設計。過去の修正がすべて5分以内にリバートされていた原因。 |
| **exact_change** | `sed -i` で 4行を修正:<br>- line 959: `<div style="` → `<div id="np-scoreboard" style="`<br>- line 987: 同上（別 return path）<br>- line 2580: `<div style="` → `<div id="np-resolved" style="`<br>- line 2590: 同上（else branch） |
| **approval_flow** | `touch /opt/shared/reports/page-history/ui_layout_approved.flag` → sed patch 適用 → `python3 ui_guard.py` 手動実行 → "approved change accepted" → ベースライン更新 → フラグ消費 |
| **evidence_after** | Ghost DB: `predictions` + `en-predictions` 両方 scoreboard=YES / resolved=YES / tracking=YES ✅<br>Live site: `curl https://nowpattern.com/predictions/` → ID count 4 ✅<br>E2E: 6/6 PASS ✅<br>File md5 stable: `fbe75d79b5f16017e4fe77a5cec7ac9c` (141492 bytes) |
| **backup** | `/opt/shared/scripts/prediction_page_builder.py.bak-20260328` (pre-patch original)<br>`/opt/shared/reports/page-history/builder-backups/prediction_page_builder.py.bak-20260328-faq` (ui_guard 自動バックアップ) |
| **rollback** | `cp prediction_page_builder.py.bak-20260328 prediction_page_builder.py`<br>`touch ui_layout_approved.flag && python3 ui_guard.py` でベースライン差し戻し |
| **blast_radius** | prediction_page_builder.py のみ。ページ再生成後 E2E PASS 確認済み。 |
| **lesson** | ui_guard.py の承認フロー（`prediction-design-system.md` § UI変更提案フロー）を必ず先に実行すること。「patch → verify → done」では ui_guard.py が5分で差し戻す。正しい手順: `flag 作成 → patch → ui_guard 手動実行 → ベースライン更新確認`。 |

---

## FIX-004+005: Caddyfile 修正（llms-full.txt + gzip）

| フィールド | 内容 |
|-----------|------|
| **req_ids** | REQ-004, REQ-005 |
| **issue_ids** | ISS-002, ISS-011 |
| **why_now** | REQ-004 ROI=8（llms-full.txt 404解消）。REQ-005 ROI=8（同セッションでコスト実質ゼロ）。 |
| **evidence_before** | llms-full.txt: 301 → 404。圧縮: content-encoding ヘッダーなし（289KB非圧縮）。 |
| **exact_change_005** | `/etc/caddy/Caddyfile` の `nowpattern.com {` 直後に `encode zstd gzip` 追加 |
| **exact_change_004** | Caddyfile に `handle /llms-full.txt { root * /var/www/nowpattern-static; file_server; header Content-Type "text/plain; charset=utf-8" }` 追加 + `/var/www/nowpattern-static/llms-full.txt` を新規作成（約5407バイト） |
| **evidence_after_005** | `curl -sI https://nowpattern.com/predictions/ \| grep content-encoding` → `content-encoding: gzip` ✅（289KB → 50KB、83%削減） |
| **evidence_after_004** | `curl -o /dev/null -w "%{http_code}" https://nowpattern.com/llms-full.txt` → 200 ✅ |
| **backup** | `/etc/caddy/Caddyfile.bak-20260328` |
| **rollback** | `cp Caddyfile.bak-20260328 Caddyfile && systemctl reload caddy` |
| **blast_radius** | Caddy 設定変更。全ページの圧縮が有効化（全サイトに影響。今回は改善のみ）。 |
| **implementation_note** | sed コマンドは改行エスケープ処理で失敗（`\tencode` が `tencode` になる）。Python content.replace() で安全に修正した。llms-full.txt はコンテンツ内の括弧・特殊文字が heredoc を壊すため Python で作成。配置パスは仕様書の `content/files/` ではなく既存 static ディレクトリ（`nowpattern-static/`）に統一。 |

---

## PASS-009: ホームページ hreflang（確認のみ）

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-009 |
| **issue_id** | ISS-010 |
| **evidence** | `curl -s https://nowpattern.com/ \| grep -c hreflang` → 7 ✅（要件: ≥ 3） |
| **action** | 変更なし。既に PASS。 |

---

## PASS-012: 読者投票 API（確認のみ）

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-012 |
| **issue_id** | ISS-018 |
| **evidence** | `curl -s https://nowpattern.com/reader-predict/health` → `{"status":"ok"}` ✅ |
| **action** | 変更なし。既に PASS。 |

---

*作成: 2026-03-28 | エンジニア: Claude Code (local)*
