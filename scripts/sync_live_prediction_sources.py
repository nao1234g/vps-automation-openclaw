#!/usr/bin/env python3
"""Pull live prediction platform source files from the VPS into this repo."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = os.environ.get("NOWPATTERN_VPS_HOST", "root@163.44.124.123")
TARGETS = [
    {
        "name": "prediction_db",
        "remote": "/opt/shared/scripts/prediction_db.json",
        "local": REPO_ROOT / "scripts" / "prediction_db.json",
    },
    {
        "name": "prediction_page_builder",
        "remote": "/opt/shared/scripts/prediction_page_builder.py",
        "local": REPO_ROOT / "scripts" / "prediction_page_builder.py",
    },
    {
        "name": "reader_prediction_api",
        "remote": "/opt/shared/scripts/reader_prediction_api.py",
        "local": REPO_ROOT / "scripts" / "reader_prediction_api.py",
    },
    {
        "name": "refresh_prediction_db_meta",
        "remote": "/opt/shared/scripts/refresh_prediction_db_meta.py",
        "local": REPO_ROOT / "scripts" / "refresh_prediction_db_meta.py",
    },
    {
        "name": "prediction_state_utils",
        "remote": "/opt/shared/scripts/prediction_state_utils.py",
        "local": REPO_ROOT / "scripts" / "prediction_state_utils.py",
    },
    {
        "name": "prediction_state_integrity_gate",
        "remote": "/opt/shared/scripts/prediction_state_integrity_gate.py",
        "local": REPO_ROOT / "scripts" / "prediction_state_integrity_gate.py",
    },
    {
        "name": "playwright_e2e_predictions",
        "remote": "/opt/shared/scripts/playwright_e2e_predictions.py",
        "local": REPO_ROOT / "scripts" / "playwright_e2e_predictions.py",
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


def fetch_remote_bytes(ssh_bin: str, host: str, remote_path: str) -> bytes:
    remote_cmd = (
        "python3 -c \"import pathlib,sys; "
        "sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())\" "
        + "'" + remote_path.replace("'", "'\"'\"'") + "'"
    )
    result = subprocess.run([ssh_bin, host, remote_cmd], capture_output=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or f"failed to fetch {remote_path}")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync live prediction platform source files from VPS.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="VPS ssh target, e.g. root@163.44.124.123")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced without writing files")
    parser.add_argument(
        "--target",
        action="append",
        choices=[target["name"] for target in TARGETS],
        help="Sync only the named target. Can be passed multiple times.",
    )
    args = parser.parse_args()

    ssh_bin = choose_ssh_bin()
    selected = set(args.target or [])
    targets = [target for target in TARGETS if not selected or target["name"] in selected]
    for target in targets:
        remote_path = target["remote"]
        local_path = target["local"]
        if args.dry_run:
            print(f"WOULD SYNC {target['name']}: {remote_path} -> {local_path}")
            continue
        data = fetch_remote_bytes(ssh_bin, args.host, remote_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
        print(f"SYNCED {target['name']}: {remote_path} -> {local_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
