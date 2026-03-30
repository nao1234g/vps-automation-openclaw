#!/usr/bin/env python3
"""Post-generation fact-check and revision helpers.

This module is intentionally fail-closed:
- If we cannot fetch any real source evidence, publication should stop.
- If the fact-check model cannot produce a clean pass after one revision pass,
  publication should stop.

It is designed for generated article JSON before HTML is built/published.
"""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import urllib.request
from html import unescape
from typing import Any

from article_truth_guard import DEFAULT_SITE_URL, evaluate_article_truth, external_urls

USER_AGENT = "Mozilla/5.0 Nowpattern-FactCheck/1.0"
MAX_SOURCE_BYTES = 250_000
MAX_SOURCE_SNIPPET_CHARS = 1_600
MAX_SOURCE_COUNT = 6
MAX_ARTICLE_TEXT_CHARS = 16_000
CLAUDE_TIMEOUT = 420

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
META_DESC_RE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)

FACTCHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "revise", "block"]},
        "issues": {"type": "array", "items": {"type": "string"}},
        "revision_summary": {"type": "string"},
        "claim_checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["supported", "partial", "unsupported"]},
                    "supporting_urls": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["claim", "verdict", "supporting_urls"],
                "additionalProperties": False,
            },
        },
        "revised_data": {"type": "object"},
    },
    "required": ["verdict", "issues", "revision_summary", "claim_checks", "revised_data"],
    "additionalProperties": False,
}


def _normalize_ws(text: str) -> str:
    return WS_RE.sub(" ", (text or "")).strip()


def _strip_html(html: str) -> str:
    return _normalize_ws(unescape(TAG_RE.sub(" ", html or "")))


def _collect_text_fields(value: Any, out: list[str], *, depth: int = 0) -> None:
    if depth > 6:
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            key_lower = str(key).lower()
            if key_lower.endswith("url") or key_lower.endswith("urls"):
                continue
            _collect_text_fields(nested, out, depth=depth + 1)
        return
    if isinstance(value, list):
        for item in value:
            _collect_text_fields(item, out, depth=depth + 1)
        return
    if isinstance(value, str):
        text = _normalize_ws(value)
        if text:
            out.append(text)


def article_text_from_data(data: dict) -> str:
    chunks: list[str] = []
    _collect_text_fields(data, chunks)
    joined = "\n".join(chunks)
    return joined[:MAX_ARTICLE_TEXT_CHARS]


def _extract_meta_description(html: str) -> str:
    match = META_DESC_RE.search(html or "")
    return _normalize_ws(unescape(match.group(1))) if match else ""


def _extract_title(html: str) -> str:
    match = TITLE_RE.search(html or "")
    return _normalize_ws(unescape(match.group(1))) if match else ""


def fetch_source_evidence(url: str, *, timeout: int = 20) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(MAX_SOURCE_BYTES)
            content_type = resp.headers.get_content_charset() or "utf-8"
            html = raw.decode(content_type, errors="replace")
            text = _strip_html(html)[:MAX_SOURCE_SNIPPET_CHARS]
            return {
                "url": url,
                "final_url": resp.geturl(),
                "ok": True,
                "status": getattr(resp, "status", 200),
                "title": _extract_title(html),
                "description": _extract_meta_description(html),
                "snippet": text,
            }
    except Exception as exc:
        return {
            "url": url,
            "ok": False,
            "error": str(exc)[:240],
        }


def collect_source_evidence(
    source_urls: list[str] | tuple[str, ...] | None,
    *,
    site_url: str = DEFAULT_SITE_URL,
    max_sources: int = MAX_SOURCE_COUNT,
) -> list[dict[str, Any]]:
    unique_urls: list[str] = []
    seen: set[str] = set()
    for url in external_urls(source_urls, site_url=site_url):
        if url in seen:
            continue
        seen.add(url)
        unique_urls.append(url)
        if len(unique_urls) >= max_sources:
            break
    return [fetch_source_evidence(url) for url in unique_urls]


def _merge_missing(template: Any, candidate: Any) -> Any:
    if isinstance(template, dict):
        merged = dict(candidate) if isinstance(candidate, dict) else {}
        for key, value in template.items():
            if key in merged:
                merged[key] = _merge_missing(value, merged[key])
            else:
                merged[key] = copy.deepcopy(value)
        return merged
    if isinstance(template, list):
        if isinstance(candidate, list):
            return candidate
        return copy.deepcopy(template)
    if candidate in (None, "") and template not in (None, ""):
        return copy.deepcopy(template)
    return candidate


def _call_claude_json(prompt: str, schema: dict, *, timeout: int = CLAUDE_TIMEOUT) -> dict[str, Any] | None:
    cmd = [
        "claude", "-p",
        "--model", "opus",
        "--output-format", "json",
        "--json-schema", json.dumps(schema, ensure_ascii=False),
        "--permission-mode", "acceptEdits",
        "--no-session-persistence",
        prompt,
    ]
    cwd = "/opt" if os.path.exists("/opt") else os.getcwd()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None

    if result.returncode != 0:
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict) and payload.get("is_error"):
        return None
    if isinstance(payload, dict) and "result" in payload:
        inner = payload["result"]
        if isinstance(inner, str):
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                return None
        if isinstance(inner, dict):
            return inner
    return payload if isinstance(payload, dict) else None


