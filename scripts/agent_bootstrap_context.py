#!/usr/bin/env python3
"""Build the authoritative startup context every agent must read before acting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mission_contract import (
    MISSION_CONTRACT_VERSION,
    format_contract_summary,
    get_mission_contract,
    mission_contract_hash,
)
from report_authority import load_authoritative_json
from runtime_boundary import shared_or_local_path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORT_DIR = shared_or_local_path(
    script_file=__file__,
    shared_path="/opt/shared/reports",
    local_path=REPO_ROOT / "reports",
)
DATA_DIR = shared_or_local_path(
    script_file=__file__,
    shared_path="/opt/shared/data",
    local_path=REPO_ROOT / "data",
)

SNAPSHOT_PATH = REPORT_DIR / "content_release_snapshot.json"
GOVERNANCE_PATH = REPORT_DIR / "ecosystem_governance_audit.json"
MISTAKE_REGISTRY_PATH = DATA_DIR / "mistake_registry.json"


def _read_json(path: Path) -> dict[str, Any]:
    return load_authoritative_json(path)


def _summarize_mistake_registry(registry: dict[str, Any]) -> dict[str, Any]:
    mistakes = registry.get("mistakes")
    if not isinstance(mistakes, list):
        return {
            "mistakes": registry.get("mistakes"),
            "active": registry.get("active"),
            "critical_active": registry.get("critical_active"),
            "guard_coverage_pct": registry.get("guard_coverage_pct"),
            "test_coverage_pct": registry.get("test_coverage_pct"),
            "prevention_rate_pct": registry.get("prevention_rate_pct"),
        }

    total = len(mistakes)
    active_statuses = {"open", "active", "regressed"}
    active = sum(1 for item in mistakes if str(item.get("status") or "").lower() in active_statuses)
    critical_active = sum(
        1
        for item in mistakes
        if str(item.get("status") or "").lower() in active_statuses
        and str(item.get("severity") or "").lower() == "critical"
    )
    guarded = sum(1 for item in mistakes if item.get("linked_guard"))
    tested = sum(1 for item in mistakes if item.get("linked_test"))
    prevented = sum(1 for item in mistakes if str(item.get("status") or "").lower() == "prevented")

    return {
        "mistakes": total,
        "active": active,
        "critical_active": critical_active,
        "guard_coverage_pct": round((guarded / total) * 100, 1) if total else 0.0,
        "test_coverage_pct": round((tested / total) * 100, 1) if total else 0.0,
        "prevention_rate_pct": round((prevented / total) * 100, 1) if total else 0.0,
    }


def build_bootstrap_payload() -> dict[str, Any]:
    contract = get_mission_contract()
    snapshot = _read_json(SNAPSHOT_PATH)
    governance = _read_json(GOVERNANCE_PATH)
    registry = _read_json(MISTAKE_REGISTRY_PATH)
    tracker_summary = snapshot.get("tracker_summary", {}) if isinstance(snapshot, dict) else {}
    operational = snapshot.get("operational_metrics", {}) if isinstance(snapshot, dict) else {}
    manifest_counts = snapshot.get("manifest_counts", {}) if isinstance(snapshot, dict) else {}

    return {
        "mission_contract_version": MISSION_CONTRACT_VERSION,
        "mission_contract_hash": mission_contract_hash(contract),
        "owner": contract.get("owner"),
        "founder_os": (contract.get("founder_os") or {}).get("canonical_name"),
        "north_star": contract.get("north_star"),
        "pvqe": (contract.get("founder_os") or {}).get("pvqe", {}),
        "read_order": (contract.get("founder_os") or {}).get("read_order", []),
        "system_names": contract.get("system_names", []),
        "lexicon_version": contract.get("brand_contract", {}).get("lexicon_version"),
        "non_negotiables": contract.get("non_negotiables", []),
        "current_state": {
            "release_snapshot_generated_at": snapshot.get("generated_at"),
            "manifest_generated_at": snapshot.get("manifest_generated_at"),
            "tracker_generated_at": snapshot.get("tracker_generated_at"),
            "published_total": manifest_counts.get("published_total"),
            "public_truth_allowed": manifest_counts.get("public_truth_allowed"),
            "distribution_allowed": manifest_counts.get("distribution_allowed"),
            "distribution_blocked": manifest_counts.get("distribution_blocked"),
            "truth_blocked": manifest_counts.get("truth_blocked"),
            "high_risk_unapproved": manifest_counts.get("high_risk_unapproved"),
            "formal_prediction_total": tracker_summary.get("formal_prediction_total"),
            "ghost_published_posts_release_scope": tracker_summary.get("ghost_published_posts_release_scope"),
            "orphan_oracle_articles": tracker_summary.get("orphan_oracle_articles"),
            "distribution_allowed_ratio_pct": operational.get("distribution_allowed_ratio_pct"),
            "approval_backlog_ratio_pct": operational.get("approval_backlog_ratio_pct"),
            "governance_failed": governance.get("failed"),
            "governance_total": governance.get("total"),
        },
        "mistake_registry": _summarize_mistake_registry(registry),
        "required_sources_of_truth": contract.get("source_docs", []),
        "required_artifacts": contract.get("required_artifacts", {}),
    }


def format_bootstrap_summary(payload: dict[str, Any] | None = None) -> str:
    data = payload or build_bootstrap_payload()
    state = data["current_state"]
    registry = data["mistake_registry"]
    lines = [
        "Agent Bootstrap Context",
        f"Mission: {data['mission_contract_version']}",
        f"Hash: {data['mission_contract_hash']}",
        f"Founder OS: {data.get('founder_os')}",
        f"North Star: {data['north_star']}",
        (
            "PVQE: "
            f"P={data.get('pvqe', {}).get('P')} | "
            f"V={data.get('pvqe', {}).get('V')} | "
            f"Q={data.get('pvqe', {}).get('Q')} | "
            f"E={data.get('pvqe', {}).get('E')}"
        ),
        f"Lexicon: {data['lexicon_version']}",
        (
            "Current State: "
            f"published={state.get('published_total')} | "
            f"truth_allowed={state.get('public_truth_allowed')} | "
            f"distribution_allowed={state.get('distribution_allowed')} | "
            f"truth_blocked={state.get('truth_blocked')} | "
            f"orphans={state.get('orphan_oracle_articles')}"
        ),
        (
            "Mistake Registry: "
            f"mistakes={registry.get('mistakes')} | "
            f"active={registry.get('active')} | "
            f"critical_active={registry.get('critical_active')} | "
            f"guard_coverage={registry.get('guard_coverage_pct')}% | "
            f"test_coverage={registry.get('test_coverage_pct')}%"
        ),
        f"Read Order: {' -> '.join(data.get('read_order') or [])}",
        "Contract Summary:",
        format_contract_summary(),
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the authoritative agent bootstrap context.")
    parser.add_argument("--summary", action="store_true", help="Print a readable summary")
    parser.add_argument("--json", action="store_true", help="Print the JSON payload")
    args = parser.parse_args()

    payload = build_bootstrap_payload()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_bootstrap_summary(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
