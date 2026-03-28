/**
 * J-Quants Adapter (JPX Official API)
 * https://api.jquants.com/v2/
 *
 * Auth (2-step):
 *   1. POST /v1/token/auth_user  { mailaddress, password } → refreshToken
 *   2. POST /v1/token/auth_refresh?refreshtoken=xxx        → idToken
 *   3. All V2 requests use: Authorization: Bearer {idToken}
 *
 * Free tier: 12-week price delay. Financial statements require Premium.
 * Rate limits: not officially documented; conservative 1 req/s default.
 *
 * Endpoints used:
 *   GET /v2/listed/info          — Company master (銘柄マスター)
 *   GET /v2/prices/daily_quotes  — Daily OHLCV
 */

import { ok, err } from "@equity/domain";
import type { Result, Security, PriceBar } from "@equity/domain";
import type {
  SecurityAdapter,
  PriceAdapter,
  FinancialStatementsAdapter,
} from "../interfaces.js";
import type { IncomeStatement, BalanceSheet } from "@equity/domain";

const JQUANTS_AUTH_BASE = "https://api.jquants.com/v1";
const JQUANTS_BASE = "https://api.jquants.com/v2";

// idToken TTL: 24 hours per J-Quants docs. Refresh 30 min before expiry.
const ID_TOKEN_TTL_MS = 23.5 * 60 * 60 * 1000;

interface JQuantsListedInfo {
  Code: string;
  CompanyName: string;
  CompanyNameEnglish: string;
  Sector17Code: string;
  Sector17CodeName: string;
  ListingDate: string;
}

interface JQuantsDailyQuote {
  Code: string;
  Date: string;
  Open: number | null;
  High: number | null;
  Low: number | null;
  Close: number | null;
  Volume: number | null;
  AdjustmentClose: number | null;
}

