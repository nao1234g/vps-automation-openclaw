#!/usr/bin/env python3
"""Audit VPS cron policy for unsafe autonomous content/distribution jobs."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from ghost_write_surface_audit import ACTIVE_GOVERNED_CLASSES, CLASSIFIED_SURFACES


FORBIDDEN_ACTIVE_PATTERNS = {
    "a1-bulk-en-translator.py": "autonomous translation publishing must remain frozen until it is routed through the shared release governor",
    "nowpattern-deep-pattern-generate.py": "autonomous article generation must remain frozen behind human-governed lanes",
    "breaking-news-watcher.py": "autonomous breaking-news publication must remain frozen behind release governor review",
    "neo_queue_dispatcher.py": "queue dispatcher must not autonomously reactivate content generation",
    "news-analyst-pipeline.py": "legacy news analyst publishing must not run unattended",
    "nowpattern-ghost-post.py": "direct ghost posting must not run unattended",
    "publish_predictions_articles.py": "prediction article publication must not run unattended",
    "post-notes.py": "external notes distribution must not run unattended outside the shared release governor",
    "ghost_to_tweet_queue.py": "distribution queueing must not run unattended",
    "auto_tweet.py": "external distribution must not run unattended",
    "x_swarm_dispatcher.py": "swarm distribution must not run unattended",
    "rss-post-quote-rt.py": "auto repost must not run unattended",
}

WARNING_THRESHOLDS = {
    "active_total_warn": 120,
    "active_total_fail": 180,
}

SCRIPT_PATH_RE = re.compile(r"/opt/shared/scripts/([A-Za-z0-9_.-]+\.py)")


def current_crontab_lines(crontab_file: str | None = None) -> list[str]:
    if crontab_file:
        return [
            line for line in Path(crontab_file).read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        ]
    if not shutil.which("crontab"):
        raise RuntimeError("crontab command not available; use --crontab-file for offline auditing")
    proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line.strip()]


def run_audit(crontab_file: str | None = None) -> dict[str, object]:
    lines = current_crontab_lines(crontab_file)
    active = [line for line in lines if not line.lstrip().startswith("#")]
    failures: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    active_write_surfaces: list[dict[str, object]] = []

    for pattern, reason in FORBIDDEN_ACTIVE_PATTERNS.items():
        matched = [line for line in active if pattern in line]
        if matched:
            failures.append(
                {
                    "pattern": pattern,
                    "reason": reason,
                    "matches": matched,
                }
            )

    for line in active:
        match = SCRIPT_PATH_RE.search(line)
        if not match:
            continue
        rel_path = f"scripts/{match.group(1)}"
        klass = CLASSIFIED_SURFACES.get(rel_path)
        if not klass:
            continue
        if klass not in ACTIVE_GOVERNED_CLASSES:
            failures.append(
                {
                    "pattern": rel_path,
                    "reason": f"active cron uses non-governed class '{klass}'",
                    "matches": [line],
                }
            )
            continue
        active_write_surfaces.append({"path": rel_path, "class": klass})

    active_total = len(active)
    if active_total > WARNING_THRESHOLDS["active_total_fail"]:
        failures.append(
            {
                "pattern": "active_total",
                "reason": f"active cron count too high ({active_total} > {WARNING_THRESHOLDS['active_total_fail']})",
                "matches": [],
            }
        )
    elif active_total > WARNING_THRESHOLDS["active_total_warn"]:
        warnings.append(
            {
                "warning": f"active cron count high ({active_total} > {WARNING_THRESHOLDS['active_total_warn']})"
            }
        )

    return {
        "active_total": active_total,
        "forbidden_patterns_checked": len(FORBIDDEN_ACTIVE_PATTERNS),
        "active_governed_write_surfaces": active_write_surfaces,
        "failures": failures,
        "warnings": warnings,
        "active_subset": active[:80],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit cron governance for unsafe autonomous content jobs.")
    parser.add_argument("--crontab-file", help="Audit a saved crontab file instead of the live crontab")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    report = run_audit(args.crontab_file)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
