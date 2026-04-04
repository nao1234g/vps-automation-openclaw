#!/usr/bin/env python3
"""Run the core governance audits that keep the agent ecosystem centrally controlled."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from mission_contract import assert_mission_handshake

SCRIPT_DIR = Path(__file__).resolve().parent
MISSION_HANDSHAKE = assert_mission_handshake(
    "ecosystem_governance_audit",
    "audit that all active ecosystem controls remain aligned with the shared founder mission contract",
)

BASE_AUDITS = [
    ("mission_contract", [sys.executable, str(SCRIPT_DIR / "mission_contract_audit.py")]),
    ("lexicon_contract", [sys.executable, str(SCRIPT_DIR / "lexicon_contract_audit.py")]),
    ("change_freeze_contract", [sys.executable, str(SCRIPT_DIR / "test_change_freeze_guard.py")]),
    ("credibility_budget_contract", [sys.executable, str(SCRIPT_DIR / "test_credibility_budget_guard.py")]),
    ("one_pass_completion_contract", [sys.executable, str(SCRIPT_DIR / "test_one_pass_completion_gate.py")]),
    ("publish_path_guard", [sys.executable, str(SCRIPT_DIR / "publish_path_guard_audit.py")]),
    ("ghost_write_surface", [sys.executable, str(SCRIPT_DIR / "ghost_write_surface_audit.py")]),
    ("release_guard_canary", [sys.executable, str(SCRIPT_DIR / "release_guard_canary.py")]),
    (
        "article_anchor_integrity",
        [
            sys.executable,
            str(SCRIPT_DIR / "article_anchor_integrity_audit.py"),
            "--base-url",
            "https://nowpattern.com",
            "--discover-limit",
            "160",
            "--check-limit",
            "24",
        ],
    ),
    (
        "site_dev_pages",
        [sys.executable, str(SCRIPT_DIR / "site_dev_page_audit.py"), "--base-url", "https://nowpattern.com"],
    ),
    (
        "stateful_user_journey",
        [
            sys.executable,
            str(SCRIPT_DIR / "stateful_user_journey_audit.py"),
            "--base-url",
            "https://nowpattern.com",
        ],
    ),
    (
        "article_source_repairs",
        [
            sys.executable,
            str(SCRIPT_DIR / "repair_article_source_urls.py"),
            "--audit-only",
        ],
    ),
    (
        "cross_language_article_links",
        [
            sys.executable,
            str(SCRIPT_DIR / "repair_cross_language_article_links.py"),
            "--audit-only",
        ],
    ),
    (
        "site_article_source",
        [
            sys.executable,
            str(SCRIPT_DIR / "site_article_source_audit.py"),
            "--base-url",
            "https://nowpattern.com",
            "--discover-limit",
            "160",
            "--check-limit",
            "18",
        ],
    ),
    (
        "ghost_author_integrity",
        [
            sys.executable,
            str(SCRIPT_DIR / "repair_ghost_post_authors.py"),
            "--audit-only",
        ],
    ),
    (
        "draft_link_integrity",
        [
            sys.executable,
            str(SCRIPT_DIR / "repair_internal_draft_links.py"),
            "--audit-only",
        ],
    ),
    (
        "site_link_crawler",
        [
            sys.executable,
            str(SCRIPT_DIR / "site_link_crawler.py"),
            "--base-url",
            "https://nowpattern.com",
            "--check-limit",
            "60",
            "--discover-limit",
            "140",
        ],
    ),
    (
        "synthetic_user_freshness",
        [
            sys.executable,
            str(SCRIPT_DIR / "synthetic_user_freshness_audit.py"),
        ],
    ),
]


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_audit(name: str, command: list[str]) -> dict[str, object]:
    proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part).strip()
    parsed = None
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except Exception:
            parsed = None
    return {
        "name": name,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "output": output,
        "json": parsed,
    }


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Run the core ecosystem governance audits.")
    parser.add_argument("--json-out", help="Optional JSON report path")
    parser.add_argument(
        "--include-full-crawl",
        action="store_true",
        help="Include the exhaustive synthetic-user crawl in this run",
    )
    args = parser.parse_args()

    audits = list(BASE_AUDITS)
    if shutil.which("crontab"):
        audits.append(("cron_governance", [sys.executable, str(SCRIPT_DIR / "cron_governance_audit.py")]))
    if args.include_full_crawl:
        full_crawl_audit = (
            "synthetic_user_crawler",
            [
                sys.executable,
                str(SCRIPT_DIR / "synthetic_user_crawler.py"),
                "--base-url",
                "https://nowpattern.com",
            ],
        )
        freshness_index = next(
            (idx for idx, (name, _) in enumerate(audits) if name == "synthetic_user_freshness"),
            None,
        )
        if freshness_index is None:
            audits.append(full_crawl_audit)
        else:
            audits.insert(freshness_index, full_crawl_audit)

    results = [run_audit(name, command) for name, command in audits]
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_epoch": int(time.time()),
        "total": len(results),
        "failed": sum(1 for item in results if not item["ok"]),
        "results": results,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
