#!/usr/bin/env python3
"""Install recurring UI self-heal and smoke-audit cron jobs on the VPS."""

from __future__ import annotations

import subprocess
from pathlib import Path


CRON_LINES = [
    "7,37 * * * * /usr/bin/env python3 /opt/shared/scripts/site_guard_runner.py --job lang >> /opt/shared/logs/fix_global_language_switcher.log 2>&1 # np-ui-guard-lang",
    "13,43 * * * * /usr/bin/env python3 /opt/shared/scripts/site_guard_runner.py --job en-routes >> /opt/shared/logs/install_en_article_route_guard.log 2>&1 # np-ui-guard-en-routes",
    "2,17,32,47 * * * * /usr/bin/env python3 /opt/shared/scripts/site_guard_runner.py --job ghost-routes >> /opt/shared/logs/check_ghost_article_routes.log 2>&1 # np-ui-guard-ghost-routes",
    "22 * * * * /usr/bin/env python3 /opt/shared/scripts/site_guard_runner.py --job preview-routes >> /opt/shared/logs/install_uuid_preview_route_guard.log 2>&1 # np-ui-guard-preview-routes",
    "28 * * * * /usr/bin/env python3 /opt/shared/scripts/site_guard_runner.py --job source-links >> /opt/shared/logs/fix_ghost_content_links.log 2>&1 # np-ui-guard-source-links",
    "52 * * * * /usr/bin/env python3 /opt/shared/scripts/site_guard_runner.py --job smoke >> /opt/shared/logs/site_ui_smoke_audit.log 2>&1 # np-ui-smoke-audit",
]

CRON_TAGS = [
    "# np-ui-guard-lang",
    "# np-ui-guard-en-routes",
    "# np-ui-guard-ghost-routes",
    "# np-ui-guard-preview-routes",
    "# np-ui-guard-source-links",
    "# np-ui-smoke-audit",
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
    filtered = [line for line in lines if not any(tag in line for tag in CRON_TAGS)]
    updated = filtered + CRON_LINES
    install_crontab(updated)

    print("OK: installed site UI guard cron jobs")
    for line in CRON_LINES:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
