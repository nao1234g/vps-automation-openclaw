/**
 * DossierBuilder — structured company research layer
 *
 * Calls all available adapters in parallel and assembles a typed Dossier.
 * Never throws: all errors are captured per-adapter; partial data is fine.
 *
 * Design: adapters are optional at runtime — the dossier will contain
 * whatever data is actually available from configured providers.
 */

import { ok } from "@equity/domain";
import type { Result, Market, Dossier, FreshnessMetadata, PriceDelta } from "@equity/domain";
import type { AdapterRegistry } from "@equity/adapters";
import { ChatAnthropic } from "@langchain/anthropic";
import { readPreviousDossier } from "@equity/walltalk";

export interface DossierBuildOptions {
  /** How many financial statement periods to fetch (default: 4) */
  financialPeriods?: number;
  /** Max number of filings to fetch (default: 5) */
  filingLimit?: number;
  /** Fetch news/context via search adapter (default: true when adapter available) */
  includeNews?: boolean;
  /** Custom news query — defaults to "{ticker} {companyName} 最近 決算" */
  newsQuery?: string;
  /** Generate LLM executive summary (default: true) */
  generateSummary?: boolean;
  /** Inject past judgment context from JudgmentMemory (placed in analystNotes) */
  priorJudgmentContext?: string;
  /**
   * Compare current dossier with most recent prior dossier to compute priceDelta.
   * Requires a prior dossier to exist in walltalk output dir (default: true).
   */
  computePriorDiff?: boolean;
}

export interface DossierBuildSources {
  security: boolean;
  latestPrice: boolean;
  incomeStatements: number;
  balanceSheets: number;
  recentFilings: number;
  newsItems: number;
  summaryGenerated: boolean;
}

