#!/usr/bin/env python3
"""Externally audit public pages for broken Oracle/tracker anchor patterns."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urljoin

from public_article_rotation import (
    LINK_RE,
    discover_article_paths,
    fetch,
    load_state,
    pick_batch,
    save_state,
)


SEEDS = (
    {"slug": "home-ja", "path": "/"},
    {"slug": "home-en", "path": "/en/"},
    {"slug": "predictions-ja", "path": "/predictions/"},
    {"slug": "predictions-en", "path": "/en/predictions/"},
)

BROKEN_PATTERNS = (
    re.compile(r"#np-vote-label-", re.IGNORECASE),
    re.compile(r"/predictions/#NP-2026-"),
    re.compile(r"/en/predictions/#NP-2026-"),
    re.compile(r"#NP-2026-"),
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
LOCAL_REPORT_DIR = REPO_ROOT / "reports" / "site_guard"
DEFAULT_STATE_PATH = LOCAL_REPORT_DIR / "article_anchor_integrity_state.json"


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


def audit_page(base_url: str, path: str) -> AnchorAuditResult:
    url = urljoin(base_url, path)
    result = AnchorAuditResult(slug=path.strip("/") or "root", url=url)
    try:
        status, html = fetch(base_url, path)
    except Exception as exc:
        result.fail(f"fetch_failed:{exc}")
        return result
    if status >= 400:
        result.fail(f"http_{status}")
        return result
    for href in LINK_RE.findall(html):
        for pattern in BROKEN_PATTERNS:
            match = pattern.search(href)
            if match:
                result.fail(f"broken_anchor_pattern:{match.group(0)}")
    return result


def is_stale_article_result(result: AnchorAuditResult) -> bool:
    if result.ok:
        return False
    errors = " | ".join(result.errors)
    return any(
        marker in errors
        for marker in (
            "fetch_failed:HTTP Error 404",
            "fetch_failed:HTTP Error 410",
            "http_404",
            "http_410",
        )
    )


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Audit public pages for broken Oracle/tracker anchors.")
    parser.add_argument("--base-url", default="https://nowpattern.com", help="Base public URL")
    parser.add_argument("--discover-limit", type=int, default=120, help="How many article pages to discover")
    parser.add_argument("--check-limit", type=int, default=18, help="How many article pages to verify this run")
    parser.add_argument("--full-scan", action="store_true", help="Ignore rotation state and verify every discovered article this run")
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH), help="State file path")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    pages = [seed["path"] for seed in SEEDS]
    state_path = Path(args.state_path)
    state = load_state(state_path)
    known_paths = [path for path in state.get("known_paths", []) if isinstance(path, str)]
    cursor = int(state.get("cursor", 0) or 0)
    known_paths = discover_article_paths(base_url, known_paths, args.discover_limit)
    article_candidates = [path for path in known_paths if path not in pages]
    if args.full_scan:
        article_batch = article_candidates
        next_cursor = 0
    else:
        article_batch, next_cursor = pick_batch(
            article_candidates,
            cursor,
            args.check_limit,
        )
    pages.extend(article_batch)

    results: list[dict[str, object]] = []
    failed: list[dict[str, object]] = []
    pruned_stale_paths: list[str] = []
    for path in pages:
        result = audit_page(base_url, path)
        if path not in pages[: len(SEEDS)] and is_stale_article_result(result):
            pruned_stale_paths.append(path)
            continue
        result_payload = asdict(result)
        results.append(result_payload)
        if not result.ok:
            failed.append(result_payload)

    if pruned_stale_paths:
        stale = set(pruned_stale_paths)
        known_paths = [path for path in known_paths if path not in stale]
        next_cursor = 0 if not known_paths else next_cursor % len(known_paths)
    state.update(
        {
            "known_paths": known_paths,
            "cursor": next_cursor,
            "last_generated_at_epoch": int(time.time()),
            "last_checked_batch": article_batch,
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
            "failed": len(failed),
            "passed": len(results) - len(failed),
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
        for item in failed:
            print(f"FAIL {item['slug']}: {' | '.join(item['errors'])}")
        return 1
    print("PASS: article anchor integrity audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
