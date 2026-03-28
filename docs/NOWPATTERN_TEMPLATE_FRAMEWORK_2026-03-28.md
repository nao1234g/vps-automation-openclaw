# NOWPATTERN AUDIT TEMPLATE FRAMEWORK — 2026-03-28
> 監査の「型」定義ファイル。UI_AUDIT / AI_ACCESS_AUDIT / ISSUE_MATRIX / FIX_PRIORITY の全ドキュメントはここの型に従う。
> 監査担当者: Senior Engineer / UI-UX Audit Lead / AI Accessibility Audit Lead
> 原則: 実装禁止。監査・ドキュメント化のみ。

---

## 1. 監査スコープ（対象ページ）

| PageID | 公開URL | Ghostスラッグ | 言語 | 種別 |
|--------|---------|-------------|------|------|
| P01 | `nowpattern.com/` | `index` | JA | ホーム |
| P02 | `nowpattern.com/predictions/` | `predictions` | JA | 予測ページ（カスタムビルド） |
| P03 | `nowpattern.com/en/predictions/` | `en-predictions` | EN | 予測ページ（カスタムビルド） |
| P04 | `nowpattern.com/about/` | `about` | JA | Aboutページ |
| P05 | `nowpattern.com/en/about/` | `en-about` | EN | Aboutページ |
| P06 | `nowpattern.com/taxonomy/` | `taxonomy-ja` | JA | タクソノミーガイド |
| P07 | `nowpattern.com/en/taxonomy/` | `en-taxonomy` | EN | タクソノミーガイド |
| P08 | `nowpattern.com/llms.txt` | — | — | AIエージェント指示ファイル |
| P09 | `nowpattern.com/llms-full.txt` | — | — | AI全記事リスト |
| P10 | `nowpattern.com/robots.txt` | — | — | クローラー制御 |
| P11 | `nowpattern.com/sitemap.xml` | — | — | サイトマップ |
| P12 | `nowpattern.com/{article-slug}/` | 各記事 | JA | 個別記事 |
| P13 | `nowpattern.com/en/{article-slug}/` | `en-{slug}` | EN | 個別記事 |

---

## 2. 重大度スケール（Severity Scale）

| レベル | 記号 | 定義 | 対応期限 |
|--------|------|------|---------|
| **問題なし** | ✅ | 期待通り動作。改善余地なし or 軽微 | — |
| **要改善** | ⚠️ | 動作するが最適でない。UX/SEO/AI indexing に悪影響 | 1週間以内 |
| **重大** | 🔴 | 機能が壊れているか、重要な機会損失が発生している | 即日対応 |

---

## 3. 影響軸（Impact Axes）

各問題は2軸で評価する:

| 軸 | 説明 |
|----|------|
| **user_impact** | 人間ユーザー（読者・購読者）への影響度（高/中/低） |
| **ai_impact** | AIエージェント（GPTBot/ClaudeBot/Gemini等）への影響度（高/中/低） |

---

## 4. Issue Record スキーマ（ISSUE_MATRIX の1行）

各問題は以下のフィールドを持つ:

| フィールド | 型 | 説明 |
|------------|-----|------|
| `issue_id` | String | 例: `UI-001`, `AI-003` |
| `workstream` | Enum | `UI` / `AI_ACCESS` / `SCHEMA` / `CLICKPATH` |
| `page_id` | String | 上記PageID（例: P02） |
| `severity` | Enum | `問題なし` / `要改善` / `重大` |
| `title` | String | 問題の短い説明（60字以内） |
| `root_cause` | String | なぜ起きているか |
| `user_impact` | String | 人間への影響 |
| `ai_impact` | String | AIエージェントへの影響 |
| `fix_suggestion` | String | 具体的な修正方法（コマンド/手順） |
| `verification` | String | 修正後の確認コマンド |
| `status` | Enum | `OPEN` / `IN_PROGRESS` / `FIXED` |

---

## 5. Requirement Contract スキーマ（FIX_PRIORITY の1行）

| フィールド | 説明 |
|------------|------|
| `req_id` | 要件ID（例: REQ-001） |
| `workstream` | UI / AI_ACCESS / SCHEMA / CLICKPATH |
| `requirement_text` | 「〜であること」形式で記述 |
| `acceptance_criteria` | 合格の定義（測定可能であること） |
| `evidence_needed` | 必要な証拠の種類 |
| `evidence_source` | 証拠の取得元（curl/VPS/Google等） |
| `status` | PASS / FAIL / UNVERIFIED |
| `blocker_reason` | FAILの場合の理由 |
| `notes` | 補足事項 |

---

## 6. 監査ワークストリーム（実施順序）

```
WS1 → このファイル（TEMPLATE_FRAMEWORK）: 型を定義
  ↓
WS2 → ライブサイトチェック: curl/SSH で実データ収集
  ↓
WS3 → UI_AUDIT: 人間向けUI品質監査（9種チェック）
  ↓
WS4 → AI_ACCESS_AUDIT: AIエージェント向けアクセシビリティ監査
  ↓
WS5 → SCHEMA_AUDIT + CLICKPATH_AUDIT（任意補足）
  ↓
WS6 → ISSUE_MATRIX: 全問題の統合リスト
  ↓
WS7 → FIX_PRIORITY: ROI順の優先リスト（Requirement Contract付き）
  ↓
WS8 → FINAL_HANDOFF: 次のセッションへの引き継ぎ
```

---

## 7. UI監査チェックリスト（WS3）

UIチェックは以下9カテゴリで実施:

