#!/usr/bin/env python3
"""
Nowpattern Reader Prediction API v2.0
FastAPI + SQLite — Community Prediction Platform
Port: 8766 (replaces reader_predict_server.py)
Caddy: /reader-predict/* → 127.0.0.1:8766
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
import sqlite3
import json
import os
import math
from datetime import datetime
from contextlib import contextmanager

from prediction_state_utils import (
    is_prediction_publicly_scorable,
    is_prediction_resolved,
    normalize_public_status,
    normalize_score_tier,
    normalize_verdict,
    public_prediction_status,
)

DB_PATH = "/opt/shared/reader_predictions.db"
PUBLIC_LEADERBOARD_MIN_RESOLVED = 5
HUMAN_PUBLIC_MIN_VOTERS = 25
HUMAN_PUBLIC_MIN_TOTAL_VOTES = 200
HUMAN_PUBLIC_MIN_RESOLVED_VOTES = 20

# ── Synthetic / system voter detection ───────────────────────────────────────
# These UUIDs are AI players, test seeds, or migration artefacts.
# They must be excluded from *human* reader aggregates and the human
# forecaster ranking, but kept queryable via /my-stats/{uuid}.

SYNTHETIC_VOTER_EXACT = frozenset({
    "neo-one-ai-player",
})

SYNTHETIC_VOTER_PREFIXES = (
    "test-",       # test harness UUIDs (e.g. test-uuid-12345)
    "migrated_",   # legacy JSON→SQLite migration artefacts
)


def is_synthetic_voter(voter_uuid: str) -> bool:
    """Return True if *voter_uuid* belongs to a known synthetic / system account."""
    if voter_uuid in SYNTHETIC_VOTER_EXACT:
        return True
    for prefix in SYNTHETIC_VOTER_PREFIXES:
        if voter_uuid.startswith(prefix):
            return True
    return False

app = FastAPI(
    title="Nowpattern Reader Prediction API",
    version="2.0.0",
    description="Community prediction voting backend for nowpattern.com/predictions/",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nowpattern.com", "http://localhost:2368", "http://127.0.0.1:2368"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


def normalize_status(status: Optional[str]) -> str:
    return normalize_public_status(status)


def is_resolved_status(status: Optional[str]) -> bool:
    return normalize_status(status) == "resolved"


def brier_index(raw_brier: Optional[float]) -> Optional[float]:
    try:
        score = float(raw_brier)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(score):
        return None
    score = max(0.0, min(1.0, score))
    return round((1.0 - math.sqrt(score)) * 100.0, 1)


def human_competition_snapshot(unique_voters: int, total_votes: int, resolved_votes: int) -> dict:
    ready = (
        unique_voters >= HUMAN_PUBLIC_MIN_VOTERS
        and total_votes >= HUMAN_PUBLIC_MIN_TOTAL_VOTES
        and resolved_votes >= HUMAN_PUBLIC_MIN_RESOLVED_VOTES
    )
    return {
        "ready": ready,
        "state": "live_human_ranking" if ready else "beta_ai_benchmark_only",
        "display_mode": "public_human_ranking" if ready else "ai_benchmark_only",
        "thresholds": {
            "min_unique_voters": HUMAN_PUBLIC_MIN_VOTERS,
            "min_total_votes": HUMAN_PUBLIC_MIN_TOTAL_VOTES,
            "min_resolved_votes": HUMAN_PUBLIC_MIN_RESOLVED_VOTES,
            "min_resolved_per_forecaster": PUBLIC_LEADERBOARD_MIN_RESOLVED,
        },
        "sample": {
            "unique_voters": unique_voters,
            "total_votes": total_votes,
            "resolved_votes": resolved_votes,
        },
    }


# ── Database setup ────────────────────────────────────────────────────────────

def init_db():
    """Initialize SQLite DB and migrate old JSON data if present."""
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS reader_votes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id TEXT    NOT NULL,
            voter_uuid    TEXT    NOT NULL,
            scenario      TEXT    NOT NULL CHECK(scenario IN ('optimistic','base','pessimistic')),
            probability   INTEGER NOT NULL CHECK(probability BETWEEN 5 AND 95),
            explanation   TEXT,
            created_at    TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
            updated_at    TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
            UNIQUE(prediction_id, voter_uuid)
        );
        CREATE INDEX IF NOT EXISTS idx_pred_id    ON reader_votes(prediction_id);
        CREATE INDEX IF NOT EXISTS idx_voter_uuid ON reader_votes(voter_uuid);
    """)
    cols = {row[1] for row in cur.execute("PRAGMA table_info(reader_votes)").fetchall()}
    if "explanation" not in cols:
        cur.execute("ALTER TABLE reader_votes ADD COLUMN explanation TEXT")
    con.commit()

    # Migrate legacy JSON votes (reader_predictions.json from v1.0)
    old_json = "/opt/shared/reader_predictions.json"
    if os.path.exists(old_json):
        try:
            data = json.load(open(old_json))
            votes = data.get("votes", {})
            migrated = 0
            for pred_id, ip_votes in votes.items():
                for ip_hash, verdict in ip_votes.items():
                    try:
                        prob = 70 if verdict == "YES" else 30
                        cur.execute("""
                            INSERT OR IGNORE INTO reader_votes
                            (prediction_id, voter_uuid, scenario, probability)
                            VALUES (?, ?, ?, ?)
                        """, (pred_id, "migrated_" + ip_hash[:16], "base", prob))
                        migrated += 1
                    except Exception:
                        pass
            con.commit()
            os.rename(old_json, old_json + ".migrated")
            print(f"[MIGRATE] {migrated} votes migrated from JSON to SQLite")
        except Exception as e:
            print(f"[MIGRATE] Warning: {e}")

    con.close()


