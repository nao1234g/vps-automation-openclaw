# Claude → Codex (Round 6): Prediction Linkage Backfill + Slug Drift + Ledger Dedup + Cross-Language Audit

## Date: 2026-04-05

## 変更概要

Round 5で構築したprediction release contractの上に、4つの改善トラックを実装・デプロイ・検証した。

| トラック | 成果物 | 状態 |
|---------|--------|------|
| A. missing_sibling 80件分類 | `prediction_linkage_backfill.py` + レポート | ✅ VPS稼働中 |
| B. slug drift検知 | `prediction_slug_drift_audit.py` + レポート | ✅ VPS稼働中 |
| C. ledger状態変化型dedup | `prediction_release_contract.py` 改修 | ✅ VPS検証済み |
| D. cross_language_only 10件監査 | `cross_language_only_audit.py` + レポート | ✅ VPS稼働中 |

---

## 変更ファイル一覧（8ファイル）

### 新規作成

| ファイル | 目的 |
|---------|------|
| `scripts/prediction_linkage_backfill.py` | missing_sibling記事を機械的に分類しbackfill queueを生成 |
| `scripts/prediction_slug_drift_audit.py` | prediction_dbとGhostのslug乖離を検知 |
| `scripts/cross_language_only_audit.py` | cross_language_only記事の原因調査・分類 |
| `scripts/test_prediction_linkage_backfill.py` | 上記3スクリプト + ledger dedup のテスト（13テスト） |

### 修正

| ファイル | 変更内容 |
|---------|---------|
| `scripts/prediction_release_contract.py` | `_state_signature()`, `read_latest_entry_by_slug()` 追加。`append_ledger_entry()` に `skip_if_unchanged` パラメータ追加 |
| `scripts/build_article_release_manifest.py` | ledger appendに `skip_if_unchanged=True` 追加 |

---

## Track A: missing_sibling 80件の分類結果

### VPS実行結果（2026-04-05 ライブGhost DB）

```
total_missing_sibling=80
action_translate_and_register=80
auto_fixable=0
needs_translation=80
```

**全80件が `translate_and_register`** — EN版が完全に不在、prediction_dbにもEN article_linksが未登録。

| 分類 | 件数 | 意味 |
|------|------|------|
| `en_missing_entirely` | 80 | EN版がGhostに存在しない（publishedにもdraftにもない） |
| `db_link_missing` | 80 | prediction_dbにもEN article_linksエントリなし |

**アクション内訳**:
- `publish_draft` (Ghost draftを公開するだけ): **0件**
- `investigate_slug_mismatch` (slug不一致調査): **0件**
- `create_and_publish_translation` (DBリンク登録済み、翻訳のみ): **0件**
- `translate_and_register` (翻訳＋DBリンク登録＋Ghost公開): **80件**

**結論**: 自動解消できる記事は0件。全80件にEN版の翻訳・作成が必要。

レポート: `/opt/shared/reports/prediction_linkage_backfill_queue.json` + `.md`

### classify_missing_sibling() の分類ロジック

```python
def classify_missing_sibling(*, slug, article_lang, prediction_id, published, draft, pid_to_links):
    target_lang = "ja" if article_lang == "en" else "en"
    expected_slug = "en-" + clean_slug(slug) if target_lang == "en" else clean_slug(slug)

    # Ghost状態チェック
    if expected_slug in published:  → slug_mismatch
    elif expected_slug in draft:    → exists_draft (auto_fixable)
    else:                           → missing_entirely

    # prediction_db article_linksチェック
    if pid has target_lang link:    → db_link_registered
    else:                           → db_link_missing
```

---

## Track B: slug drift検知結果

### VPS実行結果

```
total_drifts=2154
drift_db_link_ghost_draft=663
drift_db_link_ghost_missing=156
drift_db_slug_ghost_draft=663
drift_db_slug_ghost_missing=146
drift_link_slug_pattern_mismatch=526
```

| drift種別 | 件数 | 意味 |
|-----------|------|------|
| `db_slug_ghost_draft` | 663 | article_slugがGhostでdraft状態（QA Sentinel降格分含む） |
| `db_slug_ghost_missing` | 146 | article_slugがGhostに不在 |
| `db_link_ghost_draft` | 663 | article_links[].slugがGhostでdraft状態 |
| `db_link_ghost_missing` | 156 | article_links[].slugがGhostに不在 |
| `link_slug_pattern_mismatch` | 526 | EN linkにen-接頭辞なし、またはJA linkにen-接頭辞あり |

**注**: draft 663件はQA Sentinel降格による意図的設計。ghost_missing 146-156件が要調査。

レポート: `/opt/shared/reports/prediction_slug_drift_report.json` + `.md`

実行コマンド:
```bash
cd /opt/shared/scripts && python3 prediction_slug_drift_audit.py
```

---

## Track C: ledger状態変化型dedup

### 変更内容

`append_ledger_entry()` に `skip_if_unchanged: bool = False` パラメータを追加。

```python
def _state_signature(linkage_state, article_backing_state, release_lane,
                     sibling_slug, prediction_id, governor_policy_version) -> str:
    parts = [linkage_state, article_backing_state, release_lane,
             sibling_slug or "", prediction_id, governor_policy_version]
    return "|".join(parts)
```

`skip_if_unchanged=True` の場合:
1. 同じslugの最新エントリを `read_latest_entry_by_slug()` で取得
2. 同じstate signature → None返却（書き込みスキップ）
3. 異なるstate signature → 通常通り書き込み
4. 異なるslug → 常に書き込み

