# equity-intelligence — Architecture Design

> Personal equity research OS for US + Japanese stocks.
> Designed 2026-03-28. RIGHT role: Architecture Lead.

---

## Principles

1. **Bounded context** — Completely separate from nowpattern. No shared DB, no shared services.
2. **Adapter pattern** — Agent layer never imports concrete API clients. Only interfaces.
3. **File-based walltalk boundary** — Read-only artifact output. No direct API coupling.
4. **Dexter-compatible pattern** — Same 4-agent workflow, same tool registry approach, but extended for JP markets.
5. **Claude Max inside** — Uses Anthropic Claude (same $200/month subscription). No API billing.

---

## Directory Structure

```
projects/equity-intelligence/
├── package.json              # Bun workspace root
├── tsconfig.json
├── .env.example
│
├── packages/
│   ├── domain/               # Shared types (Security, Filing, Dossier, Thesis, etc.)
│   │   └── src/
│   │       ├── schemas/      # Zod schemas (canonical source of truth)
│   │       └── types/        # TypeScript utility types (Result<T>, etc.)
│   │
│   ├── adapters/             # Market data adapters
│   │   └── src/
│   │       ├── interfaces.ts # Contracts: SecurityAdapter, PriceAdapter, FilingsAdapter
│   │       ├── registry.ts   # Runtime wiring: builds adapters from env vars
│   │       ├── us/           # Financial Datasets API (US stocks)
│   │       ├── jquants/      # J-Quants API (JP prices, company master)
│   │       ├── edinet/       # EDINET API (JP filings — server-side only)
│   │       └── exa/          # Exa (optional: semantic news search)
│   │
│   ├── services/             # Business logic
│   │   └── src/
│   │       └── research/     # LangChain agent (Planner→Executor→Validator→Answerer)
│   │
│   └── walltalk/             # Read-only artifact writer (file-based boundary)
│       └── src/
│           └── index.ts      # writeDossier(), writeThesis(), getArtifactIndex()
│
├── docs/
│   └── architecture.md       # This file
│
├── output/
│   └── walltalk/             # Generated artifacts (gitignored)
│       ├── dossier/
│       ├── thesis/
│       ├── screener/
│       └── sessions/
│
└── tests/
```

---

## Data Flow

```
User Query
  │
  ▼
research/agent.ts (LangChain AgentExecutor)
  │
  │  [Planning phase]
  │  Decomposes query: market?, ticker?, data needs?
  │
  │  [Tool execution loop]
  │    get_security_info(ticker, market)
  │    get_latest_price(ticker, market)
  │    get_income_statements(ticker, market)
  │    list_filings(ticker, market)
  │    search_news(query)          ← only if Exa key present
  │
  │  [Validation phase]
  │  Claude checks consistency, flags missing data
  │
  │  [Synthesis phase]
  │  Produces structured markdown report
  │
  ▼
AdapterRegistry.getXxxAdapter(market)
  │
  ├── market=US → FinancialDatasetsAdapter (Financial Datasets API)
  │
  └── market=JP → JQuantsAdapter (prices + company master)
                  EdinetAdapter  (filings — 有価証券報告書, etc.)

  ▼
Domain types (Security, PriceBar, IncomeStatement, Filing, ...)
  (all adapters normalize to these — agent never sees raw API responses)

  ▼
walltalk/index.ts
  writeDossier()  → output/walltalk/dossier/{ticker}-{date}.json
  writeThesis()   → output/walltalk/thesis/{ticker}-{id}.md
  writeResearchSession() → output/walltalk/sessions/{id}.json
```

---

## Market Adapter Capabilities

| Capability | US (FinancialDatasets) | JP: J-Quants | JP: EDINET |
|------------|----------------------|--------------|------------|
| Company info | ✅ | ✅ | ❌ (no API) |
| Daily prices (OHLCV) | ✅ | ✅ (12-week delay free) | ❌ |
| Income statements | ✅ | ❌ (premium only) | ✅ (via XBRL) |
| Balance sheets | ✅ | ❌ (premium only) | ✅ (via XBRL) |
| Annual report filings | ✅ (10-K via SEC) | ❌ | ✅ (有価証券報告書) |
| Quarterly filings | ✅ (10-Q) | ❌ | ✅ (四半期報告書) |
| Real-time prices | ✅ | ❌ (free tier delay) | ❌ |
| News search | Optional (Exa) | Optional (Exa) | Optional (Exa) |

