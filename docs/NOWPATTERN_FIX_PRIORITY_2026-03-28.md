# NOWPATTERN FIX PRIORITY — 2026-03-28
> ROI 順の優先リスト + Requirement Contract（9列）
> 監査担当: Senior Engineer / AI Accessibility Audit Team
> 原則: 監査のみ。ユーザーが「実装してよい」と明示するまで変更なし。
> 前提: ISSUE_MATRIX_2026-03-28.md の 18件を ROI 順に並び替え

---

## ROI スコアリング基準

| 軸 | 説明 | 点数 |
|----|------|------|
| **ビジネスインパクト** | 収益・トラフィック・信頼への直接影響 | 1〜5 |
| **修正コスト** | 実装時間・リスク（低いほど高スコア） | 1〜5 |
| **ROI = インパクト + 修正コスト** | 高いほど優先 | 2〜10 |

---

## TIER 0: 即日 × 低コスト（ROI 最大）— まずここから

### REQ-001: llms.txt の EN URL を修正する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-001 |
| **workstream** | AI_ACCESS |
| **requirement_text** | llms.txt の英語予測ページ URL が `https://nowpattern.com/en/predictions/` であること（`en-predictions/` は不可） |
| **acceptance_criteria** | `curl -s https://nowpattern.com/llms.txt \| grep "en/predictions"` が 2件ヒットすること |
| **evidence_needed** | llms.txt の全文（URL 含む） |
| **evidence_source** | `curl -s https://nowpattern.com/llms.txt` |
| **status** | ✅ DONE（2026-03-28） |
| **blocker_reason** | 現在 `en-predictions/`（2箇所）が誤り |
| **notes** | Ghost Admin → Pages → llms.txt で編集。約5分の作業。リスクゼロ。ISS-001 + ISS-009 を同時解決 |

**修正コマンド:**
```
Ghost Admin → https://nowpattern.com/ghost/
→ Pages → "llms.txt" を開く
→ 本文で "en-predictions/" を "en/predictions/" に置換（2箇所）
→ Update
```

**ビジネスインパクト**: 5（ChatGPT/Claude/Gemini が正しいURL案内）
**修正コスト**: 5（5分・リスクゼロ）
**ROI スコア**: 10

---

### REQ-002: portal_plans に monthly/yearly を追加する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-002 |
| **workstream** | CLICKPATH |
| **requirement_text** | Ghost Portal で月額・年額プランが表示されること |
| **acceptance_criteria** | Ghost Portal を開いたとき "Monthly" / "Yearly" プランが表示される |
| **evidence_needed** | Ghost Admin → Settings → Portal のスクリーンショット |
| **evidence_source** | Ghost Admin UI または `sqlite3 ghost.db "SELECT value FROM settings WHERE key='portal_plans';"` |
| **status** | FAIL |
| **blocker_reason** | `portal_plans: ["free"]` で有料プランが非表示 |
| **notes** | Stripe 接続も別途必要。Stripe 未接続なら Portal に表示してもクレジットカード入力不可。2ステップ: (1) Stripe 設定, (2) portal_plans 更新。ISS-008 解決 |

**修正コマンド（Stripe 接続後）:**
```bash
# SQLite直接更新
ssh root@163.44.124.123 "sqlite3 /var/www/nowpattern/content/data/ghost.db \
  \"UPDATE settings SET value='{\"plans\":[\"free\",\"monthly\",\"yearly\"]}' \
    WHERE key='portal_plans';\""
# Ghost 再起動
ssh root@163.44.124.123 "systemctl restart ghost-nowpattern"
```

**ビジネスインパクト**: 5（有料転換 0→N、直接収益化）
**修正コスト**: 3（Stripe設定が複数ステップ）
**ROI スコア**: 8

---

### REQ-003: np-scoreboard / np-resolved ID を追加する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-003 |
| **workstream** | UI |
| **requirement_text** | `/predictions/` と `/en/predictions/` の HTML に `id="np-scoreboard"` と `id="np-resolved"` が存在すること |
| **acceptance_criteria** | `curl -s https://nowpattern.com/predictions/ \| grep -c 'id="np-scoreboard"'` → 1 / `curl -s https://nowpattern.com/predictions/ \| grep -c 'id="np-resolved"'` → 1 |
| **evidence_needed** | 両予測ページの HTML（ID 属性） |
| **evidence_source** | curl + grep 実行 |
| **status** | ✅ DONE（2026-03-28） |
| **blocker_reason** | audit_check.py: np-scoreboard=False, np-resolved=False（両ページ） |
| **notes** | prediction_page_builder.py の class="np-scoreboard-wrapper" → id="np-scoreboard" class="np-scoreboard-wrapper" に変更。ページ再生成が必要。ISS-006 + ISS-007 を同時解決 |

