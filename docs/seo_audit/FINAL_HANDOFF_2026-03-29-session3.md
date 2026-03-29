# Final Handoff — 2026-03-29 Session 3

> このセッション（session 3）で実施したこと・残っていること・次セッションへの引き継ぎ。
> 前セッション: FINAL_HANDOFF_2026-03-29-session2.md（ghost_url 4件修正 + ISS-014 RESOLVED）

---

## セッションクローズ確認

| 項目 | 状態 |
|------|------|
| Phase 0: VPS live verification 完走 | ✅ 完了（VERIFICATION_LOG_2026-03-29-session3.md） |
| 13項目 Phase 1 分類 | ✅ 全件 STALE/RESOLVED/BLOCKED/BACKLOG に分類完了 |
| Phase 2: 新規実装 | ✅ 不要（新しいOPEN項目なし） |
| Phase 3: Builder durability | ✅ 確認済み（block-aware regex + log OK） |
| Phase 4: Docs closeout | ✅ VERIFICATION_LOG + FINAL_HANDOFF 作成 |
| 本番への影響 | なし（今セッションはread-only確認のみ） |

---

## 今セッションの主な発見

### 1. ClaimReview @graph スキーマ — 期待通り

JA predictions の codeinjection_head に存在した `@type=NO_TYPE`（`@graph`型）スキーマ2件は、`prediction_page_builder.py` が生成する **ClaimReview JSON-LD**（各5件の予測が入ったGraph）であることを確認。

- SEO的に正常なスキーマ構造（`@context` + `@graph`は有効なJSON-LD形式）
- バグではない。監査時に「タイプ不明」と見えていたが、実体はbuilderの正常出力

### 2. ISS-NAV-001 — ドキュメントがstale

`docs/NOWPATTERN_EN_JA_LINK_MAPPING_2026-03-29.md` の「残存課題」でISS-NAV-001（`/taxonomy-ja/`露出）が OPEN として記録されていたが、ライブVPSのGhost navigationは既に `/taxonomy/` を使用中。ドキュメントが実態より遅れていた。

**措置**: 本ドキュメント（FINAL_HANDOFF）でRESOLVED記録。

### 3. NP-0007 builder警告 — stale log entry

`page_rebuild.log`に`⚠️ NO ARTICLE: NP-2026-0007 — ghost_url missing`が出現していたが、この警告コードは現行の`prediction_page_builder.py`には存在しない（バックアップ版のみ）。NP-2026-0007 には ghost_url が正しく設定されており、Ghost DB にもスラッグが`published`で存在する。→ 古いbuilder版実行時の残留ログ。

### 4. WebPage=2 / WebSite=1 の正しい解釈

`about`/`taxonomy-ja`等のページの `codeinjection_head` で schema check が WebPage=2 と見える理由:
- Index 1: `<!-- ISS-012: WebPage schema -->` マーカーコメント（JSON-LDではない、正規表現で拾われる）
- Index 2: 実際の `"@type": "WebPage"` JSON-LDオブジェクト

WebSite=1 の理由: `isPartOf: {"@type": "WebSite"}` として WebPage schema 内にネスト済み（独立WebSite宣言ではない）。

これらは全て期待通りの構造。

---

## 13項目 Phase 1 分類サマリー

| 項目 | 分類 | 確認方法 |
|------|------|---------|
| ISS-003 Article from ghost_head | LOW_PRIORITY_MONITOR | ghost_head仕様。CollectionPage確認済み。 |
| ISS-012 Article from ghost_head | LOW_PRIORITY_MONITOR | ghost_head仕様。WebPage確認済み。 |
| ISS-014 WebSite duplicate | STALE_HYPOTHESIS | ライブ確認=WebSite 1件のみ（ネスト） |
| ISS-015 robots.txt | RESOLVED ✅ | robots.txt AI directives確認済み |
| ghost_url 4件 | RESOLVED ✅ | JA URLすべて確認済み（session2修正） |
| ISS-NAV-001 /taxonomy/ | RESOLVED ✅ | Ghost nav確認済み（doc stale修正） |
| ClaimReview @graph schemas | CURRENT_TRUTH/EXPECTED | builder正常動作確認 |
| FAQPage/Dataset regression | CURRENT_TRUTH/HEALTHY | codeinjection_head FAQPage=1/Dataset=1 |
| block-aware regex | CURRENT_TRUTH/HEALTHY | L3010確認済み |
| ISS-SLUG-001 681件 | OPEN_BACKLOG | 次スプリント（中優先） |
| ISS-HREFLANG-001 記事hreflang | OPEN_BACKLOG | 次スプリント（低〜中優先） |
| NP-0007 warning | STALE_LOG_ENTRY | 現行builderに該当コードなし |
| ISS-008 Stripe | BLOCKED | Stripe接続待ち |

---

## 現在の Issue 状態（完全版）

