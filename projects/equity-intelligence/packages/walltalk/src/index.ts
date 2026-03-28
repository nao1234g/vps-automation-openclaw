/**
 * Walltalk Integration — Read-only knowledge artifact writer
 *
 * Architecture: equity-intelligence produces structured artifacts (JSON/Markdown).
 * Walltalk consumes those artifacts from a shared directory.
 * NO direct API coupling — purely file-based boundary.
 *
 * Why read-only + file-based?
 *   - Walltalk's internals may change; a file-based boundary is stable
 *   - Nowpattern infra is completely isolated from equity-intelligence
 *   - Artifacts can also be consumed by Claude Code, NEO, or any future tool
 *
 * Output directory: $WALLTALK_OUTPUT_DIR (default: ./output/walltalk)
 *
 * Artifact types:
 *   dossier/   — {ticker}-{date}.json   (Dossier)
 *   thesis/    — {ticker}-{id}.md       (Thesis markdown)
 *   screener/  — {query-hash}.json      (ScreenerResult)
 *   sessions/  — {sessionId}.json       (ResearchSession log)
 */

import * as fs from "node:fs/promises";
import * as path from "node:path";

import type { Dossier, Thesis, ScreenerResult, ResearchSession, JudgmentStore } from "@equity/domain";

const DEFAULT_OUTPUT_DIR = "./output/walltalk";

function getOutputDir(): string {
  return process.env["WALLTALK_OUTPUT_DIR"] ?? DEFAULT_OUTPUT_DIR;
}

async function ensureDir(dir: string): Promise<void> {
  await fs.mkdir(dir, { recursive: true });
}

// ─────────────────────────────────────────────
// Dossier artifacts
// ─────────────────────────────────────────────

export async function writeDossier(dossier: Dossier): Promise<string> {
  const dir = path.join(getOutputDir(), "dossier");
  await ensureDir(dir);
  const date = dossier.createdAt.slice(0, 10);
  const filename = `${dossier.ticker.toLowerCase()}-${date}.json`;
  const filepath = path.join(dir, filename);
  await fs.writeFile(filepath, JSON.stringify(dossier, null, 2), "utf-8");
  return filepath;
}