| カテゴリID | 名称 | チェック内容 |
|------------|------|------------|
| UI-HTTP | HTTPステータス | 全ページが200を返すか |
| UI-VISUAL | 視覚的破綻 | レイアウト崩れ、重なり、白紙表示 |
| UI-LINK | リンク/CTA | 壊れたリンク、404先リンク、不正なCTA |
| UI-ANCHOR | アンカーID | np-scoreboard/np-resolved/np-tracking-listの存在 |
| UI-LANG | 言語切り替え | JA/EN双方向リンクの正確性 |
| UI-SEO | canonical/hreflang | 正確なcanonical設定、双方向hreflang |
| UI-INTERACT | インタラクション | 投票UI、予測参加UI、フォーム |
| UI-MOBILE | モバイル | スマートフォンでの表示問題（推測ベース） |
| UI-INFO | 情報設計 | CTAの視認性、情報の優先度、認知負荷 |

---

## 8. AIアクセシビリティ監査チェックリスト（WS4）

| カテゴリID | 名称 | チェック内容 |
|------------|------|------------|
| AI-LLMS | llms.txt | 到達可能か、URLが正確か |
| AI-FULL | llms-full.txt | 到達可能か（301→404問題） |
| AI-ROBOTS | robots.txt | クローラー許可/拒否設定 |
| AI-SITEMAP | sitemap.xml | 到達可能か、記事数が適切か |
| AI-SCHEMA | 構造化データ | @typeが各ページに適切か |
| AI-AUTHOR | 著者/発行者 | author/publisherが正確か |
| AI-DATE | dateModified | 最終更新日が正確か |
| AI-CANON | canonical | AIが参照するURLが正確か |
| AI-PREDICT | 予測機械可読性 | 予測データがAIに伝わる形式か |

---

## 9. スキーマ適切性マトリクス（参照基準）

| ページ種別 | 現在の@type | 期待される@type | 正/否 |
|------------|------------|----------------|------|
| ホーム | WebSite | WebSite | ✅ |
| 予測ページ（JA/EN） | Article or WebPage | Dataset + WebPage | 要確認 |
| About | WebPage | WebPage | ✅ |
| タクソノミー | WebPage | WebPage | ✅ |
| 個別記事（JA/EN） | Article / NewsArticle | Article / NewsArticle | ✅ |
| llms.txt | — | — | 非HTML |

---

## 10. 予測ページ専用チェック（prediction-design-system.md 準拠）

| チェック | 期待値 | チェック方法 |
|----------|--------|------------|
| `id="np-scoreboard"` | HTMLに1件 | `curl ... \| grep -c 'id="np-scoreboard"'` |
| `id="np-resolved"` | HTMLに1件 | `curl ... \| grep -c 'id="np-resolved"'` |
| `id="np-tracking-list"` または相当 | HTMLに存在 | grep確認 |
| スコアボード4列グリッド | `grid-template-columns:repeat(4,1fr)` | HTML確認 |
| カード背景#fff | 存在 | HTML確認 |
| 的中色#22c55e | 存在 | HTML確認 |
| 外れ色#ef4444 | 存在 | HTML確認 |
| 投票ウィジェット | 各カードに存在 | HTML確認 |

---

## 11. 出力ドキュメント一覧（作成義務）

| ファイル名 | 種別 | 状態 |
|-----------|------|------|
| `NOWPATTERN_TEMPLATE_FRAMEWORK_2026-03-28.md` | 必須 | ✅ このファイル |
| `NOWPATTERN_UI_AUDIT_2026-03-28.md` | 必須 | 作成中 |
| `NOWPATTERN_AI_ACCESS_AUDIT_2026-03-28.md` | 必須 | 作成中 |
| `NOWPATTERN_ISSUE_MATRIX_2026-03-28.md` | 必須 | 作成中 |
| `NOWPATTERN_FIX_PRIORITY_2026-03-28.md` | 必須 | 作成中 |
| `NOWPATTERN_FINAL_HANDOFF_2026-03-28.md` | 必須（更新） | 存在 |
| `NOWPATTERN_SCHEMA_AUDIT_2026-03-28.md` | 任意 | 作成中 |
| `NOWPATTERN_CLICKPATH_AUDIT_2026-03-28.md` | 任意 | 作成中 |
| `NOWPATTERN_LLM_DISCOVERY_AUDIT_2026-03-28.md` | 任意 | 作成中 |

---

## 12. 監査の前提事実（2026-03-28時点）

以下はライブチェック前に確認済みの事実（CURRENT_STATE_2026-03-28.md から）:

| 事実 | 確認方法 | 重要度 |
|------|----------|--------|
| Ghost v5.130.6（NOT 6.0） | VPS確認済み | 高（ActivityPub使用不可） |
| 記事数: JA229/EN1131 | SQLite確認済み | 参考 |
| draft: 88件 | SQLite確認済み | 参考 |
| prediction_db.json: 1,093件 | VPS確認済み | 高 |
| Brier Score: 0.1828 | VPS確認済み | 参考 |
| portal_plans: ["free"] | SQLite確認済み | 重大 |
| llms.txt: EN URL誤り | curl確認済み | 重大 |
| llms-full.txt: 301→404 | curl確認済み | 重大 |
| gzip: 無効 | curl -I確認済み | 要改善 |
| X DLQ: 79件REPLY 403 | VPS確認済み | 重大 |

---

## 絶対原則（このセッション全体）

```
1. NO IMPLEMENTATION — 変更・push・実行は禁止
2. 全ての問題は「提案」として記録するのみ
3. 証拠（curl出力/SSH出力）をドキュメントに含める
4. ユーザーが「実装してよい」と言うまで変更しない
```

---

*作成: 2026-03-28 | 監査セッション用型定義*
*次のドキュメント: NOWPATTERN_UI_AUDIT_2026-03-28.md*
