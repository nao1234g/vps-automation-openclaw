# Operations Board — Nowpattern Platform

> Single operational board for the current platform state, restart readiness, and cross-agent execution.
> This file is the source of truth for "100% done / not done yet" tracking.
> Last updated: 2026-04-05 12:47 JST

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
- This file is also the **single human-readable coordination board** for all agents touching prediction/article restart work.
- Agent-local files may still exist for resume safety, but they are **not** the planning authority.
- Every agent must mirror these four facts here:
  - what is in progress now
  - what is blocked
  - what is next
  - what is actually done

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
- Public state model V2 is now implemented, documented, and consumed by the public tracker.
- Reader-facing methodology pages are live at the new JA/EN URLs, and stale Caddy redirects were removed and reloaded.
- Tracker page titles / meta descriptions no longer overclaim `Full Accuracy Transparency`; they now expose public-score record wording with provisional-score context.
- JA/EN tracker bucket counts are now aligned from the same canonical state path: `976 in play / 87 awaiting / 58 resolved`.
- Recovery scope is complete, but product/content maturity is still open and tracked below.

---

## Cross-Agent Coordination

This section is the one place every agent should check first.

### Coordination Rule

- `docs/OPERATIONS_BOARD.md` is the shared operational truth.
- `.agent-mailbox/*.md` is for message passing, not final status truth.
- `reports/claude_sidecar/*` is sidecar-local execution memory, not the shared board.
- If an agent updates a mailbox or sidecar status, the user-visible state still must be mirrored here.

### Current Agent Snapshot

| Agent | Current Status | Current Scope | Next Exact Step | Source |
|------|----------------|---------------|-----------------|--------|
| Codex | `IN_PROGRESS` | R2 new-work bilingual linkage enforcement | patch publish path to enforce prediction linkage before Ghost publish | `.coordination/codex.json` |
| Claude Code sidecar | `DONE` | `sidecar-20260405-prediction-quality-v1` / `all-phases-done` | completed; choose next scope from Shared Open Queue | `reports/claude_sidecar/session_status.json` |

### Shared Open Queue

These are the highest-priority not-done items across all agents:

1. Reduce prediction-page initial load cost
2. Enforce JA/EN linkage for every newly published prediction
3. Add append-only prediction history
4. Add tamper-evident snapshot chaining
5. Raise article-backed JA/EN coverage for high-value predictions

### Restart Execution Order

This is the ordered implementation queue for article-restart readiness. If work pauses, resume from the first row that is not `DONE`.

| Order | Track | Current % | Status | Why It Matters | Next Exact Implementation Step |
|------|-------|-----------|--------|----------------|--------------------------------|
| 1 | R1 Tracker performance readiness | `100%` | `DONE` | first-paint cost had to be cut before article restart could be credible | keep monitoring live payload/page regressions; next work starts at R2 |
| 2 | R2 New-work bilingual linkage enforcement | `15%` | `IN_PROGRESS` | new JA-only / EN-only prediction publishing must stop | wire the prediction-linkage gate into the shared release path and classify the 80 `missing_sibling` cases into an executable backfill queue |
| 3 | R3 Prediction history trail | `10%` | `NOT_STARTED` | restart should preserve a visible append-only change trail | define the per-prediction history schema and write-path before new publishing resumes |
| 4 | R4 Tamper-evident integrity chain | `5%` | `NOT_STARTED` | silent retroactive edits must become detectable | extend the current ledger approach into prediction snapshot chaining for new updates |
| 5 | R5 Legacy article-backed coverage lift | `10%` | `IN_PROGRESS` | tracker parity without article depth is not enough for restart confidence | raise high-value JA/EN article-backed coverage from the current `JA 99 / EN 197` baseline |

---

## Schedule And Progress Model

### Target Dates

- **Core public recovery target**: `2026-04-10 JST`
  - Scope: P0-P6
  - Meaning: public truth restored, counts aligned, leaderboard honest, English page language fixed, vote CTA real
- **Recovery board 100% completion target**: `2026-05-01 JST`
  - Scope: P0-P10
  - Meaning: all current recovery tasks done, including redesign/spec tasks and methodology pages
- **Product/content maturity target**: `2026-05-30 JST`
  - Scope: M0-M3
  - Meaning: recovery is no longer the bottleneck; EN card depth, human participation framing, and scored-sample operations are credible enough to market aggressively
