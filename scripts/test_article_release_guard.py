#!/usr/bin/env python3
"""Deterministic guard tests for truth-first publication policy."""

from __future__ import annotations

from article_release_guard import classify_release_lane, evaluate_release_blockers


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
    assert broken["release_lane"] == "truth_blocked", broken
    assert broken["human_approval_required"] is False, broken

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

    auto_safe_war = evaluate_release_blockers(
        title="Hormuz closure risk rattles energy markets",
        html="""
        <article>
          <p>Oil and shipping markets are repricing after new naval threats in Hormuz.</p>
          <h2>Sources</h2>
          <ul>
            <li><a href="https://www.reuters.com/world/middle-east/example">Reuters</a></li>
            <li><a href="https://www.ft.com/content/example">FT</a></li>
          </ul>
        </article>
        """,
        source_urls=[
            "https://www.reuters.com/world/middle-east/example",
            "https://www.ft.com/content/example",
        ],
        tags=["war", "geopolitics"],
        status="published",
        channel="distribution",
        require_external_sources=True,
    )
    assert auto_safe_war["ok"] is True, auto_safe_war
    assert auto_safe_war["release_lane"] == "auto_safe", auto_safe_war

    auto_safe_single_source_war = evaluate_release_blockers(
        title="US sanctions escalation raises Hormuz shipping risk",
        html="""
        <article>
          <p>Shipping insurers are repricing Gulf routes after new sanctions and naval warnings.</p>
          <h2>Sources</h2>
          <ul>
            <li><a href="https://www.reuters.com/world/middle-east/example">Reuters</a></li>
          </ul>
        </article>
        """,
        source_urls=["https://www.reuters.com/world/middle-east/example"],
        tags=["war", "geopolitics"],
        status="published",
        channel="distribution",
        require_external_sources=True,
    )
    assert auto_safe_single_source_war["ok"] is True, auto_safe_single_source_war
    assert auto_safe_single_source_war["release_lane"] == "auto_safe", auto_safe_single_source_war

    mixed_risk_advised = evaluate_release_blockers(
        title="Hormuz shock pushes markets toward a banking crisis",
        html="""
        <article>
          <p>War escalation and systemic liquidity fears are colliding.</p>
          <h2>Sources</h2>
          <ul>
            <li><a href="https://www.reuters.com/world/middle-east/example">Reuters</a></li>
            <li><a href="https://www.ft.com/content/example">FT</a></li>
          </ul>
        </article>
        """,
        source_urls=[
            "https://www.reuters.com/world/middle-east/example",
            "https://www.ft.com/content/example",
        ],
        tags=["war", "finance"],
        status="published",
        channel="distribution",
        require_external_sources=True,
    )
    assert mixed_risk_advised["ok"] is True, mixed_risk_advised
    assert mixed_risk_advised["editor_review_required"] is False, mixed_risk_advised
    assert mixed_risk_advised["release_lane"] == "editorial_review_advised", mixed_risk_advised
    assert "EDITORIAL_REVIEW_ADVISED:WAR_CONFLICT,FINANCIAL_CRISIS" in mixed_risk_advised["warnings"], mixed_risk_advised

    mixed_risk_single_source_needs_review = evaluate_release_blockers(
        title="Hormuz shock pushes markets toward a banking crisis",
        html="""
        <article>
          <p>War escalation and systemic liquidity fears are colliding.</p>
          <h2>Sources</h2>
          <ul>
            <li><a href="https://www.reuters.com/world/middle-east/example">Reuters</a></li>
          </ul>
        </article>
        """,
        source_urls=["https://www.reuters.com/world/middle-east/example"],
        tags=["war", "finance"],
        status="published",
        channel="distribution",
        require_external_sources=True,
    )
    assert mixed_risk_single_source_needs_review["ok"] is True, mixed_risk_single_source_needs_review
    assert mixed_risk_single_source_needs_review["editor_review_required"] is False, mixed_risk_single_source_needs_review
    assert mixed_risk_single_source_needs_review["release_lane"] == "editorial_review_advised", mixed_risk_single_source_needs_review
    assert (
        "EDITORIAL_REVIEW_ADVISED:WAR_CONFLICT,FINANCIAL_CRISIS"
        in mixed_risk_single_source_needs_review["warnings"]
    ), mixed_risk_single_source_needs_review

    single_risk_two_urls_fallback = classify_release_lane(
        truth_errors=[],
        risk_flags=["WAR_CONFLICT"],
        approval_present=False,
        external_url_count=2,
        verified_external_source_count=0,
        oracle_marker_present=False,
    )
    assert single_risk_two_urls_fallback == "auto_safe", single_risk_two_urls_fallback

    oracle_non_frontier = evaluate_release_blockers(
        title="Hormuz closure forecast for shipping insurance",
        html="""
        <article>
          <div id="np-oracle">
            <strong>Prediction Question</strong>: Will insurers raise Gulf route premiums by 20%?
          </div>
          <h2>Sources</h2>
          <ul>
            <li><a href="https://www.reuters.com/world/middle-east/example">Reuters</a></li>
            <li><a href="https://www.ft.com/content/example">FT</a></li>
          </ul>
        </article>
        """,
        source_urls=[
            "https://www.reuters.com/world/middle-east/example",
            "https://www.ft.com/content/example",
        ],
        tags=["oracle", "war", "geopolitics"],
        status="published",
        channel="distribution",
        require_external_sources=True,
    )
    assert oracle_non_frontier["ok"] is False, oracle_non_frontier
    assert oracle_non_frontier["human_approval_required"] is False, oracle_non_frontier
    assert oracle_non_frontier["editor_review_required"] is True, oracle_non_frontier
    assert oracle_non_frontier["release_lane"] == "review_required", oracle_non_frontier

    jp_war = evaluate_release_blockers(
        title="停戦崩壊で中東戦争が再拡大",
        html="<article><p>停戦が崩壊し、軍事衝突が再燃した。</p></article>",
        source_urls=["https://www.reuters.com/world/middle-east/example"],
        tags=[],
        status="published",
        channel="public",
        require_external_sources=False,
    )
    assert "WAR_CONFLICT" in jp_war["risk_flags"], jp_war

    jp_finance = evaluate_release_blockers(
        title="銀行危機で市場崩壊リスクが拡大",
        html="<article><p>銀行危機と債務危機が重なり、不況懸念が強まった。</p></article>",
        source_urls=["https://www.ft.com/content/example"],
        tags=[],
        status="published",
        channel="public",
        require_external_sources=False,
    )
    assert "FINANCIAL_CRISIS" in jp_finance["risk_flags"], jp_finance

    print("PASS: article release guard regression checks")


if __name__ == "__main__":
    run()
