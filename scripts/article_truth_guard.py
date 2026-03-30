#!/usr/bin/env python3
"""Shared truth/source guard for generated articles and distribution.

This module is intentionally conservative:
- Articles must have at least one real external source URL to be considered publishable.
- If an article claims a frontier model release (for example GPT-6 release/launch),
  it must cite the vendor's official domain.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

DEFAULT_SITE_URL = "https://nowpattern.com"

SOURCE_MARKER_RE = re.compile(
    r"(?i)(?:>|\b)(sources?|source|references?|reference|出典|ソース)(?:<|\b)"
)
HREF_RE = re.compile(r"""href=["']([^"']+)["']""", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")

RELEASE_TERM_RE = re.compile(
    r"(?i)\b(release|released|launch|launched|announce|announced|introduc(?:e|ed|ing))\b|発表|リリース|公開"
)

FRONTIER_RULES = (
    (
        re.compile(r"(?i)\b(?:chatgpt|gpt)[\s\-]?(?:6|[7-9]|\d{2,})[a-z]*\b"),
        ("openai.com",),
        "OpenAI frontier model release claims require an official OpenAI source",
    ),
    (
        re.compile(r"(?i)\bclaude[\s\-]?(?:5|[6-9]|\d{2,})[a-z]*\b"),
        ("anthropic.com",),
        "Anthropic frontier model release claims require an official Anthropic source",
    ),
    (
        re.compile(r"(?i)\bgemini[\s\-]?(?:3|[4-9]|\d{2,})[a-z]*\b"),
        ("blog.google", "deepmind.google", "ai.google"),
        "Google frontier model release claims require an official Google source",
    ),
    (
        re.compile(r"(?i)\bgrok[\s\-]?(?:4|[5-9]|\d{2,})[a-z]*\b"),
        ("x.ai",),
        "xAI frontier model release claims require an official xAI source",
    ),
)


def strip_tags(html: str) -> str:
    return TAG_RE.sub(" ", html or "")


def extract_href_urls(html: str) -> list[str]:
    if not html:
        return []
    return [m.group(1).strip() for m in HREF_RE.finditer(html) if m.group(1).strip()]


def _normalize_urls(urls: list[str] | tuple[str, ...] | None) -> list[str]:
    if not urls:
        return []
    out: list[str] = []
    for item in urls:
        if isinstance(item, tuple) or isinstance(item, list):
            if len(item) >= 2 and item[1]:
                out.append(str(item[1]).strip())
        elif item:
            out.append(str(item).strip())
    return out


def external_urls(urls: list[str] | tuple[str, ...] | None, site_url: str = DEFAULT_SITE_URL) -> list[str]:
    site_host = urlparse(site_url).netloc.lower()
    results: list[str] = []
    for url in _normalize_urls(urls):
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if parsed.scheme not in {"http", "https"}:
            continue
        if not host:
            continue
        if host == site_host or host.endswith("." + site_host):
            continue
        if host in {"example.com", "www.example.com", "placeholder", "source"}:
            continue
        results.append(url)
    return results


def has_source_marker(html: str) -> bool:
    return bool(SOURCE_MARKER_RE.search(html or ""))


def official_domain_present(urls: list[str], official_domains: tuple[str, ...]) -> bool:
    domains = tuple(d.lower() for d in official_domains)
    for url in urls:
        host = urlparse(url).netloc.lower()
        if any(host == d or host.endswith("." + d) for d in domains):
            return True
    return False


def evaluate_article_truth(
    *,
    title: str = "",
    body_text: str = "",
    html: str = "",
    source_urls: list[str] | tuple[str, ...] | None = None,
    site_url: str = DEFAULT_SITE_URL,
    require_external_sources: bool = True,
) -> tuple[list[str], list[str]]:
    """Return (errors, external_urls_found)."""

    urls = _normalize_urls(source_urls)
    if html:
        urls.extend(extract_href_urls(html))
    ext_urls = external_urls(urls, site_url=site_url)

    errors: list[str] = []
    text = " ".join(part for part in [title or "", body_text or "", strip_tags(html)] if part)

    if require_external_sources and not ext_urls:
        errors.append("NO_EXTERNAL_SOURCES")
    if html and has_source_marker(html) and not ext_urls:
        errors.append("BROKEN_SOURCE_SECTION")

    if RELEASE_TERM_RE.search(text):
        for model_re, official_domains, message in FRONTIER_RULES:
            if model_re.search(text) and not official_domain_present(ext_urls, official_domains):
                errors.append("UNSUPPORTED_FRONTIER_RELEASE_CLAIM")
                errors.append(message)
                break

    return errors, ext_urls
