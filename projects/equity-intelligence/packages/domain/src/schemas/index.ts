/**
 * equity-intelligence — Shared Domain Schemas (Zod)
 *
 * Canonical types for the entire research OS.
 * All adapters MUST normalize their raw data to these schemas.
 */

import { z } from "zod";

// ─────────────────────────────────────────────
// Market identifier
// ─────────────────────────────────────────────

export const MarketSchema = z.enum(["US", "JP"]);
export type Market = z.infer<typeof MarketSchema>;

// ─────────────────────────────────────────────
// Security (銘柄)
// US: "AAPL"  /  JP: "7203" (トヨタ) — always string, no leading zeros stripped
// ─────────────────────────────────────────────

export const SecuritySchema = z.object({
  ticker: z.string(),           // "AAPL" or "7203"
  market: MarketSchema,
  name: z.string(),             // "Apple Inc." / "トヨタ自動車"
  nameEn: z.string().optional(),
  sector: z.string().optional(),
  industry: z.string().optional(),
  listingDate: z.string().optional(), // ISO date
  currency: z.enum(["USD", "JPY"]),
  isin: z.string().optional(),
});
export type Security = z.infer<typeof SecuritySchema>;

// ─────────────────────────────────────────────
// Price Bar (OHLCV)
// ─────────────────────────────────────────────

export const PriceBarSchema = z.object({
  ticker: z.string(),
  market: MarketSchema,
  date: z.string(),             // "YYYY-MM-DD"
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
  volume: z.number(),
  adjustedClose: z.number().optional(),
});
export type PriceBar = z.infer<typeof PriceBarSchema>;

// ─────────────────────────────────────────────
// Financial Statement — common structure
// ─────────────────────────────────────────────

export const PeriodTypeSchema = z.enum(["annual", "quarterly", "semiannual"]);
export type PeriodType = z.infer<typeof PeriodTypeSchema>;

export const IncomeStatementSchema = z.object({
  ticker: z.string(),
  market: MarketSchema,
  periodType: PeriodTypeSchema,
  periodEnd: z.string(),        // "YYYY-MM-DD"
  currency: z.enum(["USD", "JPY"]),
  revenue: z.number().nullable(),
  operatingIncome: z.number().nullable(),
  netIncome: z.number().nullable(),
  eps: z.number().nullable(),
  ebitda: z.number().nullable().optional(),
  raw: z.record(z.unknown()).optional(), // original payload from provider
});
export type IncomeStatement = z.infer<typeof IncomeStatementSchema>;

export const BalanceSheetSchema = z.object({
  ticker: z.string(),
  market: MarketSchema,
  periodType: PeriodTypeSchema,
  periodEnd: z.string(),
  currency: z.enum(["USD", "JPY"]),
  totalAssets: z.number().nullable(),
  totalLiabilities: z.number().nullable(),
  shareholdersEquity: z.number().nullable(),
  cashAndEquivalents: z.number().nullable(),
  totalDebt: z.number().nullable().optional(),
  raw: z.record(z.unknown()).optional(),
});
export type BalanceSheet = z.infer<typeof BalanceSheetSchema>;

// ─────────────────────────────────────────────
// Filing (開示書類)
// Covers both SEC (US) and EDINET (JP)
// ─────────────────────────────────────────────

export const FilingTypeSchema = z.enum([
  // US (SEC)
  "10-K",      // Annual report
  "10-Q",      // Quarterly report
  "8-K",       // Material event
  "DEF 14A",   // Proxy statement
  // JP (EDINET)
  "有価証券報告書",     // Annual securities report
  "四半期報告書",       // Quarterly report
  "決算短信",           // Earnings flash
  "臨時報告書",         // Extraordinary report
  "大量保有報告書",     // Large shareholding report
  // Generic
  "OTHER",
]);
export type FilingType = z.infer<typeof FilingTypeSchema>;

export const FilingSchema = z.object({
  id: z.string(),               // docID (EDINET) or accessionNumber (SEC)
  ticker: z.string().optional(),
  companyName: z.string(),
  market: MarketSchema,
  filingType: FilingTypeSchema,
  filedAt: z.string(),          // ISO datetime
  periodEnd: z.string().optional(),
  url: z.string().optional(),   // Direct link to filing
  summary: z.string().optional(),
  raw: z.record(z.unknown()).optional(),
});
export type Filing = z.infer<typeof FilingSchema>;

