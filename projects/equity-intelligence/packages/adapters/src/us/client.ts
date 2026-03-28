/**
 * US Market Adapter (Financial Datasets API)
 * https://financialdatasets.ai/
 *
 * This is the same data source as Dexter's primary provider.
 * Free tier: AAPL, NVDA, MSFT only.
 * Paid tier: Full US market coverage.
 *
 * Endpoints:
 *   GET /tickers/{ticker}                    — Security info
 *   GET /tickers/{ticker}/prices             — Historical prices
 *   GET /tickers/{ticker}/income-statements  — Income statements
 *   GET /tickers/{ticker}/balance-sheets     — Balance sheets
 *   GET /tickers/{ticker}/filings            — SEC filings
 */

import { ok, err } from "@equity/domain";
import type {
  Result,
  Security,
  PriceBar,
  IncomeStatement,
  BalanceSheet,
  Filing,
  FilingType,
} from "@equity/domain";
import type {
  SecurityAdapter,
  PriceAdapter,
  FinancialStatementsAdapter,
  FilingsAdapter,
} from "../interfaces.js";

const FD_BASE = "https://api.financialdatasets.ai";

export class FinancialDatasetsAdapter
  implements SecurityAdapter, PriceAdapter, FinancialStatementsAdapter, FilingsAdapter
{
  readonly market = "US" as const;
  readonly name = "Financial Datasets API";

  private readonly apiKey: string;
  private readonly baseUrl: string;

  constructor(apiKey: string, baseUrl = FD_BASE) {
    if (!apiKey) throw new Error("FINANCIAL_DATASETS_API_KEY is required");
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  private async get<T>(path: string, params: Record<string, string> = {}): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, v);
    }

    const res = await fetch(url.toString(), {
      headers: {
        "X-API-KEY": this.apiKey,
        "Content-Type": "application/json",
      },
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`FinancialDatasets ${path} → ${res.status}: ${body}`);
    }

    return res.json() as Promise<T>;
  }

  async ping(): Promise<boolean> {
    try {
      await this.get("/tickers/AAPL");
      return true;
    } catch {
      return false;
    }
  }

  // ── SecurityAdapter ──────────────────────────────────────

  async getSecurity(ticker: string): Promise<Result<Security>> {
    try {
      const data = await this.get<{
        ticker: string;
        name: string;
        sector: string;
        industry: string;
      }>(`/tickers/${ticker}`);

      return ok({
        ticker: data.ticker ?? ticker,
        market: "US",
        name: data.name ?? ticker,
        sector: data.sector,
        industry: data.industry,
        currency: "USD",
      });
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }

  async searchSecurities(keyword: string, limit = 20): Promise<Result<Security[]>> {
    try {
      const data = await this.get<{ tickers: Array<{ ticker: string; name: string }> }>(
        "/tickers/search",
        { query: keyword, limit: String(limit) }
      );
      const securities = (data.tickers ?? []).map(
        (t): Security => ({
          ticker: t.ticker,
          market: "US",
          name: t.name,
          currency: "USD",
        })
      );
      return ok(securities);
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }

  // ── PriceAdapter ─────────────────────────────────────────

  async getDailyBars(ticker: string, from: string, to: string): Promise<Result<PriceBar[]>> {
    try {
      const data = await this.get<{
        prices: Array<{
          date: string;
          open: number;
          high: number;
          low: number;
          close: number;
          volume: number;
          adjusted_close?: number;
        }>;
      }>(`/tickers/${ticker}/prices`, {
        start_date: from,
        end_date: to,
        interval: "1d",
      });

      const bars = (data.prices ?? []).map(
        (p): PriceBar => ({
          ticker,
          market: "US",
          date: p.date,
          open: p.open,
          high: p.high,
          low: p.low,
          close: p.close,
          volume: p.volume,
          adjustedClose: p.adjusted_close,
        })
      );
      return ok(bars);
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }

  async getLatestPrice(ticker: string): Promise<Result<PriceBar>> {
    const today = new Date().toISOString().slice(0, 10);
    const weekAgo = new Date(Date.now() - 7 * 86_400_000).toISOString().slice(0, 10);
    const result = await this.getDailyBars(ticker, weekAgo, today);
    if (!result.ok) return result;
    const bars = result.data;
    if (bars.length === 0) return err(new Error(`No price data for ${ticker}`));
    return ok(bars[bars.length - 1]!);
  }

  // ── FinancialStatementsAdapter ───────────────────────────

  async getIncomeStatements(ticker: string, limit = 4): Promise<Result<IncomeStatement[]>> {
    try {
      const data = await this.get<{
        income_statements: Array<{
          period_end_date: string;
          period_type: string;
          revenue: number | null;
          operating_income: number | null;
          net_income: number | null;
          eps_diluted: number | null;
          ebitda: number | null;
        }>;
      }>(`/tickers/${ticker}/income-statements`, { limit: String(limit) });

      const statements = (data.income_statements ?? []).map(
        (s): IncomeStatement => ({
          ticker,
          market: "US",
          periodType: (s.period_type as "annual" | "quarterly") ?? "quarterly",
          periodEnd: s.period_end_date,
          currency: "USD",
          revenue: s.revenue,
          operatingIncome: s.operating_income,
          netIncome: s.net_income,
          eps: s.eps_diluted,
          ebitda: s.ebitda,
          raw: s as Record<string, unknown>,
        })
      );
      return ok(statements);
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }

  async getBalanceSheets(ticker: string, limit = 4): Promise<Result<BalanceSheet[]>> {
    try {
      const data = await this.get<{
        balance_sheets: Array<{
          period_end_date: string;
          period_type: string;
          total_assets: number | null;
          total_liabilities: number | null;
          shareholders_equity: number | null;
          cash_and_equivalents: number | null;
          total_debt: number | null;
        }>;
      }>(`/tickers/${ticker}/balance-sheets`, { limit: String(limit) });

      const sheets = (data.balance_sheets ?? []).map(
        (b): BalanceSheet => ({
          ticker,
          market: "US",
          periodType: (b.period_type as "annual" | "quarterly") ?? "quarterly",
          periodEnd: b.period_end_date,
          currency: "USD",
          totalAssets: b.total_assets,
          totalLiabilities: b.total_liabilities,
          shareholdersEquity: b.shareholders_equity,
          cashAndEquivalents: b.cash_and_equivalents,
          totalDebt: b.total_debt,
          raw: b as Record<string, unknown>,
        })
      );
      return ok(sheets);
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }

  // ── FilingsAdapter (SEC EDGAR via Financial Datasets) ───

  async listFilings(
    ticker: string,
    types?: FilingType[],
    limit = 10
  ): Promise<Result<Filing[]>> {
    try {
      const data = await this.get<{
        filings: Array<{
          accession_number: string;
          company_name: string;
          form_type: string;
          filing_date: string;
          period_of_report: string;
          document_url: string;
        }>;
      }>(`/tickers/${ticker}/filings`, { limit: String(limit) });

      const filings = (data.filings ?? [])
        .filter((f) => {
          if (!types || types.length === 0) return true;
          return types.includes(f.form_type as FilingType);
        })
        .map(
          (f): Filing => ({
            id: f.accession_number,
            ticker,
            companyName: f.company_name,
            market: "US",
            filingType: (f.form_type as FilingType) ?? "OTHER",
            filedAt: f.filing_date,
            periodEnd: f.period_of_report || undefined,
            url: f.document_url,
          })
        );
      return ok(filings);
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }

  async getFilingContent(filingId: string): Promise<Result<string>> {
    try {
      const data = await this.get<{ content: string }>(`/filings/${filingId}/content`);
      return ok(data.content ?? "");
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }
}
