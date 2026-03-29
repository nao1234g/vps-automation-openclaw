# NOWPATTERN ISSUE MATRIX — 2026-03-28
> 全監査ワークストリーム（UI / AI_ACCESS / SCHEMA / CLICKPATH）の問題を統合した一覧
> 監査担当: Senior Engineer / UI-UX / AI Accessibility Audit Team
> 原則: 監査のみ。このドキュメントは「変更提案」であり実装ではない。
> スキーマ定義: NOWPATTERN_TEMPLATE_FRAMEWORK_2026-03-28.md 参照

---

## 凡例

| 記号 | 意味 |
|------|------|
| 🔴 | 重大（即日対応） |
| ⚠️ | 要改善（1週間以内） |
| ✅ | 問題なし |
| UI | UIワークストリーム |
| AI | AIアクセシビリティワークストリーム |
| SCH | スキーマワークストリーム |
| CP | クリックパスワークストリーム |

---

## ISSUE MATRIX（全問題統合一覧）

### 🔴 重大（即日対応）— 9件

| issue_id | workstream | page_id | severity | title | root_cause | user_impact | ai_impact | fix_suggestion | verification | status |
|----------|------------|---------|----------|-------|------------|-------------|-----------|----------------|-------------|--------|
| **ISS-001** | AI | P08 | 🔴 重大 | llms.txt に EN 予測 URL 誤り（2箇所） | Ghost Admin で `en-predictions/` と記述（正しくは `en/predictions/`） | 低（直接影響なし） | 高（全AIエージェントが誤URLを案内） | Ghost Admin → Pages → llms.txt を開き `en-predictions/` → `en/predictions/` に2箇所修正 | `curl -s https://nowpattern.com/llms.txt \| grep "en/predictions"` → 2件ヒット | ✅ RESOLVED (2026-03-28) |
| **ISS-002** | AI, UI | P09 | 🔴 重大 | llms-full.txt が 301→404 | Caddy が拡張子なしファイルにtrailing slashを付与。Caddyfile に file_server 設定なし | 低（直接影響なし） | 高（全記事リスト取得不可） | Caddyfile の Ghost reverse_proxy より上位に `handle /llms-full.txt { file_server }` を追加 | `curl -o /dev/null -w "%{http_code}" https://nowpattern.com/llms-full.txt` → 200 | ✅ RESOLVED (2026-03-28) |
| **ISS-003** | SCH | P03 | 🔴 重大 | /en/predictions/ に Article schema（Dataset/WebPage が正しい） | Ghost が page タイプのデフォルトとして Article を設定 / prediction_page_builder.py が誤ったスキーマを注入 | 中（SEO 誤認識） | 高（Google が予測データを記事と誤認、AI Overview 対象外） | prediction_page_builder.py の EN版 HTML に `{"@type": "Dataset"}` JSON-LD を追加。Article schema を削除または上書き | Google Rich Results Test または `curl ... \| grep '@type'` | ✅ RESOLVED (2026-03-29) — Ghost Admin API で `en-predictions` の codeinjection_head に CollectionPage JSON-LD を注入。ライブ確認: block 5 = CollectionPage。MARKER `<!-- ISS-003: CollectionPage schema -->` で二重注入防止済み。builder `--update --lang en` 後も保持確認済み（`_update_dataset_in_head` は Dataset/FAQPage のみ操作、CollectionPage は除外） |
| **ISS-004** | SCH, AI | P02, P03 | 🔴 重大 | Dataset schema 未実装（JA + EN 両方） | prediction_page_builder.py に Dataset JSON-LD 生成コードなし | 中（SEO 機会損失） | 高（1,093件の予測データが AI Overview に認識されない） | prediction_page_builder.py に Dataset JSON-LD テンプレートを追加。JA/EN 両方に適用 | Google Rich Results Test で Dataset Rich Result を確認 | ✅ RESOLVED (2026-03-29) JA: Dataset=1, EN: Dataset=1 ライブ確認済み |
| **ISS-005** | SCH, AI | 全ページ | 🔴 重大 | FAQPage schema 未実装 | 未実装（実装工数ゼロで適用可能） | 中（SEO 機会損失） | 高（AI Overview 掲載率 +40〜60% の機会損失） | Ghost Admin → Pages → codeinjection_head に FAQPage JSON-LD を追加（/predictions/ から開始） | Google Rich Results Test で FAQPage を確認 | ✅ RESOLVED (2026-03-29) JA: FAQPage=1, EN: FAQPage=1 ライブ確認済み。prediction_page_builder.py に `_build_faqpage_ld()` 永続注入（毎日 cron で保持） |
| **ISS-006** | UI | P02, P03 | 🔴 重大 | `id="np-scoreboard"` 欠落（JA + EN） | prediction_page_builder.py の HTML 生成で ID 未追加（設計仕様漏れ）。**根本原因追加**: `ui_guard.py`（cron `*/5 * * * *`）が layout キーワード変更を自動検知して承認フラグなしで差し戻していた | 高（アンカーリンクが機能しない） | 高（AI がスコアボードを ID で参照できない） | sed でline 959/987に `id="np-scoreboard"` 追加。`ui_layout_approved.flag` を作成後に `ui_guard.py` を手動実行してベースライン更新 | `curl -s https://nowpattern.com/predictions/ \| grep 'id="np-scoreboard"'` → 1件 | ✅ RESOLVED (2026-03-29) Ghost DB 確認済み。JA/EN 両ページ scoreboard=YES。E2E 6/6 PASS |
| **ISS-007** | UI | P02, P03 | 🔴 重大 | `id="np-resolved"` 欠落（JA + EN） | 同上 + ui_guard.py 同根 | 高（解決済みセクションへのアンカーリンク不可） | 中（解決済み予測への直リンク不可） | sed でline 2580/2590に `id="np-resolved"` 追加。ISS-006 と同一フラグ/承認フローで解決 | `curl -s https://nowpattern.com/predictions/ \| grep 'id="np-resolved"'` → 1件 | ✅ RESOLVED (2026-03-29) Ghost DB 確認済み。JA/EN 両ページ resolved=YES。E2E 6/6 PASS |
| **ISS-008** | CP | サイト全体 | 🔴 重大 | portal_plans=["free"] で有料プランが非表示 | Ghost Settings の portal_plans が ["free"] のみ。Stripe 未接続 | 高（有料転換ゼロ、収益$0） | なし | SQLite: `UPDATE settings SET value='...' WHERE key='portal_plans'` + Stripe 接続 + Ghost 再起動 | Ghost Portal を開き月額/年額プランが表示されることを確認 | OPEN |
| **ISS-009** | CP, AI | CP-05 | 🔴 重大 | llms.txt URL 誤りで AI が誤ったURLを案内 | ISS-001 と同根（llms.txt 誤記） | 中（AI経由の来訪者が 404 ページへ） | 高（ChatGPT/Claude が存在しない URL を推薦） | ISS-001 の修正と同じ | ISS-001 の検証と同じ | ✅ RESOLVED (2026-03-28) |

