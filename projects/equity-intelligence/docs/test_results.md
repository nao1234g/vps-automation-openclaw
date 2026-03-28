# Smoke Test Results — equity-intelligence Judgment Support OS v2

> Run: `bun run tests/smoke-walltalk.ts`
> Date: 2026-03-28
> Env: `WALLTALK_OUTPUT_DIR` = system temp dir (auto-cleaned after run)
> Result: **45/45 PASS**

---

## Summary

| Test Group | Tests | PASS | FAIL |
|------------|-------|------|------|
| [1] writeJudgment / readJudgment round-trip | 8 | 8 | 0 |
| [2] readJudgment — null for unknown ticker | 1 | 1 | 0 |
| [3] writeDossier / readPreviousDossier date filtering | 5 | 5 | 0 |
| [4] getArtifactIndex — hasJudgmentStore flag | 4 | 4 | 0 |
| [5] syncJudgmentStore — creates store from first Thesis | 8 | 8 | 0 |
| [6] syncJudgmentStore — stanceHistory accumulation + risk de-duplication | 8 | 8 | 0 |
| [7] answerCompanyQuestion — intent detection (no LLM) | 6 | 6 | 0 |
| [8] answerCompanyQuestion — JudgmentStore integration path (no LLM) | 5 | 5 | 0 |
| **TOTAL** | **45** | **45** | **0** |

---

## Detailed Results

### [1] writeJudgment / readJudgment round-trip

```
✅ PASS: writeJudgment returns correct path
✅ PASS: readJudgment returns non-null for written ticker
✅ PASS: ticker matches
✅ PASS: market matches
✅ PASS: thesisCount matches
✅ PASS: stanceHistory[0].stance matches
✅ PASS: recurringRisks[0].occurrences = 1
✅ PASS: openQuestions count matches
```

**What was tested**: Mock `JudgmentStore` (ticker=7203, bullish, 1 risk, 2 open questions)
written via `writeJudgment()`, read back via `readJudgment()`, all fields verified equal.

---

### [2] readJudgment — null for unknown ticker

```
✅ PASS: readJudgment(UNKNOWN_XYZ) = null
```

**What was tested**: `readJudgment()` returns `null` (does not throw) when file doesn't exist.

---

### [3] writeDossier / readPreviousDossier date filtering

```
✅ PASS: readPreviousDossier returns non-null
✅ PASS: prior dossier date = 2026-01-10
✅ PASS: prior dossier close price = 2930
✅ PASS: readPreviousDossier before earliest = null
✅ PASS: most recent prior to 2026-12-31 = FEB
```

**What was tested**: Two dossiers written (2026-01-10 and 2026-02-20).
- `readPreviousDossier("7203", "2026-02-20")` → returns JAN dossier (close=2930) ✓
- `readPreviousDossier("7203", "2026-01-10")` → returns null (nothing before earliest) ✓
- `readPreviousDossier("7203", "2026-12-31")` → returns FEB dossier (most recent prior to year-end) ✓

---

### [4] getArtifactIndex — hasJudgmentStore flag

```
✅ PASS: hasJudgmentStore = true after writeJudgment
✅ PASS: dossiers.length >= 2 (got 2)
✅ PASS: hasJudgmentStore = false for unknown ticker
✅ PASS: dossiers.length = 0 for unknown
```

**What was tested**: `ArtifactIndex` correctly reflects:
- `hasJudgmentStore: true` after `writeJudgment()` has been called
- `dossiers: ["7203-2026-01-10.json", "7203-2026-02-20.json"]` (2 files)
- Missing ticker returns `hasJudgmentStore: false`, `dossiers: []`

---

### [5] syncJudgmentStore — creates store from first Thesis

```
✅ PASS: store.ticker = 9984
✅ PASS: thesisCount = 1 after first sync
✅ PASS: stanceHistory.length = 1
✅ PASS: currentStance.stance = bullish
✅ PASS: recurringRisks.length = 2 (got 2)
✅ PASS: openQuestions.length >= 1
✅ PASS: syncJudgmentStore wrote to disk
✅ PASS: disk thesisCount = 1
```

**What was tested**: `syncJudgmentStore(thesis1)` on ticker=9984 with no pre-existing store.
Creates new `JudgmentStore`, populates `stanceHistory`, `recurringRisks`, `openQuestions`.
Verified the store was actually persisted to disk via `readJudgment()`.

---

### [6] syncJudgmentStore — stanceHistory accumulation + risk de-duplication

```
✅ PASS: thesisCount = 2 after second sync
✅ PASS: stanceHistory.length = 2
✅ PASS: currentStance updated to neutral
✅ PASS: newest stance first
✅ PASS: prior stance second
✅ PASS: repeated risk de-duplicated → occurrences = 2
✅ PASS: recurringRisks.length = 3 (2 new + 1 merged)
✅ PASS: openQuestions merged (got 3)
```

