# Prediction OTS (OpenTimestamps) System

> How Nowpattern timestamps predictions on the Bitcoin blockchain for tamper-evidence.
> Last updated: 2026-03-29

---

## Purpose

OTS timestamping creates a cryptographic proof that a file existed at a specific point in time,
anchored to the Bitcoin blockchain. For Nowpattern predictions:

- **What it proves**: That the prediction file existed at timestamp T
- **What it does NOT prove** (yet): The exact content of `our_pick_prob` at that time
  (because the SHA-256 manifest hash and prediction JSON currently don't match)
- **Why it matters**: A confirmed OTS proof is the foundation for upgrading predictions from
  PROVISIONAL to MIGRATED_OFFICIAL tier

---

## How It Works

```
1. prediction_timestamper.py runs hourly on VPS
2. For each prediction without confirmed OTS:
   a. Compute SHA-256 of prediction JSON
   b. Create .ots file (OpenTimestamps calendar proof)
   c. Set timestamp_pending = true
3. OTS library periodically checks Bitcoin blockchain
4. When Bitcoin block confirms the timestamp:
   a. timestamp_pending = false
   b. Update official_score_tier accordingly
```

---

## Current State (2026-03-29)

| Metric | Value |
|--------|-------|
| Total OTS files | 1115 |
| timestamp_pending = true | 1115 (ALL) |
| timestamp_pending = false | 0 |
| Blockchain confirmations received | 0 |

**All 1115 predictions have pending OTS proofs.**

This means:
- OTS files EXIST (created during Phase 6 backfill, 2026-03-29)
- But NONE have received Bitcoin blockchain confirmation yet
- Expected confirmation: within 1-2 hours per batch (Bitcoin confirms a new block ~every 10 min)

---

## Why SHA-256 Mismatch Matters

The OTS system works like this:
1. Take SHA-256 of prediction JSON → hash value H
2. Embed H in OTS proof
3. Bitcoin confirms H existed at time T

**The problem**: The prediction JSON was modified AFTER the hash H was computed.
- If H = SHA-256(prediction at time T1)
- And current prediction JSON = different content (modified at T2 > T1)
- Then confirming H just proves the *older version* existed at T1, not the current content

**Impact**: Even when OTS confirms, the proof is for an older version of the prediction.
We can use it to prove existence, but NOT to prove `our_pick_prob` at original publish time.

This is why all scores remain **PROVISIONAL** even after OTS confirmation.
Best achievable tier: **MIGRATED_OFFICIAL** (OTS confirmed, but not for original content).

---

## Upgrade Path

### PROVISIONAL → MIGRATED_OFFICIAL
Happens when ALL of:
1. OTS confirmation received (`timestamp_pending = false`)
2. `official_score_tier` updated to `MIGRATED_OFFICIAL` in prediction_db.json
3. Public display updated to show "移行確定スコア" label

**Automated in**: `prediction_auto_verifier.py` (checks OTS status on each run)

### MIGRATED_OFFICIAL → VERIFIED_OFFICIAL
Requires:
1. Future predictions (not current backfill)
2. SHA-256 hash computed BEFORE prediction is modified
3. OTS confirmation of that hash
4. `initial_prob` recorded at same time as hash

**Process for future predictions**:
```python
# At prediction publish time:
p["initial_prob"] = p["our_pick_prob"]  # Lock before any edits
p["initial_prob_source"] = "FROM_IMMUTABLE_LEDGER"
hash_val = sha256(json.dumps(p))  # Hash INCLUDES initial_prob
create_ots_proof(hash_val)  # OTS immediately
# No modifications to p["our_pick_prob"] or p["initial_prob"] after this point
```

---

## Implementation

| Component | Location |
|-----------|----------|
| OTS timestamping script | `/opt/shared/scripts/prediction_timestamper.py` |
| OTS files directory | `/opt/shared/scripts/ots/` (1115 files) |
| Cron schedule | Hourly on VPS |
| OTS confirmation check | `prediction_auto_verifier.py` |

---

## Monitoring

To check OTS status:
```bash
ssh root@163.44.124.123 "python3 -c \"
import json
db = json.load(open('/opt/shared/scripts/prediction_db.json'))
preds = db['predictions']
pending = [p for p in preds if p.get('timestamp_pending', True)]
confirmed = [p for p in preds if not p.get('timestamp_pending', True)]
print('Pending OTS:', len(pending))
print('Confirmed OTS:', len(confirmed))
\""
```

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial document. All 1115 OTS proofs currently pending. |
