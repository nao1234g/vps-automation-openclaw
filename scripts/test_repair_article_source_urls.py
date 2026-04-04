#!/usr/bin/env python3
"""Regression tests for known article source URL repairs."""

from __future__ import annotations

from repair_article_source_urls import canonicalize_external_url


def test_strip_nowpattern_ref_param_from_external_url() -> None:
    url = "https://example.com/report?ref=nowpattern.com&utm_source=newsletter"
    repaired, reason = canonicalize_external_url(url)
    assert repaired == "https://example.com/report?utm_source=newsletter", repaired
    assert reason == "strip_ref_param", reason


def test_known_broken_iea_source_is_canonicalized() -> None:
    url = "https://www.iea.org/reports/oil-market-report?ref=nowpattern.com"
    repaired, reason = canonicalize_external_url(url)
    assert repaired == "https://www.iea.org/about/oil-security-and-emergency-response/strait-of-hormuz", repaired
    assert reason == "known_broken_source", reason


def test_internal_nowpattern_url_is_untouched() -> None:
    url = "https://nowpattern.com/example/?ref=nowpattern.com"
    repaired, reason = canonicalize_external_url(url)
    assert repaired == url, repaired
    assert reason is None, reason


def run() -> None:
    test_strip_nowpattern_ref_param_from_external_url()
    test_known_broken_iea_source_is_canonicalized()
    test_internal_nowpattern_url_is_untouched()
    print("PASS: repair_article_source_urls regression checks")


if __name__ == "__main__":
    run()