| Issue | 状態 | 詳細 |
|-------|------|------|
| ISS-001 | ✅ RESOLVED | |
| ISS-002 | ✅ RESOLVED | |
| ISS-003 | ✅ RESOLVED | CollectionPage on /en/predictions/ 確認。Article残存=ghost_head仕様（低優先監視） |
| ISS-004 | ✅ RESOLVED | |
| ISS-005 | ✅ RESOLVED | |
| ISS-006 | ✅ RESOLVED | |
| ISS-007 | ✅ RESOLVED | |
| ISS-008 | 🚫 BLOCKED | Stripe接続待ち（スコープ外） |
| ISS-009 | ✅ RESOLVED | |
| ISS-010 | ✅ RESOLVED | |
| ISS-011 | ✅ RESOLVED | |
| ISS-012 | ✅ RESOLVED | WebPage on 4 pages 確認。Article残存=ghost_head仕様（低優先監視） |
| ISS-013 | ✅ RESOLVED | |
| ISS-014 | ✅ RESOLVED | ライブ確認=WebSite 1件（重複なし）。監査時仮説誤り。 |
| ISS-015 | ✅ RESOLVED | robots.txt AI directives 確認済み |
| ISS-016 | ✅ RESOLVED | |
| ISS-017 | ✅ RESOLVED | |
| ISS-018 | ✅ RESOLVED | |
| ISS-019 | ✅ RESOLVED | |
| ISS-NAV-001 | ✅ RESOLVED | Ghost nav=/taxonomy/確認済み（2026-03-29 session3） |

**合計: 21件 / 解決済み 20件 / OPEN 1件（ISS-008 Stripe待ち）**

---

## バックログ（次SEOスプリント以降）

### 1位（中優先）: ISS-SLUG-001 — EN記事681件の`en-`プレフィックス未付与
- **対象**: EN記事でGhost slug先頭に`en-`がない681件（旧形式）
- **現在の動作**: Caddyが`lang-en`タグ検知で `/en/[slug]/` にリダイレクト（200到達）
- **リスク**: Google Searchが `/en/` パス統一を学習しにくい。SEO弱め。
- **推奨対応**: batch slug修正スクリプト（slugをen-[slug]に変更 + Caddy redirect rule追加）
- **注意**: slugを変えると既存URLが301に変わる。インデックス更新待ちが発生。

### 2位（低〜中優先）: ISS-HREFLANG-001 — 記事個別のhreflangがJS動的注入
- **対象**: 全記事（1315件超）の個別hreflang
- **現在の動作**: Ghost テーマのJS（`<head>`に動的inject）
- **リスク**: GooglebotがJSを実行しない場合、hreflangが読み取れない
- **推奨対応**: 記事公開時にGhost `codeinjection_head` に静的 `<link rel="alternate">` を注入するスクリプトを検討
- **注意**: 新規記事からの適用でも1315件のレトロフィットが必要

### 3位（BLOCKED）: ISS-008 Stripe portal_plans
- Stripe接続が先決。BLOCKED継続。

### 4位（低優先）: Article schema / theme修正
- Ghost `{{ghost_head}}`が全ページにArticle JSON-LDを自動生成する仕様
- 正しいスキーマ（WebPage/CollectionPage）が既に存在するため SEO影響軽微
- 修正にはGhostテーマ変更が必要（`default.hbs` + Ghost再起動）

---

## PVQE 視点の引き継ぎ

| レバー | 状態 | 今セッション貢献 |
|--------|------|----------------|
| P（判断精度） | ✅ | 13項目を証拠ベースで分類。stale仮説を切り捨て。ClaimReview/WebPage構造を確実に解明。 |
| V（改善速度） | ✅ | Phase 0-4を1セッションで完走（read-only確認） |
| Q（行動量） | ✅ | 200記事/日パイプライン継続（変更なし） |
| E（波及力） | → | バックログ整理済み。次スプリントのEN slug修正でSEO波及力が上がる。 |

---

## 参照ドキュメント一覧

| ファイル | 内容 |
|---------|------|
| `VERIFICATION_LOG_2026-03-29-session3.md` | 本セッション全検証コマンドと確認結果の証跡 |
| `FINAL_HANDOFF_2026-03-29-session2.md` | 前セッション引き継ぎ（ghost_url 4件修正 + ISS-014 RESOLVED） |
| `FINAL_HANDOFF_2026-03-29.md` | session1引き継ぎ（Phase 0-4完了記録） |
| `docs/NOWPATTERN_EN_JA_LINK_MAPPING_2026-03-29.md` | EN/JAペアマッピング（ISS-NAV-001はstale→実態RESOLVED） |
| `docs/NOWPATTERN_ISSUE_MATRIX_2026-03-28.md` | 全Issue状態（本セッションでISS-NAV-001追加RESOLVED） |

---

*作成: 2026-03-29 Session 3 | Engineer: Claude Code (local)*
*引き継ぎ元: FINAL_HANDOFF_2026-03-29-session2.md*

**TERMINAL STATE: WAITING_FOR_USER_DECISION**
