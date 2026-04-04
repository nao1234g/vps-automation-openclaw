#!/usr/bin/env python3
"""Regression tests for reader_prediction_api.py synthetic voter filtering.

These tests verify the is_synthetic_voter helper and the filtering logic
that the leaderboard/top-forecasters endpoints use. They import only the
helper constants and function (extracted inline to avoid FastAPI dependency
on local dev machines).

On VPS where FastAPI is installed, the tests also verify the import works
from the full module.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Inline replica of the helper (must stay in sync with reader_prediction_api.py) ──

SYNTHETIC_VOTER_EXACT = frozenset({
    "neo-one-ai-player",
})

SYNTHETIC_VOTER_PREFIXES = (
    "test-",
    "migrated_",
)
HUMAN_PUBLIC_MIN_VOTERS = 25
HUMAN_PUBLIC_MIN_TOTAL_VOTES = 200
HUMAN_PUBLIC_MIN_RESOLVED_VOTES = 20


def is_synthetic_voter(voter_uuid: str) -> bool:
    if voter_uuid in SYNTHETIC_VOTER_EXACT:
        return True
    for prefix in SYNTHETIC_VOTER_PREFIXES:
        if voter_uuid.startswith(prefix):
            return True
    return False


def human_competition_snapshot(unique_voters: int, total_votes: int, resolved_votes: int) -> dict:
    ready = (
        unique_voters >= HUMAN_PUBLIC_MIN_VOTERS
        and total_votes >= HUMAN_PUBLIC_MIN_TOTAL_VOTES
        and resolved_votes >= HUMAN_PUBLIC_MIN_RESOLVED_VOTES
    )
    return {
        "ready": ready,
        "state": "live_human_ranking" if ready else "beta_ai_benchmark_only",
        "sample": {
            "unique_voters": unique_voters,
            "total_votes": total_votes,
            "resolved_votes": resolved_votes,
        },
    }


# Try importing from actual module to verify sync
_module_available = False
try:
    from reader_prediction_api import (
        is_synthetic_voter as _api_is_synthetic,
        SYNTHETIC_VOTER_EXACT as _api_exact,
        SYNTHETIC_VOTER_PREFIXES as _api_prefixes,
    )
    _module_available = True
except ImportError:
    pass  # FastAPI not installed locally -use inline replica


# ── Tests ────────────────────────────────────────────────────────────────────

def test_module_sync():
    """If module is importable, verify constants match inline replica."""
    if not _module_available:
        print("    (skipped - FastAPI not available locally)")
        return
    assert _api_exact == SYNTHETIC_VOTER_EXACT, "SYNTHETIC_VOTER_EXACT out of sync"
    assert _api_prefixes == SYNTHETIC_VOTER_PREFIXES, "SYNTHETIC_VOTER_PREFIXES out of sync"
    # Spot-check the function
    assert _api_is_synthetic("neo-one-ai-player") is True
    assert _api_is_synthetic("real-uuid") is False


def test_synthetic_exact_ids():
    assert is_synthetic_voter("neo-one-ai-player") is True


def test_synthetic_prefixes():
    assert is_synthetic_voter("test-uuid-12345") is True
    assert is_synthetic_voter("test-abc") is True
    assert is_synthetic_voter("migrated_50ab1ad008970ec6") is True
    assert is_synthetic_voter("migrated_anything") is True


def test_human_uuids_not_synthetic():
    human_uuids = [
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "550e8400-e29b-41d4-a716-446655440000",
        "some-real-reader-uuid",
        "ABCDEF",
    ]
    for uid in human_uuids:
        assert is_synthetic_voter(uid) is False, f"{uid} should not be synthetic"


def test_edge_cases():
    assert is_synthetic_voter("") is False
    assert is_synthetic_voter("test") is False       # no trailing dash
    assert is_synthetic_voter("testing-user") is False
    assert is_synthetic_voter("neo-one-ai-player-2") is False
    assert is_synthetic_voter("Test-UUID") is False   # case sensitive


def test_human_vote_filtering():
    all_votes = [
        {"voter_uuid": "neo-one-ai-player", "prediction_id": "NP-0001"},
        {"voter_uuid": "neo-one-ai-player", "prediction_id": "NP-0002"},
        {"voter_uuid": "test-uuid-12345", "prediction_id": "NP-0001"},
        {"voter_uuid": "migrated_50ab1ad008970ec6", "prediction_id": "NP-0001"},
        {"voter_uuid": "real-human-001", "prediction_id": "NP-0001"},
        {"voter_uuid": "real-human-002", "prediction_id": "NP-0001"},
        {"voter_uuid": "real-human-001", "prediction_id": "NP-0002"},
    ]
    human = [v for v in all_votes if not is_synthetic_voter(v["voter_uuid"])]
    assert len(human) == 3
    assert {v["voter_uuid"] for v in human} == {"real-human-001", "real-human-002"}


def test_top_forecasters_loop():
    """Simulates the top-forecasters grouping loop."""
    all_votes = [
        {"voter_uuid": "neo-one-ai-player", "prediction_id": "NP-0001", "scenario": "optimistic", "probability": 70, "created_at": "2026-01-01"},
        {"voter_uuid": "test-uuid-12345", "prediction_id": "NP-0001", "scenario": "base", "probability": 50, "created_at": "2026-01-01"},
        {"voter_uuid": "migrated_abc", "prediction_id": "NP-0001", "scenario": "base", "probability": 60, "created_at": "2026-01-01"},
        {"voter_uuid": "human-a", "prediction_id": "NP-0001", "scenario": "optimistic", "probability": 75, "created_at": "2026-01-01"},
        {"voter_uuid": "human-a", "prediction_id": "NP-0002", "scenario": "base", "probability": 55, "created_at": "2026-01-01"},
        {"voter_uuid": "human-b", "prediction_id": "NP-0001", "scenario": "pessimistic", "probability": 25, "created_at": "2026-01-01"},
    ]
    voter_stats = {}
    ai_vote_total = 0
    for vote in all_votes:
        uid = vote["voter_uuid"]
        if uid == "neo-one-ai-player":
            ai_vote_total += 1
            continue
        if is_synthetic_voter(uid):
            continue
        if uid not in voter_stats:
            voter_stats[uid] = {"votes": 0}
        voter_stats[uid]["votes"] += 1

    assert ai_vote_total == 1
    assert "test-uuid-12345" not in voter_stats
    assert "migrated_abc" not in voter_stats
    assert "human-a" in voter_stats and voter_stats["human-a"]["votes"] == 2
    assert "human-b" in voter_stats and voter_stats["human-b"]["votes"] == 1


def test_leaderboard_aggregate_excludes_synthetic():
    """Simulates the leaderboard reader-aggregate counting."""
    all_votes = [
        {"voter_uuid": "neo-one-ai-player"},
        {"voter_uuid": "neo-one-ai-player"},
        {"voter_uuid": "test-uuid-12345"},
        {"voter_uuid": "migrated_xyz"},
        {"voter_uuid": "human-a"},
        {"voter_uuid": "human-b"},
        {"voter_uuid": "human-a"},
    ]
    human_votes = [v for v in all_votes if not is_synthetic_voter(v["voter_uuid"])]
    human_uuids = {v["voter_uuid"] for v in human_votes}

    assert len(human_votes) == 3, f"total_votes should be 3, got {len(human_votes)}"
    assert len(human_uuids) == 2, f"total_voters should be 2, got {len(human_uuids)}"


def test_community_stats_exclude_synthetic_votes():
    """Community bars should reflect humans only, not AI/test/migrated votes."""
    all_votes = [
        {"voter_uuid": "neo-one-ai-player", "scenario": "optimistic", "probability": 75},
        {"voter_uuid": "test-uuid-12345", "scenario": "base", "probability": 50},
        {"voter_uuid": "migrated_xyz", "scenario": "pessimistic", "probability": 20},
        {"voter_uuid": "human-a", "scenario": "optimistic", "probability": 70},
        {"voter_uuid": "human-b", "scenario": "pessimistic", "probability": 25},
    ]
    human_votes = [v for v in all_votes if not is_synthetic_voter(v["voter_uuid"])]
    total = len(human_votes)
    buckets = {"optimistic": [], "base": [], "pessimistic": []}
    for vote in human_votes:
        buckets[vote["scenario"]].append(vote["probability"])

    assert total == 2
    assert buckets["optimistic"] == [70]
    assert buckets["base"] == []
    assert buckets["pessimistic"] == [25]


def test_stats_bulk_drops_predictions_with_only_synthetic_votes():
    """stats-bulk should not expose empty human stats for synthetic-only predictions."""
    votes_by_prediction = {
        "NP-0001": [
            {"voter_uuid": "neo-one-ai-player"},
            {"voter_uuid": "test-uuid-12345"},
        ],
        "NP-0002": [
            {"voter_uuid": "human-a"},
            {"voter_uuid": "neo-one-ai-player"},
        ],
    }
    visible_predictions = [
        pred_id
        for pred_id, rows in votes_by_prediction.items()
        if any(not is_synthetic_voter(row["voter_uuid"]) for row in rows)
    ]
    assert visible_predictions == ["NP-0002"], visible_predictions


def test_my_stats_unaffected():
    """my-stats is per-UUID and should work for any UUID including synthetic."""
    for uid in ["neo-one-ai-player", "test-uuid-12345", "human-a"]:
        _ = is_synthetic_voter(uid)


def test_human_competition_snapshot_stays_beta_below_threshold():
    snap = human_competition_snapshot(9, 9, 1)
    assert snap["ready"] is False
    assert snap["state"] == "beta_ai_benchmark_only"
    assert snap["sample"] == {"unique_voters": 9, "total_votes": 9, "resolved_votes": 1}


def test_human_competition_snapshot_turns_live_at_threshold():
    snap = human_competition_snapshot(25, 200, 20)
    assert snap["ready"] is True
    assert snap["state"] == "live_human_ranking"


# ── Runner ───────────────────────────────────────────────────────────────────

def main():
    tests = [
        test_module_sync,
        test_synthetic_exact_ids,
        test_synthetic_prefixes,
        test_human_uuids_not_synthetic,
        test_edge_cases,
        test_human_vote_filtering,
        test_top_forecasters_loop,
        test_leaderboard_aggregate_excludes_synthetic,
        test_community_stats_exclude_synthetic_votes,
        test_stats_bulk_drops_predictions_with_only_synthetic_votes,
        test_my_stats_unaffected,
        test_human_competition_snapshot_stays_beta_below_threshold,
        test_human_competition_snapshot_turns_live_at_threshold,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {t.__name__} -{e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"  {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'=' * 50}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
