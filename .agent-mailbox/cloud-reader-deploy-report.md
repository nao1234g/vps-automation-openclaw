# Reader Leaderboard Integrity — VPS Deployment Report

**Date**: 2026-04-04 16:59 JST (UTC 07:59)
**Agent**: cloud-claude (Claude Opus 4.6)
**VPS**: 163.44.124.123

---

## Deployed Files

| Local Path | VPS Path | Action |
|------------|----------|--------|
| `scripts/reader_prediction_api.py` | `/opt/shared/scripts/reader_prediction_api.py` | Updated (backup: `.bak-20260404-pre-integrity`) |
| `scripts/test_reader_prediction_api.py` | `/opt/shared/scripts/test_reader_prediction_api.py` | New file |

## Service

| Item | Value |
|------|-------|
| Service name | `reader-predict.service` |
| Unit file | `/etc/systemd/system/reader-predict.service` |
| Restart command | `systemctl restart reader-predict.service` |
| PID after restart | 550678 |
| Port | 8766 (127.0.0.1) |
| Public endpoint | `https://nowpattern.com/reader-predict/*` (via Caddy) |

## Test Results (VPS)

```
9 passed, 0 failed, 9 total
```

Including `test_module_sync` which verified the inline test replica matches the actual deployed module constants and function.

---

## Before / After Comparison

### `/reader-predict/leaderboard` — readers aggregate

| Field | BEFORE | AFTER | Change |
|-------|--------|-------|--------|
| `readers.total_voters` | **9** | **2** | -7 (removed AI + 6 synthetic UUIDs) |
| `readers.total_votes` | **1129** | **2** | -1127 (removed 1121 AI + 4 test/migrated + 2 other synthetic) |
| `readers.resolved_votes` | 52 | 1 | Human-only resolved count |
| `readers.avg_brier_score` | 0.48 | 0.5625 | Human-only Brier (small sample) |
| `readers.avg_brier_index` | 30.7 | 25.0 | Human-only index |
| `readers.accuracy_pct` | 76.9 | 0.0 | Human-only accuracy (1 resolved, 0 correct) |
| `readers.correct_count` | 40 | 0 | Human-only |

### `/reader-predict/leaderboard` — AI row (unchanged, as expected)

| Field | BEFORE | AFTER |
|-------|--------|-------|
| `ai.avg_brier_score` | 0.4608 | 0.4608 |
| `ai.avg_brier_index` | 32.1 | 32.1 |
| `ai.resolved_count` | 54 | 54 |
| `ai.resolved_total` | 58 | 58 |
| `ai.not_scorable_count` | 4 | 4 |
| `ai.accuracy_pct` | 66.7 | 66.7 |
| `ai.correct_count` | 36 | 36 |

### `/reader-predict/top-forecasters`

| BEFORE (4 entries) | AFTER (2 entries) |
|--------------------|-------------------|
| `test-uuid-12345` (is_ai=false, votes=1) | **REMOVED** |
| `neo-one-ai-player` (is_ai=true, votes=1121) | `neo-one-ai-player` (is_ai=true, votes=1121) |
| `migrated_50ab1ad008970ec6` (is_ai=false, votes=1) | **REMOVED** |
| `r-1772864281172-1dpwirl6` (is_ai=false, votes=1) | `r-1772864281172-1dpwirl6` (is_ai=false, votes=1) |

### `/reader-predict/my-stats/*`

| UUID | Status |
|------|--------|
| `neo-one-ai-player` | 200 OK |
| `r-1772864281172-1dpwirl6` | 200 OK |
| `nonexistent-uuid` | 200 OK |

### `/reader-predict/health`

```json
{"status": "ok", "version": "2.0.0", "db": "/opt/shared/reader_predictions.db"}
```

---

## What Was Wrong (Before)

1. `neo-one-ai-player` contributed 1121 of 1129 total votes, inflating `readers.total_votes` and dominating `readers.avg_brier_score`
2. `test-uuid-12345` (test harness) and `migrated_50ab1ad008970ec6` (legacy migration artifact) appeared as human forecasters in the top-forecasters ranking
3. The "AI vs Readers" comparison on the leaderboard was mathematically meaningless because the AI's own votes were counted in the reader aggregate

## What Changed (After)

1. `is_synthetic_voter()` helper filters exact-match (`neo-one-ai-player`) and prefix-match (`test-*`, `migrated_*`) UUIDs
2. Leaderboard `readers.*` fields now reflect human-only aggregates
3. Top-forecasters excludes all synthetic voters from the human ranking
4. AI row remains as explicit separate entry (sourced from `_ai_official_score_summary()` using prediction_db.json, not from reader_votes)
5. `my-stats` endpoint is unaffected — works for any UUID

---

## Residual Risks

1. **Small human sample**: Only 2 real human voters with 2 total votes. Reader aggregate stats will be volatile until more real humans participate. This is correct behavior — the previous numbers were artificially inflated.
2. **New synthetic patterns**: If new test/migration scripts create votes with different UUID patterns, they won't be caught until `SYNTHETIC_VOTER_EXACT` or `SYNTHETIC_VOTER_PREFIXES` are updated in `reader_prediction_api.py`.
3. **Test replica drift**: The test file's inline copy of the helper must stay in sync with the actual module. `test_module_sync` catches this on VPS where FastAPI is available.

## No Blockers

All goals met. No outstanding issues.

---

## Verification Commands (for future reference)

```bash
# Test suite
python3 /opt/shared/scripts/test_reader_prediction_api.py

# Leaderboard check
curl -s http://localhost:8766/reader-predict/leaderboard | python3 -m json.tool

# Top forecasters check
curl -s http://localhost:8766/reader-predict/top-forecasters | python3 -m json.tool

# Service status
systemctl status reader-predict.service

# Rollback (if needed)
cp /opt/shared/scripts/reader_prediction_api.py.bak-20260404-pre-integrity /opt/shared/scripts/reader_prediction_api.py
systemctl restart reader-predict.service
```
