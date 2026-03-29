# Prediction Platform — Workstream Status

> Live status of all 11 workstreams (WS0–WS10).
> Last updated: 2026-03-29 (post Phase 1-3 migration)

---

## Summary

| Status | Count |
|--------|-------|
| ✅ Complete | 8 |
| 🔄 In Progress | 2 |
| ⏳ Pending | 1 |

---

## WS0: Baseline Inventory

**Status**: ✅ Complete

- [x] Full field coverage audit (1115 predictions × all fields)
- [x] Integrity proof assessment (OTS, SHA-256, ledger)
- [x] Critical gap identification (6 gaps)
- [x] 24/26 acceptance tests PASS baseline established

**Output**: `docs/PREDICTION_PLATFORM_PHASE0_BASELINE_REPORT.md`

---

## WS1: Canonical Schema Migration

**Status**: 🔄 In Progress

Executing via `phase10_canonical_migration.py` on VPS (agent a3b2b60).

- [ ] `question_type`: 1091 empty → `BINARY_BY_DEADLINE`
- [ ] `question_type`: 24 old `"binary"` → `BINARY_BY_DEADLINE`
- [ ] `semantic_key`: generate `np_yyyy_nnnn` format for all 1115
- [ ] `canonical_question`: set from `resolution_question_en` where available
- [ ] `evidence_grace_days`: compute from `evidence_grace_until - event_cutoff_at`
- [ ] Enum wild-value verification (no invalid status/verdict values)

**Output**: `phase10_canonical_migration.py` (VPS: /opt/shared/scripts/)

---

## WS2: Score Provenance System

**Status**: ✅ Complete (Phase 3)

Executed via `phase11_initial_prob_backfill.py` — 2026-03-29T11:12:26Z

- [x] `initial_prob` = `our_pick_prob` for all 1115 (write-once)
- [x] `initial_prob_source` = `FROM_CURRENT_VALUE_BACKFILL` for all 1115
- [x] `initial_prob_provenance` = audit string for all 1115
- [x] `official_score_tier` = `PROVISIONAL` (1111) or `NOT_SCORABLE` (4)
- [x] `meta.official_brier_avg_initial_prob` = 0.4697 (PROVISIONAL, n=53)
- [x] `meta.score_provenance_locked_at` set

**Output**: `docs/PREDICTION_SCORE_PROVENANCE_POLICY.md`

---

## WS3: Resolution Policy Schema

**Status**: ✅ Complete (Phase 2)

Executed via `phase12_resolution_policy.py` — 2026-03-29T11:14:25Z

- [x] `resolution_criteria` schema added to all 1115 (empty, `NEEDS_FILL`)
- [x] `authoritative_sources: []` added to all 1115
- [x] `unresolved_policy` verified on all 1115 (already set: `AUTO_NO_AT_DEADLINE`)
- [x] `meta.resolution_policy_schema_version` = `"1.0"`

**⚠️ Content pending**: yes/no/void criteria for 1115 predictions requires editorial fill-in.
Priority: RESOLVED 52 → OPEN 35 → AWAITING_EVIDENCE 1023.

**Output**: `docs/PREDICTION_RESOLUTION_POLICY.md`

---

## WS4: Publish Gates

**Status**: ✅ Complete (schema)

Hard gates embedded in `prediction_page_builder.py`:
- [x] Gate A: schema_version check
- [x] Gate B: initial_prob coverage
- [x] Gate C: official_score_tier coverage
- [x] Gate D: Oracle Guardian < 5%
- [x] Gate E: Brier formula sanity
- [ ] Gate F: Provisional label enforcement (implementation pending)

**Output**: `docs/PREDICTION_PUBLISH_GATES.md`

---

## WS5: Score Display Honesty

**Status**: 🔄 In Progress (pending prediction_page_builder.py update)

Required changes to `prediction_page_builder.py`:
- [ ] Display `official_score_tier` label on all score displays
- [ ] PROVISIONAL scores show "暫定計算値" / "Provisional"
- [ ] Aggregate Brier Score shows PROVISIONAL tier label
- [ ] No display of "公式確定" / "certified official" language

---

## WS6: Silent EN Fallback Fix

**Status**: ⏳ Pending

- 10 predictions with empty `hit_condition_en` silently render Japanese text on EN page
- 7 predictions with CJK contamination in EN fields
- Fix: editorial review of these 17 predictions

---

## WS7: New Reader-Facing Pages

**Status**: ⏳ Pending (blocked by WS1-5 completion)

New Ghost pages to create:
- [ ] `/forecasting-methodology/` (JA) + `/en/forecasting-methodology/` (EN)
- [ ] `/forecast-scoring-and-resolution/` (JA) + `/en/forecast-scoring-and-resolution/` (EN)
- [ ] `/forecast-integrity-and-audit/` (JA) + `/en/forecast-integrity-and-audit/` (EN)

Caddy config updates required for EN routes.

**Output**: `docs/PREDICTION_READER_PAGES_SPEC.md`

---

## WS8: OTS Confirmation Monitoring

**Status**: ✅ Operational (pending confirmations)

- [x] OTS files created (1115)
- [x] prediction_timestamper.py running hourly
- [ ] Bitcoin blockchain confirmations received (ALL still pending as of 2026-03-29)
- [ ] Auto-upgrade PROVISIONAL → MIGRATED_OFFICIAL on confirmation

---

## WS9: EvolutionLoop Integration

**Status**: ✅ Operational

- [x] evolution_loop.py runs weekly (Sunday JST 09:00)
- [x] category_brier.json generated (`/opt/shared/logs/category_brier.json`)
- [x] AGENT_WISDOM.md self-updating
- [x] Observer log active (`/opt/shared/observer_log/`)

---

## WS10: Polymarket Sync

**Status**: ✅ Operational

- [x] polymarket_sync.py deployed
- [x] Daily cron at 21:30 UTC
- [x] market_consensus data flowing to prediction_db.json

---

## Next Actions (priority order)

1. **WS1 Phase 10 migration** — waiting for agent a3b2b60 to complete
2. **WS5 score display** — update prediction_page_builder.py with PROVISIONAL labels
3. **WS6 EN fallback** — fix 17 predictions with empty/contaminated EN fields
4. **WS7 new pages** — create 6 reader-facing methodology/scoring/integrity pages
5. **WS4 Gate F** — implement provisional label enforcement check

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial workstream status document. Phase 2+3 marked complete. Phase 1 in progress. |