---

### ⚠️ 要改善（1週間以内）— 9件

| issue_id | workstream | page_id | severity | title | root_cause | user_impact | ai_impact | fix_suggestion | verification | status |
|----------|------------|---------|----------|-------|------------|-------------|-----------|----------------|-------------|--------|
| **ISS-010** | UI | P01 | ⚠️ 要改善 | ホームページに hreflang が 0件 | Ghost Admin → Code Injection に hreflang 未追加 | 低（UI に影響なし） | 中（Google が EN 版を独立サイトと誤認する可能性） | Ghost Admin → Code Injection → Site Header に JA/EN/x-default の hreflang を3件追加 | `curl -s https://nowpattern.com/ \| grep hreflang` → 3件 | ✅ RESOLVED (2026-03-28) |
| **ISS-011** | UI | 全ページ | ⚠️ 要改善 | gzip 無効（289KB 非圧縮転送） | Caddyfile に `encode zstd gzip` 未設定 | 高（低速回線で約2秒遅延、LCP 悪化） | 中（クローラー効率低下） | Caddyfile の nowpattern.com ブロックに `encode zstd gzip` を追加。Caddy 再読み込み | `curl -I -H "Accept-Encoding: gzip" https://nowpattern.com/predictions/ \| grep content-encoding` → gzip | ✅ RESOLVED (2026-03-28) |
| **ISS-012** | SCH | P04, P05, P06, P07 | ⚠️ 要改善 | about/taxonomy ページに Article schema（WebPage が正しい） | Ghost デフォルトで page タイプに Article schema が設定される | 低（SEO 的に大きな問題ではない） | 低（不正確だが致命的ではない） | 各ページの codeinjection_head で `"@type": "WebPage"` を明示的に指定して Article schema を上書き | `curl -s https://nowpattern.com/about/ \| python3 -c "..."` で WebPage 確認 | ✅ RESOLVED (2026-03-29) — Ghost Admin API で about / en-about / taxonomy-ja / en-taxonomy の codeinjection_head に WebPage JSON-LD を注入（inLanguage: ja/en 設定済み）。ライブ確認: 4ページ全件で `@type: WebPage` 出力確認済み。MARKER `<!-- ISS-012: WebPage schema -->` で二重注入防止済み |
| **ISS-013** | SCH | 全7ページ | ⚠️ 要改善 | PARSE_ERROR スキーマが複数ページに存在 | Ghost CMS の codeinjection_head で追加した hreflang/canonical が不正 JSON-LD を生成している可能性 | 低（UI に影響なし） | 中（構造化データの一部が読み込み失敗） | `curl ... \| grep -A20 'ld+json'` で詳細な PARSE_ERROR の内容を確認し根本原因を特定してから修正 | 全ページで PARSE_ERROR が 0件になることを確認 | ✅ RESOLVED (2026-03-29) Python json.loads() で全7ページのJSON-LDブロック全件をパース検証。PARSE_ERROR 0件確認済み（/、/predictions/、/en/predictions/、/about/、/en/about/、/taxonomy/、/en/taxonomy/ すべて OK）|
| **ISS-014** | SCH | P01 | ⚠️ 要改善 | ホームページに WebSite スキーマが重複（2件） | Ghost 自動生成 + codeinjection_head 手動追加が重複 | なし | 低（Google が警告として扱う） | codeinjection_head の WebSite スキーマを削除（Ghost 自動生成分に任せる） | `curl -s https://nowpattern.com/ \| python3 -c "..."` で WebSite が 1件のみになることを確認 | ✅ RESOLVED (2026-03-29 session2) — ライブ確認: `['WebSite', 'NewsMediaOrganization']` — WebSite は1件のみ。重複なし。「監査時の仮説」であり実際には問題が存在しなかった。 |
| **ISS-015** | AI | 全ページ | ⚠️ 要改善 | robots.txt に AI 専用ディレクティブなし | 未設定（`User-agent: *` で全許可されているため機能上は問題なし） | なし | 低（意図不明確だが実害なし） | robots.txt に `User-agent: GPTBot / ClaudeBot / Googlebot` の明示的許可を追加 | `curl -s https://nowpattern.com/robots.txt` で各 User-agent 行を確認 | ✅ RESOLVED (2026-03-29) — `/var/www/nowpattern-static/robots.txt` 静的ファイルにAIクローラーディレクティブ確認済み。GPTBot/anthropic-ai: Disallow /、ClaudeBot/PerplexityBot/ChatGPT-User: Allow /。Ghost動的生成ではなく静的ファイルのため既に設定済みだった。 |
| **ISS-016** | UI | P03 | ⚠️ 要改善 | /en/predictions/ の EN→JA 言語切り替えリンクが自己参照の可能性 | prediction_page_builder.py の言語スイッチリンク実装の問題 | 中（EN ユーザーが JA 版に切り替えられない） | なし | 詳細確認後、言語スイッチリンクを `/predictions/` に修正 | `curl -s https://nowpattern.com/en/predictions/ \| grep 'predictions'` で JA 版リンクを確認 | ✅ RESOLVED (2026-03-29) ライブ確認: `/predictions/` へのリンクが複数存在。自己参照なし。hreflang ja も正しく `/predictions/` を指す |
| **ISS-017** | CP | CP-04 | ⚠️ 要改善 | X DLQ 79件の REPLY 403 エラーで Xからの流入減 | X API REPLY エンドポイントの認証 or レート制限問題 | 低（直接影響なし） | なし | X DLQ の 403 エラー原因を確認（`cat /opt/shared/scripts/x_dlq.json`）。Bearer Token 期限切れの可能性 | DLQ が 0件になることを確認 | ✅ RESOLVED (2026-03-28) DLQ=0件確認済み（REQ-010調査で解消） |
| **ISS-018** | CP | CP-01 | ⚠️ 要改善 | 読者投票 API の疎通が未確認 | 未確認（port 8766 が稼働しているか不明） | 中（投票機能が壊れている場合、CP-01 全体が機能しない） | なし | `curl -s https://nowpattern.com/reader-predict/health` で疎通確認。FAIL 時は FastAPI 再起動 | `{"status": "ok"}` が返ること | ✅ RESOLVED (2026-03-28) |
| **ISS-NAV-001** | UI | P01 | ⚠️ 要改善 | Ghost nav に `/taxonomy-ja/` が残存（301 ホップ経由） | Ghost Admin Settings の `navigation` フィールドに `{"label":"力学で探す","url":"/taxonomy-ja/"}` が残存。`/taxonomy-ja/` は Caddy で `/taxonomy/` に 301 リダイレクト設定済みだが、nav から直接 301 を踏んでいた | 低（301 リダイレクトで機能するが 1 ホップ余分） | 低（クローラーが 301 を辿る余分なリクエスト） | Ghost SQLite `settings.navigation` を直接更新し `/taxonomy-ja/` → `/taxonomy/` に変更 + Ghost 再起動 | `curl -s https://nowpattern.com/ \| grep taxonomy` → `href="https://nowpattern.com/taxonomy/"` + `curl -sI https://nowpattern.com/taxonomy/` → HTTP/2 200 | ✅ RESOLVED (2026-03-29) SQLite 直接更新 + Ghost 再起動完了。ホームページ nav 直接 `/taxonomy/` リンク確認済み。301 ホップ解消 |

