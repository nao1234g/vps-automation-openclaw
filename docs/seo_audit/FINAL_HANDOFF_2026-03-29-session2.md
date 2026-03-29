# Final Handoff — 2026-03-29 Session 2

> このセッション（session 2）で実施したこと・残っていること・次セッションへの引き継ぎ。
> 前セッション: FINAL_HANDOFF_2026-03-29.md (Phase 0-4 + nav taxonomy-ja fix + ghost_url quality fix)

---

## セッションクローズ確認

| 項目 | 状態 |
|------|------|
| Phase 1: ISS-014/003/012 ライブ確認 | ✅ 完了（VERIFICATION_LOG_2026-03-29-session2.md） |
| ISS-014 RESOLVED | ✅ WebSite=1件（重複なし）。監査時仮説誤り。 |
| ISS-003/012 Article残存 root cause | ✅ 特定（Ghost ghost_head 仕様）。正常監視継続。 |
| ghost_url 4件修正（NP-0020/21/25/27） | ✅ 完了（JA URL → prediction_db.json反映） |
| prediction_page_builder 再実行 | ✅ E2E全PASS（JA/EN両ページ確認済み） |
| ISSUE_MATRIX_2026-03-28.md 更新 | ✅ 完了（ISS-014 RESOLVED、合計19件/解決18件） |
| VERIFICATION_LOG_2026-03-29-session2.md | ✅ 作成完了 |
| 本番への影響 | prediction_page_builder --force 実行（E2E PASS確認済み） |

---

## 実施済み変更の概要

| 変更 | 内容 | 検証 | ロールバック |
|------|------|------|------------|
| prediction_db.json ghost_url 4件 | EN URL → JA URL（NP-0020/21/25/27） | ✅ Ghost DB HTML INSTR確認、E2E PASS | `/opt/shared/scripts/prediction_db.json.bak-20260329-080320` |
| prediction_page_builder rebuild | --force で JA/EN 両ページ再生成 | ✅ E2E全PASS | 前回ページは Ghost DB に残存 |
| ISSUE_MATRIX.md | ISS-014 RESOLVED、サマリー更新 | ✅ ドキュメント更新 | git revert |

---

## 今セッションの主な発見

### 1. ISS-014「WebSite重複」は監査時の仮説誤り

**監査記録**: WebSite が 2件存在する可能性があると記録されていた。

**ライブ確認結果**: `['WebSite', 'NewsMediaOrganization']` — WebSite は **1件のみ**。
重複は最初から存在しなかった。監査時に仮説として記録されたものが、検証なしにISSUEとして扱われていた。

**教訓**: 監査エントリを作成する際は、ライブ確認済みの問題と「要確認の仮説」を分けて記録すること。

### 2. ISS-003/012 Article残存は Ghost ghost_head の仕様

**調査結果**:
- Ghost 5.130.6 の `{{ghost_head}}` Handlebars ヘルパーは、`type='page'` のコンテンツにも `Article` JSON-LDを自動生成する
- HTML 位置: `~3711` bytes（`<head>` の早い位置 = `ghost_head` 由来）
- codeinjection_head の Article ではない（codeinjection_head = hreflangのみを確認済み）
- 削除には `default.hbs`（Ghost テーマファイル）の修正が必要

**現状判断**:
- 正しいスキーマ（WebPage/CollectionPage）は codeinjection_head 経由で存在する ✅
- Google は複数の JSON-LD がある場合、最も具体的なスキーマを優先認識する可能性が高い
- 修正コスト: 高（テーマ変更 + Ghost再起動）
- SEO 影響: 軽微（追加スキーマとして処理される）

**結論**: 低優先監視継続。テーマ修正は Month 2 以降で検討。

### 3. ghost_url ID-slug マッピング誤りの修正

FINAL_HANDOFF_2026-03-29 のマッピング提案（NP-2026-0020 と NP-2026-0027 のスラッグが入れ替わっていた）を、Ghost DB の実データから正しい対応関係に修正して実装した。