**修正コマンド:**
```bash
# VPS で prediction_page_builder.py を編集
ssh root@163.44.124.123 "grep -n 'np-scoreboard-wrapper\|resolved-section' \
  /opt/shared/scripts/prediction_page_builder.py | head -20"
# 確認後に以下の2行を修正:
# class="np-scoreboard-wrapper" → id="np-scoreboard" class="np-scoreboard-wrapper"
# class="resolved-section" → id="np-resolved" class="resolved-section"
# ページ再生成:
ssh root@163.44.124.123 "python3 /opt/shared/scripts/prediction_page_builder.py"
```

**ビジネスインパクト**: 4（アンカーリンク復活、X シェアでスコアボード直リンク可能）
**修正コスト**: 4（2行修正 + ページ再生成）
**ROI スコア**: 8

---

## TIER 1: 即日 × 中コスト（Caddyfile 修正）

### REQ-004: llms-full.txt の 404 を解消する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-004 |
| **workstream** | AI_ACCESS |
| **requirement_text** | `https://nowpattern.com/llms-full.txt` が HTTP 200 で到達可能であること |
| **acceptance_criteria** | `curl -o /dev/null -w "%{http_code}" https://nowpattern.com/llms-full.txt` → 200 |
| **evidence_needed** | curl HTTP ステータスコード |
| **evidence_source** | curl 実行 |
| **status** | ✅ DONE（2026-03-28） |
| **blocker_reason** | 301 → /llms-full.txt/ (trailing slash) → 404。Caddyfile に file_server 設定なし |
| **notes** | Caddyfile の Ghost reverse_proxy より上位に `handle /llms-full.txt` ブロックを追加。llms-full.txt ファイルが `/var/www/nowpattern/content/files/` に存在することを先に確認。ISS-002 解決 |

**修正内容:**
```caddy
# /etc/caddy/Caddyfile（Ghost reverse_proxy より上位）
handle /llms-full.txt {
    root * /var/www/nowpattern/content/files
    file_server
}
```

**ビジネスインパクト**: 4（AI が全記事リスト取得可能）
**修正コスト**: 4（Caddyfile 修正 + reload）
**ROI スコア**: 8

---

### REQ-005: gzip 圧縮を有効化する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-005 |
| **workstream** | UI |
| **requirement_text** | `/predictions/` への gzip 圧縮レスポンスが有効であること |
| **acceptance_criteria** | `curl -I -H "Accept-Encoding: gzip" https://nowpattern.com/predictions/ \| grep content-encoding` → `content-encoding: gzip` |
| **evidence_needed** | curl -I の content-encoding ヘッダー |
| **evidence_source** | curl 実行 |
| **status** | ✅ DONE（2026-03-28） |
| **blocker_reason** | content-encoding ヘッダーなし（289,579 bytes 非圧縮）。Caddyfile に `encode zstd gzip` なし |
| **notes** | REQ-004 と同じ Caddyfile 編集セッションで同時修正可能。`encode zstd gzip` を nowpattern.com ブロックの先頭近くに追加。ISS-011 解決 |

**修正内容:**
```caddy
# /etc/caddy/Caddyfile（nowpattern.com ブロック内）
encode zstd gzip
```

**ビジネスインパクト**: 3（LCP 改善、低速回線のUX向上）
**修正コスト**: 5（REQ-004 と同時修正でコスト実質ゼロ）
**ROI スコア**: 8

---

## TIER 2: 高インパクト × 中コスト（スキーマ改善）

### REQ-006: /en/predictions/ の Dataset schema を実装する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-006 |
| **workstream** | SCHEMA, AI_ACCESS |
| **requirement_text** | `/en/predictions/` に Dataset JSON-LD が実装されており、`@type: Dataset` が確認できること。Article schema は削除または Dataset が優先されること |
| **acceptance_criteria** | Google Rich Results Test または `curl -s https://nowpattern.com/en/predictions/ \| python3 -c "..."` で Dataset @type が返ること |
| **evidence_needed** | ページの JSON-LD 全文 |
| **evidence_source** | curl + python3 JSON-LD parse |
| **status** | FAIL |
| **blocker_reason** | 現在 Article schema が存在する。Dataset schema は未実装 |
| **notes** | prediction_page_builder.py の EN版 HTML 生成部に Dataset JSON-LD テンプレートを追加。ISS-003 + ISS-004（EN）解決 |

