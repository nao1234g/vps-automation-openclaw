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
from datetime import date, datetime
from typing import Any


FINAL_VERDICTS = {"HIT", "MISS", "NOT_SCORED"}
_YES_NO_RE = re.compile(r"(?i)(?:判定|verdict|resolved as|outcome|result)\s*[:：]\s*(YES|NO|VOID|NOT[_ -]?SCORED)")
_ISO_DATE_RE = re.compile(r"^(?P<year>20\d{2})-(?P<month>\d{2})-(?P<day>\d{2})$")
_ISO_MONTH_RE = re.compile(r"^(?P<year>20\d{2})-(?P<month>\d{2})$")
_QUARTER_RE = re.compile(r"^(?:(?P<year_a>20\d{2})\s*Q(?P<q_a>[1-4])|Q(?P<q_b>[1-4])\s*(?P<year_b>20\d{2}))$", re.IGNORECASE)
_QUARTER_START_MONTH = {1: 1, 2: 4, 3: 7, 4: 10}

PUBLIC_STATE_MODEL_VERSION = "2026-04-04-public-state-v2"
FORECAST_STATE_OPEN = "OPEN_FOR_FORECASTING"
FORECAST_STATE_CLOSED = "CLOSED_FOR_FORECASTING"
RESOLUTION_STATE_PENDING = "PENDING_EVENT"
RESOLUTION_STATE_AWAITING = "AWAITING_EVIDENCE"
RESOLUTION_STATE_DISPUTED = "DISPUTED"
RESOLUTION_STATE_RECORDED = "RESOLVED_RECORDED"
RESOLUTION_STATE_HIT = "RESOLVED_HIT"
RESOLUTION_STATE_MISS = "RESOLVED_MISS"
RESOLUTION_STATE_NOT_SCORED = "RESOLVED_NOT_SCORED"
CONTENT_STATE_TRACKER_ONLY = "TRACKER_ONLY"
CONTENT_STATE_ARTICLE_LIVE = "ARTICLE_LIVE"
CONTENT_STATE_CROSS_LANG = "CROSS_LANG_FALLBACK"
PUBLIC_RENDER_BUCKET_IN_PLAY = "in_play"
PUBLIC_RENDER_BUCKET_AWAITING = "awaiting"
PUBLIC_RENDER_BUCKET_RESOLVED = "resolved"

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


def _coerce_today(value: date | datetime | None) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.today()


def _coerce_dateish(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = _clean_text(value)
    if not raw:
        return None
    token = raw[:10]
    match = _ISO_DATE_RE.match(token)
    if match:
        return date(int(match.group("year")), int(match.group("month")), int(match.group("day")))
    match = _ISO_MONTH_RE.match(raw[:7])
    if match:
        return date(int(match.group("year")), int(match.group("month")), 1)
    match = _QUARTER_RE.match(raw)
    if match:
        year = int(match.group("year_a") or match.group("year_b"))
        quarter = int(match.group("q_a") or match.group("q_b"))
        return date(year, _QUARTER_START_MONTH[quarter], 1)
    return None


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


def forecast_lifecycle_state(
    prediction: Mapping[str, Any] | None,
    today: date | datetime | None = None,
) -> str:
    if not isinstance(prediction, Mapping):
        return FORECAST_STATE_OPEN
    if is_prediction_resolved(prediction):
        return FORECAST_STATE_CLOSED
    if normalize_canonical_status(prediction.get("status")) == "DISPUTED":
        return FORECAST_STATE_CLOSED

    deadline = (
        _coerce_dateish(prediction.get("trigger_date"))
        or _coerce_dateish(prediction.get("oracle_deadline"))
    )
    if deadline is not None:
        return FORECAST_STATE_OPEN if deadline >= _coerce_today(today) else FORECAST_STATE_CLOSED

    return (
        FORECAST_STATE_OPEN
        if normalize_public_status(prediction.get("status")) in {"open", "active"}
        else FORECAST_STATE_CLOSED
    )


def resolution_lifecycle_state(
    prediction: Mapping[str, Any] | None,
    today: date | datetime | None = None,
) -> str:
    if not isinstance(prediction, Mapping):
        return RESOLUTION_STATE_PENDING

    if normalize_canonical_status(prediction.get("status")) == "DISPUTED":
        return RESOLUTION_STATE_DISPUTED

    verdict = infer_final_verdict(prediction)
    if verdict == "HIT":
        return RESOLUTION_STATE_HIT
    if verdict == "MISS":
        return RESOLUTION_STATE_MISS
    if verdict == "NOT_SCORED":
        return RESOLUTION_STATE_NOT_SCORED
    if has_resolution_markers(prediction):
        return RESOLUTION_STATE_RECORDED

    if forecast_lifecycle_state(prediction, today=today) == FORECAST_STATE_OPEN:
        return RESOLUTION_STATE_PENDING
    return RESOLUTION_STATE_AWAITING


def content_publication_state(prediction: Mapping[str, Any] | None, lang: str = "ja") -> str:
    if not isinstance(prediction, Mapping):
        return CONTENT_STATE_TRACKER_ONLY

    same_lang_url = _clean_text(prediction.get("same_lang_url"))
    fallback_url = _clean_text(prediction.get("fallback_url"))
    if same_lang_url:
        return CONTENT_STATE_ARTICLE_LIVE
    if fallback_url:
        return CONTENT_STATE_CROSS_LANG
    return CONTENT_STATE_TRACKER_ONLY


def public_render_bucket(
    prediction: Mapping[str, Any] | None,
    lang: str = "ja",
    today: date | datetime | None = None,
) -> str:
    resolution_state = resolution_lifecycle_state(prediction, today=today)
    if resolution_state in {
        RESOLUTION_STATE_DISPUTED,
        RESOLUTION_STATE_RECORDED,
        RESOLUTION_STATE_HIT,
        RESOLUTION_STATE_MISS,
        RESOLUTION_STATE_NOT_SCORED,
    }:
        return PUBLIC_RENDER_BUCKET_RESOLVED
    if forecast_lifecycle_state(prediction, today=today) == FORECAST_STATE_OPEN:
        return PUBLIC_RENDER_BUCKET_IN_PLAY
    return PUBLIC_RENDER_BUCKET_AWAITING


def public_state_snapshot(
    prediction: Mapping[str, Any] | None,
    lang: str = "ja",
    today: date | datetime | None = None,
) -> dict[str, Any]:
    forecast_state = forecast_lifecycle_state(prediction, today=today)
    resolution_state = resolution_lifecycle_state(prediction, today=today)
    content_state = content_publication_state(prediction, lang=lang)
    return {
        "state_model_version": PUBLIC_STATE_MODEL_VERSION,
        "canonical_status": canonical_prediction_status(prediction),
        "public_status": public_prediction_status(prediction),
        "forecast_state": forecast_state,
        "resolution_state": resolution_state,
        "content_state": content_state,
        "render_bucket": public_render_bucket(prediction, lang=lang, today=today),
    }
