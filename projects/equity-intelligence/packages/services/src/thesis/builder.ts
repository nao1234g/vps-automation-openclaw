/**
 * ThesisBuilder — LLM-driven investment thesis generation
 *
 * Consumes a Dossier (already assembled data) and produces:
 *   1. A structured Thesis with stance, conviction, catalysts, risks, body
 *   2. Extracted RiskNotes for the dossier.risks field
 *
 * The LLM generates JSON output which is validated with Zod before returning.
 */

import { z } from "zod";
import { ok, err } from "@equity/domain";
import type { Result, Dossier, Thesis, RiskNote } from "@equity/domain";
import { callClaudeJson } from "../llm/claude_code_backend.js";

// ── Output schema for LLM structured output ────────────────────────────────

const ThesisLlmOutputSchema = z.object({
  title: z.string().describe("Thesis title (concise, ≤60 chars)"),
  stance: z
    .enum(["bullish", "bearish", "neutral"])
    .describe("Overall investment stance"),
  horizon: z
    .enum(["short", "medium", "long"])
    .describe("Investment horizon: short <3m, medium 3-12m, long >12m"),
  conviction: z
    .enum(["low", "medium", "high"])
    .describe("Confidence level given available data quality"),
  targetPrice: z.number().nullable().describe("Target price (null if uncertain)"),
  catalysts: z.array(z.string()).describe("3–5 key positive catalysts"),
  risks: z
    .array(
      z.object({
        category: z.enum([
          "market",
          "regulatory",
          "execution",
          "financial",
          "geopolitical",
          "other",
        ]),
        severity: z.enum(["low", "medium", "high"]),
        description: z.string(),
      })
    )
    .describe("2–4 material risks"),
  body: z
    .string()
    .describe(
      "Full thesis in markdown format (400–800 chars). Cover: bull/bear case, key assumption, open questions."
    ),
  references: z.array(z.string()).describe("Filing IDs or URLs used as evidence"),
  // ── Judgment depth ──────────────────────────────────────────────────────────
  openQuestions: z
    .array(z.string())
    .describe("2–4 open questions whose answers could change this thesis"),
  bullCase: z
    .string()
    .describe("Strongest bull case argument in 1–2 sentences"),
  bearCase: z
    .string()
    .describe("Strongest bear case argument in 1–2 sentences"),
  invalidationPoints: z
    .array(z.string())
    .describe("2–3 specific conditions that would invalidate this thesis"),
  changeFromPrior: z
    .string()
    .nullable()
    .describe(
      "If a prior thesis is provided: briefly describe what changed (stance/conviction/catalysts). null if no prior."
    ),
});

type ThesisLlmOutput = z.infer<typeof ThesisLlmOutputSchema>;

// ── Options ─────────────────────────────────────────────────────────────────

export interface ThesisBuildOptions {
  /** Force a specific stance (skips LLM stance detection) */
  stance?: "bullish" | "bearish" | "neutral";
  /** Force a specific horizon */
  horizon?: "short" | "medium" | "long";
  /** Additional context to inject into the prompt */
  additionalContext?: string;
  /** Language for thesis body: "ja" (default) or "en" */
  language?: "ja" | "en";
  /**
   * Reference to the most recent prior thesis for this ticker.
   * When provided, the LLM will compare and surface changeFromPrior,
   * and the builder will compute stanceChanged automatically.
   */
  priorThesisRef?: {
    thesisId: string;
    stance: "bullish" | "bearish" | "neutral";
    conviction: "low" | "medium" | "high";
    title: string;
    createdAt: string;
  };
}

// ── buildThesis ──────────────────────────────────────────────────────────────

