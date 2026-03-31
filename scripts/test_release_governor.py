#!/usr/bin/env python3
"""Regression tests for the shared release governor wrapper."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from release_governor import (  # noqa: E402
    GOVERNOR_POLICY_VERSION,
    assert_governed_release_ready,
    evaluate_governed_release,
)


def test_governor_marks_payload_as_governed() -> None:
    result = evaluate_governed_release(
        title="Analysis with official source",
        html='<article><a href="https://openai.com/index/gpt-6/">Source</a></article>',
        source_urls=["https://openai.com/index/gpt-6/"],
        tags=["frontier-ai", "human-approved"],
        site_url="https://nowpattern.com",
        status="published",
        channel="public",
        require_external_sources=True,
    )
    assert result["governed"] is True
    assert result["governor_policy_version"] == GOVERNOR_POLICY_VERSION
    assert result["mission_contract_version"]
    assert result["mission_contract_hash"]
    assert result["lexicon_version"]


def test_assert_governor_raises_on_invalid_release() -> None:
    try:
        assert_governed_release_ready(
            title="GPT-9 launched today",
            html="<article><p>Rumor only</p></article>",
            source_urls=[],
            tags=["frontier-ai"],
            site_url="https://nowpattern.com",
            status="published",
            channel="public",
            require_external_sources=True,
        )
    except ValueError:
        return
    raise AssertionError("shared release governor allowed invalid frontier release")


def run() -> None:
    test_governor_marks_payload_as_governed()
    test_assert_governor_raises_on_invalid_release()
    print("PASS: release governor regression checks")


if __name__ == "__main__":
    run()
