#!/usr/bin/env python3
"""Deterministic guard tests for truth-first publication policy."""

from __future__ import annotations

from article_release_guard import evaluate_release_blockers


def run() -> None:
    html_broken_source = """
    <article>
      <h1>GPT-6 released for enterprise users</h1>
      <p>OpenAI released GPT-6 today.</p>
      <h2>Sources</h2>
      <ul><li><a href="#">Source</a></li></ul>
    </article>
    """
    broken = evaluate_release_blockers(
        title="GPT-6 released for enterprise users",
        html=html_broken_source,
        tags=["ai", "frontier-ai"],
        status="published",
        channel="public",
        require_external_sources=True,
    )
    assert "NO_EXTERNAL_SOURCES" in broken["errors"], broken
    assert "BROKEN_SOURCE_SECTION" in broken["errors"], broken
    assert "UNSUPPORTED_FRONTIER_RELEASE_CLAIM" in broken["errors"], broken
    assert any(err.startswith("HUMAN_APPROVAL_REQUIRED:") for err in broken["errors"]), broken

    html_non_official = """
    <article>
      <p>GPT-6 launched and changes everything.</p>
      <h2>Sources</h2>
      <ul><li><a href="https://example-news.test/gpt-6">Source</a></li></ul>
    </article>
    """
    no_vendor = evaluate_release_blockers(
        title="GPT-6 launched and changes everything",
        html=html_non_official,
        source_urls=["https://news.example.org/gpt-6-rumor"],
        tags=["ai", "frontier-ai"],
        status="published",
        channel="public",
        require_external_sources=True,
    )
    assert "UNSUPPORTED_FRONTIER_RELEASE_CLAIM" in no_vendor["errors"], no_vendor

    html_vendor = """
    <article>
      <p>OpenAI announced GPT-6.</p>
      <h2>Sources</h2>
      <ul><li><a href="https://openai.com/index/gpt-6/">OpenAI</a></li></ul>
    </article>
    """
    needs_human = evaluate_release_blockers(
        title="OpenAI announced GPT-6",
        html=html_vendor,
        source_urls=["https://openai.com/index/gpt-6/"],
        tags=["ai", "frontier-ai"],
        status="published",
        channel="public",
        require_external_sources=True,
    )
    assert "UNSUPPORTED_FRONTIER_RELEASE_CLAIM" not in needs_human["errors"], needs_human
    assert needs_human["human_approval_required"] is True, needs_human
    assert needs_human["human_approval_present"] is False, needs_human
    assert needs_human["release_lane"] == "human_review_required", needs_human

    approved = evaluate_release_blockers(
        title="OpenAI announced GPT-6",
        html=html_vendor,
        source_urls=["https://openai.com/index/gpt-6/"],
        tags=["ai", "frontier-ai", "human-approved"],
        status="published",
        channel="public",
        require_external_sources=True,
    )
    assert approved["ok"] is True, approved
    assert approved["release_lane"] == "distribution_ready", approved

    print("PASS: article release guard regression checks")


if __name__ == "__main__":
    run()
