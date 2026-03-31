#!/usr/bin/env python3
"""Single shared policy entrypoint for release/distribution decisions."""

from __future__ import annotations

from typing import Any

from article_release_guard import assert_release_ready, evaluate_release_blockers
from mission_contract import assert_mission_handshake

GOVERNOR_POLICY_VERSION = "2026-03-31-governor-v1"
MISSION_HANDSHAKE = assert_mission_handshake(
    "release_governor",
    "gate every public release and distribution decision under the founder mission contract",
)


def evaluate_governed_release(**kwargs: Any) -> dict[str, Any]:
    result = evaluate_release_blockers(**kwargs)
    result["governor_policy_version"] = GOVERNOR_POLICY_VERSION
    result["governed"] = True
    result["mission_contract_version"] = MISSION_HANDSHAKE["mission_contract_version"]
    result["mission_contract_hash"] = MISSION_HANDSHAKE["mission_contract_hash"]
    result["lexicon_version"] = MISSION_HANDSHAKE["lexicon_version"]
    return result


def assert_governed_release_ready(**kwargs: Any) -> dict[str, Any]:
    result = assert_release_ready(**kwargs)
    result["governor_policy_version"] = GOVERNOR_POLICY_VERSION
    result["governed"] = True
    result["mission_contract_version"] = MISSION_HANDSHAKE["mission_contract_version"]
    result["mission_contract_hash"] = MISSION_HANDSHAKE["mission_contract_hash"]
    result["lexicon_version"] = MISSION_HANDSHAKE["lexicon_version"]
    return result