@contextmanager
def db():
    """Thread-safe SQLite connection context manager."""
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ── Pydantic models ───────────────────────────────────────────────────────────

class VoteRequest(BaseModel):
    prediction_id: str = Field(..., min_length=5, max_length=30, description="e.g. NP-2026-0008")
    voter_uuid:    str = Field(..., min_length=10, max_length=80,  description="Client-generated UUID, persisted in localStorage")
    scenario:      str = Field(..., description="optimistic | base | pessimistic")
    probability:   int = Field(..., ge=5, le=95,                    description="5〜95 in steps of 5")
    explanation:   Optional[str] = Field(None, max_length=200, description="Optional reason for this vote (max 200 chars)")

    @field_validator("scenario")
    @classmethod
    def validate_scenario(cls, v: str) -> str:
        allowed = {"optimistic", "base", "pessimistic"}
        if v not in allowed:
            raise ValueError(f"scenario must be one of {allowed}")
        return v

    @field_validator("probability")
    @classmethod
    def validate_probability_step(cls, v: int) -> int:
        if v % 5 != 0:
            raise ValueError("probability must be a multiple of 5")
        return v


class ScenarioDist(BaseModel):
    count:           int
    avg_probability: Optional[int]
    pct:             int


class CommunityStats(BaseModel):
    total:            int
    avg_probability:  Optional[int]
    pct_optimistic:   int
    pct_base:         int
    pct_pessimistic:  int
    distribution:     Dict[str, ScenarioDist]


class VoteResponse(BaseModel):
    success:         bool
    prediction_id:   str
    community_stats: CommunityStats


class TrackerEntry(BaseModel):
    prediction_id: str
    scenario:      str
    probability:   int
    created_at:    str
    updated_at:    str


# ── Business logic ────────────────────────────────────────────────────────────

