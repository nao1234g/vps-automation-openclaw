#!/usr/bin/env python3
"""Cross-language only audit.

Investigates oracle articles classified as cross_language_only:
prediction_db has article_links for both languages, but one language
is not published in Ghost.

Classifies root cause:
  - unpublished      – Ghost has no record of the slug (never created)
  - wrong_slug       – prediction_db slug doesn't match any Ghost post
  - draft_only       – Ghost has the slug as draft, not published
  - wrong_lang_tag   – Ghost article exists but has wrong lang tag
  - ghost_missing    – Ghost DB has no record at all

Output:
  - reports/cross_language_only_audit.json
  - reports/cross_language_only_audit.md
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

from runtime_boundary import shared_or_local_path
from prediction_release_contract import (
    build_sibling_maps,
    build_slug_to_prediction_index,
    build_prediction_article_links_index,
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


def audit_cross_language_only(
    ghost_db_path: str = GHOST_DB_DEFAULT,
    prediction_db_path: str = PREDICTION_DB_DEFAULT,
) -> dict[str, Any]:
    """Audit all cross_language_only articles."""
    all_posts = load_ghost_posts(ghost_db_path, compute_oracle=True)
    published, draft = split_by_status(all_posts)

    pred_db = load_prediction_db(prediction_db_path)
    slug_to_pid = build_slug_to_prediction_index(pred_db)
    pid_to_links = build_prediction_article_links_index(pred_db)

    posts_for_maps = [
        {"slug": s, "tag_slugs": p["tag_slugs"], "status": "published"}
        for s, p in published.items()
    ]
    ja_by_clean, en_by_clean = build_sibling_maps(posts_for_maps)

    audits: list[dict[str, Any]] = []

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

        if linkage["linkage_state"] != "cross_language_only":
            continue

        article_lang = linkage["article_lang"]
        target_lang = "ja" if article_lang == "en" else "en"
        # Find the db-registered sibling slug
        db_sibling_slug = ""
        db_sibling_url = ""
        for link in matched_links:
            if link.get("lang") == target_lang:
                db_sibling_slug = link.get("slug", "")
                db_sibling_url = link.get("url", "")
                break

        # Classify root cause
        if db_sibling_slug in published:
            # This shouldn't happen (would be paired_live), but check anyway
            root_cause = "wrong_lang_tag"
            detail = f"Slug '{db_sibling_slug}' is published but not detected as {target_lang} sibling"
        elif db_sibling_slug in draft:
            root_cause = "draft_only"
            detail = f"Slug '{db_sibling_slug}' exists as Ghost draft, not published"
        elif db_sibling_slug:
            # Has slug in DB but not in Ghost at all
            root_cause = "unpublished"
            detail = f"DB registered slug '{db_sibling_slug}' not found in Ghost (never created)"
        else:
            root_cause = "ghost_missing"
            detail = f"No {target_lang} slug registered in prediction_db article_links"

        # Determine fix action
        if root_cause == "draft_only":
            fix_action = "publish_draft"
        elif root_cause == "wrong_lang_tag":
            fix_action = "fix_lang_tag"
        elif root_cause == "unpublished":
            fix_action = "create_and_publish"
        else:
            fix_action = "register_and_create"

        audits.append({
            "slug": slug,
            "prediction_id": matched_pid,
            "article_lang": article_lang,
            "target_lang": target_lang,
            "db_sibling_slug": db_sibling_slug,
            "db_sibling_url": db_sibling_url,
            "root_cause": root_cause,
            "detail": detail,
            "fix_action": fix_action,
        })

    cause_counts = Counter(a["root_cause"] for a in audits)
    action_counts = Counter(a["fix_action"] for a in audits)

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_cross_language_only": len(audits),
        "summary": {
            "by_root_cause": dict(sorted(cause_counts.items())),
            "by_fix_action": dict(sorted(action_counts.items())),
        },
        "audits": audits,
    }


def write_audit_report(result: dict[str, Any], report_dir: str | Path = _REPORT_DIR) -> tuple[str, str]:
    """Write JSON and Markdown reports."""
    report_dir = Path(report_dir)
    os.makedirs(report_dir, exist_ok=True)

    json_path = str(report_dir / "cross_language_only_audit.json")
    md_path = str(report_dir / "cross_language_only_audit.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    lines = [
        "# Cross-Language Only 監査レポート",
        "",
        f"生成日時: {result['generated_at']}",
        f"cross_language_only合計: **{result['total_cross_language_only']}件**",
        "",
        "## 原因分布",
        "",
        "| 原因 | 件数 | 説明 |",
        "|------|------|------|",
    ]
    cause_desc = {
        "unpublished": "DBにEN slugが登録済みだがGhost記事が未作成",
        "draft_only": "Ghost記事がdraft状態で未公開",
        "wrong_lang_tag": "Ghost記事はあるが言語タグが不正",
        "ghost_missing": "DB article_linksにも対象言語の登録なし",
    }
    for cause, count in sorted(result["summary"]["by_root_cause"].items()):
        desc = cause_desc.get(cause, cause)
        lines.append(f"| {cause} | {count} | {desc} |")

    lines += [
        "",
        "## 修正アクション分布",
        "",
        "| アクション | 件数 |",
        "|-----------|------|",
    ]
    for action, count in sorted(result["summary"]["by_fix_action"].items()):
        lines.append(f"| {action} | {count} |")

    lines += [
        "",
        "## 詳細一覧",
        "",
        "| # | slug | prediction_id | 言語 | 不足 | DB sibling slug | 原因 | 修正アクション |",
        "|---|------|---------------|------|------|----------------|------|---------------|",
    ]
    for i, a in enumerate(result["audits"], 1):
        slug_short = a["slug"][:50]
        db_sib = a["db_sibling_slug"][:40] if a["db_sibling_slug"] else "(none)"
        lines.append(
            f"| {i} | `{slug_short}` | {a['prediction_id']} | {a['article_lang']} | {a['target_lang']} | `{db_sib}` | {a['root_cause']} | **{a['fix_action']}** |"
        )

    lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return json_path, md_path


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Cross-language only audit")
    parser.add_argument("--ghost-db", default=GHOST_DB_DEFAULT)
    parser.add_argument("--prediction-db", default=PREDICTION_DB_DEFAULT)
    args = parser.parse_args()

    result = audit_cross_language_only(
        ghost_db_path=args.ghost_db,
        prediction_db_path=args.prediction_db,
    )

    json_path, md_path = write_audit_report(result)

    print(f"audit_json={json_path}")
    print(f"audit_md={md_path}")
    print(f"total_cross_language_only={result['total_cross_language_only']}")
    for cause, count in sorted(result["summary"]["by_root_cause"].items()):
        print(f"cause_{cause}={count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
