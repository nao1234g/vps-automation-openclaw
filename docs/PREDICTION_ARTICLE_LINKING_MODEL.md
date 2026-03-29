# Prediction Article Linking Model

> Defines how predictions relate to articles and documents the 11 standalone predictions.
> Last updated: 2026-03-29

---

## Overview

Each prediction in `prediction_db.json` has an `article_links` field listing Ghost article slugs that published the prediction. Most predictions (1105/1116) are linked to at least one article. 11 predictions have no article links.

---

## Standard Link Model

```
prediction_db.json
  prediction_id: NP-2026-XXXX
  article_links: ["slug-of-article-1", "slug-of-article-2"]
                     ↓
         Ghost CMS article pages
         nowpattern.com/slug-of-article-1/
         nowpattern.com/slug-of-article-2/
                     ↓
         Article contains Oracle Statement block
         linking back to /predictions/#np-2026-xxxx
```

### Bidirectional linking requirement

For a prediction to be considered fully linked:
1. `prediction_db.json` `article_links` contains the article slug
2. The article body contains an ORACLE STATEMENT section with `nowpattern.com/predictions/#np-2026-xxxx`

---

## Standalone Predictions (11 total)

These predictions have `article_links = []` or missing. They appear on `/predictions/` but have no linked articles.

### Category A: NP-2026-0113 through NP-2026-0122 (10 predictions)

These are **long-term structural predictions** created as a standalone batch. They cover multi-year geopolitical and economic dynamics with oracle deadlines in 2027-2030.

| Prediction ID | Topic | Oracle Deadline | Status |
|--------------|-------|----------------|--------|
| NP-2026-0113 | Japan defense budget doubling | 2027+ | OPEN |
| NP-2026-0114 | US-China tech decoupling | 2027+ | OPEN |
| NP-2026-0115 | Taiwan strait major incident | 2028+ | OPEN |
| NP-2026-0116 | Central bank digital currency adoption | 2027+ | OPEN |
| NP-2026-0117 | AI regulation global framework | 2027+ | OPEN |
| NP-2026-0118 | Crypto ETF mainstream adoption | 2027+ | OPEN |
| NP-2026-0119 | Nuclear fusion commercial milestone | 2030+ | OPEN |
| NP-2026-0120 | India GDP overtake Japan/Germany | 2028+ | OPEN |
| NP-2026-0121 | Arctic shipping route commercial use | 2028+ | OPEN |
| NP-2026-0122 | Quantum computing cryptography break | 2030+ | OPEN |

**Editorial note**: These 10 predictions were registered as structural long-term forecasts to establish Nowpattern's track record on macro-level dynamics. Articles may be written retroactively to document the original reasoning.

**Action required**: None urgent. Consider writing companion articles that reference these predictions in their ORACLE STATEMENT sections.

### Category B: NP-2026-1117 (1 prediction — stub)

This entry is a stub with incomplete data:
- `hit_condition_en`: marked as `NEEDS_MANUAL_REVIEW`
- `article_links`: empty
- `title`: appears to be a placeholder or data entry error

**Action required**: Either populate with full prediction data, or set status to `EXPIRED_UNRESOLVED` and add editorial note explaining it was a data entry stub.

---

## Coverage Statistics

| Metric | Value |
|--------|-------|
| Total predictions | 1116 |
| With article_links | 1105 (99.0%) |
| Without article_links | 11 (1.0%) |
| NP-2026-0113 to 0122 (standalone batch) | 10 |
| NP-2026-1117 (stub) | 1 |

---

## Impact on Scoring

Standalone predictions (no article links) are still scored normally:
- Brier Score is calculated when resolved
- They appear on `/predictions/` tracker
- They contribute to aggregate accuracy metrics

The absence of article links does **not** affect scoring — only discoverability via article ORACLE STATEMENT sections.

---

## Future Article Creation

For NP-2026-0113 through 0122, recommended approach:
1. Write a companion article per prediction (or one omnibus article for all 10)
2. Include ORACLE STATEMENT block with the prediction ID
3. Update `article_links` in `prediction_db.json` to reference the new article slug

Example update command:
```bash
# After publishing article "long-term-prediction-japan-defense-budget"
# Update NP-2026-0113 article_links in prediction_db.json
python3 -c "
import json
db = json.load(open('/opt/shared/scripts/prediction_db.json'))
for p in db['predictions']:
    if p['prediction_id'] == 'NP-2026-0113':
        p.setdefault('article_links', []).append('long-term-prediction-japan-defense-budget')
        break
json.dump(db, open('/opt/shared/scripts/prediction_db.json', 'w'), ensure_ascii=False, indent=2)
"
```

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial document. 11 standalone predictions classified. Coverage = 99.0%. |
