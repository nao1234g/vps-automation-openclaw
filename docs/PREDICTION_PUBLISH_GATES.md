# Prediction Platform Publish Gates

> Hard gates that MUST pass before any prediction page is deployed.
> These are embedded in the deploy path and cannot be bypassed.
> Last updated: 2026-03-29

---

## Gate Overview

| Gate | Name | Enforced by | Blocks on |
|------|------|-------------|-----------|
| A | Schema version check | prediction_page_builder.py | schema_version != "2.0" |
| B | initial_prob coverage | prediction_page_builder.py | any prediction missing initial_prob |
| C | official_score_tier coverage | prediction_page_builder.py | any prediction missing official_score_tier |
| D | Oracle Guardian | prediction_page_builder.py | block_rate > 5% |
| E | Brier formula sanity | prediction_page_builder.py | formula result out of [0,1] range |
| F | Provisional label enforcement | prediction_page_builder.py | PROVISIONAL score displayed without tier label |

---

## Gate Definitions

### Gate A — Schema Version Check

```python
assert db["meta"]["schema_version"] == "2.0", "Schema version mismatch"
```

Fails if: prediction_db.json hasn't been migrated to schema v2.0.

### Gate B — initial_prob Coverage

```python
missing = [p["prediction_id"] for p in preds if p.get("initial_prob") is None]
assert len(missing) == 0, f"initial_prob missing on {len(missing)} predictions"
```

Fails if: any prediction lacks `initial_prob` (would cause Brier calculation error).

### Gate C — official_score_tier Coverage

```python
missing = [p["prediction_id"] for p in preds if not p.get("official_score_tier")]
assert len(missing) == 0, f"official_score_tier missing on {len(missing)} predictions"
```

Fails if: any prediction lacks tier classification (affects display logic).

### Gate D — Oracle Guardian

```python
# Defined in prediction_page_builder.py
# Counts predictions where oracle block condition is met
block_rate = blocked_count / total_count
assert block_rate <= 0.05, f"Oracle block rate {block_rate:.1%} > 5% threshold"
```

Fails if: more than 5% of predictions are blocked from display (quality issue).

### Gate E — Brier Formula Sanity

```python
for p in resolved_preds:
    bs = p.get("brier_score")
    assert bs is None or 0.0 <= bs <= 1.0, f"Brier score {bs} out of range for {p['prediction_id']}"
```

Fails if: any Brier score is outside [0.0, 1.0] (calculation error).

### Gate F — Provisional Label Enforcement

```python
# Checks that PROVISIONAL tier predictions are not displayed with
# language like "公式確定" or "official" without the tier disclaimer
# This is a content check, not a data check
```

Fails if: reader-facing HTML contains tier-upgrade language without proper disclosure.

---

## Adding New Gates

To add a gate:
1. Add assertion to `prediction_page_builder.py` before page generation begins
2. Document it in this file
3. Add a test case to the acceptance test suite
4. Update this CHANGELOG

---

## Current Gate Status (2026-03-29)

| Gate | Status | Notes |
|------|--------|-------|
| A | ✅ PASS | schema_version = "2.0" |
| B | ✅ PASS | initial_prob set on 1115/1115 (Phase 3) |
| C | ✅ PASS | official_score_tier set on 1115/1115 (Phase 3) |
| D | ✅ PASS | Oracle Guardian: block_rate < 5% |
| E | ✅ PASS | All 52 Brier scores in [0,1] range |
| F | ⚠️ PENDING | Implementation pending prediction_page_builder.py update |

---

## Gate Failure Response

When a gate fails:
1. Page generation aborts immediately
2. Error logged to `/opt/shared/logs/prediction_page_builder.log`
3. Telegram alert sent to Naoto
4. Previous version of page is served (no update)

**Do NOT manually bypass gates** (`--skip-gates` flag is disabled in production).

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial document. Gates A-E verified PASS after Phase 3 migration. Gate F pending. |
