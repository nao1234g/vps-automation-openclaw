#!/usr/bin/env python3
"""Regression tests for rotating site link crawler coverage."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import site_link_crawler as slc  # noqa: E402


def test_normalize_internal_path_filters_assets() -> None:
    base = "https://nowpattern.com/"
    assert slc.normalize_internal_path(base, "/assets/app.css") is None
    assert slc.normalize_internal_path(base, "/ghost/") is None
    assert slc.normalize_internal_path(base, "/en/article/") == "/en/article/"


def test_pick_batch_rotates_cursor() -> None:
    paths = ["/", "/en/", "/predictions/", "/about/"]
    batch, next_cursor = slc.pick_batch(paths, 2, 3)
    assert batch == ["/predictions/", "/about/", "/"], batch
    assert next_cursor == 1, next_cursor


def test_stale_pattern_only_triggers_on_actual_attributes() -> None:
    html_script_only = '<script>if (normalized.indexOf("/en/en-") === 0) {}</script>'
    html_bad_href = '<a href="/en/en-broken/"></a>'
    assert not any(pattern.search(html_script_only) for pattern in slc.STALE_ATTR_PATTERNS)
    assert any(pattern.search(html_bad_href) for pattern in slc.STALE_ATTR_PATTERNS)


def test_prunable_stale_failure_only_applies_to_dead_unlinked_paths() -> None:
    dead = slc.CrawlResult(path="/dead/", url="https://nowpattern.com/dead/", ok=False, errors=["fetch_failed:HTTP Error 404: Not Found"])
    live = slc.CrawlResult(path="/live/", url="https://nowpattern.com/live/", ok=False, errors=["fetch_failed:HTTP Error 404: Not Found"])
    assert slc.is_prunable_stale_failure(dead, {"/", "/en/"})
    assert not slc.is_prunable_stale_failure(live, {"/live/"})


def test_fetch_retries_transient_timeouts() -> None:
    original_urlopen = slc.urllib.request.urlopen
    original_sleep = slc.time.sleep
    calls = {"count": 0}

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return b"ok"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def fake_urlopen(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("The read operation timed out")
        return _Resp()

    slc.urllib.request.urlopen = fake_urlopen
    slc.time.sleep = lambda *args, **kwargs: None
    try:
        status, body = slc.fetch("https://nowpattern.com/test")
    finally:
        slc.urllib.request.urlopen = original_urlopen
        slc.time.sleep = original_sleep

    assert calls["count"] == 3
    assert status == 200
    assert body == "ok"


def run() -> None:
    test_normalize_internal_path_filters_assets()
    test_pick_batch_rotates_cursor()
    test_stale_pattern_only_triggers_on_actual_attributes()
    test_prunable_stale_failure_only_applies_to_dead_unlinked_paths()
    test_fetch_retries_transient_timeouts()
    print("PASS: site link crawler regression checks")


if __name__ == "__main__":
    run()
