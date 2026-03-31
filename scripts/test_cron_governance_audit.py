#!/usr/bin/env python3
"""Regression tests for cron governance policy."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import cron_governance_audit as cga  # noqa: E402


def _write_temp_crontab(lines: list[str]) -> str:
    with NamedTemporaryFile("w", encoding="utf-8", delete=False) as fh:
        fh.write("\n".join(lines) + "\n")
        return fh.name


def test_forbidden_pattern_is_blocked() -> None:
    path = _write_temp_crontab([
        "*/5 * * * * python3 /opt/shared/scripts/nowpattern-deep-pattern-generate.py",
    ])
    report = cga.run_audit(path)
    assert report["failures"], report
    assert any("nowpattern-deep-pattern-generate.py" in item["pattern"] for item in report["failures"]), report


def test_governed_active_surface_is_allowed() -> None:
    path = _write_temp_crontab([
        "0 6 * * * /usr/bin/python3 /opt/shared/scripts/article_schema_self_test.py",
    ])
    report = cga.run_audit(path)
    assert not report["failures"], report


def run() -> None:
    test_forbidden_pattern_is_blocked()
    test_governed_active_surface_is_allowed()
    print("PASS: cron governance audit regression checks")


if __name__ == "__main__":
    run()