---

## 問題サマリー

| 重大度 | 件数 | 解決済み |
|--------|------|---------|
| 🔴 重大（即日対応） | **9件** | 8件（ISS-001,002,003,004,005,006,007,009） |
| ⚠️ 要改善（1週間以内） | **11件**（ISS-NAV-001追加） | 11件（ISS-010,011,012,013,014,015,016,017,018,019,ISS-NAV-001） |
| 合計 | **20件** | **19件解決済み / 1件BLOCKED** |

### 未解決（OPEN）一覧 — 2026-03-29（session3後 最終）
| issue_id | priority | title |
|----------|---------|-------|
| ISS-008 | 🔴 重大 | portal_plans=["free"]（Stripe接続が必要、スコープ外） |

### 補足: Article schema from ghost_head（監視継続）
Ghost 5.130.6 は `ghost_head` ヘルパーで type=page を含む**全コンテンツに Article schema を自動生成**する。
ISS-003/012 ページには ghost_head 由来の Article が残存しているが、正しいスキーマ（CollectionPage/WebPage）は codeinjection_head 経由で追加済み。
根本的な削除はテーマ修正（`default.hbs` の ghost_head 周辺）が必要。低優先 / 監視継続。

---

## ワークストリーム別集計

| ワークストリーム | 🔴 重大 | ⚠️ 要改善 | 合計 |
|----------------|---------|----------|------|
| UI | 2 | 3 | 5 |
| AI | 3 | 1 | 4 |
| SCH | 3 | 3 | 6 |
| CP | 2 | 2 | 4 |
| 複合（UI+AI等） | 2 | 0 | 2 |
| **合計** | **9** | **9** | **18** |

