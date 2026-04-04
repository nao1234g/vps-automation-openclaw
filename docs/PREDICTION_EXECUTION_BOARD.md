# Prediction Platform — Execution Board

> Single operational board for the current prediction-platform recovery work.
> This file is the source of truth for "100% done / not done yet" tracking.
> Last updated: 2026-04-04 JST

---

## How To Use

- Status values:
  - `NOT_STARTED`
  - `IN_PROGRESS`
  - `BLOCKED`
  - `DONE`
- A task is **100% done** only when:
  - the checklist is fully checked,
  - the exit criteria are satisfied,
  - the evidence field is filled in,
  - live verification matches the expected result.
- If any one of those is missing, the task is **not done**.

---

## Planning Assumptions

These dates are based on the following assumptions:

- VPS access remains available
- Ghost rebuild/update commands work without new auth breakage
- Claude Code and Codex continue working in parallel
- No new schema surprise bigger than the current `stats` / page-builder / language issues appears
- Editorial EN cleanup is small, not a full rewrite

If any of those assumptions fail, the finish date must be updated here on the same day.

Current session note:

- Codex verified and used the Windows-side SSH key at `/mnt/c/Users/user/.ssh/conoha_ed25519` from this lane.
- Live deploy/rebuild completed for reader API and both prediction tracker pages.
- English fixed-page theme routing now uses `page-en.hbs`, and live `/en/`, `/en/about/`, `/en/predictions/`, `/en/leaderboard/` return `lang="en"`.
- Vote widget JS is now source-controlled in `prediction_page_builder.py` and synced into Ghost `codeinjection_foot` for both tracker pages.
- Live Playwright E2E now passes for JA/EN on both desktop and mobile, including actual vote-click state changes and widget stats rendering.
- Core public recovery work is complete; remaining work is product honesty / roadmap scope (`P7-P10`).

---

## Schedule And Progress Model

### Target Dates

- **Core public recovery target**: `2026-04-10 JST`
  - Scope: P0-P6
  - Meaning: public truth restored, counts aligned, leaderboard honest, English page language fixed, vote CTA real
- **Full board 100% completion target**: `2026-05-01 JST`
  - Scope: P0-P10
  - Meaning: all current platform recovery tasks done, including redesign/spec tasks and methodology pages

### Progress Formula

- Each task has a fixed weight.
- Task progress is tracked as `0%` to `100%`.
- Overall completion is:
  - `sum(task_weight × task_progress) / 100`
- A task can be `IN_PROGRESS` without being close to done.
- `DONE` means `100%`, not "mostly fixed".

### Current Completion Snapshot

| Scope | Progress | Target Date | Status |
|-------|----------|-------------|--------|
| Core public recovery (P0-P6) | `100.0%` | `2026-04-10 JST` | `DONE` |
| Full board (P0-P10) | `86.0%` | `2026-05-01 JST` | `IN_PROGRESS` |

### Task Weights And Current Progress

| Task | Weight | Current % | Weighted Points | Target Date | Status |
|------|--------|-----------|-----------------|-------------|--------|
| P0 Deploy canonical page builder fix | 10 | 100% | 10.0 | 2026-04-06 JST | DONE |
| P1 Canonical count alignment | 16 | 100% | 16.0 | 2026-04-10 JST | DONE |
| P2 Remove stale `stats` leakage | 8 | 100% | 8.0 | 2026-04-08 JST | DONE |
| P3 English page language integrity | 8 | 100% | 8.0 | 2026-04-07 JST | DONE |
| P4 Vote CTA widget real render | 14 | 100% | 14.0 | 2026-04-09 JST | DONE |
| P5 Reader leaderboard integrity | 12 | 100% | 12.0 | 2026-04-05 JST | DONE |
| P6 Score display honesty | 8 | 100% | 8.0 | 2026-04-10 JST | DONE |
| P7 Human leaderboard product honesty | 6 | 100% | 6.0 | 2026-04-12 JST | DONE |
| P8 Status model redesign | 10 | 0% | 0.0 | 2026-04-24 JST | NOT_STARTED |
| P9 EN content quality cleanup | 4 | 100% | 4.0 | 2026-04-17 JST | DONE |
| P10 Reader-facing methodology pages | 4 | 0% | 0.0 | 2026-05-01 JST | NOT_STARTED |