---

## Known Constraints

### J-Quants Free Tier
- **12-week price delay** — Always disclose in research reports
- No financial statements (Premium plan required)
- Rate limits not officially documented → use conservative 1 req/s

### EDINET
- **Server-side only** — Cannot call from browser. Already handled by adapter.
- **3–5 second intervals required** between requests (coded into `rateLimitedFetch()`)
- **Date-based queries only** — No `/companies/{id}/filings` endpoint
- Strategy: Search backwards day-by-day, filter by company name match
- For production: maintain a ticker→edinetCode mapping table (reduces date scanning)

### Exa
- **Optional** — Registry skips if `EXASEARCH_API_KEY` absent
- Cost: $5/1,000 searches + $1/1,000 pages (full text)
- Not a replacement for structured JP data — enrichment layer only

---

## Adding New Markets

To add European or other Asian markets:

1. Create `packages/adapters/src/{market}/client.ts` implementing the relevant interfaces
2. Update `packages/adapters/src/registry.ts` to wire the new adapter
3. Extend `MarketSchema` in `packages/domain/src/schemas/index.ts`
4. Add new env vars to `.env.example`

The agent code in `research/agent.ts` requires **zero changes** — tools call the registry.

---

## Walltalk Integration

The walltalk package is a **one-way output channel**. equity-intelligence writes files; walltalk reads them.

```
equity-intelligence writes:                 walltalk reads:
output/walltalk/dossier/*.json    ────►    Claude, NEO, any consumer
output/walltalk/thesis/*.md       ────►    walltalk/src/index.ts helpers
output/walltalk/sessions/*.json   ────►    readDossier(ticker), getArtifactIndex(ticker)
```

**Design decision**: File-based boundary (not MCP, not REST API) because:
- Walltalk internals may change; files are the most stable contract
- Claude Code can `Read` files directly (no extra tooling)
- NEO can also access the same files from VPS if the output dir is synced

---

## Reference: Dexter-JP (Existing JP Implementation)

[edinetdb/dexter-jp](https://github.com/edinetdb/dexter-jp) is an existing fork of Dexter for Japanese stocks using EDINET + J-Quants. It proves the architecture pattern works. Our implementation differs:

- TypeScript strict mode throughout (no `any`)
- Monorepo workspace structure (domain / adapters / services are separate packages)
- Zod-validated domain types (normalized schema boundary)
- Explicit `Result<T>` type instead of thrown exceptions
- LangChain 1.1.x + `createToolCallingAgent` pattern (updated from Dexter's older agent pattern)
- Claude as default LLM (not OpenAI)
- Walltalk file-based output boundary

---

## Quick Start

```bash
# 1. Copy and fill in env vars
cp .env.example .env

# 2. Install (requires Bun)
bun install

# 3. Research US stock
bun run research "Analyze Apple AAPL — latest financials and growth outlook"

# 4. Research Japanese stock
bun run research "トヨタ自動車 7203 の財務状況と株価を分析してください"

# 5. With news enrichment (requires Exa key)
bun run research "Analyze Nvidia NVDA earnings and AI chip demand outlook"
```

---

## Roadmap

- [ ] Dossier auto-generation: after each research session, produce structured JSON artifact
- [ ] Thesis writer: LLM-drafted thesis from Dossier → walltalk output
- [ ] Screener: filter JP/US securities by sector, revenue, PE ratio
- [ ] JP ticker→edinetCode mapping table (eliminate date-scanning for known companies)
- [ ] J-Quants Premium upgrade path (real-time prices, financial statements)
- [ ] XBRL parser for EDINET (extract structured financial data from 有価証券報告書)
- [ ] Portfolio tracker: multi-ticker dashboard in CLI (Ink/React)
