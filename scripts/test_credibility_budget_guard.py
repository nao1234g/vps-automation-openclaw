#!/usr/bin/env python3
"""Regression tests for the credibility budget guard."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


GOOD_REPORT = {
    "ok": True,
    "generated_at_epoch": 4102444800,
    "checks": {
        "prediction_deploy_gate": {
            "ok": True,
            "json": {
                "ok": True,
                "manifest_counts": {"published_total": 100, "truth_blocked": 0, "high_risk_unapproved": 10},
                "tracker_summary": {"orphan_oracle_articles": 0},
                "operational_metrics": {"distribution_allowed_ratio_pct": 45.0, "approval_backlog_ratio_pct": 10.0},
            }
        },
        "ecosystem_governance_audit": {"failed": 0},
        "synthetic_user_crawler": {"failed": 0},
        "site_ui_smoke_audit": {"summary": {"failed": 0}},
        "playwright_e2e_predictions": {"ok": True},
        "check_live_repo_drift": {"ok": True},
    },
}


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "change_freeze.json"
        report_path = Path(tmpdir) / "one_pass_completion_gate.json"
        os.environ["NOWPATTERN_CHANGE_FREEZE_STATE_PATH"] = str(state_path)

        import change_freeze_guard as freeze_guard  # noqa: WPS433
        import credibility_budget_guard as budget_guard  # noqa: WPS433

        report_path.write_text(json.dumps(GOOD_REPORT, ensure_ascii=False), encoding="utf-8")
        evaluation = budget_guard.evaluate_credibility_budget(GOOD_REPORT)
        assert evaluation["ok"], evaluation

        result = budget_guard.enforce_credibility_budget(report_path=report_path, actor="test")
        assert not result["freeze_applied"], result
        assert not freeze_guard.evaluate_change_freeze("public_release")["active"]

        bad_report = json.loads(json.dumps(GOOD_REPORT))
        bad_report["ok"] = False
        bad_report["checks"]["prediction_deploy_gate"]["json"]["manifest_counts"]["truth_blocked"] = 2
        bad_report["checks"]["check_live_repo_drift"]["ok"] = False
        report_path.write_text(json.dumps(bad_report, ensure_ascii=False), encoding="utf-8")

        evaluation = budget_guard.evaluate_credibility_budget(bad_report)
        assert not evaluation["ok"], evaluation
        assert "one_pass_completion_gate_not_green" in evaluation["violations"]
        assert "truth_blocked_remaining:2" in evaluation["violations"]
        assert "live_repo_drift_detected" in evaluation["violations"]

        embedded_red = json.loads(json.dumps(GOOD_REPORT))
        embedded_red["checks"]["prediction_deploy_gate"]["ok"] = False
        embedded_red["checks"]["prediction_deploy_gate"]["json"]["ok"] = False
        embedded_red["checks"]["prediction_deploy_gate"]["json"]["failures"] = ["governance_audit_failed:1"]
        evaluation = budget_guard.evaluate_credibility_budget(embedded_red)
        assert "prediction_deploy_gate_not_green" in evaluation["violations"]
        assert "embedded_prediction_deploy_gate_failed:governance_audit_failed:1" in evaluation["violations"]

        result = budget_guard.enforce_credibility_budget(report_path=report_path, actor="test")
        assert result["freeze_applied"], result
        assert freeze_guard.evaluate_change_freeze("public_release")["active"]
        assert freeze_guard.evaluate_change_freeze("distribution")["active"]

    print("PASS: credibility budget guard regression checks")


if __name__ == "__main__":
    main()
