#!/usr/bin/env python3
"""Consolidate prediction and polymarket cron jobs into a governed scheduler."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from mission_contract import assert_mission_handshake

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_PATH = Path("/opt/shared/reports/prediction_ops/scheduler_state.json")
MISSION_HANDSHAKE = assert_mission_handshake(
    "prediction_ops_scheduler",
    "consolidate prediction and polymarket scheduled operations under the shared founder mission contract",
)


def _bash(command: str) -> list[str]:
    return ["bash", "-lc", command]


def due_commands(now: datetime) -> list[dict[str, object]]:
    hour = now.hour
    minute = now.minute
    due: list[dict[str, object]] = []

    if minute == 0 and hour == 0:
        due.extend(
            [
                {
                    "key": "prediction_auto_verifier",
                    "command": _bash(". /opt/cron-env.sh && /usr/bin/python3 /opt/shared/scripts/prediction_auto_verifier.py"),
                },
                {
                    "key": "polymarket_updater",
                    "command": _bash("/usr/bin/python3 /opt/shared/scripts/polymarket_updater.py"),
                },
                {
                    "key": "market_history_crawler",
                    "command": _bash(". /opt/cron-env.sh && /usr/bin/python3 /opt/shared/scripts/market_history_crawler.py"),
                },
            ]
        )
    if minute == 10 and hour == 0:
        due.append(
            {
                "key": "apply_polymarket_matches",
                "command": _bash("/usr/bin/python3 /opt/shared/scripts/apply_polymarket_matches.py"),
            }
        )
    if minute == 0 and hour == 1:
        due.append(
            {
                "key": "prediction_resolver",
                "command": _bash(". /opt/cron-env.sh && /usr/bin/python3 /opt/shared/scripts/prediction_resolver.py"),
            }
        )
    if minute == 10 and hour == 1:
        due.append(
            {
                "key": "sync_stats",
                "command": _bash("/usr/bin/python3 /opt/shared/scripts/sync_stats.py"),
            }
        )
    if minute == 55 and hour in {2, 8, 14, 20}:
        monitor_suffix = " --telegram" if hour == 20 else ""
        due.append(
            {
                "key": f"polymarket_monitor_{hour:02d}",
                "command": _bash(f"/usr/bin/python3 /opt/shared/scripts/polymarket_monitor.py{monitor_suffix}"),
            }
        )
    if minute == 57 and hour in {2, 8, 14, 20}:
        delta_suffix = " --telegram --neo" if hour == 20 else ""
        due.append(
            {
                "key": f"polymarket_delta_{hour:02d}",
                "command": _bash(f"/usr/bin/python3 /opt/shared/scripts/polymarket_delta.py{delta_suffix}"),
            }
        )
    if minute == 0 and hour in {3, 9, 15, 21}:
        run_id = {15: 0, 21: 1, 3: 2, 9: 3}[hour]
        due.extend(
            [
                {
                    "key": f"daily_learning_{run_id}",
                    "command": _bash(f". /opt/cron-env.sh && /usr/bin/python3 /opt/shared/scripts/daily-learning.py --run {run_id}"),
                },
                {
                    "key": f"inject_live_panel_{hour:02d}",
                    "command": _bash("/usr/bin/python3 /opt/shared/scripts/inject_live_panel.py"),
                },
            ]
        )
    if minute == 0 and hour == 6:
        due.append(
            {
                "key": "prediction_verifier",
                "command": _bash(". /opt/cron-env.sh && /usr/bin/python3 /opt/shared/scripts/prediction_verifier.py --auto-judge"),
            }
        )
    if minute == 0 and hour == 16:
        due.append(
            {
                "key": "prediction_cron_update",
                "command": _bash("/usr/bin/python3 /opt/shared/scripts/prediction_cron_update.py"),
            }
        )
    if minute == 0 and hour == 22:
        due.append(
            {
                "key": "prediction_page_builder_ja",
                "command": _bash("/usr/bin/python3 /opt/shared/scripts/prediction_page_builder.py --force --update"),
            }
        )
    if minute == 30 and hour == 22:
        due.append(
            {
                "key": "prediction_page_builder_en",
                "command": _bash("/usr/bin/python3 /opt/shared/scripts/prediction_page_builder.py --force --lang en --update"),
            }
        )
    return due


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


def run_due(now: datetime, dry_run: bool = False) -> dict[str, object]:
    slot = int(now.replace(second=0, microsecond=0).timestamp())
    state = load_state()
    due = due_commands(now)
    executed: list[dict[str, object]] = []

    for item in due:
        key = str(item["key"])
        if state.get(key) == slot:
            continue
        command = list(item["command"])
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
        executed.append({"key": key, "command": command, "returncode": rc, "output": output[:1000]})
        state[key] = slot

    if not dry_run:
        save_state(state)

    return {
        "generated_at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "due_keys": [str(item["key"]) for item in due],
        "executed": executed,
        "mission_contract_version": MISSION_HANDSHAKE["mission_contract_version"],
        "mission_contract_hash": MISSION_HANDSHAKE["mission_contract_hash"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run due prediction/polymarket jobs from a consolidated scheduler.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = run_due(datetime.now(timezone.utc), dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
