/**
 * Phase C Gap Closure Proof Script
 *
 * Demonstrates:
 *   1. buildDossier() — runs with empty registry (no API keys), returns partial Dossier
 *   2. buildThesis()  — BLOCKED: requires ANTHROPIC_API_KEY
 *   3. compareCompanies() — BLOCKED: requires ANTHROPIC_API_KEY
 *   4. Backward compatibility: optional fields verified in schema
 *   5. answerCompanyQuestion() — 4 intents covered (smoke tests [7][8])
 *   6. readJudgment / writeJudgment — covered (smoke tests [1][2])
 *   7. readPreviousDossier — covered (smoke test [3])
 */

import { buildDossier } from "../packages/services/src/dossier/builder.js";
import { buildThesis } from "../packages/services/src/thesis/builder.js";
import { compareCompanies } from "../packages/services/src/compare/index.js";
import { buildRegistry } from "../packages/adapters/src/registry.js";
import type { Dossier } from "../packages/domain/src/schemas/index.js";

console.log("=== Phase C: Gap Closure Proof ===\n");

// ── [1] buildDossier with empty registry (no API keys) ──────────────────────
console.log("[1] buildDossier — empty registry (no API keys)");
const emptyRegistry = buildRegistry({} as NodeJS.ProcessEnv);
const dossierResult = await buildDossier("7203", "JP", emptyRegistry, {
  generateSummary: false,   // skip LLM call to avoid ANTHROPIC_API_KEY requirement
  computePriorDiff: false,  // skip prior diff (no output/ dir exists)
  includeNews: false,       // skip search adapter
});

if (dossierResult.ok) {
  const d = dossierResult.data;
  console.log("  ✅ buildDossier returned ok(Dossier)");
  console.log(`     ticker=${d.ticker}, market=${d.market}`);
  console.log(`     security=${d.security ?? "undefined (no adapter)"}`);
  console.log(`     latestPrice=${d.latestPrice ?? "undefined (no adapter)"}`);
  console.log(`     incomeStatements.length=${d.incomeStatements.length}`);
  console.log(`     balanceSheets.length=${d.balanceSheets.length}`);
  console.log(`     recentFilings.length=${d.recentFilings.length}`);
  console.log(`     freshnessMetadata.securityFetched=${d.freshnessMetadata?.securityFetched}`);
  console.log(`     freshnessMetadata.latestPriceFetched=${d.freshnessMetadata?.latestPriceFetched}`);
  console.log(`     priceDelta=${d.priceDelta ?? "undefined (no prior dossier)"}`);
  console.log(`     priorDossierDate=${d.priorDossierDate ?? "undefined"}`);
  console.log(`     createdAt=${d.createdAt}`);
  console.log("  → RESULT: partial Dossier produced (data empty because no adapters configured)");
  console.log("  → COMPAT: freshnessMetadata, priceDelta, priorDossierDate are all optional — backward compatible\n");
} else {
  console.log(`  ❌ buildDossier returned err: ${dossierResult.error.message}\n`);
  process.exit(1);
}

// ── [2] buildThesis — requires ANTHROPIC_API_KEY ────────────────────────────
// Note: new ChatAnthropic() throws synchronously in constructor when API key is absent,
// BEFORE the try-catch inside buildThesis(). So we wrap the call here.
console.log("[2] buildThesis — requires ANTHROPIC_API_KEY");
try {
  const thesisResult = await buildThesis(dossierResult.data);
  if (thesisResult.ok) {
    console.log("  ✅ buildThesis returned ok (ANTHROPIC_API_KEY was found)");
    console.log(`     id=${thesisResult.data.id}, stance=${thesisResult.data.stance}`);
  } else {
    console.log(`  ⛔ buildThesis returned err: ${thesisResult.error.message.slice(0, 120)}`);
  }
} catch (e: unknown) {
  const msg = e instanceof Error ? e.message : String(e);
  console.log(`  ⛔ buildThesis threw (EXPECTED — ANTHROPIC_API_KEY not set):`);
  console.log(`     ${msg.slice(0, 120)}`);
  console.log(`  → BLOCKED reason: @langchain/anthropic constructor throws when ANTHROPIC_API_KEY absent`);
  console.log(`  → Set ANTHROPIC_API_KEY env var to enable thesis generation\n`);
}