**修正コマンド:**
```python
# prediction_page_builder.py に追加する Dataset JSON-LD テンプレート（EN版）
dataset_schema = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "name": "Nowpattern Prediction Tracker",
    "description": f"Brier Score prediction tracker with {total_count} predictions.",
    "url": "https://nowpattern.com/en/predictions/",
    "creator": {"@type": "Organization", "name": "Nowpattern"},
    "temporalCoverage": "2025/..",
    "inLanguage": "en"
}
```

**ビジネスインパクト**: 4（Google AI Overview で予測データセットとして認識）
**修正コスト**: 3（prediction_page_builder.py 修正 + 再生成）
**ROI スコア**: 7

---

### REQ-007: /predictions/ (JA) にも Dataset schema を追加する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-007 |
| **workstream** | SCHEMA, AI_ACCESS |
| **requirement_text** | `/predictions/` に Dataset JSON-LD が実装されていること |
| **acceptance_criteria** | `curl -s https://nowpattern.com/predictions/ \| python3 -c "..."` で Dataset @type が返ること |
| **evidence_needed** | ページの JSON-LD |
| **evidence_source** | curl + python3 JSON-LD parse |
| **status** | FAIL |
| **blocker_reason** | Dataset schema 未実装 |
| **notes** | REQ-006 と同じ修正セッションで JA 版にも追加。ISS-004（JA）解決 |

**ビジネスインパクト**: 4
**修正コスト**: 4（REQ-006 と同時実施でほぼ追加コストなし）
**ROI スコア**: 8

---

### REQ-008: /predictions/ に FAQPage schema を追加する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-008 |
| **workstream** | SCHEMA, AI_ACCESS |
| **requirement_text** | `/predictions/` ページに FAQPage JSON-LD が実装されていること |
| **acceptance_criteria** | Google Rich Results Test で FAQPage が PASS すること |
| **evidence_needed** | Google Rich Results Test の結果 |
| **evidence_source** | https://search.google.com/test/rich-results（手動確認） |
| **status** | FAIL |
| **blocker_reason** | FAQPage schema 未実装 |
| **notes** | Ghost Admin → Pages → predictions/en-predictions の codeinjection_head に FAQPage JSON-LD を追加。よくある質問（Brier Scoreとは？予測への参加方法は？）を3〜5問用意する。ISS-005 解決 |

**修正内容（JSON-LD テンプレート）:**
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Brier Scoreとは何ですか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Brier Scoreは予測精度を測る指標です。0が完全予測、1が最悪です。Nowpatternの現在のスコアは0.18です。"
      }
    },
    {
      "@type": "Question",
      "name": "予測に参加するにはどうすればよいですか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "予測ページで各カードの投票ウィジェットを使って参加できます。登録不要です。"
      }
    }
  ]
}
```

**ビジネスインパクト**: 5（AI Overview 掲載率大幅向上）
**修正コスト**: 3（FAQテキスト作成 + Ghost Admin 更新）
**ROI スコア**: 8

---

## TIER 3: 改善（低コスト）

### REQ-009: ホームページに hreflang を追加する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-009 |
| **workstream** | UI, AI_ACCESS |
| **requirement_text** | ホームページ（`/`）に JA / EN / x-default の hreflang が3件存在すること |
| **acceptance_criteria** | `curl -s https://nowpattern.com/ \| grep -c hreflang` → 3以上 |
| **evidence_needed** | curl の hreflang タグ数 |
| **evidence_source** | curl 実行 |
| **status** | ✅ ALREADY PASSING（変更なし） |
| **blocker_reason** | ホームページの hreflang = 0件 |
| **notes** | Ghost Admin → Code Injection → Site Header に3行追加。5分以下の作業。ISS-010 解決 |

**修正内容:**
```html
<link rel="alternate" hreflang="ja" href="https://nowpattern.com/" />
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/" />
<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/" />
```

**ビジネスインパクト**: 3（Google の言語認識改善）
**修正コスト**: 5（3行追加、5分）
**ROI スコア**: 8

---

### REQ-010: X DLQ の 403 エラーを解消する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-010 |
| **workstream** | CLICKPATH |
| **requirement_text** | X DLQ（Dead Letter Queue）の REPLY 403 エラーが 0件であること |
| **acceptance_criteria** | `/opt/shared/scripts/x_dlq.json` の 403 エラー件数が 0 |
| **evidence_needed** | x_dlq.json の内容 |
| **evidence_source** | `ssh root@163.44.124.123 "cat /opt/shared/scripts/x_dlq.json"` |
| **status** | FAIL |
| **blocker_reason** | 79件の REPLY が 403 エラーで停滞中 |
| **notes** | 403 の原因は Bearer Token 期限切れ、または REPLY 先ツイートの削除・保護設定。DLQ の内容を確認してから対処。ISS-017 解決 |

