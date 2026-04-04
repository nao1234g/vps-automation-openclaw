#!/usr/bin/env python3
"""Run exhaustive external crawls across public pages, article anchors, and source links."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def run_check(name: str, command: list[str]) -> dict[str, object]:
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
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
        "command": command,
        "output": output,
        "json": parsed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exhaustive external synthetic-user crawls.")
    parser.add_argument("--base-url", default="https://nowpattern.com")
    parser.add_argument("--json-out")
    args = parser.parse_args()

    commands = [
        (
            "site_link_crawler",
            [
                sys.executable,
                str(SCRIPT_DIR / "site_link_crawler.py"),
                "--base-url",
                args.base_url,
                "--discover-limit",
                "2000",
                "--full-scan",
            ],
        ),
        (
            "stateful_user_journey",
            [
                sys.executable,
                str(SCRIPT_DIR / "stateful_user_journey_audit.py"),
                "--base-url",
                args.base_url,
            ],
        ),
        (
            "article_anchor_integrity",
            [
                sys.executable,
                str(SCRIPT_DIR / "article_anchor_integrity_audit.py"),
                "--base-url",
                args.base_url,
                "--discover-limit",
                "2000",
                "--full-scan",
            ],
        ),
        (
            "site_article_source",
            [
                sys.executable,
                str(SCRIPT_DIR / "site_article_source_audit.py"),
                "--base-url",
                args.base_url,
                "--discover-limit",
                "2000",
                "--full-scan",
            ],
        ),
    ]

    results = [run_check(name, command) for name, command in commands]
    failed = [item for item in results if not item["ok"]]
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_epoch": int(time.time()),
        "base_url": args.base_url.rstrip("/"),
        "total": len(results),
        "failed": len(failed),
        "results": results,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
