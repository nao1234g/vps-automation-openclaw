#!/usr/bin/env python3
"""Regression tests for site UI guard cron installer cleanup."""

from __future__ import annotations

from install_site_ui_guard import filter_managed_lines


def test_filter_managed_lines_removes_legacy_and_current_tags() -> None:
    lines = [
        "7,37 * * * * ... # np-ui-guard-lang",
        "34 * * * * ... # np-ui-guard-theme-en-urls",
        "41 * * * * ... # np-ui-guard-ghost-authors",
        "46 * * * * ... # np-ui-guard-draft-links",
        "34 * * * * ... # np-ui-guard-content-integrity",
        "0 0 * * * python3 /opt/shared/scripts/safe_job.py",
    ]
    filtered = filter_managed_lines(lines)
    assert filtered == ["0 0 * * * python3 /opt/shared/scripts/safe_job.py"], filtered


def run() -> None:
    test_filter_managed_lines_removes_legacy_and_current_tags()
    print("PASS: install_site_ui_guard regression checks")


if __name__ == "__main__":
    run()
