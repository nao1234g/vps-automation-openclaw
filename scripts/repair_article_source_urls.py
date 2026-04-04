#!/usr/bin/env python3
"""Audit and repair known broken external source URLs inside published Ghost posts."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


DEFAULT_GHOST_DB = Path("/var/www/nowpattern/content/data/ghost.db")
FIELDS_TO_SCAN = ("html", "codeinjection_head", "codeinjection_foot")
BROKEN_EXACT_MAP = {
    "https://www.iea.org/reports/oil-market-report": "https://www.iea.org/about/oil-security-and-emergency-response/strait-of-hormuz",
}


@dataclass
class SourceRepairIssue:
    source_id: str
    source_slug: str
    field: str
    original_url: str
    replacement_url: str
    reason: str


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def is_external_url(url: str) -> bool:
    parsed = urlparse(url)
    if not parsed.scheme.startswith("http"):
        return False
    host = (parsed.netloc or "").lower()
    return bool(host) and host not in {"nowpattern.com", "www.nowpattern.com"}


def strip_nowpattern_ref(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    filtered = [
        (key, value)
        for key, value in query
        if not (key.lower() == "ref" and value.strip().lower() == "nowpattern.com")
    ]
    if filtered == query:
        return url
    return urlunparse(parsed._replace(query=urlencode(filtered, doseq=True)))


def canonicalize_external_url(url: str) -> tuple[str, str | None]:
    if not is_external_url(url):
        return url, None
    cleaned = strip_nowpattern_ref(url)
    reason = "strip_ref_param" if cleaned != url else None
    replacement = BROKEN_EXACT_MAP.get(cleaned)
    if replacement:
        return replacement, "known_broken_source"
    return cleaned, reason


def discover_issues(cur: sqlite3.Cursor) -> list[SourceRepairIssue]:
    issues: list[SourceRepairIssue] = []
    rows = cur.execute(
        """
        SELECT id, slug, html, codeinjection_head, codeinjection_foot
        FROM posts
        WHERE status = 'published'
        ORDER BY published_at DESC, created_at DESC
        """
    ).fetchall()
    for row in rows:
        source_id = str(row[0])
        source_slug = str(row[1])
        field_values = dict(zip(FIELDS_TO_SCAN, row[2:5], strict=True))
        for field_name, value in field_values.items():
            if not value:
                continue
            text = str(value)
            seen: set[tuple[str, str]] = set()
            start = 0
            marker = 'href="'
            while True:
                idx = text.find(marker, start)
                if idx == -1:
                    break
                url_start = idx + len(marker)
                url_end = text.find('"', url_start)
                if url_end == -1:
                    break
                original_url = text[url_start:url_end]
                start = url_end + 1
                replacement_url, reason = canonicalize_external_url(original_url)
                if not reason or replacement_url == original_url:
                    continue
                key = (field_name, original_url)
                if key in seen:
                    continue
                seen.add(key)
                issues.append(
                    SourceRepairIssue(
                        source_id=source_id,
                        source_slug=source_slug,
                        field=field_name,
                        original_url=original_url,
                        replacement_url=replacement_url,
                        reason=reason,
                    )
                )
    return issues


def apply_repairs(cur: sqlite3.Cursor, issues: list[SourceRepairIssue]) -> int:
    grouped: dict[tuple[str, str], list[SourceRepairIssue]] = {}
    for issue in issues:
        grouped.setdefault((issue.source_id, issue.field), []).append(issue)

    repaired = 0
    for (source_id, field_name), field_issues in grouped.items():
        row = cur.execute(f"SELECT {field_name} FROM posts WHERE id = ?", (source_id,)).fetchone()
        if not row or row[0] is None:
            continue
        content = str(row[0])
        original = content
        for issue in field_issues:
            content = content.replace(issue.original_url, issue.replacement_url)
        if content != original:
            cur.execute(f"UPDATE posts SET {field_name} = ? WHERE id = ?", (content, source_id))
            repaired += 1
    return repaired


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Repair known broken external source URLs in published Ghost posts.")
    parser.add_argument("--db", default=str(DEFAULT_GHOST_DB), help="Path to ghost.db")
    parser.add_argument("--audit-only", action="store_true", help="Only report issues and exit non-zero if any remain")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise FileNotFoundError(f"ghost db not found: {db_path}")

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    before = discover_issues(cur)
    repaired = 0
    if not args.audit_only:
        repaired = apply_repairs(cur, before)
        if repaired:
            con.commit()
    after = discover_issues(cur)
    con.close()

    report = {
        "db": str(db_path),
        "issues_before": len(before),
        "repaired": repaired,
        "issues_after": len(after),
        "samples_before": [asdict(issue) for issue in before[:20]],
        "samples_after": [asdict(issue) for issue in after[:20]],
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if len(after) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
