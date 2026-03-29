# Prediction Integrity Audit Trail

> How Nowpattern tracks and proves the integrity of predictions over time.
> Last updated: 2026-03-29

---

## What "Integrity" Means for Nowpattern

A prediction platform's credibility depends on ONE thing:
**Readers must be able to verify that the published probability was NOT changed after the outcome was known.**

Without tamper-evident records, a bad-faith actor could:
- Publish prediction at 50%
- Wait for outcome
- Retroactively claim they predicted 90%
- Publish Brier Score of 0.01 instead of the honest 0.25

Nowpattern's integrity system makes this technically impossible to do silently.

---

## The Three-Layer Audit System

### Layer 1: prediction_ledger.jsonl

An append-only JSONL log of events affecting predictions.

```jsonl
{"ts": "2026-03-29T01:13:48Z", "event": "REGISTERED", "prediction_id": "NP-2026-0001", "hash": "abc123...", "status": "OPEN", "actor": "phase6_backfill"}
{"ts": "2026-03-29T12:00:00Z", "event": "RESOLVED", "prediction_id": "NP-2026-0001", "verdict": "HIT", "actor": "auto_verifier"}
```

**Current limitation**: All REGISTERED events have `ts = 2026-03-29T01:13:48Z` — retroactively created during Phase 6 backfill. The ledger does NOT reflect original prediction publish dates.

### Layer 2: prediction_manifest.json

A SHA-256 manifest of each prediction at the time it was first hashed.

```json
{
  "NP-2026-0001": {
    "hash": "sha256:abc123...",
    "recorded_at": "2026-03-29T01:13:48Z",
    "status": "AWAITING_EVIDENCE",
    "verdict": "PENDING"
  }
}
```

**Current limitation**: Hashes do NOT match current prediction JSON. Records were modified after hashing. The manifest proves an older version existed, not the current content.

### Layer 3: OpenTimestamps (OTS) Proofs

Bitcoin blockchain anchoring of prediction hashes.

- 1115 `.ots` files exist in `/opt/shared/scripts/ots/`
- ALL currently `timestamp_pending = True` (awaiting blockchain confirmation)
- Once confirmed: proves the hashed content existed at a specific Bitcoin block time

---

## Audit Trail Coverage Matrix

| Evidence type | Exists | Proves original probability |
|---------------|--------|---------------------------|
| prediction_ledger.jsonl REGISTERED events | ✅ Yes | ❌ No (retroactive, no prob field) |
| prediction_manifest.json SHA-256 hashes | ✅ Yes | ❌ No (hash of old version, no prob field) |
| OTS .ots files | ✅ Yes | ❌ No (pending + hash of old version) |
| `initial_prob` field | ✅ Yes (Phase 3) | ⚠️ Partial (backfilled, no independent proof) |

**Conclusion**: We have the structure for a complete audit trail, but current records are retroactive.
New predictions created from 2026-03-29 onwards will have proper audit trails.

---

## What Readers Can Verify Today

Despite the retroactive nature of current records, readers can verify:

1. **Prediction existence**: OTS files prove predictions existed (once confirmed)
2. **Brier formula**: The formula `(initial_prob/100 - outcome)²` is documented and public
3. **Resolution events**: RESOLVED ledger entries are timestamped in real time
4. **All predictions visible**: We publish HIT and MISS equally — no cherry-picking

---

## What Readers CANNOT Verify Today (and We Disclose This)

1. The exact probability published at original prediction creation date
2. That `our_pick_prob` wasn't adjusted after publication
3. That predictions weren't added retroactively to boost accuracy

This is disclosed via:
- `official_score_tier = PROVISIONAL` on all existing predictions
- "暫定計算値" label on all score displays
- This audit trail document being publicly accessible

---

## Integrity Improvements for Future Predictions

Starting from 2026-03-29, new predictions will follow this process:

```
1. Author writes prediction
2. Set initial_prob = our_pick_prob BEFORE any edits
3. Compute SHA-256(prediction JSON including initial_prob)
4. Write to ledger with REAL timestamp
5. Create OTS proof immediately
6. Prediction is now published — no changes to initial_prob or our_pick_prob
```

This achieves `initial_prob_source = FROM_IMMUTABLE_LEDGER` and path to `VERIFIED_OFFICIAL`.

---

## Audit Verification Commands

```bash
# Check ledger event count
ssh root@163.44.124.123 "wc -l /opt/shared/scripts/prediction_ledger.jsonl"

# Check manifest entry count
ssh root@163.44.124.123 "python3 -c \"import json; m=json.load(open('/opt/shared/scripts/prediction_manifest.json')); print(m.get('total'))\""

# Check OTS pending count
ssh root@163.44.124.123 "python3 -c \"
import json
db = json.load(open('/opt/shared/scripts/prediction_db.json'))
preds = db['predictions']
pending = sum(1 for p in preds if p.get('timestamp_pending', True))
print(f'OTS pending: {pending}/{len(preds)}')
print(f'official_brier_avg_initial_prob: {db[\"meta\"].get(\"official_brier_avg_initial_prob\")}')
print(f'tier: {db[\"meta\"].get(\"official_brier_avg_initial_prob_tier\")}')
\""
```

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial document. Audit trail coverage matrix created. Limitations disclosed. |
