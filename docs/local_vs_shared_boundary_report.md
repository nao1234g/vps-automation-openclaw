# Local vs Shared Boundary Report

> **Purpose**: Define what runs on Windows (local) vs VPS (shared) to prevent conflicts
> **Last Verified**: 2026-03-26
> **Owner**: Naoto (vps-automation-openclaw)

---

## Architecture Overview

```
Windows (Local)                         VPS 163.44.124.123
─────────────────────────────           ──────────────────────────────────
Claude Code (Sonnet 4.6)                NEO-ONE (claude-opus-4-6)
  .claude/hooks/                         neo-telegram.service
  scripts/guard/                         /opt/claude-code-telegram/
                                        NEO-TWO (claude-opus-4-6)
  Git repo (vps-automation-openclaw)     neo2-telegram.service
  Sync: sync-vps.ps1 / git push          /opt/claude-code-telegram-neo2/
                                        NEO-GPT (OpenAI Codex CLI)
  OAuth tokens (4h auto-copy)            neo3-telegram.service
    → SCP → /opt/.claude/               Ghost CMS (nowpattern.com)
                                          ghost-nowpattern.service
                                        Docker Compose (/opt/openclaw/)
```

---

## File Ownership Rules

### Local-Only Files (never edit from VPS)
| Path | Owner | Notes |
|------|-------|-------|
| `.claude/` (entire dir) | Local Claude Code | Hooks, settings, memory |
| `.claude/hooks/*.py` | Local Claude Code | Guard hooks |
| `.claude/settings.local.json` | Local Claude Code | Permissions config |
| `scripts/guard/` | Local Claude Code | Pre/post tool guards |
| `docs/*.md` | Local Claude Code | Documentation |
| `.claude/rules/*.md` | Local Claude Code | Protected by north-star-guard.py |

### VPS-Only Files (never edit from local without SSH)
| Path | Owner | Notes |
|------|-------|-------|
| `/opt/shared/scripts/*.py` | VPS / NEO | Pipeline scripts |
| `/opt/shared/SHARED_STATE.md` | VPS auto-update | 30min cron |
| `/opt/shared/AGENT_WISDOM.md` | VPS NEO | Shared AI knowledge |
| `/opt/shared/prediction_db.json` | VPS / verifier | Prediction data |
| `/var/www/nowpattern/content/data/ghost.db` | Ghost CMS | Do not touch directly |
| `/etc/caddy/Caddyfile` | VPS infrastructure | Restart required after change |
| `/opt/claude-code-telegram/CLAUDE.md` | NEO-ONE | NEO's actual instructions |
| `/opt/claude-code-telegram-neo2/CLAUDE.md` | NEO-TWO | NEO's actual instructions |

### Shared (git sync both directions)
| Path | Sync Direction | Notes |
|------|----------------|-------|
| `data/prediction_db.json` | Local → VPS (read-only local) | Predictions |
| `data/pending_approvals.json` | Bidirectional | Approval queue |
| `scripts/*.py` (non-guard) | Local → VPS | Pipeline scripts |

---

## Conflict Prevention Rules

### Rule 1: SSH changes take priority
When VPS files are edited via SSH and git-tracked, `sync-vps.ps1` v2.0 creates backups before overwriting. Check `/opt/shared/scripts/*.bak-*` if overwrite suspected.

### Rule 2: NEO does not edit local hooks
NEO-ONE/TWO operate in `/opt/` only. They should never SSH back to the Windows machine.

### Rule 3: Local Claude Code does not write to VPS pipeline scripts
Local Claude Code (this session) edits `.claude/hooks/`, `scripts/guard/`, `docs/`.
VPS pipeline scripts (`/opt/shared/scripts/`) are edited via SSH Bash commands only.

### Rule 4: OAuth tokens flow one direction
Windows → VPS (SCP every 4 hours via Windows Task Scheduler).
Never copy from VPS → Windows.

---

## Known Conflict Zones

| Zone | Risk | Mitigation |
|------|------|-----------|
| `prediction_db.json` | Local reads stale copy | Always SSH to check live count |
| `AGENT_WISDOM.md` | VPS auto-writes, local reads | `session-start.sh` pulls latest via SSH |
| `SHARED_STATE.md` | VPS auto-updates | Read via SSH, never edit locally |
| `/etc/caddy/Caddyfile` | Must reload after change | `systemctl reload caddy` after every change |

---

## Deployment Flow

```
1. Local: edit scripts/ or .claude/hooks/
2. Local: git add + git commit (manual)
3. Local: git push origin main  ← requires user confirmation (ask rule)
4. VPS: git pull (manual or NEO-triggered)
   OR
   Windows: sync-vps.ps1 (PowerShell script, VPS-backup-aware)
```

---

## What Local Claude Code Should NEVER Do

- Write to `/opt/shared/scripts/` directly (use SSH)
- Edit Ghost SQLite DB (`/var/www/nowpattern/content/data/ghost.db`)
- Modify `/etc/caddy/` files without SSH
- Change systemd service files
- Modify NEO's CLAUDE.md files in `/opt/claude-code-telegram*/`
