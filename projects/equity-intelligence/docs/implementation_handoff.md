# Implementation Handoff — Judgment Support OS Upgrade

> Session: 2026-03-28 (RIGHT Architecture + Judgment Support OS upgrade + Phase C/D audit closure + Phase FV LLM proof)
> Status: Phase 5–6 audit closed. typecheck 0 errors, smoke 45/45 PASS, phase-c-proof EXIT:0. Phase FV proof EXIT:0 (FV-11 + FV-12 ✅ DONE).
> **Overall Verdict: PARTIAL** — LLM core paths (`buildThesis`, `compareCompanies`) confirmed via Phase FV proof. External-API-dependent paths (`buildDossier` real data, `runResearch`) remain PARTIAL.
> All code paths that do not require external credentials are verified and DONE.

---

## What Was Built

This session upgraded equity-intelligence from a "research capture" tool into a
**Judgment Support OS** capable of reusing past judgment knowledge across sessions.

### Files Modified

| File | Change | Status |
|------|--------|--------|
| `packages/domain/src/schemas/index.ts` | Added 7 new Zod schemas; extended Dossier + Thesis | ✅ Complete |
| `packages/walltalk/src/index.ts` | Added `writeJudgment`, `readJudgment`, `readPreviousDossier`; updated ArtifactIndex | ✅ Complete |
| `packages/services/src/judgment/store.ts` | NEW: `syncJudgmentStore()`, `mergeRecurringRisks()` | ✅ Complete |
| `packages/services/src/dossier/builder.ts` | Added `freshnessMetadata`, `priceDelta` computation and return | ✅ Complete |
| `packages/services/src/llm/claude_code_backend.ts` | **NEW**: Claude Code CLI backend — `callClaudeText`, `callClaudeJson`. Uses `claude -p` with Claude Max OAuth. No ANTHROPIC_API_KEY. | ✅ Complete |
| `packages/services/src/thesis/builder.ts` | Added `openQuestions`, `bullCase`, `bearCase`, `invalidationPoints`, `priorThesisRef`; **Phase D fix** + **CLI migration**: replaced `ChatAnthropic` with `callClaudeJson` | ✅ Complete |
| `packages/services/src/compare/index.ts` | Added `judgmentDifferences`, `pivotPoints` fields; **CLI migration**: replaced `ChatAnthropic` with `callClaudeText` | ✅ Complete |
| `packages/services/src/index.ts` | Added `syncJudgmentStore` export | ✅ Complete |
| `packages/services/src/query/walltalk.ts` | Complete rewrite: intent detection, Layer 2 context | ✅ Complete |

### Docs Created

| File | Description |
|------|-------------|
| `docs/memory_architecture_report.md` | 3-layer memory architecture design |
| `docs/artifact_memory_inventory.md` | All artifact types, paths, schemas, field listing |
| `docs/walltalk_judgment_interface_report.md` | walltalk judgment read/write API reference |
| `docs/judgment_memory_migration_plan.md` | Migration path from FileJudgmentMemory to JudgmentStore |
| `docs/claude_runtime_path_decision.md` | ADR: LangChain → `claude -p` CLI backend migration |
| `docs/implementation_handoff.md` | This file |

---

## New Public API Surface

### `@equity/services` new exports

```typescript
// JudgmentStore — structured Layer 2 judgment memory (read/write)
export { syncJudgmentStore } from "./judgment/store.js";

// WalltalkQuery now returns intent + judgment context
export type { WalltalkQueryOptions, WalltalkQueryResult } from "./query/walltalk.js";

// Note: QuestionIntent is exported from @equity/services/query/walltalk.ts
// but is NOT re-exported from @equity/services top-level index.
// Import directly: import type { QuestionIntent } from "@equity/services/query/walltalk.js"
```

### `@equity/walltalk` new exports

```typescript
export { writeJudgment, readJudgment, readPreviousDossier } from "./index.js";
```

### `@equity/domain` new types

```typescript
export type {
  FreshnessMetadata,
  PriceDelta,
  StanceHistoryItem,
  RecurringRisk,
  Lesson,
  JudgmentCrossRef,
  JudgmentStore,
} from "./schemas/index.js";
```

---

## Typical Workflow (Post-Upgrade)

