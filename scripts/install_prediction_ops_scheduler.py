#!/usr/bin/env python3
"""Replace redundant prediction/polymarket cron lines with a consolidated scheduler."""

from __future__ import annotations

import subprocess
import sys


SUSPEND_PATTERNS = (
    "daily-learning.py --run 0",
    "daily-learning.py --run 1",
    "daily-learning.py --run 2",
    "daily-learning.py --run 3",
    "polymarket_monitor.py",
    "polymarket_delta.py",
    "prediction_page_builder.py --force --update",
    "prediction_page_builder.py --force --lang en --update",
    "inject_live_panel.py",
    "prediction_auto_verifier.py",
    "prediction_resolver.py",
    "sync_stats.py",
    "apply_polymarket_matches.py",
    "prediction_cron_update.py",
    "prediction_verifier.py --auto-judge",
    "market_history_crawler.py",
)

SCHEDULER_LINE = "* * * * * /usr/bin/env python3 /opt/shared/scripts/prediction_ops_scheduler.py >> /opt/shared/logs/prediction_ops_scheduler.log 2>&1 # np-prediction-ops-scheduler"


def main() -> int:
    proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    lines = proc.stdout.splitlines() if proc.returncode == 0 else []
    updated: list[str] = []
    suspended = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            updated.append(line)
            continue
        if "np-prediction-ops-scheduler" in stripped:
            continue
        if not stripped.startswith("#") and any(pattern in stripped for pattern in SUSPEND_PATTERNS):
            updated.append("# SUSPENDED-PREDICTION-OPS: " + line)
            suspended += 1
            continue
        updated.append(line)
    updated.append(SCHEDULER_LINE)
    payload = "\n".join(updated).rstrip() + "\n"
    apply_proc = subprocess.run(["crontab", "-"], input=payload, text=True, capture_output=True, check=False)
    if apply_proc.returncode != 0:
        sys.stderr.write((apply_proc.stderr or apply_proc.stdout or "failed to update crontab").strip() + "\n")
        return apply_proc.returncode or 1
    print(f"OK: suspended {suspended} prediction/polymarket cron lines and installed scheduler")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