def compute_stats(prediction_id: str) -> CommunityStats:
    """Compute human community distribution for a given prediction ID."""
    with db() as con:
        rows = con.execute(
            "SELECT voter_uuid, scenario, probability FROM reader_votes WHERE prediction_id=?",
            (prediction_id,)
        ).fetchall()

    human_rows = [row for row in rows if not is_synthetic_voter(row["voter_uuid"])]

    if not human_rows:
        return CommunityStats(
            total=0, avg_probability=None,
            pct_optimistic=0, pct_base=0, pct_pessimistic=0,
            distribution={
                "optimistic":  ScenarioDist(count=0, avg_probability=None, pct=0),
                "base":        ScenarioDist(count=0, avg_probability=None, pct=0),
                "pessimistic": ScenarioDist(count=0, avg_probability=None, pct=0),
            }
        )

    buckets: Dict[str, List[int]] = {"optimistic": [], "base": [], "pessimistic": []}
    for r in human_rows:
        buckets[r["scenario"]].append(r["probability"])

    total = len(human_rows)
    dist: Dict[str, ScenarioDist] = {}
    for sc, probs in buckets.items():
        count = len(probs)
        dist[sc] = ScenarioDist(
            count=count,
            avg_probability=round(sum(probs) / count) if probs else None,
            pct=round(count * 100 / total) if total else 0,
        )

    all_probs = [r["probability"] for r in human_rows]
    avg_all = round(sum(all_probs) / len(all_probs)) if all_probs else None

    return CommunityStats(
        total=total,
        avg_probability=avg_all,
        pct_optimistic=dist["optimistic"].pct,
        pct_base=dist["base"].pct,
        pct_pessimistic=dist["pessimistic"].pct,
        distribution=dist,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/reader-predict/health")
def health():
    """Liveness check."""
    return {"status": "ok", "version": "2.0.0", "db": DB_PATH}


@app.post("/reader-predict/vote", response_model=VoteResponse)
def vote(req: VoteRequest):
    """
    Submit or update a community vote.
    voter_uuid identifies the reader (stored in localStorage).
    UPSERT: same reader can change their prediction.
    """
    with db() as con:
        con.execute("""
            INSERT INTO reader_votes (prediction_id, voter_uuid, scenario, probability, explanation)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(prediction_id, voter_uuid) DO UPDATE SET
                scenario    = excluded.scenario,
                probability = excluded.probability,
                explanation = COALESCE(excluded.explanation, explanation),
                updated_at  = strftime('%Y-%m-%dT%H:%M:%SZ','now')
        """, (req.prediction_id, req.voter_uuid, req.scenario, req.probability, req.explanation))

    stats = compute_stats(req.prediction_id)
    return VoteResponse(success=True, prediction_id=req.prediction_id, community_stats=stats)



@app.patch("/reader-predict/vote/{prediction_id}/{voter_uuid}/explanation")
def update_explanation(prediction_id: str, voter_uuid: str, explanation: str):
    """Update the explanation for an existing vote (max 200 chars)."""
    if len(explanation) > 200:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="explanation must be 200 chars or fewer")
    with db() as con:
        result = con.execute(
            "UPDATE reader_votes SET explanation=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE prediction_id=? AND voter_uuid=?",
            (explanation, prediction_id, voter_uuid)
        )
        if result.rowcount == 0:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="vote not found")
    return {"success": True, "prediction_id": prediction_id, "voter_uuid": voter_uuid}

@app.get("/reader-predict/stats/{prediction_id}", response_model=CommunityStats)
def stats_single(prediction_id: str):
    """Community distribution for one prediction."""
    return compute_stats(prediction_id)


@app.get("/reader-predict/stats-bulk")
def stats_bulk():
    """
    Returns stats for ALL predictions with at least 1 vote.
    Used by the /predictions/ page JS to batch-load community bars.
    """
    with db() as con:
        pred_ids = [r[0] for r in con.execute(
            "SELECT DISTINCT prediction_id FROM reader_votes"
        ).fetchall()]
    stats_map = {}
    for pid in pred_ids:
        stats = compute_stats(pid)
        if stats.total > 0:
            stats_map[pid] = stats.model_dump()
    return stats_map


