#!/usr/bin/env python3
"""
tests/test_completion_engine.py
完遂エンジン — 7テストシナリオ

実行方法:
    python tests/test_completion_engine.py
    python -m pytest tests/test_completion_engine.py -v
"""
from __future__ import annotations

import sys
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from completion_engine import (
    Task,
    Requirement,
    Evidence,
    Phase,
    Priority,
    RequirementStatus,
    EvidenceType,
    EvidenceStatus,
    FinalizationStatus,
    TaskSource,
    StateMachine,
    RequirementContract,
    EvidenceGate,
    AuditGate,
    FinalizationGuard,
    FailureRecovery,
    ReportGenerator,
    phase_progress_bar,
    task_to_dict,
    task_from_dict,
)


# ==============================
# Test Infrastructure
# ==============================

_results: list[tuple[str, bool, str]] = []


def _make_task(title: str = "テストタスク", phase: str = Phase.IMPLEMENT.value) -> Task:
    """テスト用Taskを生成する"""
    now = datetime.now(timezone.utc).isoformat()
    return Task(
        id="task-test-001",
        title=title,
        raw_input="テスト入力",
        source=TaskSource.EXPLICIT_TASK_INPUT.value,
        phase=phase,
        status="active",
        created_at=now,
        updated_at=now,
    )


def run_test(name: str):
    """テストデコレータ"""
    def decorator(fn):
        def wrapper():
            try:
                fn()
                _results.append((name, True, "PASS"))
                print(f"  ✅ PASS: {name}")
            except AssertionError as e:
                _results.append((name, False, f"FAIL: {e}"))
                print(f"  ❌ FAIL: {name} — {e}")
            except Exception as e:
                tb = traceback.format_exc()
                _results.append((name, False, f"ERROR: {e}\n{tb}"))
                print(f"  💥 ERROR: {name} — {e}")
        return wrapper
    return decorator


# ==============================
# Test 1: State Machine Phase Enforcement
# ==============================

@run_test("T1: StateMachine — フェーズ強制 + 不正遷移ブロック")
def test_state_machine():
    task = _make_task(phase=Phase.RESOLVE_TASK.value)
    sm = StateMachine(task)

    # 正常遷移: resolve_task → extract_requirements
    sm.advance()
    assert task.phase == Phase.EXTRACT_REQUIREMENTS.value, f"Expected extract_requirements, got {task.phase}"

    # 正常遷移: extract_requirements → inspect_current_state
    sm.advance()
    assert task.phase == Phase.INSPECT_CURRENT_STATE.value, f"Expected inspect_current_state, got {task.phase}"

    # advance_to でスキップを試みる → ValueError
    try:
        sm.advance_to(Phase.FINALIZE.value)
        assert False, "Should have raised ValueError for phase skip"
    except ValueError as e:
        assert "skip" in str(e).lower() or "adjacent" in str(e).lower() or "only" in str(e).lower(), \
            f"Wrong error message: {e}"

    # 正常にIMPLEMENTまで進める
    sm.advance()  # inspect → plan
    sm.advance()  # plan → implement
    assert task.phase == Phase.IMPLEMENT.value

    # phase_progress_bar が文字列を返すことを確認
    bar = phase_progress_bar(Phase.IMPLEMENT.value)
    assert isinstance(bar, str)
    assert "IMP" in bar or "implement" in bar.lower() or "█" in bar

    print(f"      progress bar: {bar}")


# ==============================
# Test 2: Requirement Contract — Evidence-based Done
# ==============================

