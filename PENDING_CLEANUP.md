# PENDING_CLEANUP — 2026-04-01 10:00

> このファイルは `scripts/repo-audit.py` が自動生成しました。
> **使い方**: Claude Code に「N番を削除して」「N番をアーカイブして」と伝えるだけ。
> **無視したい場合**: 該当行を削除してから保存してください（次回監査まで無視されます）。

検出件数: 🔴 要対応 0件 / 🟡 要確認 28件

---

## 🟡 要確認

### [1] `DEVELOPMENT.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [2] `DOCKER_SETUP.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [3] `docs/FOUNDER_CONSTITUTION.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「aisaintel」を含む: @aisaintelアカウントは廃止済み

### [4] `docs/gap_analysis.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「aisaintel」を含む: @aisaintelアカウントは廃止済み

### [5] `docs/hooks_skills_agents_matrix.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「aisaintel」を含む: @aisaintelアカウントは廃止済み

### [6] `HANDOFF_INSTRUCTIONS.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [7] `IMPLEMENTATION.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [8] `scripts/_add_seo_head.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [9] `scripts/_check_ghost_posts.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [10] `scripts/_check_slugs.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [11] `scripts/_final_check.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [12] `scripts/_fix_404_articles.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [13] `scripts/_fix_404_republish.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [14] `scripts/_fix_404_tags.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [15] `scripts/_fix_backtick_pattern.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [16] `scripts/_fix_existing_articles.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [17] `scripts/_fix_existing_articles_tags.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [18] `scripts/_fix_existing_articles_v2.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [19] `scripts/_fix_ghost_tags.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [20] `scripts/_fix_path_traversal.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [21] `scripts/_fix_publisher_tag.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [22] `scripts/_recreate_404_articles.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [23] `scripts/_site_audit.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [24] `scripts/_update_neo2_claude_md.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [25] `scripts/_update_neo_claude_md.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [26] `scripts/_verify_site_js.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [27] `scripts/_verify_taxonomy.py`
**推奨アクション**: 削除候補
- 一回限りの修正スクリプト（最終更新 37日前）

### [28] `docs/NOWPATTERN_CLICKPATH_AUDIT_2026-03-28.md`
**推奨アクション**: 修正候補
- リンク切れ: `.*?` が存在しない

---

## 承認方法

Claude Code にそのまま伝えるだけ：

```
「1番と3番を削除して」
「2番をアーカイブして」
「全部承認して」
「今回は全部スキップ」
```

*次回自動実行: 月1回（Windows タスクスケジューラ）*
*手動実行: `python scripts/repo-audit.py`*