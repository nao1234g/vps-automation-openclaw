# Current Truth Reconciliation — 2026-03-29

> セッション開始時のドキュメント（FINAL_HANDOFF_2026-03-28.md）と
> VPS実態の突き合わせ。「書いてある」と「実際にそうなっている」の差分を記録する。

---

## 一致確認（FINAL_HANDOFF_2026-03-28 と VPS実態が一致）

| 項目 | ドキュメント記載 | VPS実態 | 一致 |
|------|----------------|---------|------|
| REQ-001 llms.txt 修正 | ✅ 完了 | `en-predictions/` → `en/predictions/` curl確認済み | ✅ |
| REQ-004 llms-full.txt + gzip | ✅ 完了 | HTTP 200 + content-encoding: gzip | ✅ |
| REQ-005 zstd/gzip encode | ✅ 完了 | 289KB→50KB | ✅ |
| REQ-003 ID属性 np-scoreboard/np-resolved | ✅ 完了 | HTML確認済み | ✅ |
| REQ-010 DLQ修正4件 | ✅ 完了 | DLQ=0 継続中 | ✅ |
| REQ-008 FAQPage schema | ✅ 完了 | count=1 (JA/EN両方) | ✅ |
| REQ-006+007 Dataset schema | ✅ 完了 | count=1 (JA/EN両方) | ✅ |
| Builder bug fix (block-aware) | ✅ 完了 | コード確認済み（line 2940-2954） | ✅ |
| REQ-009 元々PASS | ✅ 確認済み | 変更なし | ✅ |
| REQ-012 元々PASS | ✅ 確認済み | 変更なし | ✅ |
| REQ-002 BLOCKED (Stripe) | 🚫 記録済み | 変更なし | ✅ |

---

## 差分発見（ドキュメントに記載なかった事実）

### 差分1: REQ-011 「PARSE_ERROR」

**ドキュメント記載（FINAL_HANDOFF Month 1 1位）**:
> X投稿のパースエラーが発生している原因を特定・修正する

**VPS実態**:
- `PARSE_ERROR` 文字列は x_swarm_dispatcher.py に存在しない（grep結果: 0件）
- x_swarm 専用ログファイルが存在しない
- DLQ = 0（REQ-010修正が機能中）
- 実際のスレッド投稿エラー（旧Fix 1/3/4相当）は既に修正済み

**評価**: FINAL_HANDOFF での「PARSE_ERROR」は実装上の用語ではなく、当時の状況説明の表現。REQ-010で実質解消済み。

### 差分2: broken links「10件」

**ドキュメント記載（FINAL_HANDOFF Month 1 2位）**:
> prediction_page_builder.py の link checker が10件の broken linkを検出しており、JAページのbuilder実行がブロックされている

**VPS実態**:
- prediction_page.log で genre-URL 404 が記録されたのは **2026-03-03付近の歴史的ログ**
- 現時点: 20件のユニークURL、**全件 HTTP 200** ✅
- prediction_db.json に genre- プレフィックスURL = 0件
- cron は `--force` でlink checkをバイパス（歴史的ワークアラウンド）

**評価**: 歴史的問題で既に自然解消。「10件blocked」という状態は現在存在しない。

### 差分3: REQ-011「月1最優先」の実際の優先度

**現在の Month 1 実際の優先タスク（優先順）**:

1. **4件 ghost_url data quality fix** — JA 予測が EN 記事にリンクしている問題（軽微、UX影響あり）
2. **`--force` フラグ削除** — link check を有効化（オプション、harmless だが dead weight）
3. **REQ-002 Stripe** — BLOCKED継続

---

## 記事数（参照値）

```
VPS確認: 1331 published (JA:211, EN:1104, draft:17)
（2026-03-26 05:09 最終確認 — 現セッションでSSH確認は予測調査で実施）
```

---

## 追記: Phase 5 完了後の実態（2026-03-29）

### ISS-012 + ISS-003: スキーマ修正完了

| Issue | 修正前 | 修正後 | 手法 |
|-------|--------|--------|------|
| ISS-012 | about/taxonomy 4ページに Article のみ | WebPage schema 追加（inLanguage: ja/en） | Ghost Admin API で codeinjection_head 更新 |
| ISS-003 | /en/predictions/ に Article のみ | CollectionPage schema 追加 | Ghost Admin API で codeinjection_head 更新 |

### Builder SyntaxError 修正

`_build_claimreview_ld()` 関数の `return` 文に literal newline が混入しており SyntaxError が発生していた。
1行に圧縮し `\n` エスケープで修正。バックアップ: `.bak-20260329-claimreview`

### 現在の Issue 状態

| Issue | 状態 | 備考 |
|-------|------|------|
| ISS-003 | ✅ RESOLVED | CollectionPage on /en/predictions/ |
| ISS-008 | 🚫 BLOCKED | Stripe接続待ち |
| ISS-012 | ✅ RESOLVED | WebPage on 4 pages |
| ISS-014 | ✅ RESOLVED | 2026-03-29 session2 — ライブ確認でWebSite重複なし（false positive）|
| ISS-NAV-001 | ✅ RESOLVED | 2026-03-29 session3 — Ghost nav確認済み（/taxonomy/使用中）|

---

## 結論

FINAL_HANDOFF_2026-03-28 の記録内容は総じて正確。
差分2件（REQ-011の用語・broken links）は「当時の状況を反映した記述」であり、その後に自然解消または誤認されていた状態。

**最終実態（session3完了時点 2026-03-29）**: 20件中19件解決済み。BLOCKED は ISS-008（Stripe）のみ。ISS-014はライブ確認でfalse positive判明→RESOLVED。ISS-NAV-001はsession3でRESOLVED。

---

## 追記: Session 5 comprehensive re-audit（2026-03-29）

### 実施内容

13仮説をライブVPS確認で全分類。実装対象ゼロ確認。

| 確認項目 | 結果 |
|---------|------|
| DLQ | 0 ✅ (回帰なし) |
| ghost_url 4件 | 全JA URL ✅ (session2修正維持) |
| JA/EN predictions schemas | Dataset+FAQPage+CollectionPage 全共存 ✅ |
| about/taxonomy 4ページ WebPage | 全4ページ ✅ (session1修正維持) |
| Builder最終実行 | 2026-03-29 07:01 JST / E2E PASS ✅ |
| robots.txt AI directives | GPTBot等全Disallow:/ ✅ |
| llms.txt / llms-full.txt | 200 OK / gzip ✅ |
| Homepage hreflang | JS injection確認 (ISS-HREFLANG-001 backlog) |

### 13仮説分類結果

STALE_HYPOTHESIS_CLOSED: 11件 / BLOCKED: 1件 / OUT_OF_SCOPE: 1件 / **OPEN_CURRENT: 0件**

### Session 5 結論

実装なし。全修正が維持されている。STATE D (TERMINAL_WAIT) 確定。

詳細証跡: `VERIFICATION_LOG_2026-03-29-session5.md`

---

*作成: 2026-03-29 | 更新: session5 2026-03-29 | Engineer: Claude Code (local)*
