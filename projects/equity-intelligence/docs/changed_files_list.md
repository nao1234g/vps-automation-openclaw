# Changed Files List — Judgment Support OS v2

> Session: 2026-03-28 (RIGHT Architecture + Judgment Support OS upgrade + Phase C/D gap closure + CLI backend migration)
> Total modified/created files: 9 (packages) + 7 (docs) + 2 (tests)

---

## Package Changes

### 1. `packages/domain/src/schemas/index.ts`
**Type**: Modified (extended)

Added 7 new Zod schemas and extended 2 existing schemas:

**New schemas added:**
- `FreshnessMetadataSchema` — structured data quality metadata (fetchedAt, securityFetched, latestPriceFetched, incomeStatementsCount, balanceSheetsCount, recentFilingsCount, newsItemsCount, summaryGenerated, priceDate)
- `PriceDeltaSchema` — price change vs prior dossier (priorPrice, currentPrice, priorDate, currentDate, changeAbsolute, changePercent, currency)
- `StanceHistoryItemSchema` — single stance snapshot (thesisId, date, stance, conviction, title?, targetPrice?)
- `RecurringRiskSchema` — risk tracking across theses (description, category, severity, occurrences, firstSeen, lastSeen)
- `LessonSchema` — learned lessons (extractedAt, thesisId, lesson, category?)
- `JudgmentCrossRefSchema` — cross-ticker references (ticker, market, relationship, addedAt)
- `JudgmentStoreSchema` — main Layer 2 artifact (ticker, market, updatedAt, stanceHistory, currentStance, recurringRisks, openQuestions, lessons, crossRefs, thesisCount)

**Extended schemas:**
- `DossierSchema` — added optional `freshnessMetadata`, `priorDossierDate`, `priceDelta` fields
- `ThesisSchema` — added optional `openQuestions[]`, `bullCase`, `bearCase`, `invalidationPoints`, `priorThesisId`, `stanceChanged`, `changeFromPrior` fields

---

### 2. `packages/walltalk/src/index.ts`
**Type**: Modified (extended)

Added 3 new functions and updated 1 existing:

**New functions:**
- `writeJudgment(store: JudgmentStore): Promise<string>` — writes to `{dir}/judgment/{ticker}-judgment.json`; creates parent dir if needed
- `readJudgment(ticker: string): Promise<JudgmentStore | null>` — returns null on not-found/parse error (never throws)
- `readPreviousDossier(ticker: string, beforeDate: string): Promise<Dossier | null>` — finds most recent dossier with date < beforeDate (string comparison, YYYY-MM-DD format)

**Updated:**
- `getArtifactIndex(ticker)` — added `hasJudgmentStore: boolean` field; checks for `{ticker}-judgment.json` existence

---

### 3. `packages/services/src/judgment/store.ts`
**Type**: NEW FILE

Created new module for JudgmentStore maintenance logic:

- `syncJudgmentStore(thesis: Thesis): Promise<JudgmentStore>` — reads existing store, merges new thesis data (stanceHistory, recurringRisks, openQuestions), writes back
- `mergeRecurringRisks(existing, newRisks, date): RecurringRisk[]` — de-duplicates via normalizeRiskKey(); increments occurrences; takes max severity
- `normalizeRiskKey(description: string): string` — lowercase + keep CJK (u3040-u9fff) + remove punctuation + slice 60 chars

---

### 4. `packages/services/src/dossier/builder.ts`
**Type**: Modified (extended)

- Added `freshnessMetadata` computation — counts income statements, price history, extracts latestFiling from adapters' fetch results
- Added `priceDelta` computation — calls `readPreviousDossier()` before fetching current price; computes `changePercent` relative to prior dossier's close price
- Both fields returned as optional fields in the `Dossier` result

---

### 5. `packages/services/src/llm/claude_code_backend.ts`
**Type**: NEW FILE (CLI backend migration — 2026-03-28)

Created new internal LLM backend module replacing `@langchain/anthropic`:

- `callClaudeText(userPrompt, systemPrompt?)` — calls `claude -p` CLI and returns raw text
- `callClaudeJson<T>(userPrompt, opts?)` — calls `claude -p` and parses JSON response
- `spawnClaude(prompt)` — internal subprocess helper using `Bun.spawn`
- `stripFences(raw)` — strips ` ```json ` / ` ``` ` markdown fences from CLI output

**Key design points:**
- Uses Claude Max OAuth (no ANTHROPIC_API_KEY required)
- Windows: spawns `["claude", "-p", prompt, ...]` directly via `Bun.spawn` — **no `cmd /c` wrapper** (cmd /c splits multiline prompts at `\n` boundaries, causing model to receive only the first line; removed 2026-03-28)
- TypeScript: `/// <reference types="bun-types" />` + `as ReadableStream<Uint8Array>` cast
- Returns `Result<T>` (never throws)

**Not exported** from `@equity/services` public index (internal use only).

---

### 5b. `packages/services/src/thesis/builder.ts`
**Type**: Modified (extended + Phase D bug fix + CLI migration)

