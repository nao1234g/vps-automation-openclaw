# Brier Score Methodology

> How Nowpattern computes, validates, and displays prediction accuracy.
> Last updated: 2026-03-29

---

## Formula

```
BS = (initial_prob / 100 − actual_outcome)²
```

Where:
- `initial_prob` = the probability locked at prediction creation time (0–100 integer)
- `actual_outcome` = 1 if verdict is HIT, 0 if verdict is MISS

**Range**: 0.0 (perfect) to 1.0 (maximally wrong)

### Reference points

| Forecaster | Brier Score | Description |
|------------|-------------|-------------|
| Perfect | 0.000 | Always 100% confident and always right |
| Excellent | < 0.150 | Superforecaster level |
| Good | 0.150–0.200 | Well-calibrated forecaster |
| Fair | 0.200–0.300 | Better than naive baseline |
| Naive (always 50%) | 0.250 | Random guessing baseline |
| Poor | > 0.300 | Worse than random at extremes |
| Maximally wrong | 1.000 | Always 100% confident and always wrong |

### Example calculations

| prediction_id | initial_prob | verdict | outcome | Brier Score |
|---------------|-------------|---------|---------|-------------|
| NP-2026-0921 | 11 | HIT | 1 | (0.11 - 1)² = 0.7921 |
| NP-2026-0988 | 6 | HIT | 1 | (0.06 - 1)² = 0.8836 |
| NP-2026-0001 | 75 | HIT | 1 | (0.75 - 1)² = 0.0625 |
| NP-2026-0001 | 75 | MISS | 0 | (0.75 - 0)² = 0.5625 |

---

## Aggregate Score

```
avg_BS = mean(BS_i) over all RESOLVED predictions with verdict ∈ {HIT, MISS}
```

**Current state** (2026-03-29):
- `official_brier_avg_initial_prob = 0.4697`
- `n = 53` RESOLVED predictions
- Tier: **PROVISIONAL** (see [PREDICTION_SCORE_PROVENANCE_POLICY.md](PREDICTION_SCORE_PROVENANCE_POLICY.md))

Note: 0.4697 is in the "Poor" range because many predictions with low probability (5–15%) resolved as HIT,
which is a known calibration issue in early predictions. The EvolutionLoop is tracking this pattern.

---

## initial_prob vs our_pick_prob

| Field | Purpose | Mutable |
|-------|---------|---------|
| `initial_prob` | Locked at publish time, used for Brier calculation | **NO** (write-once) |
| `our_pick_prob` | Working probability, may be updated as evidence evolves | Yes |

**INVARIANT**: Once `initial_prob` is set, it is never overwritten.
The Brier score formula uses `initial_prob`, NOT `our_pick_prob`.
This ensures scores cannot be gamed by retroactively adjusting probabilities.

---

## Category-level Brier Scores

Category-level Brier analysis is run by `/opt/shared/scripts/category_brier_analysis.py`
and stored in `/opt/shared/logs/category_brier.json`.

This allows identifying which topic categories have calibration issues.
The EvolutionLoop uses this data weekly to improve future prediction calibration.

---

## NOT_SCORABLE predictions

Predictions with `verdict = NOT_SCORED` are excluded from Brier calculations:
- The prediction was voided (event was ambiguous or cancelled)
- No probability was set (`our_pick_prob = null`)

These do NOT count as wrong predictions — they are simply excluded.
Current NOT_SCORABLE count: 4 predictions.

---

## Comparison with market consensus

For predictions with Polymarket data, we track:
```
market_consensus.probability = Polymarket market probability at prediction time
```

This allows comparison: "Was our probability better or worse than the prediction market?"

---

## Scoring caveats (current PROVISIONAL tier)

Because `initial_prob` was backfilled from `our_pick_prob` without blockchain proof:

1. We cannot rule out that some `our_pick_prob` values were edited after the original publish date
2. The reported Brier score of 0.4697 may not accurately reflect what was originally published
3. All scores display with "暫定計算値" (provisional) label until OTS proofs confirm

When OTS blockchain proofs are confirmed, predictions where the hash matches will be upgraded
to `MIGRATED_OFFICIAL` tier and the provisional label removed.

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial document. Formula verified against 53 RESOLVED predictions. |
