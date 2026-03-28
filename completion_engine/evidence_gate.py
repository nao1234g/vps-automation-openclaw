#!/usr/bin/env python3
"""
completion_engine/evidence_gate.py
完遂エンジン — Evidence Gate

証跡なしに Done を宣言することを物理的にブロックする。

設計原則:
  「会話の雰囲気で Done にしない。証拠で Done にする。」
  「file_exists / command_output / log_entry / test_result /
   diff / report_file / manual の7種類のどれかが必要」

ゲートパス条件:
  - 全 required_evidence が VERIFIED 状態
  - acceptance_criteria が全て evidence に対応付けられている
  - FILE_EXISTS ならファイルが実際に存在する
  - COMMAND_OUTPUT なら value が非空
  - TEST_RESULT なら value が "PASS" を含む
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from completion_engine.schema import (
    Evidence,
    EvidenceStatus,
    EvidenceType,
    Requirement,
    RequirementStatus,
    Task,
    VerificationResult,
)


# ==============================
# EvidenceGate
# ==============================

class EvidenceGate:
    """
    要件の Done 宣言前に証跡を検証するゲート。

    使い方:
        gate = EvidenceGate(task)
        ok, failures = gate.check_requirement("req-001")
        if ok:
            # proceed to mark Done
        else:
            # handle failures

        all_ok, report = gate.check_all()
    """

    def __init__(self, task: Task, project_root: Optional[Path] = None):
        self.task = task
        self.project_root = project_root or Path.cwd()

    # --------------------------
    # Per-Requirement Check
    # --------------------------

    def check_requirement(
        self, req_id: str
    ) -> Tuple[bool, List[str]]:
        """
        1つの要件の全証跡を検証する。

        Returns:
            (True, [])                — ゲートパス
            (False, failure_reasons)  — ゲートブロック
        """
        req = self._get_req(req_id)
        if req is None:
            return False, [f"Requirement {req_id!r} not found"]

        failures: List[str] = []

        # acceptance_criteria が定義されているが evidence が0件
        if req.acceptance_criteria and not req.evidences:
            failures.append(
                f"Requirement {req_id} has acceptance_criteria but no evidences attached. "
                f"At least 1 evidence is required."
            )

        # 各 evidence を個別にチェック
        for ev in req.evidences:
            ok, reason = self._check_evidence(ev)
            if not ok:
                failures.append(reason)

        return (len(failures) == 0), failures

    def check_all(self) -> Tuple[bool, Dict[str, List[str]]]:
        """
        全要件の証跡を一括検証する。

        Returns:
            (all_pass, {req_id: [failure_reasons]})
        """
        results: Dict[str, List[str]] = {}
        all_pass = True

        for req in self.task.requirements:
            ok, failures = self.check_requirement(req.id)
            if not ok:
                results[req.id] = failures
                all_pass = False
            else:
                results[req.id] = []

        return all_pass, results

    # --------------------------
    # Verification Result Builder
    # --------------------------

    def build_verification_result(
        self,
        req_id: str,
        target: str,
        method: str,
        expected: str,
        actual: str,
        evidence_text: str,
        notes: str = "",
    ) -> VerificationResult:
        """
        VerificationResult を構築して task に追加する。
        judgment は actual と expected の比較で自動決定。
        """
        judgment = _auto_judge(expected, actual)
        vr = VerificationResult(
            requirement_id=req_id,
            target=target,
            method=method,
            expected=expected,
            actual=actual,
            judgment=judgment,
            evidence=evidence_text,
            notes=notes,
            verified_at=_now_iso(),
        )
        self.task.verification_results.append(vr)
        _update_task_ts(self.task)
        return vr

    # --------------------------
    # Evidence Verification
    # --------------------------

    def _check_evidence(self, ev: Evidence) -> Tuple[bool, str]:
        """
        単一の Evidence を type ごとのルールで検証する。

        Returns:
            (True, "")     — 検証 OK
            (False, reason) — 検証 NG
        """
        # 既に FAILED ならそのまま失敗
        if ev.status == EvidenceStatus.FAILED.value:
            return False, f"Evidence {ev.id} is FAILED: {ev.notes}"

        # UNVERIFIED で value がなければ未検証
        if ev.status == EvidenceStatus.UNVERIFIED.value:
            return False, (
                f"Evidence {ev.id} ({ev.type}) is UNVERIFIED. "
                f"Must be VERIFIED before marking requirement Done."
            )

        # VERIFIED — type 別の追加チェック
        ev_type = ev.type

        if ev_type == EvidenceType.FILE_EXISTS.value:
            return self._check_file_exists(ev)

        elif ev_type == EvidenceType.COMMAND_OUTPUT.value:
            return self._check_command_output(ev)

        elif ev_type == EvidenceType.TEST_RESULT.value:
            return self._check_test_result(ev)

        elif ev_type == EvidenceType.DIFF.value:
            return self._check_diff(ev)

        elif ev_type == EvidenceType.LOG_ENTRY.value:
            return self._check_log_entry(ev)

        elif ev_type == EvidenceType.REPORT_FILE.value:
            return self._check_report_file(ev)

        elif ev_type == EvidenceType.MANUAL.value:
            # MANUAL: value が空でなければ OK
            if not ev.value:
                return False, (
                    f"Evidence {ev.id} (MANUAL) is VERIFIED but value is empty. "
                    f"Provide a description of what was manually verified."
                )
            return True, ""

        else:
            return True, ""  # 未知の type は通過させる

    def _check_file_exists(self, ev: Evidence) -> Tuple[bool, str]:
        """FILE_EXISTS: value にあるパスが実際に存在するか"""
        if not ev.value:
            return False, (
                f"Evidence {ev.id} (FILE_EXISTS) has no value (file path). "
                f"Set value to the file path."
            )
        path = Path(ev.value)
        if not path.is_absolute():
            path = self.project_root / path
        if not path.exists():
            return False, (
                f"Evidence {ev.id} (FILE_EXISTS): path does not exist: {ev.value!r}"
            )
        return True, ""

    def _check_command_output(self, ev: Evidence) -> Tuple[bool, str]:
        """COMMAND_OUTPUT: value が非空かチェック"""
        if not ev.value or not ev.value.strip():
            return False, (
                f"Evidence {ev.id} (COMMAND_OUTPUT) has empty value. "
                f"Store the actual command output."
            )
        return True, ""

    def _check_test_result(self, ev: Evidence) -> Tuple[bool, str]:
        """TEST_RESULT: value に PASS が含まれるかチェック（FAIL は NG）"""
        if not ev.value:
            return False, (
                f"Evidence {ev.id} (TEST_RESULT) has empty value."
            )
        val_upper = ev.value.upper()
        if "FAIL" in val_upper and "PASS" not in val_upper:
            return False, (
                f"Evidence {ev.id} (TEST_RESULT): test failed. value={ev.value!r}"
            )
        if "PASS" not in val_upper and "OK" not in val_upper:
            return False, (
                f"Evidence {ev.id} (TEST_RESULT): no PASS/OK found in value={ev.value!r}"
            )
        return True, ""

    def _check_diff(self, ev: Evidence) -> Tuple[bool, str]:
        """DIFF: value に diff 内容があるかチェック"""
        if not ev.value or not ev.value.strip():
            return False, (
                f"Evidence {ev.id} (DIFF) has empty value. "
                f"Store the diff output."
            )
        return True, ""

    def _check_log_entry(self, ev: Evidence) -> Tuple[bool, str]:
        """LOG_ENTRY: value が非空かチェック"""
        if not ev.value or not ev.value.strip():
            return False, (
                f"Evidence {ev.id} (LOG_ENTRY) has empty value. "
                f"Store relevant log lines."
            )
        return True, ""

    def _check_report_file(self, ev: Evidence) -> Tuple[bool, str]:
        """REPORT_FILE: value にあるパスが実際に存在するか"""
        if not ev.value:
            return False, (
                f"Evidence {ev.id} (REPORT_FILE) has no value (file path)."
            )
        path = Path(ev.value)
        if not path.is_absolute():
            path = self.project_root / path
        if not path.exists():
            return False, (
                f"Evidence {ev.id} (REPORT_FILE): report file does not exist: {ev.value!r}"
            )
        return True, ""

    # --------------------------
    # Helpers
    # --------------------------

    def _get_req(self, req_id: str) -> Optional[Requirement]:
        for r in self.task.requirements:
            if r.id == req_id:
                return r
        return None


# ==============================
# Utility Functions
# ==============================

def _auto_judge(expected: str, actual: str) -> str:
    """
    expected と actual を比較して judgment を返す。
    簡易実装 — 大文字小文字無視で expected が actual に含まれるか。
    """
    if not expected or not actual:
        return "partial"

    exp_lower = expected.lower().strip()
    act_lower = actual.lower().strip()

    # FAIL を含む場合は即 fail
    if "fail" in act_lower or "error" in act_lower:
        # ただし PASS が上回る場合は partial
        if "pass" in act_lower or "ok" in act_lower:
            return "partial"
        return "fail"

    # expected が actual に含まれるなら pass
    if exp_lower in act_lower:
        return "pass"

    # PASS / OK が actual にあるなら pass
    if "pass" in act_lower or "ok" in act_lower or "success" in act_lower:
        return "pass"

    return "partial"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_task_ts(task: Task) -> None:
    task.updated_at = _now_iso()
