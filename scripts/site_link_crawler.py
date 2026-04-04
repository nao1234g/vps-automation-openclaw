#!/usr/bin/env python3
"""Crawl public internal pages in rotating batches to catch deep broken links."""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.request
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse


SEEDS = (
    "/",
    "/en/",
    "/predictions/",
    "/en/predictions/",
    "/about/",
    "/en/about/",
    "/integrity-audit/",
    "/en/integrity-audit/",
    "/forecasting-methodology/",
    "/en/forecasting-methodology/",
    "/forecast-scoring-and-resolution/",
    "/en/forecast-scoring-and-resolution/",
    "/forecast-integrity-and-audit/",
    "/en/forecast-integrity-and-audit/",
)

SKIP_PREFIXES = (
    "/ghost/",
    "/assets/",
    "/public/",
    "/author/",
    "/tag/",
    "/rss/",
    "/webmentions/",
    "/members/",
)

HIDDEN_PATH_PREFIXES = (
    "/p/",
    "/preview/",
)

LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
BODY_404_PATTERNS = (
    "404 — Page not found",
    "404 - Page not found",
    "This page could not be found",
    "Page not found",
)
STALE_ATTR_PATTERNS = (
    re.compile(r'''(?:href|src|content)=["'](?:https?://(?:www\.)?nowpattern\.com)?/en/en-[^"']*["']''', re.IGNORECASE),
    re.compile(r'''href=["']\+["']''', re.IGNORECASE),
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
LOCAL_REPORT_DIR = REPO_ROOT / "reports" / "site_guard"
DEFAULT_STATE_PATH = LOCAL_REPORT_DIR / "site_link_crawler_state.json"
TRANSIENT_FETCH_TOKENS = (
    "timed out",
    "time-out",
    "handshake operation timed out",
    "read operation timed out",
    "temporarily unavailable",
    "connection reset",
    "connection aborted",
)


@dataclass
class CrawlResult:
    path: str
    url: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    discovered_links: int = 0

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
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nowpattern-site-link-crawler/1.0"})
            with urllib.request.urlopen(req, context=ssl_context(), timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            last_exc = exc
            if attempt >= 2:
                raise
            if not any(token in str(exc).lower() for token in TRANSIENT_FETCH_TOKENS):
                raise
            time.sleep(1 + attempt)
    raise last_exc if last_exc else RuntimeError("fetch_failed_without_exception")


def normalize_internal_path(base_url: str, href: str) -> str | None:
    parsed = urlparse(urljoin(base_url, href))
    base_host = urlparse(base_url).netloc
    if parsed.scheme and parsed.netloc and parsed.netloc != base_host:
        return None
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path
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
        if not isinstance(data.get("known_paths"), list):
            data["known_paths"] = list(SEEDS)
        if not isinstance(data.get("cursor"), int):
            data["cursor"] = 0
        return data
    except Exception:
        return {"known_paths": list(SEEDS), "cursor": 0}


def save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def discover_paths(base_url: str, discover_limit: int) -> list[str]:
    seen = set(SEEDS)
    queue: deque[str] = deque(SEEDS)
    fetched = 0
    while queue and fetched < discover_limit:
        path = queue.popleft()
        url = urljoin(base_url, path)
        try:
            status, html = fetch(url)
        except Exception:
            fetched += 1
            continue
        fetched += 1
        if status >= 400:
            continue
        for href in LINK_RE.findall(html):
            candidate = normalize_internal_path(base_url, href)
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            queue.append(candidate)
    return list(seen)


def pick_batch(known_paths: list[str], cursor: int, check_limit: int) -> tuple[list[str], int]:
    if not known_paths:
        return [], 0
    total = len(known_paths)
    batch: list[str] = []
    for offset in range(min(check_limit, total)):
        batch.append(known_paths[(cursor + offset) % total])
    next_cursor = (cursor + len(batch)) % total
    return batch, next_cursor


def audit_page(base_url: str, path: str) -> CrawlResult:
    url = urljoin(base_url, path)
    result = CrawlResult(path=path, url=url)
    try:
        status, html = fetch(url)
    except Exception as exc:
        result.fail(f"fetch_failed:{exc}")
        return result
    if status >= 400:
        result.fail(f"http_{status}")
        return result
    if any(pattern in html for pattern in BODY_404_PATTERNS):
        result.fail("soft_404_body_detected")
    for stale in STALE_ATTR_PATTERNS:
        if stale.search(html):
            result.fail(f"stale_pattern:{stale.pattern}")
    discovered = 0
    for href in LINK_RE.findall(html):
        if normalize_internal_path(base_url, href):
            discovered += 1
    result.discovered_links = discovered
    return result


def is_prunable_stale_failure(result: CrawlResult, current_paths: set[str]) -> bool:
    if result.path in current_paths:
        return False
    if not result.errors:
        return False
    return any(error.startswith("http_404") or "HTTP Error 404" in error for error in result.errors)


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Crawl public internal pages in rotating batches.")
    parser.add_argument("--base-url", default="https://nowpattern.com", help="Base public URL")
    parser.add_argument("--discover-limit", type=int, default=80, help="Maximum pages to expand while discovering")
    parser.add_argument("--check-limit", type=int, default=40, help="How many known URLs to verify this run")
    parser.add_argument("--full-scan", action="store_true", help="Ignore rotation state and verify every discovered URL this run")
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH), help="State file path")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    state_path = Path(args.state_path)
    state = load_state(state_path)
    known_paths = [path for path in state.get("known_paths", []) if isinstance(path, str)] or list(SEEDS)
    cursor = int(state.get("cursor", 0) or 0)
    last_seen = {
        path: int(epoch)
        for path, epoch in (state.get("last_seen_epoch") or {}).items()
        if isinstance(path, str) and isinstance(epoch, int)
    }

    for seed in SEEDS:
        if seed not in known_paths:
            known_paths.insert(0, seed)

    current_paths = set(discover_paths(base_url, args.discover_limit))
    now_epoch = int(time.time())
    for path in current_paths:
        last_seen[path] = now_epoch
    merged_paths = list(dict.fromkeys(list(SEEDS) + list(known_paths) + sorted(current_paths)))
    if args.full_scan:
        batch = merged_paths
        next_cursor = 0
    else:
        batch, next_cursor = pick_batch(merged_paths, cursor, args.check_limit)

    results: list[dict[str, object]] = []
    pruned_paths: list[str] = []
    for path in batch:
        result = audit_page(base_url, path)
        if is_prunable_stale_failure(result, current_paths):
            pruned_paths.append(path)
            continue
        results.append(asdict(result))

    known_paths = [path for path in merged_paths if path not in pruned_paths]
    for path in pruned_paths:
        last_seen.pop(path, None)
    failed = [item for item in results if not item["ok"]]

    state.update(
        {
            "known_paths": known_paths,
            "cursor": next_cursor,
            "last_seen_epoch": last_seen,
            "last_generated_at_epoch": now_epoch,
            "last_checked_batch": batch,
            "last_pruned_paths": pruned_paths,
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
        "current_paths_total": len(current_paths),
        "checked_paths_total": len(results),
        "cursor_start": cursor,
        "cursor_end": next_cursor,
        "pruned_paths_total": len(pruned_paths),
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
            print(f"FAIL {item['path']}: {' | '.join(item['errors'])}")
        return 1
    print("PASS: site link crawler")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
