#!/usr/bin/env python3
"""
completion_engine/schema.py
完遂エンジン — データスキーマ定義

Task / Requirement / Evidence / VerificationResult / AuditResult / FinalizationStatus
を dataclass として定義する。JSON 直列化・復元に対応。

設計原則:
  「状態と証跡で判定する。会話上の雰囲気で判定しない。」
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ==============================
# Enums
# ==============================

class RequirementCategory(str, Enum):
    IMPLEMENTATION = "implementation"
    DOCS          = "docs"
    VERIFICATION  = "verification"
    MIGRATION     = "migration"
    CLEANUP       = "cleanup"
    HANDOFF       = "handoff"
    REPORTING     = "reporting"
    CONSTRAINT    = "constraint"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class RequirementStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    PARTIAL     = "partial"
    DONE        = "done"
    BLOCKED     = "blocked"


class Phase(str, Enum):
    RESOLVE_TASK         = "resolve_task"
    EXTRACT_REQUIREMENTS = "extract_requirements"
    INSPECT_CURRENT_STATE = "inspect_current_state"
    PLAN                 = "plan"
    IMPLEMENT            = "implement"
    VERIFY               = "verify"
    AUDIT                = "audit"
    FINALIZE             = "finalize"


class FinalizationStatus(str, Enum):
    COMPLETED = "completed"
    PARTIAL   = "partial"
    BLOCKED   = "blocked"


class EvidenceType(str, Enum):
    FILE_EXISTS    = "file_exists"
    COMMAND_OUTPUT = "command_output"
    LOG_ENTRY      = "log_entry"
    TEST_RESULT    = "test_result"
    DIFF           = "diff"
    REPORT_FILE    = "report_file"
    MANUAL         = "manual"


class EvidenceStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED   = "verified"
    FAILED     = "failed"


class TaskSource(str, Enum):
    EXPLICIT_TASK_INPUT = "explicit_task_input"
    LATEST_USER_MESSAGE = "latest_user_message"
    ACTIVE_CONTEXT      = "active_context"
    HANDOFF_SOURCE      = "handoff_source"
    UNRESOLVED          = "unresolved"


# ==============================
# Dataclasses
# ==============================

@dataclass
class Evidence:
    """requirement の Done 判定に必要な証跡"""
    id: str
    requirement_id: str
    description: str
    type: str                     # EvidenceType value
    value: Optional[str] = None   # 実際の証跡内容（ファイルパス / コマンド出力 / ログ行）
    status: str = EvidenceStatus.UNVERIFIED.value
    verified_at: Optional[str] = None
    notes: str = ""

    def is_verified(self) -> bool:
        return self.status == EvidenceStatus.VERIFIED.value


@dataclass
class Requirement:
    """単一の要件。acceptance_criteria + evidence が揃って初めて Done になれる"""
    id: str
    text: str
    category: str            # RequirementCategory value
    priority: str            # Priority value
    acceptance_criteria: List[str] = field(default_factory=list)
    required_evidence: List[str] = field(default_factory=list)  # Evidence.id リスト
    target_files: List[str] = field(default_factory=list)
    status: str = RequirementStatus.PENDING.value
    blocker_reason: str = ""
    notes: str = ""
    evidences: List[Evidence] = field(default_factory=list)

    def is_critical_or_high(self) -> bool:
        return self.priority in (Priority.CRITICAL.value, Priority.HIGH.value)

    def is_done(self) -> bool:
        return self.status == RequirementStatus.DONE.value

    def is_blocked(self) -> bool:
        return self.status == RequirementStatus.BLOCKED.value


@dataclass
class FailureRecord:
    """障害発生時の7ステップ追跡記録"""
    id: str
    task_id: str
    requirement_id: Optional[str]
    phase: str
    phenomenon: str
    root_cause_hypotheses: List[str] = field(default_factory=list)
    fix_applied: str = ""
    rerun_result: str = ""
    reverification_result: str = ""
    impact_summary: str = ""
    artifact_updates: str = ""
    resolved: bool = False
    created_at: str = ""
    resolved_at: Optional[str] = None


@dataclass
class VerificationResult:
    """単一の verification 実行結果。証跡を必ず含む"""
    requirement_id: str
    target: str
    method: str
    expected: str
    actual: str
    judgment: str          # "pass" / "fail" / "partial" / "blocked"
    evidence: str          # コマンド出力・ファイル内容等の具体的証跡
    notes: str = ""
    verified_at: str = ""

    def is_passing(self) -> bool:
        return self.judgment == "pass"


@dataclass
class AuditResult:
    """Audit Pass の結果。1件でも未達があれば completed にできない"""
    task_id: str
    audited_at: str
    requirement_results: Dict[str, str] = field(default_factory=dict)  # req_id -> status
    outputs_verified: bool = False
    evidence_sufficient: bool = False
    docs_match_implementation: bool = False
    critical_high_all_done: bool = False
    overall_status: str = FinalizationStatus.BLOCKED.value
    notes: str = ""
    failures: List[str] = field(default_factory=list)  # 未達理由リスト


@dataclass
class Task:
    """完遂エンジンが管理する実行単位。resolve → finalize まで全状態を保持"""
    id: str
    title: str
    source: str                   # TaskSource value
    raw_input: str
    phase: str = Phase.RESOLVE_TASK.value
    status: str = "open"
    requirements: List[Requirement] = field(default_factory=list)
    required_outputs: List[str] = field(default_factory=list)
    verification_results: List[VerificationResult] = field(default_factory=list)
    audit_result: Optional[AuditResult] = None
    failure_records: List[FailureRecord] = field(default_factory=list)
    finalization_status: Optional[str] = None  # FinalizationStatus value
    created_at: str = ""
    updated_at: str = ""
    notes: str = ""
    assumptions: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)


# ==============================
# JSON Serialization Helpers
# ==============================

def _serialize(obj: Any) -> Any:
    """dataclass / Enum / nested 構造を JSON-safe に変換"""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def task_to_dict(task: Task) -> Dict[str, Any]:
    return _serialize(task)


def task_from_dict(d: Dict[str, Any]) -> Task:
    """JSON dict から Task を復元する（簡易版）"""
    reqs = []
    for r in d.get("requirements", []):
        evs = [Evidence(**e) for e in r.get("evidences", [])]
        r2 = {k: v for k, v in r.items() if k != "evidences"}
        reqs.append(Requirement(**r2, evidences=evs))

    vrs = [VerificationResult(**v) for v in d.get("verification_results", [])]
    frs = [FailureRecord(**f) for f in d.get("failure_records", [])]

    ar_dict = d.get("audit_result")
    audit_result = AuditResult(**ar_dict) if ar_dict else None

    base = {
        k: v for k, v in d.items()
        if k not in ("requirements", "verification_results", "failure_records", "audit_result")
    }
    return Task(
        **base,
        requirements=reqs,
        verification_results=vrs,
        failure_records=frs,
        audit_result=audit_result,
    )
