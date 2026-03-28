/**
 * Phase FV Proof Script — Claude Code CLI Backend
 *
 * Proves that buildThesis() and compareCompanies() work end-to-end
 * using the `claude -p` CLI backend (Claude Max OAuth, no ANTHROPIC_API_KEY).
 *
 * Run: bun tests/phase-fv-proof.ts
 */

import { buildThesis } from "../packages/services/src/thesis/builder.js";
import { compareCompanies } from "../packages/services/src/compare/index.js";
import { buildRegistry } from "../packages/adapters/src/registry.js";
import type { Dossier } from "../packages/domain/src/schemas/index.js";

console.log("=== Phase FV: Claude Code CLI Backend Proof ===\n");
console.log("Backend: claude -p --output-format json (Claude Max OAuth, no ANTHROPIC_API_KEY)\n");

// ── Minimal mock Dossier (no adapters needed) ────────────────────────────────
const mockDossier: Dossier = {
  ticker: "7203",
  market: "JP",
  createdAt: new Date().toISOString(),
  security: {
    ticker: "7203",
    market: "JP",
    name: "トヨタ自動車",
    nameEn: "Toyota Motor Corporation",
    sector: "自動車",
    currency: "JPY",
  },
  latestPrice: {
    ticker: "7203",
    market: "JP",
    date: "2026-03-27",
    open: 3200,
    high: 3250,
    low: 3180,
    close: 3220,
    volume: 8000000,
  },
  incomeStatements: [
    {
      ticker: "7203",
      market: "JP",
      periodType: "annual",
      periodEnd: "2025-03-31",
      currency: "JPY",
      revenue: 44540000000000,
      operatingIncome: 4790000000000,
      netIncome: 3578000000000,
      eps: 245.0,
    },
  ],
  balanceSheets: [
    {
      ticker: "7203",
      market: "JP",
      periodType: "annual",
      periodEnd: "2025-03-31",
      currency: "JPY",
      totalAssets: 77040000000000,
      totalLiabilities: 45820000000000,
      shareholdersEquity: 31220000000000,
      cashAndEquivalents: 8900000000000,
    },
  ],
  recentFilings: [],
  risks: [],
};

const mock9984: Dossier = {
  ticker: "9984",
  market: "JP",
  createdAt: new Date().toISOString(),
  security: {
    ticker: "9984",
    market: "JP",
    name: "ソフトバンクグループ",
    nameEn: "SoftBank Group Corp.",
    sector: "通信・投資",
    currency: "JPY",
  },
  latestPrice: {
    ticker: "9984",
    market: "JP",
    date: "2026-03-27",
    open: 9200,
    high: 9350,
    low: 9150,
    close: 9280,
    volume: 5000000,
  },
  incomeStatements: [
    {
      ticker: "9984",
      market: "JP",
      periodType: "annual",
      periodEnd: "2025-03-31",
      currency: "JPY",
      revenue: 6760000000000,
      operatingIncome: 420000000000,
      netIncome: -230000000000,
      eps: -14.2,
    },
  ],
  balanceSheets: [
    {
      ticker: "9984",
      market: "JP",
      periodType: "annual",
      periodEnd: "2025-03-31",
      currency: "JPY",
      totalAssets: 50000000000000,
      totalLiabilities: 42000000000000,
      shareholdersEquity: 8000000000000,
      cashAndEquivalents: 4200000000000,
    },
  ],
  recentFilings: [],
  risks: [],
};

// ── FV-11: buildThesis() ─────────────────────────────────────────────────────
console.log("[FV-11] buildThesis(mockDossier) — via claude -p CLI backend");
console.log("  Calling buildThesis for 7203 (Toyota)...");
const t0thesis = Date.now();

const thesisResult = await buildThesis(mockDossier, { language: "ja" });
const dtThesis = ((Date.now() - t0thesis) / 1000).toFixed(1);

if (thesisResult.ok) {
  const t = thesisResult.data;
  console.log(`  ✅ buildThesis returned ok(Thesis) in ${dtThesis}s`);
  console.log(`     id        = ${t.id}`);
  console.log(`     title     = ${t.title}`);
  console.log(`     stance    = ${t.stance}`);
  console.log(`     conviction= ${t.conviction}`);
  console.log(`     horizon   = ${t.horizon}`);
  console.log(`     catalysts = ${t.catalysts.length} items`);
  console.log(`     risks     = ${t.risks.length} items`);
  console.log(`     openQs    = ${t.openQuestions.length} items`);
  console.log(`     body[0:80]= ${t.body.slice(0, 80)}...`);
  console.log("  → FV-11: ✅ DONE\n");
} else {
  console.log(`  ❌ buildThesis returned err in ${dtThesis}s:`);
  console.log(`     ${thesisResult.error.message}`);
  console.log("  → FV-11: ❌ FAILED\n");
}

// ── FV-12: compareCompanies() ────────────────────────────────────────────────
// compareCompanies() calls buildDossier() internally for each target.
// With empty registry + pre-built dossiers, we need to check if the function
// accepts pre-built dossiers or rebuilds them.
// Looking at source: it always calls buildDossier() internally.
// So we need emptyRegistry — it will produce empty dossiers, then LLM compares them.
console.log("[FV-12] compareCompanies([7203,9984]) — via claude -p CLI backend");
console.log("  Note: compareCompanies() rebuilds dossiers internally via empty registry.");
console.log("  Dossiers will be empty but LLM call path will be exercised.");
console.log("  Calling compareCompanies for 7203 vs 9984...");

const emptyRegistry = buildRegistry({} as NodeJS.ProcessEnv);
const t0compare = Date.now();

const compareResult = await compareCompanies(
  [
    { ticker: "7203", market: "JP" },
    { ticker: "9984", market: "JP" },
  ],
  emptyRegistry,
  "バリュエーションと財務健全性の比較",
  {
    dossierOptions: { generateSummary: false, computePriorDiff: false, includeNews: false },
    language: "ja",
  }
);
const dtCompare = ((Date.now() - t0compare) / 1000).toFixed(1);

if (compareResult.ok) {
  const c = compareResult.ok ? compareResult.data : null;
  if (c) {
    console.log(`  ✅ compareCompanies returned ok(CompareResult) in ${dtCompare}s`);
    console.log(`     targets      = ${c.targets.map(t => t.ticker).join(", ")}`);
    console.log(`     dossiers     = ${c.dossiers.length} built`);
    console.log(`     winner       = ${c.winner ?? "null (neutral)"}`);
    console.log(`     rankings     = ${Object.keys(c.rankings).join(", ")}`);
    console.log(`     judgDiffs    = ${c.judgmentDifferences.length} items`);
    console.log(`     pivotPoints  = ${Object.keys(c.pivotPoints).join(", ")}`);
    console.log(`     analysis[0:80]= ${c.analysis.slice(0, 80)}...`);
    console.log("  → FV-12: ✅ DONE\n");
  }
} else {
  console.log(`  ❌ compareCompanies returned err in ${dtCompare}s:`);
  console.log(`     ${compareResult.error.message}`);
  console.log("  → FV-12: ❌ FAILED\n");
}

// ── Summary ──────────────────────────────────────────────────────────────────
console.log("=== Phase FV Summary ===");
console.log(`[FV-11] buildThesis       : ${thesisResult.ok ? "✅ DONE" : "❌ FAILED"}`);
console.log(`[FV-12] compareCompanies  : ${compareResult.ok ? "✅ DONE" : "❌ FAILED"}`);
console.log("\nBackend: claude -p --output-format json (Claude Max OAuth, no ANTHROPIC_API_KEY)");
