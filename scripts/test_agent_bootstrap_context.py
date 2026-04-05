#!/usr/bin/env python3
"""Regression checks for the shared agent bootstrap context."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from agent_bootstrap_context import build_bootstrap_payload, format_bootstrap_summary  # noqa: E402
from mission_contract import MISSION_CONTRACT_VERSION, mission_contract_hash  # noqa: E402


def test_bootstrap_payload_contains_contract_and_state() -> None:
    payload = build_bootstrap_payload()
    assert payload["mission_contract_version"] == MISSION_CONTRACT_VERSION
    assert payload["mission_contract_hash"] == mission_contract_hash()
    assert payload["founder_os"] == "NAOTO OS"
    assert payload["pvqe"]["P"] == "判断精度"
    assert payload["read_order"][0] == "north_star"
    assert payload["north_star"]
    assert "current_state" in payload
    assert "mistake_registry" in payload
    assert "maturity_m1_progress_pct" in payload["current_state"]


def test_bootstrap_summary_is_human_readable() -> None:
    summary = format_bootstrap_summary()
    assert "Agent Bootstrap Context" in summary
    assert MISSION_CONTRACT_VERSION in summary
    assert mission_contract_hash() in summary
    assert "Founder OS: NAOTO OS" in summary
    assert "PVQE: P=判断精度" in summary
    assert "Current State:" in summary
    assert "Mistake Registry:" in summary
    assert "Prediction Maturity:" in summary


def run() -> None:
    test_bootstrap_payload_contains_contract_and_state()
    test_bootstrap_summary_is_human_readable()
    print("PASS: agent bootstrap context regression checks")


if __name__ == "__main__":
    run()