@app.get("/reader-predict/my-votes/{voter_uuid}", response_model=List[TrackerEntry])
def my_votes(voter_uuid: str):
    """Return all votes cast by a specific reader (identified by UUID)."""
    with db() as con:
        rows = con.execute(
            "SELECT prediction_id, scenario, probability, created_at, updated_at "
            "FROM reader_votes WHERE voter_uuid=? ORDER BY updated_at DESC",
            (voter_uuid,)
        ).fetchall()
    return [TrackerEntry(**dict(r)) for r in rows]


@app.get("/reader-predict/leaderboard")
def leaderboard():
    """Real Brier Score leaderboard: AI vs readers."""
    pred_db = load_pred_db()
    ai_summary = _ai_official_score_summary(pred_db)

    # Reader stats — exclude synthetic/system voters from human aggregates
    with db() as con:
        all_votes = con.execute(
            "SELECT voter_uuid, prediction_id, scenario, probability FROM reader_votes"
        ).fetchall()

    human_votes = [v for v in all_votes if not is_synthetic_voter(v["voter_uuid"])]
    human_uuids = {v["voter_uuid"] for v in human_votes}
    reader_total_voters = len(human_uuids)
    reader_total_votes = len(human_votes)

    # Calculate aggregate reader Brier scores on-the-fly (human only)
    reader_brier_scores = []
    reader_correct = 0
    reader_resolved_votes = 0

    for vote in human_votes:
        p = pred_db.get(vote["prediction_id"], {})
        if not _is_prediction_publicly_scorable(p):
            continue
        reader_resolved_votes += 1
        reader_out = _reader_outcome(vote["scenario"], p)
        if reader_out is None:
            reader_resolved_votes -= 1
            continue
        prob = vote["probability"] / 100.0
        brier = (prob - reader_out) ** 2
        reader_brier_scores.append(brier)
        if reader_out == 1.0:
            reader_correct += 1

    reader_avg_brier = round(sum(reader_brier_scores) / len(reader_brier_scores), 4) if reader_brier_scores else None
    reader_accuracy = round(reader_correct / reader_resolved_votes * 100, 1) if reader_resolved_votes > 0 else None
    data_status = "live" if reader_resolved_votes > 0 else "accumulating"
    human_competition = human_competition_snapshot(
        reader_total_voters,
        reader_total_votes,
        reader_resolved_votes,
    )

    return {
        "public_min_resolved": PUBLIC_LEADERBOARD_MIN_RESOLVED,
        "score_display": "brier_index_public_raw_brier_internal",
        "human_competition": human_competition,
        "ai": {
            "name": "Nowpattern AI",
            "score_basis": "official_prediction_record",
            "avg_brier_score": ai_summary["avg_brier_score"],
            "avg_brier_index": ai_summary["avg_brier_index"],
            "resolved_count": ai_summary["scored_count"],
            "resolved_ids": ai_summary["prediction_ids"],
            "resolved_total": ai_summary["resolved_total"],
            "not_scorable_count": ai_summary["not_scorable_count"],
            "correct_count": ai_summary["correct_count"],
            "accuracy_pct": ai_summary["accuracy_pct"],
            "public_leaderboard_eligible": ai_summary["scored_count"] >= PUBLIC_LEADERBOARD_MIN_RESOLVED,
        },
        "readers": {
            "total_voters": reader_total_voters,
            "total_votes": reader_total_votes,
            "resolved_votes": reader_resolved_votes,
            "avg_brier_score": reader_avg_brier,
            "avg_brier_index": brier_index(reader_avg_brier),
            "accuracy_pct": reader_accuracy,
            "correct_count": reader_correct,
            "data_status": data_status,
            "score_basis": "reader_vote_brier",
            "public_leaderboard_eligible": reader_resolved_votes >= PUBLIC_LEADERBOARD_MIN_RESOLVED,
            "human_public_ready": human_competition["ready"],
            "human_competition_state": human_competition["state"],
            "human_public_thresholds": human_competition["thresholds"],
        },
    }





