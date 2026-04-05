# Task Result v7 — Prediction Linkage 4トラック完了

## 概要

| トラック | 内容 | 状態 |
|---------|------|------|
| **C** | Ghost DBローダー共通化 | ✅ 完了・コミット済み |
| **A** | EN slug正規化 dry-run | ✅ スクリプト完了・VPS実行待ち |
| **B** | cross_language publish queue | ✅ スクリプト完了・VPS実行待ち |
| **D** | E2E回帰テスト | ✅ 20/20テストPASS |

## Track C: Ghost DBローダー共通化

**問題**: 4スクリプトが各自独立にGhost SQLiteをクエリ。タグ正規化・HTML取得が不統一 → html=""バグの根本原因。

**解決**: `ghost_post_loader.py` に統合。
- タグは常に `set` 型に正規化
- HTMLは常に取得（空文字列にしない）
- `is_oracle` をロード時に計算

**リファクタリング対象**:
- `prediction_linkage_backfill.py` — `_load_ghost_posts()` 削除
- `cross_language_only_audit.py` — `_load_ghost_posts_full()` 削除
- `prediction_slug_drift_audit.py` — `_load_ghost_slugs()` 削除

## Track A: EN slug正規化 dry-run

`prediction_slug_normalization_plan.py` — 526件のpattern_mismatch ENリンクを安全分類:
- `safe_normalize`: Ghost に `en-{slug}` が存在、マッピング一意
- `unsafe_ambiguous`: 複数prediction_idが同一slugを参照
- `ghost_missing`: Ghost にどちらの形式も不在
- `draft_only`: `en-{slug}` がdraft状態
- `db_stale`: prediction_dbエントリが陳腐化

**VPS実行コマンド**: `cd /opt/shared/scripts && python3 prediction_slug_normalization_plan.py`

## Track B: cross_language publish queue

`cross_language_publish_queue_builder.py` — 10件のcross_language_only記事のpublish-ready queue:
- JA原文のslug・title・html長をGhostから取得
- prediction_dbからEN slug・URLを取得
- `ready_for_translation` ステータスのqueueを生成

**VPS実行コマンド**: `cd /opt/shared/scripts && python3 cross_language_publish_queue_builder.py`

## Track D: E2Eテスト結果

```
20 passed, 0 failed
```

新規7テスト:
1. `test_ghost_post_loader_always_includes_html` — html=""バグ再発防止
2. `test_ghost_post_loader_tag_normalization` — tag_slugsはset型
3. `test_tag_set_internal_normalization` — _tag_set()エッジケース
4. `test_ghost_post_loader_split_by_status` — published/draft分離
5. `test_ghost_post_loader_split_by_status_ignores_other_statuses` — scheduled除外
6. `test_slug_normalization_preserves_prediction_id` — prediction_id保全
7. `test_ledger_dedup_chain_integrity` — ledger chain hash検証

## コミット履歴

| ハッシュ | メッセージ |
|---------|-----------|
| `78144bd` | refactor: Ghost DBローダー共通化 |
| `655b4c4` | feat: prediction linkage infrastructure + coordination OS |
| `6c7cb24` | feat: Track A/B/D — EN slug正規化plan + publish queue + E2Eテスト |
