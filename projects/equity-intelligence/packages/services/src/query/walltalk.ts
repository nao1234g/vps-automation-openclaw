/**
 * WalltalkQuery — natural language Q&A over equity artifacts
 *
 * Answers questions like:
 *   "この会社どう？"
 *   "直近決算の要点は？"
 *   "強み/弱みは？"
 *   "何が論点？"
 *   "過去の判断と比べて何が違う？"
 *   "類似ケースは？"
 *
 * Architecture:
 *   1. Detect question intent (diff | risk | history | general)
 *   2. Read latest dossier (file-based via walltalk readDossier)
 *   3. Read JudgmentStore (structured Layer 2 memory via walltalk readJudgment)
 *   4. Build context string → LLM → structured answer
 *
 * No direct adapter calls — uses pre-built artifacts only.
 * If no dossier exists, returns a helpful error message.
 */

import { readDossier, readJudgment } from "@equity/walltalk";
import type { Dossier, JudgmentStore } from "@equity/domain";
import { callClaudeText } from "../llm/claude_code_backend.js";
import { judgmentMemory } from "../judgment/memory.js";

// ── Types ────────────────────────────────────────────────────────────────────

export type QuestionIntent = "diff" | "risk" | "history" | "general";

export interface WalltalkQueryOptions {
  /** Include past thesis history in context (default: true) */
  includeHistory?: boolean;
  /** Max chars to include from each data section (default: 800) */
  maxContextLength?: number;
  /** Specific date of dossier to read (default: latest) */
  dossierDate?: string;
  /** Language override — default: auto-detect from question */
  language?: "ja" | "en";
}

export interface WalltalkQueryResult {
  /** The answer text */
  answer: string;
  /** Which data sources were used */
  sources: string[];
  /** Confidence signal based on available data quality */
  confidence: "low" | "medium" | "high";
  /** ISO datetime of when the answer was generated */
  generatedAt: string;
  /** ISO datetime of the dossier that was used (if any) */
  dossierDate?: string;
  /** Detected question intent */
  intentDetected: QuestionIntent;
  /** Summary of past judgment history (if available) */
  judgmentHistorySummary?: string;
  /** Top recurring risks from JudgmentStore (if available) */
  recurringRisks?: Array<{ description: string; severity: string; occurrences: number }>;
}

// ── Language detection ───────────────────────────────────────────────────────

function detectLanguage(text: string): "ja" | "en" {
  // CJK Unicode ranges (basic + extended)
  const cjkPattern = /[\u3000-\u9fff\uac00-\ud7af\uf900-\ufaff]/;
  return cjkPattern.test(text) ? "ja" : "en";
}

// ── Intent detection ─────────────────────────────────────────────────────────

/**
 * Classify question intent to route context assembly.
 *
 * - diff:     comparing with prior state / what changed?
 * - risk:     focusing on risks, concerns, downsides
 * - history:  asking about past judgments, prior theses
 * - general:  any other question
 */
function detectIntent(question: string): QuestionIntent {
  const q = question.toLowerCase();

  const diffPatterns = [
    "違う", "変わ", "変化", "前回", "比べ", "差", "アップデート",
    "changed", "differ", "update", "vs", "compare", "prior", "before",
    "what changed", "株価変化", "pricedelta",
  ];
  const riskPatterns = [
    "リスク", "懸念", "問題", "課題", "弱み", "不安", "危険",
    "risk", "concern", "downside", "weakness", "threat", "danger",
  ];
  const historyPatterns = [
    "過去", "以前", "履歴", "判断", "スタンス", "テーゼ", "前に",
    "history", "past", "previous", "stance", "thesis", "last time",
  ];

  if (diffPatterns.some((p) => q.includes(p))) return "diff";
  if (riskPatterns.some((p) => q.includes(p))) return "risk";
  if (historyPatterns.some((p) => q.includes(p))) return "history";
  return "general";
}

// ── Context builders ─────────────────────────────────────────────────────────

