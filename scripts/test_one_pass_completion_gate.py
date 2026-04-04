#!/usr/bin/env python3
"""Unit tests for one-pass completion threshold evaluation."""

from __future__ import annotations

from one_pass_completion_gate import evaluate_completion


def test_completion_passes_when_all_thresholds_are_met() -> None:
    failures, warnings = evaluate_completion(
        deploy_gate={
            "manifest_counts": {
                "published_total": 100,
                "truth_blocked": 0,
                "distribution_allowed": 40,
                "high_risk_unapproved": 20,
            },
            "tracker_summary": {"orphan_oracle_articles": 0},
            "operational_metrics": {
                "distribution_allowed_ratio_pct": 40.0,
                "approval_backlog_ratio_pct": 20.0,
            },
        },
        governance_failed=0,
        crawl_failed=0,
        ui_failed=0,
        e2e_ok=True,
        drift_ok=True,
        policy={
            "min_distribution_allowed_ratio_pct": 30.0,
            "max_high_risk_unapproved_ratio_pct": 25.0,
            "require_truth_blocked_zero": True,
            "require_orphan_zero": True,
        },
    )
    assert failures == []
    assert warnings == ["high_risk_unapproved_remaining:20/100"]


def test_completion_fails_when_distribution_and_orphans_are_bad() -> None:
    failures, _ = evaluate_completion(
        deploy_gate={
            "manifest_counts": {
                "published_total": 50,
                "truth_blocked": 1,
                "distribution_allowed": 4,
                "high_risk_unapproved": 30,
            },
            "tracker_summary": {"orphan_oracle_articles": 2},
            "operational_metrics": {
                "distribution_allowed_ratio_pct": 8.0,
                "approval_backlog_ratio_pct": 60.0,
            },
        },
        governance_failed=1,
        crawl_failed=1,
        ui_failed=2,
        e2e_ok=False,
        drift_ok=False,
        policy={
            "min_distribution_allowed_ratio_pct": 30.0,
            "max_high_risk_unapproved_ratio_pct": 25.0,
            "require_truth_blocked_zero": True,
            "require_orphan_zero": True,
        },
    )
    assert "truth_blocked_remaining:1" in failures
    assert "orphan_oracle_articles_remaining:2" in failures
    assert "distribution_allowed_ratio_below_threshold:8.0<30.0" in failures
    assert "high_risk_unapproved_ratio_exceeded:60.0>25.0" in failures
    assert "governance_failed:1" in failures
    assert "full_crawl_failed:1" in failures
    assert "site_ui_failed:2" in failures
    assert "prediction_e2e_failed" in failures
    assert "live_repo_drift_detected" in failures


def run() -> None:
    test_completion_passes_when_all_thresholds_are_met()
    test_completion_fails_when_distribution_and_orphans_are_bad()
    print("PASS: one-pass completion gate regression checks")


if __name__ == "__main__":
    run()
