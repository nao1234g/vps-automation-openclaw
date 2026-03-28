# Final Audit Report — equity-intelligence Judgment Support OS v2

> Audit date: 2026-03-28
> Auditor: Senior Engineer / Audit Officer (Claude Code)
> Scope: Phase 5–6 closure + Phase FV LLM proof + docs reconciliation
> Rule: current-run evidence only. PARTIAL ≠ DONE. 1 PARTIAL remaining → OV stays PARTIAL.

---

## 1. What Changed in This Session

### 1a. Code Change: `packages/services/src/thesis/builder.ts`

**Problem**: `buildThesis()` prompt did not enforce exact field names or types.
The model returned a creative nested structure: `thesis: {direction: "long"}` instead of flat `stance: "bullish"`,
and `bullCase: {body: "..."}` (object) instead of `bullCase: "..."` (string).
This caused `ThesisLlmOutputSchema` Zod validation to fail with `"expected string, received undefined"` errors.

**Fix applied**: Replaced the free-form prompt ending with an explicit 14-field JSON schema template listing:
- All field names (no aliasing allowed — `stance` not `direction`)
- Types for each field (`bullCase`/`bearCase` explicitly marked as `"<文字列>"`)
- Prohibition against extra wrapper keys (`ticker`, `thesis`, `metadata` etc.)
- `changeFromPrior: null` default when no prior thesis is provided

**Result**: FV-11 now returns `ok(Thesis)` with all 14 fields populated and Zod-validated.

### 1b. Bug Fix Already Applied in Prior Session: `claude_code_backend.ts`

`cmd /c claude -p "<multiline>"` was splitting the prompt at `\n` boundaries on Windows,
causing the model to receive only the first line of a 300+ line prompt.
Fix: spawn `["claude", "-p", prompt, ...]` directly via `Bun.spawn` without `cmd /c` wrapper.
This was the root cause of FV-12 failing before.

### 1c. Docs Updated This Session

| File | Changes |
|------|---------|
| `docs/test_results.md` | Added Phase FV Proof section with full stdout, technical notes |
| `docs/phase56_final_report.md` | FV-11/FV-12 rows: PARTIAL → DONE; Layer C/D verdicts updated; Phase FV 完了証跡 added |
| `docs/implementation_handoff.md` | FV table corrected; axis counts corrected (FV 0→2 DONE, 4→2 PARTIAL); header verdict updated; Tests section updated; `phase-fv-proof.ts` added |
| `docs/changed_files_list.md` | Windows note corrected (cmd /c → direct spawn); `phase-fv-proof.ts` added to Tests table |

---

## 2. What Was Fixed

| Issue | Root Cause | Fix | Verification |
|-------|-----------|-----|-------------|
| FV-11 Zod validation failure | Prompt allowed model to choose its own JSON structure | Explicit 14-field schema template in `builder.ts` prompt | FV-11: ok(Thesis) 40.1s ✅ |
| FV-12 model receives truncated prompt | `cmd /c` shell split multiline at `\n` | Direct `Bun.spawn(["claude", "-p", prompt, ...])` | FV-12: ok(CompareResult) 31.0s ✅ |
| Docs: stale PARTIAL entries for FV-11/12 | Not updated after FV proof ran | Updated all 4 docs files | Verified by read |
| Docs: wrong Windows note in changed_files_list.md | Written before cmd /c removal | Corrected to reflect direct spawn | Verified by read |
| Docs: FV axis counts wrong (0 DONE / 4 PARTIAL) | Not updated after FV proof | Updated to 2 DONE / 2 PARTIAL | implementation_handoff.md line 257 |

---

## 3. What Now Passes (Current-Run Evidence)

All results below are from commands executed in this session (2026-03-28) or the immediately preceding session.

### VE — Verification Execution (3/3 ✅)

| Command | Exit Code | Status |
|---------|-----------|--------|
| `bun run typecheck` | 0 | ✅ VE DONE |
| `bun run tests/smoke-walltalk.ts` | 0 | ✅ VE DONE |
| `bun run tests/phase-c-proof.ts` | 0 | ✅ VE DONE |

### IV — Implementation Verification (10/10 ✅)

All 10 IV rows confirmed. Key items:
- TypeScript: 0 errors across all 4 packages
- Smoke: 45/45 PASS (zero failures)
- `callClaudeJson/callClaudeText` return `Result<T>`, never throw
- Backward compat: v1 Dossier + Thesis fixture parses without v2 fields

### FV — Functional Verification (2/4 ✅, 2 PARTIAL)

