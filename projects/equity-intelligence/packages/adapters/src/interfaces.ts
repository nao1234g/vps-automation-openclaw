/**
 * equity-intelligence — Adapter Contracts
 *
 * All market data adapters implement these interfaces.
 * The agent layer only imports these interfaces — never concrete clients.
 *
 * Design principle: Dexter's "easily swap data provider" pattern, formalized.
 */

import type {
  Security,
  PriceBar,
  IncomeStatement,
  BalanceSheet,
  Filing,
  FilingType,
  Market,
  ScreenerQuery,
  Result,
} from "@equity/domain";

// ─────────────────────────────────────────────
// Base adapter — all adapters implement this
// ─────────────────────────────────────────────

export interface MarketAdapter {
  /** Which market this adapter serves */
  readonly market: Market;

  /** Human-readable name for logging */
  readonly name: string;

  /** Health check — returns true if API is reachable */
  ping(): Promise<boolean>;
}

// ─────────────────────────────────────────────
// Securities (銘柄マスター)
// ─────────────────────────────────────────────

export interface SecurityAdapter extends MarketAdapter {
  /** Look up a single security by ticker */
  getSecurity(ticker: string): Promise<Result<Security>>;

  /** Search by name keyword (JP: 会社名, US: company name) */
  searchSecurities(keyword: string, limit?: number): Promise<Result<Security[]>>;
}

// ─────────────────────────────────────────────
// Price data
// ─────────────────────────────────────────────

export interface PriceAdapter extends MarketAdapter {
  /**
   * Fetch daily OHLCV bars for a ticker.
   * @param ticker  Security identifier
   * @param from    ISO date "YYYY-MM-DD"
   * @param to      ISO date "YYYY-MM-DD"
   */
  getDailyBars(
    ticker: string,
    from: string,
    to: string
  ): Promise<Result<PriceBar[]>>;

  /** Latest closing price */
  getLatestPrice(ticker: string): Promise<Result<PriceBar>>;
}

// ─────────────────────────────────────────────
// Financial statements
// ─────────────────────────────────────────────

export interface FinancialStatementsAdapter extends MarketAdapter {
  getIncomeStatements(
    ticker: string,
    limit?: number
  ): Promise<Result<IncomeStatement[]>>;

  getBalanceSheets(
    ticker: string,
    limit?: number
  ): Promise<Result<BalanceSheet[]>>;
}

// ─────────────────────────────────────────────
// Filings (開示書類)
// US: SEC EDGAR / JP: EDINET
// ─────────────────────────────────────────────

export interface FilingsAdapter extends MarketAdapter {
  /**
   * List filings for a company.
   * JP adapters may need to look up company by ticker first.
   */
  listFilings(
    ticker: string,
    types?: FilingType[],
    limit?: number
  ): Promise<Result<Filing[]>>;

  /**
   * Fetch filing content / summary.
   * Returns markdown-formatted text for LLM consumption.
   */
  getFilingContent(filingId: string): Promise<Result<string>>;
}

// ─────────────────────────────────────────────
// Web search / news (optional enrichment layer)
// ─────────────────────────────────────────────

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  publishedAt?: string;
}

export interface SearchAdapter {
  readonly name: string;
  search(query: string, limit?: number): Promise<Result<SearchResult[]>>;
}

// ─────────────────────────────────────────────
// Composite: full-featured market adapter
// Implements all capabilities for a given market
// ─────────────────────────────────────────────

export interface FullMarketAdapter
  extends SecurityAdapter,
    PriceAdapter,
    FinancialStatementsAdapter,
    FilingsAdapter {}

// ─────────────────────────────────────────────
// Adapter registry (runtime wiring)
// The agent looks up adapters by market at runtime
// ─────────────────────────────────────────────

export interface AdapterRegistry {
  getSecurityAdapter(market: Market): SecurityAdapter | undefined;
  getPriceAdapter(market: Market): PriceAdapter | undefined;
  getFinancialsAdapter(market: Market): FinancialStatementsAdapter | undefined;
  getFilingsAdapter(market: Market): FilingsAdapter | undefined;
  getSearchAdapter(): SearchAdapter | undefined;
}
