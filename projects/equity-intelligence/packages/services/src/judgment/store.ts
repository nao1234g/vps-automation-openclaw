/**
 * JudgmentStore — Layer 2 structured judgment memory per ticker
 *
 * syncJudgmentStore() reads any existing JudgmentStore from walltalk,
 * integrates a new Thesis into it (stance history, recurring risks,
 * open questions), then writes the updated store back.
 *
 * This is the bridge between file-based Markdown theses (Layer 1) and
 * the future Judgment Memory OS (Layer 3).
 *
 * No LLM calls — pure data merging / bookkeeping.
 */

import { writeJudgment, readJudgment } from "@equity/walltalk";
import type {
  Thesis,
  JudgmentStore,
  StanceHistoryItem,
  RecurringRisk,
  RiskNote,
} from "@equity/domain";

// ── syncJudgmentStore ─────────────────────────────────────────────────────────

/**
 * Integrates a newly-built Thesis into the persisted JudgmentStore.
 * Creates the store if it doesn't exist yet.
 *
 * @returns The updated (and written) JudgmentStore.
 */
export async function syncJudgmentStore(thesis: Thesis): Promise<JudgmentStore> {
  const existing = await readJudgment(thesis.ticker);
  const now = new Date().toISOString();
  const todayDate = now.slice(0, 10);

  // ── Build StanceHistoryItem from this thesis ───────────────────────
  const newStance: StanceHistoryItem = {
    thesisId: thesis.id,
    date: thesis.createdAt.slice(0, 10),
    stance: thesis.stance,
    conviction: thesis.conviction,
    title: thesis.title,
    targetPrice: thesis.targetPrice,
  };

  // ── Merge stance history (newest first, deduplicate by thesisId) ───
  const previousHistory: StanceHistoryItem[] = existing
    ? existing.stanceHistory.filter((s) => s.thesisId !== thesis.id)
    : [];
  const allStances: StanceHistoryItem[] = [newStance, ...previousHistory];

  // ── Merge recurring risks ──────────────────────────────────────────
  const recurringRisks = mergeRecurringRisks(
    existing?.recurringRisks ?? [],
    thesis.risks ?? [],
    todayDate
  );

  // ── Merge open questions (from this thesis + carry-forward existing) ─
  const newQuestions: string[] = thesis.openQuestions ?? [];
  const existingQuestions: string[] = existing?.openQuestions ?? [];
  const allOpenQuestions = Array.from(
    new Set([...newQuestions, ...existingQuestions])
  ).slice(0, 20);

  // ── Build updated store ───────────────────────────────────────────
  const store: JudgmentStore = {
    ticker: thesis.ticker,
    market: thesis.market,
    updatedAt: now,
    stanceHistory: allStances,
    currentStance: newStance,
    recurringRisks,
    openQuestions: allOpenQuestions,
    lessons: existing?.lessons ?? [],
    crossRefs: existing?.crossRefs ?? [],
    thesisCount: allStances.length,
  };

  await writeJudgment(store);
  return store;
}

// ── Internal helpers ──────────────────────────────────────────────────────────

function mergeRecurringRisks(
  existing: RecurringRisk[],
  newRisks: RiskNote[],
  date: string
): RecurringRisk[] {
  // Map keyed by normalized description
  const map = new Map<string, RecurringRisk>();

  for (const r of existing) {
    map.set(normalizeRiskKey(r.description), r);
  }

  for (const nr of newRisks) {
    const key = normalizeRiskKey(nr.description);
    const prev = map.get(key);
    if (prev) {
      map.set(key, {
        ...prev,
        occurrences: prev.occurrences + 1,
        severity: nr.severity, // update to latest severity
        lastSeen: date,
      });
    } else {
      map.set(key, {
        category: nr.category,
        severity: nr.severity,
        description: nr.description,
        occurrences: 1,
        firstSeen: date,
        lastSeen: date,
      });
    }
  }

  // Sort by occurrences desc, then by lastSeen desc
  return Array.from(map.values()).sort((a, b) => {
    if (b.occurrences !== a.occurrences) return b.occurrences - a.occurrences;
    return b.lastSeen.localeCompare(a.lastSeen);
  });
}

function normalizeRiskKey(description: string): string {
  return description
    .toLowerCase()
    .replace(/[^\w\s\u3040-\u9fff]/g, "") // keep CJK
    .trim()
    .slice(0, 60);
}
