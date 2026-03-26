# Night Mode Operating Model

> **Status**: Production
> **Last Updated**: 2026-03-26
> **Owner**: Naoto (vps-automation-openclaw)

---

## What is Night Mode?

Night Mode is a flag-based autonomous operating mode for Claude Code. When Naoto is away (sleeping, traveling), the AI executes pre-approved work without asking for human confirmation.

**Activation / Deactivation:**
```bash
# Turn ON (before leaving)
bash scripts/night-mode-on.sh

# Turn OFF (after returning)
bash scripts/night-mode-off.sh
```

**How it works:**
- `night-mode-on.sh` creates `.claude/hooks/state/night_mode.flag`
- `flash-cards-inject.sh` (UserPromptSubmit hook) detects the flag and injects autonomous directives into every prompt
- `pvqe-p-stop.py` (Stop hook) bypasses PVQE-P evidence requirements
- When the flag is removed, normal interactive mode resumes

---

## Autonomous Rules (injected by flash-cards-inject.sh)

| Rule | Detail |
|------|--------|
| `AskUserQuestion` | **FORBIDDEN** — pick safe option and continue |
| `EnterPlanMode` | **FORBIDDEN** — plan internally, execute immediately |
| Confirmation text | **FORBIDDEN** — no "shall I proceed?" |
| On error | Log it, skip task, continue to next |
| Max retries | 3 per task; after 3 failures → log + skip |

---

## Permitted Work During Night Mode

### LEVEL 1 (auto-execute)
- Article generation via NEO-ONE/TWO (already autonomous on VPS)
- Prediction verification (`prediction_auto_verifier.py`)
- Draft rescue (`batch publish` of stuck drafts)
- Health monitoring and Telegram alerts
- Observer log writes

### LEVEL 2 (queue only — do NOT execute)
- New cron job additions
- Script parameter changes
- API key rotation
- Infrastructure changes

### Forbidden During Night Mode
- Destructive operations (delete, rm -rf, DROP TABLE)
- git push to remote
- systemd service definition changes
- Changes to `.claude/hooks/` files
- Changes to `NORTH_STAR.md` or `CLAUDE.md`

---

## Night Mode Stack (execution flow)

```
User exits → bash scripts/night-mode-on.sh → creates night_mode.flag
                            ↓
Each new conversation turn:
  flash-cards-inject.sh (UserPromptSubmit hook)
    → detects night_mode.flag
    → injects autonomous directives into Claude context
                            ↓
  Claude executes work autonomously
    → no AskUserQuestion, no EnterPlanMode
    → errors logged to /opt/shared/observer_log/
                            ↓
  pvqe-p-stop.py (Stop hook)
    → skips PVQE-P evidence check when night_mode.flag present
                            ↓
User returns → bash scripts/night-mode-off.sh → removes night_mode.flag
  → normal interactive mode resumes
```

---

## Observer Log

Night Mode activity is logged to `/opt/shared/observer_log/`:
- **observer_writer.py** — writes structured JSON events
- **observer_archiver.py** — weekly archival (cron: Sunday 01:00 UTC)
- Format: `YYYY-MM-DD_HH-MM-SS_<event_type>.json`

Check overnight activity:
```bash
ssh root@163.44.124.123 "ls -lt /opt/shared/observer_log/ | head -20"
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Unintended destructive action | LEVEL 3 operations are hard-blocked by hooks |
| Infinite retry loop | Max 3 retries per task, then skip |
| Runaway API costs | Claude Max ($200/month flat rate, no per-token cost) |
| VPS state divergence | SHARED_STATE.md auto-updated every 30 minutes |
| Night Mode stuck ON | Check and remove `.claude/hooks/state/night_mode.flag` manually |

---

## Emergency: Disable Night Mode Manually

```bash
# Option 1: use script
bash scripts/night-mode-off.sh

# Option 2: manual flag removal
rm -f .claude/hooks/state/night_mode.flag
echo "Night mode disabled"
```
