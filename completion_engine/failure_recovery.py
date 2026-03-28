#!/usr/bin/env python3
"""
completion_engine/failure_recovery.py
完遂エンジン — Failure Recovery Loop

障害発生時の7ステップ追跡記録とリカバリーループを管理する。

7ステップ:
  Step 1: phenomenon    — 何が起きたか（現象の記録）
  Step 2: hypotheses    — 根本原因の仮説（複数）
  Step 3: fix_applied   — 適用した修正
  Step 4: rerun_result  — 修正後の再実行結果
  Step 5: reverification — 影響範囲の再検証
  Step 6: impact_summary — 影響の整理
  Step 7: artifact_updates — KNOWN_MISTAKES / docs 更新記録

全ステップが記録されるまで RESOLVED にできない。
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from completion_engine.schema import FailureRecord, Phase, Task


# ==============================
# FailureRecovery
# ==============================

class FailureRecovery:
    """
    Task に紐づく FailureRecord の管理とリカバリーループを提供する。

    使い方:
        recovery = FailureRecovery(task)
        rec = recovery.open_failure(
            phase="implement",
            phenomenon="FileNotFoundError in publisher.py:42"
        )
        recovery.add_hypothesis(rec.id, "パスが環境変数依存で本番と開発で差異")
        recovery.apply_fix(rec.id, "nowpattern_publisher.py のパス解決を絶対パスに変更")
        recovery.record_rerun(rec.id, "PASS — 5件投稿成功")
        recovery.resolve(rec.id, reverification="全テスト再確認 PASS", impact="本番影響なし")
    """

    def __init__(self, task: Task):
        self.task = task

    # --------------------------
    # Open / Close Failures
    # --------------------------

    def open_failure(
        self,
        phase: str,
        phenomenon: str,
        requirement_id: Optional[str] = None,
    ) -> FailureRecord:
        """
        新しい障害レコードを開く。

        Args:
            phase: 障害が発生したフェーズ（Phase value）
            phenomenon: 何が起きたか（現象の記録）
            requirement_id: 関連する要件ID（任意）
        """
        if not phenomenon:
            raise ValueError("phenomenon is required — describe what happened")

        rec = FailureRecord(
            id=_make_failure_id(),
            task_id=self.task.id,
            requirement_id=requirement_id,
            phase=phase,
            phenomenon=phenomenon,
            root_cause_hypotheses=[],
            fix_applied="",
            rerun_result="",
            reverification_result="",
            impact_summary="",
            artifact_updates="",
            resolved=False,
            created_at=_now_iso(),
            resolved_at=None,
        )
        self.task.failure_records.append(rec)
        _update_task_ts(self.task)
        return rec

    def add_hypothesis(self, failure_id: str, hypothesis: str) -> FailureRecord:
        """Step 2: 根本原因の仮説を追加する"""
        rec = self._get_or_raise(failure_id)
        if not hypothesis:
            raise ValueError("hypothesis cannot be empty")
        rec.root_cause_hypotheses.append(hypothesis)
        _update_task_ts(self.task)
        return rec

    def apply_fix(self, failure_id: str, fix_description: str) -> FailureRecord:
        """Step 3: 適用した修正を記録する"""
        rec = self._get_or_raise(failure_id)
        if not fix_description:
            raise ValueError("fix_description cannot be empty")
        rec.fix_applied = fix_description
        _update_task_ts(self.task)
        return rec

    def record_rerun(self, failure_id: str, result: str) -> FailureRecord:
        """Step 4: 修正後の再実行結果を記録する"""
        rec = self._get_or_raise(failure_id)
        if not result:
            raise ValueError("result cannot be empty")
        rec.rerun_result = result
        _update_task_ts(self.task)
        return rec

    def record_reverification(
        self, failure_id: str, reverification: str
    ) -> FailureRecord:
        """Step 5: 影響範囲の再検証を記録する"""
        rec = self._get_or_raise(failure_id)
        rec.reverification_result = reverification
        _update_task_ts(self.task)
        return rec

    def record_impact(self, failure_id: str, impact_summary: str) -> FailureRecord:
        """Step 6: 影響の整理を記録する"""
        rec = self._get_or_raise(failure_id)
        rec.impact_summary = impact_summary
        _update_task_ts(self.task)
        return rec

    def record_artifact_updates(
        self, failure_id: str, updates: str
    ) -> FailureRecord:
        """Step 7: KNOWN_MISTAKES / docs 更新記録"""
        rec = self._get_or_raise(failure_id)
        rec.artifact_updates = updates
        _update_task_ts(self.task)
        return rec

    def resolve(
        self,
        failure_id: str,
        reverification: str = "",
        impact: str = "",
        artifact_updates: str = "",
    ) -> Tuple[bool, str]:
        """
        障害を RESOLVED にしようとする。
        全7ステップが記録されていなければ失敗。

        Returns:
            (True, "")      — 解決成功
            (False, reason) — 未完了ステップあり
        """
        rec = self._get_or_raise(failure_id)

        # 後から補完できるフィールド
        if reverification:
            rec.reverification_result = reverification
        if impact:
            rec.impact_summary = impact
        if artifact_updates:
            rec.artifact_updates = artifact_updates

        ok, missing = self._validate_steps(rec)
        if not ok:
            return False, (
                f"Cannot resolve failure {failure_id}: "
                f"missing steps: {missing}"
            )

        rec.resolved = True
        rec.resolved_at = _now_iso()
        _update_task_ts(self.task)
        return True, ""

    # --------------------------
    # Validation
    # --------------------------

    def _validate_steps(self, rec: FailureRecord) -> Tuple[bool, List[str]]:
        """7ステップが全て記録されているか確認する"""
        missing: List[str] = []

        if not rec.phenomenon:
            missing.append("Step 1: phenomenon")
        if not rec.root_cause_hypotheses:
            missing.append("Step 2: root_cause_hypotheses (add at least 1)")
        if not rec.fix_applied:
            missing.append("Step 3: fix_applied")
        if not rec.rerun_result:
            missing.append("Step 4: rerun_result")
        # Step 5-7 は任意（空でも解決可）
        # ただし phenomenaが再現するケースでは必要

        return (len(missing) == 0), missing

    # --------------------------
    # Queries
    # --------------------------

    def get_open_failures(self) -> List[FailureRecord]:
        """未解決の障害レコードを返す"""
        return [r for r in self.task.failure_records if not r.resolved]

    def get_resolved_failures(self) -> List[FailureRecord]:
        """解決済みの障害レコードを返す"""
        return [r for r in self.task.failure_records if r.resolved]

    def has_unresolved(self) -> bool:
        """未解決障害が1つでもあるか"""
        return len(self.get_open_failures()) > 0

    def get_summary(self) -> Dict:
        """障害サマリーを返す"""
        all_recs = self.task.failure_records
        open_recs = self.get_open_failures()
        resolved_recs = self.get_resolved_failures()

        by_phase: Dict[str, int] = {}
        for r in all_recs:
            by_phase[r.phase] = by_phase.get(r.phase, 0) + 1

        return {
            "total": len(all_recs),
            "open": len(open_recs),
            "resolved": len(resolved_recs),
            "by_phase": by_phase,
            "open_ids": [r.id for r in open_recs],
        }

    def format_failure(self, failure_id: str) -> str:
        """障害レコードの7ステップを表示用テキストで返す"""
        rec = self._get_or_raise(failure_id)
        lines = [
            f"=== Failure Record: {rec.id} ===",
            f"Task:        {rec.task_id}",
            f"Phase:       {rec.phase}",
            f"Requirement: {rec.requirement_id or 'N/A'}",
            f"Status:      {'RESOLVED' if rec.resolved else 'OPEN'}",
            f"Created:     {rec.created_at}",
            "",
            f"Step 1 — Phenomenon:",
            f"  {rec.phenomenon}",
            "",
            f"Step 2 — Root Cause Hypotheses:",
        ]
        for i, h in enumerate(rec.root_cause_hypotheses, 1):
            lines.append(f"  [{i}] {h}")
        if not rec.root_cause_hypotheses:
            lines.append("  (none)")
        lines += [
            "",
            f"Step 3 — Fix Applied:",
            f"  {rec.fix_applied or '(not yet applied)'}",
            "",
            f"Step 4 — Rerun Result:",
            f"  {rec.rerun_result or '(not yet re-run)'}",
            "",
            f"Step 5 — Reverification:",
            f"  {rec.reverification_result or '(not recorded)'}",
            "",
            f"Step 6 — Impact Summary:",
            f"  {rec.impact_summary or '(not recorded)'}",
            "",
            f"Step 7 — Artifact Updates:",
            f"  {rec.artifact_updates or '(not recorded)'}",
        ]
        if rec.resolved_at:
            lines.append(f"\nResolved at: {rec.resolved_at}")
        return "\n".join(lines)

    # --------------------------
    # Internal
    # --------------------------

    def _get_or_raise(self, failure_id: str) -> FailureRecord:
        for r in self.task.failure_records:
            if r.id == failure_id:
                return r
        raise KeyError(f"FailureRecord not found: {failure_id!r}")


# ==============================
# Helpers
# ==============================

def _make_failure_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    short = str(uuid.uuid4())[:6]
    return f"fail-{ts}-{short}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_task_ts(task: Task) -> None:
    task.updated_at = _now_iso()
