#!/usr/bin/env python3
"""Run the core governance audits that keep the agent ecosystem centrally controlled."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import shutil
from pathlib import Path

from mission_contract import assert_mission_handshake

SCRIPT_DIR = Path(__file__).resolve().parent
MISSION_HANDSHAKE = assert_mission_handshake(
    "ecosystem_governance_audit",
    "audit that all active ecosystem controls remain aligned with the shared founder mission contract",
)

BASE_AUDITS = [
    ("mission_contract", [sys.executable, str(SCRIPT_DIR / "mission_contract_audit.py")]),
    ("lexicon_contract", [sys.executable, str(SCRIPT_DIR / "lexicon_contract_audit.py")]),
    ("publish_path_guard", [sys.executable, str(SCRIPT_DIR / "publish_path_guard_audit.py")]),
    ("ghost_write_surface", [sys.executable, str(SCRIPT_DIR / "ghost_write_surface_audit.py")]),
    ("release_guard_canary", [sys.executable, str(SCRIPT_DIR / "release_guard_canary.py")]),
    (
        "article_anchor_integrity",
        [sys.executable, str(SCRIPT_DIR / "article_anchor_integrity_audit.py"), "--base-url", "https://nowpattern.com"],
    ),
    (
        "site_dev_pages",
        [sys.executable, str(SCRIPT_DIR / "site_dev_page_audit.py"), "--base-url", "https://nowpattern.com"],
    ),
    (
        "site_article_source",
        [
            sys.executable,
            str(SCRIPT_DIR / "site_article_source_audit.py"),
            "--base-url",
            "https://nowpattern.com",
            "--per-seed",
            "1",
        ],
    ),
]


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_audit(name: str, command: list[str]) -> dict[str, object]:
    proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part).strip()
    parsed = None
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except Exception:
            parsed = None
    return {
        "name": name,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "output": output,
        "json": parsed,
    }


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Run the core ecosystem governance audits.")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    audits = list(BASE_AUDITS)
    if shutil.which("crontab"):
        audits.append(("cron_governance", [sys.executable, str(SCRIPT_DIR / "cron_governance_audit.py")]))

    results = [run_audit(name, command) for name, command in audits]
    report = {
        "total": len(results),
        "failed": sum(1 for item in results if not item["ok"]),
        "results": results,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
