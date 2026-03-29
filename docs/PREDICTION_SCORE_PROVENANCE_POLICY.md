# Prediction Score Provenance Policy

> **Single Source of Truth for how Nowpattern classifies prediction score integrity.**
> All changes require CHANGELOG entry at bottom.
> Last updated: 2026-03-29

---

## Purpose

This document defines the `official_score_tier` classification system for Nowpattern predictions.
The goal is to be honest with readers about how well we can prove that a displayed Brier Score
reflects the *originally published* probability rather than a retroactively adjusted value.

**Core principle**: "Tiers describe evidence quality, not prediction quality."
A PROVISIONAL tier score is not a bad score — it is simply one we cannot yet prove immutably.

---

## The Four Tiers

### VERIFIED_OFFICIAL
> *We can prove the original probability with blockchain-confirmed, tamper-evident evidence.*

Requirements (ALL must be met):
1. OTS (OpenTimestamps) proof is **confirmed on Bitcoin blockchain** (`timestamp_pending = false`)
2. SHA-256 hash in manifest **matches the current prediction JSON**
3. Ledger REGISTERED event has **original publish timestamp** (not retroactive)
4. `initial_prob` = value recorded at original publish time

Display label: "公式確定スコア" / "Verified Official Score"

### MIGRATED_OFFICIAL
> *OTS confirmation received after initial backfill, but SHA-256 matches at time of OTS confirmation.*

Requirements:
1. OTS proof is **confirmed on Bitcoin blockchain** after Phase 6 backfill
2. Manifest hash matches at time of OTS confirmation
3. No changes to `our_pick_prob` since OTS timestamp

Display label: "移行確定スコア" / "Migrated Official Score"
Note: Cannot achieve VERIFIED_OFFICIAL because ledger timestamps were retroactive.

### PROVISIONAL
> *initial_prob copied from our_pick_prob via backfill; no tamper-evident proof of original value.*

Applies when ANY of:
- OTS proof `timestamp_pending = true` (confirmation not yet received)
- SHA-256 manifest hash does NOT match current prediction JSON
- Ledger REGISTERED event was retroactively created

Display label: "暫定計算値" / "Provisional Score"

**Current state (2026-03-29)**: ALL 1111 scorable predictions are PROVISIONAL because:
1. All 1115 OTS proofs have `timestamp_pending = True` (blockchain confirmation not yet received)
2. SHA-256 hashes in manifest do not match current prediction JSON records
   (records were modified after initial hash was created)
3. All ledger REGISTERED events have `ts = 2026-03-29T01:13:48Z`
   (retroactively created during Phase 6 backfill, not original publish time)

### NOT_SCORABLE
> *Cannot compute a Brier Score for this prediction.*

Applies when:
- `verdict = "NOT_SCORED"` (prediction was voided or excluded)
- `our_pick_prob = null` (no probability was ever set)

Display label: "スコア対象外" / "Not Scored"

---

## Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `initial_prob` | int (0–100) | The probability locked as the "official" initial value for Brier calculation |
| `initial_prob_source` | enum | How `initial_prob` was determined (see below) |
| `initial_prob_provenance` | string | Human-readable audit string explaining evidence quality |
| `official_score_tier` | enum | One of: VERIFIED_OFFICIAL, MIGRATED_OFFICIAL, PROVISIONAL, NOT_SCORABLE |

### initial_prob_source enum

| Value | Meaning |
|-------|---------|
| `FROM_IMMUTABLE_LEDGER` | Taken from blockchain-confirmed ledger entry with probability field |
| `FROM_TIMESTAMPED_SNAPSHOT` | Taken from OTS-confirmed snapshot that includes probability |
| `FROM_MANIFEST` | Taken from manifest entry that includes probability |
| `FROM_CURRENT_VALUE_BACKFILL` | Copied from `our_pick_prob` during backfill; no independent proof |
| `UNKNOWN` | Source cannot be determined |

**Current state**: All 1115 predictions use `FROM_CURRENT_VALUE_BACKFILL`.

---

## Brier Score Formula

```
BS = (initial_prob / 100 - actual_outcome)²
```

Where `actual_outcome` = 1 if verdict = HIT, 0 if verdict = MISS.

A Brier Score of 0.0 is perfect; 1.0 is maximally wrong.
Reference points: random guessing (always 50%) = BS 0.25; always-correct forecaster = BS 0.0.

**Current aggregate**: `official_brier_avg_initial_prob = 0.4697` (PROVISIONAL, n=53 resolved)

---

## Upgrade Path: PROVISIONAL → MIGRATED_OFFICIAL

When OTS proofs are confirmed on Bitcoin blockchain:

```python
# prediction_auto_verifier.py will handle this when OTS confirms
if ots_confirmed and sha256_matches_at_confirmation:
    p["official_score_tier"] = "MIGRATED_OFFICIAL"
    p["initial_prob_source"] = "FROM_TIMESTAMPED_SNAPSHOT"
    p["ots_confirmation_date"] = confirmation_date
    p["initial_prob_provenance"] = update_provenance_with_confirmation(p)
```

The OTS confirmation process runs via `prediction_timestamper.py` (hourly cron on VPS).
Once Bitcoin blockchain confirms a timestamp, the OTS library returns `timestamp_pending = false`.

---

## Reader-Facing Display Standards

| Tier | Score display | Tooltip |
|------|--------------|---------|
| VERIFIED_OFFICIAL | Score + ✓ verified badge | "ブロックチェーンで証明済みの公式スコア" |
| MIGRATED_OFFICIAL | Score + ○ migrated badge | "OTS確認済みの移行スコア" |
| PROVISIONAL | Score + △ provisional label | "暫定計算値 — OTS確認待ち" |
| NOT_SCORABLE | "対象外" | "この予測はスコア計算対象外です" |

**Important**: Do NOT display PROVISIONAL scores as "official" or "certified" in any user-facing text.

---

## Implementation Files

| File | Purpose |
|------|---------|
| `/opt/shared/scripts/prediction_db.json` | Main DB with all tier/provenance fields |
| `/opt/shared/scripts/phase11_initial_prob_backfill.py` | Phase 3 migration that set all PROVISIONAL tiers |
| `/opt/shared/scripts/prediction_timestamper.py` | Hourly OTS timestamping (hourly cron) |
| `/opt/shared/scripts/prediction_auto_verifier.py` | Tier upgrade when OTS confirms |
| `docs/PREDICTION_CANONICAL_SCHEMA.md` | Full schema reference |

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial policy document. All 1115 predictions classified as PROVISIONAL after Phase 3 backfill. |
