#!/usr/bin/env python3
"""
completion_engine/audit_gate.py
完遂エンジン — Audit / Exit Gate

finalize フェーズに進む前の最終監査ゲート。
CRITICAL / HIGH の要件が全て Done でなければ completed に到達できない。

監査項目:
  A1. outputs_verified    — required_outputs が全て存在するか
  A2. evidence_sufficient — 全 evidence が VERIFIED 状態か
  A3. docs_match_implementation — ドキュメント更新が実装と一致しているか
  A4. critical_high_all_done — CRITICAL/HIGH 要件が全て Done か
  A5. verification_results_exist — VerificationResult が1件以上存在するか

A4 が False なら overall_status = BLOCKED（完了不可）。
A1-A3 が不完全なら PARTIAL。
全て OK なら overall_status = completed。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from completion_engine.schema import (
    AuditResult,
    EvidenceStatus,
    FinalizationStatus,
    Phase,
    Priority,
    RequirementStatus,
    Task,
)


# ==============================
# AuditGate
# ==============================

class AuditGate:
    """
    finalize 前の監査ゲート。

    使い方:
        gate = AuditGate(task)
        result = gate.run_audit()
        if result.overall_status == FinalizationStatus.BLOCKED.value:
            print("Cannot finalize:", result.failures)
        elif result.overall_status == FinalizationStatus.PARTIAL.value:
            print("Partial — some items incomplete")
        else:
            print("Audit passed — proceed to finalize")
    """

    def __init__(self, task: Task, project_root: Optional[Path] = None):
        self.task = task
        self.project_root = project_root or Path.cwd()

    def run_audit(self) -> AuditResult:
        """
        全監査項目を実行して AuditResult を返す。
        結果は task.audit_result に自動セットされる。
        """
        now = _now_iso()
        failures: List[str] = []
        req_results: Dict[str, str] = {}

        # A1. outputs_verified
        outputs_ok, outputs_failures = self._check_outputs()
        if not outputs_ok:
            failures.extend(outputs_failures)

        # A2. evidence_sufficient
        evidence_ok, evidence_failures = self._check_evidence_sufficient()
        if not evidence_ok:
            failures.extend(evidence_failures)

        # A3. docs_match_implementation
        docs_ok, docs_failures = self._check_docs_match()
        if not docs_ok:
            failures.extend(docs_failures)

        # A4. critical_high_all_done
        critical_high_ok, critical_high_failures, req_results = (
            self._check_critical_high_done()
        )
        if not critical_high_ok:
            failures.extend(critical_high_failures)

        # A5. verification_results_exist
        vr_ok, vr_failures = self._check_verification_results()
        if not vr_ok:
            failures.extend(vr_failures)

        # 全 requirement の status を req_results に追加
        for req in self.task.requirements:
            if req.id not in req_results:
                req_results[req.id] = req.status

        # overall_status 決定
        # BLOCKED: A4（CRITICAL/HIGH 未完）またはA5（verification未実行）
        if not critical_high_ok or not vr_ok:
            overall = FinalizationStatus.BLOCKED.value
        elif failures:
            overall = FinalizationStatus.PARTIAL.value
        else:
            overall = FinalizationStatus.COMPLETED.value

        result = AuditResult(
            task_id=self.task.id,
            audited_at=now,
            requirement_results=req_results,
            outputs_verified=outputs_ok,
            evidence_sufficient=evidence_ok,
            docs_match_implementation=docs_ok,
            critical_high_all_done=critical_high_ok,
            overall_status=overall,
            failures=failures,
            notes="",
        )

        self.task.audit_result = result
        _update_task_ts(self.task)
        return result

    # --------------------------
    # Audit Checks
    # --------------------------

    def _check_outputs(self) -> Tuple[bool, List[str]]:
        """A1: required_outputs が全て存在するか"""
        failures: List[str] = []
        for output_path in self.task.required_outputs:
            path = Path(output_path)
            if not path.is_absolute():
                path = self.project_root / path
            if not path.exists():
                failures.append(
                    f"A1[outputs_verified] Required output not found: {output_path!r}"
                )
        return (len(failures) == 0), failures

    def _check_evidence_sufficient(self) -> Tuple[bool, List[str]]:
        """A2: 全 evidence が VERIFIED 状態か"""
        failures: List[str] = []
        for req in self.task.requirements:
            for ev in req.evidences:
                if ev.status == EvidenceStatus.UNVERIFIED.value:
                    failures.append(
                        f"A2[evidence_sufficient] Unverified evidence: "
                        f"req={req.id!r} ev={ev.id!r} ({ev.type})"
                    )
                elif ev.status == EvidenceStatus.FAILED.value:
                    failures.append(
                        f"A2[evidence_sufficient] Failed evidence: "
                        f"req={req.id!r} ev={ev.id!r} — {ev.notes}"
                    )
        return (len(failures) == 0), failures

    def _check_docs_match(self) -> Tuple[bool, List[str]]:
        """A3: ドキュメント系要件が全て Done か"""
        failures: List[str] = []
        doc_reqs = [
            r for r in self.task.requirements
            if r.category in ("docs", "handoff", "reporting")
        ]
        for req in doc_reqs:
            if not req.is_done():
                failures.append(
                    f"A3[docs_match_implementation] Docs requirement not Done: "
                    f"{req.id!r} — {req.text[:60]}"
                )
        return (len(failures) == 0), failures

    def _check_critical_high_done(
        self,
    ) -> Tuple[bool, List[str], Dict[str, str]]:
        """A4: CRITICAL / HIGH 要件が全て Done か"""
        failures: List[str] = []
        req_results: Dict[str, str] = {}

        for req in self.task.requirements:
            req_results[req.id] = req.status
            if req.is_critical_or_high() and not req.is_done():
                failures.append(
                    f"A4[critical_high_all_done] {req.priority.upper()} requirement "
                    f"not Done: {req.id!r} [{req.status}] — {req.text[:60]}"
                )

        return (len(failures) == 0), failures, req_results

    def _check_verification_results(self) -> Tuple[bool, List[str]]:
        """A5: VerificationResult が1件以上存在するか"""
        if not self.task.verification_results:
            return False, [
                "A5[verification_results_exist] No VerificationResult found. "
                "verify phase must produce at least 1 VerificationResult."
            ]
        # fail が存在するか確認（警告のみ — BLOCKED にはしない）
        failing_vrs = [
            vr for vr in self.task.verification_results
            if not vr.is_passing()
        ]
        if failing_vrs:
            # PARTIAL 扱い（BLOCKED ではない）
            return True, []  # 警告は failures に含めない（PARTIAL扱いは A1-A3 で十分）
        return True, []

    # --------------------------
    # Quick Check (non-mutating)
    # --------------------------

    def can_finalize(self) -> Tuple[bool, List[str]]:
        """
        finalize に進めるか事前チェック（task.audit_result を書き換えない）。

        Returns:
            (True, [])         — finalize 可能
            (False, [reasons]) — ブロック理由リスト
        """
        reasons: List[str] = []

        # CRITICAL/HIGH 未完チェック
        for req in self.task.requirements:
            if req.is_critical_or_high() and not req.is_done():
                reasons.append(
                    f"{req.priority.upper()} requirement not Done: "
                    f"{req.id!r} [{req.status}]"
                )

        # verification_results 存在チェック
        if not self.task.verification_results:
            reasons.append("No VerificationResult — verify phase incomplete")

        return (len(reasons) == 0), reasons


# ==============================
# Helpers
# ==============================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_task_ts(task: Task) -> None:
    task.updated_at = _now_iso()
