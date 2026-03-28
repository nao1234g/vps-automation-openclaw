# Artifact Memory Inventory — equity-intelligence

> Last updated: 2026-03-28
> All artifacts managed by `@equity/walltalk` package (pure file I/O, no LLM)

---

## Storage Root

```
WALLTALK_OUTPUT_DIR  (env var, default: ./output/walltalk)
  ├── dossier/        ← Layer 1: Company research snapshots
  ├── thesis/         ← Layer 1: Investment thesis documents
  ├── session/        ← Layer 1: Research session logs
  ├── screener/       ← Layer 1: Multi-company screener results
  └── judgment/       ← Layer 2: Structured judgment memory (NEW)
```

---

## Artifact: Dossier

**Path**: `{WALLTALK_OUTPUT_DIR}/dossier/{ticker}-{YYYY-MM-DD}.json`
**Schema**: `DossierSchema` (Zod) → TypeScript type `Dossier`
**Writer**: `writeDossier(dossier: Dossier): Promise<void>`
**Reader**: `readDossier(ticker: string, date?: string): Promise<Dossier | null>`
**Prior reader**: `readPreviousDossier(ticker: string, beforeDate: string): Promise<Dossier | null>`

### Fields

| Field | Type | Added | Description |
|-------|------|-------|-------------|
| `ticker` | string | v1 | Stock ticker symbol |
| `market` | Market | v1 | Exchange (TSE, NYSE, NASDAQ, etc.) |
| `createdAt` | string | v1 | ISO datetime of assembly |
| `security` | SecurityInfo? | v1 | Company name, sector, currency |
| `latestPrice` | PricePoint? | v1 | Most recent close price |
| `incomeStatements` | IncomeStatement[] | v1 | Up to 4 periods |
| `balanceSheets` | BalanceSheet[] | v1 | Up to 4 periods |
| `recentFilings` | Filing[] | v1 | Up to 5 recent filings |
| `risks` | RiskNote[] | v1 | Extracted risk notes (from extractRisks()) |
| `analystNotes` | string? | v1 | Markdown with freshness + news + prior judgment |
| `summary` | string? | v1 | LLM executive summary (200 chars) |
| `freshnessMetadata` | FreshnessMetadata? | **v2** | Structured data-fetch audit trail |
| `priorDossierDate` | string? | **v2** | ISO date of prior dossier used for diff |
| `priceDelta` | PriceDelta? | **v2** | Price change vs prior dossier |

### FreshnessMetadata fields

| Field | Type | Description |
|-------|------|-------------|
| `fetchedAt` | string | ISO datetime of fetch |
| `market` | Market | |
| `ticker` | string | |
| `securityFetched` | boolean | Whether security adapter succeeded |
| `latestPriceFetched` | boolean | Whether price adapter succeeded |
| `incomeStatementsCount` | number | How many periods returned |
| `balanceSheetsCount` | number | |
| `recentFilingsCount` | number | |
| `newsItemsCount` | number | |
| `summaryGenerated` | boolean | Whether LLM summary was generated |
| `priceDate` | string? | Date of latest price point |

### PriceDelta fields

| Field | Type | Description |
|-------|------|-------------|
| `priorPrice` | number | Close price from prior dossier |
| `currentPrice` | number | Close price from this dossier |
| `priorDate` | string | Date of prior price |
| `currentDate` | string | Date of current price |
| `changeAbsolute` | number | Absolute price change |
| `changePercent` | number | Percentage change (rounded to 2dp) |
| `currency` | string | Currency code |

---

## Artifact: Thesis

**Path**: `{WALLTALK_OUTPUT_DIR}/thesis/{ticker}-{thesisId}.md`
**Schema**: `ThesisSchema` (Zod) → TypeScript type `Thesis`
**Writer**: `writeThesis(thesis: Thesis): Promise<void>`
**Reader**: not yet implemented (read from index)

### Fields (v2 additions highlighted)

