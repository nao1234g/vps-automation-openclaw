#!/usr/bin/env python3
"""Externally audit public pages for broken Oracle/tracker anchor patterns."""

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


SEEDS = (
    {"slug": "home-ja", "path": "/"},
    {"slug": "home-en", "path": "/en/"},
    {"slug": "predictions-ja", "path": "/predictions/"},
    {"slug": "predictions-en", "path": "/en/predictions/"},
)

ARTICLE_PATH_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
BROKEN_PATTERNS = (
    re.compile(r"#np-vote-label-", re.IGNORECASE),
    re.compile(r"/predictions/#NP-2026-"),
    re.compile(r"/en/predictions/#NP-2026-"),
    re.compile(r"#NP-2026-"),
)
SKIP_PREFIXES = (
    "/tag/",
    "/author/",
    "/rss/",
    "/page/",
    "/taxonomy/",
    "/about/",
    "/members/",
    "/ghost/",
    "/assets/",
    "/public/",
    "/predictions/",
    "/en/predictions/",
    "/webmentions/",
)


@dataclass
class AnchorAuditResult:
    slug: str
    url: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

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
    req = urllib.request.Request(url, headers={"User-Agent": "nowpattern-anchor-audit/1.0"})
    with urllib.request.urlopen(req, context=ssl_context(), timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def rotating_sample(items: list[str], limit: int, salt: str) -> list[str]:
    keyed = sorted(items, key=lambda item: hashlib.sha256(f"{salt}:{item}".encode("utf-8")).hexdigest())
    return keyed[:limit]


def discover_article_paths(base_url: str, limit: int) -> list[str]:
    base_host = urlparse(base_url).netloc
    candidates: list[str] = []
    seen: set[str] = set()
    for seed in SEEDS[:2]:
        _, html = fetch(urljoin(base_url, seed["path"]))
        for href in ARTICLE_PATH_RE.findall(html):
            parsed = urlparse(urljoin(base_url, href))
            if parsed.netloc != base_host:
                continue
            path = parsed.path or "/"
            if path == "/" or path.startswith(SKIP_PREFIXES):
                continue
            if path in seen:
                continue
            seen.add(path)
            candidates.append(path)
    return rotating_sample(candidates, limit, time.strftime("%Y%m%d"))


def audit_page(base_url: str, path: str) -> AnchorAuditResult:
    url = urljoin(base_url, path)
    result = AnchorAuditResult(slug=path.strip("/") or "root", url=url)
    try:
        status, html = fetch(url)
    except Exception as exc:
        result.fail(f"fetch_failed:{exc}")
        return result
    if status >= 400:
        result.fail(f"http_{status}")
        return result
    for href in ARTICLE_PATH_RE.findall(html):
        for pattern in BROKEN_PATTERNS:
            match = pattern.search(href)
            if match:
                result.fail(f"broken_anchor_pattern:{match.group(0)}")
    return result


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Audit public pages for broken Oracle/tracker anchors.")
    parser.add_argument("--base-url", default="https://nowpattern.com", help="Base public URL")
    parser.add_argument("--article-sample", type=int, default=6, help="How many article pages to sample")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    pages = [seed["path"] for seed in SEEDS]
    pages.extend(discover_article_paths(base_url, args.article_sample))

    results = [asdict(audit_page(base_url, path)) for path in pages]
    failed = [item for item in results if not item["ok"]]
    report = {
        "base_url": base_url.rstrip("/"),
        "generated_at_epoch": int(time.time()),
        "summary": {
            "total": len(results),
            "failed": len(failed),
            "passed": len(results) - len(failed),
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
        for item in failed:
            print(f"FAIL {item['slug']}: {' | '.join(item['errors'])}")
        return 1
    print("PASS: article anchor integrity audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