@app.get("/reader-predict/top-forecasters")
def top_forecasters():
    """Per-voter anonymized Brier Score ranking."""
    pred_db = load_pred_db()
    
    with db() as con:
        all_votes = con.execute(
            "SELECT voter_uuid, prediction_id, scenario, probability, created_at FROM reader_votes"
        ).fetchall()
    
    # Group by voter — skip all synthetic/system voters
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
            voter_stats[uid] = {"votes": 0, "resolved": 0, "correct": 0, "brier_scores": [], "first_vote": vote["created_at"]}
        voter_stats[uid]["votes"] += 1
        
        p = pred_db.get(vote["prediction_id"], {})
        if not _is_prediction_publicly_scorable(p):
            continue
        voter_stats[uid]["resolved"] += 1
        outcome = _reader_outcome(vote["scenario"], p)
        if outcome is None:
            voter_stats[uid]["resolved"] -= 1
            continue
        prob = vote["probability"] / 100.0
        brier = (prob - outcome) ** 2
        voter_stats[uid]["brier_scores"].append(brier)
        if outcome == 1.0:
            voter_stats[uid]["correct"] += 1
    
    # Build ranked list (voters with resolved predictions only)
    ranked = []
    for uid, s in voter_stats.items():
        if not s["brier_scores"]:
            continue
        avg_brier = round(sum(s["brier_scores"]) / len(s["brier_scores"]), 4)
        accuracy = round(s["correct"] / s["resolved"] * 100, 1) if s["resolved"] > 0 else 0
        # Anonymize: first 6 chars of uuid
        anon_id = uid[:6].upper() if len(uid) >= 6 else uid.upper()
        ranked.append({
            "voter_id": uid,
            "display_id": f"Forecaster #{anon_id}",
            "is_ai": False,
            "avg_brier_score": avg_brier,
            "avg_brier_index": brier_index(avg_brier),
            "resolved_count": s["resolved"],
            "correct_count": s["correct"],
            "accuracy_pct": accuracy,
            "total_votes": s["votes"],
            "score_basis": "reader_vote_brier",
            "public_leaderboard_eligible": s["resolved"] >= PUBLIC_LEADERBOARD_MIN_RESOLVED,
        })

    ai_summary = _ai_official_score_summary(pred_db)
    if ai_summary["scored_count"] > 0:
        ranked.append({
            "voter_id": "neo-one-ai-player",
            "display_id": "Nowpattern AI",
            "is_ai": True,
            "avg_brier_score": ai_summary["avg_brier_score"],
            "avg_brier_index": ai_summary["avg_brier_index"],
            "resolved_count": ai_summary["scored_count"],
            "resolved_total": ai_summary["resolved_total"],
            "not_scorable_count": ai_summary["not_scorable_count"],
            "correct_count": ai_summary["correct_count"],
            "accuracy_pct": ai_summary["accuracy_pct"],
            "total_votes": ai_vote_total or len(pred_db),
            "score_basis": "official_prediction_record",
            "public_leaderboard_eligible": ai_summary["scored_count"] >= PUBLIC_LEADERBOARD_MIN_RESOLVED,
        })
    
    # Sort by Brier score ascending (lower = better)
    ranked.sort(key=lambda x: x["avg_brier_score"])
    
    # Add rank
    for i, r in enumerate(ranked, 1):
        r["rank"] = i

    public_rank = 1
    for r in ranked:
        if r["public_leaderboard_eligible"]:
            r["public_rank"] = public_rank
            public_rank += 1
        else:
            r["public_rank"] = None

    public_forecasters = [r for r in ranked if r["public_leaderboard_eligible"]]
    human_public_forecasters = [r for r in public_forecasters if not r["is_ai"]]
    human_total_votes = sum(s["votes"] for s in voter_stats.values())
    human_resolved_votes = sum(s["resolved"] for s in voter_stats.values())
    human_competition = human_competition_snapshot(
        len(voter_stats),
        human_total_votes,
        human_resolved_votes,
    )
    return {
        "forecasters": ranked,
        "public_forecasters": public_forecasters,
        "human_public_forecasters": human_public_forecasters,
        "total": len(ranked),
        "public_total": len(public_forecasters),
        "public_min_resolved": PUBLIC_LEADERBOARD_MIN_RESOLVED,
        "human_competition": human_competition,
        "human_public_ready": human_competition["ready"],
        "human_competition_state": human_competition["state"],
        "human_public_thresholds": human_competition["thresholds"],
        "human_sample": human_competition["sample"],
    }

