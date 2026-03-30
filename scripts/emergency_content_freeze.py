#!/usr/bin/env python3
"""Suspend high-risk content generation/distribution cron jobs."""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import shutil

PATTERNS = (
    "nowpattern-deep-pattern-generate.py",
    "breaking-news-watcher.py",
    "neo_queue_dispatcher.py",
    "ghost_to_tweet_queue.py",
    "auto_tweet.py",
    "rss-post-quote-rt.py",
    "x_swarm_dispatcher.py",
)

PROCESS_PATTERNS = (
    "nowpattern-deep-pattern-generate.py",
    "breaking-news-watcher.py",
    "neo_queue_dispatcher.py",
    "ghost_to_tweet_queue.py",
    "auto_tweet.py",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if shutil.which("crontab") is None:
        print("ERROR: crontab command not found; run this on the Linux VPS.")
        return 1

    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=True).stdout.splitlines()
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup = f"/opt/shared/reports/crontab-backup-{stamp}.txt"
    if not args.dry_run:
        subprocess.run(["bash", "-lc", f"crontab -l > {backup}"], check=True)

    updated: list[str] = []
    suspended = 0
    for line in current:
        if any(p in line for p in PATTERNS) and not line.lstrip().startswith("#"):
            updated.append("# SUSPENDED-CONTENT-INTEGRITY: " + line)
            suspended += 1
        else:
            updated.append(line)

    payload = "\n".join(updated) + "\n"
    if not args.dry_run:
        subprocess.run(["crontab", "-"], input=payload, text=True, check=True)
        for pattern in PROCESS_PATTERNS:
            subprocess.run(["pkill", "-f", pattern], check=False)

    print(f"backup={backup}")
    print(f"suspended={suspended}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