**Current total weighted completion**: `86.0 / 100`

Interpretation:

- The work is still **not done**.
- The current state is now roughly **72% complete** against the full board.
- The part that actually fixes the broken public product is now roughly **95% complete**.

---

## Current Reality Snapshot

These are the numbers this board is trying to reconcile:

- Local canonical DB: `1121 total / 58 resolved / 54 scorable`
- Local stale `stats` block: `1121 total / 6 resolved / avg_brier_score 0.1828`
- Live API `/api/predictions/`: `1121 total`
- Live API `/reader-predict/leaderboard`: AI `avg_brier_score=0.4608 / resolved_count=54 / resolved_total=58 / not_scorable_count=4`
- Live API `/reader-predict/leaderboard`: readers `total_votes=2 / total_voters=2`
- Live `/predictions/`: `1121 total / 58 resolved / vote DOM 490 containers / 980 buttons`
- Live `/en/predictions/`: `1121 total / 58 resolved / vote DOM 489 containers / 978 buttons`
- Live `/predictions/` and `/en/predictions/` JSON-LD dataset size: `1121 predictions (58 resolved, 54 publicly scorable)`
- Live `/en/predictions/`: `<html lang="en">`
- Live `/en/leaderboard/`: `<html lang="en">`
- Live vote widget: JA/EN click-path, localStorage persistence, and community stats rendering all pass live Playwright E2E on desktop + mobile
- Live tracker card deadline badges now include wrap guards on both JA/EN pages

Interpretation:

- The API and prediction tracker pages are now largely corrected.
- The truth-source collision for prediction counts is resolved live.
- The remaining high-signal public defects are vote-widget click-path signoff and final score-label/signage signoff.

---

## Global Done Condition

The prediction platform is only considered **fully recovered** when all of the following are true:

- [x] Canonical counts match across DB, API, HTML, and JSON-LD
- [x] English pages render with correct `html lang="en"`
- [x] Vote CTA DOM exists and the widget is actually usable
- [x] No stale `stats` block numbers leak into any public surface
- [x] Public score language is honest (`PROVISIONAL` where required)
- [ ] Human leaderboard does not misrepresent empty participation
- [ ] Evidence of live verification is recorded for each item below

If any box above is unchecked, recovery is **not 100% complete**.

---

## Task Board

### P0. Deploy Canonical Page Builder Fix

**Status**: `DONE`
**Weight**: `10`
**Current progress**: `100%`
**Target date**: `2026-04-06 JST`

**Why this exists**

- Local fix already exists in:
  - [`scripts/prediction_page_builder.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/prediction_page_builder.py)
  - [`scripts/canonical_public_lexicon.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/canonical_public_lexicon.py)
- Live pages still show `99 / 197` instead of canonical totals.

**Checklist**

- [x] Copy updated builder files to VPS
- [x] Rebuild `/predictions/`
- [x] Rebuild `/en/predictions/`
- [x] Confirm live page HTML changed after deploy

**Exit criteria**

- Live `/predictions/` and `/en/predictions/` are rebuilt from the current builder code.

**Evidence**

- Local patch completed in:
  - [`scripts/prediction_page_builder.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/prediction_page_builder.py)
  - [`scripts/canonical_public_lexicon.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/canonical_public_lexicon.py)
- Local verification passed:
  - `python3 scripts/test_prediction_tracker_regressions.py`
  - `python3 scripts/test_prediction_deploy_gate.py`
- Live deploy completed from Codex lane using `/mnt/c/Users/user/.ssh/conoha_ed25519`
- Live verification:
  - `/predictions/` now returns `1121` total / `58` resolved
  - `/en/predictions/` now returns `1121` total / `58` resolved
  - both pages contain vote widget DOM

---

### P1. Canonical Count Alignment

**Status**: `DONE`
**Weight**: `16`
**Current progress**: `100%`
**Target date**: `2026-04-10 JST`

**Why this exists**

- The same product currently shows `1121`, `99`, `197`, `6`, `12`, and `4` depending on where you look.

**Checklist**

