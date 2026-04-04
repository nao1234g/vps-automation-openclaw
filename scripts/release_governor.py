#!/usr/bin/env python3
"""Single shared policy entrypoint for release/distribution decisions."""

from __future__ import annotations

from typing import Any

from article_release_guard import assert_release_ready, evaluate_release_blockers
from change_freeze_guard import assert_change_window, evaluate_change_freeze
from credibility_budget_guard import assert_credibility_budget_clear, evaluate_credibility_budget
from mission_contract import assert_mission_handshake

GOVERNOR_POLICY_VERSION = "2026-04-02-governor-v2"
MISSION_HANDSHAKE = assert_mission_handshake(
    "release_governor",
    "gate every public release and distribution decision under the founder mission contract",
)


def evaluate_governed_release(**kwargs: Any) -> dict[str, Any]:
    result = evaluate_release_blockers(**kwargs)
    channel = str(kwargs.get("channel") or "public").strip().lower()
    freeze_scope = "distribution" if channel == "distribution" else "public_release"
    freeze_state = evaluate_change_freeze(freeze_scope)
    credibility_state = {"ok": True, "violations": [], "warnings": []}
    try:
        credibility_state = assert_credibility_budget_clear()
        credibility_ok = True
    except ValueError as exc:
        credibility_ok = False
        credibility_state = {
            "ok": False,
            "violations": [str(exc)],
            "warnings": [],
        }
    result["governor_policy_version"] = GOVERNOR_POLICY_VERSION
    result["governed"] = True
    result["change_freeze_active"] = freeze_state["active"]
    result["change_freeze_scope"] = freeze_scope
    result["change_freeze_reason"] = (freeze_state.get("state") or {}).get("reason", "")
    result["credibility_budget_ok"] = credibility_ok
    result["credibility_budget"] = credibility_state
    result["mission_contract_version"] = MISSION_HANDSHAKE["mission_contract_version"]
    result["mission_contract_hash"] = MISSION_HANDSHAKE["mission_contract_hash"]
    result["lexicon_version"] = MISSION_HANDSHAKE["lexicon_version"]
    return result


def assert_governed_release_ready(**kwargs: Any) -> dict[str, Any]:
    channel = str(kwargs.get("channel") or "public").strip().lower()
    status = str(kwargs.get("status") or "published").strip().lower()
    freeze_scope = "distribution" if channel == "distribution" else "public_release"
    assert_change_window(
        scope=freeze_scope,
        actor="release_governor",
        purpose=f"status={status}; channel={channel}",
    )
    assert_credibility_budget_clear()
    result = assert_release_ready(**kwargs)
    result["governor_policy_version"] = GOVERNOR_POLICY_VERSION
    result["governed"] = True
    result["change_freeze_active"] = False
    result["change_freeze_scope"] = freeze_scope
    result["change_freeze_reason"] = ""
    result["credibility_budget_ok"] = True
    result["credibility_budget"] = {"ok": True, "violations": [], "warnings": []}
    result["mission_contract_version"] = MISSION_HANDSHAKE["mission_contract_version"]
    result["mission_contract_hash"] = MISSION_HANDSHAKE["mission_contract_hash"]
    result["lexicon_version"] = MISSION_HANDSHAKE["lexicon_version"]
    return result
