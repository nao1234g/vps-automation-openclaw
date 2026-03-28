#!/usr/bin/env python3
"""
completion_engine/__init__.py
完遂エンジン — Package Init

Public API:
    from completion_engine import (
        Task, Requirement, Evidence,
        TaskResolver,
        StateMachine,
        RequirementContract,
        EvidenceGate,
        AuditGate,
        FinalizationGuard,
        FailureRecovery,
        ReportGenerator,
    )
"""
from __future__ import annotations

# Schema types
from completion_engine.schema import (
    AuditResult,
    Evidence,
    EvidenceStatus,
    EvidenceType,
    FailureRecord,
    FinalizationStatus,
    Phase,
    Priority,
    Requirement,
    RequirementCategory,
    RequirementStatus,
    Task,
    TaskSource,
    VerificationResult,
    task_from_dict,
    task_to_dict,
)

# Core engines
from completion_engine.task_resolver import TaskResolver
from completion_engine.state_machine import StateMachine, phase_progress_bar
from completion_engine.requirement_contract import RequirementContract
from completion_engine.evidence_gate import EvidenceGate
from completion_engine.audit_gate import AuditGate
from completion_engine.finalization_guard import FinalizationGuard
from completion_engine.failure_recovery import FailureRecovery
from completion_engine.report_generator import ReportGenerator

__all__ = [
    # Schema
    "Task",
    "Requirement",
    "Evidence",
    "VerificationResult",
    "AuditResult",
    "FailureRecord",
    # Enums
    "Phase",
    "Priority",
    "RequirementCategory",
    "RequirementStatus",
    "EvidenceType",
    "EvidenceStatus",
    "FinalizationStatus",
    "TaskSource",
    # Helpers
    "task_to_dict",
    "task_from_dict",
    # Engines
    "TaskResolver",
    "StateMachine",
    "phase_progress_bar",
    "RequirementContract",
    "EvidenceGate",
    "AuditGate",
    "FinalizationGuard",
    "FailureRecovery",
    "ReportGenerator",
]
