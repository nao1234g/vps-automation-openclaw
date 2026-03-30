#!/usr/bin/env python3
"""Shared release blocker for publication and external distribution.

Principles:
- Truth/source integrity is necessary but not sufficient.
- High-risk topics must not auto-publish without explicit human approval.
- External distribution must obey the same blocker as public publication.
"""

from __future__ import annotations

import re
from typing import Any

from article_factcheck_postprocess import collect_source_evidence
from article_truth_guard import DEFAULT_SITE_URL, evaluate_article_truth, strip_tags

HUMAN_APPROVAL_TAGS = {
    "human-approved",
    "truth-reviewed",
    "risk-reviewed",
    "editor-approved",
}

HIGH_RISK_RULES: tuple[tuple[str, re.Pattern[str], set[str]], ...] = (
    (
        "FRONTIER_AI",
        re.compile(
            r"(?i)\b(?:chatgpt|gpt(?:-[a-z0-9.]+)?|claude|gemini|grok|frontier ai|frontier model|foundation model|agi)\b"
        ),
        {"frontier-ai", "ai", "artificial-intelligence"},
    ),
    (
        "WAR_CONFLICT",
        re.compile(
            r"(?i)\b(?:war|attack|strike|missile|nuclear|invasion|military|troops|conflict|ceasefire|sanction|drone|blockade|naval|airstrike)\b|戦争|侵攻|空爆|攻撃|ミサイル|核|制裁|停戦|軍事|衝突|封鎖"
        ),
        {"war", "conflict", "geopolitics", "security", "military"},
    ),
    (
        "FINANCIAL_CRISIS",
        re.compile(
            r"(?i)\b(?:financial crisis|banking crisis|bank run|liquidity crisis|default|insolvency|debt crisis|systemic risk|recession|depression|market crash|bailout)\b|金融危機|銀行危機|デフォルト|債務危機|市場崩壊|破綻|不況"
        ),
        {"finance", "banking", "macro", "economy"},
    ),
)


def classify_release_lane(
    *,
    truth_errors: list[str] | tuple[str, ...],
    risk_flags: list[str] | tuple[str, ...],
    approval_present: bool,
) -> str:
    if truth_errors:
        return "truth_blocked"
    if risk_flags and not approval_present:
        return "human_review_required"
    return "distribution_ready"


def normalize_tag_slugs(tags: Any) -> set[str]:
    if not tags:
        return set()
    slugs: set[str] = set()
    for tag in tags:
        if isinstance(tag, dict):
            slug = str(tag.get("slug") or tag.get("name") or "").strip().lower()
        else:
            slug = str(tag or "").strip().lower()
        if slug:
            slugs.add(slug)
    return slugs


def has_human_approval(tags: Any) -> bool:
    return bool(normalize_tag_slugs(tags) & HUMAN_APPROVAL_TAGS)


def detect_release_risk_flags(
    *,
    title: str = "",
    body_text: str = "",
    html: str = "",
    tags: Any = None,
) -> list[str]:
    text = " ".join(
        part for part in [title or "", body_text or "", strip_tags(html or "")] if part
    )
    tag_slugs = normalize_tag_slugs(tags)
    flags: list[str] = []
    for code, pattern, tag_hits in HIGH_RISK_RULES:
        if pattern.search(text) or tag_slugs.intersection(tag_hits):
            flags.append(code)
    return flags


def evaluate_release_blockers(
    *,
    title: str = "",
    body_text: str = "",
    html: str = "",
    source_urls: list[str] | tuple[str, ...] | None = None,
    tags: Any = None,
    site_url: str = DEFAULT_SITE_URL,
    status: str = "published",
    channel: str = "public",
    require_external_sources: bool = True,
    check_source_fetchability: bool = False,
) -> dict[str, Any]:
    truth_errors, external = evaluate_article_truth(
        title=title,
        body_text=body_text,
        html=html,
        source_urls=source_urls,
        site_url=site_url,
        require_external_sources=require_external_sources,
    )
    risk_flags = detect_release_risk_flags(
        title=title,
        body_text=body_text,
        html=html,
        tags=tags,
    )
    approval_present = has_human_approval(tags)
    approval_required = (status or "").lower() == "published" and bool(risk_flags)
    lane = classify_release_lane(
        truth_errors=truth_errors,
        risk_flags=risk_flags,
        approval_present=approval_present,
    )

    errors = list(truth_errors)
    if approval_required and not approval_present:
        errors.append("HUMAN_APPROVAL_REQUIRED:" + ",".join(risk_flags))

    evidence_packets: list[dict[str, Any]] = []
    if check_source_fetchability:
        if external:
            evidence_packets = collect_source_evidence(external, site_url=site_url)
            if not any(item.get("ok") for item in evidence_packets):
                errors.append("NO_FETCHABLE_EXTERNAL_SOURCE_URLS")
        else:
            errors.append("NO_FETCHABLE_EXTERNAL_SOURCE_URLS")

    return {
        "ok": not errors,
        "errors": errors,
        "external_urls": external,
        "risk_flags": risk_flags,
        "human_approval_required": approval_required,
        "human_approval_present": approval_present,
        "release_lane": lane,
        "channel": channel,
        "status": status,
        "evidence_packets": evidence_packets,
    }


def assert_release_ready(**kwargs: Any) -> dict[str, Any]:
    result = evaluate_release_blockers(**kwargs)
    if result["errors"]:
        raise ValueError("release blocker: " + ", ".join(result["errors"]))
    return result