// ─────────────────────────────────────────────
// FreshnessMetadata (構造化データ取得情報)
// Replaces the text-embedded freshness in analystNotes
// ─────────────────────────────────────────────

export const FreshnessMetadataSchema = z.object({
  fetchedAt: z.string(),                 // ISO datetime of dossier creation
  market: MarketSchema,
  ticker: z.string(),
  securityFetched: z.boolean(),
  latestPriceFetched: z.boolean(),
  incomeStatementsCount: z.number(),
  balanceSheetsCount: z.number(),
  recentFilingsCount: z.number(),
  newsItemsCount: z.number(),
  summaryGenerated: z.boolean(),
  priceDate: z.string().optional(),      // date of the latest price bar
});
export type FreshnessMetadata = z.infer<typeof FreshnessMetadataSchema>;

// ─────────────────────────────────────────────
// PriceDelta (株価変化 vs. 前回ドシエ)
// ─────────────────────────────────────────────

export const PriceDeltaSchema = z.object({
  priorPrice: z.number(),
  currentPrice: z.number(),
  priorDate: z.string(),                 // ISO date "YYYY-MM-DD"
  currentDate: z.string(),
  changeAbsolute: z.number(),            // currentPrice - priorPrice
  changePercent: z.number(),             // (change / priorPrice) * 100, rounded 2dp
  currency: z.enum(["USD", "JPY"]),
});
export type PriceDelta = z.infer<typeof PriceDeltaSchema>;

// ─────────────────────────────────────────────
// JudgmentStore types (構造化判断メモリ)
// ─────────────────────────────────────────────

export const StanceHistoryItemSchema = z.object({
  thesisId: z.string(),
  date: z.string(),                      // ISO date of thesis creation
  stance: z.enum(["bullish", "bearish", "neutral"]),
  conviction: z.enum(["low", "medium", "high"]),
  title: z.string().optional(),
  targetPrice: z.number().optional(),
});
export type StanceHistoryItem = z.infer<typeof StanceHistoryItemSchema>;

export const RecurringRiskSchema = z.object({
  category: z.enum([
    "market", "regulatory", "execution", "financial", "geopolitical", "other"
  ]),
  severity: z.enum(["low", "medium", "high"]),
  description: z.string(),
  occurrences: z.number(),               // how many theses mentioned this risk
  firstSeen: z.string(),                 // ISO date
  lastSeen: z.string(),                  // ISO date
});
export type RecurringRisk = z.infer<typeof RecurringRiskSchema>;

export const LessonSchema = z.object({
  extractedAt: z.string(),               // ISO datetime
  thesisId: z.string(),
  lesson: z.string(),
  category: z.string().optional(),       // "timing", "risk", "catalyst", etc.
});
export type Lesson = z.infer<typeof LessonSchema>;

export const JudgmentCrossRefSchema = z.object({
  ticker: z.string(),
  market: MarketSchema,
  relationship: z.string(),              // "sector peer", "competitor", "partner"
  addedAt: z.string(),
});
export type JudgmentCrossRef = z.infer<typeof JudgmentCrossRefSchema>;

export const JudgmentStoreSchema = z.object({
  ticker: z.string(),
  market: MarketSchema,
  updatedAt: z.string(),                 // ISO datetime of last sync
  stanceHistory: z.array(StanceHistoryItemSchema).default([]),
  currentStance: StanceHistoryItemSchema.optional(),
  recurringRisks: z.array(RecurringRiskSchema).default([]),
  openQuestions: z.array(z.string()).default([]),
  lessons: z.array(LessonSchema).default([]),
  crossRefs: z.array(JudgmentCrossRefSchema).default([]),
  thesisCount: z.number().default(0),
});
export type JudgmentStore = z.infer<typeof JudgmentStoreSchema>;

// ─────────────────────────────────────────────
// Dossier (企業調査まとめ)
// One dossier = one company at one point in time
// ─────────────────────────────────────────────

export const RiskNoteSchema = z.object({
  category: z.enum([
    "market", "regulatory", "execution", "financial", "geopolitical", "other"
  ]),
  severity: z.enum(["low", "medium", "high"]),
  description: z.string(),
  evidence: z.string().optional(),
});
export type RiskNote = z.infer<typeof RiskNoteSchema>;

