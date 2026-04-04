#!/usr/bin/env python3
"""Replace redundant monitor crons with consolidated ecosystem mission-control jobs."""

from __future__ import annotations

import subprocess
import sys


SUSPEND_PATTERNS = (
    "ui_guard.py",
    "ghost_integrity_check.py",
    "site_link_crawler.py",
    "site_playwright_check.py",
    "post_publish_auditor.py",
    "qa_sentinel.py",
    "zero-article-alert.py",
    "self-healer.py",
    "article-count-monitor.py",
    "en-translation-monitor.py",
    "content-quality-monitor.py",
    "oracle-monitor.py",
    "pipeline-monitor.py",
    "vps-error-capture.py",
    "infra-monitor.py",
    "service_watchdog.py",
    "proactive_scanner.py",
    "tag_audit_weekly.py",
    "prediction_db_guardian.py",
    "prediction_taxonomy_validator.py",
    "link_integrity_checker.py",
    "jp_en_pairing_checker.py",
    "agent_consistency_validator.py",
    "ja_en_pairing_audit.py",
    "prediction_builder_monitor.py",
    "ghost_page_guardian.py",
    "repair-verifier.py",
    "prediction-update-checker.py",
)

MISSION_LINES = (
    "* * * * * /usr/bin/env python3 /opt/shared/scripts/ecosystem_schedule_router.py >> /opt/shared/logs/ecosystem_schedule_router.log 2>&1 # np-ecosystem-schedule-router",
)


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
        if any(marker in stripped for marker in (
            "np-mission-control-hourly",
            "np-mission-control-six-hour-site",
            "np-mission-control-daily-quality",
            "np-mission-control-daily-integrity",
            "np-mission-control-weekly-governance",
            "np-ecosystem-schedule-router",
        )):
            continue
        if not stripped.startswith("#") and any(pattern in stripped for pattern in SUSPEND_PATTERNS):
            updated.append("# SUSPENDED-MISSION-CONTROL: " + line)
            suspended += 1
            continue
        updated.append(line)

    updated.extend(MISSION_LINES)
    payload = "\n".join(updated).rstrip() + "\n"
    apply_proc = subprocess.run(["crontab", "-"], input=payload, text=True, capture_output=True, check=False)
    if apply_proc.returncode != 0:
        sys.stderr.write((apply_proc.stderr or apply_proc.stdout or "failed to update crontab").strip() + "\n")
        return apply_proc.returncode or 1
    print(f"OK: suspended {suspended} redundant monitor crons and installed {len(MISSION_LINES)} mission-control jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
