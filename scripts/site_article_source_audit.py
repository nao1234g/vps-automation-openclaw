#!/usr/bin/env python3
"""Externally audit public article pages for reachable source links."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse


SEEDS = [
    {"slug": "home-ja", "path": "/", "lang": "ja"},
    {"slug": "home-en", "path": "/en/", "lang": "en"},
]

SKIP_PREFIXES = (
    "/tag/",
    "/author/",
    "/rss/",
    "/page/",
    "/predictions/",
    "/taxonomy/",
    "/about/",
    "/members/",
    "/webmentions/",
    "/ghost/",
    "/assets/",
    "/public/",
    "/p/",
)
ARTICLE_LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


@dataclass
class ArticleAuditResult:
    slug: str
    url: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_count: int = 0
    checked_source_links: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch(url: str, timeout: int = 20) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "nowpattern-article-source-audit/1.0"})
    with urllib.request.urlopen(req, context=ssl_context(), timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def rotating_sample(items: list[str], limit: int, salt: str) -> list[str]:
    keyed = sorted(items, key=lambda item: hashlib.sha256(f"{salt}:{item}".encode("utf-8")).hexdigest())
    return keyed[:limit]


def discover_article_paths(base_url: str, path: str, lang: str, limit: int) -> list[str]:
    _, html = fetch(urljoin(base_url, path))
    hrefs = ARTICLE_LINK_RE.findall(html)
    base_host = urlparse(base_url).netloc
    paths: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        parsed = urlparse(urljoin(base_url, href))
        if parsed.netloc != base_host:
            continue
        candidate = parsed.path or "/"
        if candidate == "/" or candidate.startswith(SKIP_PREFIXES):
            continue
        if lang == "en":
            if not candidate.startswith("/en/"):
                continue
        else:
            if candidate.startswith("/en/"):
                continue
        if candidate in seen:
            continue
        seen.add(candidate)
        paths.append(candidate)
    salt = time.strftime("%Y%m%d")
    return rotating_sample(paths, limit, salt)


def extract_external_links(base_url: str, html: str) -> list[str]:
    base_host = urlparse(base_url).netloc
    links: list[str] = []
    seen: set[str] = set()
    for href in ARTICLE_LINK_RE.findall(html):
        parsed = urlparse(urljoin(base_url, href))
        if not parsed.scheme.startswith("http"):
            continue
        if parsed.netloc == base_host:
            continue
        normalized = parsed.geturl()
        if normalized in seen:
            continue
        seen.add(normalized)
        links.append(normalized)
    return links


def probe_source(url: str) -> tuple[str, str] | None:
    last_error = None
    for method, timeout_seconds in (("HEAD", 12), ("GET", 20)):
        try:
            req = urllib.request.Request(
                url,
                method=method,
                headers={"User-Agent": "nowpattern-article-source-audit/1.0"},
            )
            with urllib.request.urlopen(req, context=ssl_context(), timeout=timeout_seconds) as resp:
                if resp.status < 400:
                    return None
                last_error = f"HTTP {resp.status}"
        except Exception as exc:
            last_error = str(exc)
    if not last_error:
        return ("error", "unknown_error")
    if "HTTP Error 401" in last_error or "HTTP Error 403" in last_error or "HTTP Error 429" in last_error:
        return ("warning", last_error)
    return ("error", last_error)


def audit_article(base_url: str, path: str) -> ArticleAuditResult:
    url = urljoin(base_url, path)
    result = ArticleAuditResult(slug=path.strip("/"), url=url)
    try:
        status, html = fetch(url)
    except Exception as exc:
        result.fail(f"article_fetch_failed:{exc}")
        return result
    if status >= 400:
        result.fail(f"article_http_{status}")
        return result

    source_links = extract_external_links(base_url, html)
    result.source_count = len(source_links)
    if not source_links:
        result.fail("no_external_source_links")
        return result

    for source_url in source_links[:3]:
        result.checked_source_links.append(source_url)
        status = probe_source(source_url)
        if not status:
            continue
        level, detail = status
        if level == "warning":
            result.warnings.append(f"source_access_limited:{source_url} -> {detail}")
        else:
            result.fail(f"broken_source:{source_url} -> {detail}")
    return result


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Audit public article source links from the live site.")
    parser.add_argument("--base-url", default="https://nowpattern.com", help="Base public URL")
    parser.add_argument("--per-seed", type=int, default=4, help="How many articles to sample per language seed")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    results: list[dict[str, object]] = []
    failed = False
    for seed in SEEDS:
        article_paths = discover_article_paths(base_url, seed["path"], seed["lang"], args.per_seed)
        for path in article_paths:
            result = audit_article(base_url, path)
            results.append(asdict(result))
            if not result.ok:
                failed = True

    report = {
        "base_url": base_url.rstrip("/"),
        "generated_at_epoch": int(time.time()),
        "summary": {
            "total": len(results),
            "failed": sum(1 for item in results if not item["ok"]),
            "passed": sum(1 for item in results if item["ok"]),
        },
        "results": results,
    }

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False))
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    if failed:
        for item in results:
            if item["ok"]:
                continue
            print(f"FAIL {item['slug']}: {' | '.join(item['errors'])}")
        return 1
    print("PASS: article source audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