@run_test("T2: RequirementContract — 証跡なしDone不可・全VERIFIED後Done可")
def test_requirement_contract():
    task = _make_task()
    contract = RequirementContract(task)

    # 要件追加
    req = contract.add_requirement(
        text="publisher.py を修正して language パラメータを渡す",
        category="implementation",
        priority="critical",
        acceptance_criteria=["language=_pub_lang が渡される", "ENタグが正しく付く"],
        required_evidence_types=["command_output", "test_result"],
    )
    assert req.id is not None
    assert len(req.evidences) == 2
    assert req.status == RequirementStatus.PENDING.value

    # 証跡が UNVERIFIED のまま Done を試みる → 失敗
    ok, reason = contract.mark_done(req.id)
    assert not ok, "Should fail without verified evidence"
    assert "unverified" in reason.lower() or "VERIFIED" in reason

    # 1件目の証跡を VERIFIED に
    ev1 = req.evidences[0]
    contract.verify_evidence(req.id, ev1.id, "python publisher.py → PASS, EN tag applied")

    # まだ1件 UNVERIFIED → Done 不可
    ok, reason = contract.mark_done(req.id)
    assert not ok

    # 2件目も VERIFIED に
    ev2 = req.evidences[1]
    contract.verify_evidence(req.id, ev2.id, "PASS: language=en applied correctly")

    # 全 VERIFIED → Done 可
    ok, reason = contract.mark_done(req.id)
    assert ok, f"Should succeed with all verified: {reason}"
    assert req.status == RequirementStatus.DONE.value

    # summary 確認
    summary = contract.get_summary()
    assert summary["done"] == 1
    assert summary["total"] == 1
    assert summary["all_critical_high_done"] is True


# ==============================
# Test 3: Evidence Gate — File Exists Check
# ==============================

@run_test("T3: EvidenceGate — FILE_EXISTS 実ファイル検証")
def test_evidence_gate():
    task = _make_task()
    contract = RequirementContract(task)

    # FILE_EXISTS 証跡を持つ要件を作る
    req = contract.add_requirement(
        text="スクリプトが存在することを確認",
        priority="high",
        required_evidence_types=["file_exists"],
    )
    ev = req.evidences[0]

    # 存在するファイルをセット（このテストファイル自体）
    this_file = str(Path(__file__).resolve())
    contract.verify_evidence(req.id, ev.id, this_file)

    gate = EvidenceGate(task)
    ok, failures = gate.check_requirement(req.id)
    assert ok, f"FILE_EXISTS check failed: {failures}"

    # 存在しないファイルに変更
    ev.value = "/path/that/does/not/exist/anywhere.py"

    gate2 = EvidenceGate(task)
    ok2, failures2 = gate2.check_requirement(req.id)
    assert not ok2, "Should fail for non-existent file"
    assert len(failures2) > 0


# ==============================
# Test 4: Audit Gate — BLOCKED / COMPLETED 判定
# ==============================

@run_test("T4: AuditGate — CRITICAL要件未完了でBLOCKED、全完了でCOMPLETED")
def test_audit_gate():
    task = _make_task()
    contract = RequirementContract(task)
    gate_ev = EvidenceGate(task)

    # CRITICAL 要件を追加
    req = contract.add_requirement(
        text="主要機能の実装",
        priority="critical",
        required_evidence_types=["manual"],
    )

    # CRITICAL が未完了の状態で監査 → BLOCKED
    audit = AuditGate(task)
    result = audit.run_audit()
    assert result.overall_status == "blocked", f"Expected blocked, got {result.overall_status}"

    # verification_result を追加してから再監査
    gate_ev.build_verification_result(
        req_id=req.id,
        target="publisher.py:42",
        method="manual_review",
        expected="language param passed",
        actual="PASS — language=en passed",
        evidence_text="confirmed manually",
    )

    # 証跡を VERIFIED にして Done にする
    ev = req.evidences[0]
    contract.verify_evidence(req.id, ev.id, "manual check passed")
    ok, _ = contract.mark_done(req.id)
    assert ok

    # 監査 → A4（CRITICAL全Done）+ A5（VerificationResult存在）→ COMPLETED
    result2 = audit.run_audit()
    # A1（required_outputs）が空 → COMPLETED になる
    assert result2.overall_status in ("completed", "partial"), \
        f"Expected completed or partial, got {result2.overall_status}"
    assert task.audit_result is not None


# ==============================
# Test 5: Finalization Guard — COMPLETED / PARTIAL / BLOCKED 判定
# ==============================