- **Core public recovery achieved**: `2026-04-04 JST`
- **Recovery board achieved**: `2026-04-04 JST`

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
| Recovery board (P0-P10) | `100.0%` | `2026-05-01 JST` | `DONE` |
| Product/content maturity (M0-M3) | `49.1%` | `2026-05-30 JST` | `IN_PROGRESS` |
| Article restart readiness | `72.0%` | `TBD` | `IN_PROGRESS` |
| Restart-foundation buildout | `32.5%` | `TBD` | `IN_PROGRESS` |

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
| P8 Status model redesign | 10 | 100% | 10.0 | 2026-04-24 JST | DONE |
| P9 EN critical-slot contamination cleanup | 4 | 100% | 4.0 | 2026-04-17 JST | DONE |
| P10 Reader-facing methodology pages | 4 | 100% | 4.0 | 2026-05-01 JST | DONE |

**Current recovery-weighted completion**: `100.0 / 100`

Interpretation:

- The recovery work in this board is **done**.
- Public truth is aligned across DB-derived snapshot, API, tracker HTML, JSON-LD, leaderboard copy, and methodology pages.
- This does **not** mean product/content maturity is done.
- This also does **not** mean article publishing should restart immediately.
- The maturity work below remains open until EN card substance, human-baseline framing, and scored-sample operations are strong enough to market without caveats.
- The article-restart bar is still blocked by prediction-page speed, bilingual article coverage, and final SEO verification.

### Restart Foundation Buildout

This is the stronger system the user actually wants before article restart:

1. a canonical prediction registry
2. a bilingual article layer that can link each prediction to JA and EN analysis
3. a public tracker that reflects the canonical registry honestly
4. a history trail that preserves what changed and when
5. a tamper-evident audit surface that makes silent retroactive edits difficult

Current interpretation:

- `1121` means tracked predictions, not fully paired bilingual articles
- tracker visibility is now `1121 / 1121` in JA and EN
- article parity is still far from complete
- restart should happen only under a stricter new contract, not under the old loose workflow

### Restart Criteria

Normal publishing should restart only when all of these are true:

- [ ] prediction tracker initial load is no longer obviously slow
- [ ] every newly published prediction has JA and EN article linkage rules
- [ ] every new prediction has a stable history trail
- [ ] every new prediction has tamper-evident integrity metadata
- [ ] the tracker clearly distinguishes article-backed vs tracker-only rows
- [ ] the restart workflow no longer creates new JA-only or EN-only analysis by accident

### Restart Decision Table

**Current answer**: `NO`, do **not** restart normal article publishing yet.

| Area | Current State | Ready Now? | What Still Must Be Implemented |
|------|---------------|------------|--------------------------------|
| Public tracker truth | Tracker counts and score surfaces are aligned (`1121 total / 58 resolved / 54 publicly scored`) | YES | Keep monitoring only |
| Prediction page speed | live tracker now seeds only the first `36` tracking cards, defers the remaining `1063` via `/reader-predict/tracking-payload/{lang}`, and serves page HTML at about `0.90 MB` (`JA 908,725 bytes / EN 896,113 bytes`) with first response around `0.32s-0.44s` from the VPS curl check | YES | keep monitoring for regressions; optimize further only if user-facing complaints persist |
| New-work JA/EN linkage | New prediction-linked work is not yet fully blocked on bilingual sibling readiness in the shared restart workflow | NO | Enforce JA/EN sibling contract for every newly published prediction-linked article |
| Prediction history trail | A stable per-prediction append-only history trail is not yet part of the restart contract | NO | Add append-only prediction history and make it part of release/readiness checks |
| Tamper-evident audit surface | Tamper-evident integrity metadata is not yet fully wired into the restart path | NO | Add hash-chain or equivalent tamper-evident snapshot chain for new prediction updates |
| Article-backed vs tracker-only distinction | Internal coverage metrics exist, but the restart contract still treats this as unfinished | NO | Make article-backed vs tracker-only state explicit and durable in the public workflow |
| Accidental JA-only / EN-only publishing | The old workflow can still drift unless the stricter release contract is enforced end-to-end | NO | Block or hold releases that would create new one-language-only analysis by accident |
| Legacy article parity | Tracker visibility is `1121 / 1121`, but same-language live article coverage is still far from full parity | NO | Backfill high-value legacy predictions and raise JA/EN article-backed coverage over time |

### Restart Foundation Tracks

| Track | Weight | Current % | Status |
|------|--------|-----------|--------|
| R1 Tracker performance readiness | 25 | 100% | DONE |
| R2 New-work bilingual linkage enforcement | 20 | 15% | IN_PROGRESS |
| R3 Prediction history trail | 20 | 10% | NOT_STARTED |
| R4 Tamper-evident integrity chain | 20 | 5% | NOT_STARTED |
| R5 Legacy article-backed coverage lift | 15 | 10% | IN_PROGRESS |

### Restart Foundation Time Estimate

