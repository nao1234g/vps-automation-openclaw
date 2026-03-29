# Prediction Platform — Phase 0 Baseline Inventory Report

> Generated: 2026-03-29
> Purpose: Document the verified state BEFORE Phase 1-3 migrations began.
> This is the "before" snapshot. See PREDICTION_PLATFORM_MIGRATION_COMPLETE.md for "after".

---

## Summary

| Category | Status |
|----------|--------|
| Schema version | 2.0 |
| Total predictions | 1115 |
| Completed workstreams (pre-migration) | 15/26 |
| Critical gaps identified | 6 |

---

## Verified Complete Items (Phase 0 confirmed)

### Schema & Enums
- ✅ `schema_version = "2.0"` in meta
- ✅ `status` enum: OPEN, AWAITING_EVIDENCE, RESOLVING, RESOLVED, EXPIRED_UNRESOLVED
- ✅ `verdict` enum: PENDING, HIT, MISS, NOT_SCORED
- ✅ `event_cutoff_at` set on ~99% of predictions
- ✅ `evidence_grace_until` set on ~99% of predictions
- ✅ `article_slug` set on ~99% of predictions (article linkage)
- ✅ `brier_score` computed on 52/52 RESOLVED predictions

### Status Distribution (baseline)
| Status | Count |
|--------|-------|
| AWAITING_EVIDENCE | 1023 |
| RESOLVED | 52 |
| OPEN | 35 |
| EXPIRED_UNRESOLVED | 5 |
| **Total** | **1115** |

### Verdict Distribution (baseline)
| Verdict | Count |
|---------|-------|
| PENDING | 1058 |
| HIT | 35 |
| MISS | 18 |
| NOT_SCORED | 4 |

### Integrity infrastructure
- ✅ `prediction_manifest.json`: 1115 entries with SHA-256 hashes
- ✅ `prediction_ledger.jsonl`: 1172 events (REGISTERED×1115, RESOLVED×52, EXPIRED×5)
- ✅ OTS `.ots` files: 1115 files created
- ✅ Oracle Guardian gate: block_rate < 5%
- ✅ 6 public-facing pages live: /predictions/, /en/predictions/, /forecast-rules/, /scoring-guide/, /integrity-audit/ (JA+EN)
- ✅ 24/26 acceptance tests PASS | 2 WARN | 0 FAIL

---

## Critical Gaps Identified (Phase 0 → targeted by Phase 1-3)

### GAP 1: question_type empty (CRITICAL)
- `question_type = ""` on 1091/1115 predictions (97.8%)
- `question_type = "binary"` on 24/1115 (old format, non-canonical)
- **Fix**: Phase 1 migration → all → `BINARY_BY_DEADLINE`

### GAP 2: initial_prob missing (CRITICAL)
- `initial_prob` = 0/1115 (0%)
- Without this, Brier scores cannot be officially attributed to an immutable value
- **Fix**: Phase 3 backfill → `initial_prob = our_pick_prob` with PROVISIONAL tier

### GAP 3: official_score_tier missing (CRITICAL)
- `official_score_tier` = 0/1115 (0%)
- Scores were being reported without clarity on evidence quality
- **Fix**: Phase 3 backfill → PROVISIONAL for 1111, NOT_SCORABLE for 4

### GAP 4: semantic_key missing
- `semantic_key` = 0/1115 (0%)
- Needed for programmatic prediction reference
- **Fix**: Phase 1 migration → `np_yyyy_nnnn` format

### GAP 5: Integrity proofs unverified
- OTS: ALL 1115 have `timestamp_pending = True` (blockchain confirmation pending)
- SHA-256: Manifest hashes do NOT match current prediction JSON
- Ledger timestamps: ALL retroactive (2026-03-29T01:13:48Z)
- **Impact**: All scores classified PROVISIONAL — cannot claim VERIFIED_OFFICIAL

### GAP 6: Resolution criteria empty
- `yes_criteria`, `no_criteria` = 0/1115 (0%)
- `authoritative_sources` = 0/1115 (0%)
- **Fix**: Phase 2 schema added; content fill-in is multi-sprint editorial work

---

## Integrity Proof Assessment

### OTS (OpenTimestamps)
- Files: ✅ 1115 `.ots` files exist
- Confirmed: ❌ ALL `timestamp_pending = True`
- Blockchain status: **PENDING** — Bitcoin confirmation not yet received
- Impact: Cannot claim immutable timestamp proof for any prediction

### SHA-256 Manifest
- Entries: ✅ 1115 entries in prediction_manifest.json
- Match: ❌ Hashes do NOT match current prediction JSON
  - Records were modified after initial hash was computed
  - The manifest records a hash of an older state
- Impact: Cannot prove current `our_pick_prob` matches originally-published probability

### Ledger
- Events: ✅ 1172 events in prediction_ledger.jsonl
- REGISTERED timestamps: ❌ ALL `ts = 2026-03-29T01:13:48Z`
  - Retroactively created during Phase 6 backfill on 2026-03-29
  - NOT the original prediction publish timestamps
- Impact: Cannot prove original publish date for any prediction

### Conclusion
All 1115 predictions must be classified **PROVISIONAL** based on:
- OTS pending
- SHA-256 mismatch
- Retroactive ledger

This is the correct, honest classification. Display as "暫定計算値" until OTS confirms.

---

## Acceptance Test Baseline (24/26 PASS)

| Test | Result | Notes |
|------|--------|-------|
| schema_version = "2.0" | ✅ PASS | |
| status enum valid | ✅ PASS | |
| verdict enum valid | ✅ PASS | |
| brier_score on RESOLVED | ✅ PASS | 52/52 |
| event_cutoff_at presence | ✅ PASS | 99%+ |
| evidence_grace_until presence | ✅ PASS | 99%+ |
| article_slug presence | ✅ PASS | 99%+ |
| Oracle Guardian < 5% | ✅ PASS | |
| /predictions/ page loads | ✅ PASS | |
| /en/predictions/ page loads | ✅ PASS | |
| Brier formula correctness | ✅ PASS | spot-checked |
| Manifest 1115 entries | ✅ PASS | |
| Ledger REGISTERED count | ✅ PASS | |
| JA/EN page bilingual | ✅ PASS | |
| ... (24 total PASS) | | |
| question_type coverage | ⚠️ WARN | 1091 empty |
| initial_prob coverage | ⚠️ WARN | 0/1115 |

---

## Files Verified

| File | Size (approx) | Location |
|------|---------------|----------|
| prediction_db.json | ~8MB | /opt/shared/scripts/ |
| prediction_manifest.json | ~300KB | /opt/shared/scripts/ |
| prediction_ledger.jsonl | ~200KB | /opt/shared/scripts/ |
| *.ots files | 1115 files | /opt/shared/scripts/ots/ |

---

*End of Phase 0 Baseline Report. See PREDICTION_PLATFORM_MIGRATION_COMPLETE.md for Phase 1-9 completion status.*
