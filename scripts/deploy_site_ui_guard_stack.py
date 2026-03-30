#!/usr/bin/env python3
"""Push and install the site UI hardening stack on the VPS."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = os.environ.get("NOWPATTERN_VPS_HOST", "root@163.44.124.123")
TARGETS = [
    "prediction_page_builder",
    "playwright_e2e_predictions",
    "fix_global_language_switcher",
    "fix_ghost_content_links",
    "live_site_availability_check",
    "check_ghost_article_routes",
    "site_guard_runner",
    "site_ui_smoke_audit",
    "install_site_ui_guard",
    "install_en_article_route_guard",
    "install_uuid_preview_route_guard",
    "check_live_repo_drift",
]


def choose_ssh_bin() -> str:
    override = os.environ.get("NP_SSH_BIN")
    if override and Path(override).exists():
        return override

    windows_builtin = Path(r"C:\Windows\System32\OpenSSH\ssh.exe")
    if windows_builtin.exists():
        return str(windows_builtin)

    candidate = shutil.which("ssh")
    if candidate and ".sbx-denybin" not in candidate.lower():
        return candidate

    raise FileNotFoundError("No usable ssh binary found. Set NP_SSH_BIN if needed.")


def run_checked(command: list[str], workdir: Path) -> None:
    result = subprocess.run(command, cwd=str(workdir), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"command failed: {command}")
    if result.stdout.strip():
        print(result.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy site UI guard/source-fix stack to VPS.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="VPS ssh target, e.g. root@163.44.124.123")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without running them")
    args = parser.parse_args()

    push_cmd = ["python", "scripts/push_prediction_platform_sources.py", "--host", args.host]
    for target in TARGETS:
        push_cmd.extend(["--target", target])

    remote_cmd = " && ".join(
        [
            "python3 /opt/shared/scripts/fix_global_language_switcher.py",
            "python3 /opt/shared/scripts/install_en_article_route_guard.py --quiet",
            "python3 /opt/shared/scripts/install_uuid_preview_route_guard.py --quiet",
            "python3 /opt/shared/scripts/fix_ghost_content_links.py --quiet",
            "python3 /opt/shared/scripts/check_ghost_article_routes.py --repair --quiet",
            "python3 /opt/shared/scripts/install_site_ui_guard.py",
            "python3 /opt/shared/scripts/check_live_repo_drift.py --host local",
        ]
    )

    if args.dry_run:
        print("WOULD RUN:")
        print("  " + " ".join(shlex.quote(part) for part in push_cmd))
        print(f"  ssh {args.host} {shlex.quote(remote_cmd)}")
        return 0

    run_checked(push_cmd, REPO_ROOT)
    ssh_bin = choose_ssh_bin()
    run_checked([ssh_bin, args.host, remote_cmd], REPO_ROOT)
    print("OK: deployed site UI guard stack")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