```typescript
import { buildDossier, buildThesis, syncJudgmentStore, answerCompanyQuestion } from "@equity/services";
import { writeDossier, writeThesis } from "@equity/walltalk";

// 1. Build and save dossier
const dossierResult = await buildDossier("7203", "TSE", registry);
if (!dossierResult.ok) return;
await writeDossier(dossierResult.data);

// 2. Build thesis (reference prior if available)
const thesisResult = await buildThesis(dossierResult.data, {
  language: "ja",
  priorThesisRef: priorThesis ? {
    thesisId: priorThesis.id,
    stance: priorThesis.stance,
    conviction: priorThesis.conviction,
    title: priorThesis.title,
    createdAt: priorThesis.createdAt,
  } : undefined,
});
if (!thesisResult.ok) return;
await writeThesis(thesisResult.data);

// 3. Sync judgment store (accumulates stance history + recurring risks)
const judgmentStore = await syncJudgmentStore(thesisResult.data);
console.log(`JudgmentStore: ${judgmentStore.thesisCount} theses, stance: ${judgmentStore.currentStance?.stance}`);

// 4. Answer questions using judgment-aware context
const qa = await answerCompanyQuestion("7203", "過去と比べて何が変わった？");
console.log(qa.intentDetected);   // "diff"
console.log(qa.answer);           // uses priceDelta + stanceHistory in context
```

---

## What Each New Feature Does

### `priceDelta` in Dossier
- Automatically computes price change vs the most recent prior dossier
- Surfaced prominently in Q&A when intent is "diff"
- Requires prior dossier to exist in `output/walltalk/dossier/` — no error if absent

### `freshnessMetadata` in Dossier
- Structured version of what was previously embedded as text in `analystNotes`
- Allows programmatic inspection of data quality without parsing markdown
- Useful for filtering dossiers: `if (dossier.freshnessMetadata.incomeStatementsCount === 0) skip()`

### `openQuestions/bullCase/bearCase/invalidationPoints` in Thesis
- First-class LLM output — not buried in `body` text
- `invalidationPoints` is especially useful: "if X happens, this thesis is wrong"
- `changeFromPrior` summarizes what changed when `priorThesisRef` is provided

### `JudgmentStore` per ticker
- Single JSON file per ticker, updated in-place after each thesis
- `stanceHistory` shows how your view evolved over time
- `recurringRisks` de-duplicates and counts risk frequency across theses
- `openQuestions` always reflects the latest thesis's unresolved questions

### Intent-aware `answerCompanyQuestion()`
- Detects question type from JP/EN keywords
- Routes context assembly differently per intent
- "diff" → surfaces priceDelta and stance changes prominently
- "risk" → surfaces more risks (5 instead of 3) and recurringRisks
- "history" → surfaces full stanceHistory trajectory
- Returns `intentDetected`, `judgmentHistorySummary`, `recurringRisks` in result

---

## Remaining Work (Not Implemented)

### Phase 5: FileJudgmentMemory deprecation (optional)
Once all tickers have JudgmentStore files (via `syncJudgmentStore()`):
1. Remove `legacyJudgmentContext` fallback from `answerCompanyQuestion()`
2. Remove `FileJudgmentMemory` import

### Backfill script (optional)
`readAllThesesForTicker(ticker)` function not yet in walltalk — needed for
processing existing thesis archives into JudgmentStore format.

### `runResearch()` integration (optional)
The research agent (`packages/services/src/research/agent.ts`) does not yet
call `syncJudgmentStore()` after thesis generation. This would need to be
added to the agent's post-thesis tool call.

### Tests
`projects/equity-intelligence/tests/smoke-walltalk.ts` — 45 smoke tests (45/45 PASS).
`projects/equity-intelligence/tests/phase-c-proof.ts` — Phase C gap closure proof (EXIT:0, 2026-03-28).
`projects/equity-intelligence/tests/phase-fv-proof.ts` — Phase FV CLI backend proof (EXIT:0, 2026-03-28): FV-11 buildThesis ✅, FV-12 compareCompanies ✅.
All code paths that don't require external credentials are covered.

Integration tests (require live API credentials — not yet written):
- `buildDossier()` — J-Quants / Exa adapter fetch (🟡 PARTIAL: empty dossier confirmed, real adapter data not tested)
- `buildThesis()` / `compareCompanies()` — ✅ DONE via Phase FV proof: `bun tests/phase-fv-proof.ts` — FV-11 ok(Thesis) in 40.1s, FV-12 ok(CompareResult) in 31.0s
- `runResearch()` agent — full multi-tool loop (not yet tested)

---

## Known Constraints

1. **No breaking changes** — All new fields added as optional; existing code continues to work
2. **Claude Max only** — All LLM calls use `claude-opus-4-6` via Claude Code CLI (`claude -p`); no ANTHROPIC_API_KEY required, no pay-per-use billing
3. **No adapters modified** — `@equity/adapters` unchanged; only service + domain + walltalk affected
4. **`runResearch()` untouched** — Research agent API unchanged; no risk to existing agent flows

