# Gap Analysis — World-Class Claude Code OS
> Generated: 2026-03-26 | Auditor: general-purpose Agent (a5b67fa) + LEFT_EXECUTOR synthesis

---

## Executive Summary

This is an **exceptionally sophisticated** Claude Code setup (~7.5/10). The hook system demonstrates
world-class patterns: state-based gating, transcript analysis, AI-assisted fact-checking. However,
critical structural gaps must be addressed for reliable autonomous operation.

---

## CRITICAL GAPS (P1 — Fix Immediately)

### G1: WebFetch Wildcard Override ✅ FIXED
- **Problem**: Bare `"WebFetch"` entry in allow list after 80+ domain-specific entries — made entire
  domain whitelist redundant (any URL accessible)
- **Fix Applied**: Removed bare `"WebFetch"` from `settings.local.json` (2026-03-26)
- **Impact**: Domain whitelist now enforced

### G2: vps-health-gate.py 60s Timeout ✅ FIXED
- **Problem**: 60-second timeout after every Bash operation = interaction delays
- **Fix Applied**: Reduced to 30s in `settings.local.json` (2026-03-26)
- **Recommendation**: Long-term: run health gate async, cache results for 5 min

### G3: Session.json Race Condition ⚠️ OPEN
- **Problem**: 5+ hooks write to `session.json` without file locking
- **Risk**: JSON corruption on concurrent hook execution (LOW probability, HIGH impact)
- **Recommended Fix**:
  ```python
  import fcntl
  # Wrap all session.json reads/writes with flock()
  ```
- **Priority**: LOW (sequential execution is typical)

---

## HIGH-PRIORITY GAPS (P2)

### G4: Permission Model (bypassPermissions)
- **Problem**: `defaultMode: "bypassPermissions"` means deny rules are the ONLY protection
- **Current**: Works because deny list covers .env/credentials
- **Risk**: If Claude receives adversarial system prompt, can access anything not in deny list
- **Recommendation**: Test switching to `"default"` mode; add explicit allows for Bash/Edit/Write

### G5: fact-checker.py Godclass (946 lines, 30s timeout)
- **Problem**: Single hook handles 6+ verification concerns; timeout = all checks fail
- **Risk**: Slow responses; hard to debug; all-or-nothing failure mode
- **Recommendation**: Extract transcript analyzer into standalone pre-computed module
- **Effort**: HIGH (4+ hours) — defer to next sprint

### G6: Session-Start SSH Fragility
- **Problem**: 5-second SSH timeout, no retry, `2>/dev/null` hides errors
- **Risk**: VPS busy → no context injection → Claude works from stale CLAUDE.md
- **Recommended Fix**:
  ```bash
  # session-start.sh: add retry logic
  for attempt in 1 2 3; do
    VPS_STATE=$(ssh -o ConnectTimeout=10 root@163.44.124.123 "cat /opt/shared/SHARED_STATE.md" 2>&1)
    [ $? -eq 0 ] && break
    sleep 2
  done
  ```
- **Priority**: MEDIUM

### G7: PVQE-P False Negatives
- **Problem**: All `.sh`, `.yml`, `.yaml` files exempt from PVQE-P gate
  - `docker-compose.yml` can be edited without evidence plan
  - Pipeline scripts (`.sh`) can be edited without justification
- **Recommendation**: Narrow exemptions to `docs/`, `memory/`, `hooks/state/`
- **Priority**: MEDIUM

---

## MEDIUM-PRIORITY GAPS (P3)

### G8: No Hook Observability
- **Problem**: No timing dashboard; can't see which hooks are slow or catching violations
- **Impact**: Impossible to optimize or debug hook performance
- **Recommendation**: Add `observatory.py` PostToolUse hook that logs timing to `hook_timings.jsonl`

### G9: Memory System One-Way
- **Problem**: VPS → local session injection works; local session → VPS memory sync is manual
- **Impact**: Local discoveries don't persist to NEO-ONE/TWO
- **Recommendation**: Add `memory-ingestion.py` PostToolUse to auto-extract + push insights

### G10: 6 Orphaned Hooks
- **Problem**: `debug-hook.py`, `intent-confirm.py`, `mistake-auto-guard.py`,
  `h1-vps-diff.py`, `regression-runner.py`, `pvqe-p-gate.py` — not wired to events
- **Risk**: Misleading (appears active, isn't), file clutter
- **Recommendation**: Move to `.claude/hooks/deprecated/` with explanation comment

### G11: OPERATING_PRINCIPLES.md Lacks @implementation Tags
- **Problem**: 13 principles described but no hook-to-principle traceability
- **Impact**: Hard to verify which principles are actually enforced vs aspirational
- **Recommendation**: Add `@implementation: hook-name` inline for each principle

---

## STRENGTHS TO PRESERVE (Do Not Refactor)

| Feature | Why It's World-Class |
|---------|---------------------|
| NORTH_STAR.md protection | AI-resistant constitution, north-star-guard.py physical block |
| Transcript analysis (fact-checker.py) | State-based, immune to linguistic evasion |
| Session-start context injection | Combines local + VPS truth at session start |
| Research gate banned terms | Prevents @aisaintel/AISA references automatically |
| Eternal Directives (three principles) | Correctly non-negotiable, hardcoded |
| ECC Pipeline (mistake → pattern → block) | Self-improving, no git lag |
| Failure memory (35 records) | Rich audit trail for pattern recognition |

---

## IMPROVEMENTS IMPLEMENTED THIS SESSION

| Item | Change | File |
|------|--------|------|
| WebFetch wildcard | Removed bare `"WebFetch"` override | settings.local.json |
| vps-health-gate timeout | 60s → 30s | settings.local.json |
| Skills created | commit, vps-status, night-mode, health-check | .claude/skills/*.md |
| Agents directory | Created `.claude/agents/` | filesystem |

---

## RECOMMENDED NEXT SPRINT (Priority Order)

1. **session-start.sh SSH retry** (30 min) — high reliability gain
2. **PVQE-P exemption tightening** (30 min) — closes false-negative gap
3. **Move orphaned hooks to deprecated/** (15 min) — reduces confusion
4. **observatory.py hook timing** (2h) — enables future optimization
5. **session.json fcntl locking** (1h) — eliminates race condition risk
6. **fact-checker.py extraction** (4h) — deferred, complex

---

*Created by LEFT_EXECUTOR session_20260326 | Based on general-purpose Agent a5b67fa gap analysis*
