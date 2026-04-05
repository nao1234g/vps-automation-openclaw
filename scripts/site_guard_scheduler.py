#!/usr/bin/env python3
"""Consolidate site guard cron jobs into a single minute-level scheduler."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from mission_contract import assert_mission_handshake

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_PATH = Path("/opt/shared/reports/site_guard/scheduler_state.json")
MISSION_HANDSHAKE = assert_mission_handshake(
    "site_guard_scheduler",
    "consolidate site self-heal and audit schedules under the shared founder mission contract",
)


def due_jobs(now: datetime) -> list[str]:
    minute = now.minute
    hour = now.hour
    jobs: list[str] = []
    if minute in {7, 37}:
        jobs.append("lang")
    if minute in {13, 43}:
        jobs.append("en-routes")
    if minute in {2, 17, 32, 47}:
        jobs.append("ghost-routes")
    if minute == 22:
        jobs.append("preview-routes")
    if minute == 28:
        jobs.append("source-links")
    if minute == 34:
        jobs.append("content-integrity")
    if minute == 52:
        jobs.append("smoke")
    if minute == 56 and hour % 6 == 0:
        jobs.append("prediction-maturity")
    if minute == 11 and hour % 2 == 0:
        jobs.append("governance")
    return jobs


def load_state() -> dict[str, int]:
    if not STATE_PATH.exists():
        return {}
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return {str(k): int(v) for k, v in raw.items()}
    except Exception:
        return {}


def save_state(state: dict[str, int]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_due_jobs(now: datetime, dry_run: bool = False) -> dict[str, object]:
    state = load_state()
    slot = int(now.replace(second=0, microsecond=0).timestamp())
    due = due_jobs(now)
    executed: list[dict[str, object]] = []
    for job in due:
        if state.get(job) == slot:
            continue
        command = [sys.executable, str(SCRIPT_DIR / "site_guard_runner.py"), "--job", job]
        if dry_run:
            rc = 0
            output = "dry-run"
        else:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            rc = proc.returncode
            output = "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part).strip()
        executed.append({"job": job, "returncode": rc, "output": output[:1000]})
        state[job] = slot
    if not dry_run:
        save_state(state)
    return {
        "generated_at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "due_jobs": due,
        "executed": executed,
        "mission_contract_version": MISSION_HANDSHAKE["mission_contract_version"],
        "mission_contract_hash": MISSION_HANDSHAKE["mission_contract_hash"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run due site guard jobs from a consolidated scheduler.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = run_due_jobs(datetime.now(timezone.utc), dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