---

## Build Verification Checklist

```bash
# From monorepo root
cd projects/equity-intelligence

# Type check all packages
bun run typecheck

# Or check individually
cd packages/domain && bun tsc --noEmit
cd packages/walltalk && bun tsc --noEmit
cd packages/services && bun tsc --noEmit
```

**Expected**: Zero TypeScript errors across all packages.

---

---

## Phase 5–6 Audit Closure Record (2026-03-28) — 4-Layer Verification

> **4-Layer Verification Model:**
> - **VE (Verification Execution)**: コマンドが走り exit code が記録されたか。phase-c-proof.ts EXIT:0 は VE DONE であり FV DONE ではない。
> - **IV (Implementation Verification)**: コードが安全に動作するか（err() 返却 / 0 errors / テスト PASS）。buildThesis() → err() は IV DONE であり FV DONE ではない。
> - **FV (Functional Verification)**: 元の要件機能が end-to-end で実行完了するか。CLI backend 実装済みだが未実行の場合は PARTIAL になる。
> - **OV (Overall Verdict)**: FV 結果のみに基づいて判定する。VE/IV の DONE は OV を COMPLETE にしない。

### Verification Execution (VE)

| Command | Exit Code | VE Status |
|---|---|---|
| `bun run typecheck` | 0 | ✅ VE DONE |
| `bun run tests/smoke-walltalk.ts` | 0 | ✅ VE DONE |
| `bun run tests/phase-c-proof.ts` | 0 | ✅ VE DONE |

### Implementation Verification (IV)

| Verification | Status | Evidence |
|---|---|---|
| TypeScript typecheck 0 errors | ✅ IV DONE | tsc --noEmit output empty |
| Smoke tests 45/45 PASS | ✅ IV DONE | smoke stdout: 45 passed, 0 failed |
| `buildDossier()` returns ok() without throw | ✅ IV DONE | phase-c-proof [1] |
| `buildThesis()` CLI backend → err() on spawn failure | ✅ IV DONE | claude_code_backend.ts: spawnClaude returns err() on exit code ≠ 0 |
| `compareCompanies()` CLI backend → err() on spawn failure | ✅ IV DONE | claude_code_backend.ts: same spawnClaude error path |
| v1 backward compat (fixture safeParse) | ✅ IV DONE | phase-c-proof [4] |
| answerCompanyQuestion() 4 intents | ✅ IV DONE | smoke [7][8] |
| writeJudgment/readJudgment round-trip | ✅ IV DONE | smoke [1][2] |
| readPreviousDossier date filtering | ✅ IV DONE | smoke [3] |
| callClaudeJson/callClaudeText never throws | ✅ IV DONE | claude_code_backend.ts: all paths return Result<T> |

### Functional Verification (FV)

| Requirement | FV Status | Evidence / Blocker |
|---|---|---|
| `buildDossier()` 1件実行 | 🟡 FV PARTIAL | ok() 返却だが全アダプタ空 — 実データなし |
| `buildThesis()` 1件 Thesis 生成 | ✅ FV DONE | `bun tests/phase-fv-proof.ts` FV-11 — ok(Thesis) in 40.1s (2026-03-28) |
| `compareCompanies()` 1件比較実行 | ✅ FV DONE | `bun tests/phase-fv-proof.ts` FV-12 — ok(CompareResult) in 31.0s (2026-03-28) |
| 実 artifact backward compat | 🟡 FV PARTIAL | output/ ディレクトリ不在 — fixture のみで検証 |

### Overall Verdict (OV)

**PARTIAL** — FV に PARTIAL 2件が残存する（`buildDossier()` 実アダプタ未接続・実 artifact backward compat 未検証）。LLM コアパス（`buildThesis()` / `compareCompanies()`）は Phase FV proof で DONE に昇格済み。VE 全 DONE・IV 全 DONE・FV 2 DONE で OV は COMPLETE に届かない — FV PARTIAL が 1 件でも残る限り COMPLETE にしない。

| Axis | DONE | PARTIAL | BLOCKED | PENDING | Total |
|------|------|---------|---------|---------|-------|
| VE | 3 | 0 | 0 | 0 | 3 |
| IV | 10 | 0 | 0 | 0 | 10 |
| FV | 2 | 2 | 0 | 0 | 4 |
| DR | 3 | 0 | 0 | 0 | 3 |
| **Total** | **18** | **2** | **0** | **0** | **20** |

*Handoff document — 2026-03-28 (updated: Phase 5–6 audit closure + Phase FV LLM proof) — equity-intelligence Judgment Support OS v2*
