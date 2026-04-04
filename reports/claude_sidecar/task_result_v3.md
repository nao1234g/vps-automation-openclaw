# Claude Code Sidecar -- Task Result v3
> Generated: 2026-04-04 | Agent: claude-opus-4-6 | Mission Contract: v3 | Lexicon: v4
> Version: v3 (stop-proof contract + drift canonicalization + codex action packet)
> Parent: task_result_v2 (slug-level distribution audit)

---

## Scope & Completion

| Metric | Value |
|--------|-------|
| scope_completion_pct | 100% |
| overall_completion_estimate_pct | 14% (estimate) |
| reached_100_pct_for_this_scope | true |

### Bounded Tasks (this session)

| # | Task | Status |
|---|------|--------|
| A | Stop-proof sidecar contract (4 mandatory files) | DONE |
| B | 100% completion semantics definition | DONE |
| C | NAOTO OS <-> Nowpattern drift canonicalization | DONE |
| D | Codex action packet (5 items, priority-ordered) | DONE |

### What "100% for this scope" means

All 5 mandatory deliverables exist with all required fields. No blocking_reason remains. No next_exact_step is pending within scope. Production scripts are untouched.

### What "14% overall" means

distribution_allowed_ratio is 44.73% (target 65%). Sidecar has provided audit + action packet but Codex has not yet applied IC-1/IC-2/IC-3 changes. Drift items are documented but not yet fixed in source files. 14% = audit complete + contract established, implementation pending.

---

## A. Stop-Proof Sidecar Contract

### Problem

Prior sidecar sessions had no machine-readable progress tracking. If Claude Code stopped mid-task, Codex had no way to know what was done vs pending.

### Solution: 4 Mandatory Files

| File | Path | Update Frequency |
|------|------|-----------------|
| Session Status | `reports/claude_sidecar/session_status.json` | At session start, each phase boundary, session end/interruption |
| Heartbeat | `reports/claude_sidecar/heartbeat.json` | At each phase completion |
| Task Result | `reports/claude_sidecar/task_result_v{N}.json` | Once per session at completion |
| Resume Prompt | `reports/claude_sidecar/resume_prompt.txt` | At session end regardless of status |

### Contract Invariants

1. `session_status.json` is ALWAYS written BEFORE any other work in a phase
2. `heartbeat.json` is ALWAYS written at phase completion BEFORE moving to next phase
3. If session is about to stop, update `session_status.json` with `status=blocked`, `blocking_reason`, and `next_exact_step` BEFORE stopping
4. Silent stops are prohibited
5. `resume_prompt.txt` is written at session end regardless of completion status
6. Production scripts in edit-prohibited set are never modified

### session_status.json Required Fields

```json
{
  "generated_at": "ISO timestamp",
  "agent": "claude-code-sidecar",
  "task_id": "unique task identifier",
  "status": "running|blocked|completed",
  "current_phase": "human-readable phase name",
  "scope_completion_pct": 0,
  "overall_completion_estimate_pct": 0,
  "reached_100_pct_for_this_scope": false,
  "blocking_reason": "empty string if not blocked",
  "next_exact_step": "empty string if completed",
  "files_written": [],
  "safe_write_set": []
}
```

---

## B. 100% Completion Semantics

### scope_completion_pct

- **Definition**: Percentage of the bounded tasks assigned to THIS sidecar session that are complete.
- **Denominator**: The explicit list of tasks in the session's scope_definition.
- **When 100 = 100**: All deliverables exist with all required fields. No blocking_reason. No pending next_exact_step within scope.

### overall_completion_estimate_pct

- **Definition**: Estimated progress toward the full NAOTO OS / Nowpattern operational target.
- **Targets**: distribution_allowed_ratio >= 65%, all drift resolved, all IC items in production.
- **Always marked as estimate**. Never presented as a fact.
- **Calculation basis**: Current distribution ratio vs target, audit completeness, implementation status.

### reached_100_pct_for_this_scope

- **Definition**: Boolean. True if and only if scope_completion_pct == 100 AND all deliverables pass validation.
- **This is scope-specific**, not system-wide. A session can reach 100% for its scope while overall is 14%.

---

## C. NAOTO OS <-> Nowpattern Drift

### Identity Hierarchy (Canonical)

```
NAOTO OS
  = The operating system (Founder OS)
  = Intelligence and execution layer governing all projects
  = Defined in: mission_contract.py founder_os.canonical_name

  Nowpattern
    = Primary project under NAOTO OS
    = A verifiable forecast platform (nowpattern.com)
    = Defined in: mission_contract.py north_star
```

**Rule**: NAOTO OS contains Nowpattern. Nowpattern is not the OS.

### DRIFT-01: Identity Hierarchy Confusion (info)

- **Observed**: Some docs use "Nowpattern" as if it were the OS name
- **Canonical**: NAOTO OS = OS, Nowpattern = platform/project
- **Guard**: PROJECT_DRIFT_GUARD in mistake_patterns.json
- **Action**: Docs clarification only

### DRIFT-02: Brier Score Notation (info)

- **Observed**: Three values coexist: 0.1780 / 0.1828 / 0.4759
- **Canonical**: binary methodology, n=53 (HIT+MISS), avg = **0.4759**, accuracy = 66.0%
- **Stale values**: 0.1780 (VPS live subset n=7), 0.1828 (stale stats snapshot)
- **Guard**: M006 in mistake_registry.json
- **Action**: Remove stale values from any docs citing 0.1780 or 0.1828

### DRIFT-03: PVQE V Definition (warning)

- **Observed**: NORTH_STAR.md and OPERATING_PRINCIPLES.md say V = "改善速度" (improvement speed)
- **Canonical**: mission_contract.py L49 says V = "価値密度" (value density)
- **Affected files**: `.claude/rules/NORTH_STAR.md`, `.claude/rules/OPERATING_PRINCIPLES.md`
- **Action**: Update both files. V = "価値密度"