@run_test("T5: FinalizationGuard — 機械的な完了判定")
def test_finalization_guard():
    task = _make_task()

    # audit_result が None → BLOCKED
    guard = FinalizationGuard(task)
    status, reasons = guard.determine()
    assert status == FinalizationStatus.BLOCKED.value
    assert len(reasons) > 0

    # 手動で PARTIAL な audit_result を設定
    from completion_engine.schema import AuditResult
    task.audit_result = AuditResult(
        task_id=task.id,
        overall_status="partial",
        audited_at=datetime.now(timezone.utc).isoformat(),
        outputs_verified=False,
        evidence_sufficient=True,
        docs_match_implementation=True,
        critical_high_all_done=True,
        failures=["A1: outputs not verified"],
    )

    guard2 = FinalizationGuard(task)
    status2, reasons2 = guard2.determine()
    assert status2 == FinalizationStatus.PARTIAL.value, \
        f"Expected partial, got {status2}"

    # COMPLETED な audit_result に変更
    task.audit_result = AuditResult(
        task_id=task.id,
        overall_status="completed",
        audited_at=datetime.now(timezone.utc).isoformat(),
        outputs_verified=True,
        evidence_sufficient=True,
        docs_match_implementation=True,
        critical_high_all_done=True,
        failures=[],
    )

    guard3 = FinalizationGuard(task)
    status3, reasons3 = guard3.determine()
    assert status3 == FinalizationStatus.COMPLETED.value, \
        f"Expected completed, got {status3}: {reasons3}"
    assert task.finalization_status == FinalizationStatus.COMPLETED.value


# ==============================
# Test 6: Failure Recovery — 7ステップ追跡
# ==============================

@run_test("T6: FailureRecovery — 7ステップ全記録でRESOLVED可")
def test_failure_recovery():
    task = _make_task()
    recovery = FailureRecovery(task)

    # 障害を開く
    rec = recovery.open_failure(
        phase=Phase.IMPLEMENT.value,
        phenomenon="FileNotFoundError in publisher.py:42 — path not found",
    )
    assert rec.id.startswith("fail-")
    assert rec.resolved is False

    # Steps 1-4 のみで resolve → 失敗（Step 2〜4 が不足）
    ok, msg = recovery.resolve(rec.id)
    assert not ok, "Should fail without all required steps"
    assert "missing" in msg.lower() or "step" in msg.lower()

    # Step 2: 仮説
    recovery.add_hypothesis(rec.id, "パスが絶対パスではなく相対パスで指定されていた")
    recovery.add_hypothesis(rec.id, "環境変数 BASE_DIR が本番では未設定")

    # Step 3: 修正
    recovery.apply_fix(rec.id, "publisher.py のパス解決を Path(__file__).parent / 'data' に変更")

    # Step 4: 再実行結果
    recovery.record_rerun(rec.id, "PASS — 5件投稿成功、エラーなし")

    # Step 1-4 揃ったので resolve 成功
    ok, msg = recovery.resolve(rec.id)
    assert ok, f"Should succeed with steps 1-4: {msg}"
    assert rec.resolved is True
    assert rec.resolved_at is not None

    # サマリー確認
    summary = recovery.get_summary()
    assert summary["total"] == 1
    assert summary["resolved"] == 1
    assert summary["open"] == 0

    # format_failure が文字列を返すこと確認
    formatted = recovery.format_failure(rec.id)
    assert "RESOLVED" in formatted
    assert "FileNotFoundError" in formatted


# ==============================
# Test 7: Report Generator + JSON Serialization
# ==============================

