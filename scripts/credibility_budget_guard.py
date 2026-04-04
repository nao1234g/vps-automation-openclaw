#!/usr/bin/env python3
"""Freeze governed release surfaces when credibility budget is exceeded."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from change_freeze_guard import enable_change_freeze, evaluate_change_freeze
from report_authority import load_authoritative_json


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
IS_LIVE_RUNTIME = Path(__file__).resolve().as_posix().startswith("/opt/shared/")
REPORT_DIR = Path("/opt/shared/reports") if IS_LIVE_RUNTIME else REPO_ROOT / "reports"
DEFAULT_SCOPES = ["public_release", "distribution", "governed_write"]
DEFAULT_MAX_ONE_PASS_AGE_SECONDS = int(os.environ.get("NOWPATTERN_MAX_ONE_PASS_AGE_SECONDS") or 6 * 60 * 60)


def default_report_path() -> Path:
    override = os.environ.get("NOWPATTERN_ONE_PASS_REPORT_PATH")
    if override:
        return Path(override)
    return REPORT_DIR / "one_pass_completion_gate.json"


def _parse_iso_utc(value: str) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _load_report(path: Path) -> dict[str, Any]:
    return load_authoritative_json(path, sync_local=True)


def evaluate_credibility_budget(report: dict[str, Any]) -> dict[str, Any]:
    violations: list[str] = []
    warnings: list[str] = []

    if not report:
        violations.append("missing_one_pass_completion_report")
        return {"violations": violations, "warnings": warnings, "ok": False}

    if not bool(report.get("ok")):
        violations.append("one_pass_completion_gate_not_green")
    generated_at_epoch = int(report.get("generated_at_epoch") or 0)
    if generated_at_epoch:
        age_seconds = int(time.time()) - generated_at_epoch
        if age_seconds > DEFAULT_MAX_ONE_PASS_AGE_SECONDS:
            violations.append(f"one_pass_completion_gate_stale:{age_seconds}>{DEFAULT_MAX_ONE_PASS_AGE_SECONDS}")
    elif report.get("generated_at"):
        parsed = _parse_iso_utc(str(report.get("generated_at")))
        if parsed:
            age_seconds = int(time.time() - parsed.timestamp())
            if age_seconds > DEFAULT_MAX_ONE_PASS_AGE_SECONDS:
                violations.append(f"one_pass_completion_gate_stale:{age_seconds}>{DEFAULT_MAX_ONE_PASS_AGE_SECONDS}")
    else:
        warnings.append("missing_one_pass_generated_at")

    checks = report.get("checks") or {}
    deploy_gate_check = checks.get("prediction_deploy_gate") or {}
    deploy_gate = (deploy_gate_check.get("json") or {})
    governance = checks.get("ecosystem_governance_audit") or {}
    crawl = checks.get("synthetic_user_crawler") or {}
    smoke = checks.get("site_ui_smoke_audit") or {}
    e2e = checks.get("playwright_e2e_predictions") or {}
    drift = checks.get("check_live_repo_drift") or {}
    if not bool(deploy_gate_check.get("ok")):
        violations.append("prediction_deploy_gate_not_green")
    if deploy_gate and not bool(deploy_gate.get("ok", True)):
        failures = deploy_gate.get("failures") or []
        if failures:
            violations.append("embedded_prediction_deploy_gate_failed:" + ",".join(str(item) for item in failures))
        else:
            violations.append("embedded_prediction_deploy_gate_not_green")

    manifest_counts = deploy_gate.get("manifest_counts") or {}
    tracker_summary = deploy_gate.get("tracker_summary") or {}
    operational = deploy_gate.get("operational_metrics") or {}

    if int(manifest_counts.get("truth_blocked") or 0) > 0:
        violations.append(f"truth_blocked_remaining:{manifest_counts.get('truth_blocked')}")
    if int((tracker_summary.get("orphan_oracle_articles") or 0)) > 0:
        violations.append(f"orphan_oracle_articles_remaining:{tracker_summary.get('orphan_oracle_articles')}")
    if int(governance.get("failed") or 0) > 0:
        violations.append(f"governance_failed:{governance.get('failed')}")
    if int(crawl.get("failed") or 0) > 0:
        violations.append(f"synthetic_crawl_failed:{crawl.get('failed')}")
    if int((smoke.get("summary") or {}).get("failed") or 0) > 0:
        violations.append(f"site_ui_failed:{(smoke.get('summary') or {}).get('failed')}")
    if not bool(e2e.get("ok")):
        violations.append("prediction_e2e_failed")
    if not bool(drift.get("ok")):
        violations.append("live_repo_drift_detected")

    high_risk_unapproved = int(manifest_counts.get("high_risk_unapproved") or 0)
    published_total = int(manifest_counts.get("published_total") or 0)
    ratio = float(operational.get("distribution_allowed_ratio_pct") or 0.0)
    backlog_ratio = float(operational.get("approval_backlog_ratio_pct") or 0.0)
    if high_risk_unapproved and published_total:
        warnings.append(f"high_risk_unapproved_backlog:{high_risk_unapproved}/{published_total}")
    if ratio > 0:
        warnings.append(f"distribution_allowed_ratio_pct:{ratio}")
    if backlog_ratio > 0:
        warnings.append(f"approval_backlog_ratio_pct:{backlog_ratio}")

    return {
        "violations": violations,
        "warnings": warnings,
        "ok": not violations,
    }


def enforce_credibility_budget(
    *,
    actor: str = "credibility_budget_guard",
    report_path: Path | None = None,
) -> dict[str, Any]:
    resolved_report_path = report_path or default_report_path()
    report = _load_report(resolved_report_path)
    evaluation = evaluate_credibility_budget(report)
    freeze_state = evaluate_change_freeze("public_release")
    result: dict[str, Any] = {
        "report_path": str(resolved_report_path),
        "evaluation": evaluation,
        "freeze_before": freeze_state,
        "freeze_applied": False,
        "freeze_state": freeze_state.get("state") or {},
    }
    if evaluation["ok"]:
        return result

    reason = "credibility_budget_exceeded:" + ",".join(evaluation["violations"])
    state = enable_change_freeze(
        reason=reason,
        enabled_by=actor,
        scopes=list(DEFAULT_SCOPES),
        notes="auto-freeze triggered by credibility budget guard",
    )
    result["freeze_applied"] = True
    result["freeze_state"] = state
    return result

def assert_credibility_budget_clear(report_path: Path | None = None) -> dict[str, Any]:
    resolved_report_path = report_path or default_report_path()
    report = _load_report(resolved_report_path)
    evaluation = evaluate_credibility_budget(report)
    if not evaluation["ok"]:
        raise ValueError(
            "CREDIBILITY_BUDGET_EXCEEDED:"
            f"report_path={resolved_report_path}; violations={','.join(evaluation['violations'])}"
        )
    return evaluation


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate and optionally enforce the credibility budget.")
    parser.add_argument("--report-path", default=str(default_report_path()), help="Path to one_pass_completion_gate.json")
    parser.add_argument("--status", action="store_true", help="Print evaluation only")
    parser.add_argument("--enforce", action="store_true", help="Enable change freeze when the budget is exceeded")
    parser.add_argument("--actor", default="credibility_budget_guard", help="Actor recorded when enforcing freeze")
    args = parser.parse_args()

    report_path = Path(args.report_path)
    if args.enforce:
        payload = enforce_credibility_budget(actor=args.actor, report_path=report_path)
    else:
        report = _load_report(report_path)
        payload = {
            "report_path": str(report_path),
            "evaluation": evaluate_credibility_budget(report),
            "freeze_state": evaluate_change_freeze("public_release"),
        }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    evaluation = payload.get("evaluation") or {}
    return 0 if evaluation.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
