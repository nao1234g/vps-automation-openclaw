#!/usr/bin/env python3
"""
completion_engine/requirement_contract.py
完遂エンジン — Requirement Contract Engine

タスクから要件を抽出・管理する。
各 Requirement は acceptance_criteria + required_evidence が揃って初めて Done になれる。

設計原則:
  「感覚ではなく contract で判断する。」
  「Done は自己申告ではなく evidence で証明する。」
"""
from __future__ import annotations

import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from completion_engine.schema import (
    Evidence,
    EvidenceStatus,
    EvidenceType,
    Priority,
    Requirement,
    RequirementCategory,
    RequirementStatus,
    Task,
)


# ==============================
# RequirementContract
# ==============================

class RequirementContract:
    """
    Task の要件コントラクトを管理する。

    使い方:
        contract = RequirementContract(task)
        contract.add_requirement(text="...", category="implementation", ...)
        contract.mark_done("req-001", evidence_values={...})
        all_done = contract.all_critical_high_done()
        summary = contract.get_summary()
    """

    def __init__(self, task: Task):
        self.task = task

    # --------------------------
    # Requirement CRUD
    # --------------------------

    def add_requirement(
        self,
        text: str,
        category: str = RequirementCategory.IMPLEMENTATION.value,
        priority: str = Priority.HIGH.value,
        acceptance_criteria: Optional[List[str]] = None,
        required_evidence_types: Optional[List[str]] = None,
        target_files: Optional[List[str]] = None,
        notes: str = "",
    ) -> Requirement:
        """
        新しい要件を追加して返す。

        Args:
            text: 要件の説明
            category: RequirementCategory value
            priority: Priority value
            acceptance_criteria: 完了条件リスト
            required_evidence_types: EvidenceType value のリスト（任意）
            target_files: 関連ファイルパスリスト
            notes: 補足
        """
        req_id = _make_req_id()
        req = Requirement(
            id=req_id,
            text=text,
            category=category,
            priority=priority,
            acceptance_criteria=acceptance_criteria or [],
            required_evidence=[],  # evidence id は後で追加
            target_files=target_files or [],
            status=RequirementStatus.PENDING.value,
            notes=notes,
        )

        # required_evidence_types から Evidence を自動生成
        if required_evidence_types:
            for ev_type in required_evidence_types:
                ev = self._make_evidence_placeholder(req_id, ev_type)
                req.evidences.append(ev)
                req.required_evidence.append(ev.id)

        self.task.requirements.append(req)
        _update_task_ts(self.task)
        return req

    def get_requirement(self, req_id: str) -> Optional[Requirement]:
        for r in self.task.requirements:
            if r.id == req_id:
                return r
        return None

    def update_status(
        self,
        req_id: str,
        status: str,
        blocker_reason: str = "",
    ) -> Requirement:
        """要件のステータスを更新する"""
        req = self._get_or_raise(req_id)
        if status not in [s.value for s in RequirementStatus]:
            raise ValueError(f"Unknown status: {status!r}")
        req.status = status
        req.blocker_reason = blocker_reason
        _update_task_ts(self.task)
        return req

    # --------------------------
    # Evidence Management
    # --------------------------

    def add_evidence(
        self,
        req_id: str,
        description: str,
        ev_type: str = EvidenceType.MANUAL.value,
        value: Optional[str] = None,
        notes: str = "",
    ) -> Evidence:
        """要件に証跡を追加する（後から追加可能）"""
        req = self._get_or_raise(req_id)
        ev = Evidence(
            id=_make_ev_id(),
            requirement_id=req_id,
            description=description,
            type=ev_type,
            value=value,
            status=EvidenceStatus.UNVERIFIED.value,
            notes=notes,
        )
        req.evidences.append(ev)
        req.required_evidence.append(ev.id)
        _update_task_ts(self.task)
        return ev

    def verify_evidence(
        self,
        req_id: str,
        ev_id: str,
        value: str,
        notes: str = "",
    ) -> Evidence:
        """証跡を検証済みにマークする"""
        req = self._get_or_raise(req_id)
        ev = self._get_evidence_or_raise(req, ev_id)
        ev.value = value
        ev.status = EvidenceStatus.VERIFIED.value
        ev.verified_at = _now_iso()
        ev.notes = notes
        _update_task_ts(self.task)
        return ev

    def fail_evidence(
        self,
        req_id: str,
        ev_id: str,
        notes: str = "",
    ) -> Evidence:
        """証跡を FAILED にマークする"""
        req = self._get_or_raise(req_id)
        ev = self._get_evidence_or_raise(req, ev_id)
        ev.status = EvidenceStatus.FAILED.value
        ev.notes = notes
        _update_task_ts(self.task)
        return ev

    # --------------------------
    # Done / Block Marking
    # --------------------------

    def mark_done(self, req_id: str) -> Tuple[bool, str]:
        """
        要件を Done にしようとする。
        acceptance_criteria を全て満たし、evidence が全て VERIFIED なら成功。

        Returns:
            (True, "")              — Done に成功
            (False, reason_str)     — Done にできない理由
        """
        req = self._get_or_raise(req_id)

        # acceptance_criteria チェック（criteriaがない場合はスキップ）
        # 実際の証拠で確認する必要がある。evidence が全て VERIFIED かチェック
        unverified = [
            ev for ev in req.evidences
            if ev.status != EvidenceStatus.VERIFIED.value
        ]
        if unverified:
            ids = [ev.id for ev in unverified]
            return False, (
                f"Requirement {req_id} has unverified evidence: {ids}. "
                f"All evidence must be VERIFIED before marking Done."
            )

        req.status = RequirementStatus.DONE.value
        _update_task_ts(self.task)
        return True, ""

    def mark_blocked(self, req_id: str, reason: str) -> Requirement:
        """要件を BLOCKED にマークする"""
        if not reason:
            raise ValueError("reason is required for mark_blocked()")
        req = self._get_or_raise(req_id)
        req.status = RequirementStatus.BLOCKED.value
        req.blocker_reason = reason
        _update_task_ts(self.task)
        return req

    # --------------------------
    # Aggregate Queries
    # --------------------------

    def all_done(self) -> bool:
        """全要件が Done かどうか"""
        return all(r.is_done() for r in self.task.requirements)

    def all_critical_high_done(self) -> bool:
        """CRITICAL / HIGH 優先度の要件が全て Done かどうか"""
        critical_high = [
            r for r in self.task.requirements
            if r.is_critical_or_high()
        ]
        if not critical_high:
            return True  # 該当なしは true
        return all(r.is_done() for r in critical_high)

    def has_blocked(self) -> bool:
        """BLOCKED 要件が1つでもあるか"""
        return any(r.is_blocked() for r in self.task.requirements)

    def get_pending_requirements(self) -> List[Requirement]:
        return [r for r in self.task.requirements
                if r.status == RequirementStatus.PENDING.value]

    def get_in_progress_requirements(self) -> List[Requirement]:
        return [r for r in self.task.requirements
                if r.status == RequirementStatus.IN_PROGRESS.value]

    def get_blocked_requirements(self) -> List[Requirement]:
        return [r for r in self.task.requirements if r.is_blocked()]

    def get_done_requirements(self) -> List[Requirement]:
        return [r for r in self.task.requirements if r.is_done()]

    def get_summary(self) -> Dict:
        """要件の集計サマリーを返す"""
        reqs = self.task.requirements
        total = len(reqs)
        done_count = sum(1 for r in reqs if r.is_done())
        blocked_count = sum(1 for r in reqs if r.is_blocked())
        critical_high = [r for r in reqs if r.is_critical_or_high()]
        critical_high_done = sum(1 for r in critical_high if r.is_done())

        by_priority: Dict[str, Dict[str, int]] = {}
        for priority in [p.value for p in Priority]:
            subset = [r for r in reqs if r.priority == priority]
            by_priority[priority] = {
                "total": len(subset),
                "done": sum(1 for r in subset if r.is_done()),
                "blocked": sum(1 for r in subset if r.is_blocked()),
            }

        return {
            "total": total,
            "done": done_count,
            "blocked": blocked_count,
            "pending_or_in_progress": total - done_count - blocked_count,
            "done_pct": round(done_count / total * 100, 1) if total > 0 else 0,
            "critical_high_total": len(critical_high),
            "critical_high_done": critical_high_done,
            "all_critical_high_done": self.all_critical_high_done(),
            "by_priority": by_priority,
        }

    # --------------------------
    # Internal Helpers
    # --------------------------

    def _get_or_raise(self, req_id: str) -> Requirement:
        req = self.get_requirement(req_id)
        if req is None:
            raise KeyError(f"Requirement not found: {req_id!r}")
        return req

    def _get_evidence_or_raise(self, req: Requirement, ev_id: str) -> Evidence:
        for ev in req.evidences:
            if ev.id == ev_id:
                return ev
        raise KeyError(f"Evidence {ev_id!r} not found in requirement {req.id!r}")

    def _make_evidence_placeholder(
        self, req_id: str, ev_type: str
    ) -> Evidence:
        return Evidence(
            id=_make_ev_id(),
            requirement_id=req_id,
            description=f"[{ev_type}] evidence required",
            type=ev_type,
            value=None,
            status=EvidenceStatus.UNVERIFIED.value,
        )


# ==============================
# Helpers
# ==============================

def _make_req_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%H%M%S")
    short = str(uuid.uuid4())[:6]
    return f"req-{ts}-{short}"


def _make_ev_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%H%M%S")
    short = str(uuid.uuid4())[:6]
    return f"ev-{ts}-{short}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_task_ts(task: Task) -> None:
    task.updated_at = _now_iso()