| Field | Type | Added | Description |
|-------|------|-------|-------------|
| `id` | string | v1 | `thesis-{ticker}-{timestamp}` |
| `ticker` | string | v1 | |
| `market` | Market | v1 | |
| `createdAt` | string | v1 | |
| `updatedAt` | string | v1 | |
| `title` | string | v1 | ≤60 chars |
| `stance` | bullish/bearish/neutral | v1 | |
| `horizon` | short/medium/long | v1 | |
| `conviction` | low/medium/high | v1 | |
| `targetPrice` | number? | v1 | |
| `targetCurrency` | string? | v1 | |
| `catalysts` | string[] | v1 | 3–5 key catalysts |
| `risks` | ThesisRisk[] | v1 | 2–4 structured risks |
| `body` | string | v1 | Full thesis in markdown (400–800 chars) |
| `references` | string[] | v1 | Filing IDs / URLs used as evidence |
| `version` | number | v1 | Thesis version number |
| `openQuestions` | string[] | **v2** | 2–4 questions that could change thesis |
| `bullCase` | string? | **v2** | Strongest bull case (1–2 sentences) |
| `bearCase` | string? | **v2** | Strongest bear case (1–2 sentences) |
| `invalidationPoints` | string[] | **v2** | 2–3 invalidation conditions |
| `priorThesisId` | string? | **v2** | Reference to prior thesis |
| `stanceChanged` | boolean? | **v2** | Whether stance changed vs prior |
| `changeFromPrior` | string? | **v2** | LLM description of what changed |

---

## Artifact: JudgmentStore (NEW — Layer 2)

**Path**: `{WALLTALK_OUTPUT_DIR}/judgment/{ticker}-judgment.json`
**Schema**: `JudgmentStoreSchema` (Zod) → TypeScript type `JudgmentStore`
**Writer**: `writeJudgment(store: JudgmentStore): Promise<void>`
**Reader**: `readJudgment(ticker: string): Promise<JudgmentStore | null>`
**Sync**: `syncJudgmentStore(thesis: Thesis): Promise<JudgmentStore>` (in `@equity/services`)

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | |
| `market` | Market | |
| `updatedAt` | string | ISO datetime of most recent sync |
| `thesisCount` | number | Total theses processed |
| `currentStance` | StanceHistoryItem? | Most recent stance |
| `stanceHistory` | StanceHistoryItem[] | Chronological stance progression |
| `recurringRisks` | RecurringRisk[] | De-duplicated risks, sorted by frequency |
| `lessons` | Lesson[] | Key takeaways |
| `openQuestions` | string[] | Open questions from latest thesis |
| `crossRefs` | JudgmentCrossRef[] | Links to related tickers |

### StanceHistoryItem fields

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | ISO date |
| `stance` | bullish/bearish/neutral | |
| `conviction` | low/medium/high | |
| `thesisId` | string | Source thesis ID |
| `title` | string? | Thesis title at this point |
| `targetPrice` | number? | Target price at this point |

### RecurringRisk fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Risk description |
| `category` | RiskCategory | market/regulatory/execution/financial/geopolitical/other |
| `severity` | low/medium/high | |
| `occurrences` | number | How many theses flagged this risk |
| `firstSeen` | string | ISO date of first occurrence |
| `lastSeen` | string | ISO date of most recent occurrence |

---

## Artifact: Session

**Path**: `{WALLTALK_OUTPUT_DIR}/session/{sessionId}.json`
**Schema**: `SessionSchema` (Zod) → TypeScript type `Session`
**Writer**: `writeSession(session: Session): Promise<void>`
**Purpose**: Records what was researched in a single agent session

---

## Artifact: ScreenerResult

**Path**: `{WALLTALK_OUTPUT_DIR}/screener/{id}.json`
**Schema**: `ScreenerResultSchema` (Zod) → TypeScript type `ScreenerResult`
**Writer**: `writeScreenerResult(result: ScreenerResult): Promise<void>`
**Purpose**: Records multi-company screener comparison results from `compareCompanies()`

---

## Artifact Index

**Function**: `getArtifactIndex(ticker: string): Promise<ArtifactIndex>`
**Purpose**: Quick lookup of what artifacts exist for a ticker

```typescript
interface ArtifactIndex {
  ticker: string;
  dossiers: string[];           // filenames of all dossiers (sorted by date)
  theses: string[];             // filenames of all theses
  hasJudgmentStore: boolean;    // true if judgment/{ticker}-judgment.json exists
}
```

---

## Lifecycle Summary

```
buildDossier()
  → writes Dossier (Layer 1)
  → reads prior Dossier for priceDelta computation (Layer 1)

buildThesis(dossier, { priorThesisRef })
  → writes Thesis (Layer 1)
  → includes openQuestions, bullCase, bearCase, invalidationPoints

syncJudgmentStore(thesis)
  → reads JudgmentStore (Layer 2) if exists
  → merges thesis data (stanceHistory, recurringRisks, openQuestions)
  → writes updated JudgmentStore (Layer 2)

answerCompanyQuestion(ticker, question)
  → reads Dossier (Layer 1) for financial context
  → reads JudgmentStore (Layer 2) for judgment history
  → falls back to FileJudgmentMemory (legacy) if no Layer 2 store
  → returns structured answer with intent detection
```

---

*Generated: 2026-03-28 — equity-intelligence v2 artifact inventory*
