# Memory Architecture Report — equity-intelligence Judgment Support OS

> Designed: 2026-03-28
> Status: Phase 2 design complete, Phase 3–4 service implementation complete

---

## Executive Summary

The equity-intelligence system has been upgraded from a "research capture" tool
into a **Judgment Support OS**. The key distinction:

- **Before**: "保存できる" (can save) — artifacts written to disk, rarely reused
- **After**: "再利用できる" (can reuse) — each research session builds on prior judgment history

This upgrade introduces a **3-layer Memory Architecture** and a suite of enhancements
to DossierBuilder, ThesisBuilder, CompareCompanies, and the WalltalkQuery Q&A interface.

---

## 3-Layer Memory Architecture

### Layer 1 — Artifact Memory (File-Based)

Managed by `@equity/walltalk` package. Pure file I/O, no LLM, no side effects.

| Artifact | Path Pattern | Schema | Write Function | Read Function |
|----------|-------------|--------|----------------|---------------|
| Dossier | `output/walltalk/dossier/{ticker}-{YYYY-MM-DD}.json` | `DossierSchema` | `writeDossier()` | `readDossier()`, `readPreviousDossier()` |
| Thesis | `output/walltalk/thesis/{ticker}-{id}.md` | `ThesisSchema` | `writeThesis()` | — |
| Session | `output/walltalk/session/{id}.json` | `SessionSchema` | `writeSession()` | — |
| Screener | `output/walltalk/screener/{id}.json` | `ScreenerSchema` | `writeScreenerResult()` | — |
| **JudgmentStore** | `output/walltalk/judgment/{ticker}-judgment.json` | `JudgmentStoreSchema` | `writeJudgment()` | `readJudgment()` |

**Key addition**: `JudgmentStore` is the new Layer 2 artifact — a ticker-level structured
summary of all past theses, updated automatically via `syncJudgmentStore()`.

### Layer 2 — Judgment Memory (Structured, Per-Ticker)

`JudgmentStore` is built from the cumulative stream of theses for a single ticker.
It is the most important new artifact — enabling the Q&A system to answer
"what changed?" and "what recurring risks exist?" without re-processing all old theses.

```typescript
interface JudgmentStore {
  ticker: string;
  market: Market;
  updatedAt: string;           // ISO datetime of most recent sync
  thesisCount: number;         // Total theses ever written for this ticker

  currentStance: StanceHistoryItem | null;   // Most recent investment stance
  stanceHistory: StanceHistoryItem[];         // Full chronological stance progression

  recurringRisks: RecurringRisk[];  // De-duplicated risks, sorted by frequency
  lessons: Lesson[];                 // Key takeaways from resolved stance changes
  openQuestions: string[];          // Open questions from most recent thesis

  crossRefs: JudgmentCrossRef[];   // Links to related tickers
}
```

**Data flow**: `buildThesis()` → `syncJudgmentStore(thesis)` → `JudgmentStore` updated in-place.

### Layer 3 — Walltalk Context Memory (On-The-Fly Assembly)

Not persisted. Assembled at Q&A time by `answerCompanyQuestion()`:

1. Reads latest `Dossier` from Layer 1
2. Reads `JudgmentStore` from Layer 2
3. Falls back to `FileJudgmentMemory` (markdown-based, legacy) if no Layer 2 store
4. Detects question intent (diff / risk / history / general)
5. Assembles intent-specific context string → LLM → structured answer

---

## Intent Detection & Routing

`answerCompanyQuestion()` classifies incoming questions into 4 intents:

| Intent | Trigger Keywords (JP) | Trigger Keywords (EN) | Context Emphasis |
|--------|----------------------|----------------------|-----------------|
| `diff` | 違う、変わ、前回、比べ | changed, differ, update, vs | `priceDelta`, `stanceHistory` |
| `risk` | リスク、懸念、弱み | risk, concern, downside | Top 5 risks, `recurringRisks` |
| `history` | 過去、履歴、判断、テーゼ | history, past, thesis | `stanceHistory` trajectory |
| `general` | (default) | (default) | Balanced context |

---

## New Schema Fields (Phase 3)

### Dossier additions

```typescript
freshnessMetadata?: FreshnessMetadata  // Structured data-fetch audit trail
priorDossierDate?: string              // ISO date of prior dossier for diff comparison
priceDelta?: PriceDelta                // Price change vs prior dossier
```

### Thesis additions

```typescript
openQuestions: string[]               // 2–4 questions that could change the thesis
bullCase?: string                     // Strongest bull case (1–2 sentences)
bearCase?: string                     // Strongest bear case (1–2 sentences)
invalidationPoints: string[]          // 2–3 conditions that would invalidate the thesis
priorThesisId?: string                // Reference to prior thesis for change tracking
stanceChanged?: boolean               // Whether stance changed vs prior thesis
changeFromPrior?: string              // LLM-generated description of what changed
```

### WalltalkQueryResult additions

```typescript
intentDetected: QuestionIntent        // Detected intent of the question
judgmentHistorySummary?: string       // Formatted Layer 2 judgment context
recurringRisks?: Array<{              // Top recurring risks from JudgmentStore
  description: string;
  severity: string;
  occurrences: number;
}>
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   USER / AGENT                      │
│   buildDossier()  buildThesis()  compareCompanies() │
│   answerCompanyQuestion()                           │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│              @equity/services                       │
│   DossierBuilder  ──────────────────────────────┐  │
│        ↓ (priceDelta, freshnessMetadata)        │  │
│   ThesisBuilder                                 │  │
│        ↓ (openQuestions, bullCase, bearCase,    │  │
│           invalidationPoints, changeFromPrior)  │  │
│   syncJudgmentStore()  ◄────────────────────────┘  │
│        ↓                                            │
│   answerCompanyQuestion()                           │
│        ↓ (intent routing, Layer 2 context)          │
└──────────────┬──────────────────────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌────────────┐  ┌───────────────┐
│  Layer 1   │  │   Layer 2     │
│  Artifact  │  │  Judgment     │
│  Memory    │  │  Memory       │
│  (walltalk │  │  JudgmentStore│
│   files)   │  │  per ticker   │
└────────────┘  └───────────────┘
```

---

## Design Principles

1. **No breaking changes** — All new fields are optional in existing interfaces
2. **Walltalk boundary** — `@equity/walltalk` remains pure file I/O; LLM only in `@equity/services`
3. **Graceful degradation** — Q&A works even with no dossier (low confidence), no JudgmentStore (uses legacy FileJudgmentMemory), no prior thesis (no diff computation)
4. **Structured over text** — `JudgmentStore` replaces free-form markdown as primary judgment memory; `FreshnessMetadata` replaces text-embedded freshness section
5. **Intent-aware assembly** — Context is not one-size-fits-all; surface what matters most for the question type

---

*Generated: 2026-03-28 — equity-intelligence Judgment Support OS upgrade complete*