**What was tested**: Second `syncJudgmentStore(thesis2)` call on same ticker=9984.
- thesis2 has stance=neutral (was bullish) — stance change tracked correctly
- `stanceHistory` = [neutral(new), bullish(old)] — newest first ✓
- Risk "競合他社の価格競争が激化している" appears in both theses → `occurrences: 2` ✓
- 3 unique risk keys total (1 merged + 2 new from thesis2) ✓
- `openQuestions` merged from both theses (de-duplicated via Set) ✓

---

### [7] answerCompanyQuestion — intent detection (no LLM)

```
✅ PASS: intent = general for general question
✅ PASS: confidence = low when no dossier
✅ PASS: answer is not empty
✅ PASS: intent = diff for 変わ keyword
✅ PASS: intent = risk for リスク keyword
✅ PASS: intent = history for 過去 keyword
```

**What was tested**: `answerCompanyQuestion()` with ticker that has no dossier.
Returns "no data" response without calling LLM. Intent detection verified for all 4 paths:
- JP "変わ" → `"diff"` ✓
- JP "リスク" → `"risk"` ✓
- JP "過去" → `"history"` ✓
- Default → `"general"` ✓

---

### [8] answerCompanyQuestion — JudgmentStore integration path (no LLM)

```
✅ PASS: intent = risk for リスク question
✅ PASS: confidence = low (no dossier, JudgmentStore only)
✅ PASS: judgmentHistorySummary populated from JudgmentStore
✅ PASS: recurringRisks populated from JudgmentStore
✅ PASS: answer non-empty (LLM error or response)
```

**What was tested**: `answerCompanyQuestion()` for ticker=9984 which has a JudgmentStore
(written in tests [5]–[6]) but no dossier. Exercises the Layer 2 integration path:
- `readJudgment()` returns non-null → early-return condition NOT triggered
- `buildJudgmentStoreContext()` runs → `judgmentHistorySummary` populated ✓
- `recurringRisks` extracted from JudgmentStore (3 risks written in test [6]) ✓
- `confidence = "low"` (dossier=null, regardless of JudgmentStore availability) ✓
- LLM call fails (no API key in test env) → `answer` contains error message (non-empty) ✓

Note: This test **covers the gap** identified in audit — test [7] only exercised the
early-return path. Test [8] exercises the JudgmentStore context-building path.

---

## Build Verification (TypeScript)

```bash
bun run typecheck  # → bun tsc --noEmit -p tsconfig.json
```

Result: **0 TypeScript errors** across all 4 packages.

One pre-existing error was fixed as part of this session:
- `packages/adapters/src/edinet/client.ts:174` — double cast `doc as unknown as Record<string, unknown>`

---

## Coverage Gaps (Not Tested)

The following require live API credentials and cannot be smoke-tested locally:

| Component | Gap | Reason |
|-----------|-----|--------|
| `buildDossier()` | Adapter fetch | Requires J-Quants / Exa API keys |
| `buildThesis()` | LLM call | ✅ **Verified via Phase FV proof** — see section below |
| `compareCompanies()` | LLM call | ✅ **Verified via Phase FV proof** — see section below |
| `answerCompanyQuestion()` — LLM path | LLM call | Layer 2 integration tested (test [8]); LLM response not verifiable without `claude` CLI available |
| `runResearch()` agent | Multi-tool | Full agent loop, requires all of the above |

All code paths that don't require external credentials are covered by the 45 smoke tests above.

---

## Phase FV Proof — Claude Code CLI Backend (`tests/phase-fv-proof.ts`)

> Run: `bun tests/phase-fv-proof.ts`
> Date: 2026-03-28
> Backend: `claude -p --output-format json` (Claude Max OAuth, no `ANTHROPIC_API_KEY`)
> Result: **FV-11 ✅ DONE | FV-12 ✅ DONE**

```
=== Phase FV: Claude Code CLI Backend Proof ===

Backend: claude -p --output-format json (Claude Max OAuth, no ANTHROPIC_API_KEY)

[FV-11] buildThesis(mockDossier) — via claude -p CLI backend
  Calling buildThesis for 7203 (Toyota)...
  ✅ buildThesis returned ok(Thesis) in 40.1s
     id        = thesis-7203-1774673157118
     title     = トヨタ自動車：EV転換期における収益力と割安感の評価
     stance    = neutral
     conviction= low
     horizon   = medium
     catalysts = 5 items
     risks     = 5 items
     openQs    = 5 items
     body[0:80]= ## 投資テーゼ概要

トヨタ自動車は2025年3月期に売上高44.5兆円、純利益3.58兆円と過去最高水準の業績を達成した。PERは約9倍と日本の大型株の中で...
  → FV-11: ✅ DONE

[FV-12] compareCompanies([7203,9984]) — via claude -p CLI backend
  Note: compareCompanies() rebuilds dossiers internally via empty registry.
  Dossiers will be empty but LLM call path will be exercised.
  Calling compareCompanies for 7203 vs 9984...
  ✅ compareCompanies returned ok(CompareResult) in 31.0s
     targets      = 7203, 9984
     dossiers     = 2 built
     winner       = 7203
     rankings     = 7203, 9984
     judgDiffs    = 4 items
     pivotPoints  = 7203, 9984
     analysis[0:80]= ## バリュエーションと財務健全性の比較：トヨタ自動車(7203) vs ソフトバンクグループ(9984)

### バリュエーション
トヨタ(7203)はPE...
  → FV-12: ✅ DONE

=== Phase FV Summary ===
[FV-11] buildThesis       : ✅ DONE
[FV-12] compareCompanies  : ✅ DONE

Backend: claude -p --output-format json (Claude Max OAuth, no ANTHROPIC_API_KEY)
```