export async function buildDossier(
  ticker: string,
  market: Market,
  registry: AdapterRegistry,
  options: DossierBuildOptions = {}
): Promise<Result<Dossier>> {
  const {
    financialPeriods = 4,
    filingLimit = 5,
    includeNews = true,
    newsQuery,
    generateSummary = true,
    priorJudgmentContext,
    computePriorDiff = true,
  } = options;

  const createdAt = new Date().toISOString();

  // ── Step 1: Security metadata ────────────────────────────────
  const secAdapter = registry.getSecurityAdapter(market);
  let security: Dossier["security"] = undefined;
  if (secAdapter) {
    const r = await secAdapter.getSecurity(ticker).catch(() => null);
    if (r?.ok) security = r.data;
  }

  // ── Step 2 & 3: Price + Financials in parallel ───────────────
  const priceAdapter = registry.getPriceAdapter(market);
  const financialsAdapter = registry.getFinancialsAdapter(market);

  const [priceResult, incomeResult, bsResult] = await Promise.all([
    priceAdapter
      ? priceAdapter.getLatestPrice(ticker).catch(() => null)
      : Promise.resolve(null),
    financialsAdapter
      ? financialsAdapter
          .getIncomeStatements(ticker, financialPeriods)
          .catch(() => null)
      : Promise.resolve(null),
    financialsAdapter
      ? financialsAdapter
          .getBalanceSheets(ticker, financialPeriods)
          .catch(() => null)
      : Promise.resolve(null),
  ]);

  const latestPrice =
    priceResult?.ok ? priceResult.data : undefined;
  const incomeStatements =
    incomeResult?.ok ? incomeResult.data : [];
  const balanceSheets =
    bsResult?.ok ? bsResult.data : [];

  // ── Step 4: Recent filings ──────────────────────────────────
  const filingsAdapter = registry.getFilingsAdapter(market);
  let recentFilings: Dossier["recentFilings"] = [];
  if (filingsAdapter) {
    const r = await filingsAdapter
      .listFilings(ticker, undefined, filingLimit)
      .catch(() => null);
    if (r?.ok) recentFilings = r.data;
  }

  // ── Step 5: News context ────────────────────────────────────
  const searchAdapter = registry.getSearchAdapter();
  let newsItems: Array<{ title: string; url: string; snippet: string }> = [];
  if (includeNews && searchAdapter) {
    const q =
      newsQuery ??
      `${ticker} ${security?.name ?? ""} 最近 ニュース 決算`.trim();
    const r = await searchAdapter.search(q, 5).catch(() => null);
    if (r?.ok) newsItems = r.data;
  }

  // ── Step 6: Assemble analystNotes (freshness + news + priors) ──
  const sources: DossierBuildSources = {
    security: !!security,
    latestPrice: !!latestPrice,
    incomeStatements: incomeStatements.length,
    balanceSheets: balanceSheets.length,
    recentFilings: recentFilings.length,
    newsItems: newsItems.length,
    summaryGenerated: false, // updated below
  };

  const priceStr = latestPrice
    ? `${latestPrice.close.toLocaleString()} ${security?.currency ?? ""} (${latestPrice.date})`
    : "未取得";

  const freshnessSection =
    `## データ取得情報\n` +
    `- **取得日時**: ${createdAt}\n` +
    `- **市場/ティッカー**: ${market} / ${ticker}\n` +
    `- **銘柄マスター**: ${security ? security.name : "未取得"}\n` +
    `- **最新株価**: ${priceStr}\n` +
    `- **損益計算書**: ${incomeStatements.length}件\n` +
    `- **貸借対照表**: ${balanceSheets.length}件\n` +
    `- **最新開示書類**: ${recentFilings.length}件`;

  const newsSection =
    newsItems.length > 0
      ? `\n\n## 最新ニュース・コンテキスト\n` +
        newsItems
          .map((n) => `- [${n.title}](${n.url})\n  ${n.snippet}`)
          .join("\n")
      : "";

  const priorSection = priorJudgmentContext
    ? `\n\n## 過去の判断コンテキスト\n${priorJudgmentContext}`
    : "";

  const analystNotes = freshnessSection + newsSection + priorSection;

  // ── Step 6.5: Structured freshness metadata ─────────────────
  const freshnessMetadata: FreshnessMetadata = {
    fetchedAt: createdAt,
    market,
    ticker,
    securityFetched: !!security,
    latestPriceFetched: !!latestPrice,
    incomeStatementsCount: incomeStatements.length,
    balanceSheetsCount: balanceSheets.length,
    recentFilingsCount: recentFilings.length,
    newsItemsCount: newsItems.length,
    summaryGenerated: false, // updated below
    priceDate: latestPrice?.date,
  };

  // ── Step 6.6: Compute priceDelta vs prior dossier (optional) ──
  let priorDossierDate: string | undefined;
  let priceDelta: PriceDelta | undefined;

  if (computePriorDiff && latestPrice) {
    try {
      const today = createdAt.slice(0, 10);
      const priorDossier = await readPreviousDossier(ticker, today);
      if (priorDossier?.latestPrice) {
        const priorPrice = priorDossier.latestPrice.close;
        const currentPrice = latestPrice.close;
        const changeAbsolute = currentPrice - priorPrice;
        const changePercent =
          priorPrice !== 0
            ? Math.round((changeAbsolute / priorPrice) * 10000) / 100
            : 0;
        priceDelta = {
          priorPrice,
          currentPrice,
          priorDate: priorDossier.latestPrice.date,
          currentDate: latestPrice.date,
          changeAbsolute: Math.round(changeAbsolute * 100) / 100,
          changePercent,
          currency: security?.currency ?? "JPY",
        };
        priorDossierDate = priorDossier.createdAt.slice(0, 10);
      }
    } catch {
      // Prior dossier diff is optional enrichment — silently skip
    }
  }

  // ── Step 7: LLM executive summary (optional) ────────────────
  let summary: string | undefined;
  if (generateSummary && security) {
    try {
      const llm = new ChatAnthropic({
        model: "claude-opus-4-6",
        maxTokens: 400,
      });

      const latestIncome = incomeStatements[0];
      const latestBS = balanceSheets[0];

      const finSnippet = latestIncome
        ? `\n- 売上: ${latestIncome.revenue?.toLocaleString() ?? "N/A"} ${latestIncome.currency} (${latestIncome.periodEnd})\n` +
          `- 純利益: ${latestIncome.netIncome?.toLocaleString() ?? "N/A"} ${latestIncome.currency}`
        : "";
      const bsSnippet = latestBS
        ? `\n- 総資産: ${latestBS.totalAssets?.toLocaleString() ?? "N/A"} ${latestBS.currency}\n` +
          `- 自己資本: ${latestBS.shareholdersEquity?.toLocaleString() ?? "N/A"} ${latestBS.currency}`
        : "";
      const recentFilingStr =
        recentFilings.length > 0
          ? `\n最新開示: ${recentFilings[0]!.filingType} (${recentFilings[0]!.filedAt.slice(0, 10)})`
          : "";

      const prompt =
        `アナリストとして、以下の企業データを元に200字以内のエグゼクティブサマリーを日本語で作成してください。\n\n` +
        `企業名: ${security.name}${security.nameEn ? ` (${security.nameEn})` : ""}\n` +
        `市場: ${market} / ティッカー: ${ticker}\n` +
        `セクター: ${security.sector ?? "不明"}\n` +
        `最新株価: ${priceStr}${finSnippet}${bsSnippet}${recentFilingStr}\n\n` +
        `エグゼクティブサマリー（200字以内）:`;

      const res = await llm.invoke(prompt);
      if (typeof res.content === "string") {
        summary = res.content.trim();
        sources.summaryGenerated = true;
        freshnessMetadata.summaryGenerated = true;
      }
    } catch {
      // Summary is optional enrichment — silently continue without it
    }
  }

  const dossier: Dossier = {
    ticker,
    market,
    createdAt,
    security,
    latestPrice,
    incomeStatements,
    balanceSheets,
    recentFilings,
    risks: [],        // populated by extractRisks() in thesis/builder
    analystNotes,
    summary,
    freshnessMetadata,
    priorDossierDate,
    priceDelta,
  };

  return ok(dossier);
}
