#!/usr/bin/env python3
"""Consolidate non-publishing ecosystem monitors into a smaller governed scheduler surface."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

PROFILES: dict[str, list[list[str]]] = {
    "hourly-core": [
        ["python3", str(SCRIPT_DIR / "ghost_integrity_check.py")],
        ["python3", str(SCRIPT_DIR / "zero-article-alert.py")],
        ["python3", str(SCRIPT_DIR / "post_publish_auditor.py")],
        ["python3", str(SCRIPT_DIR / "service_watchdog.py")],
        ["python3", str(SCRIPT_DIR / "vps-error-capture.py")],
        ["python3", str(SCRIPT_DIR / "infra-monitor.py")],
        ["python3", str(SCRIPT_DIR / "repair-verifier.py")],
    ],
    "six-hour-site": [
        ["python3", str(SCRIPT_DIR / "site_link_crawler.py")],
        ["python3", str(SCRIPT_DIR / "site_playwright_check.py")],
        ["python3", str(SCRIPT_DIR / "prediction_db_guardian.py")],
        ["python3", str(SCRIPT_DIR / "ghost_page_guardian.py")],
        ["python3", str(SCRIPT_DIR / "prediction_builder_monitor.py")],
        ["python3", str(SCRIPT_DIR / "prediction-update-checker.py")],
    ],
    "daily-quality": [
        ["python3", str(SCRIPT_DIR / "article-count-monitor.py")],
        ["python3", str(SCRIPT_DIR / "en-translation-monitor.py")],
        ["python3", str(SCRIPT_DIR / "content-quality-monitor.py")],
        ["python3", str(SCRIPT_DIR / "oracle-monitor.py")],
        ["python3", str(SCRIPT_DIR / "pipeline-monitor.py")],
        ["python3", str(SCRIPT_DIR / "qa_sentinel.py")],
    ],
    "daily-integrity": [
        ["python3", str(SCRIPT_DIR / "link_integrity_checker.py"), "--notify"],
        ["python3", str(SCRIPT_DIR / "jp_en_pairing_checker.py"), "--notify"],
        ["python3", str(SCRIPT_DIR / "agent_consistency_validator.py"), "--notify"],
        ["python3", str(SCRIPT_DIR / "ja_en_pairing_audit.py")],
    ],
    "daily-full-crawl": [
        [
            "python3",
            str(SCRIPT_DIR / "synthetic_user_crawler.py"),
            "--base-url",
            "https://nowpattern.com",
            "--json-out",
            "/opt/shared/reports/synthetic_user_crawler/latest.json",
        ],
    ],
    "weekly-governance": [
        ["python3", str(SCRIPT_DIR / "proactive_scanner.py")],
        ["python3", str(SCRIPT_DIR / "tag_audit_weekly.py")],
        ["python3", str(SCRIPT_DIR / "prediction_taxonomy_validator.py"), "--notify"],
    ],
}


def run_profile(profile: str) -> dict[str, object]:
    commands = PROFILES[profile]
    results: list[dict[str, object]] = []
    for command in commands:
        proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        output = "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part).strip()
        results.append(
            {
                "command": command,
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "output": output[:1000],
            }
        )
    failed = [item for item in results if not item["ok"]]
    return {
        "profile": profile,
        "generated_at_epoch": int(time.time()),
        "total": len(results),
        "failed": len(failed),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a consolidated ecosystem monitor profile.")
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES.keys()))
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    report = run_profile(args.profile)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
