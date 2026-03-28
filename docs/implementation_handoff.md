# 完遂エンジン（Completion Engine） — 実装ハンドオフ

**生成日**: 2026-03-28
**バージョン**: 1.0.1
**テスト結果**: 9/9 PASS

---

## 概要

完遂エンジンは「タスクが本当に完了しているか」をコードで強制する Python パッケージ。
プロンプトではなく、**型・ゲート・ステートマシン**によって不完全な完了を構造的に防ぐ。

> **設計思想**: 「完了したつもり」を技術的に不可能にする。

---

## パッケージ構造

```
completion_engine/
├── __init__.py             # Public API — 全クラスを export
├── schema.py               # データクラス・Enum 定義（唯一の真実）
├── task_resolver.py        # タスク解決（4ソース優先度）
├── state_machine.py        # 8フェーズ強制ステートマシン
├── requirement_contract.py # 要件管理（証跡なしDone不可）
├── evidence_gate.py        # 証跡ゲート（型別検証）
├── audit_gate.py           # 監査ゲート（5チェック）
├── finalization_guard.py   # 完了判定（COMPLETED/PARTIAL/BLOCKED）
├── failure_recovery.py     # 障害回復ループ（7ステップ）
└── report_generator.py     # 完了レポート生成（10セクション）
```

---

## アーキテクチャ

### Layer 1: スキーマ（schema.py）

全データ構造の定義。他モジュールはここの型だけを使う。

| 型 | 用途 |
|----|------|
| `Task` | タスク全体のコンテナ（要件・証跡・監査結果を内包） |
| `Requirement` | 個別要件（acceptance_criteria + evidences） |
| `Evidence` | 証跡（type + status + value） |
| `VerificationResult` | 検証結果（target + expected + actual + judgment） |
| `AuditResult` | 監査結果（5チェック + overall_status） |
| `FailureRecord` | 障害記録（7ステップ） |

**Phase enum（8フェーズ、順序固定）:**

```
resolve_task → extract_requirements → inspect_current_state
→ plan → implement → verify → audit → finalize
```

### Layer 2: ステートマシン（state_machine.py）

- `advance()` — 次のフェーズに進む（順序チェックあり）
- `advance_to(target)` — 隣接フェーズのみ許可（スキップで ValueError）
- `force_phase(target, reason)` — 強制移動（ロールバック時のみ使用）
- `phase_progress_bar(phase)` — ASCII 進捗バー生成

### Layer 3: 要件コントラクト（requirement_contract.py）

```python
contract = RequirementContract(task)
req = contract.add_requirement(
    text="publisher.py を修正",
    priority="critical",
    required_evidence_types=["command_output", "test_result"],
)
contract.verify_evidence(req.id, ev.id, "PASS: language=en applied")
ok, reason = contract.mark_done(req.id)  # 全証跡 VERIFIED なら True
```

- **Done の条件**: 全 Evidence が `VERIFIED` 状態
- **Blocked の条件**: `mark_blocked(req.id, "reason")` で明示的にブロック

### Layer 4: 証跡ゲート（evidence_gate.py）

型別検証ルール:

| EvidenceType | 検証ロジック |
|---|---|
| `file_exists` | `Path(value).exists()` |
| `test_result` | value に "PASS" / "OK" が含まれるか |
| `command_output` | value が非空かつ ERROR/FAIL がないか |
| `url_accessible` | HTTP 200 を返すか（requests） |
| `manual` | 非空で "confirmed" / "checked" / "verified" を含むか |
| `screenshot` | `file_exists` と同様 |
| `log_entry` | 非空かつ ERROR がないか |

### Layer 5: 監査ゲート（audit_gate.py）

5チェック、全て PASS で `completed`:

| チェック | 条件 |
|---|---|
| A1: outputs_verified | `task.required_outputs` が全て `VERIFIED` |
| A2: evidence_sufficient | 全要件に少なくとも1件の VERIFIED 証跡がある |
| A3: docs_match_implementation | `task.changed_files` が非空 |
| A4: critical_high_all_done | CRITICAL / HIGH 要件が全て DONE |
| A5: verification_results | `task.verification_results` が1件以上 |

### Layer 6: 完了判定（finalization_guard.py）

| 状態 | 条件 |
|---|---|
| `BLOCKED` | audit_result が None、または audit が BLOCKED、または CRITICAL/HIGH が BLOCKED |
| `PARTIAL` | audit が PARTIAL、または required_outputs 未達 |
| `COMPLETED` | 全チェック通過 |

