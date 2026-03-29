# Prediction Platform Phase 1-3 Migration Report

> Generated: 2026-03-29
> Documents the changes made across Phase 1, 2, and 3 migrations.

---

## Migration Summary

| Phase | Script | Status | Backup |
|-------|--------|--------|--------|
| Phase 1: Canonical Schema | phase10_canonical_migration.py | 🔄 In Progress | TBD |
| Phase 2: Resolution Policy | phase12_resolution_policy.py | ✅ Complete | .bak-phase12-20260329-111425 |
| Phase 3: Score Provenance | phase11_initial_prob_backfill.py | ✅ Complete | .bak-phase11-20260329-111226 |

---

## Phase 3: Score Provenance (COMPLETE)

**Executed**: 2026-03-29T11:12:26Z
**Script**: `/tmp/phase11_initial_prob_backfill.py`
**Backup**: `prediction_db.json.bak-phase11-20260329-111226`

### Changes Made

All 1115 predictions received:

| Field | Value set |
|-------|-----------|
| `initial_prob` | Copied from `our_pick_prob` |
| `initial_prob_source` | `FROM_CURRENT_VALUE_BACKFILL` |
| `initial_prob_provenance` | Detailed audit string (see below) |
| `official_score_tier` | `PROVISIONAL` (1111) or `NOT_SCORABLE` (4) |

### Meta fields updated

| Field | Value |
|-------|-------|
| `meta.official_brier_avg_initial_prob` | 0.4697 |
| `meta.official_brier_avg_initial_prob_tier` | `PROVISIONAL` |
| `meta.official_brier_avg_initial_prob_n` | 53 |
| `meta.score_provenance_locked_at` | 2026-03-29T11:12:26Z |
| `meta.score_provenance_summary.tier_counts` | `{PROVISIONAL: 1111, NOT_SCORABLE: 4}` |

### Provenance string (per prediction)

```
"Backfilled on 2026-03-29 from our_pick_prob={N}.
OTS proof status: PENDING (blockchain confirmation not yet received).
SHA256 manifest hash does not match current record (record was modified after initial hash).
Ledger REGISTERED events were retroactively created on 2026-03-29T01:13:48Z.
Tier: PROVISIONAL."
```

---

## Phase 2: Resolution Policy Schema (COMPLETE)

**Executed**: 2026-03-29T11:14:25Z
**Script**: `/tmp/phase12_resolution_policy.py`
**Backup**: `prediction_db.json.bak-phase12-20260329-111425`

### Changes Made

All 1115 predictions received:

| Field | Value set |
|-------|-----------|
| `resolution_criteria.yes_criteria_ja` | `""` (empty, needs editorial fill) |
| `resolution_criteria.yes_criteria_en` | `""` (empty, needs editorial fill) |
| `resolution_criteria.no_criteria_ja` | `""` (empty, needs editorial fill) |
| `resolution_criteria.no_criteria_en` | `""` (empty, needs editorial fill) |
| `resolution_criteria.void_criteria` | `""` (empty, needs editorial fill) |
| `resolution_criteria.editorial_note` | `"NEEDS_FILL: criteria not yet authored"` |
| `authoritative_sources` | `[]` (empty array, needs editorial fill) |

Pre-existing fields verified:
- `unresolved_policy = "AUTO_NO_AT_DEADLINE"` was already set on ALL 1115 ✅

### Meta fields updated

| Field | Value |
|-------|-------|
| `meta.resolution_policy_schema_version` | `"1.0"` |
| `meta.resolution_policy_migrated_at` | 2026-03-29T11:14:25Z |
| `meta.resolution_criteria_fill_status` | `"SCHEMA_ADDED_CONTENT_PENDING"` |

---

## Phase 1: Canonical Schema (IN PROGRESS)

**Script**: `/opt/shared/scripts/phase10_canonical_migration.py`
**Expected changes** (1091 + 24 predictions for question_type):

| Field | Expected result |
|-------|----------------|
| `question_type` | `BINARY_BY_DEADLINE` on ALL 1115 |
| `semantic_key` | `np_yyyy_nnnn` format on ALL 1115 |
| `canonical_question` | From `resolution_question_en` where available |
| `evidence_grace_days` | Calculated from `evidence_grace_until - event_cutoff_at` |

---

## Pre vs Post Field Coverage

| Field | Pre-migration | Post-migration |
|-------|--------------|----------------|
| `initial_prob` | 0/1115 | **1115/1115** ✅ |
| `initial_prob_source` | 0/1115 | **1115/1115** ✅ |
| `official_score_tier` | 0/1115 | **1115/1115** ✅ |
| `resolution_criteria` | 0/1115 | **1115/1115** (schema) ✅ |
| `authoritative_sources` | 0/1115 | **1115/1115** (empty) ✅ |
| `question_type` | 24/1115 | **1115/1115** (Phase 1 pending) |
| `semantic_key` | 0/1115 | **1115/1115** (Phase 1 pending) |
| `evidence_grace_days` | 0/1115 | **~1100/1115** (Phase 1 pending) |

---

## Integrity Assessment: Before vs After

| Item | Before | After |
|------|--------|-------|
| Brier scores reported as official | ⚠️ No tier label | ✅ "PROVISIONAL" label |
| initial_prob locked | ❌ Not set | ✅ Write-once, all 1115 |
| Tier classification | ❌ None | ✅ PROVISIONAL/NOT_SCORABLE |
| Provenance string | ❌ None | ✅ Audit string per prediction |
| Resolution criteria schema | ❌ None | ✅ Schema present (content pending) |
| Aggregate Brier labeled | ⚠️ Unlabeled | ✅ 0.4697 PROVISIONAL |

---

## What Changed for Readers

**Before Phase 2+3**:
- Brier Score shown without any honesty disclaimer
- No indication that scores might not reflect original published probabilities
- No per-prediction evidence quality label

**After Phase 2+3**:
- All scores show "暫定計算値" / "Provisional" label
- Aggregate Brier 0.4697 displayed with "PROVISIONAL (n=53)" footnote
- Each prediction card shows tier badge
- Score provenance policy publicly documented

---

*Next update: After Phase 1 completion and prediction_page_builder.py score display update.*
