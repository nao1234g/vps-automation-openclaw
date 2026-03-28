/**
 * JudgmentMemory — read-only interface over walltalk thesis artifacts
 *
 * Reads thesis markdown files written by writeThesis() to reconstruct
 * past judgment context. Injected into DossierBuildOptions.priorJudgmentContext
 * so the dossier carries a "what did we think last time?" section.
 *
 * Architecture:
 *   walltalk writes: output/walltalk/thesis/{ticker}-{id}.md
 *   memory reads:    same files via fs.readFile
 *   services injects: context string → dossier.analystNotes
 *
 * No LLM calls in this module — pure file I/O.
 */

import * as fs from "node:fs/promises";
import * as path from "node:path";
import { getArtifactIndex } from "@equity/walltalk";

// ── Types ────────────────────────────────────────────────────────────────────

export interface JudgmentEntry {
  ticker: string;
  thesisId: string;
  /** Parsed from filename pattern: {ticker}-{id}.md */
  filedAt?: string;
  /** Raw markdown content of the thesis file */
  content: string;
  /** Extracted stance from markdown header metadata table */
  stance?: "bullish" | "bearish" | "neutral";
  /** Extracted conviction from markdown header metadata table */
  conviction?: "low" | "medium" | "high";
  /** Extracted created date from markdown table */
  createdAt?: string;
}

export interface JudgmentMemory {
  /**
   * Returns all past thesis judgments for a ticker, newest first.
   * Returns [] if no theses exist.
   */
  getPastJudgments(ticker: string): Promise<JudgmentEntry[]>;

  /**
   * Returns a formatted markdown string suitable for injection into
   * dossier.analystNotes as "過去の判断コンテキスト".
   */
  getJudgmentContext(ticker: string): Promise<string>;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function getWalltalkOutputDir(): string {
  return process.env["WALLTALK_OUTPUT_DIR"] ?? "./output/walltalk";
}

/**
 * Extract key fields from rendered thesis markdown.
 * The markdown format is written by walltalk/src/index.ts renderThesisMarkdown().
 *
 * Header table format:
 *   | Stance | **BULLISH** |
 *   | Conviction | 🔴 High |
 *   | Created | 2026-03-28 |
 */
function parseThesisMarkdown(content: string): {
  stance?: "bullish" | "bearish" | "neutral";
  conviction?: "low" | "medium" | "high";
  createdAt?: string;
} {
  const stanceMatch = content.match(/\|\s*Stance\s*\|\s*\*\*([A-Z]+)\*\*\s*\|/i);
  const convictionMatch = content.match(/\|\s*Conviction\s*\|[^|]*?(Low|Medium|High)[^|]*\|/i);
  const createdMatch = content.match(/\|\s*Created\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|/);

  const rawStance = stanceMatch?.[1]?.toLowerCase();
  const stance =
    rawStance === "bullish" || rawStance === "bearish" || rawStance === "neutral"
      ? (rawStance as "bullish" | "bearish" | "neutral")
      : undefined;

  const rawConviction = convictionMatch?.[1]?.toLowerCase();
  const conviction =
    rawConviction === "low" || rawConviction === "medium" || rawConviction === "high"
      ? (rawConviction as "low" | "medium" | "high")
      : undefined;

  return { stance, conviction, createdAt: createdMatch?.[1] };
}

// ── FileJudgmentMemory ────────────────────────────────────────────────────────

export class FileJudgmentMemory implements JudgmentMemory {
  async getPastJudgments(ticker: string): Promise<JudgmentEntry[]> {
    let index: Awaited<ReturnType<typeof getArtifactIndex>>;
    try {
      index = await getArtifactIndex(ticker);
    } catch {
      return [];
    }

    if (index.theses.length === 0) return [];

    const thesisDir = path.join(getWalltalkOutputDir(), "thesis");

    const entries = await Promise.all(
      index.theses.map(async (filename): Promise<JudgmentEntry | null> => {
        try {
          const filepath = path.join(thesisDir, filename);
          const content = await fs.readFile(filepath, "utf-8");
          const { stance, conviction, createdAt } = parseThesisMarkdown(content);

          // Filename pattern: {ticker}-{id}.md
          const withoutExt = filename.replace(/\.md$/, "");
          const thesisId = withoutExt.slice(ticker.length + 1); // strip "{ticker}-"

          return {
            ticker,
            thesisId,
            filedAt: createdAt,
            content,
            stance,
            conviction,
            createdAt,
          };
        } catch {
          return null;
        }
      })
    );

    return entries
      .filter((e): e is JudgmentEntry => e !== null)
      .sort((a, b) => {
        // Sort newest first by createdAt date
        if (a.createdAt && b.createdAt) {
          return b.createdAt.localeCompare(a.createdAt);
        }
        return 0;
      });
  }

  async getJudgmentContext(ticker: string): Promise<string> {
    const judgments = await this.getPastJudgments(ticker);

    if (judgments.length === 0) {
      return `${ticker} に関する過去の判断記録はありません。`;
    }

    const latest = judgments[0]!;
    const stanceStr = latest.stance ?? "不明";
    const convictionStr = latest.conviction ?? "不明";
    const dateStr = latest.createdAt ?? "日付不明";

    // Build summary: most recent thesis + historical trend
    const historicalStances = judgments
      .slice(0, 5)
      .map((j) => `${j.createdAt ?? "?"}: ${j.stance ?? "不明"}/${j.conviction ?? "不明"}`)
      .join(" → ");

    // Extract thesis body (content after the metadata table and first ---)
    const bodyMatch = latest.content.match(/---\s*\n([\s\S]+)/);
    const bodyPreview = bodyMatch
      ? bodyMatch[1]!.slice(0, 300).trim() + (bodyMatch[1]!.length > 300 ? "…" : "")
      : latest.content.slice(0, 300).trim();

    return (
      `### 最新テーゼ (${dateStr})\n` +
      `- スタンス: **${stanceStr}** / コンビクション: **${convictionStr}**\n\n` +
      `${bodyPreview}\n\n` +
      (judgments.length > 1
        ? `### 判断履歴 (${judgments.length}件)\n${historicalStances}\n`
        : "")
    );
  }
}

// ── Singleton ────────────────────────────────────────────────────────────────

/** Default singleton — use this in most call sites */
export const judgmentMemory: JudgmentMemory = new FileJudgmentMemory();
