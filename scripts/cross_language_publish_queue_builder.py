#!/usr/bin/env python3
"""Cross-language publish queue builder.

Builds an actionable translation/publish queue for cross_language_only
articles: predictions where the DB has EN article_links registered but
the EN Ghost article does not yet exist.

For each entry, extracts the JA source article metadata from Ghost and
the expected EN slug from prediction_db, producing a queue that can feed
into the nowpattern_publisher pipeline.

Output:
  - reports/cross_language_publish_queue.json
  - reports/cross_language_publish_queue.md
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from runtime_boundary import shared_or_local_path
from prediction_release_contract import (
    build_prediction_article_links_index,
    load_prediction_db,
    PREDICTION_DB_DEFAULT,
)
from ghost_post_loader import (
    GHOST_DB_DEFAULT,
    load_ghost_posts,
    split_by_status,
)

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_REPORT_DIR = shared_or_local_path(
    script_file=__file__,
    shared_path="/opt/shared/reports",
    local_path=_REPO_ROOT / "reports",
)

# ---------------------------------------------------------------------------
# Audit loader
# ---------------------------------------------------------------------------

_AUDIT_JSON = shared_or_local_path(
    script_file=__file__,
    shared_path="/opt/shared/reports/cross_language_only_audit.json",
    local_path=_REPO_ROOT / "reports" / "cross_language_only_audit.json",
)


def _load_audit(audit_path: str | Path = _AUDIT_JSON) -> list[dict[str, Any]]:
    """Load the cross_language_only_audit.json and return the audits list."""
    path = Path(audit_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Audit file not found: {path}\n"
            "Run cross_language_only_audit.py first."
        )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("audits", [])


# ---------------------------------------------------------------------------
# Queue builder
# ---------------------------------------------------------------------------


def build_publish_queue(
    ghost_db_path: str = GHOST_DB_DEFAULT,
    prediction_db_path: str = PREDICTION_DB_DEFAULT,
    audit_path: str | Path = _AUDIT_JSON,
) -> dict[str, Any]:
    """Build the cross-language publish queue.

    For each cross_language_only audit entry (JA articles needing EN
    translation), extract JA source metadata from Ghost and EN target
    metadata from prediction_db.
    """
    # Load audit entries
    audits = _load_audit(audit_path)
    if not audits:
        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_items": 0,
            "queue": [],
        }

    # Load Ghost posts
    all_posts = load_ghost_posts(ghost_db_path, compute_oracle=True)
    published, _draft = split_by_status(all_posts)

    # Load prediction_db indexes
    pred_db = load_prediction_db(prediction_db_path)
    pid_to_links = build_prediction_article_links_index(pred_db)

    # Build queue entries
    queue: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for audit in audits:
        ja_slug = audit["slug"]
        pid = audit["prediction_id"]
        db_sibling_slug = audit.get("db_sibling_slug", "")
        db_sibling_url = audit.get("db_sibling_url", "")

        # Only process JA → EN translation cases
        if audit.get("article_lang") != "ja" or audit.get("target_lang") != "en":
            skipped.append({
                "slug": ja_slug,
                "reason": f"Not JA→EN (article_lang={audit.get('article_lang')}, target_lang={audit.get('target_lang')})",
            })
            continue

        # Look up the JA source article in Ghost
        ja_post = published.get(ja_slug)
        if not ja_post:
            skipped.append({
                "slug": ja_slug,
                "reason": "JA source article not found in Ghost published posts",
            })
            continue

        # Extract expected EN slug and URL from prediction_db
        expected_en_slug = db_sibling_slug
        expected_en_url = db_sibling_url

        # If audit didn't have the info, fall back to prediction_db lookup
        if not expected_en_slug and pid:
            for link in pid_to_links.get(pid, []):
                if link.get("lang") == "en":
                    expected_en_slug = link.get("slug", "")
                    expected_en_url = link.get("url", "")
                    break

        if not expected_en_slug:
            skipped.append({
                "slug": ja_slug,
                "reason": "No EN slug found in prediction_db article_links",
            })
            continue

        # Build the queue entry
        queue.append({
            "prediction_id": pid,
            "ja_slug": ja_slug,
            "ja_title": ja_post["title"],
            "expected_en_slug": expected_en_slug,
            "expected_en_url": expected_en_url,
            "source_html_length": len(ja_post.get("html") or ""),
            "status": "ready_for_translation",
        })

    # Sort by prediction_id for stable ordering
    queue.sort(key=lambda x: x["prediction_id"])

    result: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_items": len(queue),
        "queue": queue,
    }
    if skipped:
        result["skipped"] = skipped

    return result


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------


def write_publish_queue_report(
    result: dict[str, Any],
    report_dir: str | Path = _REPORT_DIR,
) -> tuple[str, str]:
    """Write JSON and Markdown reports."""
    report_dir = Path(report_dir)
    os.makedirs(report_dir, exist_ok=True)

    json_path = str(report_dir / "cross_language_publish_queue.json")
    md_path = str(report_dir / "cross_language_publish_queue.md")

    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Markdown
    lines = [
        "# Cross-Language Publish Queue",
        "",
        f"生成日時: {result['generated_at']}",
        f"翻訳・公開対象: **{result['total_items']}件**",
        "",
        "## 概要",
        "",
        "prediction_dbにEN article_linksが登録済みだが、Ghost記事が未作成の10件。",
        "すべてJA記事 → EN翻訳が必要。",
        "",
        "## キュー一覧",
        "",
        "| # | prediction_id | JA slug | JA title | EN slug | HTML長 | ステータス |",
        "|---|---------------|---------|----------|---------|--------|-----------|",
    ]

    for i, item in enumerate(result["queue"], 1):
        ja_slug_short = item["ja_slug"][:45]
        ja_title_short = item["ja_title"][:40]
        en_slug_short = item["expected_en_slug"][:45]
        lines.append(
            f"| {i} | {item['prediction_id']} "
            f"| `{ja_slug_short}` "
            f"| {ja_title_short} "
            f"| `{en_slug_short}` "
            f"| {item['source_html_length']:,} "
            f"| {item['status']} |"
        )

    # Skipped section
    skipped = result.get("skipped", [])
    if skipped:
        lines += [
            "",
            "## スキップされた項目",
            "",
            "| slug | 理由 |",
            "|------|------|",
        ]
        for s in skipped:
            lines.append(f"| `{s['slug'][:60]}` | {s['reason']} |")

    lines += [
        "",
        "## 次のステップ",
        "",
        "1. 各JA記事のHTMLをClaude Opus 4.6で英語翻訳",
        "2. nowpattern_publisher.pyで `expected_en_slug` を使ってGhost公開",
        "3. hreflangタグ注入（a4-hreflang-injector.py）",
        "4. 公開後に cross_language_only_audit.py を再実行して0件を確認",
        "",
    ]

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return json_path, md_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Build cross-language publish queue for EN translation"
    )
    parser.add_argument("--ghost-db", default=GHOST_DB_DEFAULT)
    parser.add_argument("--prediction-db", default=PREDICTION_DB_DEFAULT)
    parser.add_argument(
        "--audit-json",
        default=str(_AUDIT_JSON),
        help="Path to cross_language_only_audit.json",
    )
    args = parser.parse_args()

    result = build_publish_queue(
        ghost_db_path=args.ghost_db,
        prediction_db_path=args.prediction_db,
        audit_path=args.audit_json,
    )

    json_path, md_path = write_publish_queue_report(result)

    print(f"publish_queue_json={json_path}")
    print(f"publish_queue_md={md_path}")
    print(f"total_items={result['total_items']}")
    skipped = result.get("skipped", [])
    if skipped:
        print(f"skipped={len(skipped)}")
    for item in result["queue"]:
        print(f"  {item['prediction_id']}: {item['ja_slug'][:50]} -> {item['expected_en_slug'][:50]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
