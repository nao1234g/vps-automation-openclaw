#!/usr/bin/env python3
"""Shared release blocker for publication and external distribution.

Principles:
- Truth/source integrity is necessary but not sufficient.
- High-risk topics must not auto-publish without explicit human approval.
- External distribution must obey the same blocker as public publication.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit
from typing import Any

from article_factcheck_postprocess import collect_source_evidence
from article_truth_guard import DEFAULT_SITE_URL, evaluate_article_truth, strip_tags

HUMAN_APPROVAL_TAGS = {
    "human-approved",
    "truth-reviewed",
    "risk-reviewed",
    "editor-approved",
}

PREDICTION_ORACLE_TAGS = {
    "oracle",
    "forecast",
    "prediction",
    "reader-predict",
    "np-oracle",
}

ORACLE_MARKER_RE = re.compile(
    r"(?i)(?:np-oracle|oracle declaration|prediction question|forecast question|oracle pick|nowpattern(?:の)?予測|予測質問|予測期限)"
)

AUTO_SAFE_SINGLE_RISK_FLAGS = {
    "WAR_CONFLICT",
    "FINANCIAL_CRISIS",
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
    external_url_count: int,
    verified_external_source_count: int,
    oracle_marker_present: bool,
    prediction_linkage_state: str = "",
) -> str:
    if truth_errors:
        return "truth_blocked"
    if approval_present:
        return "distribution_ready"
    # Prediction-linked articles without a cross-language sibling are not ready.
    if oracle_marker_present and prediction_linkage_state in (
        "missing_sibling",
        "tracker_only",
    ):
        return "review_required"
    verified_count = verified_external_source_count or external_url_count
    if "FRONTIER_AI" in risk_flags:
        return "human_review_required"
    if oracle_marker_present:
        return "review_required"
    if len(risk_flags) >= 2:
        if set(risk_flags).issubset(AUTO_SAFE_SINGLE_RISK_FLAGS):
            if verified_count >= 1:
                return "editorial_review_advised"
            if external_url_count >= 2:
                return "editorial_review_advised"
        return "review_required"
    if risk_flags and verified_count < 1:
        if set(risk_flags).issubset(AUTO_SAFE_SINGLE_RISK_FLAGS) and external_url_count >= 2:
            return "editorial_review_advised"
        return "review_required"
    if set(risk_flags).issubset(AUTO_SAFE_SINGLE_RISK_FLAGS):
        return "auto_safe"
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


def has_oracle_marker(
    *,
    title: str = "",
    body_text: str = "",
    html: str = "",
    tags: Any = None,
) -> bool:
    tag_slugs = normalize_tag_slugs(tags)
    if tag_slugs & PREDICTION_ORACLE_TAGS:
        return True
    text = " ".join(part for part in [title or "", body_text or "", strip_tags(html or "")] if part)
    return bool(ORACLE_MARKER_RE.search(text) or "np-oracle" in (html or ""))


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


def _normalize_external_url(url: str) -> str:
    parsed = urlsplit((url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return (url or "").strip()
    normalized = parsed._replace(fragment="")
    return urlunsplit(normalized).rstrip("/")


def _dedupe_external_urls(urls: list[str] | tuple[str, ...]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in urls:
        normalized = _normalize_external_url(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


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
    prediction_linkage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    truth_errors, external = evaluate_article_truth(
        title=title,
        body_text=body_text,
        html=html,
        source_urls=source_urls,
        site_url=site_url,
        require_external_sources=require_external_sources,
    )
    external = _dedupe_external_urls(external)
    risk_flags = detect_release_risk_flags(
        title=title,
        body_text=body_text,
        html=html,
        tags=tags,
    )
    approval_present = has_human_approval(tags)
    oracle_marker_present = has_oracle_marker(
        title=title,
        body_text=body_text,
        html=html,
        tags=tags,
    )
    evidence_packets: list[dict[str, Any]] = []
    verified_external_source_count = len(external)
    if check_source_fetchability:
        if external:
            evidence_packets = collect_source_evidence(external, site_url=site_url)
            verified_external_source_count = sum(1 for item in evidence_packets if item.get("ok"))
        else:
            evidence_packets = []
    linkage_state = ""
    linkage_info: dict[str, Any] = {}
    if prediction_linkage:
        linkage_state = str(prediction_linkage.get("linkage_state", ""))
        linkage_info = prediction_linkage
    lane = classify_release_lane(
        truth_errors=truth_errors,
        risk_flags=risk_flags,
        approval_present=approval_present,
        external_url_count=len(external),
        verified_external_source_count=verified_external_source_count,
        oracle_marker_present=oracle_marker_present,
        prediction_linkage_state=linkage_state,
    )
    approval_required = (status or "").lower() == "published" and lane == "human_review_required"
    review_required = (status or "").lower() == "published" and lane == "review_required"
    warnings: list[str] = []

    errors = list(truth_errors)
    # Add linkage errors from prediction contract evaluation
    if linkage_info:
        errors.extend(linkage_info.get("errors", []))
    if approval_required and not approval_present:
        errors.append("HUMAN_APPROVAL_REQUIRED:" + ",".join(risk_flags))
    if review_required and not approval_present:
        errors.append("EDITOR_REVIEW_REQUIRED:" + ",".join(risk_flags))
    if lane == "editorial_review_advised":
        warnings.append("EDITORIAL_REVIEW_ADVISED:" + ",".join(risk_flags))

    if check_source_fetchability:
        if verified_external_source_count <= 0:
            errors.append("NO_FETCHABLE_EXTERNAL_SOURCE_URLS")

    return {
        "ok": not errors,
        "errors": errors,
        "external_urls": external,
        "verified_external_source_count": verified_external_source_count,
        "risk_flags": risk_flags,
        "oracle_marker_present": oracle_marker_present,
        "human_approval_required": approval_required,
        "editor_review_required": review_required,
        "human_approval_present": approval_present,
        "release_lane": lane,
        "channel": channel,
        "status": status,
        "evidence_packets": evidence_packets,
        "warnings": warnings,
        "prediction_linkage": linkage_info or None,
    }


def assert_release_ready(**kwargs: Any) -> dict[str, Any]:
    result = evaluate_release_blockers(**kwargs)
    if result["errors"]:
        raise ValueError("release blocker: " + ", ".join(result["errors"]))
    return result