export const DossierSchema = z.object({
  ticker: z.string(),
  market: MarketSchema,
  createdAt: z.string(),        // ISO datetime
  security: SecuritySchema.optional(),
  latestPrice: PriceBarSchema.optional(),
  incomeStatements: z.array(IncomeStatementSchema).default([]),
  balanceSheets: z.array(BalanceSheetSchema).default([]),
  recentFilings: z.array(FilingSchema).default([]),
  risks: z.array(RiskNoteSchema).default([]),
  analystNotes: z.string().optional(),
  summary: z.string().optional(),       // LLM-generated executive summary
  // ── Layer 1 enrichments ──────────────────────────────────
  freshnessMetadata: FreshnessMetadataSchema.optional(), // structured fetch info
  priorDossierDate: z.string().optional(),               // ISO date of prior dossier used for diff
  priceDelta: PriceDeltaSchema.optional(),               // price change vs prior dossier
});
export type Dossier = z.infer<typeof DossierSchema>;

// ─────────────────────────────────────────────
// Thesis (投資テーゼ)
// Human-or-AI authored investment thesis
// ─────────────────────────────────────────────

export const ThesisSchema = z.object({
  id: z.string(),
  ticker: z.string(),
  market: MarketSchema,
  createdAt: z.string(),
  updatedAt: z.string(),
  title: z.string(),
  stance: z.enum(["bullish", "bearish", "neutral"]),
  horizon: z.enum(["short", "medium", "long"]),  // <3m, 3-12m, >12m
  targetPrice: z.number().optional(),
  targetCurrency: z.enum(["USD", "JPY"]).optional(),
  conviction: z.enum(["low", "medium", "high"]),
  catalysts: z.array(z.string()).default([]),
  risks: z.array(RiskNoteSchema).default([]),
  body: z.string(),             // Full thesis markdown
  references: z.array(z.string()).default([]),  // Filing IDs, URLs
  version: z.number().default(1),
  // ── Judgment depth fields ────────────────────────────────
  openQuestions: z.array(z.string()).default([]),    // questions that could change this thesis
  bullCase: z.string().optional(),                   // strongest bull case (1-2 sentences)
  bearCase: z.string().optional(),                   // strongest bear case (1-2 sentences)
  invalidationPoints: z.array(z.string()).default([]), // conditions that would invalidate this
  // ── Change tracking vs prior thesis ─────────────────────
  priorThesisId: z.string().optional(),              // ID of the thesis this supersedes
  stanceChanged: z.boolean().optional(),             // true if stance differs from prior
  changeFromPrior: z.string().optional(),            // human-readable description of change
});
export type Thesis = z.infer<typeof ThesisSchema>;

// ─────────────────────────────────────────────
// Screener Query
// ─────────────────────────────────────────────

export const ScreenerQuerySchema = z.object({
  market: MarketSchema.optional(),
  sector: z.string().optional(),
  minRevenue: z.number().optional(),
  maxPeRatio: z.number().optional(),
  minDividendYield: z.number().optional(),
  keywordSearch: z.string().optional(),
  limit: z.number().default(20),
});
export type ScreenerQuery = z.infer<typeof ScreenerQuerySchema>;

export const ScreenerResultSchema = z.object({
  securities: z.array(SecuritySchema),
  query: ScreenerQuerySchema,
  generatedAt: z.string(),
});
export type ScreenerResult = z.infer<typeof ScreenerResultSchema>;

// ─────────────────────────────────────────────
// Research Session (agent conversation context)
// ─────────────────────────────────────────────

export const ResearchSessionSchema = z.object({
  id: z.string(),
  startedAt: z.string(),
  query: z.string(),
  market: MarketSchema.optional(),
  ticker: z.string().optional(),
  steps: z.array(z.object({
    tool: z.string(),
    args: z.record(z.unknown()),
    result: z.unknown(),
    timestamp: z.string(),
  })).default([]),
  finalAnswer: z.string().optional(),
  dossier: DossierSchema.optional(),
  thesis: ThesisSchema.optional(),
});
export type ResearchSession = z.infer<typeof ResearchSessionSchema>;
