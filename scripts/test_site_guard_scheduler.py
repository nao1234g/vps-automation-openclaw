#!/usr/bin/env python3
"""Regression tests for site guard scheduler due-job routing."""

from __future__ import annotations

from datetime import datetime, timezone

from site_guard_scheduler import due_jobs


def main() -> int:
    assert due_jobs(datetime(2026, 4, 2, 10, 7, tzinfo=timezone.utc)) == ["lang"]
    assert due_jobs(datetime(2026, 4, 2, 10, 13, tzinfo=timezone.utc)) == ["en-routes"]
    assert due_jobs(datetime(2026, 4, 2, 10, 17, tzinfo=timezone.utc)) == ["ghost-routes"]
    assert due_jobs(datetime(2026, 4, 2, 10, 22, tzinfo=timezone.utc)) == ["preview-routes"]
    assert due_jobs(datetime(2026, 4, 2, 10, 28, tzinfo=timezone.utc)) == ["source-links"]
    assert due_jobs(datetime(2026, 4, 2, 10, 34, tzinfo=timezone.utc)) == ["content-integrity"]
    assert due_jobs(datetime(2026, 4, 2, 10, 52, tzinfo=timezone.utc)) == ["smoke"]
    assert due_jobs(datetime(2026, 4, 2, 12, 56, tzinfo=timezone.utc)) == ["prediction-maturity"]
    assert due_jobs(datetime(2026, 4, 2, 13, 56, tzinfo=timezone.utc)) == []
    assert due_jobs(datetime(2026, 4, 2, 10, 11, tzinfo=timezone.utc)) == ["governance"]
    assert due_jobs(datetime(2026, 4, 2, 11, 11, tzinfo=timezone.utc)) == []
    print("PASS: site guard scheduler routing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
