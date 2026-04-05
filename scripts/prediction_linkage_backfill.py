#!/usr/bin/env python3
"""Prediction linkage backfill queue builder.

Analyzes missing_sibling oracle articles and produces an actionable
backfill queue with per-article classification of what's missing and why.

Output:
  - reports/prediction_linkage_backfill_queue.json
  - reports/prediction_linkage_backfill_queue.md
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from runtime_boundary import shared_or_local_path
from prediction_release_contract import (
    build_sibling_maps,
    build_slug_to_prediction_index,
    build_prediction_article_links_index,
    clean_slug,
    evaluate_prediction_linkage,
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
# Missing reason classification
# ---------------------------------------------------------------------------

# Possible reasons:
#   en_missing_entirely   – No EN version exists (not published, not draft)
#   en_exists_draft       – EN version exists as Ghost draft
#   en_exists_published_slug_mismatch – EN version published but slug doesn't match expected pattern
#   ja_missing_entirely   – No JA version (EN-only article without JA sibling)
#   ja_exists_draft       – JA version exists as Ghost draft
#   db_link_registered    – prediction_db has article_links entry for missing lang
#   db_link_missing       – prediction_db has NO article_links entry for missing lang

MISSING_REASONS = {
    "en_missing_entirely",
    "en_exists_draft",
    "en_exists_published_slug_mismatch",
    "ja_missing_entirely",
    "ja_exists_draft",
    "ja_exists_published_slug_mismatch",
}

DB_LINK_STATES = {
    "db_link_registered",
    "db_link_missing",
}




def classify_missing_sibling(
    *,
    slug: str,
    article_lang: str,
    prediction_id: str,
    published: dict[str, dict],
    draft: dict[str, dict],
    pid_to_links: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Classify why a sibling is missing for a given article."""
    target_lang = "ja" if article_lang == "en" else "en"
    cs = clean_slug(slug)

    # Expected sibling slug
    if target_lang == "en":
        expected_slug = "en-" + cs
    else:
        expected_slug = cs  # JA slug is the clean slug

    # Check Ghost state of expected sibling
    if expected_slug in published:
        missing_reason = f"{target_lang}_exists_published_slug_mismatch"
        ghost_state = "published"
    elif expected_slug in draft:
        missing_reason = f"{target_lang}_exists_draft"
        ghost_state = "draft"
    else:
        missing_reason = f"{target_lang}_missing_entirely"
        ghost_state = "missing"

    # Check prediction_db article_links for the missing lang
    db_link_state = "db_link_missing"
    db_link_slug = ""
    if prediction_id and prediction_id in pid_to_links:
        for link in pid_to_links[prediction_id]:
            if link.get("lang") == target_lang:
                db_link_state = "db_link_registered"
                db_link_slug = link.get("slug", "")
                break

    # Determine action category
    if ghost_state == "draft":
        action = "publish_draft"
    elif ghost_state == "published":
        action = "investigate_slug_mismatch"
    elif db_link_state == "db_link_registered":
        action = "create_and_publish_translation"
    else:
        action = "translate_and_register"

    return {
        "slug": slug,
        "prediction_id": prediction_id,
        "article_lang": article_lang,
        "target_lang": target_lang,
        "expected_sibling_slug": expected_slug,
        "missing_reason": missing_reason,
        "ghost_state": ghost_state,
        "db_link_state": db_link_state,
        "db_link_slug": db_link_slug,
        "action": action,
    }


