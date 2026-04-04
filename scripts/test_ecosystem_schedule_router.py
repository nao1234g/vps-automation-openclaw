#!/usr/bin/env python3
"""Regression tests for ecosystem schedule router due-profile mapping."""

from __future__ import annotations

from datetime import datetime, timezone

from ecosystem_schedule_router import due_profiles


def main() -> int:
    assert due_profiles(datetime(2026, 4, 2, 10, 7, tzinfo=timezone.utc)) == ["hourly-core"]
    assert due_profiles(datetime(2026, 4, 2, 12, 19, tzinfo=timezone.utc)) == ["six-hour-site"]
    assert due_profiles(datetime(2026, 4, 2, 4, 31, tzinfo=timezone.utc)) == ["daily-quality"]
    assert due_profiles(datetime(2026, 4, 2, 5, 43, tzinfo=timezone.utc)) == ["daily-integrity"]
    assert due_profiles(datetime(2026, 4, 2, 6, 49, tzinfo=timezone.utc)) == ["daily-full-crawl"]
    assert due_profiles(datetime(2026, 4, 6, 6, 17, tzinfo=timezone.utc)) == ["weekly-governance"]
    assert due_profiles(datetime(2026, 4, 3, 6, 17, tzinfo=timezone.utc)) == []
    print("PASS: ecosystem schedule router routing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