- To reach "safe to restart under the new contract": `26-48 hours` of implementation work
- Realistically: `3-6 working days`
- Full legacy JA/EN depth is not an hours-scale coding task; it remains a `days to weeks` content/tooling backlog

### Post-Recovery Maturity Track

| Task | Weight | Current % | Weighted Points | Target Date | Status |
|------|--------|-----------|-----------------|-------------|--------|
| M0 Honest completion model and board split | 20 | 100% | 20.0 | 2026-04-06 JST | DONE |
| M1 Publicly scored sample growth and backlog compression | 30 | 34.9% | 10.5 | 2026-05-15 JST | IN_PROGRESS |
| M2 Human baseline readiness before public contest framing | 20 | 18.2% | 3.6 | 2026-05-20 JST | IN_PROGRESS |
| M3 EN card completeness beyond shell integrity | 30 | 50.0% | 15.0 | 2026-05-30 JST | IN_PROGRESS |

**Current maturity-weighted completion**: `49.1 / 100`

---

## Current Reality Snapshot

These are the numbers this board is trying to reconcile:

- Local canonical DB: `1121 total / 58 resolved / 54 scorable`
- Local stale `stats` block: `1121 total / 6 resolved / avg_brier_score 0.1828`
- Live API `/api/predictions/`: `1121 total`
- Live API `/reader-predict/leaderboard`: AI `avg_brier_score=0.4608 / resolved_count=54 / resolved_total=58 / not_scorable_count=4`
- Live API `/reader-predict/leaderboard`: readers `total_votes=11 / total_voters=11 / resolved_votes=1 / human_public_ready=false`
- Live API `/reader-predict/top-forecasters`: `human_public_ready=false`, thresholds `25 voters / 200 votes / 20 resolved votes`, `public_forecasters` currently contains AI only
- Live `/predictions/`: `1121 total / 58 resolved / vote DOM 490 containers / 980 buttons`
- Live `/en/predictions/`: `1121 total / 58 resolved / vote DOM 489 containers / 978 buttons`
- Live `/predictions/` toolbar buckets: `976 in play / 87 awaiting / 58 resolved`
- Live `/en/predictions/` toolbar buckets: `976 in play / 87 awaiting / 58 resolved`
- Live `/predictions/` and `/en/predictions/` JSON-LD dataset size: `1121 predictions (58 resolved, 54 publicly scorable)`
- Fresh site link crawl: `539 checked / 0 failed`
- Fresh prediction-page availability check: JA `/predictions/` `6764ms`, EN `/en/predictions/` `8275ms`, reader API health `92ms`
- Content release snapshot: tracker rows are public in both languages (`1121 / 1121`), but same-language article coverage is still uneven (`JA 99`, `EN 197`)
- Content release snapshot: tracker-only rows with no same-language live article remain large (`JA 1022`, `EN 924`)
- Live `/en/predictions/`: `<html lang="en">`
- Live `/en/leaderboard/`: `<html lang="en">`
- Live tracker titles/meta now use public-score record wording instead of `Full Accuracy Transparency`
- Automated maturity audit now runs as `prediction-maturity` in `site_guard_runner`, scheduled by `site_guard_scheduler` every 6 hours at minute `56`, and writes `/opt/shared/reports/site_guard/prediction_maturity_audit.json` plus `.md`
- Latest maturity audit snapshot: `M1 34.9% / M2 18.2% / M3 50.0%`
- Latest maturity audit blockers: `87 awaiting vs 58 resolved`, `54/150 publicly scored`, `11/25 human voters`, `EN generic fallback count 1356`
- Live leaderboard titles/meta now use `AI Benchmark Leaderboard | Nowpattern`, not `AIを倒せるか？`
- Live vote widget: JA/EN click-path, localStorage persistence, and community stats rendering all pass live Playwright E2E on desktop + mobile
- Live tracker card deadline badges now include wrap guards on both JA/EN pages
- Live methodology URLs now return current content with no stale redirect hijack:
  - `/forecasting-methodology/`
  - `/en/forecasting-methodology/`
  - `/forecast-scoring-and-resolution/`
  - `/en/forecast-scoring-and-resolution/`
  - `/forecast-integrity-and-audit/`
  - `/en/forecast-integrity-and-audit/`

Interpretation:

- The API and prediction tracker pages are corrected live.
- The truth-source collision for prediction counts and score semantics is resolved live.
- Broken-link risk is low on the currently crawled public set.
- The remaining work is not correctness debt, but it is still release debt for article publishing.
- Article restart is not green yet because performance and bilingual article coverage are still materially weak.

---

## Global Done Condition

The prediction platform is only considered **fully recovered** when all of the following are true:

