# NAOTO OS Project Anchor

This repository is governed by `NAOTO OS`.
`Nowpattern` is a product running under `NAOTO OS`; it is not the OS itself.

## Non-negotiables

- Truth-first always.
- `source 0`, broken sources, unsupported frontier claims: never acceptable.
- Public release and distribution must respect the release governor path.
- Do not claim completion without evidence in files.

## Sidecar Contract

If you are working as a Claude Code sidecar worker, you must keep these files up to date in `reports/claude_sidecar/`:

- `session_status.json`
- `heartbeat.json`
- `task_result_v*.json`
- `task_result_v*.md`
- `resume_prompt.txt`

Before stopping, you must either:

- mark the scope `completed`, or
- mark the scope `blocked` with `blocking_reason` and `next_exact_step`

Silent stops are not allowed.

## Read Order

1. `.claude/rules/NORTH_STAR.md`
2. `scripts/mission_contract.py`
3. `scripts/agent_bootstrap_context.py`
4. `reports/content_release_snapshot.json`
5. `reports/one_pass_completion_gate.json`
6. `data/mistake_registry.json`

## Resume Discipline

- Prefer resuming the same named session with `claude --continue` or `claude --resume`.
- If you stop mid-scope, write the next exact step into `reports/claude_sidecar/resume_prompt.txt`.
- The UI chat is not the system of record; the files above are.