function buildDossierContext(dossier: Dossier, maxLen: number, intent: QuestionIntent): string {
  const parts: string[] = [];

  if (dossier.security) {
    const co = dossier.security;
    parts.push(
      `企業名: ${co.name}${co.nameEn ? ` (${co.nameEn})` : ""}` +
        ` / ${dossier.market}:${dossier.ticker}` +
        ` / セクター: ${co.sector ?? "不明"}`
    );
  }

  if (dossier.latestPrice) {
    const p = dossier.latestPrice;
    parts.push(
      `最新株価: ${p.close.toLocaleString()} ${dossier.security?.currency ?? ""} (${p.date})`
    );
  }

  // For diff intent, surface price delta prominently
  if (intent === "diff" && dossier.priceDelta) {
    const d = dossier.priceDelta;
    const sign = d.changeAbsolute >= 0 ? "+" : "";
    parts.push(
      `株価変化 (前回比): ${sign}${d.changeAbsolute} (${sign}${d.changePercent}%) ` +
        `${d.priorDate} → ${d.currentDate}`
    );
  }

  if (dossier.summary) {
    parts.push(`サマリー: ${dossier.summary.slice(0, 300)}`);
  }

  const latestIncome = dossier.incomeStatements[0];
  if (latestIncome) {
    parts.push(
      `最新損益 (${latestIncome.periodEnd}): ` +
        `売上=${latestIncome.revenue?.toLocaleString() ?? "N/A"}, ` +
        `純利益=${latestIncome.netIncome?.toLocaleString() ?? "N/A"} ` +
        `${latestIncome.currency}`
    );
  }

  const latestBS = dossier.balanceSheets[0];
  if (latestBS) {
    parts.push(
      `貸借対照表 (${latestBS.periodEnd}): ` +
        `総資産=${latestBS.totalAssets?.toLocaleString() ?? "N/A"}, ` +
        `自己資本=${latestBS.shareholdersEquity?.toLocaleString() ?? "N/A"} ` +
        `${latestBS.currency}`
    );
  }

  if (dossier.recentFilings.length > 0) {
    parts.push(
      `最新開示: ` +
        dossier.recentFilings
          .slice(0, 3)
          .map((f) => `${f.filingType} (${f.filedAt.slice(0, 10)})`)
          .join(", ")
    );
  }

  // Risk intent: surface more risk detail
  if (dossier.risks.length > 0) {
    const riskLimit = intent === "risk" ? 5 : 3;
    parts.push(
      `識別リスク: ` +
        dossier.risks
          .slice(0, riskLimit)
          .map((r) => `[${r.severity}] ${r.description}`)
          .join("; ")
    );
  }

  // Include analyst notes (news + freshness), truncated
  if (dossier.analystNotes) {
    const newsSection = dossier.analystNotes
      .split("## 最新ニュース")[1]
      ?.split("##")[0]
      ?.trim();
    if (newsSection) {
      parts.push(`最新ニュース:\n${newsSection.slice(0, 400)}`);
    }
  }

  const joined = parts.join("\n");
  return joined.length > maxLen ? joined.slice(0, maxLen) + "…" : joined;
}

function buildJudgmentStoreContext(store: JudgmentStore, intent: QuestionIntent): string {
  const parts: string[] = [];

  if (store.currentStance) {
    const s = store.currentStance;
    parts.push(
      `現在のスタンス: ${s.stance} / コンビクション: ${s.conviction}` +
        (s.targetPrice ? ` / 目標株価: ${s.targetPrice}` : "") +
        ` (${s.date})`
    );
  }

  // For history/diff intent, show stance trajectory
  if ((intent === "history" || intent === "diff") && store.stanceHistory.length > 1) {
    const trajectory = store.stanceHistory
      .slice(0, 4)
      .map((s) => `${s.date}: ${s.stance}(${s.conviction})`)
      .join(" → ");
    parts.push(`スタンス推移: ${trajectory}`);
  }

  // For risk intent, surface recurring risks
  if ((intent === "risk" || intent === "general") && store.recurringRisks.length > 0) {
    const topRisks = store.recurringRisks
      .slice(0, 3)
      .map((r) => `[${r.severity}×${r.occurrences}] ${r.description}`)
      .join("; ");
    parts.push(`繰り返しリスク: ${topRisks}`);
  }

  if (store.openQuestions.length > 0) {
    parts.push(`未解決の論点: ${store.openQuestions.slice(0, 3).join(" / ")}`);
  }

  parts.push(`テーゼ数: ${store.thesisCount}`);

  return parts.join("\n");
}

// ── answerCompanyQuestion ────────────────────────────────────────────────────