@run_test("T7: ReportGenerator — Markdown/JSON生成 + task_to_dict往復")
def test_report_generator():
    task = _make_task(title="完遂エンジン統合テスト")

    # 要件・証跡を設定
    contract = RequirementContract(task)
    req = contract.add_requirement(
        text="integration_test.py を作成して全テストがPASS",
        priority="high",
        required_evidence_types=["test_result"],
    )
    ev = req.evidences[0]
    contract.verify_evidence(req.id, ev.id, "PASS: 7/7 tests passed")
    contract.mark_done(req.id)

    # audit_result を設定
    from completion_engine.schema import AuditResult
    task.audit_result = AuditResult(
        task_id=task.id,
        overall_status="completed",
        audited_at=datetime.now(timezone.utc).isoformat(),
        outputs_verified=True,
        evidence_sufficient=True,
        docs_match_implementation=True,
        critical_high_all_done=True,
        failures=[],
    )
    task.finalization_status = FinalizationStatus.COMPLETED.value

    # Markdown生成
    gen = ReportGenerator(task)
    md = gen.generate_markdown()
    assert isinstance(md, str)
    assert "§1" in md
    assert "§10" in md
    assert "COMPLETED" in md
    assert task.title in md

    # JSON生成
    json_report = gen.generate_json()
    assert "task" in json_report
    assert "summary" in json_report
    assert json_report["summary"]["finalization_status"] == "completed"

    # task_to_dict / task_from_dict の往復
    d = task_to_dict(task)
    assert isinstance(d, dict)
    assert d["id"] == task.id

    task2 = task_from_dict(d)
    assert task2.id == task.id
    assert task2.title == task.title
    assert task2.finalization_status == task.finalization_status
    assert len(task2.requirements) == len(task.requirements)

    print(f"      Markdown: {len(md)} chars, JSON keys: {list(json_report.keys())}")


# ==============================
# Test 8: TaskResolver — Empty/Placeholder Input
# ==============================

@run_test("T8: TaskResolver — 空入力/プレースホルダー検出 + フォールスルー")
def test_task_resolver():
    from completion_engine.task_resolver import (
        _is_placeholder,
        _extract_task_input_content,
        TaskResolver as TR,
    )

    # プレースホルダー検出
    assert _is_placeholder("") is True, "空文字はplaceholder"
    assert _is_placeholder("   ") is True, "スペースのみはplaceholder"
    assert _is_placeholder("<TASK_INPUT>\n</TASK_INPUT>") is True, "空タグはplaceholder"
    assert _is_placeholder("[ここにタスクを書く]") is True, "日本語プレースホルダー"
    assert _is_placeholder("[Insert task here]") is True, "英語プレースホルダー"
    assert _is_placeholder("publisher.py の language パラメータを修正") is False, "実タスクはplaceholderでない"

    # タグ抽出
    content = _extract_task_input_content("<TASK_INPUT>実装タスク内容</TASK_INPUT>")
    assert content == "実装タスク内容"

    content2 = _extract_task_input_content("タグなしの入力")
    assert content2 == "タグなしの入力"

    # 明示的な入力での解決
    resolver = TR(raw_input="completion_engine の統合テストを完遂させる")
    task, blocked = resolver.resolve()
    assert task is not None, "実タスク入力は解決できるはず"
    assert blocked is None
    assert task.source == TaskSource.EXPLICIT_TASK_INPUT.value
    assert task.id.startswith("CE-")

    # 空入力の場合 — active_context / handoff から解決 or BLOCKED
    resolver_empty = TR(raw_input="")
    task2, blocked2 = resolver_empty.resolve()
    if task2 is not None:
        # active_context か handoff_source から解決
        assert task2.source in (
            TaskSource.ACTIVE_CONTEXT.value,
            TaskSource.HANDOFF_SOURCE.value,
        ), f"Expected fallthrough source, got {task2.source!r}"
        assert blocked2 is None
        print(f"      empty input → resolved via source={task2.source!r}")
    else:
        # 全ソース失敗 → BLOCKED (正常な挙動)
        assert blocked2 is not None
        assert "concrete task missing" in blocked2, \
            f"Expected 'concrete task missing' in reason: {blocked2!r}"
        print(f"      empty input → BLOCKED (no active context)")


# ==============================
# Test 9: Full 8-Phase Happy Path
# ==============================