export async function buildThesis(
  dossier: Dossier,
  options: ThesisBuildOptions = {}
): Promise<Result<Thesis>> {
  const { stance, horizon, additionalContext, language = "ja", priorThesisRef } = options;

  // Build prompt from dossier data
  const companyLine =
    dossier.security
      ? `${dossier.security.name}${dossier.security.nameEn ? ` (${dossier.security.nameEn})` : ""} — ${dossier.market}:${dossier.ticker}`
      : `${dossier.market}:${dossier.ticker}`;

  const priceSnippet = dossier.latestPrice
    ? `最新株価: ${dossier.latestPrice.close.toLocaleString()} ${dossier.security?.currency ?? ""} (${dossier.latestPrice.date})`
    : "株価: 未取得";

  const latestIncome = dossier.incomeStatements[0];
  const finSnippet = latestIncome
    ? `売上: ${latestIncome.revenue?.toLocaleString() ?? "N/A"} / 純利益: ${latestIncome.netIncome?.toLocaleString() ?? "N/A"} (${latestIncome.periodEnd})`
    : "財務データ: 未取得";

  const filingSnippet =
    dossier.recentFilings.length > 0
      ? `最新開示: ${dossier.recentFilings
          .slice(0, 3)
          .map((f) => `${f.filingType} (${f.filedAt.slice(0, 10)})`)
          .join(", ")}`
      : "開示書類: 未取得";

  const summaryBlock = dossier.summary
    ? `\n\nサマリー:\n${dossier.summary}`
    : "";

  const newsBlock = dossier.analystNotes?.includes("## 最新ニュース")
    ? `\n\nニュースコンテキスト:\n${dossier.analystNotes.split("## 最新ニュース")[1]?.split("##")[0] ?? ""}`
    : "";

  const priorThesisBlock = priorThesisRef
    ? `\n\n## 前回テーゼ（変化の比較に使用）\n` +
      `- ID: ${priorThesisRef.thesisId}\n` +
      `- スタンス: ${priorThesisRef.stance} / コンビクション: ${priorThesisRef.conviction}\n` +
      `- タイトル: ${priorThesisRef.title}\n` +
      `- 作成日: ${priorThesisRef.createdAt.slice(0, 10)}\n` +
      `前回との変化を "changeFromPrior" に記述してください。変化なければ null。`
    : "";

  const constraintBlock =
    [
      stance ? `スタンスは必ず "${stance}" にすること` : "",
      horizon ? `ホライゾンは必ず "${horizon}" にすること` : "",
      additionalContext ?? "",
    ]
      .filter(Boolean)
      .join("\n") || "";

  const langInstruction =
    language === "en"
      ? "Write the 'body' field in English."
      : "「body」フィールドは日本語で書くこと。";

  const prompt =
    `あなたはエクイティアナリストです。以下の企業データを元に、投資テーゼを構造化JSONで出力してください。\n\n` +
    `企業: ${companyLine}\n` +
    `${priceSnippet}\n` +
    `${finSnippet}\n` +
    `${filingSnippet}${summaryBlock}${newsBlock}${priorThesisBlock}\n\n` +
    (constraintBlock ? `制約:\n${constraintBlock}\n\n` : "") +
    `${langInstruction}\n` +
    `参照IDはdossierの開示書類IDを使用してください。データが不十分な場合はconviction="low"にすること。\n\n` +
    `以下の正確なJSONスキーマに従って出力すること。フィールド名を変えたり、ラッパーオブジェクトを追加したりしないこと。\n` +
    `{\n` +
    `  "title": "<テーゼタイトル（60字以内）>",\n` +
    `  "stance": "bullish" | "bearish" | "neutral",\n` +
    `  "horizon": "short" | "medium" | "long",\n` +
    `  "conviction": "low" | "medium" | "high",\n` +
    `  "targetPrice": <数値 or null>,\n` +
    `  "catalysts": ["<文字列>", ...],\n` +
    `  "risks": [{"category": "market"|"regulatory"|"execution"|"financial"|"geopolitical"|"other", "severity": "low"|"medium"|"high", "description": "<文字列>"}],\n` +
    `  "body": "<マークダウン形式のテーゼ本文（400〜800字）>",\n` +
    `  "references": ["<開示書類IDまたはURL>"],\n` +
    `  "openQuestions": ["<文字列>", ...],\n` +
    `  "bullCase": "<強気論拠（1〜2文の文字列）>",\n` +
    `  "bearCase": "<弱気論拠（1〜2文の文字列）>",\n` +
    `  "invalidationPoints": ["<文字列>", ...],\n` +
    `  "changeFromPrior": "<前回テーゼとの変化の説明>" | null\n` +
    `}\n` +
    `重要: "bullCase"と"bearCase"は必ず文字列（string）で返すこと。オブジェクトや配列にしてはいけない。\n` +
    `重要: トップレベルのキーは上記14個のみ。"ticker"、"thesis"、"metadata"等の余分なキーを追加しないこと。`;

  const llmResult = await callClaudeJson<ThesisLlmOutput>(prompt);
  if (!llmResult.ok) return err(llmResult.error);
  const llmOutput = llmResult.data;

  // Validate and coerce
  const parsed = ThesisLlmOutputSchema.safeParse(llmOutput);
  if (!parsed.success) {
    return err(new Error(`Thesis LLM output validation failed: ${parsed.error.message}`));
  }

  const now = new Date().toISOString();
  const id = `thesis-${dossier.ticker.toLowerCase()}-${Date.now()}`;

  const thesis: Thesis = {
    id,
    ticker: dossier.ticker,
    market: dossier.market,
    createdAt: now,
    updatedAt: now,
    title: parsed.data.title,
    stance: parsed.data.stance,
    horizon: parsed.data.horizon,
    conviction: parsed.data.conviction,
    targetPrice: parsed.data.targetPrice ?? undefined,
    targetCurrency: dossier.security?.currency,
    catalysts: parsed.data.catalysts,
    risks: parsed.data.risks,
    body: parsed.data.body,
    references: parsed.data.references,
    version: 1,
    // ── Judgment depth fields ─────────────────────────────────────────────────
    openQuestions: parsed.data.openQuestions,
    bullCase: parsed.data.bullCase,
    bearCase: parsed.data.bearCase,
    invalidationPoints: parsed.data.invalidationPoints,
    // ── Change tracking vs prior thesis ──────────────────────────────────────
    ...(priorThesisRef && {
      priorThesisId: priorThesisRef.thesisId,
      stanceChanged: parsed.data.stance !== priorThesisRef.stance,
      changeFromPrior: parsed.data.changeFromPrior ?? undefined,
    }),
  };

  return ok(thesis);
}

