# Prediction Evolution Loop Reference

> How Brier Scores feed into the self-improving intelligence system.
> The "self-correction loop" for Nowpattern's prediction accuracy.
> Last updated: 2026-03-29

---

## Overview

The Evolution Loop is Nowpattern's self-learning engine. Every week, it:
1. Analyzes resolved predictions by Brier Score
2. Identifies which topics and dynamics the system predicts poorly
3. Generates improvement guidance
4. Writes those insights to `AGENT_WISDOM.md`
5. All future agents read the updated wisdom

This is the **Intelligence Flywheel** in action — predictions become training data for better predictions.

---

## System Components

| Component | Location | Schedule |
|-----------|----------|----------|
| Main script | `/opt/shared/scripts/evolution_loop.py` | Every Sunday 09:00 JST |
| Evolution log | `/opt/shared/logs/evolution_log.json` | Updated each run |
| Agent wisdom | `/opt/shared/AGENT_WISDOM.md` | Auto-appended each run |
| Category Brier | `/opt/shared/logs/category_brier.json` | Updated each run |
| Category script | `/opt/shared/scripts/category_brier_analysis.py` | Integrated into evolution_loop.py |

---

## The Evolution Cycle (Step by Step)

```
SUNDAY 09:00 JST — evolution_loop.py starts
  ↓
Step 1: Load prediction_db.json
  - Filter: verdict in (HIT, MISS) AND initial_prob is not None
  - Compute per-prediction Brier scores

Step 2: Category Brier Analysis
  - Group predictions by dynamics tags (力学タグ)
  - Compute mean Brier per category
  - Save to /opt/shared/logs/category_brier.json
  - Identify worst-performing categories (highest Brier = worst)

Step 3: Gemini API Analysis
  - Input: resolved predictions with Brier > threshold
  - Prompt: "Why did these predictions fail? What patterns explain the misses?"
  - Output: meta-analysis of failure modes

Step 4: Insight Generation
  - Extract actionable rules from the Gemini analysis
  - Format as AGENT_WISDOM.md self-learning log entries
  - Include: category, Brier score, failure pattern, suggested adjustment

Step 5: AGENT_WISDOM.md Update
  - Append new entries to "## 自己学習ログ" section
  - Each entry: date, category, Brier, pattern, recommendation

Step 6: Logging
  - Write to /opt/shared/logs/evolution_log.json
  - Include: run_ts, predictions_analyzed, categories_analyzed, insights_generated

Step 7: Notification
  - Send Telegram to Naoto: "今週の自己進化サマリー"
  - Show: worst category, best category, delta from last week
```

---

## Current State (2026-03-29)

| Metric | Value |
|--------|-------|
| Total resolved predictions | 52 (HIT=35, MISS=18) |
| Avg Brier (all resolved) | 0.1828 (FAIR level) |
| Evolution log entries | Available at `/opt/shared/logs/evolution_log.json` |
| Last run analysis | March 22 subset (29 predictions, Brier=0.4256) |
| Category Brier | Generated at `/opt/shared/logs/category_brier.json` |

**Note on Brier figures:**
- `0.1828` = mean Brier over ALL 52 resolved predictions (using `initial_prob` as backfilled value)
- `0.4256` = Brier score from the March 22 evolution_loop analysis subset (29 predictions selected for analysis — these tend to be harder/less accurate cases, causing higher Brier)
- These are **different measurement populations** and should not be confused

---

## Category Brier Analysis

### What It Measures

For each dynamics tag (力学タグ), compute:
```
mean_brier = mean((initial_prob/100 - outcome)² for all resolved in category)
```

### Current Category Results

Stored at `/opt/shared/logs/category_brier.json`. Example structure:
```json
{
  "generated_at": "2026-03-29T09:00:00Z",
  "total_resolved": 52,
  "categories": {
    "geopolitics": { "n": 12, "mean_brier": 0.18, "tier": "FAIR" },
    "crypto": { "n": 8, "mean_brier": 0.31, "tier": "WEAK" },
    "tech": { "n": 5, "mean_brier": 0.12, "tier": "GOOD" }
  }
}
```

### Brier Score Reference Tiers

| Brier Range | Tier | Meaning |
|-------------|------|---------|
| 0.00 – 0.05 | EXCELLENT | Near-perfect calibration |
| 0.05 – 0.15 | GOOD | Better than most forecasters |
| 0.15 – 0.25 | FAIR | Competitive with market consensus |
| 0.25 – 0.35 | WEAK | Systematic bias or poor calibration |
| 0.35 – 1.00 | POOR | Worse than random (50/50) for some predictions |