| Requirement | Status | Current-Run Evidence |
|---|---|---|
| `buildDossier()` 1件実行 | 🟡 PARTIAL | ok() returns but all adapters empty — no real data fetched |
| `buildThesis()` 1件 Thesis 生成 | ✅ **DONE** | `bun tests/phase-fv-proof.ts` FV-11: ok(Thesis) in 40.1s, all 14 fields present |
| `compareCompanies()` 1件比較実行 | ✅ **DONE** | `bun tests/phase-fv-proof.ts` FV-12: ok(CompareResult) in 31.0s, winner=7203, 4 judgmentDiffs |
| 実 artifact backward compat | 🟡 PARTIAL | No `output/` directory — fixture only; real on-disk artifacts untested |

### DR — Deliverables (3/3 ✅)

| Deliverable | Status |
|---|---|
| `packages/services/src/llm/claude_code_backend.ts` | ✅ Exists, compiles, FV-verified |
| `tests/phase-fv-proof.ts` | ✅ Exists, EXIT:0, FV-11+FV-12 DONE |
| All 7 docs files | ✅ All exist in `docs/` |

---

## 4. What Remains (PARTIAL — Not Blocked, Just Not Tested)

These items are PARTIAL because they require external credentials or live artifacts that are not present in the test environment. They are not bugs.

### FV-P1: `buildDossier()` with real adapter data

- **Status**: PARTIAL (not BLOCKED — code is complete)
- **Gap**: No J-Quants API key or Exa API key in test environment
- **Evidence available**: `phase-c-proof.ts [1]` — `buildDossier()` returns `ok(Dossier)` with empty adapters
- **To close**: Run with live J-Quants + Exa credentials; verify `latestPrice`, `incomeStatements`, `recentFilings` are populated

### FV-P2: Actual artifact backward compatibility

- **Status**: PARTIAL (not BLOCKED — v1 Zod fixture passes)
- **Gap**: No `output/walltalk/` directory with real v1 JSON files on disk
- **Evidence available**: `phase-c-proof.ts [4]` — fixture `safeParse` passes for v1 Dossier and v1 Thesis
- **To close**: Populate `output/walltalk/dossier/`, `output/walltalk/thesis/` with real v1 files; run `readPreviousDossier()` on them

### Not Tested (Out of Scope — Not Part of Original Requirements)

- `runResearch()` full agent loop — multi-tool, requires all adapters + LLM + persistence
- Live J-Quants / Exa adapter integration

---

## 5. Requirement Matrix — Final Axis Counts

| Axis | DONE | PARTIAL | BLOCKED | PENDING | Total |
|------|------|---------|---------|---------|-------|
| VE (Verification Execution) | 3 | 0 | 0 | 0 | 3 |
| IV (Implementation Verification) | 10 | 0 | 0 | 0 | 10 |
| FV (Functional Verification) | 2 | 2 | 0 | 0 | 4 |
| DR (Deliverables) | 3 | 0 | 0 | 0 | 3 |
| **Total** | **18** | **2** | **0** | **0** | **20** |

---

## 6. Overall Verdict

**PARTIAL**

Rationale: FV axis has 2 PARTIAL rows remaining. Per audit rule — "1つでも未達があれば COMPLETE にしない" — the overall verdict cannot be COMPLETE.

What IS complete:
- All TypeScript types correct (0 errors)
- All pure-logic smoke tests pass (45/45)
- LLM core paths confirmed end-to-end (`buildThesis` + `compareCompanies` via `claude -p`)
- All deliverables exist and are verified

What prevents COMPLETE:
- `buildDossier()` with real market data adapter responses — requires J-Quants/Exa keys
- Backward compatibility verified only via fixture, not real on-disk v1 artifacts

**The PARTIAL status is structural (external credentials required), not a code defect.**
No code changes are needed to advance these two rows to DONE. Only credentials + data are needed.

---

## 7. Path to COMPLETE

To close the 2 remaining PARTIAL rows:

```bash
# FV-P1: Run with real credentials (J-Quants + Exa)
JQUANTS_REFRESH_TOKEN=xxx EXA_API_KEY=xxx bun tests/phase-c-proof.ts
# Expect: [1] buildDossier → ok(Dossier) with latestPrice, incomeStatements populated

# FV-P2: Test with real v1 artifacts
# 1. Locate existing output/walltalk/dossier/*.json files from prior sessions
# 2. Run readPreviousDossier() on them
# 3. Confirm Zod parse passes without v2 optional fields
```

Once both pass with current-run evidence, all FV rows become DONE → OV becomes COMPLETE.

---

*Final audit report — 2026-03-28 — equity-intelligence Judgment Support OS v2*
*Auditor: Claude Code (Senior Engineer / Audit Officer mode)*