class PredictionSummary(BaseModel):
    prediction_id: str
    article_title: Optional[str]
    article_title_en: Optional[str]
    ghost_url: Optional[str]
    status: str
    our_pick: Optional[str]
    our_pick_prob: Optional[int]
    oracle_deadline: Optional[str]
    brier_score: Optional[float]
    brier_index: Optional[float]
    official_score_tier: Optional[str]
    dynamics_tags: Optional[list]
    genre_tags: Optional[list]


class MyTrackerEntry(BaseModel):
    prediction_id: str
    scenario: str
    probability: int
    created_at: str
    updated_at: str
    prediction: Optional[PredictionSummary]
    is_resolved: bool
    is_correct: Optional[bool]


PRED_DB_CACHE = {}
PRED_DB_CACHE_TIME = 0


def load_pred_db() -> dict:
    """Load prediction_db.json with 60s cache."""
    import time
    global PRED_DB_CACHE, PRED_DB_CACHE_TIME
    now = time.time()
    if not PRED_DB_CACHE or now - PRED_DB_CACHE_TIME > 60:
        try:
            with open("/opt/shared/scripts/prediction_db.json") as f:
                raw = json.load(f)
            PRED_DB_CACHE = {p["prediction_id"]: p for p in raw.get("predictions", [])}
            PRED_DB_CACHE_TIME = now
        except Exception:
            pass
    return PRED_DB_CACHE


def _prediction_status(prediction: dict) -> str:
    return public_prediction_status(prediction)


def _is_prediction_resolved(prediction: dict) -> bool:
    return is_prediction_resolved(prediction)


def _is_prediction_publicly_scorable(prediction: dict) -> bool:
    return is_prediction_publicly_scorable(prediction)


def _ai_official_score_summary(predictions: List[dict] | dict) -> dict:
    rows = list(predictions.values()) if isinstance(predictions, dict) else list(predictions)
    scored_scores = []
    scored_ids = []
    scored_hits = 0
    resolved_total = 0
    not_scorable_count = 0

    for prediction in rows:
        if not _is_prediction_resolved(prediction):
            continue
        resolved_total += 1
        if normalize_score_tier(prediction.get("official_score_tier")) == "NOT_SCORABLE":
            not_scorable_count += 1
            continue
        if not is_prediction_publicly_scorable(prediction):
            continue
        try:
            scored_scores.append(float(prediction["brier_score"]))
            scored_ids.append(prediction.get("prediction_id", ""))
        except (TypeError, ValueError):
            continue
        if normalize_verdict(prediction.get("verdict")) == "HIT":
            scored_hits += 1

    avg_brier = round(sum(scored_scores) / len(scored_scores), 4) if scored_scores else None
    accuracy_pct = round(scored_hits / len(scored_scores) * 100.0, 1) if scored_scores else None
    return {
        "avg_brier_score": avg_brier,
        "avg_brier_index": brier_index(avg_brier),
        "scored_count": len(scored_scores),
        "prediction_ids": scored_ids,
        "correct_count": scored_hits,
        "accuracy_pct": accuracy_pct,
        "resolved_total": resolved_total,
        "not_scorable_count": not_scorable_count,
    }


