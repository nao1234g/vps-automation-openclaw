# Current State Map — Naoto Intelligence OS / Claude Code Setup
> Generated: 2026-03-26 | Auditor: Explore Agent (a6547df) + LEFT_EXECUTOR synthesis

---

## 1. FILE INVENTORY

| Category | Count | Total Size | Notes |
|----------|-------|-----------|-------|
| Hook scripts (Python) | 23 | ~200 KB | 17 active, 6 orphaned |
| Hook scripts (Bash) | 6 | ~15 KB | session-start.sh is largest (13.9 KB) |
| Rules files | 7 | ~120 KB | All @imported into CLAUDE.md |
| State files (JSON) | 10 | ~90 KB | Task ledger, failure memory, approval queue |
| Memory entries | 37 | ~400 KB | Session summaries + research notes |
| Skills | 4 | ~8 KB | commit, vps-status, night-mode, health-check |
| Agent definitions | 0 | — | Directory created, empty |

---

## 2. HOOK LIFECYCLE MAP (Active Hooks Only)

```
UserPromptSubmit
  ├─ flash-cards-inject.sh    — Night Mode autonomy injection
  ├─ feedback-trap.py         — PVQE compliance + approval queue
  └─ backlog-guard.py         — Open task conflict detection

PreToolUse (Edit|Write)
  ├─ research-gate.sh/.py     — Banned terms + research mandate
  ├─ llm-judge.py             — Gemini semantic fact-check
  ├─ north-star-guard.py      — Eternal Directives protection
  ├─ ui-layout-guard.py       — CSS/layout change approval
  ├─ pvqe-p-gate.py           — Evidence plan requirement
  ├─ pre_edit_task_guard.py   — Task ledger validation
  └─ task_state_integrity.py  — State sanity check

PreToolUse (Bash)
  ├─ vps-ssh-guard.py         — VPS health preflight
  └─ release_gate.py          — Destructive command block

Stop (Post-generation)
  ├─ fact-checker.py          — 946-line multi-pattern verifier (30s timeout)
  └─ pvqe-p-stop.py           — Evidence execution validation

PostToolUse (Edit|Write)
  ├─ post_edit_task_reconcile.py — Task ledger sync
  ├─ task_close_memory_check.py  — Completion criteria check
  ├─ task_state_integrity.py     — Side-effect detection
  ├─ auto-codifier.py            — Mistake → guard pattern auto-generation
  ├─ rules-sync.py               — Sync rules to VPS for NEO access
  └─ change-tracker.py           — Diff log + changelog

PostToolUse (Bash)
  └─ vps-health-gate.py       — Full VPS health check (60s timeout ⚠️)

PostToolUse (WebSearch|WebFetch)
  └─ research-reward.sh       — Research credit tracking

PostToolUse (TodoWrite)
  └─ task-tracker.py          — Todo audit trail

SessionStart
  └─ session-start.sh         — VPS state injection + AGENT_WISDOM + ledger

SessionEnd
  └─ session-end.sh           — Sync AGENT_WISDOM to VPS

PostToolUseFailure
  ├─ failure_capture.py       — Root cause taxonomy recording
  └─ error-tracker.sh         — Repeat pattern alert
```

### Orphaned Hooks (Not in settings.local.json)
- `debug-hook.py` — Development artifact
- `intent-confirm.py` — Referenced in CLAUDE.md but not wired
- `mistake-auto-guard.py` — Superseded by fact-checker.py
- `h1-vps-diff.py` — Specific to old H1 setup
- `regression-runner.py` — 25-test suite, not in CI/cron
- `pvqe-p-gate.py` — Present but bypassed in Night Mode

---

## 3. SETTINGS.LOCAL.JSON KEY CONFIGURATIONS

### Permissions
```json
"defaultMode": "bypassPermissions"  ← All ops allowed unless denied
```

### Known Issues
1. **WebFetch wildcard** (line ~131): bare `"WebFetch"` entry after 80+ domain whitelist makes domain list redundant
2. **north-star-guard.py** registered 3 times: PreToolUse(Write), PreToolUse(Edit), PostToolUse(Edit) — redundant
3. **vps-health-gate.py** timeout: 60,000ms on every Bash postToolUse — performance bottleneck

### Security Denials (Active)
- Read: `.env`, `.env.*`, `*credentials*`, `*secret*`, `*private_key*`, `*.pem`, `*.key`
- Bash: `rm -rf /`, `dd if=`, `mkfs`, `fdisk`, `DROP TABLE`, `DROP DATABASE`

---

## 4. RULES STACK (CLAUDE.md @import chain)

```
CLAUDE.md (222 lines)
  ├─ NORTH_STAR.md            (33.5 KB) — Mission + Eternal Directives
  ├─ OPERATING_PRINCIPLES.md  (36.4 KB) — 13 universal principles
  ├─ execution-map.md         (9.4 KB)  — Principle → hook mapping
  ├─ agent-instructions.md    (3.9 KB)  — Type1/2 judgment
  ├─ infrastructure.md        (3.6 KB)  — VPS/Docker/NEO
  ├─ content-rules.md         (15.4 KB) — X/Ghost/article rules
  └─ prediction-design-system.md (6.5 KB) — Frozen UI baseline
```

Total context loaded per session: ~110 KB of rules

---

## 5. STATE FILES

| File | Size | Purpose |
|------|------|---------|
| `state/task_ledger.json` | 39.6 KB | 7-11 active tasks (T001-T011) |
| `state/failure_memory.json` | 5.9 KB | 35 failure records |
| `state/approval_queue.json` | 5.0 KB | Pending LEVEL 2 decisions |
| `state/constitution_candidates.json` | 632 B | AI-proposed rule changes |
| `state/memory_routing_rules.json` | 6.6 KB | Smart context injection rules |
| `hooks/state/mistake_patterns.json` | 10.8 KB | 20+ auto-generated guard patterns |
| `hooks/state/prevention_log.json` | 8.2 KB | All fact-checker.py blocks |
| `hooks/state/chaos_test_report.json` | 9.0 KB | Regression test results |

---

## 6. MATURITY SCORES (per Gap Analysis agent)

| Dimension | Score | Bottleneck |
|-----------|-------|-----------|
| Hook sophistication | 9/10 | ✅ World-class transcript analysis |
| Rule clarity | 8/10 | CLAUDE.md context load |
| Enforcement coverage | 8/10 | PVQE-P false negatives on .sh/.yml |
| Observability | 4/10 | ❌ No hook metrics dashboard |
| Resilience | 6/10 | fact-checker 30s timeout = single failure point |
| Maintainability | 5/10 | 24 hooks, godclass fact-checker |
| Security | 6/10 | bypassPermissions undermines deny list |

**Overall: 7.5/10 — Advanced, needs production hardening**

---

*Created by LEFT_EXECUTOR session_20260326 | Based on Explore Agent a6547df audit*
