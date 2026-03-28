# 完遂エンジン — テスト結果レポート

**実行日**: 2026-03-28
**スクリプト**: `tests/test_completion_engine.py`
**結果**: **9/9 PASS** ✅

---

## サマリー

```
============================================================
  完遂エンジン — テストスイート (9シナリオ)
============================================================
  ✅ PASS: T1: StateMachine — フェーズ強制 + 不正遷移ブロック
  ✅ PASS: T2: RequirementContract — 証跡なしDone不可・全VERIFIED後Done可
  ✅ PASS: T3: EvidenceGate — FILE_EXISTS 実ファイル検証
  ✅ PASS: T4: AuditGate — CRITICAL要件未完了でBLOCKED、全完了でCOMPLETED
  ✅ PASS: T5: FinalizationGuard — 機械的な完了判定
  ✅ PASS: T6: FailureRecovery — 7ステップ全記録でRESOLVED可
  ✅ PASS: T7: ReportGenerator — Markdown/JSON生成 + task_to_dict往復
  ✅ PASS: T8: TaskResolver — 空入力/プレースホルダー検出 + フォールスルー
  ✅ PASS: T9: 全8フェーズ ハッピーパスシナリオ (resolve_task → finalize)

============================================================
  Results: 9/9 PASS  |  0 FAIL
============================================================
```

---

## テスト別詳細

### T1: StateMachine — フェーズ強制 + 不正遷移ブロック

**検証内容:**
- `resolve_task` → `extract_requirements` → `inspect_current_state` の正常遷移
- `advance_to(Phase.FINALIZE)` のフェーズスキップが `ValueError` を発生させること
- `phase_progress_bar()` が `implement` フェーズで ASCII バーを返すこと

**確認済み挙動:**
- 隣接フェーズのみ `advance_to()` で許可される
- スキップ試行時のエラーメッセージに `"skip"` / `"adjacent"` / `"only"` が含まれる
- `phase_progress_bar("implement")` → `[████▓░░░] IMP (5/8)` 形式の文字列

---

### T2: RequirementContract — 証跡なしDone不可・全VERIFIED後Done可

**検証内容:**
- 証跡 UNVERIFIED の状態で `mark_done()` が失敗すること
- 証跡 1件 VERIFIED / 1件 UNVERIFIED の状態でも `mark_done()` が失敗すること
- 全証跡 VERIFIED で `mark_done()` が成功すること
- `get_summary()` が正確な件数を返すこと

**確認済み挙動:**
- `ok=False` + エラーメッセージに `"unverified"` または `"VERIFIED"` が含まれる
- 全 VERIFIED → `req.status == "done"` に更新される
- `summary["all_critical_high_done"] == True`

---

### T3: EvidenceGate — FILE_EXISTS 実ファイル検証

**検証内容:**
- 実在するファイル（テストファイル自体）の `FILE_EXISTS` 証跡が PASS すること
- 存在しないパスの証跡が FAIL すること

**確認済み挙動:**
- `Path(__file__).resolve()` を証跡値に設定 → `gate.check_requirement()` が `(True, [])`
- 非存在パスに変更 → `(False, [failure_message])`

---

### T4: AuditGate — CRITICAL要件未完了でBLOCKED、全完了でCOMPLETED

**検証内容:**
- CRITICAL 要件が PENDING の状態で監査 → `"blocked"` になること
- CRITICAL 要件を Done にして再監査 → `"completed"` または `"partial"` になること
- `task.audit_result` が設定されること

**確認済み挙動:**
- A4 (critical_high_all_done) が False → `overall_status = "blocked"`
- `EvidenceGate.build_verification_result()` でVerificationResultを追加後、証跡をVERIFIEDにしてDone → `overall_status in ("completed", "partial")`
- `task.audit_result is not None`

---

### T5: FinalizationGuard — 機械的な完了判定

**検証内容:**
- `audit_result = None` → `BLOCKED`
- `audit_result.overall_status = "partial"` → `PARTIAL`
- `audit_result.overall_status = "completed"` (全フィールドTrue) → `COMPLETED`

**確認済み挙動:**
- `FinalizationGuard(task).determine()` が `(status_value, reasons)` を返す
- `COMPLETED` 判定後、`task.finalization_status == "completed"` に自動更新される

---

### T6: FailureRecovery — 7ステップ全記録でRESOLVED可

**検証内容:**
- `open_failure()` で障害を開いた直後は `resolved = False`
- Step 2–4 未完了で `resolve()` → 失敗
- Step 1–4 全て記録後に `resolve()` → 成功
- `get_summary()` が正確な件数を返すこと
- `format_failure()` が `"RESOLVED"` を含む文字列を返すこと

