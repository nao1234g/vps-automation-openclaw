/**
 * Exa Adapter (optional semantic search)
 * https://exa.ai / https://docs.exa.ai
 *
 * Cost: $5 per 1,000 searches + $1 per 1,000 pages (full text)
 * Rate limit: 10 QPS default
 *
 * Use for: real-time financial news, earnings announcements, analyst commentary.
 * NOT a replacement for J-Quants or EDINET structured data.
 *
 * This adapter is optional — the registry skips it if EXASEARCH_API_KEY is absent.
 */

import { ok, err } from "@equity/domain";
import type { Result } from "@equity/domain";
import type { SearchAdapter, SearchResult } from "../interfaces.js";

const EXA_BASE = "https://api.exa.ai";

interface ExaSearchResponse {
  results: Array<{
    title: string;
    url: string;
    publishedDate?: string;
    text?: string;
    highlights?: string[];
    score: number;
  }>;
}

export class ExaAdapter implements SearchAdapter {
  readonly name = "Exa";

  private readonly apiKey: string;
  private readonly baseUrl: string;

  constructor(apiKey: string, baseUrl = EXA_BASE) {
    if (!apiKey) throw new Error("EXASEARCH_API_KEY is required for ExaAdapter");
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  async search(query: string, limit = 10): Promise<Result<SearchResult[]>> {
    try {
      const res = await fetch(`${this.baseUrl}/search`, {
        method: "POST",
        headers: {
          "x-api-key": this.apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query,
          numResults: limit,
          // Request text snippets (costs $1/1000 pages extra)
          contents: {
            text: { maxCharacters: 500 },
            highlights: { numSentences: 2 },
          },
          // Prefer recent financial news
          useAutoprompt: true,
          category: "news",
        }),
      });

      if (!res.ok) {
        const body = await res.text();
        return err(new Error(`Exa search → ${res.status}: ${body}`));
      }

      const data = (await res.json()) as ExaSearchResponse;

      const results: SearchResult[] = (data.results ?? []).map((r) => ({
        title: r.title ?? "",
        url: r.url,
        snippet: r.highlights?.[0] ?? r.text?.slice(0, 300) ?? "",
        publishedAt: r.publishedDate,
      }));

      return ok(results);
    } catch (e) {
      return err(e instanceof Error ? e : new Error(String(e)));
    }
  }
}
