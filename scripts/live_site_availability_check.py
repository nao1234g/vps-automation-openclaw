#!/usr/bin/env python3
"""External-facing availability probe for the public Nowpattern site."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin


ENDPOINTS = [
    {"slug": "home-ja", "path": "/", "expected_status": 200, "kind": "html", "expected_lang": "ja"},
    {"slug": "home-en", "path": "/en/", "expected_status": 200, "kind": "html", "expected_lang": "en"},
    {"slug": "predictions-ja", "path": "/predictions/", "expected_status": 200, "kind": "html", "expected_lang": "ja"},
    {"slug": "predictions-en", "path": "/en/predictions/", "expected_status": 200, "kind": "html", "expected_lang": "en"},
    {"slug": "reader-api-health", "path": "/reader-predict/health", "expected_status": 200, "kind": "json"},
]


@dataclass
class ProbeResult:
    slug: str
    url: str
    status: int = 0
    ok: bool = True
    elapsed_ms: int = 0
    final_url: str = ""
    content_type: str = ""
    errors: list[str] | None = None
    warnings: list[str] | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    return ctx


def probe_endpoint(base_url: str, endpoint: dict[str, Any], timeout_seconds: int, slow_ms: int, critical_ms: int) -> ProbeResult:
    url = urljoin(base_url, endpoint["path"])
    result = ProbeResult(slug=endpoint["slug"], url=url)
    started = time.perf_counter()
    try:
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "nowpattern-live-site-guard/1.0"},
        )
        with urllib.request.urlopen(request, context=ssl_context(), timeout=timeout_seconds) as response:
            body = response.read(8192)
            result.status = response.status
            result.final_url = response.geturl()
            result.content_type = response.headers.get("content-type", "")

            if response.status != endpoint["expected_status"]:
                result.fail(f"unexpected HTTP {response.status}")

            if endpoint["kind"] == "html":
                text = body.decode("utf-8", errors="replace").lower()
                expected_lang = endpoint.get("expected_lang")
                if expected_lang and f'lang="{expected_lang}"' not in text and f"lang='{expected_lang}'" not in text:
                    result.fail(f"missing html lang={expected_lang}")
                if "page not found" in text and "404" in text:
                    result.fail("404 template rendered")
            elif endpoint["kind"] == "json":
                text = body.decode("utf-8", errors="replace").lower()
                if '"status"' not in text and "ok" not in text:
                    result.fail("unexpected health payload")

    except urllib.error.HTTPError as exc:
        result.status = exc.code
        result.final_url = getattr(exc, "url", url)
        result.fail(f"HTTPError {exc.code}")
    except Exception as exc:
        result.fail(str(exc))
    finally:
        result.elapsed_ms = int((time.perf_counter() - started) * 1000)

    if result.elapsed_ms > critical_ms:
        result.fail(f"critical latency {result.elapsed_ms}ms > {critical_ms}ms")
    elif result.elapsed_ms > slow_ms:
        result.warnings.append(f"slow response {result.elapsed_ms}ms > {slow_ms}ms")

    return result


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Check public site availability and latency budgets.")
    parser.add_argument("--base-url", default="https://nowpattern.com", help="Base public URL")
    parser.add_argument(
        "--slugs",
        help="Optional comma-separated subset of endpoint slugs to probe, e.g. home-ja,reader-api-health",
    )
    parser.add_argument("--timeout-seconds", type=int, default=12, help="Per-request timeout in seconds")
    parser.add_argument("--slow-ms", type=int, default=4000, help="Warn when request exceeds this latency")
    parser.add_argument("--critical-ms", type=int, default=12000, help="Fail when request exceeds this latency")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    selected = None
    if args.slugs:
        selected = {slug.strip() for slug in args.slugs.split(",") if slug.strip()}
    report: dict[str, Any] = {
        "base_url": base_url.rstrip("/"),
        "generated_at_epoch": int(time.time()),
        "results": [],
        "summary": {},
    }

    failed = False
    endpoints = [endpoint for endpoint in ENDPOINTS if not selected or endpoint["slug"] in selected]
    if not endpoints:
        raise SystemExit("No endpoints selected.")

    for endpoint in endpoints:
        result = probe_endpoint(base_url, endpoint, args.timeout_seconds, args.slow_ms, args.critical_ms)
        report["results"].append(asdict(result))
        if not result.ok:
            failed = True

    warnings = sum(len(item["warnings"]) for item in report["results"])
    report["summary"] = {
        "total": len(report["results"]),
        "failed": sum(1 for item in report["results"] if not item["ok"]),
        "warnings": warnings,
        "service_green": not failed,
    }

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False))
    if failed:
        for item in report["results"]:
            if item["ok"]:
                continue
            details = " | ".join(item["errors"]) if item["errors"] else "failed"
            print(f"FAIL {item['slug']}: {details}")
        return 1

    print("PASS: live site availability")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