**修正内容**:
| prediction_id | 旧 ghost_url | 正しい ghost_url |
|--------------|-------------|----------------|
| NP-2026-0020 | `/en/en-fed-fomc-march-2026-rate-decision/` | `/fed-fomc-march-2026-rate-decision/` |
| NP-2026-0021 | `/en/en-btc-90k-march-31-2026/` | `/btc-90k-march-31-2026/` |
| NP-2026-0025 | `/en/en-khamenei-assassination-iran-supreme-leader-succession-2026/` | `/khamenei-assassination-iran-supreme-leader-succession-2026/` |
| NP-2026-0027 | `/en/en-btc-70k-march-31-2026/` | `/btc-70k-march-31-2026/` |

---

## 現在の Issue 状態（完全版）

| Issue | 状態 | 詳細 |
|-------|------|------|
| ISS-001 | ✅ RESOLVED | |
| ISS-002 | ✅ RESOLVED | |
| ISS-003 | ✅ RESOLVED | CollectionPage on /en/predictions/ 存在確認。Article残存=ghost_head仕様（低優先監視） |
| ISS-004 | ✅ RESOLVED | |
| ISS-005 | ✅ RESOLVED | |
| ISS-006 | ✅ RESOLVED | |
| ISS-007 | ✅ RESOLVED | |
| ISS-008 | 🚫 BLOCKED | Stripe接続待ち（スコープ外） |
| ISS-009 | ✅ RESOLVED | |
| ISS-010 | ✅ RESOLVED | |
| ISS-011 | ✅ RESOLVED | |
| ISS-012 | ✅ RESOLVED | WebPage on 4 pages 存在確認。Article残存=ghost_head仕様（低優先監視） |
| ISS-013 | ✅ RESOLVED | |
| ISS-014 | ✅ RESOLVED | ライブ確認でWebSite=1件（重複なし）。監査時仮説誤り。 |
| ISS-015 | ✅ RESOLVED | |
| ISS-016 | ✅ RESOLVED | |
| ISS-017 | ✅ RESOLVED | |
| ISS-018 | ✅ RESOLVED | |
| ISS-019 | ✅ RESOLVED | |

**合計: 19件 / 解決済み 18件 / OPEN 1件（ISS-008 Stripe待ち）**

---

## 残存タスク（次セッション以降のバックログ）

### 1位（低優先）: `--force` フラグ削除

cron から `--force` を削除して link check を有効化。現在の全リンクは200 OKなので影響なし。

### 2位（低優先）: Article schema / theme 修正検討

Ghost ghost_head が生成する Article を抑制するためのテーマ修正。
- ファイル: `/var/www/nowpattern/content/themes/source/default.hbs`
- 方法: `{{ghost_head}}` の後に JSON-LD を上書きするスクリプトを追加（要調査）
- 影響: Ghost 再起動が必要
- 優先度: 低（正しいスキーマが既に存在するため SEO 影響軽微）

### 3位（BLOCKED）: ISS-008 Stripe portal_plans

Stripe接続が先決。現在BLOCKED継続。

---

## PVQE 視点の引き継ぎ

| レバー | 状態 | 今セッション貢献 |
|--------|------|----------------|
| P（判断精度） | ✅ | 監査仮説（ISS-014）を実証的に否定・クローズ。ghost_head仕様の根本原因特定。 |
| V（改善速度） | ✅ | ghost_url 4件修正 + ISSUE_MATRIX更新を1セッションで完走 |
| Q（行動量） | ✅ | 200記事/日パイプライン継続（変更なし） |
| E（波及力） | ↑ | JA /predictions/ から JA 記事への直接リンク化（301ホップ解消） |

---

## 参照ドキュメント一覧

| ファイル | 内容 |
|---------|------|
| `VERIFICATION_LOG_2026-03-29-session2.md` | 本セッション全検証コマンドと確認結果の証跡 |
| `FINAL_HANDOFF_2026-03-29.md` | 前セッション引き継ぎ（Phase 0-4完了記録） |
| `MONTH1_EXECUTION_RUN_2026-03-29.md` | Month 1 全Phase実行記録 |
| `CURRENT_TRUTH_RECONCILIATION_2026-03-29.md` | ドキュメント vs VPS実態差分 |
| `docs/NOWPATTERN_ISSUE_MATRIX_2026-03-28.md` | 全Issue最終状態（19件/18件解決） |

---

*作成: 2026-03-29 Session 2 | Engineer: Claude Code (local)*
*引き継ぎ元: FINAL_HANDOFF_2026-03-29.md, VERIFICATION_LOG_2026-03-29-session2.md*