def _build_review_prompt(
    *,
    data: dict,
    source_packets: list[dict[str, Any]],
    lang: str,
    mode: str,
    round_index: int,
) -> str:
    language_label = "Japanese" if lang == "ja" else "English"
    round_label = "initial review" if round_index == 1 else f"verification round {round_index}"
    source_json = json.dumps(source_packets, ensure_ascii=False, indent=2)
    article_json = json.dumps(data, ensure_ascii=False, indent=2)
    return f"""You are the final factual publication gate for Nowpattern.

Task:
- Review the generated {mode} article JSON against the provided source evidence only.
- Do not rely on memory or unstated assumptions.
- Unsupported claims must be removed, softened, or rewritten so the article becomes publishable.
- If the core thesis cannot be supported by the sources, return verdict=block.

Critical rules:
- Never state an unverified product release, launch, or announcement as fact.
- Never keep a claim that is not supported by the provided source evidence.
- Preserve the original JSON structure and keys as much as possible.
- Keep source_urls accurate; do not invent URLs.
- If revision is possible, return the full corrected JSON as revised_data.

Language of article: {language_label}
Review phase: {round_label}

Source evidence:
{source_json}

Generated article JSON:
{article_json}

Return JSON with:
- verdict: pass | revise | block
- issues: short machine-readable issue strings
- revision_summary: one concise sentence
- claim_checks: up to 5 key claims with verdict supported|partial|unsupported and supporting_urls from the provided evidence only
- revised_data: full corrected JSON object
"""


def fact_check_and_revise_generated_article(
    *,
    data: dict,
    source_urls: list[str] | tuple[str, ...] | None,
    lang: str,
    mode: str,
    site_url: str = DEFAULT_SITE_URL,
    max_rounds: int = 2,
) -> dict[str, Any]:
    """Run post-generation fact-check, optionally revise once, then verify again."""

    source_packets = collect_source_evidence(source_urls, site_url=site_url)
    good_packets = [packet for packet in source_packets if packet.get("ok")]
    if not good_packets:
        return {
            "ok": False,
            "data": data,
            "issues": ["NO_FETCHABLE_SOURCES"],
            "summary": "No fetchable external source evidence available",
            "rounds": [],
            "source_packets": source_packets,
        }

    current = copy.deepcopy(data)
    rounds: list[dict[str, Any]] = []
    latest_claim_checks: list[dict[str, Any]] = []

    for round_index in range(1, max_rounds + 1):
        response = _call_claude_json(
            _build_review_prompt(
                data=current,
                source_packets=good_packets,
                lang=lang,
                mode=mode,
                round_index=round_index,
            ),
            FACTCHECK_SCHEMA,
        )
        if not response:
            return {
                "ok": False,
                "data": current,
                "issues": ["FACTCHECK_MODEL_UNAVAILABLE"],
                "summary": "Fact-check model did not return a usable response",
                "rounds": rounds,
                "claim_checks": latest_claim_checks,
                "source_packets": source_packets,
            }

        verdict = str(response.get("verdict", "block")).strip().lower()
        issues = [str(item) for item in (response.get("issues") or [])]
        claim_checks = [
            {
                "claim": str(item.get("claim", "")).strip(),
                "verdict": str(item.get("verdict", "")).strip(),
                "supporting_urls": [
                    str(url).strip()
                    for url in (item.get("supporting_urls") or [])
                    if str(url).strip()
                ],
            }
            for item in (response.get("claim_checks") or [])
            if isinstance(item, dict) and str(item.get("claim", "")).strip()
        ]
        latest_claim_checks = claim_checks
        revised = _merge_missing(current, response.get("revised_data") or current)
        summary = str(response.get("revision_summary", "")).strip()

        truth_errors, external = evaluate_article_truth(
            title=str(revised.get("title", "")),
            body_text=article_text_from_data(revised),
            source_urls=[
                item.get("url")
                for item in (revised.get("source_urls") or [])
                if isinstance(item, dict)
            ] or source_urls,
            site_url=site_url,
            require_external_sources=True,
        )
        if truth_errors:
            issues = list(dict.fromkeys(issues + truth_errors))
            if verdict == "pass":
                verdict = "revise"

        rounds.append({
            "round": round_index,
            "verdict": verdict,
            "issues": issues,
            "summary": summary,
            "external_source_count": len(external),
            "claim_checks": claim_checks,
        })

        if verdict == "pass":
            return {
                "ok": True,
                "data": revised,
                "issues": issues,
                "summary": summary or "Fact-check passed",
                "rounds": rounds,
                "claim_checks": claim_checks,
                "source_packets": source_packets,
            }

        if verdict == "revise" and round_index < max_rounds:
            current = revised
            continue

        return {
            "ok": False,
            "data": revised,
            "issues": issues or ["FACTCHECK_BLOCKED"],
            "summary": summary or "Fact-check blocked publication",
            "rounds": rounds,
            "claim_checks": claim_checks,
            "source_packets": source_packets,
        }

    return {
        "ok": False,
        "data": current,
        "issues": ["FACTCHECK_EXHAUSTED"],
        "summary": "Fact-check rounds exhausted",
        "rounds": rounds,
        "claim_checks": latest_claim_checks,
        "source_packets": source_packets,
    }
