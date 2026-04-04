# Claude Code Sidecar — Task Result v4
> Generated: 2026-04-04 | Agent: claude-opus-4-6 | Mission Contract: v3 | Lexicon: v4
> Version: v4 (coverage / in-play audit)
> Parent: task_result_v3 (stop-proof contract + drift + codex action packet)

---

## Scope & Completion

| Metric | Value |
|--------|-------|
| scope_completion_pct | 100% |
| overall_completion_estimate_pct | 18% (estimate) |
| reached_100_pct_for_this_scope | true |

### Bounded Tasks (this session)

| # | Task | Status |
|---|------|--------|
| A | Coverage gap inventory (JA/EN exact numbers) | DONE |
| B | In-play candidate inventory (20 predictions) | DONE |
| C | Tracker currentness recommendations (5 items) | DONE |
| D | Stop-proof outputs update (all 5 files) | DONE |

---

## A. Coverage Gap Inventory

### Global Numbers

| Metric | Value |
|--------|-------|
| Total formal predictions | 1121 |
| RESOLVING | 1058 |
| RESOLVED | 58 (36 HIT, 18 MISS, 4 NOT_SCORED) |
| OPEN | 5 |
| Distribution allowed ratio | **80.38%** (up from 44.73% in v3) |
| Distribution blocked | 93 |
| Truth blocked | 0 |

### JA Tracker Coverage

| Metric | Value |
|--------|-------|
| Public rows on tracker | 99 (8.83%) |
| In-play | **3** |
| Awaiting | 84 |
| Resolved | 12 |
| Hidden: no_live_article | 1022 |
| Hidden: cross_lang_only | 197 |

**91.17% of predictions are NOT visible on the JA tracker.**

### EN Tracker Coverage

| Metric | Value |
|--------|-------|
| Public rows on tracker | 197 (17.57%) |
| In-play | **0** |
| Awaiting | 193 |
| Resolved | 4 |
| Hidden: no_live_article | 924 |
| Hidden: cross_lang_only | 89 |

**82.43% of predictions are NOT visible on the EN tracker.**

### Root Cause Analysis

**Why are 1022 JA / 924 EN predictions hidden?**

1. **no_live_article** (dominant): The Ghost article referenced by `ghost_url` is not live. Articles were either:
   - Never published (prediction generated but article stayed in draft)
   - Draft-demoted by QA Sentinel (legitimate quality gate)
   - Have broken slugs that don't resolve to a published page

2. **cross_lang_only** (secondary): Article exists only in the other language. 197 JA-hidden have EN articles but no JA version. 89 EN-hidden have JA articles but no EN version.

3. **linked_articles structural gap**: ALL 1121 predictions have `linked_articles = []` (empty). The only prediction-to-article link is the `ghost_url` field. If a slug changes, the link breaks silently.

### In-Play Thinness Diagnosis

| Metric | JA | EN |
|--------|----|----|
| In-play on tracker | 3 | 0 |
| Awaiting on tracker | 84 | 193 |
| RESOLVING with Q2 deadline | 628 | 628 |

**628 predictions have Q2 2026 deadlines but are stuck in 'awaiting' instead of 'in-play'.** The page builder's in-play classification is too restrictive. Readers visiting /predictions/ see an almost-empty "active tracking" section.

---

## B. In-Play Candidate Inventory (Top 20)

### Selection Criteria
- Status: RESOLVING or OPEN
- Deadline: Q2 2026 (April-June) or imminent
- Diverse topics: geopolitics, crypto/finance, AI/tech, economics
- Mixed conviction levels (high/medium/low probability)

### Candidates

| # | ID | Title (short) | Lang | Deadline | Pick | Codex Action |
|---|----|----|------|----------|------|------|
| 1 | NP-0048 | Trump Iran Gambit — China Window | EN | Mar 31-Apr 2 | YES@87% | **Check if past deadline → resolve** |
| 2 | NP-0028 | GPT-6 Multimodal Launch | EN | May 2026 | YES@77% | Ensure article live → in-play |
| 3 | NP-0078 | トランプ対イラン攻撃示唆 | JA | 3月中旬〜4月 | YES@62% | **Check deadline → resolve or in-play** |
| 4 | NP-0871 | Bitcoin $120K Institutional Herding | EN | 2026-05-06 | NO@27% | Ensure article live → in-play |
| 5 | NP-0999 | Bitcoin 500万円 Breakout | JA | 2026-06-17 | YES@77% | Ensure article live → in-play |
| 6 | NP-0035 | Bitcoin $120K FOMO | EN | Jun 10-11 | NO@27% | Ensure article live → in-play |
| 7 | NP-0082 | 南シナ海 米中偶発衝突リスク | JA | 4-6月 G7前後 | NO@11% | Ensure article live → in-play |
| 8 | NP-0065 | UK Energy Bills & Iran | EN | Late May-Jun | YES@82% | Ensure article live → in-play |
| 9 | NP-0085 | 米軍中東被害リスク | JA | 3月〜6月 | YES@82% | Ensure article live → in-play |
| 10 | NP-0072 | Trump vs Banks Crypto | EN | Q2 Apr-Jun | YES@62% | Ensure article live → in-play |
| 11 | NP-0091 | Iran Overreach Trap | EN | Mar-Jun | YES@91% | Ensure article live → in-play |
| 12 | NP-0033 | US Stablecoin Regulation | EN | Q2 Apr-Jun | NO@18% | Ensure article live → in-play |
| 13 | NP-0088 | シビハ外相発言 恐怖の不均衡 | JA | 3月〜6月 | NO@3% | Ensure article live → in-play |
| 14 | NP-0083 | Ethereum Staking Yield | EN | Q2 Apr-Jun | YES@38% | Ensure article live → in-play |
| 15 | NP-0074 | Pentagon China-First Strategy | EN | Mar-Apr | YES@91% | **Check deadline → resolve or in-play** |
| 16 | NP-0070 | Iran + Taiwan China Window | EN | Mar-Jun | YES@94% | Ensure article live → in-play |
| 17 | NP-1009 | Bitcoin $120K Supply Squeeze | EN | 2026-05-06 | NO@27% | Ensure article live → in-play |
| 18 | NP-0052 | Congress Iran War Powers | EN | Late Apr/May | NO@11% | Ensure article live → in-play |
| 19 | NP-0012 | 公開企業BTC 200万枚 | JA | 2026-12-31 | NO@15% | **OPEN status — needs article first** |
| 20 | NP-0071 | FATF Stablecoin Warning | EN | Q2-Q3 | YES@77% | Ensure article live → in-play |

