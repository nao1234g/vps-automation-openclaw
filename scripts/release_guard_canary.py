#!/usr/bin/env python3
"""Runtime canary for release/distribution blockers.

This intentionally feeds bad content into the shared release guard so that
"guard present" is not just a static token audit; it proves the blocker still
behaves correctly at runtime.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from article_release_guard import assert_release_ready, evaluate_release_blockers


def run_canary() -> dict[str, object]:
    checks: list[dict[str, object]] = []

    blocked_no_sources = evaluate_release_blockers(
        title="GPT-9 launch rewrites frontier AI competition",
        html="<article><p>OpenAI released GPT-9 today.</p><p>Sources</p></article>",
        source_urls=[],
        tags={"frontier-ai", "lang-en"},
        status="published",
        channel="public",
        require_external_sources=True,
    )
    checks.append(
        {
            "name": "frontier_claim_without_sources_blocked",
            "ok": (not blocked_no_sources["ok"]) and ("NO_EXTERNAL_SOURCES" in blocked_no_sources["errors"]),
            "errors": blocked_no_sources["errors"],
        }
    )

    blocked_unofficial = evaluate_release_blockers(
        title="GPT-9 launch changes everything",
        html="<article><p>OpenAI launched GPT-9.</p></article>",
        source_urls=["https://example.com/rumor"],
        tags={"frontier-ai", "lang-en"},
        status="published",
        channel="public",
        require_external_sources=True,
    )
    checks.append(
        {
            "name": "frontier_claim_without_vendor_source_blocked",
            "ok": (not blocked_unofficial["ok"]) and any(
                err.startswith("UNSUPPORTED_FRONTIER_RELEASE_CLAIM") for err in blocked_unofficial["errors"]
            ),
            "errors": blocked_unofficial["errors"],
        }
    )

    blocked_broken_source = evaluate_release_blockers(
        title="Analysis with broken source section",
        html='<article><a href="/about/">Source</a><p>Some analysis.</p></article>',
        source_urls=[],
        tags={"lang-en"},
        status="published",
        channel="public",
        require_external_sources=True,
    )
    checks.append(
        {
            "name": "broken_source_section_blocked",
            "ok": (not blocked_broken_source["ok"]) and ("BROKEN_SOURCE_SECTION" in blocked_broken_source["errors"]),
            "errors": blocked_broken_source["errors"],
        }
    )

    blocked_high_risk = evaluate_release_blockers(
        title="Iran conflict escalates after missile strikes",
        html="<article><p>War risk rises.</p></article>",
        source_urls=["https://www.reuters.com/world/middle-east/sample"],
        tags={"war", "lang-en"},
        status="published",
        channel="distribution",
        require_external_sources=True,
    )
    checks.append(
        {
            "name": "high_risk_article_requires_human_approval",
            "ok": (not blocked_high_risk["ok"]) and any(
                err.startswith("HUMAN_APPROVAL_REQUIRED:") for err in blocked_high_risk["errors"]
            ),
            "errors": blocked_high_risk["errors"],
        }
    )

    allowed_high_risk = evaluate_release_blockers(
        title="Iran conflict escalates after missile strikes",
        html="<article><p>War risk rises.</p></article>",
        source_urls=["https://www.reuters.com/world/middle-east/sample"],
        tags={"war", "lang-en", "human-approved"},
        status="published",
        channel="distribution",
        require_external_sources=True,
    )
    checks.append(
        {
            "name": "high_risk_article_with_human_approval_can_pass",
            "ok": allowed_high_risk["ok"] and not allowed_high_risk["errors"],
            "errors": allowed_high_risk["errors"],
        }
    )

    assert_ready_ok = True
    assert_ready_error = ""
    try:
        assert_release_ready(
            title="Claude 7 release announced",
            html="<article><p>Anthropic launched Claude 7 today.</p></article>",
            source_urls=["https://example.com/rumor"],
            tags={"frontier-ai", "lang-en"},
            status="published",
            channel="public",
            require_external_sources=True,
        )
        assert_ready_ok = False
        assert_ready_error = "assert_release_ready allowed invalid frontier claim"
    except ValueError as exc:
        assert_ready_error = str(exc)
    checks.append(
        {
            "name": "assert_release_ready_raises_on_invalid_frontier_claim",
            "ok": assert_ready_ok,
            "errors": [assert_ready_error] if assert_ready_error else [],
        }
    )

    failed = [check for check in checks if not check["ok"]]
    return {
        "total": len(checks),
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtime canary for the shared release guard.")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    report = run_canary()
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
