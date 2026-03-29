# Prediction Canonical Schema Reference

> **Single Source of Truth for prediction_db.json field definitions.**
> Last updated: 2026-03-29 (Phase 1-3 migration)

---

## Schema Version

Current: `schema_version = "2.0"` (set in `meta.schema_version`)

---

## Top-level Structure

```json
{
  "meta": { ... },
  "predictions": [ ... ]
}
```

---

## meta object

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | "2.0" |
| `last_updated` | ISO datetime | Last write timestamp |
| `total_predictions` | int | Count of predictions array |
| `official_brier_avg` | float | Brier avg from `our_pick_prob` (legacy) |
| `official_brier_avg_initial_prob` | float | Brier avg from `initial_prob` (canonical) |
| `official_brier_avg_initial_prob_tier` | string | Tier label (currently "PROVISIONAL") |
| `official_brier_avg_initial_prob_n` | int | Number of RESOLVED predictions in avg |
| `score_provenance_locked_at` | ISO datetime | When Phase 3 backfill ran |
| `score_provenance_summary` | object | Tier counts + provenance note |
| `resolution_policy_schema_version` | string | "1.0" after Phase 2 migration |
| `resolution_policy_migrated_at` | ISO datetime | When Phase 2 ran |

---

## prediction object

### Identity fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prediction_id` | string | ✅ | Format: `NP-YYYY-NNNN` (e.g., `NP-2026-0001`) |
| `semantic_key` | string | Phase 1 | Lowercase slug: `np_yyyy_nnnn` (e.g., `np_2026_0001`) |
| `canonical_question` | string | Phase 1 | English question from `resolution_question_en` |
| `article_slug` | string | ✅ | Ghost CMS article slug |
| `article_url` | string | - | Full URL to article |

### Classification fields

| Field | Type | Enum values | Description |
|-------|------|-------------|-------------|
| `question_type` | string | `BINARY_BY_DEADLINE`, `BINARY_OPEN`, `RANGE`, `MULTINOMIAL` | Prediction format |
| `category` | string | geopolitics, economics, technology, ... | Topic category |
| `tags` | array[string] | - | Force-dynamic tags from taxonomy |

**question_type backfill**: All 1115 predictions set to `BINARY_BY_DEADLINE` as of Phase 1 migration.

### Timing fields

| Field | Type | Description |
|-------|------|-------------|
| `created_at` | ISO datetime | When prediction was created |
| `event_cutoff_at` | ISO datetime | Deadline for the predicted event |
| `evidence_grace_until` | ISO datetime | Deadline for evidence collection |
| `evidence_grace_days` | int | Days between `event_cutoff_at` and `evidence_grace_until` |
| `oracle_deadline` | ISO datetime | Legacy alias for `event_cutoff_at` |

### Probability fields

| Field | Type | Description |
|-------|------|-------------|
| `our_pick_prob` | int (0–100) | Current/working probability — may change |
| `our_pick` | string | "YES", "NO", or specific outcome label |
| `initial_prob` | int (0–100) | **Locked** initial probability for Brier calculation. Write-once. |
| `initial_prob_source` | enum | Evidence source (see PREDICTION_SCORE_PROVENANCE_POLICY.md) |
| `initial_prob_provenance` | string | Audit string explaining evidence quality |
| `official_score_tier` | enum | VERIFIED_OFFICIAL / MIGRATED_OFFICIAL / PROVISIONAL / NOT_SCORABLE |

**INVARIANT**: `initial_prob` is write-once. Never overwrite after first set.

### Resolution fields

| Field | Type | Enum values | Description |
|-------|------|-------------|-------------|
| `status` | string | OPEN, AWAITING_EVIDENCE, RESOLVING, RESOLVED, EXPIRED_UNRESOLVED | Lifecycle state |
| `verdict` | string | PENDING, HIT, MISS, NOT_SCORED | Resolution outcome |
| `unresolved_policy` | string | AUTO_NO_AT_DEADLINE, MANUAL, VOID_AT_DEADLINE | How to handle unresolved predictions at deadline |
| `resolution_date` | ISO date | When verdict was set |
| `resolution_notes` | string | Human-readable resolution explanation |
| `resolution_evidence_url` | string | URL to authoritative evidence |

**unresolved_policy**: All 1115 predictions use `AUTO_NO_AT_DEADLINE`.