### Category Improvement Loop

When a category reaches WEAK or POOR tier:
1. Evolution loop flags it in AGENT_WISDOM.md
2. Next predictions in that category: NEO agents use the insight to recalibrate confidence
3. Over time: Brier score trends toward GOOD as calibration improves

---

## AGENT_WISDOM.md Integration

### Self-Learning Log Format

Each evolution run appends to the `## 自己学習ログ` section:

```markdown
### 2026-W14 Evolution Analysis (2026-04-05)
- Analyzed: 52 resolved predictions
- Worst category: crypto (Brier=0.31, n=8)
- Pattern: Crypto predictions skewed toward optimism (hit_rate 62%)
  → Recommendation: For crypto predictions, reduce our_pick_prob by 10-15 percentage points
- Best category: tech (Brier=0.12, n=5)
  → Pattern: Technology adoption timelines were well-calibrated
- Global Brier trend: 0.1828 → [next week value]
```

### What All Agents Read At Session Start

Every agent reads `/opt/shared/AGENT_WISDOM.md` at the start of each session. The self-learning log ensures that:
- NEO-ONE/TWO inherit category calibration adjustments automatically
- No human intervention needed for routine recalibration
- The system gets smarter every Sunday

---

## Polymarket Sync Integration

Since 2026-03-25 (Night Mode), the evolution loop also receives market consensus data:

```
/opt/shared/scripts/polymarket_sync.py — runs daily at 21:30 UTC
  ↓
Updates prediction_db.json: market_consensus.probability (where Polymarket has matching question)
  ↓
Evolution loop compares: our Brier vs implied Brier from market consensus
  ↓
If market was closer: insight → "For [category], market was better calibrated at [probability]"
  ↓
AGENT_WISDOM.md: "Defer to market consensus when our confidence is within ±15%"
```

---

## Evolution Loop Monitoring

### Check Last Run

```bash
ssh root@163.44.124.123 "python3 -c \"
import json
log = json.load(open('/opt/shared/logs/evolution_log.json'))
entries = log if isinstance(log, list) else [log]
last = entries[-1] if entries else {}
print('Last run:', last.get('run_ts', 'NONE'))
print('Predictions analyzed:', last.get('predictions_analyzed', 0))
print('Insights generated:', last.get('insights_generated', 0))
\""
```

### Check Category Brier

```bash
ssh root@163.44.124.123 "python3 -c \"
import json
cat = json.load(open('/opt/shared/logs/category_brier.json'))
cats = cat.get('categories', {})
sorted_cats = sorted(cats.items(), key=lambda x: x[1].get('mean_brier', 0), reverse=True)
print('Worst categories (highest Brier):')
for name, data in sorted_cats[:5]:
    print(f'  {name}: {data[\"mean_brier\"]:.4f} (n={data[\"n\"]})')
\""
```

### Verify Cron

```bash
ssh root@163.44.124.123 "crontab -l | grep evolution"
# Expected: 0 0 * * 0 python3 /opt/shared/scripts/evolution_loop.py >> /opt/shared/logs/evolution.log 2>&1
```

---

## Evolution Loop — AI Permissions

Per `NORTH_STAR.md` (The Eternal Directives, Principle 3: Autonomous Evolution):

**Permitted (no approval needed):**
- ✅ Appending to `AGENT_WISDOM.md` `## 自己学習ログ` section
- ✅ Writing to `evolution_log.json`
- ✅ Writing to `category_brier.json`
- ✅ Updating `prediction_db.json` Brier scores (auto_verifier only)
- ✅ Sending Telegram notifications

**Prohibited:**
- ❌ Modifying `NORTH_STAR.md` or `OPERATING_PRINCIPLES.md`
- ❌ Changing existing prediction probabilities (`initial_prob` or `our_pick_prob`)
- ❌ Deleting resolved prediction records
- ❌ Changing the Brier Score formula

---

## Future Enhancements (Backlog)

| Enhancement | Expected Benefit | Priority |
|-------------|-----------------|---------|
| Per-forecaster Brier (when readers participate) | Compare human vs AI accuracy | High (TIER 1) |
| DSPy prompt auto-optimization | Improve NEO prediction prompts automatically | Medium |
| Multi-resolution window analysis | Track calibration at 30/60/90 day windows | Medium |
| Polymarket calibration diff | Weekly comparison of our Brier vs market | Low (already started) |

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial document. Evolution loop described as integrated system. Category Brier + Polymarket sync noted as Phase 1 Night Mode additions. |