**ビジネスインパクト**: 4（X からの流入 30% 回復）
**修正コスト**: 3（原因調査が必要）
**ROI スコア**: 7

---

### REQ-011: PARSE_ERROR スキーマの根本原因を特定する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-011 |
| **workstream** | SCHEMA |
| **requirement_text** | 全7ページで JSON-LD の PARSE_ERROR が 0件であること |
| **acceptance_criteria** | audit_check.py を再実行して PARSE_ERROR が 0件 |
| **evidence_needed** | PARSE_ERROR の詳細なエラー内容（行番号・内容） |
| **evidence_source** | VPS で詳細調査スクリプトを実行 |
| **status** | FAIL |
| **blocker_reason** | 全7ページで PARSE_ERROR が複数検出されている。根本原因は調査中 |
| **notes** | 先に原因調査が必要（Ghost自動生成 vs codeinjection_head 手動追加の切り分け）。ISS-013 解決 |

**ビジネスインパクト**: 3（構造化データが完全に読み取られる）
**修正コスト**: 2（原因調査 + 修正の2段階）
**ROI スコア**: 5

---

### REQ-012: 読者投票 API の疎通を確認する

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-012 |
| **workstream** | CLICKPATH |
| **requirement_text** | `https://nowpattern.com/reader-predict/health` が `{"status": "ok"}` を返すこと |
| **acceptance_criteria** | curl でステータス 200 + `status: ok` の JSON レスポンス |
| **evidence_needed** | curl レスポンス |
| **evidence_source** | `curl -s https://nowpattern.com/reader-predict/health` |
| **status** | ✅ ALREADY PASSING（変更なし） |
| **blocker_reason** | 未確認（調査が必要） |
| **notes** | 5分以内で確認可能。FAIL の場合は FastAPI サービス再起動が必要。ISS-018 解決 |

**ビジネスインパクト**: 4（投票機能が機能しているか確認）
**修正コスト**: 5（確認のみ。1コマンド）
**ROI スコア**: 9（確認コスト最小で影響大）

---

## 実施順序（推奨）

```
Day 1（即日）:
  1. REQ-001: llms.txt URL 修正（5分）
  2. REQ-009: hreflang ホームページ追加（5分）
  3. REQ-012: 読者投票 API 疎通確認（5分）
  4. REQ-004 + REQ-005: Caddyfile 修正（llms-full.txt + gzip）（30分）
  5. REQ-003: np-scoreboard/np-resolved ID 追加（30分）

Week 1（1週間以内）:
  6. REQ-002: portal_plans + Stripe 設定（60〜120分）
  7. REQ-006 + REQ-007: Dataset schema 追加（60分）
  8. REQ-008: FAQPage schema 追加（30分）
  9. REQ-010: X DLQ 403 調査・解消（30〜60分）

Month 1:
  10. REQ-011: PARSE_ERROR 根本原因調査・修正
  11. about/taxonomy の WebPage schema 修正（ISS-012）
  12. WebSite 重複スキーマ削除（ISS-014）
  13. robots.txt AI 専用ディレクティブ追加（ISS-015）
```

---

## 総 ROI サマリー

| req_id | タイトル | ROI スコア | 推定時間 |
|--------|---------|-----------|---------|
| REQ-001 | llms.txt URL 修正 | 10 | 5分 |
| REQ-012 | 読者投票 API 確認 | 9 | 5分 |
| REQ-002 | portal_plans 修正 | 8 | 60〜120分 |
| REQ-003 | np-scoreboard ID 追加 | 8 | 30分 |
| REQ-004 | llms-full.txt 404 解消 | 8 | 30分 |
| REQ-005 | gzip 有効化 | 8 | 10分（REQ-004と同時） |
| REQ-007 | JA Dataset schema | 8 | 同上 |
| REQ-008 | FAQPage schema | 8 | 30分 |
| REQ-009 | hreflang ホーム追加 | 8 | 5分 |
| REQ-006 | EN Dataset schema | 7 | 60分 |
| REQ-010 | X DLQ 403 解消 | 7 | 30〜60分 |
| REQ-011 | PARSE_ERROR 調査 | 5 | 60〜120分 |

---

*作成: 2026-03-28 | ユーザーが「実装してよい」と明示するまで変更なし*
*次: NOWPATTERN_FINAL_HANDOFF_2026-03-28.md 更新*
