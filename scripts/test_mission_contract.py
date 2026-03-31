#!/usr/bin/env python3
"""Regression checks for the canonical mission contract and handshake."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from mission_contract import (  # noqa: E402
    MISSION_CONTRACT_VERSION,
    assert_mission_handshake,
    format_contract_summary,
    get_mission_contract,
    mission_contract_hash,
)


def test_contract_has_expected_core_fields() -> None:
    contract = get_mission_contract()
    assert contract["version"] == MISSION_CONTRACT_VERSION
    assert contract["owner"] == "Naoto"
    assert contract["founder_os"]["canonical_name"] == "NAOTO OS"
    assert contract["founder_os"]["pvqe"]["P"] == "判断精度"
    assert "Truth first" in contract["non_negotiables"][0]
    assert contract["brand_contract"]["lexicon_version"]


def test_handshake_carries_contract_hash() -> None:
    receipt = assert_mission_handshake("test_agent", "verify mission contract", record=False)
    assert receipt["mission_contract_version"] == MISSION_CONTRACT_VERSION
    assert receipt["mission_contract_hash"] == mission_contract_hash()
    assert receipt["founder_os"] == "NAOTO OS"
    assert receipt["pvqe"]["P"] == "判断精度"
    assert "bootstrap_context_hash" in receipt
    assert receipt["lexicon_version"]


def test_summary_is_human_readable() -> None:
    summary = format_contract_summary()
    assert MISSION_CONTRACT_VERSION in summary
    assert mission_contract_hash() in summary
    assert "Founder OS: NAOTO OS" in summary
    assert "PVQE: P=判断精度" in summary
    assert "Non-negotiables" in summary


def run() -> None:
    test_contract_has_expected_core_fields()
    test_handshake_carries_contract_hash()
    test_summary_is_human_readable()
    print("PASS: mission contract regression checks")


if __name__ == "__main__":
    run()