export async function readDossier(ticker: string, date?: string): Promise<Dossier | null> {
  const dir = path.join(getOutputDir(), "dossier");
  const pattern = date
    ? `${ticker.toLowerCase()}-${date}.json`
    : null;

  if (pattern) {
    try {
      const raw = await fs.readFile(path.join(dir, pattern), "utf-8");
      return JSON.parse(raw) as Dossier;
    } catch {
      return null;
    }
  }

  // Find latest dossier for ticker
  try {
    const files = await fs.readdir(dir);
    const matching = files
      .filter((f) => f.startsWith(ticker.toLowerCase() + "-"))
      .sort()
      .reverse();
    if (matching.length === 0) return null;
    const raw = await fs.readFile(path.join(dir, matching[0]!), "utf-8");
    return JSON.parse(raw) as Dossier;
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────
// Thesis artifacts
// ─────────────────────────────────────────────

export async function writeThesis(thesis: Thesis): Promise<string> {
  const dir = path.join(getOutputDir(), "thesis");
  await ensureDir(dir);
  const filename = `${thesis.ticker.toLowerCase()}-${thesis.id}.md`;
  const filepath = path.join(dir, filename);

  // Render thesis as structured markdown
  const md = renderThesisMarkdown(thesis);
  await fs.writeFile(filepath, md, "utf-8");
  return filepath;
}

function renderThesisMarkdown(thesis: Thesis): string {
  const stanceEmoji = {
    bullish: "🐂",
    bearish: "🐻",
    neutral: "⚖️",
  }[thesis.stance];

  const convictionBadge = {
    low: "🟡 Low",
    medium: "🟠 Medium",
    high: "🔴 High",
  }[thesis.conviction];

  return [
    `# ${stanceEmoji} ${thesis.title}`,
    ``,
    `| Field | Value |`,
    `|-------|-------|`,
    `| Ticker | \`${thesis.ticker}\` (${thesis.market}) |`,
    `| Stance | **${thesis.stance.toUpperCase()}** |`,
    `| Horizon | ${thesis.horizon} |`,
    `| Conviction | ${convictionBadge} |`,
    thesis.targetPrice
      ? `| Target Price | ${thesis.targetCurrency ?? ""} ${thesis.targetPrice.toLocaleString()} |`
      : null,
    `| Created | ${thesis.createdAt.slice(0, 10)} |`,
    `| Version | v${thesis.version} |`,
    ``,
    `---`,
    ``,
    thesis.body,
    ``,
    thesis.catalysts.length > 0
      ? [`## Catalysts`, ...thesis.catalysts.map((c) => `- ${c}`), ``].join("\n")
      : null,
    thesis.risks.length > 0
      ? [
          `## Risks`,
          ...thesis.risks.map(
            (r) =>
              `- **[${r.severity.toUpperCase()}]** ${r.category}: ${r.description}`
          ),
          ``,
        ].join("\n")
      : null,
    thesis.references.length > 0
      ? [`## References`, ...thesis.references.map((r) => `- ${r}`), ``].join("\n")
      : null,
  ]
    .filter(Boolean)
    .join("\n");
}

// ─────────────────────────────────────────────
// Screener results
// ─────────────────────────────────────────────

export async function writeScreenerResult(result: ScreenerResult): Promise<string> {
  const dir = path.join(getOutputDir(), "screener");
  await ensureDir(dir);
  const hash = Buffer.from(JSON.stringify(result.query)).toString("base64url").slice(0, 16);
  const filename = `screener-${hash}.json`;
  const filepath = path.join(dir, filename);
  await fs.writeFile(filepath, JSON.stringify(result, null, 2), "utf-8");
  return filepath;
}

// ─────────────────────────────────────────────
// Session logs
// ─────────────────────────────────────────────

export async function writeResearchSession(session: ResearchSession): Promise<string> {
  const dir = path.join(getOutputDir(), "sessions");
  await ensureDir(dir);
  const filename = `${session.id}.json`;
  const filepath = path.join(dir, filename);
  await fs.writeFile(filepath, JSON.stringify(session, null, 2), "utf-8");
  return filepath;
}

// ─────────────────────────────────────────────
// Judgment store (Layer 2 memory)
// ─────────────────────────────────────────────

export async function writeJudgment(store: JudgmentStore): Promise<string> {
  const dir = path.join(getOutputDir(), "judgment");
  await ensureDir(dir);
  const filename = `${store.ticker.toLowerCase()}-judgment.json`;
  const filepath = path.join(dir, filename);
  await fs.writeFile(filepath, JSON.stringify(store, null, 2), "utf-8");
  return filepath;
}

export async function readJudgment(ticker: string): Promise<JudgmentStore | null> {
  const dir = path.join(getOutputDir(), "judgment");
  const filename = `${ticker.toLowerCase()}-judgment.json`;
  try {
    const raw = await fs.readFile(path.join(dir, filename), "utf-8");
    return JSON.parse(raw) as JudgmentStore;
  } catch {
    return null;
  }
}

/**
 * Reads the most recent dossier that was created strictly before `beforeDate`.
 * Used by DossierBuilder to compute priceDelta across sessions.
 */
export async function readPreviousDossier(
  ticker: string,
  beforeDate: string
): Promise<Dossier | null> {
  const dir = path.join(getOutputDir(), "dossier");
  try {
    const files = await fs.readdir(dir);
    const candidates = files
      .filter((f) => f.startsWith(ticker.toLowerCase() + "-"))
      .sort()
      .reverse()
      .filter((f) => {
        const m = f.match(/-(\d{4}-\d{2}-\d{2})\.json$/);
        return m && m[1]! < beforeDate;
      });
    if (candidates.length === 0) return null;
    const raw = await fs.readFile(path.join(dir, candidates[0]!), "utf-8");
    return JSON.parse(raw) as Dossier;
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────
// Index: list all artifacts for a ticker
// ─────────────────────────────────────────────

export interface ArtifactIndex {
  ticker: string;
  dossiers: string[];
  theses: string[];
  hasJudgmentStore: boolean;
}

export async function getArtifactIndex(ticker: string): Promise<ArtifactIndex> {
  const base = getOutputDir();
  const lowerTicker = ticker.toLowerCase();

  async function listDir(subdir: string, prefix: string): Promise<string[]> {
    const dir = path.join(base, subdir);
    try {
      const files = await fs.readdir(dir);
      return files.filter((f) => f.startsWith(prefix));
    } catch {
      return [];
    }
  }

  async function fileExists(subdir: string, filename: string): Promise<boolean> {
    try {
      await fs.access(path.join(base, subdir, filename));
      return true;
    } catch {
      return false;
    }
  }

  const [dossiers, theses, hasJudgmentStore] = await Promise.all([
    listDir("dossier", `${lowerTicker}-`),
    listDir("thesis", `${lowerTicker}-`),
    fileExists("judgment", `${lowerTicker}-judgment.json`),
  ]);

  return { ticker, dossiers, theses, hasJudgmentStore };
}
