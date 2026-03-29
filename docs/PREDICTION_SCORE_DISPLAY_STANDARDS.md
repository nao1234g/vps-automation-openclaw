# Prediction Score Display Standards

> Defines exactly how scores MUST be displayed to readers on all prediction pages.
> These standards are enforced by Gate F (provisional label enforcement) in prediction_page_builder.py.
> Last updated: 2026-03-29

---

## Why This Document Exists

A score without context is misleading. Nowpattern's Brier Score is currently:
- Computed from `initial_prob = our_pick_prob` (backfilled, not original publish-time probability)
- All 1115 existing predictions: `official_score_tier = PROVISIONAL`
- No predictions have blockchain-confirmed timestamps yet (all OTS `timestamp_pending = True`)

Displaying these scores without disclosure labels would be deceptive to readers.
This document defines the mandatory display rules that prevent that.

---

## Score Tier Labels (Mandatory)

### PROVISIONAL (1111 predictions — ALL currently displayed scores)

**Japanese display label:** `暫定計算値`
**English display label:** `Provisional Score`

**Required disclaimer on every score display:**
```html
<!-- JA version -->
<span class="score-tier-label provisional">暫定計算値</span>
<small class="score-disclaimer">
  ※ この確率は事後的に登録されたため、独立検証はできません。
  OTSブロックチェーン確認待ちです。
</small>

<!-- EN version -->
<span class="score-tier-label provisional">Provisional Score</span>
<small class="score-disclaimer">
  This probability was backfilled — independent verification is not possible.
  Awaiting OTS blockchain confirmation.
</small>
```

**Prohibited language for PROVISIONAL scores:**
- ❌ 公式確定スコア / Official certified score
- ❌ 検証済み / Verified
- ❌ ブロックチェーン確認済み / Blockchain confirmed
- ❌ Any wording implying the probability was locked before outcome was known

---

### MIGRATED_OFFICIAL (future — currently 0 predictions)

**Japanese display label:** `移行確定スコア`
**English display label:** `Migrated Official Score`

**Context:** OTS timestamp confirmed on Bitcoin blockchain. Proves existence at T, but original `our_pick_prob` may have changed since.

**Required note:**
```
移行確定: OTSブロックチェーン確認済み。元の確率が発表時点と一致するかは検証不可。
```

---

### VERIFIED_OFFICIAL (future — requires new predictions from 2026-03-29)

**Japanese display label:** `公式確定スコア`
**English display label:** `Official Verified Score`

**Context:** SHA-256 hash computed BEFORE publication, OTS confirmed, `initial_prob` matches hashed content.

**Allowed to display:**
```
✅ 公式確定: 予測確率は公開時点でハッシュ化・タイムスタンプされています。
```

---

### NOT_SCORABLE (4 predictions)

**Japanese display label:** `採点対象外`
**English display label:** `Not Scored`

**Context:** Verdict = `NOT_SCORED`. Do not display Brier Score for these.

---

## Aggregate Score Display (Scoreboard)

The main scoreboard on `/predictions/` and `/en/predictions/` shows aggregate statistics.

### Required format (current state)

```
┌─────────────────────────────────────────────────────┐
│  スコアボード（暫定計算値）                           │
│                                                     │
│  [1115件]  [的中35件]  [外れ18件]  [正確率72.9%]    │
│  平均Brier: 0.47 ※暫定                              │
│                                                     │
│  ⚠️ 現在のスコアは「暫定計算値」です。               │
│  詳細: /integrity-audit/                            │
└─────────────────────────────────────────────────────┘
```

**Mandatory elements on scoreboard:**
1. `（暫定計算値）` in the scoreboard section title
2. `※暫定` suffix on average Brier Score display
3. Link to `/integrity-audit/` page
4. The count `1115件` is total predictions, `的中` is HIT, `外れ` is MISS

### EN version format

```
Scoreboard (Provisional)
[1115 total]  [35 hits]  [18 misses]  [72.9% accuracy]
Avg Brier: 0.47 ※provisional

⚠️ All scores are provisional. Details: /en/integrity-audit/
```

---

## Per-Card Score Display

Each prediction card that shows a Brier Score must display:

### For RESOLVED predictions (HIT or MISS)

```html
<!-- Example: HIT prediction -->
<div class="prediction-card resolved hit">
  <div class="verdict-badge hit">✅ 的中 / HIT</div>
  <div class="brier-score">
    Brier Score: <strong>0.04</strong>
    <span class="tier-label provisional">[暫定]</span>
  </div>
  <div class="prob-display">
    予測確率: <strong>80%</strong>
    <span class="prob-source">(initial_prob, FROM_CURRENT_VALUE_BACKFILL)</span>
  </div>
</div>
```

**Rules:**
- Every `brier_score` display → must have `[暫定]` / `[provisional]` tag
- Every `initial_prob` display → must note it is backfilled (not show-by-default, but must be in page source)
- NOT_SCORABLE predictions → show verdict but NO Brier Score field

---

## Category Brier Display

When showing per-category Brier Scores (e.g., geopolitics, crypto):

```
カテゴリ別スコア（暫定）
geopolitics: 0.18 [暫定, n=12]
crypto: 0.31 [暫定, n=8]
...
```

All category scores are PROVISIONAL. Show `n=X` (sample size) next to each.

---

## What MUST NOT Be Changed Without WS5 Review

These CSS classes are protected by the design system:
- `.score-tier-label` — tier label display
- `.score-disclaimer` — disclaimer text
- `.provisional` — provisional state styling
- `.verified-official` — verified state styling (future)

Color conventions:
- PROVISIONAL: `#888` (gray — neutral, not official)
- MIGRATED_OFFICIAL: `#fbbf24` (amber — cautiously positive)
- VERIFIED_OFFICIAL: `#16a34a` (green — fully trusted)
- NOT_SCORABLE: `#dc2626` (red/gray — excluded)

---

## Gate F Implementation Requirements

Gate F (provisional label enforcement) in `prediction_page_builder.py` must:

```python
def check_gate_f_provisional_labels(html_content):
    """
    Verify that no PROVISIONAL score is displayed without tier disclaimer.
    Returns True if gate passes, raises AssertionError if not.
    """
    # Check: brier_score appears in output → must have provisional marker nearby
    brier_pattern = re.findall(r'Brier Score[^<]{0,50}(?:<[^>]+>)*\s*[\d.]+', html_content)
    for match in brier_pattern:
        if '暫定' not in match and 'provisional' not in match.lower() and 'tier-label' not in match:
            raise AssertionError(f"Gate F FAIL: Brier Score displayed without tier label: {match[:100]}")

    # Check: score section title does not contain "公式確定" without tier check
    if '公式確定スコア' in html_content:
        assert 'official_score_tier.*VERIFIED_OFFICIAL' in html_content or \
               '移行確定' in html_content, "Gate F FAIL: official language without verified tier"

    return True
```

**Status**: Gate F is currently PENDING implementation. Until implemented, manually verify that all score displays include `（暫定計算値）` labels before deploying page updates.

---

## Upgrade Path: When Labels Change

When a prediction's `official_score_tier` changes from PROVISIONAL → MIGRATED_OFFICIAL:
1. `prediction_page_builder.py` detects tier = MIGRATED_OFFICIAL
2. Display label changes from `暫定計算値` → `移行確定スコア`
3. Disclaimer text changes to mention OTS blockchain confirmation date
4. The `[暫定]` tag is replaced with `[移行確定]` on the card

This is **automatic** — prediction_page_builder.py reads `official_score_tier` per prediction.

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial document. Standards established after Phase 3 provenance backfill. All 1115 predictions are PROVISIONAL. |
