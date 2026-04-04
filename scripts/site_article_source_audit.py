#!/usr/bin/env python3
"""Externally audit public article pages for reachable source links."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

from public_article_rotation import (
    LINK_RE,
    discover_article_paths,
    fetch,
    load_state,
    pick_batch,
    save_state,
    ssl_context,
)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
LOCAL_REPORT_DIR = REPO_ROOT / "reports" / "site_guard"
DEFAULT_STATE_PATH = LOCAL_REPORT_DIR / "site_article_source_state.json"
ARTICLE_SCOPE_RE = re.compile(r"<article\b.*?</article>", re.IGNORECASE | re.DOTALL)


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


def extract_external_links(base_url: str, html: str) -> list[str]:
    base_host = urlparse(base_url).netloc
    links: list[str] = []
    seen: set[str] = set()
    for href in LINK_RE.findall(html):
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


def extract_article_scope(html: str) -> str:
    match = ARTICLE_SCOPE_RE.search(html)
    if match:
        return match.group(0)
    return html


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


def is_stale_article_result(result: ArticleAuditResult) -> bool:
    if result.ok:
        return False
    errors = " | ".join(result.errors)
    return any(
        marker in errors
        for marker in (
            "article_fetch_failed:HTTP Error 404",
            "article_fetch_failed:HTTP Error 410",
            "article_http_404",
            "article_http_410",
        )
    )


def audit_article(base_url: str, path: str) -> ArticleAuditResult:
    url = urljoin(base_url, path)
    result = ArticleAuditResult(slug=path.strip("/"), url=url)
    try:
        status, html = fetch(base_url, path)
    except Exception as exc:
        result.fail(f"article_fetch_failed:{exc}")
        return result
    if status >= 400:
        result.fail(f"article_http_{status}")
        return result

    source_links = extract_external_links(base_url, extract_article_scope(html))
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
    parser.add_argument("--discover-limit", type=int, default=120, help="How many known article pages to expand")
    parser.add_argument("--check-limit", type=int, default=12, help="How many article pages to verify this run")
    parser.add_argument("--full-scan", action="store_true", help="Ignore rotation state and verify every discovered article this run")
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH), help="State file path")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    state_path = Path(args.state_path)
    state = load_state(state_path)
    known_paths = [path for path in state.get("known_paths", []) if isinstance(path, str)]
    cursor = int(state.get("cursor", 0) or 0)
    known_paths = discover_article_paths(base_url, known_paths, args.discover_limit)
    if args.full_scan:
        batch = known_paths
        next_cursor = 0
    else:
        batch, next_cursor = pick_batch(known_paths, cursor, args.check_limit)

    results: list[dict[str, object]] = []
    failed = False
    pruned_stale_paths: list[str] = []
    for path in batch:
        result = audit_article(base_url, path)
        if is_stale_article_result(result):
            pruned_stale_paths.append(path)
            continue
        results.append(asdict(result))
        if not result.ok:
            failed = True

    if pruned_stale_paths:
        stale = set(pruned_stale_paths)
        known_paths = [path for path in known_paths if path not in stale]
        next_cursor = 0 if not known_paths else next_cursor % len(known_paths)

    state.update(
        {
            "known_paths": known_paths,
            "cursor": next_cursor,
            "last_generated_at_epoch": int(time.time()),
            "last_checked_batch": batch,
            "last_pruned_stale_paths": pruned_stale_paths,
        }
    )
    save_state(state_path, state)

    report = {
        "base_url": base_url.rstrip("/"),
        "generated_at_epoch": int(time.time()),
        "discover_limit": args.discover_limit,
        "check_limit": args.check_limit,
        "full_scan": args.full_scan,
        "known_paths_total": len(known_paths),
        "cursor_start": cursor,
        "cursor_end": next_cursor,
        "summary": {
            "total": len(results),
            "failed": sum(1 for item in results if not item["ok"]),
            "passed": sum(1 for item in results if item["ok"]),
            "pruned_stale_paths": len(pruned_stale_paths),
        },
        "pruned_stale_paths": pruned_stale_paths,
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
