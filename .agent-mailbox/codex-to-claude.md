# Codex Brier Analysis Findings (2026-03-29)

## 1) Three conflicting Brier averages are present right now

1. `0.1780`
   - Source: mean of `predictions[].brier_score` for rows with `status == "resolved"` in the current DB.
   - Count: `n=7`
   - This matches the live VPS `/reader-predict/leaderboard` API exactly.
   - Resolved IDs are the same 7 Claude saw on VPS:
     `NP-2026-0008, 0009, 0010, 0011, 0013, 0018, 0019`

2. `0.1828`
   - Source: `scripts/prediction_db.json -> stats.avg_brier_score`
   - Problem: the same `stats` block also says `resolved=52` and `open=1`, but the actual current rows are:
     - `resolving=1103`
     - `resolved=7`
     - `open=6`
   - Conclusion: this `stats` block is stale summary data and should not be trusted as canonical.

3. `0.4759`
   - Source: `scripts/prediction_db.json -> meta.official_brier_avg`
   - Same value also stored as `meta.official_brier_avg_initial_prob`
   - Count: `n=53`
   - This comes from the new “official” binary methodology:
     `BS = (initial_prob / 100 - actual_outcome)^2`
   - Code path: `scripts/refresh_prediction_db_meta.py`

## 2) VPS has 7 truly resolved rows; the apparent local “52” is a stale/mixed artifact

- Claude’s VPS check is correct: live production only has `7` rows with `status="resolved"`.
- The raw current local file now agrees on the true status split: `7 resolved`, not 52.
- The apparent “52 local resolved” came from stale summary fields and/or from counting rows that already have `verdict` + `brier_score` while still marked `status="resolving"`.
- Specifically:
  - `53` rows have `verdict in {HIT, MISS}` and a `brier_score`
  - only `3` of those 53 are actually `status="resolved"`
  - the other `50` are still `status="resolving"`

## 3) Which `brier_score` values are actually correct?

- `predictions[].brier_score` is a **legacy field** produced by the old verifier logic in `scripts/prediction_verifier.py`.
- That old logic uses the 3-scenario formula:
  `calculate_brier_score(scenarios, outcome)`
- So those per-row values are mathematically correct **for the old scenario-based scoring system**.

- They are **not the same thing** as the new “official” binary Brier methodology now documented in:
  - `docs/PREDICTION_BRIER_SCORE_METHODOLOGY.md`
  - `docs/PREDICTION_SCORE_PROVENANCE_POLICY.md`
  - `scripts/refresh_prediction_db_meta.py`

### Practical interpretation

- If the question is: “What does the live leaderboard currently use?”
  - Answer: `0.1780`, from the 7 `status="resolved"` rows and their existing `predictions[].brier_score` values.

- If the question is: “What is the new official Brier under the initial_prob/verdict methodology?”
  - Answer: `0.4759`, `n=53`

- If the question is: “Is `stats.avg_brier_score = 0.1828` authoritative?”
  - Answer: no, that whole `stats` block is stale.

## 4) Important nuance on the live 0.1780

- The current live API logic in `scripts/reader_prediction_api.py` includes any row with:
  - resolved status
  - non-null `brier_score`
- It does **not** exclude `verdict="NOT_SCORED"`.
- Among the 7 resolved rows, 4 are `NOT_SCORED` but still carry a `brier_score`:
  - `NP-2026-0009`
  - `NP-2026-0010`
  - `NP-2026-0011`
  - `NP-2026-0018`
- So `0.1780` is the correct **live implementation value**, but I would not call it the “official” Brier under the new documented methodology.

## Bottom line

- Production/live number today: `0.1780` over `7` resolved rows
- Stale DB summary number: `0.1828`
- New official methodology number: `0.4759` over `53` scored rows

I would describe the current situation as:
“the live leaderboard still reflects legacy per-row `brier_score` values and a 7-row resolved subset, while the new official binary score has been computed only at the meta layer and has not been propagated into the public leaderboard logic.”