export class JQuantsAdapter
  implements SecurityAdapter, PriceAdapter, FinancialStatementsAdapter
{
  readonly market = "JP" as const;
  readonly name = "J-Quants (JPX)";

  private readonly mailAddress: string;
  private readonly password: string;
  private readonly baseUrl: string;

  // Token state
  private refreshToken: string | null = null;
  private idToken: string | null = null;
  private idTokenExpiresAt = 0;

  constructor(mailAddress: string, password: string, baseUrl = JQUANTS_BASE) {
    if (!mailAddress || !password) {
      throw new Error("JQUANTS_MAIL_ADDRESS and JQUANTS_PASSWORD are required");
    }
    this.mailAddress = mailAddress;
    this.password = password;
    this.baseUrl = baseUrl;
  }

  // ── Auth flow ─────────────────────────────────────────────

  /**
   * Step 1: POST /v1/token/auth_user
   * Returns a refreshToken valid for ~7 days.
   */
  private async fetchRefreshToken(): Promise<string> {
    const res = await fetch(`${JQUANTS_AUTH_BASE}/token/auth_user`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mailaddress: this.mailAddress,
        password: this.password,
      }),
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`J-Quants auth_user → ${res.status}: ${body}`);
    }
    const data = (await res.json()) as { refreshToken: string };
    return data.refreshToken;
  }

  /**
   * Step 2: POST /v1/token/auth_refresh?refreshtoken=xxx
   * Returns an idToken valid for 24 hours.
   */
  private async fetchIdToken(refreshToken: string): Promise<string> {
    const res = await fetch(
      `${JQUANTS_AUTH_BASE}/token/auth_refresh?refreshtoken=${encodeURIComponent(refreshToken)}`,
      { method: "POST" }
    );
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`J-Quants auth_refresh → ${res.status}: ${body}`);
    }
    const data = (await res.json()) as { idToken: string };
    return data.idToken;
  }

  /**
   * Returns a valid idToken, refreshing as needed.
   */
  private async getIdToken(): Promise<string> {
    // Return cached token if still valid
    if (this.idToken && Date.now() < this.idTokenExpiresAt) {
      return this.idToken;
    }

    // Try refreshing with existing refreshToken
    if (this.refreshToken) {
      try {
        this.idToken = await this.fetchIdToken(this.refreshToken);
        this.idTokenExpiresAt = Date.now() + ID_TOKEN_TTL_MS;
        return this.idToken;
      } catch {
        // refreshToken expired — fall through to full auth
        this.refreshToken = null;
      }
    }

    // Full authentication
    this.refreshToken = await this.fetchRefreshToken();
    this.idToken = await this.fetchIdToken(this.refreshToken);
    this.idTokenExpiresAt = Date.now() + ID_TOKEN_TTL_MS;
    return this.idToken;
  }

  // ── HTTP helper ───────────────────────────────────────────

  private async get<T>(path: string, params: Record<string, string> = {}): Promise<T> {
    const idToken = await this.getIdToken();
    const url = new URL(`${this.baseUrl}${path}`);
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, v);
    }

    const res = await fetch(url.toString(), {
      headers: {
        Authorization: `Bearer ${idToken}`,
        "Content-Type": "application/json",
      },
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`J-Quants ${path} → ${res.status}: ${body}`);
    }

    return res.json() as Promise<T>;
  }

  async ping(): Promise<boolean> {
    try {
      await this.get("/listed/info", { code: "7203" });
      return true;
    } catch {
      return false;
    }
  }

  // ── SecurityAdapter ──────────────────────────────────────

  async getSecurity(ticker: string): Promise<Result<Security>> {
    try {
      const data = await this.get<{ info: JQuantsListedInfo[] }>(
        "/listed/info",
        { code: ticker }
      );
      const info = data.info?.[0];
      if (!info) return err(new Error(`Ticker ${ticker} not found in J-Quants`));

      return ok({
        ticker: info.Code,
        market: "JP",
        name: info.CompanyName,
        nameEn: info.CompanyNameEnglish || undefined,
        sector: info.Sector17CodeName || undefined,
        listingDate: info.ListingDate || undefined,
        currency: "JPY",
      });
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }

  async searchSecurities(keyword: string, limit = 20): Promise<Result<Security[]>> {
    try {
      // J-Quants doesn't have a keyword search endpoint in free tier.
      // Fetch all listed companies and filter client-side.
      const data = await this.get<{ info: JQuantsListedInfo[] }>("/listed/info");
      const matches = (data.info ?? [])
        .filter(
          (c) =>
            c.CompanyName.includes(keyword) ||
            c.CompanyNameEnglish?.toLowerCase().includes(keyword.toLowerCase()) ||
            c.Code === keyword
        )
        .slice(0, limit)
        .map(
          (info): Security => ({
            ticker: info.Code,
            market: "JP",
            name: info.CompanyName,
            nameEn: info.CompanyNameEnglish || undefined,
            sector: info.Sector17CodeName || undefined,
            listingDate: info.ListingDate || undefined,
            currency: "JPY",
          })
        );
      return ok(matches);
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }

  // ── PriceAdapter ─────────────────────────────────────────

  async getDailyBars(ticker: string, from: string, to: string): Promise<Result<PriceBar[]>> {
    try {
      // V2 endpoint: /prices/daily_quotes (replaces /equities/bars/daily)
      const data = await this.get<{ daily_quotes: JQuantsDailyQuote[] }>(
        "/prices/daily_quotes",
        { code: ticker, date_from: from, date_to: to }
      );
      const bars = (data.daily_quotes ?? []).map(
        (b): PriceBar => ({
          ticker: b.Code,
          market: "JP",
          date: b.Date,
          open: b.Open ?? 0,
          high: b.High ?? 0,
          low: b.Low ?? 0,
          close: b.Close ?? 0,
          volume: b.Volume ?? 0,
          adjustedClose: b.AdjustmentClose ?? undefined,
        })
      );
      return ok(bars);
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }

  async getLatestPrice(ticker: string): Promise<Result<PriceBar>> {
    const today = new Date().toISOString().slice(0, 10);
    // J-Quants: go back 7 days to handle weekends/holidays
    const weekAgo = new Date(Date.now() - 7 * 86_400_000).toISOString().slice(0, 10);
    const result = await this.getDailyBars(ticker, weekAgo, today);
    if (!result.ok) return result;
    const bars = result.data;
    if (bars.length === 0) return err(new Error(`No price data for ${ticker}`));
    // Last bar = most recent
    return ok(bars[bars.length - 1]!);
  }

  // ── FinancialStatementsAdapter ───────────────────────────
  // NOTE: Financial statements require Premium tier in J-Quants.
  // These stubs return a clear error so the agent can fall back to EDINET.

  async getIncomeStatements(ticker: string): Promise<Result<IncomeStatement[]>> {
    return err(
      new Error(
        `J-Quants free tier: income statements not available for ${ticker}. ` +
          "Use EDINET adapter for 有価証券報告書 data."
      )
    );
  }

  async getBalanceSheets(ticker: string): Promise<Result<BalanceSheet[]>> {
    return err(
      new Error(
        `J-Quants free tier: balance sheets not available for ${ticker}. ` +
          "Use EDINET adapter for 有価証券報告書 data."
      )
    );
  }
}