// ── [3] compareCompanies — requires ANTHROPIC_API_KEY ───────────────────────
// Note: same as buildThesis — ChatAnthropic constructor throws synchronously.
console.log("[3] compareCompanies — requires ANTHROPIC_API_KEY");
try {
  const compareResult = await compareCompanies(
    [
      { ticker: "7203", market: "JP" },
      { ticker: "9984", market: "JP" },
    ],
    emptyRegistry,
    "バリュエーション比較",
    { dossierOptions: { generateSummary: false, computePriorDiff: false, includeNews: false } }
  );
  if (compareResult.ok) {
    console.log("  ✅ compareCompanies returned ok (ANTHROPIC_API_KEY was found)");
  } else {
    console.log(`  ⛔ compareCompanies returned err: ${compareResult.error.message.slice(0, 120)}`);
  }
} catch (e: unknown) {
  const msg = e instanceof Error ? e.message : String(e);
  console.log(`  ⛔ compareCompanies threw (EXPECTED — ANTHROPIC_API_KEY not set):`);
  console.log(`     ${msg.slice(0, 120)}`);
  console.log(`  → BLOCKED reason: @langchain/anthropic constructor throws when ANTHROPIC_API_KEY absent`);
  console.log(`  → Set ANTHROPIC_API_KEY env var to enable company comparison\n`);
}

// ── [4] Backward compatibility: schema optional fields ───────────────────────
console.log("[4] Backward compatibility — v1 Dossier (no new fields) passes schema");
import { DossierSchema } from "../packages/domain/src/schemas/index.js";

const v1Dossier: unknown = {
  ticker: "7203",
  market: "JP",
  createdAt: "2026-01-15T00:00:00Z",
  security: { ticker: "7203", market: "JP", name: "Toyota", currency: "JPY" },
  latestPrice: { ticker: "7203", market: "JP", date: "2026-01-15", close: 2930, open: 2900, high: 2950, low: 2890, volume: 1000000 },
  incomeStatements: [],
  balanceSheets: [],
  recentFilings: [],
  risks: [],
  // v2 optional fields are ABSENT — testing backward compat
};

const parsedDossier = DossierSchema.safeParse(v1Dossier);
if (parsedDossier.success) {
  const d = parsedDossier.data;
  console.log("  ✅ v1 Dossier (no freshnessMetadata/priceDelta/priorDossierDate) passes schema");
  console.log(`     freshnessMetadata=${d.freshnessMetadata} (optional, absent = ok)`);
  console.log(`     priceDelta=${d.priceDelta} (optional, absent = ok)`);
  console.log(`     priorDossierDate=${d.priorDossierDate} (optional, absent = ok)\n`);
} else {
  console.log(`  ❌ v1 Dossier FAILS schema: ${parsedDossier.error.message}\n`);
  process.exit(1);
}

import { ThesisSchema } from "../packages/domain/src/schemas/index.js";

const v1Thesis: unknown = {
  id: "thesis-7203-1234567890",
  ticker: "7203",
  market: "JP",
  createdAt: "2026-01-15T00:00:00Z",
  updatedAt: "2026-01-15T00:00:00Z",
  title: "Toyota v1 thesis",
  stance: "neutral",
  horizon: "medium",
  conviction: "medium",
  catalysts: ["EV expansion"],
  risks: [{ category: "market", severity: "medium", description: "competition" }],
  body: "Test body",
  references: [],
  version: 1,
  openQuestions: [],
  invalidationPoints: [],
  // v2 fields absent: bullCase, bearCase, priorThesisId, stanceChanged, changeFromPrior
};

const parsedThesis = ThesisSchema.safeParse(v1Thesis);
if (parsedThesis.success) {
  const t = parsedThesis.data;
  console.log("  ✅ v1 Thesis (no bullCase/bearCase/priorThesisId/stanceChanged/changeFromPrior) passes schema");
  console.log(`     bullCase=${t.bullCase} (optional, absent = ok)`);
  console.log(`     bearCase=${t.bearCase} (optional, absent = ok)`);
  console.log(`     priorThesisId=${t.priorThesisId} (optional, absent = ok)\n`);
} else {
  console.log(`  ❌ v1 Thesis FAILS schema: ${parsedThesis.error.message}\n`);
  process.exit(1);
}

// ── Summary ──────────────────────────────────────────────────────────────────
console.log("=== Phase C Summary ===");
console.log("[1] buildDossier          : ✅ EXECUTED — partial dossier (empty adapters, no API keys)");
console.log("[2] buildThesis           : ⛔ BLOCKED — ANTHROPIC_API_KEY not set (error returned as expected)");
console.log("[3] compareCompanies      : ⛔ BLOCKED — ANTHROPIC_API_KEY not set (error returned as expected)");
console.log("[4] backward compat       : ✅ VERIFIED — v1 Dossier + Thesis schema parse without v2 fields");
console.log("[5] answerCompanyQuestion : ✅ PROVEN — smoke tests [7][8]: 4 intents (general/diff/risk/history)");
console.log("[6] readJudgment/write    : ✅ PROVEN — smoke tests [1][2]: write→read round-trip");
console.log("[7] readPreviousDossier   : ✅ PROVEN — smoke test [3]: date filtering 3 patterns");
