#!/usr/bin/env python3
"""Regression tests for article anchor integrity audit behavior."""

from __future__ import annotations

from article_anchor_integrity_audit import AnchorAuditResult, is_stale_article_result


def test_stale_article_result_detects_dead_rotation_paths() -> None:
    result = AnchorAuditResult(
        slug="dead-path",
        url="https://nowpattern.com/dead-path/",
        ok=False,
        errors=["fetch_failed:HTTP Error 404: Not Found"],
    )
    assert is_stale_article_result(result) is True

    broken_anchor = AnchorAuditResult(
        slug="broken-anchor",
        url="https://nowpattern.com/live/",
        ok=False,
        errors=["broken_anchor_pattern:#NP-2026-0001"],
    )
    assert is_stale_article_result(broken_anchor) is False


def run() -> None:
    test_stale_article_result_detects_dead_rotation_paths()
    print("PASS: article_anchor_integrity_audit regression checks")


if __name__ == "__main__":
    run()
