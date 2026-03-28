#!/usr/bin/env python3
"""
completion_engine/state_machine.py
完遂エンジン — Execution State Machine

8フェーズの強制遷移を管理する。
フェーズ飛ばし禁止。逆行禁止（BLOCKED→前フェーズへの修正のみ例外）。

フェーズ順序（固定）:
  resolve_task → extract_requirements → inspect_current_state →
  plan → implement → verify → audit → finalize

重要制約:
  - finalize 前に audit 完了必須
  - audit 前に verify 完了必須
  - 不正遷移は ValueError を投げる
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from completion_engine.schema import AuditResult, FinalizationStatus, Phase, Task


# ==============================
# Phase Order Definition
# ==============================

PHASE_ORDER: List[str] = [
    Phase.RESOLVE_TASK.value,
    Phase.EXTRACT_REQUIREMENTS.value,
    Phase.INSPECT_CURRENT_STATE.value,
    Phase.PLAN.value,
    Phase.IMPLEMENT.value,
    Phase.VERIFY.value,
    Phase.AUDIT.value,
    Phase.FINALIZE.value,
]

PHASE_INDEX: Dict[str, int] = {p: i for i, p in enumerate(PHASE_ORDER)}

# 各フェーズで「このフェーズに進む前に満たすべき条件」
PHASE_PRECONDITIONS: Dict[str, str] = {
    Phase.EXTRACT_REQUIREMENTS.value: "resolve_task must be complete",
    Phase.INSPECT_CURRENT_STATE.value: "extract_requirements must be complete",
    Phase.PLAN.value: "inspect_current_state must be complete",
    Phase.IMPLEMENT.value: "plan must be complete",
    Phase.VERIFY.value: "implement must be complete",
    Phase.AUDIT.value: "verify must be complete",
    Phase.FINALIZE.value: "audit must be complete with non-BLOCKED status",
}


# ==============================
# StateMachine
# ==============================

class StateMachine:
    """
    Task のフェーズ遷移を管理する。

    使い方:
        sm = StateMachine(task)
        sm.advance()              # 次フェーズへ
        sm.advance_to("verify")   # 指定フェーズへ（連続スキップは禁止）
        sm.mark_phase_complete()  # 現フェーズの完了を記録
        sm.can_advance()          # 次フェーズへ進めるか確認
    """

    def __init__(self, task: Task):
        self.task = task
        if self.task.phase not in PHASE_INDEX:
            raise ValueError(
                f"Unknown phase: {self.task.phase!r}. "
                f"Valid phases: {PHASE_ORDER}"
            )

    # --------------------------
    # Properties
    # --------------------------

    @property
    def current_phase(self) -> str:
        return self.task.phase

    @property
    def current_index(self) -> int:
        return PHASE_INDEX[self.current_phase]

    @property
    def is_at_final_phase(self) -> bool:
        return self.current_phase == Phase.FINALIZE.value

    @property
    def next_phase(self) -> Optional[str]:
        idx = self.current_index + 1
        if idx < len(PHASE_ORDER):
            return PHASE_ORDER[idx]
        return None  # finalize の次はない

    # --------------------------
    # Transition Guards
    # --------------------------

    def _check_finalize_precondition(self) -> Tuple[bool, str]:
        """finalize に進む前に audit が完了しているかチェック"""
        audit = self.task.audit_result
        if audit is None:
            return False, "audit_result is None — audit phase must complete before finalize"
        if audit.overall_status == FinalizationStatus.BLOCKED.value:
            return False, (
                f"audit_result.overall_status is BLOCKED — "
                f"failures: {audit.failures}"
            )
        return True, ""

    def _check_audit_precondition(self) -> Tuple[bool, str]:
        """audit に進む前に verify が完了しているかチェック"""
        vrs = self.task.verification_results
        if not vrs:
            return False, "verification_results is empty — verify phase must complete before audit"
        return True, ""

    def can_advance(self) -> Tuple[bool, str]:
        """
        次フェーズへ進めるかどうかを返す。

        Returns:
            (True, "")             — 進める
            (False, reason_str)    — 進めない
        """
        if self.is_at_final_phase:
            return False, "already at finalize — no further phases"

        next_p = self.next_phase
        if next_p is None:
            return False, "no next phase"

        # finalize 前の特別チェック
        if next_p == Phase.FINALIZE.value:
            ok, reason = self._check_finalize_precondition()
            if not ok:
                return False, reason

        # audit 前の特別チェック
        if next_p == Phase.AUDIT.value:
            ok, reason = self._check_audit_precondition()
            if not ok:
                return False, reason

        return True, ""

    # --------------------------
    # Transitions
    # --------------------------

    def advance(self) -> str:
        """
        現在フェーズから次フェーズへ進む。

        Returns: 遷移後のフェーズ名

        Raises:
            ValueError — 不正遷移（スキップ / precondition未達 / 最終フェーズ）
        """
        ok, reason = self.can_advance()
        if not ok:
            raise ValueError(
                f"Cannot advance from {self.current_phase!r}: {reason}"
            )

        next_p = self.next_phase
        assert next_p is not None

        prev_phase = self.task.phase
        self.task.phase = next_p
        self.task.updated_at = _now_iso()

        return next_p

    def advance_to(self, target_phase: str) -> str:
        """
        指定フェーズへ直接進む（連続スキップ禁止 — 隣接フェーズのみ）。

        Raises:
            ValueError — スキップ / 逆行 / 不正フェーズ名
        """
        if target_phase not in PHASE_INDEX:
            raise ValueError(
                f"Unknown target phase: {target_phase!r}. "
                f"Valid phases: {PHASE_ORDER}"
            )

        target_idx = PHASE_INDEX[target_phase]
        current_idx = self.current_index

        if target_idx < current_idx:
            raise ValueError(
                f"Cannot go backward: {self.current_phase!r} → {target_phase!r}. "
                f"Use force_phase() only for blocked recovery."
            )

        if target_idx > current_idx + 1:
            skipped = PHASE_ORDER[current_idx + 1 : target_idx]
            raise ValueError(
                f"Phase skip prohibited: {self.current_phase!r} → {target_phase!r}. "
                f"Must pass through: {skipped}"
            )

        return self.advance()

    def force_phase(self, target_phase: str, reason: str) -> str:
        """
        BLOCKED回復時など特別な事情で現フェーズを強制書き換えする。
        通常の advance() とは別扱い。監査証跡を残す。

        Args:
            target_phase: 設定するフェーズ
            reason: なぜ強制設定するか（必須）
        """
        if not reason:
            raise ValueError("reason is required for force_phase()")
        if target_phase not in PHASE_INDEX:
            raise ValueError(f"Unknown phase: {target_phase!r}")

        prev_phase = self.task.phase
        self.task.phase = target_phase
        self.task.updated_at = _now_iso()
        # notes に記録
        note = (
            f"[force_phase] {_now_iso()}: "
            f"{prev_phase!r} → {target_phase!r} | reason: {reason}"
        )
        self.task.notes = (self.task.notes + "\n" + note).strip()

        return target_phase

    # --------------------------
    # Status
    # --------------------------

    def get_status(self) -> Dict:
        """現在の状態サマリーを返す"""
        ok, reason = self.can_advance()
        return {
            "current_phase": self.current_phase,
            "current_index": self.current_index,
            "total_phases": len(PHASE_ORDER),
            "next_phase": self.next_phase,
            "can_advance": ok,
            "blocked_reason": reason if not ok else "",
            "phase_order": PHASE_ORDER,
        }

    def __repr__(self) -> str:
        return (
            f"StateMachine("
            f"task_id={self.task.id!r}, "
            f"phase={self.current_phase!r}, "
            f"index={self.current_index}/{len(PHASE_ORDER) - 1})"
        )


# ==============================
# Helpers
# ==============================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def phase_progress_bar(current_phase: str) -> str:
    """ASCII プログレスバーを返す（表示用）"""
    if current_phase not in PHASE_INDEX:
        return "[unknown phase]"
    idx = PHASE_INDEX[current_phase]
    bar = ""
    for i, p in enumerate(PHASE_ORDER):
        if i < idx:
            bar += "█"
        elif i == idx:
            bar += "▓"
        else:
            bar += "░"
    short_names = {
        "resolve_task": "RSV",
        "extract_requirements": "REQ",
        "inspect_current_state": "INS",
        "plan": "PLN",
        "implement": "IMP",
        "verify": "VRF",
        "audit": "AUD",
        "finalize": "FIN",
    }
    name = short_names.get(current_phase, current_phase[:3].upper())
    return f"[{bar}] {name} ({idx + 1}/{len(PHASE_ORDER)})"