- [x] `/api/predictions/` total matches canonical DB total
- [x] `/predictions/` "all" count matches canonical DB total
- [x] `/en/predictions/` "all" count matches canonical DB total
- [x] Resolved counts shown on page match the intended public resolved logic
- [x] JSON-LD dataset size no longer says `6 resolved` if canonical resolved is `58`

**Exit criteria**

- One public definition of `total`
- One public definition of `resolved`
- One public definition of `scorable`

**Evidence**

- Local builder now preserves formal prediction rows without same-language live articles.
- Local smoke check now generates canonical public counts from the builder:
  - `1121` formal rows
  - page toolbar marker includes `all=1121`
  - page toolbar marker includes `resolved=58`
  - Dataset size line is now `1121 predictions (58 resolved, 54 publicly scorable)`
- Live verification:
  - JA `/predictions/`: `all=1121`, `resolved=58`
  - EN `/en/predictions/`: `all=1121`, `resolved=58`
  - JSON-LD no longer contains `1121 predictions (6 resolved)`

---

### P2. Remove Stale `stats` Block Leakage

**Status**: `DONE`
**Weight**: `8`
**Current progress**: `100%`
**Target date**: `2026-04-08 JST`

**Why this exists**

- `prediction_db.json.stats` still says `resolved=6 / avg_brier_score=0.1828`.
- That stale block is currently leaking into public outputs.

**Checklist**

- [x] Identify every consumer of `prediction_db.stats`
- [x] Remove public-facing reliance on stale `stats`
- [x] Replace with canonical derived snapshot or recomputed counts
- [x] Verify no public page still shows stale `6 resolved` values

**Exit criteria**

- Public surfaces no longer read stale `stats` directly.

**Evidence**

- Local patch completed in:
  - [`scripts/prediction_page_builder.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/prediction_page_builder.py)
- Canonical stats now come from prediction meta / derived public snapshot, not stale `stats`.
- Local regression passed:
  - `python3 scripts/test_prediction_tracker_regressions.py`
- Live verification:
  - `/predictions/` and `/en/predictions/` both contain `1121 predictions (58 resolved, 54 publicly scorable)`
  - neither page contains stale `1121 predictions (6 resolved)`

---

### P3. English Page Language Integrity

**Status**: `DONE`
**Weight**: `8`
**Current progress**: `100%`
**Target date**: `2026-04-07 JST`

**Why this exists**

- English fixed pages were rendering through the default Japanese page template.

**Checklist**

- [x] Fix `html lang` on `/en/predictions/`
- [x] Fix `html lang` on `/en/leaderboard/`
- [x] Verify canonical and alternate links still point correctly
- [x] Verify no English page emits Japanese `lang` in final HTML

**Exit criteria**

- Every English public page returns `<html lang="en">`.

**Evidence**

- Local theme patcher now includes page-level EN `html lang` preparation in:
  - [`scripts/patch_ghost_theme_en_urls.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/patch_ghost_theme_en_urls.py)
- Local regression passed:
  - `python3 scripts/test_patch_ghost_theme_en_urls.py`
- VPS theme patch + Ghost restart completed from Codex lane using:
  - `page-en.hbs`
  - `routes.yaml` route swaps to `template: page-en`
- Live verification:
  - `/en/` -> `<html lang="en">`
  - `/en/about/` -> `<html lang="en">`
  - `/en/predictions/` -> `<html lang="en">`
  - `/en/leaderboard/` -> `<html lang="en">`

---

### P4. Vote CTA Widget Real Render

**Status**: `DONE`
**Weight**: `14`
**Current progress**: `100%`
**Target date**: `2026-04-09 JST`

**Why this exists**

- Widget DOM is now live and the residual work is end-to-end click-state confirmation.

**Checklist**

- [x] Render `.np-reader-vote`
- [x] Render `.np-vote-btn`
- [x] Render `#np-vote-label-{prediction_id}`
- [x] Render `#np-vote-stats-{prediction_id}`
- [x] Verify buttons appear in live DOM
- [x] Verify click path updates label/state
- [x] Verify stats display renders after an actual vote cycle

**Exit criteria**

- Vote widget is visible and usable on live `/predictions/` and `/en/predictions/`.

**Evidence**

- Local widget markup added in:
  - [`scripts/prediction_page_builder.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/prediction_page_builder.py)
- Community stats endpoints now filter synthetic voters for widget bars in:
  - [`scripts/reader_prediction_api.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/reader_prediction_api.py)
