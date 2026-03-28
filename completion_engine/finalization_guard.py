#!/usr/bin/env python3
"""
completion_engine/finalization_guard.py
完遂エンジン — Finalization Guard

Task の最終ステータスを機械的に決定する。
「完了した気がする」ではなく「audit_result + requirement_results から計算する」。

判定ロジック:
  COMPLETED: audit_result.overall_status == "completed"
             AND all CRITICAL/HIGH requirements are Done
  PARTIAL:   audit_result.overall_status == "partial"
             OR some CRITICAL/HIGH done but not all
  BLOCKED:   audit_result.overall_status == "blocked"
             OR any CRITICAL/HIGH requirement is BLOCKED
             OR audit_result is None
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from completion_engine.schema import (
    AuditResult,
    FinalizationStatus,
    Phase,
    Priority,
    RequirementStatus,
    Task,
)


# ==============================
# FinalizationGuard
# ==============================

class FinalizationGuard:
    """
    Task の完了ステータスを機械的に判定する。

    使い方:
        guard = FinalizationGuard(task)
        status, reasons = guard.determine()
        # status: "completed" | "partial" | "blocked"
        task.finalization_status = status
    """

    def __init__(self, task: Task):
        self.task = task

    def determine(self) -> Tuple[str, List[str]]:
        """
        Task の finalization_status を機械的に決定して返す。
        task.finalization_status も更新する。

        Returns:
            (status, reasons)
            status: FinalizationStatus value
            reasons: PARTIAL/BLOCKED の場合の理由リスト
        """
        status, reasons = self._compute()
        self.task.finalization_status = status
        _update_task_ts(self.task)
        return status, reasons

    def _compute(self) -> Tuple[str, List[str]]:
        audit = self.task.audit_result

        # audit_result が存在しない → BLOCKED
        if audit is None:
            return FinalizationStatus.BLOCKED.value, [
                "audit_result is None — run AuditGate.run_audit() first"
            ]

        reasons: List[str] = []

        # audit 判定
        audit_status = audit.overall_status

        # CRITICAL/HIGH 要件の状態確認
        critical_high = [
            r for r in self.task.requirements
            if r.is_critical_or_high()
        ]
        critical_high_done = [r for r in critical_high if r.is_done()]
        critical_high_blocked = [r for r in critical_high if r.is_blocked()]

        # BLOCKED 判定（いずれか1つでも該当すれば BLOCKED）
        blocked_reasons: List[str] = []

        if audit_status == FinalizationStatus.BLOCKED.value:
            blocked_reasons.append(
                f"audit_result.overall_status is BLOCKED: {audit.failures}"
            )

        for req in critical_high_blocked:
            blocked_reasons.append(
                f"{req.priority.upper()} requirement BLOCKED: {req.id!r} — {req.blocker_reason}"
            )

        if blocked_reasons:
            return FinalizationStatus.BLOCKED.value, blocked_reasons

        # PARTIAL 判定
        partial_reasons: List[str] = []

        if audit_status == FinalizationStatus.PARTIAL.value:
            partial_reasons.append(
                f"audit_result.overall_status is PARTIAL: {audit.failures}"
            )

        if critical_high and len(critical_high_done) < len(critical_high):
            not_done = [r for r in critical_high if not r.is_done()]
            partial_reasons.append(
                f"{len(not_done)} CRITICAL/HIGH requirement(s) not Done: "
                f"{[r.id for r in not_done]}"
            )

        # required_outputs の未作成チェック
        missing_outputs = self._check_missing_outputs()
        if missing_outputs:
            partial_reasons.append(
                f"Missing required outputs: {missing_outputs}"
            )

        if partial_reasons:
            return FinalizationStatus.PARTIAL.value, partial_reasons

        # COMPLETED
        return FinalizationStatus.COMPLETED.value, []

    def _check_missing_outputs(self) -> List[str]:
        """required_outputs のうち存在しないものを返す"""
        from pathlib import Path
        missing: List[str] = []
        for out_path in self.task.required_outputs:
            p = Path(out_path)
            if not p.exists():
                missing.append(out_path)
        return missing

    def get_completion_report(self) -> Dict:
        """完了判定のサマリーを返す（determine() の呼び出し不要）"""
        status, reasons = self._compute()

        reqs = self.task.requirements
        total = len(reqs)
        done_count = sum(1 for r in reqs if r.is_done())
        blocked_count = sum(1 for r in reqs if r.is_blocked())
        critical_high = [r for r in reqs if r.is_critical_or_high()]

        return {
            "finalization_status": status,
            "reasons": reasons,
            "requirements": {
                "total": total,
                "done": done_count,
                "blocked": blocked_count,
                "not_done": total - done_count,
            },
            "critical_high": {
                "total": len(critical_high),
                "done": sum(1 for r in critical_high if r.is_done()),
                "blocked": sum(1 for r in critical_high if r.is_blocked()),
            },
            "required_outputs_missing": self._check_missing_outputs(),
            "verification_results_count": len(self.task.verification_results),
            "audit_status": (
                self.task.audit_result.overall_status
                if self.task.audit_result
                else "no_audit"
            ),
        }


# ==============================
# Helpers
# ==============================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_task_ts(task: Task) -> None:
    task.updated_at = _now_iso()