### Technical Notes

- **Backend**: `claude_code_backend.ts` using `Bun.spawn(["claude", "-p", prompt, ...])` directly (no `cmd /c`)
- **Windows fix**: `cmd /c` wrapper was removed — it split multiline prompts at `\n` boundaries on Windows, causing the model to receive only the first line
- **FV-11 prompt fix**: Added explicit JSON schema template to `builder.ts` prompt enforcing exact field names (`stance` not `direction`, `bullCase`/`bearCase` as plain strings not objects)
- **Authentication**: Claude Max OAuth via existing `~/.claude.json` session — no `ANTHROPIC_API_KEY` required

---

---

## Phase 5–6 Audit Re-run (2026-03-28)

```bash
# Command executed during Phase 5-6 audit
cd projects/equity-intelligence
bun run typecheck    # → 0 TypeScript errors
bun tests/smoke-walltalk.ts  # → 45/45 PASS, 0 FAIL
```

Re-run confirmed all results identical. No regressions introduced by doc drift fixes (D1–D5).

---

## Phase C Gap Closure Proof (`tests/phase-c-proof.ts`)

> Run: `bun run tests/phase-c-proof.ts`
> Date: 2026-03-28 (after Phase D fix to `buildThesis`)
> Result: **EXIT:0**

```
[1] buildDossier — empty registry (no API keys)
  ✅ buildDossier returned ok(Dossier)
     ticker=7203, market=JP
     security=undefined (no adapter)
     latestPrice=undefined (no adapter)
     incomeStatements.length=0  balanceSheets.length=0  recentFilings.length=0
     freshnessMetadata.securityFetched=false
     freshnessMetadata.latestPriceFetched=false
     priceDelta=undefined (no prior dossier)

[2] buildThesis — requires ANTHROPIC_API_KEY
  ⛔ buildThesis returned err: Anthropic API key not found

[3] compareCompanies — requires ANTHROPIC_API_KEY
  ⛔ compareCompanies returned err: Anthropic API key not found

[4] v1 Dossier (no freshnessMetadata/priceDelta/priorDossierDate) passes schema ✅
[4] v1 Thesis (no bullCase/bearCase/priorThesisId/stanceChanged/changeFromPrior) passes schema ✅

=== Phase C Summary ===
[1] buildDossier          : ✅ EXECUTED — partial dossier (empty adapters, no API keys)
[2] buildThesis           : ⛔ BLOCKED — ANTHROPIC_API_KEY not set (error returned as expected)
[3] compareCompanies      : ⛔ BLOCKED — ANTHROPIC_API_KEY not set (error returned as expected)
[4] backward compat       : ✅ VERIFIED — v1 Dossier + Thesis schema parse without v2 fields
[5] answerCompanyQuestion : ✅ PROVEN — smoke tests [7][8]: 4 intents (general/diff/risk/history)
[6] readJudgment/write    : ✅ PROVEN — smoke tests [1][2]: write→read round-trip
[7] readPreviousDossier   : ✅ PROVEN — smoke test [3]: date filtering 3 patterns
EXIT:0
```

---

## Current-Session Re-run (2026-03-28 — Session 3, Source-of-Truth Re-confirmation)

> Re-run date: 2026-03-28 (this session)
> Purpose: §2 source-of-truth compliance — commands re-executed in current Bash session, not relying on prior session logs.

```
bun run typecheck
  → EXIT:0  (0 TypeScript errors)

bun run tests/smoke-walltalk.ts
  → 45 tests, 45 passed, 0 failed  EXIT:0

bun run tests/phase-c-proof.ts
  → phase-c-proof [1][4] ✅  [2][3] ⛔ BLOCKED (ANTHROPIC_API_KEY)  EXIT:0
```

**Result**: All 3 commands match prior session. No regressions.

*Generated: 2026-03-28 — equity-intelligence Judgment Support OS v2 smoke test run (updated after audit: 40→45 tests, test [8] added; Phase C proof added)*
