#!/usr/bin/env python3
"""Canonical mission contract and handshake utilities for all Nowpattern agents."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from canonical_public_lexicon import LEXICON_VERSION, get_brand_copy
from runtime_boundary import shared_or_local_path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORT_DIR = shared_or_local_path(
    script_file=__file__,
    shared_path="/opt/shared/reports",
    local_path=REPO_ROOT / "reports",
)
HANDSHAKE_DIR = REPORT_DIR / "mission_handshakes"

MISSION_CONTRACT_VERSION = "2026-03-31-naoto-mission-v3"

MISSION_CONTRACT: dict[str, Any] = {
    "version": MISSION_CONTRACT_VERSION,
    "owner": "Naoto",
    "system_names": [
        "NAOTO OS",
        "Naoto Intelligence OS",
        "Nowpattern",
    ],
    "founder_os": {
        "canonical_name": "NAOTO OS",
        "read_order": [
            "north_star",
            "pvqe",
            "principles",
            "truth_protocol",
            "public_lexicon",
            "release_snapshot",
            "mistake_registry",
        ],
        "pvqe": {
            "P": "判断精度",
            "V": "価値密度",
            "Q": "行動量",
            "E": "波及力",
        },
        "principle_docs": [
            ".claude/rules/NORTH_STAR.md",
            ".claude/rules/OPERATING_PRINCIPLES.md",
            "docs/TRUTH_PROTOCOL.md",
            "docs/AGENT_WISDOM.md",
        ],
    },
    "north_star": "Nowpattern is a verifiable forecast platform.",
    "brand_contract": {
        "ja_platform_name": get_brand_copy("ja")["platform_name"],
        "en_platform_name": get_brand_copy("en")["platform_name"],
        "ja_oracle_subtitle": get_brand_copy("ja")["oracle_subtitle"],
        "en_oracle_subtitle": get_brand_copy("en")["oracle_subtitle"],
        "lexicon_version": LEXICON_VERSION,
    },
    "non_negotiables": [
        "Truth first. No unsupported factual claims may reach a public surface.",
        "No source-free public content. Broken or empty source sections are release blockers.",
        "No internal-only diagnostics, counts, or implementation leakage on public UI.",
        "Same-language integrity first. Public tracker cards must not silently fall back across languages.",
        "All public release and distribution must pass the central release governor.",
        "High-risk topics require explicit human approval before distribution.",
        "Every incident must become a rule, a regression test, and a monitor target.",
        "Shared vocabulary is canonical. Status, metrics, and brand labels must come from one lexicon.",
        "Synthetic user checks run before and after public changes.",
        "If uncertainty remains, the system must stop rather than improvise.",
    ],
    "high_risk_topics": [
        "frontier-ai",
        "war-conflict",
        "financial-crisis",
        "regulation",
        "election",
        "macro-shock",
    ],
    "required_artifacts": {
        "release_snapshot": "reports/content_release_snapshot.json",
        "public_lexicon": "scripts/canonical_public_lexicon.py",
        "mistake_registry": "data/mistake_registry.json",
        "known_mistakes": "docs/KNOWN_MISTAKES.md",
    },
    "source_docs": [
        "docs/NAOTO_OS_OPERATING_STACK.md",
        "docs/FOUNDER_CONSTITUTION.md",
        "docs/AGENT_CONSTITUTION.md",
        ".claude/rules/NORTH_STAR.md",
        "docs/TRUTH_PROTOCOL.md",
        "docs/PREDICTION_SYSTEM_NORTH_STAR.md",
        "docs/AGENT_WISDOM.md",
    ],
}


def get_mission_contract() -> dict[str, Any]:
    return json.loads(json.dumps(MISSION_CONTRACT, ensure_ascii=False))


def mission_contract_hash(contract: dict[str, Any] | None = None) -> str:
    payload = contract or get_mission_contract()
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_mission_handshake(agent_name: str, purpose: str) -> dict[str, Any]:
    contract = get_mission_contract()
    bootstrap_hash = ""
    bootstrap_generated_at = ""
    try:
        from agent_bootstrap_context import build_bootstrap_payload

        bootstrap = build_bootstrap_payload()
        bootstrap_generated_at = (
            (bootstrap.get("current_state") or {}).get("release_snapshot_generated_at") or ""
        )
        canonical = json.dumps(bootstrap, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        bootstrap_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    except Exception:
        bootstrap_hash = ""
        bootstrap_generated_at = ""
    return {
        "agent_name": agent_name,
        "purpose": purpose,
        "mission_contract_version": contract["version"],
        "mission_contract_hash": mission_contract_hash(contract),
        "lexicon_version": contract["brand_contract"]["lexicon_version"],
        "north_star": contract["north_star"],
        "founder_os": contract["founder_os"]["canonical_name"],
        "pvqe": contract["founder_os"]["pvqe"],
        "bootstrap_context_hash": bootstrap_hash,
        "bootstrap_release_generated_at": bootstrap_generated_at,
        "non_negotiable_count": len(contract["non_negotiables"]),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def record_mission_handshake(receipt: dict[str, Any]) -> None:
    HANDSHAKE_DIR.mkdir(parents=True, exist_ok=True)
    path = HANDSHAKE_DIR / f"{receipt['agent_name']}.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_mission_handshake(agent_name: str, purpose: str, *, record: bool = True) -> dict[str, Any]:
    receipt = build_mission_handshake(agent_name=agent_name, purpose=purpose)
    if record:
        record_mission_handshake(receipt)
    return receipt


def format_contract_summary() -> str:
    contract = get_mission_contract()
    lines = [
        f"Mission Contract: {contract['version']}",
        f"Hash: {mission_contract_hash(contract)}",
        f"Founder OS: {contract['founder_os']['canonical_name']}",
        f"North Star: {contract['north_star']}",
        (
            "PVQE: "
            f"P={contract['founder_os']['pvqe']['P']} | "
            f"V={contract['founder_os']['pvqe']['V']} | "
            f"Q={contract['founder_os']['pvqe']['Q']} | "
            f"E={contract['founder_os']['pvqe']['E']}"
        ),
        f"Lexicon: {contract['brand_contract']['lexicon_version']}",
        "Non-negotiables:",
    ]
    lines.extend(f"- {item}" for item in contract["non_negotiables"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read or record the canonical mission contract.")
    parser.add_argument("--summary", action="store_true", help="Print a readable mission contract summary")
    parser.add_argument("--json", action="store_true", help="Print the mission contract JSON payload")
    parser.add_argument("--agent", help="Optional agent name to record a handshake")
    parser.add_argument("--purpose", help="Purpose string when recording a handshake")
    args = parser.parse_args()

    if args.agent:
        receipt = assert_mission_handshake(args.agent, args.purpose or "unspecified")
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0

    if args.json:
        print(json.dumps(get_mission_contract(), ensure_ascii=False, indent=2))
        return 0

    print(format_contract_summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
