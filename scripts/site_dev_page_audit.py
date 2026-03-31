#!/usr/bin/env python3
"""Externally audit the public site for published dev/duplicate page URLs."""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.request
from pathlib import Path


DEV_PAGE_RE = re.compile(
    r"/(?:en/)?(?:predictions|taxonomy|about|members|integrity-audit)(?:-[0-9]+)+/",
    re.IGNORECASE,
)


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "nowpattern-dev-page-audit/1.0"})
    with urllib.request.urlopen(req, context=ssl_context(), timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Audit public sitemaps for dev page leaks.")
    parser.add_argument("--base-url", default="https://nowpattern.com", help="Base public URL")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    bodies = []
    for path in ("/sitemap.xml", "/sitemap-pages.xml"):
        try:
            bodies.append(fetch(base + path))
        except Exception:
            continue
    combined = "\n".join(bodies)
    matches = sorted(set(DEV_PAGE_RE.findall(combined)))
    report = {
        "base_url": base,
        "generated_at_epoch": int(time.time()),
        "summary": {
            "dev_pages_found": len(matches),
        },
        "matches": matches,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False))
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    if matches:
        for match in matches:
            print(f"FAIL dev_page_visible:{match}")
        return 1
    print("PASS: no published dev pages detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
