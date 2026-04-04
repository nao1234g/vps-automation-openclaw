#!/usr/bin/env python3
"""Shared rotating discovery utilities for public article audits."""

from __future__ import annotations

import json
import re
import ssl
import urllib.request
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse


SEEDS = (
    "/",
    "/en/",
)

SKIP_PREFIXES = (
    "/ghost/",
    "/assets/",
    "/public/",
    "/author/",
    "/tag/",
    "/rss/",
    "/page/",
    "/en/page/",
    "/webmentions/",
    "/members/",
    "/genre-",
    "/taxonomy/",
    "/en/taxonomy/",
    "/taxonomy-ja/",
    "/taxonomy-en/",
    "/en-taxonomy/",
    "/taxonomy-guide",
    "/taxonomy-guide-ja",
    "/taxonomy-guide-en",
    "/en/taxonomy-guide",
    "/en/taxonomy-guide-ja",
    "/en/taxonomy-guide-en",
    "/about/",
    "/integrity-audit/",
    "/predictions/",
    "/en/predictions/",
    "/en/about/",
    "/en/integrity-audit/",
)

HIDDEN_PATH_PREFIXES = (
    "/p/",
    "/preview/",
)

LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch(base_url: str, path_or_url: str, timeout: int = 20) -> tuple[int, str]:
    url = path_or_url if path_or_url.startswith("http") else urljoin(base_url, path_or_url)
    req = urllib.request.Request(url, headers={"User-Agent": "nowpattern-public-article-rotation/1.0"})
    with urllib.request.urlopen(req, context=ssl_context(), timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def normalize_article_path(base_url: str, href: str) -> str | None:
    parsed = urlparse(urljoin(base_url, href))
    base_host = urlparse(base_url).netloc
    if parsed.scheme and parsed.netloc and parsed.netloc != base_host:
        return None
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    if path in {"/", "/en", "/en/"}:
        return None
    if path == "/":
        return None
    if any(path.startswith(prefix) for prefix in SKIP_PREFIXES):
        return None
    if any(path.startswith(prefix) for prefix in HIDDEN_PATH_PREFIXES):
        return None
    return path


def load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"known_paths": list(SEEDS), "cursor": 0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"known_paths": list(SEEDS), "cursor": 0}
    if not isinstance(data.get("known_paths"), list):
        data["known_paths"] = list(SEEDS)
    if not isinstance(data.get("cursor"), int):
        data["cursor"] = 0
    return data


def save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def discover_article_paths(base_url: str, known_paths: list[str], discover_limit: int) -> list[str]:
    ordered = []
    seen: set[str] = set()
    for path in known_paths:
        if not isinstance(path, str):
            continue
        normalized = normalize_article_path(base_url, path)
        if normalized != path or path in seen:
            continue
        seen.add(path)
        ordered.append(path)

    queue: deque[str] = deque(SEEDS)
    fetched = 0
    while queue and fetched < discover_limit:
        path = queue.popleft()
        try:
            status, html = fetch(base_url, path)
        except Exception:
            fetched += 1
            continue
        fetched += 1
        if status >= 400:
            continue
        for href in LINK_RE.findall(html):
            candidate = normalize_article_path(base_url, href)
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            ordered.append(candidate)
            queue.append(candidate)
    return ordered


def pick_batch(known_paths: list[str], cursor: int, check_limit: int) -> tuple[list[str], int]:
    if not known_paths:
        return [], 0
    total = len(known_paths)
    batch: list[str] = []
    for offset in range(min(check_limit, total)):
        batch.append(known_paths[(cursor + offset) % total])
    next_cursor = (cursor + len(batch)) % total
    return batch, next_cursor