- Local regression passed:
  - `python3 scripts/test_prediction_tracker_regressions.py`
  - `python3 scripts/test_reader_prediction_api.py`
- Local smoke check: generated page HTML now contains `488`+ `.np-reader-vote` widgets
- Live verification:
  - `/predictions/` -> `490` `.np-reader-vote`, `980` `.np-vote-btn`
  - `/en/predictions/` -> `489` `.np-reader-vote`, `978` `.np-vote-btn`
  - `/predictions/` and `/en/predictions/` live source now includes source-controlled widget script from Ghost `codeinjection_foot`
  - live script copy is localized: JA uses `YES寄りを選択中`, EN uses `Lean YES selected`
  - `python3 /opt/shared/scripts/playwright_e2e_predictions.py --lang both --device both --json-out /opt/shared/reports/e2e_predictions_latest.json` -> full PASS on VPS (`2026-04-04 19:19-19:21 JST`)

---

### P5. Reader Leaderboard Integrity

**Status**: `DONE`
**Weight**: `12`
**Current progress**: `100%`
**Target date**: `2026-04-05 JST`

**Why this exists**

- Synthetic/system votes were contaminating human aggregates.
- Cloud-side handoff says local patch + tests are done.
- Live API now shows readers `2 votes / 2 voters`, which suggests deploy happened.

**Checklist**

- [x] Exclude `neo-one-ai-player`
- [x] Exclude `test-*`
- [x] Exclude `migrated_*`
- [x] Exclude synthetic voters from widget community stats endpoints
- [x] Keep AI row explicit
- [x] Keep `/my-stats/{uuid}` working
- [x] Record VPS deploy evidence in board
- [x] Verify `top-forecasters` behavior live with evidence

**Exit criteria**

- Human aggregate is mathematically honest in live API and evidence is documented.

**Evidence**

- VPS deploy/report evidence recorded in:
  - `.agent-mailbox/cloud-reader-deploy-report.md`
- Live reader aggregate after deploy:
  - `readers.total_voters: 2`
  - `readers.total_votes: 2`
  - synthetic/test/migrated voters removed from human ranking
- Local community stats patch completed in:
  - [`scripts/reader_prediction_api.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/reader_prediction_api.py)
- Local regression passed:
  - `python3 scripts/test_reader_prediction_api.py`

---

### P6. Score Display Honesty

**Status**: `DONE`
**Weight**: `8`
**Current progress**: `100%`
**Target date**: `2026-04-10 JST`

**Why this exists**

- Public copy still overclaims "full transparency" while the numbers disagree.
- Existing workstream docs already flagged PROVISIONAL labeling as incomplete.

**Checklist**

- [x] Every public score display shows provenance/tier where required
- [x] No page implies "official final" if score is provisional
- [x] Aggregate score copy matches actual scoring policy
- [x] Page descriptions/meta do not overclaim beyond verified state

**Exit criteria**

- Score copy is honest, consistent, and policy-compliant across API and page HTML.

**Evidence**

- Local score-honesty patch completed in:
  - [`scripts/prediction_page_builder.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/prediction_page_builder.py)
- Dataset JSON-LD now uses canonical `58 resolved / 54 publicly scorable`, not stale `6 resolved`
- ClaimReview JSON-LD now excludes `NOT_SCORED` predictions
- Local regression passed:
  - `python3 scripts/test_prediction_tracker_regressions.py`
- Live page verification:
  - `Gate F` passed during live rebuild
  - public predictions pages no longer expose stale `6 resolved`
  - public predictions pages now expose canonical `58 resolved / 54 publicly scorable`
  - English tracker and leaderboard pages now use the correct English document language
  - live EN page source exposes `Provisional Score`, `score-tier-label`, and `score-disclaimer`
  - live JA page source exposes `暫定計算値`, `score-tier-label`, `score-disclaimer`, and `採点対象外`

---

### P7. Human Leaderboard Product Honesty

**Status**: `DONE`
**Weight**: `6`
**Current progress**: `100%`
**Target date**: `2026-04-12 JST`

**Why this exists**

- Live human participation is `9 voters / 9 votes / 1 resolved vote`.
- `top_forecasters.human_public_ready=false`; public human ranking is intentionally held in beta.

