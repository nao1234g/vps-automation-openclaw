/**
 * Smoke Tests — walltalk judgment I/O + syncJudgmentStore
 *
 * Tests:
 *   [1] writeJudgment / readJudgment round-trip
 *   [2] readJudgment returns null for unknown ticker
 *   [3] writeDossier / readPreviousDossier (date filtering)
 *   [4] getArtifactIndex — hasJudgmentStore flag
 *   [5] syncJudgmentStore — creates store from Thesis
 *   [6] syncJudgmentStore — accumulates stanceHistory across two theses
 *   [7] answerCompanyQuestion intent detection (no LLM — returns "no data" for unknown ticker)
 *   [8] answerCompanyQuestion JudgmentStore integration path (9984 store from tests [5]-[6])
 *
 * Run: bun run tests/smoke-walltalk.ts
 * Uses a temporary directory — never writes to ./output/walltalk
 */

import * as os from "node:os";
import * as path from "node:path";
import * as fs from "node:fs/promises";

// ── Setup temp output dir ─────────────────────────────────────────────────────

const TEMP_DIR = path.join(os.tmpdir(), `eq-smoke-${Date.now()}`);
process.env["WALLTALK_OUTPUT_DIR"] = TEMP_DIR;

// Import AFTER setting env so the module picks up the temp dir
const { writeJudgment, readJudgment, writeDossier, readPreviousDossier, getArtifactIndex } =
  await import("../packages/walltalk/src/index.js");
const { syncJudgmentStore } = await import("../packages/services/src/judgment/store.js");
const { answerCompanyQuestion } = await import("../packages/services/src/query/walltalk.js");

import type { JudgmentStore, Dossier, Thesis } from "../packages/domain/src/schemas/index.js";

// ── Test helpers ──────────────────────────────────────────────────────────────

let passed = 0;
let failed = 0;
const errors: string[] = [];

function assert(cond: boolean, label: string, detail?: string): void {
  if (cond) {
    console.log(`  ✅ PASS: ${label}`);
    passed++;
  } else {
    console.log(`  ❌ FAIL: ${label}${detail ? ` — ${detail}` : ""}`);
    failed++;
    errors.push(`${label}${detail ? `: ${detail}` : ""}`);
  }
}

