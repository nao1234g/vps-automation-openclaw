# Hooks / Skills / Agents Matrix
> Updated: 2026-03-26

## Skills (`.claude/skills/`)
| Skill | File | Trigger | Purpose |
|-------|------|---------|---------|
| `/commit` | `commit.md` | Manual | Stage + conventional commit message |
| `/vps-status` | `vps-status.md` | Manual | VPS service status report |
| `/night-mode` | `night-mode.md` | Manual | Toggle autonomous Night Mode |
| `/health-check` | `health-check.md` | Manual | Site health + HTTP status check |

## Agent Definitions (`.claude/agents/`)
| Agent | File | Scope | Purpose |
|-------|------|-------|---------|
| `vps-explorer` | `vps-explorer.md` | Read-only, SSH | Explore VPS state, files, logs |
| `article-auditor` | `article-auditor.md` | Read-only | Ghost CMS article quality audits |

## Active Hooks (settings.local.json)
| Event | Hook | Matcher | Role |
|-------|------|---------|------|
| UserPromptSubmit | flash-cards-inject.sh | * | Night Mode autonomy injection |
| UserPromptSubmit | feedback-trap.py | * | PVQE compliance gate |
| UserPromptSubmit | backlog-guard.py | * | Task conflict detection |
| PreToolUse | research-gate.sh | Edit\|Write\|WebSearch\|Read | Research mandate |
| PreToolUse | research-gate.py | Edit\|Write | Banned terms (AISA/@aisaintel) |
| PreToolUse | llm-judge.py | Edit\|Write | Gemini semantic fact-check |
| PreToolUse | north-star-guard.py | Write | NORTH_STAR.md protection |
| PreToolUse | north-star-guard.py | Edit | Eternal Directives protection |
| PreToolUse | ui-layout-guard.py | Edit\|Write\|Bash | UI change approval gate |
| PreToolUse | pvqe-p-gate.py | Edit\|Write | Evidence plan requirement |
| PreToolUse | pre_edit_task_guard.py | Edit\|Write | Task ledger validation |
| PreToolUse | task_state_integrity.py | Edit\|Write | State sanity check |
| PreToolUse | vps-ssh-guard.py | Bash | VPS health preflight |
| PreToolUse | release_gate.py | Bash | Destructive command block |
| Stop | fact-checker.py | * | 946-line multi-pattern verifier |
| Stop | pvqe-p-stop.py | * | Evidence execution validation |
| PostToolUse | vps-health-gate.py | Bash | VPS health post-check (30s) |
| PostToolUse | task-tracker.py | TodoWrite | Todo audit trail |
| PostToolUse | change-tracker.py | Edit\|Write\|Bash | Diff changelog |
| PostToolUse | auto-codifier.py | Edit\|Write | Mistake → guard auto-generation |
| PostToolUse | rules-sync.py | Edit\|Write | Sync rules to VPS |
| PostToolUse | north-star-guard.py | Edit | CHANGELOG enforcement |
| PostToolUse | post_edit_task_reconcile.py | Edit\|Write | Task ledger sync |
| PostToolUse | task_close_memory_check.py | Edit\|Write | Completion criteria check |
| PostToolUse | research-reward.sh | WebSearch\|WebFetch | Research credit tracking |
| SessionStart | session-start.sh | * | VPS state + AGENT_WISDOM injection |
| SessionEnd | session-end.sh | * | AGENT_WISDOM VPS sync |
| PostToolFailure | failure_capture.py | * | Root cause taxonomy recording |
| PostToolFailure | error-tracker.sh | * | Repeat pattern alert |

## Orphaned Hooks (Not Wired)
| File | Last Known Purpose | Recommended Action |
|------|-------------------|-------------------|
| debug-hook.py | Development debugging | Archive to deprecated/ |
| intent-confirm.py | CLAUDE.md references but unwired | Evaluate + wire or archive |
| mistake-auto-guard.py | Superseded by fact-checker.py | Archive |
| h1-vps-diff.py | H1-specific (old setup) | Archive |
| regression-runner.py | 25-test suite | Wire to PostToolUse or cron |
| pvqe-p-gate.py | Bypassed in Night Mode | Document bypass rationale |
