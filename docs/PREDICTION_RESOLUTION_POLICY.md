# Prediction Resolution Policy

> Defines how Nowpattern predictions move from OPEN to RESOLVED (or EXPIRED_UNRESOLVED).
> Last updated: 2026-03-29

---

## Resolution Lifecycle

```
OPEN
  ↓  event_cutoff_at passes
AWAITING_EVIDENCE
  ↓  outcome detected (auto_verifier or manual)
RESOLVING
  ↓  verdict confirmed
RESOLVED  (verdict = HIT | MISS | NOT_SCORED)

OR:

AWAITING_EVIDENCE
  ↓  evidence_grace_until passes with no outcome
EXPIRED_UNRESOLVED  (verdict = PENDING)
```

---

## Unresolved Policy

**Current policy for all predictions**: `AUTO_NO_AT_DEADLINE`

This means:
- If the predicted event does not occur by `event_cutoff_at`
- AND no outcome evidence is found during the evidence grace period (`evidence_grace_until`)
- THEN the prediction is counted as **MISS** (our pick did not materialize)

This policy applies to 1115/1115 predictions (set as default).

### Evidence Grace Period

`evidence_grace_days` = number of days between `event_cutoff_at` and `evidence_grace_until`.

The grace period exists because:
1. News reporting may lag the actual event by hours/days
2. Official data (GDP, election results, etc.) may have publication delays
3. The auto_verifier needs time to run and confirm the outcome

Typical grace period: 7–30 days depending on prediction category.
After `evidence_grace_until`, the auto_verifier makes a final determination.

---

## Automated Resolution (prediction_auto_verifier.py)

The auto_verifier runs on VPS via Grok API search + Claude Opus judgment.

**Process**:
1. Check if `event_cutoff_at` has passed
2. Search for outcome evidence via Grok (X search) + web search
3. If evidence found: set verdict = HIT or MISS, move to RESOLVED
4. If no evidence after `evidence_grace_until`: set verdict according to `unresolved_policy`

**Scoring after resolution**:
```python
brier_score = (initial_prob / 100 - actual_outcome) ** 2
```

---

## Manual Resolution Override

For predictions that require human judgment (ambiguous outcomes):

1. Set `status = RESOLVING`
2. Add `resolution_notes` with explanation
3. Add `resolution_evidence_url` with source
4. Set `verdict = HIT | MISS | NOT_SCORED`
5. Status auto-updates to RESOLVED

---

## NOT_SCORED conditions

A verdict of `NOT_SCORED` is used when:
- The predicted event was cancelled or became moot
- The resolution criteria cannot be applied (ambiguity)
- The prediction was a test/calibration entry
- The event was outside Nowpattern's control to verify

NOT_SCORED predictions are excluded from Brier Score calculations.
They appear in the prediction tracker with "対象外" label.

---

## Resolution Criteria Fields (Phase 2 — content pending)

Each prediction should eventually have:

```json
{
  "resolution_criteria": {
    "yes_criteria_ja": "予測が的中する条件（日本語）",
    "yes_criteria_en": "Conditions for HIT verdict (English)",
    "no_criteria_ja": "予測が外れる条件（日本語）",
    "no_criteria_en": "Conditions for MISS verdict (English)",
    "void_criteria": "Conditions for NOT_SCORED verdict",
    "editorial_note": "NEEDS_FILL: criteria not yet authored"
  },
  "authoritative_sources": [
    "https://example.com/official-source"
  ]
}
```

**Current status**: Schema structure added to all 1115 predictions (2026-03-29).
Content not yet authored. This is a multi-sprint editorial effort.

Priority order for content fill-in:
1. RESOLVED predictions (52) — needed for audit trail
2. OPEN predictions (35) — needed for active reader transparency
3. AWAITING_EVIDENCE predictions (1023) — lower priority, will auto-resolve

---

## Evidence Sources by Category

Authoritative sources by prediction category:

| Category | Primary sources |
|----------|----------------|
| geopolitics | AP, Reuters, BBC, Associated Press |
| economics | IMF, World Bank, Federal Reserve, BOJ |
| technology | Company announcements, SEC filings |
| markets | Bloomberg, Reuters, official exchange data |
| politics | Official election results, government announcements |

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial document. Covers AUTO_NO_AT_DEADLINE policy for all 1115 predictions. |