- [x] Canonical counts match across DB, API, HTML, and JSON-LD
- [x] English pages render with correct `html lang="en"`
- [x] Vote CTA DOM exists and the widget is actually usable
- [x] No stale `stats` block numbers leak into any public surface
- [x] Public score language is honest (`PROVISIONAL` where required)
- [x] Human leaderboard does not misrepresent empty participation
- [x] Evidence of live verification is recorded for each item below

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
- Live API now shows human-only reader aggregates and beta-gated public ranking.

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
  - `readers.total_voters: 9`
  - `readers.total_votes: 9`
  - `readers.resolved_votes: 1`
  - `readers.human_public_ready: false`
  - synthetic/test/migrated voters removed from human ranking
  - `public_forecasters` currently contains AI only
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

**Status**: `DONE`
**Weight**: `10`
**Current progress**: `100%`
**Target date**: `2026-04-24 JST`

**Why this exists**

- Local DB status distribution is `open=5 / resolving=1058 / resolved=58`.
- `94.38%` of predictions are `resolving`, which means the current state model is semantically broken.

**Checklist**

- [x] Design separate axes for forecast lifecycle, resolution lifecycle, and content publication lifecycle
- [x] Map current states into the new model
- [x] Define migration plan
- [x] Define public rendering rules from the new state model

**Exit criteria**

- New state model is specified, documented, implemented, and consumed by the public tracker.

**Evidence**

- State model document:
  - [`docs/PREDICTION_STATE_MODEL_V2.md`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/docs/PREDICTION_STATE_MODEL_V2.md)
- Helper implementation:
  - [`scripts/prediction_state_utils.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/prediction_state_utils.py)
- Regression coverage:
  - `python3 scripts/test_prediction_state_utils.py`
- Public tracker now consumes derived V2 state via:
  - [`scripts/prediction_page_builder.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/prediction_page_builder.py)
- Live tracker rows now expose and render from derived state rather than a single overloaded raw `status`.

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

**Status**: `DONE`
**Weight**: `4`
**Current progress**: `100%`
**Target date**: `2026-05-01 JST`

**Why this exists**

- The product needs public explanation pages for scoring, resolution, and integrity.

**Checklist**

- [x] `/forecasting-methodology/` + `/en/forecasting-methodology/`
- [x] `/forecast-scoring-and-resolution/` + `/en/forecast-scoring-and-resolution/`
- [x] `/forecast-integrity-and-audit/` + `/en/forecast-integrity-and-audit/`

**Exit criteria**

- All six pages exist live and are linked from relevant public surfaces.

**Evidence**

- Methodology page generator:
  - [`scripts/update_prediction_methodology_pages.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/update_prediction_methodology_pages.py)
- Regression coverage:
  - `python3 scripts/test_update_prediction_methodology_pages.py`
- Live pages verified:
  - `/forecasting-methodology/` -> `予測手法 — Nowpatternはどう予測を作るか`
  - `/en/forecasting-methodology/`
  - `/forecast-scoring-and-resolution/`
  - `/en/forecast-scoring-and-resolution/` -> `Scoring and Resolution — Brier Score and Outcome Rules`
  - `/forecast-integrity-and-audit/`
  - `/en/forecast-integrity-and-audit/`
- Tracker scorecards and leaderboard pages now link to the methodology pages.
- Stale methodology redirects were removed from Caddy via:
  - [`scripts/patch_ghost_theme_en_urls.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/patch_ghost_theme_en_urls.py)

---

## Progress Summary

| Bucket | Total | Done | Not Done |
|--------|-------|------|----------|
| Global recovery conditions | 7 | 7 | 0 |
| Execution tasks (P0-P10) | 11 | 11 | 0 |

**Platform recovery status**: `DONE`
**Core public recovery achieved**: `2026-04-04 JST`
**Full board achieved**: `2026-04-04 JST`
**Current full-board progress**: `100.0%`
**Current core-recovery progress**: `100.0%`

Reason:

- Core public defects are closed live.
- Public state semantics and reader-facing methodology are now live, documented, and linked.
- There are no remaining open recovery items in this board.

---

## Post-Recovery Watchlist

1. Monitor Ghost Admin API `502/503` rates during future tracker page updates
2. Monitor reader sample growth against the human-public thresholds (`25 voters / 200 votes / 20 resolved votes`)
3. Decide whether to open a new board for post-recovery product work beyond this recovery scope
4. Keep methodology pages in sync with future scoring-policy changes
5. Treat any new public inconsistency as a fresh issue, not as unfinished recovery work from this board

---

## Update Rule

When anything changes, update all of:

- task status
- checklist boxes
- evidence field
- progress summary counts
- `.coordination/{agent}.json` current state
- `Current Agent Snapshot` in this board

Recommended sync command:

- `python3 scripts/update_operations_board.py`

If those four are not updated together, this board is stale.
