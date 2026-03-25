# /night-mode skill

Toggle Night Mode (autonomous execution mode) on or off.

## Usage
- `/night-mode on`  — Enable autonomous mode before stepping away
- `/night-mode off` — Disable after returning

## Steps for ON

1. Check if already enabled:
   ```bash
   test -f "$CLAUDE_PROJECT_DIR/.claude/hooks/state/night_mode.flag" && echo "ALREADY ON" || echo "OFF"
   ```

2. Enable:
   ```bash
   touch "$CLAUDE_PROJECT_DIR/.claude/hooks/state/night_mode.flag"
   echo "Night Mode ENABLED: $(date)" >> "$CLAUDE_PROJECT_DIR/.claude/hooks/state/night_mode.log"
   ```

3. Confirm active hooks/behavior with the user:
   - AskUserQuestion → disabled (safe default chosen)
   - EnterPlanMode → disabled (plan immediately)
   - Confirmations → disabled (proceed autonomously)

## Steps for OFF

1. Remove flag:
   ```bash
   rm -f "$CLAUDE_PROJECT_DIR/.claude/hooks/state/night_mode.flag"
   echo "Night Mode DISABLED: $(date)" >> "$CLAUDE_PROJECT_DIR/.claude/hooks/state/night_mode.log"
   ```

2. Report what was done during Night Mode (last 10 entries from task ledger)

## Safety Rules (enforced even in Night Mode)
- NEVER git push
- NEVER delete production data
- NEVER restart services without verification
- NEVER spend money
