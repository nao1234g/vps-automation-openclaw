/**
 * CompareCompanies — multi-company dossier comparison
 *
 * Builds a dossier for each target company (in parallel) and asks the LLM
 * to compare them on the specified dimension/question.
 *
 * Output is intentionally kept in services (not walltalk) because:
 *   - Comparison requires LLM reasoning across multiple dossiers
 *   - walltalk is a read-only artifact boundary; writing comparisons is
 *     done via walltalk's writeScreenerResult (ScreenerResult schema)
 */

import { ok, err } from "@equity/domain";
import type { Result, Market, Dossier } from "@equity/domain";
import type { AdapterRegistry } from "@equity/adapters";
import { callClaudeText } from "../llm/claude_code_backend.js";
import { buildDossier } from "../dossier/builder.js";
import type { DossierBuildOptions } from "../dossier/builder.js";

// ── Types ────────────────────────────────────────────────────────────────────

export interface CompareTarget {
  ticker: string;
  market: Market;
}

export interface CompareResult {
  /** All targets that were compared */
  targets: CompareTarget[];
  /** The successfully built dossiers (may be fewer than targets if some failed) */
  dossiers: Dossier[];
  /** Original question/dimension provided by caller */
  question?: string;
  /** LLM-generated structured comparison */
  analysis: string;
  /** Ticker of recommended focus (may be undefined for neutral comparisons) */
  winner?: string;
  /** Concise ranking with rationale, keyed by ticker */
  rankings: Record<string, { rank: number; rationale: string }>;
  generatedAt: string;
  /** Key judgment differences between the companies (2–4 points) */
  judgmentDifferences: string[];
  /** Decision-critical factors per ticker that make it unique vs. peers */
  pivotPoints: Record<string, string[]>;
}

// ── compareCompanies ─────────────────────────────────────────────────────────

export interface CompareOptions {
  dossierOptions?: DossierBuildOptions;
  language?: "ja" | "en";
}

export async function compareCompanies(
  targets: CompareTarget[],
  registry: AdapterRegistry,
  question?: string,
  options: CompareOptions = {}
): Promise<Result<CompareResult>> {
  if (targets.length < 2) {
    return err(new Error("compareCompanies requires at least 2 targets"));
  }

  const { dossierOptions = {}, language = "ja" } = options;
  const generatedAt = new Date().toISOString();

  // ── Step 1: Build dossiers in parallel ──────────────────────────────
  const dossierResults = await Promise.all(
    targets.map((t) =>
      buildDossier(t.ticker, t.market, registry, {
        ...dossierOptions,
        generateSummary: true,
      })
    )
  );

  const dossiers: Dossier[] = [];
  const failedTargets: string[] = [];

  for (let i = 0; i < dossierResults.length; i++) {
    const r = dossierResults[i]!;
    if (r.ok) {
      dossiers.push(r.data);
    } else {
      failedTargets.push(`${targets[i]!.ticker} (${r.error.message})`);
    }
  }

  if (dossiers.length < 2) {
    return err(
      new Error(
        `Not enough dossiers built (${dossiers.length}/${targets.length}). Failures: ${failedTargets.join(", ")}`
      )
    );
  }

  // ── Step 2: Build comparison prompt ─────────────────────────────────
  const dossierSummaries = dossiers.map((d) => {
    const co = d.security;
    const latestIncome = d.incomeStatements[0];
    const latestBS = d.balanceSheets[0];
    const priceLine = d.latestPrice
      ? `株価: ${d.latestPrice.close.toLocaleString()} (${d.latestPrice.date})`
      : "株価: 未取得";
    const finLine = latestIncome
      ? `売上: ${latestIncome.revenue?.toLocaleString() ?? "N/A"}, 純利益: ${latestIncome.netIncome?.toLocaleString() ?? "N/A"}`
      : "財務: 未取得";
    const bsLine = latestBS
      ? `総資産: ${latestBS.totalAssets?.toLocaleString() ?? "N/A"}, 自己資本: ${latestBS.shareholdersEquity?.toLocaleString() ?? "N/A"}`
      : "";
    const summaryLine = d.summary ? `サマリー: ${d.summary}` : "";

    return (
      `【${d.market}:${d.ticker}】${co ? ` ${co.name}` : ""}\n` +
      `  ${priceLine}\n` +
      `  ${finLine}\n` +
      (bsLine ? `  ${bsLine}\n` : "") +
      (summaryLine ? `  ${summaryLine}\n` : "")
    );
  }).join("\n");

  const questionLine = question
    ? `\n比較の観点: 「${question}」\n`
    : "\n総合的な競合比較を行ってください。\n";

  const langInstruction =
    language === "en"
      ? "Respond in English."
      : "日本語で回答してください。";

  const tickerList = dossiers.map((d) => d.ticker).join(", ");

  const prompt =
    `あなたはシニアエクイティアナリストです。以下の${dossiers.length}社を比較分析してください。${questionLine}\n` +
    `${dossierSummaries}\n` +
    `以下の形式で回答してください（JSON）:\n` +
    `{\n` +
    `  "analysis": "詳細な比較分析（マークダウン形式、400〜600字）",\n` +
    `  "winner": "${tickerList}のいずれか、または null（中立の場合）",\n` +
    `  "rankings": {\n` +
    `    "<ticker>": { "rank": <1始まりの整数>, "rationale": "<30字以内の理由>" },\n` +
    `    ...\n` +
    `  },\n` +
    `  "judgmentDifferences": [\n` +
    `    "各社の投資判断に影響する主要な差異（2〜4件）"\n` +
    `  ],\n` +
    `  "pivotPoints": {\n` +
    `    "<ticker>": ["この銘柄固有の判断ポイント（2〜3件）"],\n` +
    `    ...\n` +
    `  }\n` +
    `}\n\n` +
    `${langInstruction}`;

  // ── Step 3: LLM comparison ───────────────────────────────────────────
  let analysis = "";
  let winner: string | undefined;
  const rankings: CompareResult["rankings"] = {};
  let judgmentDifferences: string[] = [];
  const pivotPoints: CompareResult["pivotPoints"] = {};

  const llmResult = await callClaudeText(prompt);
  if (!llmResult.ok) return err(llmResult.error);

  try {
    const raw = llmResult.data.trim();

    // Try to parse JSON response
    const jsonMatch = raw.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]) as {
        analysis?: string;
        winner?: string | null;
        rankings?: Record<string, { rank: number; rationale: string }>;
        judgmentDifferences?: string[];
        pivotPoints?: Record<string, string[]>;
      };
      analysis = parsed.analysis ?? raw;
      winner = parsed.winner ?? undefined;
      if (parsed.rankings) {
        Object.assign(rankings, parsed.rankings);
      }
      if (Array.isArray(parsed.judgmentDifferences)) {
        judgmentDifferences = parsed.judgmentDifferences;
      }
      if (parsed.pivotPoints && typeof parsed.pivotPoints === "object") {
        Object.assign(pivotPoints, parsed.pivotPoints);
      }
    } else {
      // Fallback: treat entire response as analysis text
      analysis = raw;
    }
  } catch (e) {
    return err(e instanceof Error ? e : new Error(String(e)));
  }

  return ok({
    targets,
    dossiers,
    question,
    analysis,
    winner: winner ?? undefined,
    rankings,
    generatedAt,
    judgmentDifferences,
    pivotPoints,
  });
}
