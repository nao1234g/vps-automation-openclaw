#!/usr/bin/env python3
"""Shared prediction-state normalization helpers.

These helpers define the canonical truth model for prediction status:

- Final verdict / resolved_at / brier_score are stronger evidence than raw status.
- Canonical DB statuses are uppercase and audit-friendly.
- Public/UI statuses are lower-case and presentation-oriented.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


FINAL_VERDICTS = {"HIT", "MISS", "NOT_SCORED"}
_YES_NO_RE = re.compile(r"(?i)(?:判定|verdict|resolved as|outcome|result)\s*[:：]\s*(YES|NO|VOID|NOT[_ -]?SCORED)")

_CANONICAL_STATUS_ALIASES = {
    "open": "OPEN",
    "active": "ACTIVE",
    "resolving": "RESOLVING",
    "awaiting_evidence": "RESOLVING",
    "expired_unresolved": "EXPIRED_UNRESOLVED",
    "resolved": "RESOLVED",
    "disputed": "DISPUTED",
}

_PUBLIC_STATUS_ALIASES = {
    "OPEN": "open",
    "ACTIVE": "active",
    "RESOLVING": "resolving",
    "EXPIRED_UNRESOLVED": "resolving",
    "RESOLVED": "resolved",
    "DISPUTED": "disputed",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_verdict(verdict: Any) -> str:
    return _clean_text(verdict).upper()


def is_final_verdict(verdict: Any) -> bool:
    return normalize_verdict(verdict) in FINAL_VERDICTS


def normalize_canonical_status(status: Any) -> str:
    raw = _clean_text(status)
    if not raw:
        return "OPEN"
    lowered = raw.lower()
    return _CANONICAL_STATUS_ALIASES.get(lowered, raw.upper())


def normalize_public_status(status: Any) -> str:
    canonical = normalize_canonical_status(status)
    return _PUBLIC_STATUS_ALIASES.get(canonical, canonical.lower())


def has_resolution_markers(prediction: Mapping[str, Any] | None) -> bool:
    if not isinstance(prediction, Mapping):
        return False
    if is_final_verdict(prediction.get("verdict")):
        return True
    if prediction.get("resolved_at"):
        return True
    return prediction.get("brier_score") is not None


def canonical_prediction_status(prediction: Mapping[str, Any] | None) -> str:
    if not isinstance(prediction, Mapping):
        return "OPEN"
    if has_resolution_markers(prediction):
        return "RESOLVED"
    return normalize_canonical_status(prediction.get("status"))


def public_prediction_status(prediction: Mapping[str, Any] | None) -> str:
    canonical = canonical_prediction_status(prediction)
    return _PUBLIC_STATUS_ALIASES.get(canonical, canonical.lower())


def is_prediction_resolved(prediction: Mapping[str, Any] | None) -> bool:
    return canonical_prediction_status(prediction) == "RESOLVED"


def normalize_score_tier(score_tier: Any) -> str:
    tier = _clean_text(score_tier).upper()
    return tier or "NONE"


def infer_final_verdict(prediction: Mapping[str, Any] | None) -> str:
    current = normalize_verdict((prediction or {}).get("verdict"))
    if is_final_verdict(current):
        return current
    if not has_resolution_markers(prediction):
        return current

    if normalize_score_tier((prediction or {}).get("official_score_tier")) == "NOT_SCORABLE":
        return "NOT_SCORED"

    hit_miss = _clean_text((prediction or {}).get("hit_miss")).lower()
    if hit_miss in {"correct", "hit"}:
        return "HIT"
    if hit_miss in {"incorrect", "miss"}:
        return "MISS"

    resolution_note = _clean_text((prediction or {}).get("resolution_note")).upper()
    match = _YES_NO_RE.search(resolution_note)
    resolved_outcome = match.group(1).replace("-", "_") if match else ""
    if resolved_outcome in {"VOID", "NOT_SCORED"}:
        return "NOT_SCORED"

    our_pick = _clean_text((prediction or {}).get("our_pick")).upper()
    if resolved_outcome in {"YES", "NO"} and our_pick in {"YES", "NO"}:
        return "HIT" if resolved_outcome == our_pick else "MISS"

    return current


def is_prediction_publicly_scorable(prediction: Mapping[str, Any] | None) -> bool:
    if not isinstance(prediction, Mapping):
        return False
    if not is_prediction_resolved(prediction):
        return False
    if normalize_score_tier(prediction.get("official_score_tier")) == "NOT_SCORABLE":
        return False
    if prediction.get("brier_score") is None:
        return False
    return normalize_verdict(prediction.get("verdict")) in {"HIT", "MISS"}