### Resolution criteria fields (Phase 2 — schema only, content pending)

| Field | Type | Description |
|-------|------|-------------|
| `resolution_criteria.yes_criteria_ja` | string | Japanese: conditions for HIT verdict |
| `resolution_criteria.yes_criteria_en` | string | English: conditions for HIT verdict |
| `resolution_criteria.no_criteria_ja` | string | Japanese: conditions for MISS verdict |
| `resolution_criteria.no_criteria_en` | string | English: conditions for MISS verdict |
| `resolution_criteria.void_criteria` | string | Conditions for void/NOT_SCORED |
| `resolution_criteria.editorial_note` | string | Internal note (e.g., "NEEDS_FILL") |
| `authoritative_sources` | array[string] | URLs or source names for verification |

**Status**: Schema structure added to all predictions 2026-03-29. Content not yet authored.

### Score tracking fields

| Field | Type | Description |
|-------|------|-------------|
| `brier_score` | float | Computed Brier score (only on RESOLVED verdicts) |
| `brier_score_formula` | string | "BS = (initial_prob/100 - outcome)²" |
| `market_consensus` | object | Polymarket or other market probability at prediction time |

### Integrity / timestamping fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp_sha256` | string | SHA-256 hash when prediction was first recorded |
| `timestamp_pending` | bool | `true` = OTS blockchain proof not yet confirmed |
| `ots_file` | string | Path to `.ots` file on VPS |

---

## Status State Machine

```
OPEN
  ↓ (event cutoff approaches)
AWAITING_EVIDENCE
  ↓ (auto_verifier checks for outcome)
RESOLVING
  ↓ (outcome confirmed)
RESOLVED  ← verdict = HIT / MISS / NOT_SCORED

OR:
AWAITING_EVIDENCE
  ↓ (evidence_grace_until passed, no outcome found)
EXPIRED_UNRESOLVED ← verdict = PENDING
```

---

## Enum Reference

### question_type
| Value | Meaning |
|-------|---------|
| `BINARY_BY_DEADLINE` | Yes/No question, resolves at event_cutoff_at |
| `BINARY_OPEN` | Yes/No question, no fixed deadline |
| `RANGE` | Numeric range prediction |
| `MULTINOMIAL` | Multiple-choice outcome |

### status
| Value | Meaning |
|-------|---------|
| `OPEN` | Prediction is live, event has not yet reached cutoff |
| `AWAITING_EVIDENCE` | Event cutoff passed, gathering resolution evidence |
| `RESOLVING` | Auto-verifier has candidate resolution, under review |
| `RESOLVED` | Final verdict rendered |
| `EXPIRED_UNRESOLVED` | Evidence grace period expired, no resolution found |

### verdict
| Value | Meaning | Brier scorable |
|-------|---------|----------------|
| `PENDING` | No verdict yet | No |
| `HIT` | Prediction was correct | Yes |
| `MISS` | Prediction was wrong | Yes |
| `NOT_SCORED` | Excluded from scoring (void, edge case) | No |

### official_score_tier
See [PREDICTION_SCORE_PROVENANCE_POLICY.md](PREDICTION_SCORE_PROVENANCE_POLICY.md) for full definitions.

---

## Coverage as of 2026-03-29

| Field | Coverage | Notes |
|-------|----------|-------|
| prediction_id | 1115/1115 | ✅ |
| semantic_key | Phase 1 migration | Pending Phase 1 completion |
| canonical_question | Phase 1 migration | Pending Phase 1 completion |
| question_type | Phase 1 migration | 1091 empty → BINARY_BY_DEADLINE |
| event_cutoff_at | ~99% | ✅ |
| evidence_grace_until | ~99% | ✅ |
| evidence_grace_days | Phase 1 migration | Pending Phase 1 completion |
| initial_prob | 1115/1115 | ✅ Phase 3 complete |
| initial_prob_source | 1115/1115 | ✅ Phase 3 complete |
| official_score_tier | 1115/1115 | ✅ Phase 3 complete |
| resolution_criteria | 1115/1115 schema | Phase 2 schema added, content pending |
| authoritative_sources | 1115/1115 schema | Phase 2 schema added, content pending |
| brier_score | 52/52 RESOLVED | ✅ |

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial schema doc. Covers Phase 1-3 migration results. |