### Layer 7: 障害回復（failure_recovery.py）

7ステップ（Step 1–4 は必須、Step 5–7 は任意）:

1. `phenomenon` — 何が起きたか
2. `root_cause_hypotheses` — 根本原因仮説（1件以上）
3. `fix_applied` — 適用した修正
4. `rerun_result` — 再実行結果
5. `reverification_result` — 影響範囲再検証（任意）
6. `impact_summary` — 影響整理（任意）
7. `artifact_updates` — KNOWN_MISTAKES 更新記録（任意）

### Layer 8: レポート生成（report_generator.py）

10セクション Markdown + JSON:

```
§1  Task Overview
§2  Phase Journey
§3  Requirement Summary
§4  Evidence Inventory
§5  Verification Results
§6  Audit Result
§7  Failure Records
§8  Changed Files
§9  Final Status
§10 Next Actions / Handoff Notes
```

---

## Public API（import パス）

```python
from completion_engine import (
    # Schema
    Task, Requirement, Evidence, VerificationResult, AuditResult, FailureRecord,
    # Enums
    Phase, Priority, RequirementCategory, RequirementStatus,
    EvidenceType, EvidenceStatus, FinalizationStatus, TaskSource,
    # Helpers
    task_to_dict, task_from_dict,
    # Engines
    TaskResolver, StateMachine, phase_progress_bar,
    RequirementContract, EvidenceGate, AuditGate,
    FinalizationGuard, FailureRecovery, ReportGenerator,
)
```

---

## 典型的な使用フロー

```python
# 1. タスク作成
task = Task(id="task-001", title="publisher.py 修正", ...)

# 2. ステートマシン起動
sm = StateMachine(task)
sm.advance()  # resolve_task → extract_requirements

# 3. 要件定義
contract = RequirementContract(task)
req = contract.add_requirement(
    text="publisher.py に language パラメータを追加",
    priority="critical",
    required_evidence_types=["command_output"],
)

# 4. 実装後に証跡を記録
ev = req.evidences[0]
contract.verify_evidence(req.id, ev.id, "python publisher.py → PASS: language=en applied")

# 5. 要件を Done に
ok, reason = contract.mark_done(req.id)

# 6. 監査実行
gate_ev = EvidenceGate(task)
audit = AuditGate(task)
result = audit.run_audit()

# 7. 完了判定
guard = FinalizationGuard(task)
status, reasons = guard.determine()  # "completed" / "partial" / "blocked"

# 8. レポート生成
gen = ReportGenerator(task)
md = gen.generate_markdown()
gen.save("docs/task-001-report.md")
```

---

## run_civilization_os.py との統合

`_import_engines()` に `completion_engine` を追加済み（オプション扱い）:

```python
checks = [
    ...
    ("completion_engine",  "completion_engine",  "StateMachine"),
]
```

OS 起動時のヘルスチェックで `StateMachine` のインポート可否を検証する。
（必須エンジンではないため、インポート失敗でも OS 起動は続行可能）

---

## 既知の制約・注意事項

1. **`EvidenceType.url_accessible`**: `requests` ライブラリが必要。未インストールの場合は `incomplete` 扱いになる
2. **`FinalizationGuard.determine()`**: `COMPLETED` 判定と同時に `task.finalization_status` を自動更新する副作用がある
3. **`AuditGate.run_audit()`**: `task.audit_result` を直接書き換える（イミュータブルではない）
4. **`task_from_dict()`**: 入れ子の AuditResult / FailureRecord は部分的にしか復元されない（ネスト深い型は手動で対応が必要）
5. **フェーズスキップ**: `StateMachine.force_phase()` は緊急ロールバック専用。通常フローでは使用しない

---

## 今後の拡張候補

| 機能 | 優先度 | 備考 |
|------|--------|------|
| SQLite 永続化 | HIGH | 現在はメモリのみ。`task_to_dict()` でJSON保存は可能 |
| タスク一覧管理 | MEDIUM | 複数タスクのダッシュボード |
| Telegram 通知連携 | MEDIUM | 完了/ブロック時に自動通知 |
| Ghost 記事への自動挿入 | LOW | §7 Failure Records を ORACLE STATEMENT と連動 |
| Brier Score 統合 | LOW | 予測タスクの精度を完遂エンジンでトラック |

---

*完遂エンジン v1.0.1 — 2026-03-28 実装完了、9/9 PASS 確認済み*