**確認済み挙動:**
- `rec.id.startswith("fail-")`
- Step 2 未実施で `resolve()` → `(False, "missing steps: ...")`
- 全ステップ後 `resolve()` → `(True, "")`、`rec.resolved = True`、`rec.resolved_at is not None`
- `"FileNotFoundError"` が `format_failure()` 出力に含まれる

---

### T7: ReportGenerator — Markdown/JSON生成 + task_to_dict往復

**検証内容:**
- `generate_markdown()` が §1〜§10 を含む文字列を返すこと
- `generate_json()` が `task` / `summary` キーを含む dict を返すこと
- `task_to_dict()` / `task_from_dict()` の往復後にデータが保持されること

**確認済み挙動:**
- Markdown に `"§1"` と `"§10"` が含まれる
- Markdown に `"COMPLETED"` と `task.title` が含まれる
- `json_report["summary"]["finalization_status"] == "completed"`
- `task2.id == task.id`、`task2.title == task.title`、`task2.finalization_status == task.finalization_status`
- `len(task2.requirements) == len(task.requirements)`
- 追加ログ例: `Markdown: 3842 chars, JSON keys: ['generated_at', 'task', 'summary']`

---

---

### T8: TaskResolver — 空入力/プレースホルダー検出 + フォールスルー

**検証内容:**
- `_is_placeholder("")` が `True` を返すこと
- `_is_placeholder("[ここにタスクを書く]")` が `True` を返すこと
- `_is_placeholder("<TASK_INPUT>\n</TASK_INPUT>")` が `True` を返すこと
- 具体的な入力では `False` を返すこと
- `_extract_task_input_content()` が `<TASK_INPUT>` タグを除去すること
- explicit_task_input がある場合は `TaskSource.EXPLICIT_TASK_INPUT` で解決されること
- 空入力かつアクティブタスクがない場合は BLOCKED になること

**確認済み挙動:**
- `_is_placeholder("", "   ", "<TASK_INPUT>...</TASK_INPUT>", "[ここ...]", "[Insert...]")` → `True`
- `_is_placeholder("publisher.py の language パラメータを修正")` → `False`
- explicit 入力あり → `task.source == "explicit_task_input"`, `task.id.startswith("CE-")`
- 空入力 → `"concrete task missing"` を含む blocked_reason

---

### T9: 全8フェーズ ハッピーパスシナリオ (resolve_task → finalize)

**検証内容:**
- `resolve_task → extract_requirements → inspect_current_state → plan → implement → verify → audit → finalize` の8フェーズ全遷移
- `verify → audit` 前に `EvidenceGate.build_verification_result()` で VerificationResult を追加
- `audit → finalize` 前に `AuditGate.run_audit()` を実行
- 最終フェーズで `phase_progress_bar("finalize")` が `FIN (8/8)` を含む文字列を返すこと
- `FinalizationGuard.determine()` が `"completed"` または `"partial"` を返すこと

**確認済み挙動:**
- 各 `sm.advance()` 後に `task.phase` が次のフェーズ値に更新される
- `vr.judgment == "pass"` / `len(task.verification_results) == 1`
- `task.audit_result is not None` / `result.overall_status in ("completed", "partial")`
- `task.phase == "finalize"` に到達後 `[███████▓] FIN (8/8)` が返る
- `final_status in ("completed", "partial")` / `task.finalization_status == final_status`

---

## テスト中に発見・修正したバグ

### Bug 1: Phase enum 名の不一致（T1）

| 項目 | 内容 |
|------|------|
| **症状** | `AttributeError: type object 'Phase' has no attribute 'CLARIFY_REQUIREMENTS'` |
| **原因** | テストが `Phase.CLARIFY_REQUIREMENTS` を使用していたが、実際の値は `Phase.EXTRACT_REQUIREMENTS` |
| **修正** | `Phase.EXTRACT_REQUIREMENTS`、`Phase.INSPECT_CURRENT_STATE` に修正。`sm.advance()` 呼び出し回数も調整 |

### Bug 2: AuditResult の存在しないフィールド（T5, T7）

| 項目 | 内容 |
|------|------|
| **症状** | `TypeError: AuditResult.__init__() got an unexpected keyword argument 'verification_results_exist'` |
| **原因** | テストが `verification_results_exist=True/False` を使用していたが、`AuditResult` にそのフィールドは存在しない |
| **修正** | `verification_results_exist` を削除し、必須フィールド `task_id=task.id` を追加 |

---

## 実行方法

```bash
# Windows (プロジェクトルートから)
"/c/Program Files/Python312/python.exe" tests/test_completion_engine.py

# または pytest
"/c/Program Files/Python312/python.exe" -m pytest tests/test_completion_engine.py -v
```

---

*テスト結果 v1.0.1 — 2026-03-28 9/9 PASS 確認済み（T8+T9追加）*