def build_backfill_queue(
    ghost_db_path: str = GHOST_DB_DEFAULT,
    prediction_db_path: str = PREDICTION_DB_DEFAULT,
) -> dict[str, Any]:
    """Build the full backfill queue from Ghost DB and prediction_db."""
    all_posts = load_ghost_posts(ghost_db_path, compute_oracle=True)
    published, draft = split_by_status(all_posts)

    pred_db = load_prediction_db(prediction_db_path)
    slug_to_pid = build_slug_to_prediction_index(pred_db)
    pid_to_links = build_prediction_article_links_index(pred_db)

    # Build sibling maps from published posts
    posts_for_maps = [
        {"slug": s, "tag_slugs": p["tag_slugs"], "status": "published"}
        for s, p in published.items()
    ]
    ja_by_clean, en_by_clean = build_sibling_maps(posts_for_maps)

    # Find all oracle articles and evaluate linkage
    queue: list[dict[str, Any]] = []

    for slug, post in published.items():
        if not post["is_oracle"]:
            continue
        tag_slugs = post["tag_slugs"]

        matched_pid = slug_to_pid.get(slug, "")
        matched_links = pid_to_links.get(matched_pid, []) if matched_pid else []
        linkage = evaluate_prediction_linkage(
            slug=slug,
            tag_slugs=tag_slugs,
            prediction_id=matched_pid,
            ja_by_clean=ja_by_clean,
            en_by_clean=en_by_clean,
            prediction_article_links=matched_links,
        )

        if linkage["linkage_state"] != "missing_sibling":
            continue

        classification = classify_missing_sibling(
            slug=slug,
            article_lang=linkage["article_lang"],
            prediction_id=matched_pid,
            published=published,
            draft=draft,
            pid_to_links=pid_to_links,
        )
        queue.append(classification)

    # Sort by action priority: publish_draft first, then create, then translate
    action_order = {
        "publish_draft": 0,
        "investigate_slug_mismatch": 1,
        "create_and_publish_translation": 2,
        "translate_and_register": 3,
    }
    queue.sort(key=lambda x: (action_order.get(x["action"], 99), x["slug"]))

    # Build summary
    from collections import Counter
    reason_counts = Counter(item["missing_reason"] for item in queue)
    action_counts = Counter(item["action"] for item in queue)
    db_link_counts = Counter(item["db_link_state"] for item in queue)

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_missing_sibling": len(queue),
        "summary": {
            "by_missing_reason": dict(sorted(reason_counts.items())),
            "by_action": dict(sorted(action_counts.items())),
            "by_db_link_state": dict(sorted(db_link_counts.items())),
            "auto_fixable": action_counts.get("publish_draft", 0),
            "needs_translation": (
                action_counts.get("create_and_publish_translation", 0)
                + action_counts.get("translate_and_register", 0)
            ),
            "needs_investigation": action_counts.get("investigate_slug_mismatch", 0),
        },
        "queue": queue,
    }


def write_backfill_report(result: dict[str, Any], report_dir: str | Path = _REPORT_DIR) -> tuple[str, str]:
    """Write JSON and Markdown reports."""
    report_dir = Path(report_dir)
    os.makedirs(report_dir, exist_ok=True)

    json_path = str(report_dir / "prediction_linkage_backfill_queue.json")
    md_path = str(report_dir / "prediction_linkage_backfill_queue.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Build Markdown
    lines = [
        "# Prediction Linkage Backfill Queue",
        "",
        f"生成日時: {result['generated_at']}",
        f"missing_sibling合計: **{result['total_missing_sibling']}件**",
        "",
        "## サマリー",
        "",
        "### 原因別",
        "",
        "| 原因 | 件数 |",
        "|------|------|",
    ]
    for reason, count in sorted(result["summary"]["by_missing_reason"].items()):
        lines.append(f"| {reason} | {count} |")

    lines += [
        "",
        "### アクション別",
        "",
        "| アクション | 件数 | 説明 |",
        "|-----------|------|------|",
        f"| publish_draft | {result['summary']['by_action'].get('publish_draft', 0)} | Ghost draftを公開するだけ |",
        f"| investigate_slug_mismatch | {result['summary']['by_action'].get('investigate_slug_mismatch', 0)} | slug不一致を調査 |",
        f"| create_and_publish_translation | {result['summary']['by_action'].get('create_and_publish_translation', 0)} | 翻訳して公開（DBリンク登録済み） |",
        f"| translate_and_register | {result['summary']['by_action'].get('translate_and_register', 0)} | 翻訳＋DBリンク登録＋公開 |",
        "",
        f"**自動解消可能**: {result['summary']['auto_fixable']}件",
        f"**翻訳が必要**: {result['summary']['needs_translation']}件",
        f"**調査が必要**: {result['summary']['needs_investigation']}件",
        "",
        "## Backfill Queue（アクション優先度順）",
        "",
        "| # | slug | prediction_id | 言語 | 不足言語 | 原因 | DBリンク | アクション |",
        "|---|------|---------------|------|---------|------|---------|-----------|",
    ]
    for i, item in enumerate(result["queue"], 1):
        lines.append(
            f"| {i} | `{item['slug'][:60]}` | {item['prediction_id']} | {item['article_lang']} | {item['target_lang']} | {item['missing_reason']} | {item['db_link_state']} | **{item['action']}** |"
        )

    lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return json_path, md_path


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Build prediction linkage backfill queue")
    parser.add_argument("--ghost-db", default=GHOST_DB_DEFAULT)
    parser.add_argument("--prediction-db", default=PREDICTION_DB_DEFAULT)
    args = parser.parse_args()

    result = build_backfill_queue(
        ghost_db_path=args.ghost_db,
        prediction_db_path=args.prediction_db,
    )

    json_path, md_path = write_backfill_report(result)

    print(f"backfill_queue_json={json_path}")
    print(f"backfill_queue_md={md_path}")
    print(f"total_missing_sibling={result['total_missing_sibling']}")
    for action, count in sorted(result["summary"]["by_action"].items()):
        print(f"action_{action}={count}")
    print(f"auto_fixable={result['summary']['auto_fixable']}")
    print(f"needs_translation={result['summary']['needs_translation']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
