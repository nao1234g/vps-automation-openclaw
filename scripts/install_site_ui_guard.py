#!/usr/bin/env python3
"""Install recurring UI self-heal and smoke-audit cron jobs on the VPS."""

from __future__ import annotations

import subprocess
from pathlib import Path


CRON_LINES = [
    "* * * * * /usr/bin/env python3 /opt/shared/scripts/site_guard_scheduler.py >> /opt/shared/logs/site_guard_scheduler.log 2>&1 # np-site-guard-scheduler",
]

CRON_TAGS = [
    "# np-ui-guard-lang",
    "# np-ui-guard-en-routes",
    "# np-ui-guard-ghost-routes",
    "# np-ui-guard-preview-routes",
    "# np-ui-guard-source-links",
    "# np-ui-guard-content-integrity",
    "# np-ui-guard-theme-en-urls",
    "# np-ui-guard-ghost-authors",
    "# np-ui-guard-draft-links",
    "# np-ui-smoke-audit",
    "# np-ecosystem-governance",
    "# np-site-guard-scheduler",
]


def current_crontab() -> list[str]:
    result = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def filter_managed_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if not any(tag in line for tag in CRON_TAGS)]


def install_crontab(lines: list[str]) -> None:
    payload = "\n".join(lines).rstrip() + "\n"
    result = subprocess.run(
        ["crontab", "-"],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "failed to install crontab")


def main() -> int:
    Path("/opt/shared/logs").mkdir(parents=True, exist_ok=True)
    Path("/opt/shared/reports/site_ui_smoke").mkdir(parents=True, exist_ok=True)
    Path("/opt/shared/reports/site_guard").mkdir(parents=True, exist_ok=True)
    Path("/opt/shared/locks").mkdir(parents=True, exist_ok=True)

    lines = current_crontab()
    filtered = filter_managed_lines(lines)
    updated = filtered + CRON_LINES
    install_crontab(updated)

    print("OK: installed site UI guard cron jobs")
    for line in CRON_LINES:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
