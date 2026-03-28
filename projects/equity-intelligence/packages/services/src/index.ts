// Research agent (LangChain tool-calling)
export { runResearch } from "./research/agent.js";

// Dossier layer — structured company data assembly
export { buildDossier } from "./dossier/builder.js";
export type { DossierBuildOptions, DossierBuildSources } from "./dossier/builder.js";

// Thesis layer — LLM-driven investment thesis generation
export { buildThesis, extractRisks } from "./thesis/builder.js";
export type { ThesisBuildOptions } from "./thesis/builder.js";

// Compare layer — multi-company dossier comparison
export { compareCompanies } from "./compare/index.js";
export type { CompareTarget, CompareResult, CompareOptions } from "./compare/index.js";

// Judgment Memory — read-only past thesis context
export { FileJudgmentMemory, judgmentMemory } from "./judgment/memory.js";
export type { JudgmentEntry, JudgmentMemory } from "./judgment/memory.js";

// JudgmentStore — structured Layer 2 judgment memory (read/write)
export { syncJudgmentStore } from "./judgment/store.js";

// Walltalk Query — natural language Q&A over artifacts
export { answerCompanyQuestion } from "./query/walltalk.js";
export type { WalltalkQueryOptions, WalltalkQueryResult } from "./query/walltalk.js";
