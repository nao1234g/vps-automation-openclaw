#!/usr/bin/env python3
"""Consolidate mission-control profile scheduling into a single minute-level router."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from mission_contract import assert_mission_handshake

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_PATH = Path("/opt/shared/reports/ecosystem_scheduler/state.json")
MISSION_HANDSHAKE = assert_mission_handshake(
    "ecosystem_schedule_router",
    "route ecosystem mission-control profiles through a single governed schedule",
)


def due_profiles(now: datetime) -> list[str]:
    minute = now.minute
    hour = now.hour
    weekday = now.weekday()
    profiles: list[str] = []
    if minute == 7:
        profiles.append("hourly-core")
    if minute == 19 and hour % 6 == 0:
        profiles.append("six-hour-site")
    if minute == 31 and hour == 4:
        profiles.append("daily-quality")
    if minute == 43 and hour == 5:
        profiles.append("daily-integrity")
    if minute == 49 and hour == 6:
        profiles.append("daily-full-crawl")
    if minute == 17 and hour == 6 and weekday == 0:
        profiles.append("weekly-governance")
    return profiles


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


def run_due_profiles(now: datetime, dry_run: bool = False) -> dict[str, object]:
    state = load_state()
    slot = int(now.replace(second=0, microsecond=0).timestamp())
    due = due_profiles(now)
    executed: list[dict[str, object]] = []
    for profile in due:
        if state.get(profile) == slot:
            continue
        command = [sys.executable, str(SCRIPT_DIR / "ecosystem_mission_control.py"), "--profile", profile]
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
        executed.append({"profile": profile, "returncode": rc, "output": output[:1000]})
        state[profile] = slot
    if not dry_run:
        save_state(state)
    return {
        "generated_at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "due_profiles": due,
        "executed": executed,
        "mission_contract_version": MISSION_HANDSHAKE["mission_contract_version"],
        "mission_contract_hash": MISSION_HANDSHAKE["mission_contract_hash"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run due ecosystem mission-control profiles from one scheduler.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = run_due_profiles(datetime.now(timezone.utc), dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