### DRIFT-04: Public/Internal Wording (info)

- **Observed**: No active public-facing wording violations detected
- **Canonical source**: scripts/canonical_public_lexicon.py (v4)
- **Lexicon shims**: public_lexicon.py, product_lexicon.py correctly forward to canonical
- **Action**: None required

---

## D. Codex Action Packet (Priority Order)

### CAP-1: IC-1 Dual-Flag Threshold Relaxation (HIGH)

| Field | Value |
|-------|-------|
| Title | Relax dual-flag verified_count threshold from >= 2 to >= 1 |
| Why Now | 196 posts (41% of published) blocked solely by dual AUTO_SAFE verified_count >= 2. Single largest blocker. |
| Expected Impact | +20pp (44.73% -> ~65%) |
| Target Files | `scripts/article_release_guard.py` L86-89 |
| Risk | low |
| Done Definition | After manifest regen: distribution_allowed_ratio >= 60% AND truth_blocked == 0 AND all 196 IC-1 slugs in (auto_safe, editorial_review_advised) |

### CAP-2: IC-3 External URL Fallback (MEDIUM)

| Field | Value |
|-------|-------|
| Title | Add external_url_count >= 2 fallback for single-flag posts |
| Why Now | 4 FINANCIAL_CRISIS-only posts blocked with no fallback. Low-risk escape hatch. |
| Expected Impact | +1-2pp |
| Target Files | `scripts/article_release_guard.py` L90-91 |
| Risk | low |
| Done Definition | After manifest regen: 4 IC-3 slugs have distribution_allowed = true |

### CAP-3: IC-2 WAR_CONFLICT Regex Narrowing (MEDIUM)

| Field | Value |
|-------|-------|
| Title | Narrow WAR_CONFLICT regex to compound phrases |
| Why Now | 59 posts blocked by bare keyword regex firing on 96% of geopolitics articles. |
| Expected Impact | +5-10pp (regex-dependent) |
| Target Files | `scripts/article_release_guard.py` L45-52 |
| Risk | medium -- requires before/after comparison of all 474 posts |
| Done Definition | WAR_CONFLICT flag count drops >= 30% AND no new truth_blocked AND ratio >= 70% |

### CAP-4: Empty Risk Flags Edge Case (LOW)

| Field | Value |
|-------|-------|
| Title | Fix classify_release_lane for empty risk_flags |
| Why Now | 3 posts have risk_flags=[] but get EDITOR_REVIEW_REQUIRED: (empty) error. Logic gap. |
| Expected Impact | +0.6pp (3 posts) |
| Target Files | `scripts/article_release_guard.py` L224-226 |
| Risk | low |
| Done Definition | After manifest regen: 3 Other slugs have distribution_allowed = true, release_errors empty |

### CAP-5: PVQE V Definition Fix (LOW)

| Field | Value |
|-------|-------|
| Title | Fix V definition in NORTH_STAR.md and OPERATING_PRINCIPLES.md |
| Why Now | V = "改善速度" in docs vs "価値密度" in mission_contract.py. Misleads agents. |
| Expected Impact | docs-only |
| Target Files | `.claude/rules/NORTH_STAR.md`, `.claude/rules/OPERATING_PRINCIPLES.md` |
| Risk | low |
| Done Definition | Both files have V = "価値密度". lexicon_contract_audit.py passes. |

### Cumulative Effect Projection

```
Current:                            44.73%
After CAP-1 (IC-1):                 ~65%
After CAP-1 + CAP-2 (IC-3):        ~67%
After CAP-1 + CAP-2 + CAP-3 (IC-2): ~75%
After all 4 code changes:           ~76%
Target:                             >= 65%
```

---

## Verification Commands (for Codex after implementation)

```bash
# After CAP-1/CAP-2/CAP-3/CAP-4 changes:
python3 /opt/shared/scripts/build_article_release_manifest.py
python3 /opt/shared/scripts/article_release_guard.py --report
# Verify: distribution_allowed_ratio_pct >= 65%
# Verify: truth_blocked == 0

# After CAP-5 docs fix:
python3 /opt/shared/scripts/lexicon_contract_audit.py
```

---

## Evidence References

| Source | What it proves |
|--------|---------------|
| `reports/article_release_manifest.json` | 474 posts, 262 blocked, per-post risk_flags/release_lane |
| `reports/content_release_snapshot.json` | 44.73% distribution ratio, 0 truth_blocked |
| `reports/one_pass_completion_gate.json` | All governance/UI/crawl/e2e checks passing |
| `reports/claude_sidecar/task_result_v2.json` | Slug-level IC-1/IC-2/IC-3 breakdown |
| `scripts/mission_contract.py` | PVQE canonical definitions, founder_os = NAOTO OS |
| `scripts/agent_bootstrap_context.py` | Bootstrap payload structure |
| `data/mistake_registry.json` | M006 Brier guard, existing mistake patterns |
| `.claude/rules/NORTH_STAR.md` | V = "改善速度" (drift source) |
| `.claude/rules/OPERATING_PRINCIPLES.md` | V = "改善速度" (drift source) |

---

## Do Not Touch

- `data/prediction_db.json`
- `scripts/one_pass_completion_gate.py`
- `scripts/release_governor.py`
- `scripts/article_release_guard.py`
- `scripts/build_article_release_manifest.py`
- `scripts/prediction_deploy_gate.py`
- `scripts/synthetic_user_crawler.py`
- `reports/content_release_snapshot.json`
- `reports/one_pass_completion_gate.json`
- `reports/article_release_manifest.json`

---

*End of sidecar task result v3. Machine-readable: `task_result_v3.json`*