### 検証結果

- manifest 2回連続実行: ledger 99行 → 99行（dedup完全動作）
- `verify_ledger_chain()`: `{"ok": true, "entry_count": 99, "errors": []}`
- 後方互換性: `skip_if_unchanged` のデフォルトは `False`（既存呼び出し元影響なし）

**Remaining Risk #4（Round 5）は解消**: 「No deduplication in ledger」→ 状態変化時のみ追記に改善。

---

## Track D: cross_language_only 10件監査結果

### VPS実行結果

```
total_cross_language_only=10
cause_unpublished=10
```

**全10件の原因が `unpublished`**: prediction_dbにEN slug（article_links）が登録されているが、Ghost記事が未作成。

| 原因 | 件数 | 意味 |
|------|------|------|
| `unpublished` | 10 | DBにEN slugが登録済みだがGhost記事が存在しない |
| `draft_only` | 0 | Ghost draftとして存在（公開するだけで解消） |
| `wrong_lang_tag` | 0 | Ghost記事あるが言語タグ不正 |
| `ghost_missing` | 0 | DBにも対象言語の登録なし |

**修正アクション**: 全10件 `create_and_publish`（EN記事を作成して公開）

レポート: `/opt/shared/reports/cross_language_only_audit.json` + `.md`

---

## テスト結果

### ローカル（Windows）

| テストファイル | 件数 | 結果 |
|--------------|------|------|
| `test_prediction_linkage_backfill.py` | 13 | 13 PASS |
| `test_prediction_release_contract.py` | 28 | 28 PASS |
| **合計** | **41** | **41 PASS** |

### VPS

| テストファイル | 件数 | 結果 |
|--------------|------|------|
| `test_prediction_linkage_backfill.py` | 13 | 13 PASS |
| `test_prediction_release_contract.py` | 28 | 28 PASS |
| **合計** | **41** | **41 PASS** |

テスト内容:
- `classify_missing_sibling`: 5パターン（en_missing_entirely, en_exists_draft, en_missing_with_db_link, ja_missing_from_en, slug_mismatch）
- `_state_signature`: 3パターン（deterministic, linkage change, lane change）
- `read_latest_entry_by_slug`: multi-slug latest entry
- ledger dedup: 4パターン（skip identical, write on state change, different slug always writes, backward compat）

---

## VPSデプロイ済みファイル

```bash
# デプロイコマンド
scp scripts/prediction_linkage_backfill.py root@163.44.124.123:/opt/shared/scripts/
scp scripts/prediction_slug_drift_audit.py root@163.44.124.123:/opt/shared/scripts/
scp scripts/cross_language_only_audit.py root@163.44.124.123:/opt/shared/scripts/
scp scripts/prediction_release_contract.py root@163.44.124.123:/opt/shared/scripts/
scp scripts/build_article_release_manifest.py root@163.44.124.123:/opt/shared/scripts/
scp scripts/test_prediction_linkage_backfill.py root@163.44.124.123:/opt/shared/scripts/
```

---

## 実行コマンド一覧

```bash
# backfill queue生成
cd /opt/shared/scripts && python3 prediction_linkage_backfill.py

# slug drift検知
cd /opt/shared/scripts && python3 prediction_slug_drift_audit.py

# cross_language_only監査
cd /opt/shared/scripts && python3 cross_language_only_audit.py

# テスト実行
cd /opt/shared/scripts && python3 test_prediction_linkage_backfill.py
cd /opt/shared/scripts && python3 test_prediction_release_contract.py

# ledger検証
cd /opt/shared/scripts && python3 -c "from prediction_release_contract import verify_ledger_chain; import json; print(json.dumps(verify_ledger_chain(), indent=2))"
```

---

## 残るリスク

1. **missing_sibling 80件**: 全件EN版翻訳が必要。自動解消不可。nowpattern_publisherの翻訳パイプラインで対応予定。

2. **link_slug_pattern_mismatch 526件**: prediction_dbのarticle_links[lang=en]のslugに`en-`接頭辞がないケースが大量にある。prediction_db側のslug正規化が必要。

3. **db_slug_ghost_missing 146件**: prediction_dbに登録されたarticle_slugがGhostに存在しない。記事未作成 or slug変更の可能性。

4. **cross_language_only 10件**: DBにENリンク登録済みだがGhost記事未作成。翻訳パイプラインで優先対応すべき（DBリンクは既に正しい）。

---

## Codex向け次のステップ

### 即実行可能

1. **レポート確認**: `cat /opt/shared/reports/prediction_linkage_backfill_queue.json | python3 -m json.tool | head -50`

2. **slug pattern mismatch修正**: 526件のEN article_linksにen-接頭辞を追加するスクリプト作成

3. **cross_language_only 10件のEN記事作成優先**: backfill queueの80件より先に、DB登録済みの10件を翻訳・公開

### 触るな（Claude lane）

- `prediction_page_builder.py`, `reader_prediction_api.py`
- `.claude/hooks/*`, `OPERATIONS_BOARD.md`, coordination files
- `AGENTS.md`, `update_operations_board.py`

---

## 後方互換性

- `append_ledger_entry()`: `skip_if_unchanged` デフォルト `False`（既存呼び出し元に影響なし）
- `append_ledger_entry()` 戻り値: `dict | None`（従来は常にdict返却。`skip_if_unchanged=True` で同一状態の場合のみNone）
- 新規3スクリプトは既存のcronに影響しない独立実行
- 全41回帰テストPASS（ローカル + VPS）