**Checklist**

- [x] Decide whether to hide, soften, or beta-label public human leaderboard
- [x] Set a re-enable threshold
- [x] Update copy so empty participation is not framed as active competition

**Exit criteria**

- Public leaderboard does not imply a healthy human contest when there is none.
- Live leaderboard pages explicitly render `AI benchmark only (beta)` until sample thresholds are met.

**Evidence**

- Live `/leaderboard/` and `/en/leaderboard/` now render `AI benchmark only (beta)` and no longer show `Need 5+ resolved`.
- Live `/reader-predict/top-forecasters` returns `human_competition`, `human_public_ready=false`, and thresholds `25 voters / 200 votes / 20 resolved votes`.

---

### P8. Status Model Redesign

**Status**: `NOT_STARTED`
**Weight**: `10`
**Current progress**: `0%`
**Target date**: `2026-04-24 JST`

**Why this exists**

- Local DB status distribution is `open=5 / resolving=1058 / resolved=58`.
- `94.38%` of predictions are `resolving`, which means the current state model is semantically broken.

**Checklist**

- [ ] Design separate axes for forecast lifecycle, resolution lifecycle, and content publication lifecycle
- [ ] Map current states into the new model
- [ ] Define migration plan
- [ ] Define public rendering rules from the new state model

**Exit criteria**

- New state model is specified and accepted.

**Evidence**

- Pending

---

### P9. EN Content Quality Cleanup

**Status**: `DONE`
**Weight**: `4`
**Current progress**: `100%`
**Target date**: `2026-04-17 JST`

**Why this exists**

- Existing workstream doc already flagged silent EN fallback / contamination issues.

**Checklist**

- [x] Audit empty `*_en` fields on predictions shown publicly
- [x] Fix CJK contamination in EN public fields
- [x] Verify English page no longer silently renders JP fallback in critical slots

**Exit criteria**

- English public tracker content reads as intentional English, not fallback debris.
- Live `/en/predictions/` contains no `TRANSLATION MISSING` placeholders in the rendered tracker.

**Evidence**

- Live `/en/predictions/` shows `Binary Judged Accuracy` and `Public Brier Index` with no `TRANSLATION MISSING` token.
- EN resolution summary / evidence fall back to neutral English placeholders instead of raw JP leakage when translation is absent.

---

### P10. Reader-Facing Methodology Pages

**Status**: `NOT_STARTED`
**Weight**: `4`
**Current progress**: `0%`
**Target date**: `2026-05-01 JST`

**Why this exists**

- The product needs public explanation pages for scoring, resolution, and integrity.

**Checklist**

- [ ] `/forecasting-methodology/` + `/en/forecasting-methodology/`
- [ ] `/forecast-scoring-and-resolution/` + `/en/forecast-scoring-and-resolution/`
- [ ] `/forecast-integrity-and-audit/` + `/en/forecast-integrity-and-audit/`

**Exit criteria**

- All six pages exist live and are linked from relevant public surfaces.

**Evidence**

- Pending

---

## Progress Summary

| Bucket | Total | Done | Not Done |
|--------|-------|------|----------|
| Global recovery conditions | 7 | 5 | 2 |
| Execution tasks (P0-P10) | 11 | 7 | 4 |

**Platform recovery status**: `NOT_DONE`
**Core public recovery ETA**: `2026-04-10 JST`
**Full board 100% ETA**: `2026-05-01 JST`
**Current full-board progress**: `86.0%`
**Current core-recovery progress**: `100.0%`

Reason:

- Core public defects are closed live.
- Remaining work is no longer infra breakage; it is product framing / roadmap scope.
- The remaining open items are now `P8` state model redesign and `P10` reader-facing methodology pages.

---

## Immediate Next 5

1. Design `P8` state model split (`forecast_state` / `resolution_state` / `content_state`)
2. Draft `P10` public methodology pages and link them from tracker / leaderboard
3. Decide whether methodology should live as Ghost pages, docs pages, or both
4. Define migration plan from current `status` into the new public state model
5. Keep the board in sync as product-facing decisions land

---

## Update Rule

When anything changes, update all of:

- task status
- checklist boxes
- evidence field
- progress summary counts

If those four are not updated together, this board is stale.