def _reader_outcome(voted_scenario: str, prediction: dict):
    """Determine if a reader's voted scenario matches the resolved prediction outcome.

    Returns:
        1.0  — reader voted the correct scenario
        0.0  — reader voted the wrong scenario
        None — outcome unknown (can't calculate)
    """
    outcome_raw = prediction.get("outcome")
    if outcome_raw is None:
        return None

    outcome = str(outcome_raw).strip()

    # Map voted_scenario ("optimistic"/"base"/"pessimistic") to expected outcome text
    SCENARIO_MAP = {
        "optimistic": ("楽観", "YES", "yes", "bull", "optimistic"),
        "base":       ("基本", "base", "neutral"),
        "pessimistic": ("悲観", "NO", "no", "bear", "pessimistic"),
    }
    expected_keywords = SCENARIO_MAP.get(voted_scenario.lower(), ())
    outcome_lower = outcome.lower()
    for kw in expected_keywords:
        if kw.lower() in outcome_lower:
            return 1.0
    return 0.0


@app.get("/reader-predict/my-tracker/{voter_uuid}", response_model=List[MyTrackerEntry])
def my_tracker(voter_uuid: str):
    """Return enriched vote history for a reader (UUID-based, anonymous).
    Includes prediction context: title, status, our_pick, deadline."""
    with db() as con:
        rows = con.execute(
            "SELECT prediction_id, scenario, probability, created_at, updated_at "
            "FROM reader_votes WHERE voter_uuid=? ORDER BY updated_at DESC",
            (voter_uuid,)
        ).fetchall()

    pred_db = load_pred_db()
    result = []
    for row in rows:
        pred_id = row["prediction_id"]
        p = pred_db.get(pred_id, {})

        status = _prediction_status(p)
        is_resolved = _is_prediction_resolved(p)

        # Did reader call it correctly?
        is_correct = None
        if is_resolved:
            scenario = row["scenario"]
            reader_out = _reader_outcome(scenario, p)
            if reader_out is not None:
                is_correct = (reader_out == 1.0)

        pred_summary = PredictionSummary(
            prediction_id=pred_id,
            article_title=p.get("article_title"),
            article_title_en=p.get("article_title_en"),
            ghost_url=p.get("ghost_url"),
            status=status,
            our_pick=p.get("our_pick"),
            our_pick_prob=p.get("our_pick_prob"),
            oracle_deadline=p.get("oracle_deadline") or (
                p.get("triggers", [{}])[0].get("date") if p.get("triggers") else None
            ),
            brier_score=p.get("brier_score"),
            brier_index=brier_index(p.get("brier_score")),
            official_score_tier=p.get("official_score_tier"),
            dynamics_tags=(_t if isinstance(_t := p.get("dynamics_tags"), list) else ([_t] if _t else [])),
            genre_tags=(_g if isinstance(_g := p.get("genre_tags"), list) else ([_g] if _g else [])),
        ) if p else None

        result.append(MyTrackerEntry(
            prediction_id=pred_id,
            scenario=row["scenario"],
            probability=row["probability"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            prediction=pred_summary,
            is_resolved=is_resolved,
            is_correct=is_correct,
        ))

    return result


@app.get("/reader-predict/my-stats/{voter_uuid}")
def my_stats(voter_uuid: str):
    """Summary stats for a reader: votes count, accuracy %, Brier-like score."""
    with db() as con:
        rows = con.execute(
            "SELECT prediction_id, scenario, probability FROM reader_votes WHERE voter_uuid=?",
            (voter_uuid,)
        ).fetchall()

    pred_db = load_pred_db()
    total = len(rows)
    resolved = 0
    correct = 0
    brier_scores = []

    for row in rows:
        pred_id = row["prediction_id"]
        p = pred_db.get(pred_id, {})
        if not _is_prediction_publicly_scorable(p):
            continue
        resolved += 1
        scenario = row["scenario"]
        prob = row["probability"] / 100.0

        # Outcome: 1.0 = reader voted correctly, 0.0 = incorrect
        reader_out = _reader_outcome(scenario, p)
        if reader_out is None:
            resolved -= 1  # skip: can't determine outcome
            continue
        outcome = reader_out
        brier = (prob - outcome) ** 2

        brier_scores.append(brier)
        if outcome == 1.0:
            correct += 1

    accuracy = round(correct / resolved * 100, 1) if resolved > 0 else None
    avg_brier = round(sum(brier_scores) / len(brier_scores), 4) if brier_scores else None

    return {
        "voter_uuid": voter_uuid,
        "total_votes": total,
        "resolved_count": resolved,
        "correct_count": correct,
        "accuracy_pct": accuracy,
        "avg_brier_score": avg_brier,
        "avg_brier_index": brier_index(avg_brier),
        "open_votes": total - resolved,
        "public_leaderboard_eligible": resolved >= PUBLIC_LEADERBOARD_MIN_RESOLVED,
        "public_min_resolved": PUBLIC_LEADERBOARD_MIN_RESOLVED,
        "rank_label": (
            "Expert Forecaster" if accuracy and accuracy >= 70 else
            "Calibrated Forecaster" if accuracy and accuracy >= 60 else
            "Developing Forecaster" if accuracy and accuracy >= 50 else
            "Novice Forecaster" if resolved >= 3 else
            "New Forecaster"
        )
    }

@app.get("/api/predictions/")
def public_predictions(
    status: Optional[str] = None,
    lang: Optional[str] = None,
    tag: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    """Public Predictions API v1 — returns prediction_db entries with filtering.

    Query params:
      status: open|resolving|resolved|active (comma-separated ok)
      lang:   ja|en  (filters by ghost_url containing /en/ or not)
      tag:    dynamics/genre tag slug (partial match)
      page:   1-based page number (default 1)
      limit:  results per page (default 50, max 200)
    """
    limit = min(max(1, limit), 200)
    page = max(1, page)

    pred_db = load_pred_db()
    preds = list(pred_db.values())

    # Filter by status
    if status:
        statuses = {normalize_status(s.strip()) for s in status.split(",")}
        preds = [p for p in preds if _prediction_status(p) in statuses]

    # Filter by lang
    if lang:
        if lang == "en":
            preds = [p for p in preds if "/en/" in (p.get("ghost_url") or "")]
        elif lang == "ja":
            preds = [p for p in preds if "/en/" not in (p.get("ghost_url") or "") and p.get("ghost_url")]

    # Filter by tag
    if tag:
        tag_lower = tag.lower()
        def has_tag(p):
            all_tags = (p.get("dynamics_tags") or []) + (p.get("genre_tags") or [])
            return any(tag_lower in t.lower() for t in all_tags)
        preds = [p for p in preds if has_tag(p)]

    total = len(preds)
    offset = (page - 1) * limit
    page_preds = preds[offset:offset + limit]

    result = []
    for p in page_preds:
        result.append({
            "prediction_id": p.get("prediction_id"),
            "article_title": p.get("article_title"),
            "article_title_en": p.get("article_title_en"),
            "ghost_url": p.get("ghost_url"),
            "status": _prediction_status(p),
            "our_pick": p.get("our_pick"),
            "our_pick_prob": p.get("our_pick_prob"),
            "oracle_deadline": p.get("oracle_deadline"),
            "resolution_question": p.get("resolution_question"),
            "resolution_question_ja": p.get("resolution_question_ja"),
            "brier_score": p.get("brier_score"),
            "brier_index": brier_index(p.get("brier_score")),
            "official_score_tier": p.get("official_score_tier"),
            "hit_miss": p.get("hit_miss"),
            "dynamics_tags": p.get("dynamics_tags", []),
            "genre_tags": p.get("genre_tags", []),
            "category": p.get("category"),
            "published_at": p.get("published_at") or p.get("timestamp_created_at"),
        })

    return {
        "predictions": result,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 1,
    }


@app.on_event("startup")
def startup():
    init_db()
    print(f"[STARTUP] Reader Prediction API v2.0 ready. DB: {DB_PATH}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("reader_prediction_api:app", host="127.0.0.1", port=8766, reload=False)
