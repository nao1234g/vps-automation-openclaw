#!/usr/bin/env python3
"""Push local prediction platform source files from this repo to the VPS."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = os.environ.get("NOWPATTERN_VPS_HOST", "root@163.44.124.123")
TARGETS = [
    {
        "name": "prediction_db",
        "local": REPO_ROOT / "scripts" / "prediction_db.json",
        "remote": "/opt/shared/scripts/prediction_db.json",
    },
    {
        "name": "prediction_page_builder",
        "local": REPO_ROOT / "scripts" / "prediction_page_builder.py",
        "remote": "/opt/shared/scripts/prediction_page_builder.py",
    },
    {
        "name": "reader_prediction_api",
        "local": REPO_ROOT / "scripts" / "reader_prediction_api.py",
        "remote": "/opt/shared/scripts/reader_prediction_api.py",
    },
    {
        "name": "refresh_prediction_db_meta",
        "local": REPO_ROOT / "scripts" / "refresh_prediction_db_meta.py",
        "remote": "/opt/shared/scripts/refresh_prediction_db_meta.py",
    },
    {
        "name": "prediction_state_utils",
        "local": REPO_ROOT / "scripts" / "prediction_state_utils.py",
        "remote": "/opt/shared/scripts/prediction_state_utils.py",
    },
    {
        "name": "prediction_state_integrity_gate",
        "local": REPO_ROOT / "scripts" / "prediction_state_integrity_gate.py",
        "remote": "/opt/shared/scripts/prediction_state_integrity_gate.py",
    },
    {
        "name": "playwright_e2e_predictions",
        "local": REPO_ROOT / "scripts" / "playwright_e2e_predictions.py",
        "remote": "/opt/shared/scripts/playwright_e2e_predictions.py",
    },
    {
        "name": "fix_global_language_switcher",
        "local": REPO_ROOT / "scripts" / "fix_global_language_switcher.py",
        "remote": "/opt/shared/scripts/fix_global_language_switcher.py",
    },
    {
        "name": "fix_ghost_content_links",
        "local": REPO_ROOT / "scripts" / "fix_ghost_content_links.py",
        "remote": "/opt/shared/scripts/fix_ghost_content_links.py",
    },
    {
        "name": "live_site_availability_check",
        "local": REPO_ROOT / "scripts" / "live_site_availability_check.py",
        "remote": "/opt/shared/scripts/live_site_availability_check.py",
    },
    {
        "name": "check_ghost_article_routes",
        "local": REPO_ROOT / "scripts" / "check_ghost_article_routes.py",
        "remote": "/opt/shared/scripts/check_ghost_article_routes.py",
    },
    {
        "name": "site_guard_runner",
        "local": REPO_ROOT / "scripts" / "site_guard_runner.py",
        "remote": "/opt/shared/scripts/site_guard_runner.py",
    },
    {
        "name": "site_ui_smoke_audit",
        "local": REPO_ROOT / "scripts" / "site_ui_smoke_audit.py",
        "remote": "/opt/shared/scripts/site_ui_smoke_audit.py",
    },
    {
        "name": "install_site_ui_guard",
        "local": REPO_ROOT / "scripts" / "install_site_ui_guard.py",
        "remote": "/opt/shared/scripts/install_site_ui_guard.py",
    },
    {
        "name": "install_en_article_route_guard",
        "local": REPO_ROOT / "scripts" / "install_en_article_route_guard.py",
        "remote": "/opt/shared/scripts/install_en_article_route_guard.py",
    },
    {
        "name": "install_uuid_preview_route_guard",
        "local": REPO_ROOT / "scripts" / "install_uuid_preview_route_guard.py",
        "remote": "/opt/shared/scripts/install_uuid_preview_route_guard.py",
    },
    {
        "name": "check_live_repo_drift",
        "local": REPO_ROOT / "scripts" / "check_live_repo_drift.py",
        "remote": "/opt/shared/scripts/check_live_repo_drift.py",
    },
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


def choose_scp_bin() -> str:
    override = os.environ.get("NP_SCP_BIN")
    if override and Path(override).exists():
        return override

    windows_builtin = Path(r"C:\Windows\System32\OpenSSH\scp.exe")
    if windows_builtin.exists():
        return str(windows_builtin)

    candidate = shutil.which("scp")
    if candidate and ".sbx-denybin" not in candidate.lower():
        return candidate

    raise FileNotFoundError("No usable scp binary found. Set NP_SCP_BIN if needed.")


def push_bytes(ssh_bin: str, host: str, remote_path: str, data: bytes) -> None:
    remote_cmd = (
        "python3 -c \"import pathlib,sys; "
        "path=pathlib.Path(sys.argv[1]); "
        "path.parent.mkdir(parents=True, exist_ok=True); "
        "path.write_bytes(sys.stdin.buffer.read())\" "
        + "'" + remote_path.replace("'", "'\"'\"'") + "'"
    )
    result = subprocess.run(
        [ssh_bin, host, remote_cmd],
        input=data,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or f"failed to push {remote_path}")


def push_with_scp(scp_bin: str, host: str, local_path: Path, remote_path: str) -> None:
    result = subprocess.run(
        [scp_bin, str(local_path), f"{host}:{remote_path}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or f"failed to push {local_path} via scp")


def main() -> int:
    parser = argparse.ArgumentParser(description="Push local prediction platform files to VPS.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="VPS ssh target, e.g. root@163.44.124.123")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be pushed without writing files")
    parser.add_argument(
        "--target",
        action="append",
        choices=[target["name"] for target in TARGETS],
        help="Push only the named target. Can be passed multiple times.",
    )
    args = parser.parse_args()

    ssh_bin = choose_ssh_bin()
    try:
        scp_bin = choose_scp_bin()
    except FileNotFoundError:
        scp_bin = ""
    selected = set(args.target or [])
    targets = [target for target in TARGETS if not selected or target["name"] in selected]

    for target in targets:
        local_path = target["local"]
        remote_path = target["remote"]
        if args.dry_run:
            print(f"WOULD PUSH {target['name']}: {local_path} -> {remote_path}")
            continue
        if scp_bin:
            push_with_scp(scp_bin, args.host, local_path, remote_path)
        else:
            data = local_path.read_bytes()
            push_bytes(ssh_bin, args.host, remote_path, data)
        print(f"PUSHED {target['name']}: {local_path} -> {remote_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
