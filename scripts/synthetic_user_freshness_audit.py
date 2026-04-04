#!/usr/bin/env python3
"""Validate that the exhaustive synthetic-user crawl has run recently and passed."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


DEFAULT_REPORT = Path("/opt/shared/reports/synthetic_user_crawler/latest.json")


def run_audit(report_path: Path, max_age_seconds: int) -> dict[str, object]:
    failures: list[str] = []
    warnings: list[str] = []
    if not report_path.exists():
        failures.append("missing_full_crawl_report")
        return {
            "report_path": str(report_path),
            "max_age_seconds": max_age_seconds,
            "failures": failures,
            "warnings": warnings,
        }
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"unreadable_full_crawl_report:{exc}")
        return {
            "report_path": str(report_path),
            "max_age_seconds": max_age_seconds,
            "failures": failures,
            "warnings": warnings,
        }
    generated_at_epoch = int(report.get("generated_at_epoch") or 0)
    if not generated_at_epoch:
        failures.append("missing_generated_at_epoch")
    else:
        age_seconds = int(time.time()) - generated_at_epoch
        if age_seconds > max_age_seconds:
            failures.append(f"full_crawl_stale:{age_seconds}>{max_age_seconds}")
    if int(report.get("failed") or 0) > 0:
        failures.append(f"full_crawl_failed:{report.get('failed')}")
    if int(report.get("total") or 0) < 3:
        warnings.append(f"full_crawl_total_low:{report.get('total')}")
    return {
        "report_path": str(report_path),
        "max_age_seconds": max_age_seconds,
        "generated_at_epoch": generated_at_epoch,
        "failures": failures,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check freshness of the exhaustive synthetic-user crawl report.")
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT))
    parser.add_argument("--max-age-seconds", type=int, default=36 * 60 * 60)
    args = parser.parse_args()
    report = run_audit(Path(args.report_path), args.max_age_seconds)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
