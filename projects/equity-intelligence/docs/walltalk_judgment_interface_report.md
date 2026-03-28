# Walltalk Judgment Interface Report

> Describes the judgment read/write interface in `@equity/walltalk`
> and how services layer consumes it.
> Version: 2.0 (2026-03-28)

---

## Overview

The `@equity/walltalk` package defines the **file boundary** for all equity research artifacts.
It is a pure I/O layer — no LLM calls, no external API calls, only file read/write.

The v2 upgrade adds **JudgmentStore** as a new first-class artifact, enabling structured
judgment memory to persist and accumulate across multiple research sessions.

---

## New Functions (v2)

### `writeJudgment(store: JudgmentStore): Promise<void>`

Writes a `JudgmentStore` to disk.

- **Path**: `{WALLTALK_OUTPUT_DIR}/judgment/{ticker}-judgment.json`
- **Behavior**: Creates parent directory if not exists; overwrites existing file
- **Idempotent**: Writing the same store twice produces the same file

```typescript
import { writeJudgment } from "@equity/walltalk";
import type { JudgmentStore } from "@equity/domain";

const store: JudgmentStore = { /* ... */ };
await writeJudgment(store);
```

---

### `readJudgment(ticker: string): Promise<JudgmentStore | null>`

Reads the `JudgmentStore` for a given ticker.

- **Returns**: `JudgmentStore` if file exists and is valid JSON, `null` if not found
- **Does not throw**: Returns `null` on any file/parse error
- **Used by**: `syncJudgmentStore()`, `answerCompanyQuestion()`

```typescript
import { readJudgment } from "@equity/walltalk";

const store = await readJudgment("7203");
if (store) {
  console.log(`${store.ticker}: ${store.thesisCount} theses, stance: ${store.currentStance?.stance}`);
}
```

---

### `readPreviousDossier(ticker: string, beforeDate: string): Promise<Dossier | null>`

Reads the most recent `Dossier` written **before** `beforeDate`.

- **beforeDate**: ISO date string `"YYYY-MM-DD"` (exclusive upper bound)
- **Returns**: Most recent dossier with `createdAt < beforeDate`, or `null` if none exists
- **Used by**: `buildDossier()` to compute `priceDelta`

```typescript
import { readPreviousDossier } from "@equity/walltalk";

const today = new Date().toISOString().slice(0, 10);
const priorDossier = await readPreviousDossier("7203", today);
if (priorDossier?.latestPrice) {
  const priorPrice = priorDossier.latestPrice.close;
  // compute price delta...
}
```

---

### Updated: `getArtifactIndex(ticker: string): Promise<ArtifactIndex>`

Now checks for JudgmentStore existence.

```typescript
interface ArtifactIndex {
  ticker: string;
  dossiers: string[];           // filenames of all dossiers (sorted by date)
  theses: string[];             // filenames of all theses
  hasJudgmentStore: boolean;    // true if judgment/{ticker}-judgment.json exists
}
```

---

## Services Layer: `syncJudgmentStore()`

The services layer (`@equity/services`) provides `syncJudgmentStore(thesis)` which
reads a `JudgmentStore` via `readJudgment()`, merges new thesis data, and writes via `writeJudgment()`.

**Typical usage after building a thesis:**

```typescript
import { buildDossier, buildThesis, syncJudgmentStore } from "@equity/services";

// 1. Build dossier
const dossierResult = await buildDossier("7203", "TSE", registry);
if (!dossierResult.ok) throw dossierResult.error;

// 2. Build thesis (optionally with prior thesis reference)
const thesisResult = await buildThesis(dossierResult.data, {
  priorThesisRef: {
    thesisId: "thesis-7203-1234567890",
    stance: "neutral",
    conviction: "medium",
    title: "Previous thesis title",
    createdAt: "2026-01-15T10:00:00Z",
  },
});
if (!thesisResult.ok) throw thesisResult.error;

// 3. Sync judgment store — accumulates stance history, recurring risks
const judgmentStore = await syncJudgmentStore(thesisResult.data);
console.log(`JudgmentStore updated: ${judgmentStore.thesisCount} theses`);
```

---

## Q&A Interface: `answerCompanyQuestion()`

Consumes both Layer 1 (Dossier) and Layer 2 (JudgmentStore) for intent-aware Q&A.

**Return type additions:**

```typescript
interface WalltalkQueryResult {
  answer: string;
  sources: string[];
  confidence: "low" | "medium" | "high";
  generatedAt: string;
  dossierDate?: string;
  intentDetected: QuestionIntent;         // NEW: "diff" | "risk" | "history" | "general"
  judgmentHistorySummary?: string;        // NEW: formatted Layer 2 context used
  recurringRisks?: Array<{               // NEW: top recurring risks from JudgmentStore
    description: string;
    severity: string;
    occurrences: number;
  }>;
}
```

**Example with judgment context:**

```typescript
import { answerCompanyQuestion } from "@equity/services";

const result = await answerCompanyQuestion("7203", "過去の判断と比べて何が違う？");
console.log(result.intentDetected);         // "history"
console.log(result.judgmentHistorySummary); // formatted stance progression
console.log(result.recurringRisks);         // [{description: "...", severity: "high", occurrences: 3}]
console.log(result.answer);                 // LLM answer using Layer 1 + 2 context
```

---

## Judgment Context Building Logic

When `intent === "history"` or `intent === "diff"`:
- Shows `stanceHistory` trajectory (last 4 entries)
- Format: `"2026-01-15: neutral(medium) → 2026-02-20: bullish(high)"`

When `intent === "risk"` or `intent === "general"`:
- Shows `recurringRisks` (top 3)
- Format: `"[high×3] 競合他社の価格競争が激化"`

Always shown (if present):
- `currentStance` (stance + conviction + targetPrice + date)
- `openQuestions` (up to 3 questions)
- `thesisCount`

---

## File Structure Conventions

```
output/walltalk/
  dossier/
    7203-2026-01-15.json      ← daily snapshot
    7203-2026-02-20.json      ← newer snapshot
  thesis/
    7203-thesis-7203-1706000000.md
  judgment/
    7203-judgment.json         ← single file per ticker, updated in-place
  session/
    session-2026-01-15T10.json
  screener/
    screener-2026-01-15T10.json
```

**Note on JudgmentStore naming**: `{ticker}-judgment.json` — always one file per ticker,
mutated in place by `syncJudgmentStore()`. This is different from dossier (date-versioned).

---

## Error Handling Pattern

All walltalk functions follow the same pattern:

```typescript
// Read functions: return null on not-found or parse error (never throw)
const store = await readJudgment("9999");   // → null if file doesn't exist

// Write functions: throw on I/O error (caller should catch)
try {
  await writeJudgment(store);
} catch (e) {
  // handle I/O error
}
```

In `answerCompanyQuestion()`, judgment reads are wrapped in try/catch and treated
as optional enrichment — the answer still returns even if judgment reads fail.

---

*Generated: 2026-03-28 — walltalk v2 judgment interface documentation*
