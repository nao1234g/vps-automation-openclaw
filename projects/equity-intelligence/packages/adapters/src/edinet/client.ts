/**
 * EDINET Adapter (FSA — Financial Services Agency)
 * https://api.edinet-fsa.go.jp/api/v2/
 *
 * Auth: Ocp-Apim-Subscription-Key header (preferred) or query param
 * CRITICAL: Server-side only. Cannot be called from browser.
 * CRITICAL: 3–5 second intervals REQUIRED between requests. Rapid calls → connection drop.
 *
 * Data scope: 11,000+ companies (listed and unlisted)
 * Document types: 有価証券報告書 (120), 四半期報告書 (140), 決算短信, 臨時報告書, etc.
 *
 * Key limitation: Date-based queries only — no /companies/{id}/filings endpoint.
 * Strategy: Search by date range, then filter by company EDINETCode.
 */

import { ok, err } from "@equity/domain";
import type { Result, Filing, FilingType } from "@equity/domain";
import type { FilingsAdapter } from "../interfaces.js";

const EDINET_BASE = "https://api.edinet-fsa.go.jp/api/v2";

// EDINET document type code → our FilingType
const EDINET_DOC_TYPE_MAP: Record<string, FilingType> = {
  "120": "有価証券報告書",
  "140": "四半期報告書",
  "160": "有価証券報告書",   // semi-annual → map to annual for simplicity
  "180": "臨時報告書",
  "350": "大量保有報告書",
};

interface EdinetDocument {
  docID: string;
  edinetCode: string;
  filerName: string;
  docTypeCode: string;
  periodEnd: string | null;
  submitDateTime: string;
  docDescription: string;
  pdfFlag: string;
  csvFlag: string;
  xbrlFlag: string;
}

interface EdinetDocListResponse {
  metadata: {
    count: number;
    resultset: { count: number };
    status: string;
    message: string;
  };
  results: EdinetDocument[];
}

// Cache: ticker → edinetCode mapping (populated lazily)
const tickerToEdinetCode = new Map<string, string>();

export class EdinetAdapter implements FilingsAdapter {
  readonly market = "JP" as const;
  readonly name = "EDINET (FSA)";

  private readonly subscriptionKey: string;
  private readonly baseUrl: string;

  // Minimum interval between requests (ms) — EDINET requirement
  private readonly minInterval = 3500;
  private lastRequestAt = 0;

  constructor(subscriptionKey: string, baseUrl = EDINET_BASE) {
    if (!subscriptionKey) throw new Error("EDINET_SUBSCRIPTION_KEY is required");
    this.subscriptionKey = subscriptionKey;
    this.baseUrl = baseUrl;
  }

  // ── Rate-limited fetch ────────────────────────────────────

  private async rateLimitedFetch(url: string): Promise<Response> {
    const now = Date.now();
    const elapsed = now - this.lastRequestAt;
    if (elapsed < this.minInterval) {
      await new Promise((r) => setTimeout(r, this.minInterval - elapsed));
    }
    this.lastRequestAt = Date.now();

    return fetch(url, {
      headers: { "Ocp-Apim-Subscription-Key": this.subscriptionKey },
    });
  }

  private async getDocList(date: string): Promise<EdinetDocument[]> {
    // type=2 → documents with metadata (not just header)
    const url = `${this.baseUrl}/documents.json?date=${date}&type=2&Subscription-Key=${this.subscriptionKey}`;
    const res = await this.rateLimitedFetch(url);
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`EDINET documents.json ${date} → ${res.status}: ${body}`);
    }
    const data = (await res.json()) as EdinetDocListResponse;
    return data.results ?? [];
  }

  // ── Public interface ──────────────────────────────────────

  async ping(): Promise<boolean> {
    try {
      const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
      await this.getDocList(yesterday);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * List filings for a company.
   * Strategy: search last `lookbackDays` days for matching company.
   * EDINET has no company-centric endpoint, so we search by date.
   */
  async listFilings(
    ticker: string,
    types?: FilingType[],
    limit = 10,
    lookbackDays = 365
  ): Promise<Result<Filing[]>> {
    try {
      const results: Filing[] = [];
      const today = new Date();

      // Resolve ticker → company name pattern for matching
      // (EDINET doesn't directly map JPX ticker codes)
      // We look for the company name in filerName via a broad search.
      // For production use: maintain a ticker→edinetCode mapping table.
      let cachedCode = tickerToEdinetCode.get(ticker);

      // Search backwards day by day until we have enough results
      for (let i = 0; i < lookbackDays && results.length < limit; i++) {
        const date = new Date(today.getTime() - i * 86_400_000)
          .toISOString()
          .slice(0, 10);

        let docs: EdinetDocument[];
        try {
          docs = await this.getDocList(date);
        } catch {
          continue; // Skip holidays / no-data days
        }

        for (const doc of docs) {
          // Match by cached edinetCode or by ticker in description
          const isMatch =
            (cachedCode && doc.edinetCode === cachedCode) ||
            doc.docDescription?.includes(ticker) ||
            doc.filerName?.includes(ticker);

          if (!isMatch) continue;

          // Cache the edinetCode for future requests
          if (!cachedCode) {
            cachedCode = doc.edinetCode;
            tickerToEdinetCode.set(ticker, cachedCode);
          }

          const rawType = EDINET_DOC_TYPE_MAP[doc.docTypeCode];
          if (types && rawType && !types.includes(rawType)) continue;

          results.push({
            id: doc.docID,
            ticker,
            companyName: doc.filerName,
            market: "JP",
            filingType: rawType ?? "OTHER",
            filedAt: doc.submitDateTime,
            periodEnd: doc.periodEnd ?? undefined,
            url: `https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S1,${doc.docID}`,
            raw: doc as unknown as Record<string, unknown>,
          });

          if (results.length >= limit) break;
        }
      }

      return ok(results);
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }

  /**
   * Fetch filing content.
   * Returns a markdown summary of the filing metadata + download link.
   * Full XBRL parsing is beyond the scope of the stub — extend as needed.
   */
  async getFilingContent(filingId: string): Promise<Result<string>> {
    try {
      // Download ZIP (type=1) contains XBRL. For now return metadata + link.
      const url = `${this.baseUrl}/documents/${filingId}?type=2&Subscription-Key=${this.subscriptionKey}`;
      const res = await this.rateLimitedFetch(url);
      if (!res.ok) {
        return err(new Error(`EDINET filing ${filingId} → ${res.status}`));
      }
      const data = (await res.json()) as Record<string, unknown>;

      const content = [
        `# EDINET Filing: ${filingId}`,
        `**Company**: ${data.filerName ?? "N/A"}`,
        `**Type**: ${data.docTypeCode ?? "N/A"} — ${data.docDescription ?? ""}`,
        `**Filed**: ${data.submitDateTime ?? "N/A"}`,
        `**Period**: ${data.periodEnd ?? "N/A"}`,
        ``,
        `Download full XBRL data:`,
        `https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S1,${filingId}`,
      ].join("\n");

      return ok(content);
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }
}
