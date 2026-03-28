#!/usr/bin/env python3
"""
completion_engine/report_generator.py
完遂エンジン — Report Generator

Task の完了レポートを生成する（10セクション）。

セクション構成:
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
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from completion_engine.schema import (
    AuditResult,
    Evidence,
    EvidenceStatus,
    FailureRecord,
    FinalizationStatus,
    Phase,
    Requirement,
    RequirementStatus,
    Task,
    VerificationResult,
    task_to_dict,
)
from completion_engine.state_machine import phase_progress_bar


# ==============================
# ReportGenerator
# ==============================

class ReportGenerator:
    """
    Task から10セクションの完了レポートを生成する。

    使い方:
        gen = ReportGenerator(task)
        md_text = gen.generate_markdown()
        gen.save(output_path)
        json_report = gen.generate_json()
    """

    def __init__(self, task: Task):
        self.task = task

    def generate_markdown(self) -> str:
        """Markdownフォーマットでレポートを生成する"""
        sections = [
            self._section_1_overview(),
            self._section_2_phase_journey(),
            self._section_3_requirements(),
            self._section_4_evidence(),
            self._section_5_verification(),
            self._section_6_audit(),
            self._section_7_failures(),
            self._section_8_changed_files(),
            self._section_9_final_status(),
            self._section_10_next_actions(),
        ]
        header = self._header()
        return header + "\n\n".join(sections) + "\n"

    def generate_json(self) -> dict:
        """JSON形式で機械可読レポートを生成する"""
        return {
            "generated_at": _now_iso(),
            "task": task_to_dict(self.task),
            "summary": self._build_summary_dict(),
        }

    def save(self, output_path: str) -> Path:
        """Markdownレポートをファイルに保存する"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.generate_markdown()
        path.write_text(content, encoding="utf-8")
        return path

    def save_json(self, output_path: str) -> Path:
        """JSONレポートをファイルに保存する"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.generate_json()
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    # --------------------------
    # Header
    # --------------------------

    def _header(self) -> str:
        status = self.task.finalization_status or "in_progress"
        status_badge = {
            "completed": "✅ COMPLETED",
            "partial": "⚠️ PARTIAL",
            "blocked": "❌ BLOCKED",
            "in_progress": "🔄 IN PROGRESS",
        }.get(status, f"[{status}]")

        return f"""# 完遂エンジン — タスク完了レポート

**Task ID**: `{self.task.id}`
**Status**: {status_badge}
**Generated**: {_now_iso()}
**Source**: {self.task.source}

