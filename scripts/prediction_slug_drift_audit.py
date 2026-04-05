#!/usr/bin/env python3
"""Prediction slug drift audit.

Detects divergence between prediction_db article slugs and Ghost published state.

Checks:
  1. prediction_db article_slug not found in Ghost (published or draft)
  2. prediction_db article_links[].slug not found in Ghost
  3. Ghost published oracle articles not mapped to any prediction_id
  4. article_links[].slug doesn't match expected en-/ja pattern

Output:
  - reports/prediction_slug_drift_report.json
  - reports/prediction_slug_drift_report.md
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
    build_slug_to_prediction_index,
    build_prediction_article_links_index,
    load_prediction_db,
    PREDICTION_DB_DEFAULT,
)
from ghost_post_loader import (
    GHOST_DB_DEFAULT,
    load_ghost_posts,
    split_by_status,
    pub_slugs_set,
    dft_slugs_set,
)

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_REPORT_DIR = shared_or_local_path(
    script_file=__file__,
    shared_path="/opt/shared/reports",
    local_path=_REPO_ROOT / "reports",
)


# ---------------------------------------------------------------------------
# Drift categories
# ---------------------------------------------------------------------------

# DRIFT_TYPES:
#   db_slug_ghost_missing       – prediction_db.article_slug not in Ghost at all
#   db_slug_ghost_draft         – prediction_db.article_slug in Ghost as draft only
#   db_link_ghost_missing       – article_links[].slug not in Ghost at all
#   db_link_ghost_draft         – article_links[].slug in Ghost as draft only
#   oracle_no_prediction_id     – Published oracle article not mapped to any prediction
#   link_slug_pattern_mismatch  – article_links slug doesn't follow en-/ja convention


def run_slug_drift_audit(
    ghost_db_path: str = GHOST_DB_DEFAULT,
    prediction_db_path: str = PREDICTION_DB_DEFAULT,
) -> dict[str, Any]:
    """Run the full slug drift audit."""
    all_posts = load_ghost_posts(ghost_db_path, compute_oracle=True)
    published, draft = split_by_status(all_posts)
    pub_slugs = pub_slugs_set(all_posts)
    dft_slugs = dft_slugs_set(all_posts)

    pred_db = load_prediction_db(prediction_db_path)
    slug_to_pid = build_slug_to_prediction_index(pred_db)
    pid_to_links = build_prediction_article_links_index(pred_db)

    drifts: list[dict[str, Any]] = []

    # Check 1 & 2: prediction_db slugs vs Ghost
    for pred in pred_db.get("predictions", []):
        pid = str(pred.get("prediction_id", "")).strip()
        if not pid:
            continue

        # Check article_slug
        primary_slug = str(pred.get("article_slug") or "").strip()
        if primary_slug:
            if primary_slug not in pub_slugs:
                if primary_slug in dft_slugs:
                    drifts.append({
                        "drift_type": "db_slug_ghost_draft",
                        "prediction_id": pid,
                        "slug": primary_slug,
                        "field": "article_slug",
                        "detail": "Primary article_slug exists as Ghost draft, not published",
                    })
                else:
                    drifts.append({
                        "drift_type": "db_slug_ghost_missing",
                        "prediction_id": pid,
                        "slug": primary_slug,
                        "field": "article_slug",
                        "detail": "Primary article_slug not found in Ghost at all",
                    })

        # Check article_links
        for link in pred.get("article_links") or []:
            if not isinstance(link, dict):
                continue
            link_slug = str(link.get("slug") or "").strip()
            link_lang = str(link.get("lang") or "").strip()
            if not link_slug:
                continue

            if link_slug not in pub_slugs:
                if link_slug in dft_slugs:
                    drifts.append({
                        "drift_type": "db_link_ghost_draft",
                        "prediction_id": pid,
                        "slug": link_slug,
                        "field": f"article_links[lang={link_lang}]",
                        "detail": f"article_links slug exists as Ghost draft",
                    })
                else:
                    drifts.append({
                        "drift_type": "db_link_ghost_missing",
                        "prediction_id": pid,
                        "slug": link_slug,
                        "field": f"article_links[lang={link_lang}]",
                        "detail": f"article_links slug not found in Ghost",
                    })

            # Check slug pattern
            if link_lang == "en" and not link_slug.startswith("en-"):
                drifts.append({
                    "drift_type": "link_slug_pattern_mismatch",
                    "prediction_id": pid,
                    "slug": link_slug,
                    "field": f"article_links[lang={link_lang}]",
                    "detail": f"EN link slug lacks 'en-' prefix",
                })
            elif link_lang == "ja" and link_slug.startswith("en-"):
                drifts.append({
                    "drift_type": "link_slug_pattern_mismatch",
                    "prediction_id": pid,
                    "slug": link_slug,
                    "field": f"article_links[lang={link_lang}]",
                    "detail": f"JA link slug has 'en-' prefix",
                })

    # Check 3: Published oracle articles without prediction_id mapping
    for slug, post in published.items():
        if not post["is_oracle"]:
            continue
        if slug not in slug_to_pid:
            drifts.append({
                "drift_type": "oracle_no_prediction_id",
                "prediction_id": "",
                "slug": slug,
                "field": "ghost_published",
                "detail": "Published oracle article has no prediction_id mapping in prediction_db",
            })

    # Build summary
    type_counts = Counter(d["drift_type"] for d in drifts)

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_drifts": len(drifts),
        "drift_type_counts": dict(sorted(type_counts.items())),
        "ghost_published_count": len(pub_slugs),
        "ghost_draft_count": len(dft_slugs),
        "prediction_db_count": len(pred_db.get("predictions", [])),
        "drifts": drifts,
    }


def write_drift_report(result: dict[str, Any], report_dir: str | Path = _REPORT_DIR) -> tuple[str, str]:
    """Write JSON and Markdown reports."""
    report_dir = Path(report_dir)
    os.makedirs(report_dir, exist_ok=True)

    json_path = str(report_dir / "prediction_slug_drift_report.json")
    md_path = str(report_dir / "prediction_slug_drift_report.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    lines = [
        "# Prediction Slug Drift Report",
        "",
        f"生成日時: {result['generated_at']}",
        f"検出された乖離: **{result['total_drifts']}件**",
        "",
        f"Ghost published: {result['ghost_published_count']}件 / draft: {result['ghost_draft_count']}件",
        f"prediction_db: {result['prediction_db_count']}件",
        "",
        "## 乖離タイプ別サマリー",
        "",
        "| タイプ | 件数 | 説明 |",
        "|--------|------|------|",
    ]

    type_descriptions = {
        "db_slug_ghost_missing": "DB article_slugがGhostに不在",
        "db_slug_ghost_draft": "DB article_slugがGhostでdraft状態",
        "db_link_ghost_missing": "DB article_linksのslugがGhostに不在",
        "db_link_ghost_draft": "DB article_linksのslugがGhostでdraft状態",
        "oracle_no_prediction_id": "Oracle記事にprediction_idマッピングなし",
        "link_slug_pattern_mismatch": "article_linksのslugパターン不一致",
    }

    for dtype, count in sorted(result["drift_type_counts"].items()):
        desc = type_descriptions.get(dtype, dtype)
        lines.append(f"| {dtype} | {count} | {desc} |")

    lines += [
        "",
        "## 乖離一覧（最大100件）",
        "",
        "| # | タイプ | prediction_id | slug | フィールド | 詳細 |",
        "|---|--------|---------------|------|-----------|------|",
    ]
    for i, d in enumerate(result["drifts"][:100], 1):
        slug_short = d["slug"][:50]
        lines.append(
            f"| {i} | {d['drift_type']} | {d['prediction_id']} | `{slug_short}` | {d['field']} | {d['detail']} |"
        )

    if len(result["drifts"]) > 100:
        lines.append(f"\n*... 残り{len(result['drifts']) - 100}件はJSONレポートを参照*")

    lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return json_path, md_path


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Prediction slug drift audit")
    parser.add_argument("--ghost-db", default=GHOST_DB_DEFAULT)
    parser.add_argument("--prediction-db", default=PREDICTION_DB_DEFAULT)
    args = parser.parse_args()

    result = run_slug_drift_audit(
        ghost_db_path=args.ghost_db,
        prediction_db_path=args.prediction_db,
    )

    json_path, md_path = write_drift_report(result)

    print(f"drift_report_json={json_path}")
    print(f"drift_report_md={md_path}")
    print(f"total_drifts={result['total_drifts']}")
    for dtype, count in sorted(result["drift_type_counts"].items()):
        print(f"drift_{dtype}={count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
