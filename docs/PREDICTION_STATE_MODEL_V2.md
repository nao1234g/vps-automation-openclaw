# Prediction State Model V2

> Canonical public state contract for the prediction platform.
> Version: `2026-04-04-public-state-v2`
> Backed by code in [`scripts/prediction_state_utils.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/prediction_state_utils.py)

---

## Why This Exists

The old single `status` field was overloaded.

- It tried to describe whether forecasting was still open.
- It tried to describe whether resolution evidence existed.
- It tried to describe whether the same-language article was live.

That collision produced semantically broken distributions such as `1058 / 1121 = 94.4%` of predictions sitting in `resolving`.

V2 separates those meanings into distinct axes.

---

## The Three Axes

### 1. `forecast_state`

This answers: can this forecast still be treated as in-play for the reader?

Values:

- `OPEN_FOR_FORECASTING`
- `CLOSED_FOR_FORECASTING`

Rule:

- Resolved or disputed predictions are always `CLOSED_FOR_FORECASTING`.
- If the trigger/deadline is still in the future, use `OPEN_FOR_FORECASTING`.
- If the deadline has passed and the prediction is not resolved, use `CLOSED_FOR_FORECASTING`.

### 2. `resolution_state`

This answers: what do we know about the result itself?

Values:

- `PENDING_EVENT`
- `AWAITING_EVIDENCE`
- `RESOLVED_RECORDED`
- `RESOLVED_HIT`
- `RESOLVED_MISS`
- `RESOLVED_NOT_SCORED`
- `DISPUTED`

Rule:

- `HIT`, `MISS`, `NOT_SCORED` come from verdict-level evidence.
- `RESOLVED_RECORDED` means resolution markers exist (`resolved_at`, `brier_score`, etc.) but the final explicit verdict token is not yet normalized.
- `DISPUTED` overrides normal resolution display.
- If the event is still in play, use `PENDING_EVENT`.
- If the event window is closed but final evidence is not fixed, use `AWAITING_EVIDENCE`.

### 3. `content_state_{ja,en}`

This answers: what publication surface exists in a given language?

Values:

- `TRACKER_ONLY`
- `ARTICLE_LIVE`
- `CROSS_LANG_FALLBACK`

Rule:

- `ARTICLE_LIVE` means the same-language article URL is available.
- `CROSS_LANG_FALLBACK` means only the other-language article is available.
- `TRACKER_ONLY` means the forecast is public on the tracker without a same-language article.

---

## Public Render Bucket

Public tracker grouping is derived from the three axes, not from raw `status`.

Values:

- `in_play`
- `awaiting`
- `resolved`

Render rules:

- `resolved` if `resolution_state ∈ {RESOLVED_RECORDED, RESOLVED_HIT, RESOLVED_MISS, RESOLVED_NOT_SCORED, DISPUTED}`
- `in_play` if `forecast_state = OPEN_FOR_FORECASTING`
- `awaiting` otherwise

This is the bucket used by the public tracker page and integrity report.

---

## Migration Mapping From Current Data

The current single-field inputs are mapped like this:

| Current signal | V2 interpretation |
|---|---|
| `status=open/active` and deadline in future | `forecast_state=OPEN_FOR_FORECASTING`, `resolution_state=PENDING_EVENT` |
| `status=resolving` and deadline passed | `forecast_state=CLOSED_FOR_FORECASTING`, `resolution_state=AWAITING_EVIDENCE` |
| `resolved_at` or `brier_score` or final `verdict` present | `resolution_state=RESOLVED_*`, `forecast_state=CLOSED_FOR_FORECASTING` |
| `official_score_tier=NOT_SCORABLE` or `verdict=NOT_SCORED` | `resolution_state=RESOLVED_NOT_SCORED` |
| `status=disputed` | `resolution_state=DISPUTED` |
| Same-language article URL exists | `content_state_{lang}=ARTICLE_LIVE` |
| Only cross-language article URL exists | `content_state_{lang}=CROSS_LANG_FALLBACK` |
| No article URL exists | `content_state_{lang}=TRACKER_ONLY` |

---

## Canonical Snapshot Fields

Every public-facing snapshot should be able to expose these fields explicitly:

- `state_model_version`
- `canonical_status`
- `public_status`
- `forecast_state`
- `resolution_state`
- `content_state`
- `render_bucket`
- `accuracy_binary_n`
- `accuracy_binary_hit`
- `accuracy_binary_miss`
- `public_brier_n`
- `public_brier_avg`

The page builder should consume these fields, not rebuild meaning ad hoc.

---

## Code Contract

Implemented helpers:

- `forecast_lifecycle_state(...)`
- `resolution_lifecycle_state(...)`
- `content_publication_state(...)`
- `public_render_bucket(...)`
- `public_state_snapshot(...)`

Current consumers:

- [`scripts/prediction_page_builder.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/prediction_page_builder.py)
  - stores per-row state snapshot
  - derives public tracker buckets from `render_bucket`
  - exposes `data-forecast-state`, `data-resolution-state`, `data-content-state`

---

## Migration Plan

### Phase A: Derived state only

- Keep current DB `status`
- Derive V2 state at read time
- Use V2 for public rendering

### Phase B: Snapshot export

- Add V2 fields to canonical snapshot / release reports
- Stop using raw `status` directly in public surfaces

### Phase C: Optional DB materialization

- Only if needed later, persist V2 fields directly in the canonical DB
- Public rendering rules should already be stable before this step

---

## Non-Goals

- This document does not redefine scoring formulas.
- This document does not create a new verdict taxonomy beyond `HIT / MISS / NOT_SCORED / DISPUTED`.
- This document does not require an immediate DB schema migration.

---

## Acceptance Standard

P8 is considered complete only when:

- the V2 contract is documented,
- helper code exists,
- the public tracker consumes the derived bucket instead of raw single-field status logic,
- the execution board evidence points here.