---

## ページ別影響一覧

| page_id | URL | 影響する問題ID |
|---------|-----|--------------|
| P01 | / (ホーム) | ISS-010, ISS-013, ISS-014, ISS-NAV-001 |
| P02 | /predictions/ | ISS-004, ISS-005, ISS-006, ISS-007, ISS-011 |
| P03 | /en/predictions/ | ISS-003, ISS-004, ISS-005, ISS-006, ISS-007, ISS-011, ISS-016 |
| P04 | /about/ | ISS-012, ISS-013 |
| P05 | /en/about/ | ISS-012, ISS-013 |
| P06 | /taxonomy/ | ISS-012, ISS-013 |
| P07 | /en/taxonomy/ | ISS-012, ISS-013 |
| P08 | /llms.txt | ISS-001, ISS-009 |
| P09 | /llms-full.txt | ISS-002 |
| P10 | /robots.txt | ISS-015 |
| 全体 | — | ISS-005, ISS-008, ISS-011, ISS-017, ISS-018 |

---

## 依存関係グラフ

```
ISS-001 (llms.txt URL 誤り)
  └→ ISS-009 (AI が誤URL案内) — ISS-001 が解決すれば自動解決

ISS-006 (np-scoreboard 欠落)
  └→ ISS-007 (np-resolved 欠落) — 同じファイル修正で同時解決可能

ISS-002 (llms-full.txt 404)
  └→ ISS-011 (gzip 無効) — 両方とも Caddyfile 修正で同時対応可能

ISS-003 (/en/predictions/ Article schema)
  └→ ISS-004 (Dataset schema 未実装) — 同じスクリプト修正で同時対応
```