@run_test("T9: 全8フェーズ ハッピーパスシナリオ (resolve_task → finalize)")
def test_full_8_phase_happy_path():
    """全8フェーズを順序通りに通過できることを確認する"""
    task = _make_task(phase=Phase.RESOLVE_TASK.value)
    sm = StateMachine(task)

    # Phase 1: resolve_task (出発点)
    assert task.phase == Phase.RESOLVE_TASK.value

    # Phase 1 → 2: resolve_task → extract_requirements
    sm.advance()
    assert task.phase == Phase.EXTRACT_REQUIREMENTS.value

    # Phase 2 → 3: extract_requirements → inspect_current_state
    sm.advance()
    assert task.phase == Phase.INSPECT_CURRENT_STATE.value

    # Phase 3 → 4: inspect_current_state → plan
    sm.advance()
    assert task.phase == Phase.PLAN.value

    # Phase 4 → 5: plan → implement
    sm.advance()
    assert task.phase == Phase.IMPLEMENT.value

    # Phase 5 → 6: implement → verify
    sm.advance()
    assert task.phase == Phase.VERIFY.value

    # verify → audit 前に VerificationResult が1件以上必要
    gate_ev = EvidenceGate(task)
    vr = gate_ev.build_verification_result(
        req_id="happy-path-check",
        target="completion_engine/__init__.py",
        method="import_test",
        expected="module importable",
        actual="PASS — import successful",
        evidence_text="python -c 'import completion_engine' exit 0",
    )
    assert vr.judgment == "pass", f"Expected pass, got {vr.judgment}"
    assert len(task.verification_results) == 1

    # Phase 6 → 7: verify → audit (VerificationResult あるのでOK)
    sm.advance()
    assert task.phase == Phase.AUDIT.value

    # audit → finalize 前に AuditGate を実行
    audit = AuditGate(task)
    result = audit.run_audit()
    assert task.audit_result is not None
    # 要件なし + VR あり + required_outputs 空 → COMPLETED
    assert result.overall_status in ("completed", "partial"), \
        f"Expected completed or partial before finalize, got {result.overall_status}"

    # Phase 7 → 8: audit → finalize (audit が BLOCKED でなければ可)
    assert result.overall_status != "blocked", \
        f"Audit is BLOCKED — cannot finalize: {result.failures}"
    sm.advance()
    assert task.phase == Phase.FINALIZE.value, \
        f"Expected finalize, got {task.phase}"

    # progress bar が FIN (8/8) を示すことを確認
    bar = phase_progress_bar(Phase.FINALIZE.value)
    assert "FIN" in bar or "finalize" in bar.lower(), f"Expected FIN in bar: {bar}"
    assert "8/8" in bar, f"Expected 8/8 in bar: {bar}"

    # FinalizationGuard で最終判定
    guard = FinalizationGuard(task)
    final_status, reasons = guard.determine()
    assert final_status in ("completed", "partial"), \
        f"Final status should be completed or partial, got {final_status}: {reasons}"
    assert task.finalization_status == final_status

    print(f"      audit={result.overall_status}, finalization={final_status}")
    print(f"      final bar: {bar}")


# ==============================
# Main Runner
# ==============================

def main():
    print("\n" + "=" * 60)
    print("  完遂エンジン — テストスイート (9シナリオ)")
    print("=" * 60)

    tests = [
        test_state_machine,
        test_requirement_contract,
        test_evidence_gate,
        test_audit_gate,
        test_finalization_guard,
        test_failure_recovery,
        test_report_generator,
        test_task_resolver,
        test_full_8_phase_happy_path,
    ]

    for t in tests:
        t()

    # サマリー
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = len(_results) - passed

    print("\n" + "=" * 60)
    print(f"  Results: {passed}/{len(_results)} PASS  |  {failed} FAIL")
    print("=" * 60)

    if failed > 0:
        print("\nFailed tests:")
        for name, ok, msg in _results:
            if not ok:
                print(f"  ❌ {name}")
                print(f"     {msg}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
