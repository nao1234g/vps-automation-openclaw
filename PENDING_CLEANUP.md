# PENDING_CLEANUP — 2026-02-23 06:16

> このファイルは `scripts/repo-audit.py` が自動生成しました。
> **使い方**: Claude Code に「N番を削除して」「N番をアーカイブして」と伝えるだけ。
> **無視したい場合**: 該当行を削除してから保存してください（次回監査まで無視されます）。

検出件数: 🔴 要対応 0件 / 🟡 要確認 15件

---

## 🟡 要確認

### [1] `DEPLOYMENT.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [2] `DEVELOPMENT.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [3] `DOCKER_SETUP.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [4] `docs/API_ENDPOINTS.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [5] `docs/CLAUDE_BRAIN_CONTEXT.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「Antigravity」を含む: Antigravity体制は廃止済み（2025年7月）

### [6] `docs/FAQ.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [7] `docs/MIGRATION.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [8] `docs/PROJECT_OVERVIEW.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [9] `docs/SKILL_TEMPLATE.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「Antigravity」を含む: Antigravity体制は廃止済み（2025年7月）

### [10] `docs/SUBSCRIPTION_OPTIMIZATION.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「Antigravity」を含む: Antigravity体制は廃止済み（2025年7月）

### [11] `docs/SUBSTACK_AUTO_PUBLISH_SETUP.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「AISA Newsletter」を含む: AISAブランドは廃止済み（Nowpattern統合）

### [12] `HANDOFF_INSTRUCTIONS.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [13] `IMPLEMENTATION.md`
**推奨アクション**: アーカイブ候補
- 廃止ワード「OpenNotebook」を含む: OpenNotebookサービスは現在未使用

### [14] `docs/PROJECT_OVERVIEW.md`
**推奨アクション**: 修正候補
- リンク切れ: `QUICKSTART.md` が存在しない

### [15] `docs/PROJECT_OVERVIEW.md`
**推奨アクション**: 修正候補
- リンク切れ: `MIGRATION_GUIDE.md` が存在しない

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