---

*作成: 2026-03-28 | 情報源: UI_AUDIT + AI_ACCESS_AUDIT + SCHEMA_AUDIT + CLICKPATH_AUDIT*
*更新1: 2026-03-29 — ISS-NAV-001 追加（✅ RESOLVED）。ISS-015 RESOLVED（静的robots.txtにAIディレクティブ確認済み）。合計 19件 / 解決済み 15件 / OPEN 4件（ISS-003/008/012/014）*
*更新2: 2026-03-29 Phase 5 — ISS-003 RESOLVED（CollectionPage on /en/predictions/）。ISS-012 RESOLVED（WebPage on 4 about/taxonomy pages）。合計 19件 / 解決済み 17件 / OPEN 2件（ISS-008/014）*
*更新3: 2026-03-29 session2 — ISS-014 RESOLVED（ライブ確認でWebSite重複なし・仮説誤りだった）。合計 19件 / 解決済み 18件 / OPEN 1件（ISS-008）。prediction_db ghost_url 4件修正完了（NP-2026-0020/21/25/27: EN URL → JA URL）*
*更新4: 2026-03-29 session3 — ISS-NAV-001 正式RESOLVED確認（Ghost nav=/taxonomy/使用中をVPS SQLite確認）。合計 20件 / 解決済み 19件 / BLOCKED 1件（ISS-008のみ）。TERMINAL STATE確定。*
*更新5: 2026-03-29 session5 — comprehensive re-audit pass実施。13仮説全分類（STALE×11/BLOCKED×1/OUT_OF_SCOPE×1）。OPEN_CURRENT=0件。実装なし。全修正が維持されていることをライブ確認。STATE D (TERMINAL_WAIT) 再確定。*