### Summary

- **By language**: JA=6, EN=14
- **By topic**: Geopolitics=7, Crypto/Finance=9, AI/Tech=2, Economics=2
- **Immediate action** (deadline may have passed): NP-0048, NP-0078, NP-0074 — Codex should resolve these first
- **OPEN → needs article**: NP-0012 needs a live Ghost article before it can appear on tracker

---

## C. Tracker Currentness Recommendations (Top 5)

### TCR-1: Batch In-Play Promotion (HIGH PRIORITY)

**Problem**: 628 RESOLVING predictions have Q2 deadlines but only 3 JA / 0 EN show as in-play.
**Fix**: Adjust page_builder in-play classification to include RESOLVING predictions with near-term deadlines.
**Impact**: JA 3→12, EN 0→15 in-play predictions.
**Risk**: Low — display-only change.
**Done**: JA in-play ≥ 8, EN in-play ≥ 10 after page rebuild.

### TCR-2: Auto-Resolve Past-Deadline Predictions (HIGH)

**Problem**: Many RESOLVING predictions have March 2026 or earlier deadlines. These are stale.
**Fix**: Run auto_verifier in batch mode for all past-deadline predictions.
**Impact**: 50-200 predictions resolved. Brier sample size increases.
**Risk**: Medium — ambiguous cases need manual review.
**Done**: Zero RESOLVING predictions with deadline > 30 days past.

### TCR-3: Fix Hidden Articles for Top 20 Candidates (MEDIUM)

**Problem**: Top 20 in-play candidates are hidden because their Ghost articles aren't live.
**Fix**: Publish or republish the 20 articles via Ghost Admin API.
**Impact**: 20 predictions become visible. Prerequisite for TCR-1.
**Risk**: Low.
**Done**: All 20 slugs return HTTP 200.

### TCR-4: Populate linked_articles Field (LOW)

**Problem**: ALL 1121 predictions have `linked_articles = []`. Fragile single-point link via ghost_url.
**Fix**: Backfill linked_articles from ghost_url + Ghost API slug resolution.
**Impact**: Structural improvement. Enables richer cross-referencing.
**Risk**: Low — additive.
**Done**: ≥ 200 predictions have valid linked_articles entries.

### TCR-5: Cross-Language Article Pairs (LOW)

**Problem**: 197 JA-hidden predictions have EN-only articles. 89 EN-hidden have JA-only articles.
**Fix**: Translate top-value articles to create same-language pairs.
**Impact**: JA 8.83% → ~10%, EN 17.57% → ~18.5%.
**Risk**: Medium — requires translation pipeline.
**Done**: ≥ 10 cross_lang_only predictions in each language gain same-language articles.

### Cumulative Impact Projection

```
Current state:
  JA: 3 in-play, 84 awaiting, 8.83% coverage
  EN: 0 in-play, 193 awaiting, 17.57% coverage

After TCR-1 + TCR-2 + TCR-3:
  JA: ~12 in-play, 100+ resolved, ~12% coverage
  EN: ~15 in-play, 100+ resolved, ~20% coverage
  Tracker appearance: "alive and actively tracking dozens of predictions"

After all 5 TCRs:
  Coverage improvement + structural robustness
  linked_articles populated, cross-language gaps reduced
```

---

## Distribution Ratio Update

| Metric | v3 (prior session) | v4 (this session) |
|--------|--------------------|--------------------|
| distribution_allowed_ratio_pct | 44.73% | **80.38%** |
| distribution_blocked | 262 | 93 |
| truth_blocked | 0 | 0 |

**+35.65pp improvement.** CAP-1 through CAP-4 from v3 appear partially or fully applied.

---

## Do Not Touch

- `data/prediction_db.json` (except additive changes by Codex)
- `scripts/one_pass_completion_gate.py`
- `scripts/release_governor.py`
- `scripts/article_release_guard.py`
- `scripts/build_article_release_manifest.py`
- `scripts/prediction_deploy_gate.py`
- `scripts/synthetic_user_crawler.py`
- `reports/content_release_snapshot.json`
- `reports/one_pass_completion_gate.json`
- `reports/article_release_manifest.json`

---

*End of sidecar task result v4. Machine-readable: `task_result_v4.json`*