function assertEq<T>(actual: T, expected: T, label: string): void {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  assert(ok, label, ok ? undefined : `got ${JSON.stringify(actual)}, expected ${JSON.stringify(expected)}`);
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const MOCK_STORE: JudgmentStore = {
  ticker: "7203",
  market: "JP",
  updatedAt: "2026-01-15T10:00:00.000Z",
  stanceHistory: [
    {
      thesisId: "thesis-7203-1000",
      date: "2026-01-15",
      stance: "bullish",
      conviction: "high",
      title: "EV transition catalyst",
      targetPrice: 3200,
    },
  ],
  currentStance: {
    thesisId: "thesis-7203-1000",
    date: "2026-01-15",
    stance: "bullish",
    conviction: "high",
    title: "EV transition catalyst",
    targetPrice: 3200,
  },
  recurringRisks: [
    {
      category: "market",
      severity: "high",
      description: "競合他社の価格競争が激化している",
      occurrences: 1,
      firstSeen: "2026-01-15",
      lastSeen: "2026-01-15",
    },
  ],
  openQuestions: ["Will EV subsidies continue?", "How does China compet affect margins?"],
  lessons: [],
  crossRefs: [],
  thesisCount: 1,
};

const DOSSIER_JAN: Dossier = {
  ticker: "7203",
  market: "JP",
  createdAt: "2026-01-10T09:00:00.000Z",
  latestPrice: {
    ticker: "7203",
    market: "JP",
    date: "2026-01-10",
    open: 2900,
    high: 2950,
    low: 2880,
    close: 2930,
    volume: 5000000,
  },
  incomeStatements: [],
  balanceSheets: [],
  recentFilings: [],
  risks: [],
};

const DOSSIER_FEB: Dossier = {
  ticker: "7203",
  market: "JP",
  createdAt: "2026-02-20T09:00:00.000Z",
  latestPrice: {
    ticker: "7203",
    market: "JP",
    date: "2026-02-20",
    open: 3050,
    high: 3100,
    low: 3020,
    close: 3080,
    volume: 6000000,
  },
  incomeStatements: [],
  balanceSheets: [],
  recentFilings: [],
  risks: [],
};

const MOCK_THESIS_1: Thesis = {
  id: "thesis-7203-alpha",
  ticker: "7203",
  market: "JP",
  createdAt: "2026-01-15T10:00:00.000Z",
  updatedAt: "2026-01-15T10:00:00.000Z",
  title: "Toyota EV Transition Thesis v1",
  stance: "bullish",
  horizon: "long",
  conviction: "medium",
  targetPrice: 3200,
  targetCurrency: "JPY",
  catalysts: ["EV market share gains", "Solid-state battery progress"],
  risks: [
    {
      category: "market",
      severity: "high",
      description: "競合他社の価格競争が激化している",
    },
    {
      category: "execution",
      severity: "medium",
      description: "EV battery supply chain uncertainty",
    },
  ],
  body: "Toyota is positioned to benefit from the EV transition...",
  references: ["有価証券報告書-2025"],
  version: 1,
  openQuestions: ["Will subsidies last?", "China competition intensity?"],
  invalidationPoints: ["Lose >5% market share in 2 years"],
};

const MOCK_THESIS_2: Thesis = {
  id: "thesis-7203-beta",
  ticker: "7203",
  market: "JP",
  createdAt: "2026-02-20T10:00:00.000Z",
  updatedAt: "2026-02-20T10:00:00.000Z",
  title: "Toyota EV Thesis v2 — Stance Change",
  stance: "neutral",
  horizon: "medium",
  conviction: "low",
  catalysts: ["Cautious on timeline"],
  risks: [
    {
      category: "market",
      severity: "high",
      description: "競合他社の価格競争が激化している", // same as thesis_1 — should de-duplicate
    },
    {
      category: "geopolitical",
      severity: "medium",
      description: "China EV tariff escalation",
    },
  ],
  body: "Revising stance to neutral given slower-than-expected EV ramp...",
  references: ["四半期報告書-Q3-2025"],
  version: 2,
  openQuestions: ["Will subsidies last?", "Battery cost improvement pace?"],
  stanceChanged: true,
  priorThesisId: "thesis-7203-alpha",
  changeFromPrior: "Downgrade from bullish to neutral on slower EV ramp",
  invalidationPoints: ["Regain >15% EV market share"],
};

// ─────────────────────────────────────────────────────────────────────────────
// TEST 1: writeJudgment / readJudgment round-trip
// ─────────────────────────────────────────────────────────────────────────────

console.log("\n[1] writeJudgment / readJudgment round-trip");
try {
  const filepath = await writeJudgment(MOCK_STORE);
  assert(filepath.includes("7203-judgment.json"), "writeJudgment returns correct path");

  const readBack = await readJudgment("7203");
  assert(readBack !== null, "readJudgment returns non-null for written ticker");
  assertEq(readBack?.ticker, "7203", "ticker matches");
  assertEq(readBack?.market, "JP", "market matches");
  assertEq(readBack?.thesisCount, 1, "thesisCount matches");
  assertEq(readBack?.stanceHistory[0]?.stance, "bullish", "stanceHistory[0].stance matches");
  assertEq(readBack?.recurringRisks[0]?.occurrences, 1, "recurringRisks[0].occurrences = 1");
  assertEq(readBack?.openQuestions.length, 2, "openQuestions count matches");
} catch (e) {
  assert(false, "writeJudgment/readJudgment no exception", String(e));
}

// ─────────────────────────────────────────────────────────────────────────────
// TEST 2: readJudgment returns null for unknown ticker
// ─────────────────────────────────────────────────────────────────────────────

console.log("\n[2] readJudgment returns null for unknown ticker");
try {
  const result = await readJudgment("UNKNOWN_XYZ");
  assertEq(result, null, "readJudgment(UNKNOWN_XYZ) = null");
} catch (e) {
  assert(false, "readJudgment unknown ticker no exception", String(e));
}

// ─────────────────────────────────────────────────────────────────────────────
// TEST 3: writeDossier / readPreviousDossier (date filtering)
// ─────────────────────────────────────────────────────────────────────────────

console.log("\n[3] writeDossier / readPreviousDossier date filtering");
try {
  await writeDossier(DOSSIER_JAN);   // 2026-01-10
  await writeDossier(DOSSIER_FEB);   // 2026-02-20

  // Query "before 2026-02-20" → should return JAN dossier
  const prior = await readPreviousDossier("7203", "2026-02-20");
  assert(prior !== null, "readPreviousDossier returns non-null");
  assertEq(prior?.createdAt.slice(0, 10), "2026-01-10", "prior dossier date = 2026-01-10");
  assertEq(prior?.latestPrice?.close, 2930, "prior dossier close price = 2930");

  // Query "before 2026-01-10" → should return null (no dossier before Jan)
  const none = await readPreviousDossier("7203", "2026-01-10");
  assertEq(none, null, "readPreviousDossier before earliest = null");

  // Query "before 2026-12-31" → should return FEB dossier (most recent prior to year-end)
  const latest = await readPreviousDossier("7203", "2026-12-31");
  assertEq(latest?.createdAt.slice(0, 10), "2026-02-20", "most recent prior to 2026-12-31 = FEB");
} catch (e) {
  assert(false, "readPreviousDossier no exception", String(e));
}

// ─────────────────────────────────────────────────────────────────────────────
// TEST 4: getArtifactIndex — hasJudgmentStore flag
// ─────────────────────────────────────────────────────────────────────────────

console.log("\n[4] getArtifactIndex — hasJudgmentStore");
try {
  const idx = await getArtifactIndex("7203");
  assert(idx.hasJudgmentStore === true, "hasJudgmentStore = true after writeJudgment");
  assert(idx.dossiers.length >= 2, `dossiers.length >= 2 (got ${idx.dossiers.length})`);

  const idxMissing = await getArtifactIndex("AAPL_MISSING");
  assert(idxMissing.hasJudgmentStore === false, "hasJudgmentStore = false for unknown ticker");
  assertEq(idxMissing.dossiers.length, 0, "dossiers.length = 0 for unknown");
} catch (e) {
  assert(false, "getArtifactIndex no exception", String(e));
}

// ─────────────────────────────────────────────────────────────────────────────
// TEST 5: syncJudgmentStore — creates store from Thesis
// ─────────────────────────────────────────────────────────────────────────────

console.log("\n[5] syncJudgmentStore — creates store from first Thesis");
// Use a different ticker to start fresh
const SYNC_TICKER = "9984";
const THESIS_SYNC_1: Thesis = { ...MOCK_THESIS_1, id: "thesis-9984-alpha", ticker: SYNC_TICKER };

try {
  const store1 = await syncJudgmentStore(THESIS_SYNC_1);
  assertEq(store1.ticker, SYNC_TICKER, "store.ticker = 9984");
  assertEq(store1.thesisCount, 1, "thesisCount = 1 after first sync");
  assertEq(store1.stanceHistory.length, 1, "stanceHistory.length = 1");
  assertEq(store1.currentStance?.stance, "bullish", "currentStance.stance = bullish");
  assert(store1.recurringRisks.length === 2, `recurringRisks.length = 2 (got ${store1.recurringRisks.length})`);
  assert(store1.openQuestions.length >= 1, "openQuestions.length >= 1");

  // Verify it was written to disk
  const fromDisk = await readJudgment(SYNC_TICKER);
  assert(fromDisk !== null, "syncJudgmentStore wrote to disk");
  assertEq(fromDisk?.thesisCount, 1, "disk thesisCount = 1");
} catch (e) {
  assert(false, "syncJudgmentStore (first thesis) no exception", String(e));
}

// ─────────────────────────────────────────────────────────────────────────────
// TEST 6: syncJudgmentStore — accumulates stanceHistory + de-duplication
// ─────────────────────────────────────────────────────────────────────────────

console.log("\n[6] syncJudgmentStore — stanceHistory accumulation + risk de-duplication");
const THESIS_SYNC_2: Thesis = { ...MOCK_THESIS_2, id: "thesis-9984-beta", ticker: SYNC_TICKER };

try {
  const store2 = await syncJudgmentStore(THESIS_SYNC_2);
  assertEq(store2.thesisCount, 2, "thesisCount = 2 after second sync");
  assertEq(store2.stanceHistory.length, 2, "stanceHistory.length = 2");
  assertEq(store2.currentStance?.stance, "neutral", "currentStance updated to neutral");
  assertEq(store2.stanceHistory[0]?.stance, "neutral", "newest stance first");
  assertEq(store2.stanceHistory[1]?.stance, "bullish", "prior stance second");

  // Risk de-duplication: "競合他社の価格競争が激化している" appears in both theses → occurrences = 2
  const deduped = store2.recurringRisks.find(
    (r) => r.description.includes("競合他社") && r.occurrences === 2
  );
  assert(deduped !== undefined, "repeated risk de-duplicated → occurrences = 2");

  // Total risk keys: "競合他社..." (merged×2) + "EV battery supply chain" + "China EV tariff" = 3 unique
  assertEq(store2.recurringRisks.length, 3, "recurringRisks.length = 3 (2 new + 1 merged)");

  // Open questions from both theses merged
  assert(store2.openQuestions.length >= 2, `openQuestions merged (got ${store2.openQuestions.length})`);
} catch (e) {
  assert(false, "syncJudgmentStore (second thesis) no exception", String(e));
}

// ─────────────────────────────────────────────────────────────────────────────
// TEST 7: answerCompanyQuestion intent detection (no LLM)
// For unknown ticker with no dossier, returns "low confidence no data" immediately
// ─────────────────────────────────────────────────────────────────────────────

console.log("\n[7] answerCompanyQuestion — intent detection (no LLM required)");
try {
  const r1 = await answerCompanyQuestion("TICKER_NO_DATA", "どんな企業？");
  assertEq(r1.intentDetected, "general", "intent = general for general question");
  assertEq(r1.confidence, "low", "confidence = low when no dossier");
  assert(r1.answer.length > 0, "answer is not empty");

  const r2 = await answerCompanyQuestion("TICKER_NO_DATA", "前回と何が変わった？");
  assertEq(r2.intentDetected, "diff", "intent = diff for 変わ keyword");

  const r3 = await answerCompanyQuestion("TICKER_NO_DATA", "リスクは何？");
  assertEq(r3.intentDetected, "risk", "intent = risk for リスク keyword");

  const r4 = await answerCompanyQuestion("TICKER_NO_DATA", "過去の判断は？");
  assertEq(r4.intentDetected, "history", "intent = history for 過去 keyword");
} catch (e) {
  assert(false, "answerCompanyQuestion intent detection no exception", String(e));
}

// ─────────────────────────────────────────────────────────────────────────────
// TEST 8: answerCompanyQuestion — JudgmentStore integration path
// 9984 has a JudgmentStore from tests [5]-[6] but NO dossier.
// Exercises: readJudgment() returns non-null → skips early-return →
//   buildJudgmentStoreContext() runs → judgmentHistorySummary + recurringRisks populated.
// LLM call is expected to fail (no API key) — answer will be an error string.
// ─────────────────────────────────────────────────────────────────────────────

console.log("\n[8] answerCompanyQuestion — JudgmentStore integration path (no LLM)");
try {
  // 9984 has JudgmentStore written in tests [5]-[6]; no dossier exists for this ticker
  const r5 = await answerCompanyQuestion(SYNC_TICKER, "リスクは何？", { includeHistory: true });

  // intent must be detected correctly
  assertEq(r5.intentDetected, "risk", "intent = risk for リスク question");

  // no dossier → confidence must be low
  assertEq(r5.confidence, "low", "confidence = low (no dossier, JudgmentStore only)");

  // JudgmentStore was read → judgmentHistorySummary must be populated
  assert(
    r5.judgmentHistorySummary !== undefined && r5.judgmentHistorySummary.length > 0,
    "judgmentHistorySummary populated from JudgmentStore"
  );

  // recurringRisks from JudgmentStore (3 risks written in test [6])
  assert(
    (r5.recurringRisks?.length ?? 0) > 0,
    "recurringRisks populated from JudgmentStore"
  );

  // answer is returned (LLM error message is acceptable — no API key in test env)
  assert(r5.answer.length > 0, "answer non-empty (LLM error or response)");
} catch (e) {
  assert(false, "answerCompanyQuestion JudgmentStore integration no exception", String(e));
}

// ─────────────────────────────────────────────────────────────────────────────
// Summary
// ─────────────────────────────────────────────────────────────────────────────

// Cleanup temp dir
await fs.rm(TEMP_DIR, { recursive: true, force: true });

console.log(`\n${"─".repeat(60)}`);
console.log(`SMOKE TEST RESULTS: ${passed + failed} tests, ${passed} passed, ${failed} failed`);
if (errors.length > 0) {
  console.log(`\nFailed tests:`);
  for (const e of errors) console.log(`  ✗ ${e}`);
}
console.log("─".repeat(60));

process.exit(failed > 0 ? 1 : 0);
