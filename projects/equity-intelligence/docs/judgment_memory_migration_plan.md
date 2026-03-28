# Judgment Memory Migration Plan

> From: Legacy `FileJudgmentMemory` (markdown-based, Layer 1)
> To:   Structured `JudgmentStore` (JSON, Layer 2)
> Status: Layer 2 infrastructure complete — migration path documented

---

## Current State

### Legacy System (FileJudgmentMemory)

`FileJudgmentMemory` in `packages/services/src/judgment/memory.ts`:

- Reads thesis markdown files from disk
- Parses them as unstructured text
- Returns a markdown-formatted context string
- Used by `answerCompanyQuestion()` as "legacy judgment context"

**Limitations:**
- No structured stance history — must re-parse all thesis files
- No recurring risk de-duplication — same risk appears multiple times per thesis
- No open questions tracking — buried in thesis body text
- Query performance: O(n) scan of all thesis files per question
- Not machine-readable — LLM must parse markdown to extract structured data

### New System (JudgmentStore, Layer 2)

`JudgmentStore` in `output/walltalk/judgment/{ticker}-judgment.json`:

- Structured JSON artifact per ticker
- Maintained by `syncJudgmentStore()` after each `buildThesis()` call
- Includes: `stanceHistory`, `recurringRisks`, `openQuestions`, `lessons`, `crossRefs`
- O(1) lookup — single file read
- Directly usable by `answerCompanyQuestion()` without markdown parsing

---

## Migration Strategy

### Phase A: Parallel Running (Current State)

Both systems exist simultaneously. `answerCompanyQuestion()` uses this priority:

```
1. Read JudgmentStore via readJudgment() → Layer 2
2. If null → fallback to FileJudgmentMemory → Layer 1 (legacy)
3. If no data in either → return "no data" message
```

This ensures **zero breaking changes** for tickers that have not yet had
`syncJudgmentStore()` called on them.

### Phase B: Backfill (When Needed)

For tickers with existing thesis files but no JudgmentStore, a backfill script
can be run to create the initial Layer 2 store:

```typescript
// backfill-judgment-stores.ts (to be implemented)
import { readAllThesesForTicker } from "@equity/walltalk";
import { syncJudgmentStore } from "@equity/services";

const tickers = ["7203", "9984", "AAPL"];  // tickers with existing theses

for (const ticker of tickers) {
  const theses = await readAllThesesForTicker(ticker);  // sorted by createdAt
  for (const thesis of theses) {
    await syncJudgmentStore(thesis);
    console.log(`Synced: ${ticker} (${thesis.id})`);
  }
  console.log(`✅ ${ticker}: JudgmentStore created with ${theses.length} theses`);
}
```

**Order matters**: theses must be processed in chronological order (oldest first)
so that `stanceHistory` builds up correctly.

### Phase C: Forward-Only (Target State)

Once all tickers have JudgmentStore files:

1. Remove `FileJudgmentMemory` fallback from `answerCompanyQuestion()`
2. Deprecate `FileJudgmentMemory` class
3. Remove `legacyJudgmentContext` path

**Trigger condition**: When `hasJudgmentStore === true` for all tickers in `getArtifactIndex()`
for all tickers that have any thesis.

---

## Data Mapping: Thesis → JudgmentStore

When `syncJudgmentStore(thesis)` is called, it maps thesis fields:

| Source (Thesis) | Target (JudgmentStore) | Transform |
|----------------|------------------------|-----------|
| `id` | `stanceHistory[].thesisId` | Direct |
| `createdAt` | `stanceHistory[].date` | `slice(0, 10)` |
| `stance` | `stanceHistory[].stance` | Direct |
| `conviction` | `stanceHistory[].conviction` | Direct |
| `title` | `stanceHistory[].title` | Direct |
| `targetPrice` | `stanceHistory[].targetPrice` | Direct |
| `risks[].description` | `recurringRisks[].description` | De-duplication via `normalizeRiskKey()` |
| `risks[].category` | `recurringRisks[].category` | Direct |
| `risks[].severity` | `recurringRisks[].severity` | Max severity |
| `openQuestions` | `openQuestions` | Overwrite with latest |
| (derived) | `thesisCount` | Increment |
| (derived) | `currentStance` | Always = `stanceHistory[0]` (latest) |
| (derived) | `updatedAt` | `new Date().toISOString()` |

> **Note**: `stanceChanged` and `changeFromPrior` are `ThesisSchema` fields (set by `buildThesis()`). They are **not** copied into `StanceHistoryItem` — they remain on the Thesis object itself.

### Risk Normalization

`normalizeRiskKey(description)` creates a stable key for de-duplication:
1. Lowercase
2. Keep CJK characters (Japanese/Chinese text) as-is
3. Remove punctuation/special chars
4. Slice to 60 chars

Example: `"競合他社の価格競争が激化している"` → key `"競合他社の価格競争が激化している"` (same across theses)

This means the same risk mentioned in 3 different theses will be counted as 1 recurring risk
with `occurrences: 3`, rather than 3 separate entries.

---

## Dependency Graph

```
buildThesis()
  ↓ returns Thesis
syncJudgmentStore(thesis)
  ↓ calls readJudgment() — reads existing JudgmentStore
  ↓ merges data
  ↓ calls writeJudgment() — writes updated JudgmentStore
  ↓ returns updated JudgmentStore

answerCompanyQuestion()
  ↓ calls readJudgment() — reads JudgmentStore (Layer 2)
  ↓ if null: calls judgmentMemory.getJudgmentContext() (Layer 1 legacy)
  ↓ builds intent-aware context
  ↓ calls LLM
  ↓ returns WalltalkQueryResult with judgmentHistorySummary
```

---

## Required walltalk Functions Not Yet Implemented

For Phase B (backfill) to be possible, `@equity/walltalk` needs:

```typescript
// Lists all thesis files for a ticker, sorted by createdAt (oldest first)
export async function readAllThesesForTicker(ticker: string): Promise<Thesis[]>
```

This is straightforward — glob `output/walltalk/thesis/{ticker}-*.md`, parse each file,
sort by `createdAt`. Not critical for Phase A (current state) but required for Phase B.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `normalizeRiskKey()` maps different risks to same key | Low | Medium | Risk key uses first 60 chars — edge case for very similar risk descriptions |
| JudgmentStore gets out of sync if `buildThesis()` is called without `syncJudgmentStore()` | Medium | Low | `answerCompanyQuestion()` falls back to FileJudgmentMemory gracefully |
| Backfill processes theses out of order | Low | Medium | Backfill script must sort by `createdAt` before processing |
| Old `stanceHistory` items accumulate indefinitely | Low | Low | Consider truncating to last 20 entries in future |

---

*Generated: 2026-03-28 — equity-intelligence judgment memory migration plan*
