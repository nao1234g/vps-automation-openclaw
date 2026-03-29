# Prediction System North Star

> The vision, goals, and design principles for Nowpattern's prediction platform.
> This document guides ALL technical decisions for the prediction system.
> Last updated: 2026-03-29

---

## One-Sentence Mission

**Nowpattern is the world's first Japanese×English bilingual prediction platform with
transparent, automated Brier Score tracking — making it impossible to fake a forecast record.**

---

## The Problem We Solve

Other news sites say "〜だと思う" (I think it will be...) and never check if they were right.

Nowpattern says "70% probability this happens by [date]" — and then automatically checks.

| Traditional media | Nowpattern |
|-------------------|------------|
| Opinion without accountability | Probability + deadline + automatic verification |
| No track record | Brier Score accumulates over years |
| Reader is passive | Reader participates, votes, challenges |
| Copy in 1 day | 3-year track record takes 3 years to replicate |

---

## What Makes a Prediction "Real"

For a prediction to count toward our track record, it must have ALL of:

1. **A specific, verifiable question** — "Will X happen by Y date?"
2. **A probability** (0–100%) — not "probably yes" but "73%"
3. **An explicit deadline** — not "eventually" but a specific date
4. **Pre-registered** — recorded BEFORE the outcome is known
5. **Automatically verified** — not self-reported

This is the standard of Superforecasters (Philip Tetlock, Good Judgment Project).
Nowpattern implements this standard for Japanese-language news analysis.

---

## The Intelligence Flywheel

```
Write prediction (article + probability + deadline)
  ↓
Publish to Ghost + prediction_db.json
  ↓
Automatic verification (prediction_auto_verifier.py + Grok + Claude)
  ↓
Brier Score computed and published
  ↓
EvolutionLoop analyzes: "why did we miss? what patterns predict hits?"
  ↓
Next prediction is better calibrated
  ↓ (repeat forever)
Track record grows → Reader trust grows → Platform moat grows
```

After 3 years of this loop: **a competitor cannot replicate the track record by starting today**.

---

## Platform Design Principles

### 1. Radical Transparency
- Publish ALL predictions — hits AND misses — with equal prominence
- Show exact probabilities, not vague language
- Disclose exactly what evidence tier our scores have (PROVISIONAL vs VERIFIED_OFFICIAL)
- Make audit trail documents publicly accessible

### 2. Tamper Resistance
- `initial_prob` is write-once (never change after first set)
- `prediction_ledger.jsonl` is append-only
- OTS blockchain timestamps for independent proof
- Score formula (`(initial_prob/100 - outcome)²`) is documented and fixed

### 3. Calibration Over Confidence
- A good forecast is well-calibrated, not necessarily high-confidence
- A 30% prediction that resolves as MISS is CORRECT if you predicted 30%
- Brier Score rewards calibration, not overconfidence
- Goal: avg Brier Score < 0.20 (from current PROVISIONAL 0.4697)

### 4. Reader Participation
- Readers can vote on prediction outcomes
- Reader aggregate probability vs Nowpattern probability comparison
- Eventually: reader Brier Scores and leaderboard
- "誰が世界中で一番予測が当たるか" — who's the best forecaster in the world?

### 5. Bilingual Parity
- ALL predictions appear in both Japanese and English
- Same prediction_id across both languages
- Brier Scores are computed once, displayed in both languages
- Target: become the English-language reference for Japan-focused predictions

---

## Success Metrics (in order of priority)

| Metric | Today | 3-month target | 1-year target |
|--------|-------|----------------|---------------|
| Active predictions | 35 | 100 | 300 |
| Avg Brier Score | 0.4697 PROV | 0.30 PROV | 0.20 PROV |
| RESOLVED predictions | 52 | 150 | 400 |
| OTS confirmations | 0 | 1115 | all new preds |
| Reader votes | 0 | 100/month | 1000/month |
| Prediction accuracy tier | PROVISIONAL | PROVISIONAL | MIGRATED_OFFICIAL |

---

## What We Will NOT Do

- ❌ Claim VERIFIED_OFFICIAL scores when evidence is PROVISIONAL
- ❌ Delete or hide MISS predictions
- ❌ Retroactively change `initial_prob` after outcome is known
- ❌ Use vague language ("probably", "likely") without a numeric probability
- ❌ Create predictions after the fact (post-diction)

---

## Relationship to Other Systems

| System | Relationship |
|--------|-------------|
| Ghost CMS | Hosts articles that contain predictions. prediction_id links article → prediction |
| NEO-ONE/TWO | Write articles with ORACLE STATEMENT boxes linking to prediction_db.json |
| prediction_page_builder.py | Builds /predictions/ and /en/predictions/ pages from prediction_db.json |
| prediction_auto_verifier.py | Checks outcomes via Grok + Claude judgment |
| EvolutionLoop | Weekly analysis of resolved predictions to improve future calibration |
| reader_prediction_api.py | Accepts reader votes on predictions |
| OTS timestamper | Creates blockchain proofs for tamper-evidence |

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial document. Captures platform vision after Phase 0-3 migration. |