**Phase D fix (2026-03-28 audit)**: Moved `new ChatAnthropic(...)` constructor call inside the
try-catch block so that the "Anthropic API key not found" error is returned as `err(...)` rather
than propagating as an unhandled thrown exception. This makes `buildThesis()` consistent with
`compareCompanies()` which already handled the error correctly.

**CLI migration (2026-03-28)**: Replaced `@langchain/anthropic` with `callClaudeJson` from
`claude_code_backend.ts`. `buildThesis()` and `extractRisks()` now use Claude Max OAuth.

Added first-class LLM output fields to `Thesis`:

- `openQuestions[]` — unresolved questions surfaced by LLM (previously buried in `body` text)
- `bullCase` / `bearCase` — structured bull/bear scenario arguments
- `invalidationPoints[]` — conditions that would invalidate the thesis
- `priorThesisRef` input option — if provided, passed to LLM prompt; LLM fills `changeFromPrior` summary
- `stanceChanged` — boolean, true if stance differs from `priorThesisRef.stance`

---

### 6. `packages/services/src/compare/index.ts`
**Type**: Modified (extended + CLI migration)

**CLI migration (2026-03-28)**: Replaced `@langchain/anthropic` with `callClaudeText` from
`claude_code_backend.ts`. `compareCompanies()` now uses Claude Max OAuth.

Added 2 new fields to `ComparisonResult`:

- `judgmentDifferences` — structured comparison of JudgmentStore data between tickers (stance divergence, risk overlap, openQuestion differences)
- `pivotPoints` — key inflection points where thesis diverged between the two tickers

---

### 7. `packages/services/src/index.ts`
**Type**: Modified (export added)

Added export:
```typescript
export { syncJudgmentStore } from "./judgment/store.js";
```

---

### 8. `packages/services/src/query/walltalk.ts`
**Type**: Modified (complete rewrite)

Complete rewrite of the query layer with intent awareness:

- `detectIntent(question: string): QuestionIntent` — keyword-based intent detection for JP and EN keywords
  - `"diff"`: 違う/変わ/前回/比べ/changed/differ/update/vs
  - `"risk"`: リスク/懸念/問題/risk/concern/downside
  - `"history"`: 過去/以前/履歴/history/past/previous
  - `"general"`: default
- `buildDossierContext(dossier, maxLen, intent)` — assembles Dossier financial context prioritizing fields based on intent (priceDelta, analystNotes, financials); JudgmentStore context assembled separately via `buildJudgmentStoreContext(store, intent)`:
  - `"diff"` → priceDelta prominently; stanceHistory (4 entries) from JudgmentStore
  - `"risk"` → 5 recurringRisks (instead of 3) from JudgmentStore
  - `"history"` → full stanceHistory trajectory from JudgmentStore
  - `"general"` → 3 recurringRisks, currentStance from JudgmentStore
- Updated `WalltalkQueryResult` — added `intentDetected`, `judgmentHistorySummary`, `recurringRisks`
- Added Layer 2 fallback: reads `JudgmentStore` first; falls back to legacy `FileJudgmentMemory` if null

---

## Documentation Created

| File | Description |
|------|-------------|
| `docs/memory_architecture_report.md` | 3-layer memory architecture design and Layer 1/2/3 definitions |
| `docs/artifact_memory_inventory.md` | All artifact types, file paths, schemas, field listing |
| `docs/walltalk_judgment_interface_report.md` | walltalk v2 judgment read/write API reference |
| `docs/judgment_memory_migration_plan.md` | Migration plan: FileJudgmentMemory (Layer 1) → JudgmentStore (Layer 2) |
| `docs/implementation_handoff.md` | Workflow, API surface, per-feature explanations, remaining work |
| `docs/test_results.md` | Smoke test results (45/45 PASS) |
| `docs/claude_runtime_path_decision.md` | Architecture Decision Record: LangChain → `claude -p` CLI backend migration |
| `docs/changed_files_list.md` | This file |

---

## Tests Created

| File | Description |
|------|-------------|
| `tests/smoke-walltalk.ts` | 45 smoke tests covering all new walltalk/judgment functions (no LLM required) |
| `tests/phase-c-proof.ts` | Phase C Gap Closure proof script — demonstrates buildDossier (partial, no adapters), buildThesis/compareCompanies (BLOCKED → err(), ANTHROPIC_API_KEY absent), backward compat schema checks (v1 Dossier + Thesis parse without v2 fields). EXIT:0 confirmed 2026-03-28. |
| `tests/phase-fv-proof.ts` | Phase FV CLI Backend proof — FV-11: `buildThesis(mockDossier)` → ok(Thesis) in 40.1s via `claude -p`; FV-12: `compareCompanies([7203,9984])` → ok(CompareResult) in 31.0s. Both confirmed 2026-03-28. EXIT:0. |

---

## Files NOT Modified

- `packages/adapters/` — unchanged; data fetching layer untouched
- `packages/services/src/research/agent.ts` — `runResearch()` agent API unchanged
- `packages/services/src/session/` — session handling unchanged
- `packages/services/src/screener/` — screener unchanged
- `packages/walltalk/package.json` — no new dependencies required

---

*Generated: 2026-03-28 — equity-intelligence Judgment Support OS v2 changed files*
