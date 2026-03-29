#!/usr/bin/env python3
"""Hard gate for prediction_db state/scoring integrity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prediction_state_utils import (
    canonical_prediction_status,
    is_final_verdict,
    normalize_score_tier,
    normalize_verdict,
)
from refresh_prediction_db_meta import DEFAULT_DB_PATH, canonicalize_prediction_statuses, compute_meta


VALID_CANONICAL_STATUSES = {
    "OPEN",
    "ACTIVE",
    "RESOLVING",
    "EXPIRED_UNRESOLVED",
    "RESOLVED",
    "DISPUTED",
}


def collect_issues(payload: dict) -> list[str]:
    preds = payload.get("predictions", [])
    issues: list[str] = []

    for pred in preds:
        prediction_id = str(pred.get("prediction_id") or "UNKNOWN")
        raw_status = str(pred.get("status") or "")
        canonical_status = canonical_prediction_status(pred)
        verdict = normalize_verdict(pred.get("verdict"))
        score_tier = normalize_score_tier(pred.get("official_score_tier"))
        has_resolved_at = bool(pred.get("resolved_at"))
        has_brier = pred.get("brier_score") is not None

        if canonical_status not in VALID_CANONICAL_STATUSES:
            issues.append(
                f"{prediction_id}: unknown canonical status {canonical_status!r} (raw={raw_status!r})"
            )
        if raw_status != canonical_status:
            issues.append(
                f"{prediction_id}: status mismatch raw={raw_status!r} canonical={canonical_status!r}"
            )
        if (has_resolved_at or has_brier) and not is_final_verdict(verdict):
            issues.append(
                f"{prediction_id}: resolved markers present without final verdict "
                f"(verdict={verdict!r}, resolved_at={has_resolved_at}, brier={has_brier})"
            )
        if is_final_verdict(verdict) and canonical_status != "RESOLVED":
            issues.append(
                f"{prediction_id}: final verdict {verdict!r} but canonical status is {canonical_status!r}"
            )
        if score_tier == "NOT_SCORABLE" and verdict not in {"NOT_SCORED", "NONE", ""}:
            issues.append(
                f"{prediction_id}: NOT_SCORABLE tier paired with verdict {verdict!r}"
            )

    expected_payload = json.loads(json.dumps(payload, ensure_ascii=False))
    canonicalize_prediction_statuses(expected_payload)
    expected_meta, _summary = compute_meta(expected_payload)
    actual_meta = payload.get("meta", {}) or {}
    compare_keys = (
        "total_predictions",
        "scored_predictions",
        "accuracy_pct",
        "official_brier_avg",
        "resolution_coverage_pct",
        "status_counts",
        "official_brier_avg_initial_prob",
        "official_brier_avg_initial_prob_n",
        "accuracy_formula",
        "accuracy_n",
        "accuracy_hit",
        "accuracy_miss",
        "accuracy_ci_lo",
        "accuracy_ci_hi",
    )
    for key in compare_keys:
        actual_value = actual_meta.get(key)
        expected_value = expected_meta.get(key)
        if actual_value != expected_value:
            issues.append(
                f"meta.{key} mismatch: actual={actual_value!r} expected={expected_value!r}"
            )

    actual_tier_counts = (
        actual_meta.get("score_provenance_summary", {}) or {}
    ).get("tier_counts")
    expected_tier_counts = (
        expected_meta.get("score_provenance_summary", {}) or {}
    ).get("tier_counts")
    if actual_tier_counts != expected_tier_counts:
        issues.append(
            "meta.score_provenance_summary.tier_counts mismatch: "
            f"actual={actual_tier_counts!r} expected={expected_tier_counts!r}"
        )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prediction state/scoring hard gate.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to prediction_db.json")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    db_path = Path(args.db)
    payload = json.loads(db_path.read_text(encoding="utf-8"))
    issues = collect_issues(payload)
    report = {
        "db": str(db_path),
        "prediction_count": len(payload.get("predictions", [])),
        "issue_count": len(issues),
        "issues": issues,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if issues:
            print(f"[PREDICTION STATE GATE] FAIL ({len(issues)} issues)")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(
                f"[PREDICTION STATE GATE] PASS "
                f"({len(payload.get('predictions', []))} predictions, no state/scoring mismatches)"
            )

    return 2 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