// ── extractRisks ─────────────────────────────────────────────────────────────

const RiskExtractionSchema = z.object({
  risks: z.array(
    z.object({
      category: z.enum([
        "market",
        "regulatory",
        "execution",
        "financial",
        "geopolitical",
        "other",
      ]),
      severity: z.enum(["low", "medium", "high"]),
      description: z.string(),
      evidence: z.string().optional(),
    })
  ),
});

/**
 * Extract structured RiskNotes from a Dossier without building a full thesis.
 * Useful for populating dossier.risks from financial data + news context.
 */
export async function extractRisks(dossier: Dossier): Promise<Result<RiskNote[]>> {
  const latestIncome = dossier.incomeStatements[0];
  const latestBS = dossier.balanceSheets[0];

  const context =
    `企業: ${dossier.ticker} (${dossier.market})\n` +
    (dossier.security ? `セクター: ${dossier.security.sector ?? "不明"}\n` : "") +
    (latestIncome
      ? `最新損益: 売上=${latestIncome.revenue?.toLocaleString() ?? "N/A"}, 純利益=${latestIncome.netIncome?.toLocaleString() ?? "N/A"}\n`
      : "") +
    (latestBS
      ? `最新BS: 総資産=${latestBS.totalAssets?.toLocaleString() ?? "N/A"}, 自己資本=${latestBS.shareholdersEquity?.toLocaleString() ?? "N/A"}\n`
      : "") +
    (dossier.recentFilings.length > 0
      ? `開示: ${dossier.recentFilings.map((f) => f.filingType).join(", ")}\n`
      : "");

  const prompt =
    `以下の企業情報から、主要なリスク要因を3〜5件抽出して構造化JSONで返してください。\n\n` +
    `${context}\n` +
    `各リスクにはcategory、severity、descriptionを必ず含めてください。evidenceは任意。`;

  const llmResult = await callClaudeJson<z.infer<typeof RiskExtractionSchema>>(prompt);
  if (!llmResult.ok) return err(llmResult.error);
  const parsed = RiskExtractionSchema.safeParse(llmResult.data);
  if (!parsed.success) {
    return err(new Error(`Risk extraction validation failed: ${parsed.error.message}`));
  }
  return ok(parsed.data.risks);
}
