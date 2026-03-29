# AI-to-AI Collaboration System — Complete Reference
> Claude Code (Opus 4.6) + OpenAI Codex (GPT-5.4) 双方向レビューシステム
> Version 2.0 — 2026-03-29

---

## Architecture

```
┌─────────────────────────────────┐
│  Claude Code (Opus 4.6)         │
│  Windows / VSCode Extension     │
│  Role: Primary Developer        │
│  Strengths: Deep codebase ctx,  │
│    hooks system, pattern DB     │
└────────┬───────────┬────────────┘
         │           │
    ┌────▼────┐ ┌────▼──────────┐
    │ smux    │ │ .agent-mailbox│
    │ tmux-   │ │ File-based    │
    │ bridge  │ │ JSON protocol │
    │ (chat)  │ │ (review)      │
    └────┬────┘ └────┬──────────┘
         │           │
┌────────▼───────────▼────────────┐
│  Codex (GPT-5.4 xhigh)         │
│  WSL2 Ubuntu / tmux "agents"    │
│  Role: Adversarial Reviewer     │
│  Strengths: Fresh perspective,  │
│    no context bias, cross-check │
└─────────────────────────────────┘
```

## Two Communication Channels

### Channel 1: Live Chat (smux tmux-bridge)
**Use for**: Quick questions, clarifications, brainstorming, real-time discussion.

```bash
# Send message to Codex
$HOME/.smux/tmux-bridge read codex 3 >/dev/null 2>&1
$HOME/.smux/tmux-bridge type codex "Your message here"
sleep 0.5
$HOME/.smux/tmux-bridge read codex 3 >/dev/null 2>&1
$HOME/.smux/tmux-bridge keys codex Enter

# Read Codex's response (wait 10-30s for response)
tmux capture-pane -t agents:0.1 -p -S -30
```

**Constraints**:
- ~40 char effective bandwidth per `type` command (tmux limitation)
- For long messages: break into multiple `type` calls or use Channel 2
- Always `read` before `type`/`keys` (Read Guard)

### Channel 2: File-based JSON Protocol (codex-review.sh)
**Use for**: Code reviews, structured analysis, anything >100 chars.

```bash
# Automated review pipeline
bash scripts/codex-review.sh                      # All changes
bash scripts/codex-review.sh .claude/hooks/        # Specific directory
bash scripts/codex-review.sh --security            # Security files only

# Manual file exchange
echo "message" > .agent-mailbox/claude-to-codex.md
# Wait for Codex to read and write response
cat .agent-mailbox/codex-to-claude.md
```

**Protocol**:
- Request: `.agent-mailbox/review-request.json` (structured JSON)
- Full diff: `.agent-mailbox/review-diff.patch` (no truncation)
- Response: `.agent-mailbox/review-response.md` (structured markdown)

---

## Review Protocol

### When to Request Review

| Trigger | Priority | Mode |
|---------|----------|------|
| Hooks modification (fact-checker, guards) | **Critical** | `--security` |
| Production script changes | High | Specific files |
| New regression tests | High | Specific files |
| Architecture changes | Medium | Full diff |
| Documentation changes | Low | Optional |

### Review Request Format (v2 JSON)

```json
{
  "version": "2.0",
  "timestamp": "ISO-8601",
  "reviewer": "codex",
  "requester": "claude-code",
  "scope": "description of what changed",
  "diff_file": ".agent-mailbox/review-diff.patch",
  "diff_lines": 150,
  "security_mode": true,
  "checklist": [
    "correctness",
    "security",
    "nowpattern_invariants",
    "edge_cases",
    "regression_risk"
  ]
}
```

### Review Response Format

```markdown
# Review: `filename.py`

## Findings

1. **Critical** [`file.py:42-50`]: Description of the issue
   - **Concrete fix:** Exact code or approach to fix it

2. **Warning** [`file.py:100`]: Description
   - **Concrete fix:** ...

3. **Info** [`file.py:200`]: Suggestion
   - **Concrete fix:** ...
```

Severity levels:
- **Critical**: Security hole, data loss risk, invariant violation
- **Warning**: Logic bug, bypass possible, false positive/negative
- **Info**: Improvement suggestion, edge case handling

---

## Post-Review Workflow

After receiving a review:

```
1. READ review findings carefully
2. IMPLEMENT each fix (Critical first, then Warning, then Info)
3. VERIFY syntax: python -m py_compile <file>
4. ADD regression tests for each fix to regression-runner.py
5. RUN regression suite: python .claude/hooks/regression-runner.py
6. CONFIRM all tests pass (including new ones)
7. UPDATE regression_floor.json (auto-updated on all-PASS)
```

### Adding Regression Tests for Review Findings

For pattern-matching tests (BUILTIN_TESTS):
```python
("TEST_NAME",
 "trigger message that should be blocked/passed",
 True),  # True=should_block, False=should_pass
```

For proof-checking tests (PROOF_GATE_TESTS):
```python
("TEST_NAME",
 "message with/without proof",
 ["/tmp/test_file.py"],  # edited files (triggers unverified edit gate)
 True),  # True=should_block, False=should_pass
```

---

## Codex Instructions (inject when starting Codex session)

When initializing the Codex pane, send this system context:

```
You are a code reviewer for the Nowpattern project (nowpattern.com).
Your role: adversarial reviewer. Find bugs Claude Code missed.

Key context:
- fact-checker.py: Stop hook that blocks Claude's output (exit 2 = block)
- regression-runner.py: Tests all guards work (currently 56/56 PASS)
- mistake_patterns.json: Dynamic error patterns (37 patterns)
- KNOWN_MISTAKES.md: Human-readable error documentation

Review checklist:
1. Correctness: Does the logic match the stated intent?
2. Security: Injection, bypass, data leak?
3. Invariants: prediction_db integrity, Brier Score rules
4. Edge cases: Empty input, None vs [], encoding, timeout
5. Regression risk: Could this break existing 56 tests?

Output format: Write to .agent-mailbox/review-response.md
Use: **Severity** [file:line]: description + concrete fix
```

---

## tmux Session Setup

```bash
# In WSL2 Ubuntu:
tmux new-session -d -s agents -x 200 -y 50
tmux split-window -h -t agents

# Pane 0 (%0): Claude Code relay (optional)
# Pane 1 (%1): Codex
tmux send-keys -t agents:0.1 'codex --model o4-mini-high --approval-mode full-auto' Enter

# Verify:
tmux list-panes -t agents
```

---

## Known Limitations & Mitigations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| tmux 40-char bandwidth | Live chat truncation | Use file-based protocol for long content |
| One-directional init | Claude always initiates | Codex can write to mailbox proactively |
| No auto-trigger | Review is manual | Integrate into pre-commit hook (future) |
| Codex context window | May miss deep relationships | Provide focused scope, not full repo |
| WSL2 file sync latency | ~1s delay on mailbox files | Built-in polling with 5s interval |

---

## Quick Reference Commands

```bash
# Live chat with Codex
BRIDGE=$HOME/.smux/tmux-bridge
$BRIDGE read codex 3 >/dev/null 2>&1 && $BRIDGE type codex "message" && sleep 0.3 && $BRIDGE read codex 3 >/dev/null 2>&1 && $BRIDGE keys codex Enter

# Read Codex response
tmux capture-pane -t agents:0.1 -p -S -30

# Automated code review
bash scripts/codex-review.sh --security

# Full regression after applying fixes
python .claude/hooks/regression-runner.py

# Check review results
cat .agent-mailbox/review-response.md
```

---

*v2.0 — 2026-03-29. All critique holes addressed: JSON protocol, full diff, scope filtering, regression tests for findings.*