export async function answerCompanyQuestion(
  ticker: string,
  question: string,
  options: WalltalkQueryOptions = {}
): Promise<WalltalkQueryResult> {
  const {
    includeHistory = true,
    maxContextLength = 800,
    dossierDate,
    language: langOverride,
  } = options;

  const generatedAt = new Date().toISOString();
  const lang = langOverride ?? detectLanguage(question);
  const intent = detectIntent(question);
  const sources: string[] = [];

  // ── Step 1: Read dossier ─────────────────────────────────────────
  let dossier: Dossier | null = null;
  try {
    dossier = await readDossier(ticker, dossierDate);
    if (dossier) {
      sources.push(
        `dossier: ${dossier.ticker} (${dossier.createdAt.slice(0, 10)})`
      );
    }
  } catch {
    // no dossier found — continue with empty context
  }

  // ── Step 2: Read structured JudgmentStore (Layer 2) ──────────────
  let judgmentStore: JudgmentStore | null = null;
  let judgmentHistorySummary: string | undefined;
  let recurringRisks: WalltalkQueryResult["recurringRisks"];

  if (includeHistory) {
    try {
      judgmentStore = await readJudgment(ticker);
      if (judgmentStore) {
        sources.push(`judgment store: ${judgmentStore.thesisCount} theses`);
        judgmentHistorySummary = buildJudgmentStoreContext(judgmentStore, intent);
        if (judgmentStore.recurringRisks.length > 0) {
          recurringRisks = judgmentStore.recurringRisks.slice(0, 5).map((r) => ({
            description: r.description,
            severity: r.severity,
            occurrences: r.occurrences,
          }));
        }
      }
    } catch {
      // optional enrichment — silently skip
    }
  }

  // ── Step 3: Fallback to FileJudgmentMemory (markdown-based) ──────
  let legacyJudgmentContext = "";
  if (includeHistory && !judgmentStore) {
    try {
      legacyJudgmentContext = await judgmentMemory.getJudgmentContext(ticker);
      if (!legacyJudgmentContext.includes("記録はありません")) {
        sources.push("judgment memory (legacy)");
      }
    } catch {
      // optional enrichment
    }
  }

  // ── Step 4: Assess data confidence ──────────────────────────────
  const confidence: "low" | "medium" | "high" = !dossier
    ? "low"
    : dossier.incomeStatements.length > 0 && dossier.latestPrice
    ? "high"
    : "medium";

  // ── Step 5: Build context ────────────────────────────────────────
  if (!dossier && !judgmentStore && legacyJudgmentContext.includes("記録はありません")) {
    const noDataMsg =
      lang === "en"
        ? `No dossier found for ${ticker}. Please run buildDossier() first to collect data.`
        : `${ticker} のドシエが見つかりません。まず buildDossier() を実行してデータを収集してください。`;
    return {
      answer: noDataMsg,
      sources: [],
      confidence: "low",
      generatedAt,
      intentDetected: intent,
    };
  }

  const dossierContext = dossier
    ? buildDossierContext(dossier, maxContextLength, intent)
    : `${ticker} の財務データは未取得です。`;

  // Combine judgment context: structured store takes priority
  const judgmentBlock = judgmentStore
    ? `\n\n## 判断履歴（構造化メモリ）\n${judgmentHistorySummary}`
    : includeHistory && legacyJudgmentContext && !legacyJudgmentContext.includes("記録はありません")
    ? `\n\n## 過去の判断コンテキスト\n${legacyJudgmentContext.slice(0, 600)}`
    : "";

  // Intent-specific system instructions
  const intentHint =
    intent === "diff"
      ? lang === "ja"
        ? "特に前回との変化点（株価変化・スタンス変化・新リスク）を中心に回答してください。"
        : "Focus especially on what changed since last time (price, stance, new risks)."
      : intent === "risk"
      ? lang === "ja"
        ? "リスク・懸念事項を優先して回答してください。"
        : "Prioritize risks and concerns in your answer."
      : intent === "history"
      ? lang === "ja"
        ? "過去の投資判断の推移と、現在との比較を中心に回答してください。"
        : "Focus on the history of past judgments and how they compare to today."
      : "";

  // ── Step 6: LLM answer ───────────────────────────────────────────
  const sysPrompt =
    lang === "en"
      ? `You are an equity research analyst. Answer the question based on the provided company data. Be concise and factual. Clearly state if data is missing. ${intentHint}`
      : `あなたはエクイティリサーチアナリストです。提供された企業データに基づいて質問に答えてください。簡潔かつ事実に基づいて回答し、データが不足している場合はその旨を明示してください。${intentHint}`;

  const userPrompt =
    `## 企業データ (${ticker})\n${dossierContext}${judgmentBlock}\n\n` +
    `## 質問\n${question}`;

  let answer = "";
  const llmResult = await callClaudeText(userPrompt, sysPrompt);
  if (llmResult.ok) {
    answer = llmResult.data.trim();
  } else {
    answer =
      lang === "en"
        ? `Error generating answer: ${llmResult.error.message}`
        : `回答生成エラー: ${llmResult.error.message}`;
  }

  return {
    answer,
    sources,
    confidence,
    generatedAt,
    dossierDate: dossier?.createdAt,
    intentDetected: intent,
    judgmentHistorySummary,
    recurringRisks,
  };
}