---
"""

    # --------------------------
    # Sections
    # --------------------------

    def _section_1_overview(self) -> str:
        lines = [
            "## §1 Task Overview",
            "",
            f"**Title**: {self.task.title}",
            f"**Source**: `{self.task.source}`",
            f"**Phase**: {self.task.phase}",
            f"**Status**: {self.task.status}",
            f"**Created**: {self.task.created_at}",
            f"**Updated**: {self.task.updated_at}",
            "",
            "**Raw Input**:",
            "```",
            self.task.raw_input[:500] + ("..." if len(self.task.raw_input) > 500 else ""),
            "```",
        ]
        if self.task.assumptions:
            lines += ["", "**Assumptions**:"]
            for a in self.task.assumptions:
                lines.append(f"- {a}")
        if self.task.notes:
            lines += ["", f"**Notes**: {self.task.notes}"]
        return "\n".join(lines)

    def _section_2_phase_journey(self) -> str:
        bar = phase_progress_bar(self.task.phase)
        lines = [
            "## §2 Phase Journey",
            "",
            f"Progress: `{bar}`",
            "",
            "| Phase | Status |",
            "|-------|--------|",
        ]
        from completion_engine.state_machine import PHASE_ORDER, PHASE_INDEX
        current_idx = PHASE_INDEX.get(self.task.phase, 0)
        for i, p in enumerate(PHASE_ORDER):
            if i < current_idx:
                status_icon = "✅ Done"
            elif i == current_idx:
                status_icon = "🔄 Current"
            else:
                status_icon = "⬜ Pending"
            lines.append(f"| `{p}` | {status_icon} |")
        return "\n".join(lines)

    def _section_3_requirements(self) -> str:
        reqs = self.task.requirements
        total = len(reqs)
        done = sum(1 for r in reqs if r.is_done())
        blocked = sum(1 for r in reqs if r.is_blocked())

        lines = [
            "## §3 Requirement Summary",
            "",
            f"**Total**: {total} | **Done**: {done} | **Blocked**: {blocked} | "
            f"**In Progress**: {total - done - blocked}",
            "",
            "| ID | Priority | Status | Text |",
            "|----|----------|--------|------|",
        ]
        for req in reqs:
            priority_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "⚪",
            }.get(req.priority, "")
            status_icon = {
                "done": "✅",
                "blocked": "❌",
                "in_progress": "🔄",
                "pending": "⬜",
                "partial": "⚠️",
            }.get(req.status, "")
            text_short = req.text[:60] + ("…" if len(req.text) > 60 else "")
            lines.append(
                f"| `{req.id}` | {priority_icon} {req.priority} | "
                f"{status_icon} {req.status} | {text_short} |"
            )

        # Blocked 要件の詳細
        blocked_reqs = [r for r in reqs if r.is_blocked()]
        if blocked_reqs:
            lines += ["", "**Blocked Requirements:**"]
            for req in blocked_reqs:
                lines += [
                    f"- `{req.id}`: {req.blocker_reason or '(no reason given)'}",
                ]

        return "\n".join(lines)

    def _section_4_evidence(self) -> str:
        lines = [
            "## §4 Evidence Inventory",
            "",
        ]
        all_evidences: List[Evidence] = []
        for req in self.task.requirements:
            all_evidences.extend(req.evidences)

        if not all_evidences:
            lines.append("_No evidence recorded._")
            return "\n".join(lines)

        verified = sum(1 for e in all_evidences if e.is_verified())
        lines.append(
            f"**Total**: {len(all_evidences)} | **Verified**: {verified} | "
            f"**Unverified**: {len(all_evidences) - verified}"
        )
        lines += [
            "",
            "| Evidence ID | Req | Type | Status | Description |",
            "|-------------|-----|------|--------|-------------|",
        ]
        for ev in all_evidences:
            status_icon = {
                "verified": "✅",
                "unverified": "⬜",
                "failed": "❌",
            }.get(ev.status, "")
            desc_short = ev.description[:40] + ("…" if len(ev.description) > 40 else "")
            lines.append(
                f"| `{ev.id}` | `{ev.requirement_id}` | `{ev.type}` | "
                f"{status_icon} {ev.status} | {desc_short} |"
            )
        return "\n".join(lines)

    def _section_5_verification(self) -> str:
        vrs = self.task.verification_results
        lines = [
            "## §5 Verification Results",
            "",
        ]
        if not vrs:
            lines.append("_No verification results recorded._")
            return "\n".join(lines)

        passed = sum(1 for v in vrs if v.is_passing())
        lines.append(
            f"**Total**: {len(vrs)} | **Passed**: {passed} | "
            f"**Failed/Partial**: {len(vrs) - passed}"
        )
        lines += [
            "",
            "| Req ID | Target | Judgment | Method |",
            "|--------|--------|----------|--------|",
        ]
        for vr in vrs:
            judgment_icon = {
                "pass": "✅",
                "fail": "❌",
                "partial": "⚠️",
                "blocked": "🚫",
            }.get(vr.judgment, "")
            target_short = vr.target[:40]
            lines.append(
                f"| `{vr.requirement_id}` | {target_short} | "
                f"{judgment_icon} {vr.judgment} | {vr.method} |"
            )
        return "\n".join(lines)

    def _section_6_audit(self) -> str:
        audit = self.task.audit_result
        lines = ["## §6 Audit Result", ""]

        if audit is None:
            lines.append("_Audit not yet run._")
            return "\n".join(lines)

        status_icon = {
            "completed": "✅",
            "partial": "⚠️",
            "blocked": "❌",
        }.get(audit.overall_status, "")

        lines += [
            f"**Overall Status**: {status_icon} {audit.overall_status.upper()}",
            f"**Audited At**: {audit.audited_at}",
            "",
            "| Check | Result |",
            "|-------|--------|",
            f"| A1: Outputs Verified | {'✅' if audit.outputs_verified else '❌'} |",
            f"| A2: Evidence Sufficient | {'✅' if audit.evidence_sufficient else '❌'} |",
            f"| A3: Docs Match Implementation | {'✅' if audit.docs_match_implementation else '❌'} |",
            f"| A4: Critical/High All Done | {'✅' if audit.critical_high_all_done else '❌'} |",
        ]

        if audit.failures:
            lines += ["", "**Audit Failures:**"]
            for f in audit.failures:
                lines.append(f"- {f}")

        return "\n".join(lines)

    def _section_7_failures(self) -> str:
        recs = self.task.failure_records
        lines = ["## §7 Failure Records", ""]

        if not recs:
            lines.append("_No failures recorded._")
            return "\n".join(lines)

        resolved = sum(1 for r in recs if r.resolved)
        lines.append(
            f"**Total**: {len(recs)} | **Resolved**: {resolved} | "
            f"**Open**: {len(recs) - resolved}"
        )

        for rec in recs:
            status = "✅ RESOLVED" if rec.resolved else "❌ OPEN"
            lines += [
                "",
                f"### {rec.id} — {status}",
                f"**Phase**: {rec.phase}",
                f"**Phenomenon**: {rec.phenomenon}",
            ]
            if rec.root_cause_hypotheses:
                lines.append("**Root Cause Hypotheses**:")
                for h in rec.root_cause_hypotheses:
                    lines.append(f"- {h}")
            if rec.fix_applied:
                lines.append(f"**Fix Applied**: {rec.fix_applied}")
            if rec.rerun_result:
                lines.append(f"**Rerun Result**: {rec.rerun_result}")

        return "\n".join(lines)

    def _section_8_changed_files(self) -> str:
        lines = ["## §8 Changed Files", ""]
        if not self.task.changed_files:
            lines.append("_No files recorded._")
            return "\n".join(lines)

        lines.append(f"**Total**: {len(self.task.changed_files)} files")
        lines.append("")
        for f in self.task.changed_files:
            lines.append(f"- `{f}`")
        return "\n".join(lines)

    def _section_9_final_status(self) -> str:
        status = self.task.finalization_status or "in_progress"
        status_icon = {
            "completed": "✅",
            "partial": "⚠️",
            "blocked": "❌",
            "in_progress": "🔄",
        }.get(status, "")

        lines = [
            "## §9 Final Status",
            "",
            f"**Finalization Status**: {status_icon} `{status.upper()}`",
            f"**Task Status**: `{self.task.status}`",
            f"**Phase**: `{self.task.phase}`",
        ]

        # 要件サマリー
        reqs = self.task.requirements
        if reqs:
            total = len(reqs)
            done = sum(1 for r in reqs if r.is_done())
            lines.append(f"**Requirements**: {done}/{total} Done")

        return "\n".join(lines)

    def _section_10_next_actions(self) -> str:
        lines = ["## §10 Next Actions / Handoff Notes", ""]

        # 未完了の要件
        pending = [
            r for r in self.task.requirements
            if r.status in ("pending", "in_progress", "partial")
        ]
        blocked = [r for r in self.task.requirements if r.is_blocked()]
        open_failures = [r for r in self.task.failure_records if not r.resolved]

        if not pending and not blocked and not open_failures:
            lines.append("✅ All requirements done. No pending actions.")
            return "\n".join(lines)

        if pending:
            lines += ["**Pending Requirements:**"]
            for req in pending:
                lines.append(f"- [ ] `{req.id}` [{req.priority}] {req.text[:60]}")

        if blocked:
            lines += ["", "**Blocked Requirements (need resolution):**"]
            for req in blocked:
                lines.append(
                    f"- ❌ `{req.id}`: {req.blocker_reason or '(no reason)'}"
                )

        if open_failures:
            lines += ["", "**Open Failure Records:**"]
            for rec in open_failures:
                lines.append(f"- ❌ `{rec.id}` ({rec.phase}): {rec.phenomenon[:60]}")

        return "\n".join(lines)

    # --------------------------
    # Internal
    # --------------------------

    def _build_summary_dict(self) -> dict:
        reqs = self.task.requirements
        return {
            "task_id": self.task.id,
            "title": self.task.title,
            "phase": self.task.phase,
            "finalization_status": self.task.finalization_status,
            "requirements": {
                "total": len(reqs),
                "done": sum(1 for r in reqs if r.is_done()),
                "blocked": sum(1 for r in reqs if r.is_blocked()),
            },
            "verification_results": len(self.task.verification_results),
            "failure_records": {
                "total": len(self.task.failure_records),
                "open": sum(1 for r in self.task.failure_records if not r.resolved),
            },
            "audit_status": (
                self.task.audit_result.overall_status
                if self.task.audit_result
                else None
            ),
        }


# ==============================
# Helpers
# ==============================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
