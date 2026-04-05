#!/usr/bin/env python3
"""Prediction slug normalization plan — dry-run classifier.

Reads the 526 link_slug_pattern_mismatch drifts (EN article_links entries
whose slug lacks the ``en-`` prefix) and classifies each into safety
categories for potential normalization.

Safety categories:
  safe_normalize   – Ghost has exact ``en-{slug}`` published, change is unique,
                     prediction_id mapping unambiguous.
  unsafe_ambiguous – Multiple prediction_ids map to same slug, or slug
                     collision would occur after adding ``en-`` prefix.
  ghost_missing    – Neither ``slug`` nor ``en-{slug}`` exists in Ghost
                     (can't verify).
  draft_only       – ``en-{slug}`` exists as Ghost draft only.
  db_stale         – The prediction_db entry appears outdated; no Ghost
                     article for either form.

Output:
  - reports/prediction_slug_normalization_plan.json
  - reports/prediction_slug_normalization_plan.md

FORBIDDEN: This script never modifies prediction_db.  It is read-only
           classification only (dry-run).
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
    load_prediction_db,
    PREDICTION_DB_DEFAULT,
)
from ghost_post_loader import (
    GHOST_DB_DEFAULT,
    load_ghost_posts,
    published_slugs_set,
    draft_slugs_set,
)

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_REPORT_DIR = shared_or_local_path(
    script_file=__file__,
    shared_path="/opt/shared/reports",
    local_path=_REPO_ROOT / "reports",
)

# Drift report produced by prediction_slug_drift_audit.py
_DRIFT_REPORT_PATH = shared_or_local_path(
    script_file=__file__,
    shared_path="/opt/shared/reports/prediction_slug_drift_report.json",
    local_path=_REPO_ROOT / "reports" / "prediction_slug_drift_report.json",
)

# ---------------------------------------------------------------------------
# Safety category definitions
# ---------------------------------------------------------------------------

SAFETY_CATEGORIES = {
    "safe_normalize",
    "unsafe_ambiguous",
    "ghost_missing",
    "draft_only",
    "db_stale",
}


# ---------------------------------------------------------------------------
# Core classification logic
# ---------------------------------------------------------------------------


def _load_drift_mismatches(drift_report_path: str | Path) -> list[dict[str, Any]]:
    """Extract link_slug_pattern_mismatch entries from the drift report."""
    path = Path(drift_report_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Drift report not found: {path}\n"
            f"Run prediction_slug_drift_audit.py first."
        )
    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)
    return [
        d for d in report.get("drifts", [])
        if d.get("drift_type") == "link_slug_pattern_mismatch"
    ]


def _build_reverse_slug_index(
    pred_db: dict[str, Any],
) -> dict[str, list[str]]:
    """Build slug → [prediction_id, ...] index to detect ambiguity.

    Unlike build_slug_to_prediction_index (first-writer-wins), this one
    collects *all* prediction_ids that reference a given slug.
    """
    index: dict[str, list[str]] = {}
    for pred in pred_db.get("predictions", []):
        pid = str(pred.get("prediction_id", "")).strip()
        if not pid:
            continue

        primary = str(pred.get("article_slug") or "").strip()
        if primary:
            index.setdefault(primary, []).append(pid)

        for link in pred.get("article_links") or []:
            if not isinstance(link, dict):
                continue
            slug = str(link.get("slug") or "").strip()
            if slug:
                index.setdefault(slug, []).append(pid)

    # Deduplicate per slug (same pid can appear from article_slug + article_links)
    return {slug: sorted(set(pids)) for slug, pids in index.items()}


def classify_mismatch_entry(
    *,
    prediction_id: str,
    current_slug: str,
    pub_slugs: set[str],
    dft_slugs: set[str],
    reverse_index: dict[str, list[str]],
    all_en_link_slugs: set[str],
) -> dict[str, Any]:
    """Classify a single EN link slug that lacks the 'en-' prefix.

    Args:
        prediction_id: NP-YYYY-XXXX identifier.
        current_slug: The slug currently stored in article_links[lang=en].
        pub_slugs: Set of all published Ghost slugs.
        dft_slugs: Set of all draft Ghost slugs.
        reverse_index: slug → [pid, ...] for collision detection.
        all_en_link_slugs: Set of all EN link slugs in prediction_db
                           (for target collision detection).

    Returns:
        Classification dict with safety_category and evidence fields.
    """
    proposed_slug = f"en-{current_slug}"

    # --- Ambiguity check: multiple pids for the same current slug ---
    pids_for_current = reverse_index.get(current_slug, [])
    pids_for_proposed = reverse_index.get(proposed_slug, [])

    multiple_pids_current = len(pids_for_current) > 1
    proposed_already_used = len(pids_for_proposed) > 0 and not (
        len(pids_for_proposed) == 1 and pids_for_proposed[0] == prediction_id
    )
    proposed_collision_en_links = proposed_slug in all_en_link_slugs

    if multiple_pids_current or proposed_already_used or proposed_collision_en_links:
        return {
            "prediction_id": prediction_id,
            "current_slug": current_slug,
            "proposed_slug": proposed_slug,
            "safety_category": "unsafe_ambiguous",
            "reason": _ambiguity_reason(
                multiple_pids_current, proposed_already_used,
                proposed_collision_en_links, pids_for_current,
                pids_for_proposed,
            ),
            "current_in_ghost_pub": current_slug in pub_slugs,
            "current_in_ghost_draft": current_slug in dft_slugs,
            "proposed_in_ghost_pub": proposed_slug in pub_slugs,
            "proposed_in_ghost_draft": proposed_slug in dft_slugs,
        }

    # --- Ghost state of the proposed en-{slug} ---
    proposed_published = proposed_slug in pub_slugs
    proposed_draft = proposed_slug in dft_slugs
    current_published = current_slug in pub_slugs
    current_draft = current_slug in dft_slugs

    if proposed_published:
        return {
            "prediction_id": prediction_id,
            "current_slug": current_slug,
            "proposed_slug": proposed_slug,
            "safety_category": "safe_normalize",
            "reason": "en-{slug} exists as published Ghost post; unique mapping",
            "current_in_ghost_pub": current_published,
            "current_in_ghost_draft": current_draft,
            "proposed_in_ghost_pub": True,
            "proposed_in_ghost_draft": False,
        }

    if proposed_draft:
        return {
            "prediction_id": prediction_id,
            "current_slug": current_slug,
            "proposed_slug": proposed_slug,
            "safety_category": "draft_only",
            "reason": "en-{slug} exists as Ghost draft only; not yet published",
            "current_in_ghost_pub": current_published,
            "current_in_ghost_draft": current_draft,
            "proposed_in_ghost_pub": False,
            "proposed_in_ghost_draft": True,
        }

    # Neither proposed nor current is in Ghost at all → ghost_missing or db_stale
    if not current_published and not current_draft:
        return {
            "prediction_id": prediction_id,
            "current_slug": current_slug,
            "proposed_slug": proposed_slug,
            "safety_category": "db_stale",
            "reason": "Neither current slug nor en-{slug} found in Ghost (published or draft)",
            "current_in_ghost_pub": False,
            "current_in_ghost_draft": False,
            "proposed_in_ghost_pub": False,
            "proposed_in_ghost_draft": False,
        }

    # Current slug exists but proposed en-{slug} does not
    return {
        "prediction_id": prediction_id,
        "current_slug": current_slug,
        "proposed_slug": proposed_slug,
        "safety_category": "ghost_missing",
        "reason": (
            f"Current slug {'published' if current_published else 'draft'} in Ghost; "
            f"en-{{slug}} not found in Ghost"
        ),
        "current_in_ghost_pub": current_published,
        "current_in_ghost_draft": current_draft,
        "proposed_in_ghost_pub": False,
        "proposed_in_ghost_draft": False,
    }


def _ambiguity_reason(
    multiple_pids_current: bool,
    proposed_already_used: bool,
    proposed_collision_en_links: bool,
    pids_for_current: list[str],
    pids_for_proposed: list[str],
) -> str:
    """Build a human-readable ambiguity reason string."""
    parts: list[str] = []
    if multiple_pids_current:
        parts.append(
            f"Current slug mapped by {len(pids_for_current)} prediction_ids: "
            f"{', '.join(pids_for_current)}"
        )
    if proposed_already_used:
        parts.append(
            f"Proposed en-{{slug}} already used by: "
            f"{', '.join(pids_for_proposed)}"
        )
    if proposed_collision_en_links:
        parts.append("Proposed slug would collide with existing EN article_links entry")
    return "; ".join(parts) if parts else "Unknown ambiguity"


# ---------------------------------------------------------------------------
# paired_live impact estimation
# ---------------------------------------------------------------------------


def _estimate_paired_live_impact(
    queue: list[dict[str, Any]],
    pred_db: dict[str, Any],
    pub_slugs: set[str],
) -> dict[str, Any]:
    """Estimate how paired_live count changes if safe_normalize entries are applied.

    Current state: EN links without en- prefix fail sibling detection
    because ``build_sibling_maps`` keys EN posts by ``clean_slug(en-X) = X``,
    but the article_links slug is already ``X`` (no prefix) so the linkage
    evaluator may not find the published post via the slug index.

    After normalization: The EN link slug becomes ``en-X``, which matches
    the Ghost published slug, so ``slug_to_pid`` and sibling maps should
    connect correctly.
    """
    # Build prediction_id → article_links for quick lookup
    pid_links: dict[str, list[dict[str, Any]]] = {}
    for pred in pred_db.get("predictions", []):
        pid = str(pred.get("prediction_id", "")).strip()
        if pid:
            pid_links[pid] = pred.get("article_links") or []

    safe_entries = [e for e in queue if e["safety_category"] == "safe_normalize"]

    # For each safe_normalize entry, check whether the prediction currently
    # has both JA and EN links with slugs that resolve to published Ghost posts.
    before_paired = 0
    after_paired = 0

    for entry in safe_entries:
        pid = entry["prediction_id"]
        links = pid_links.get(pid, [])

        ja_link_slug = ""
        en_link_slug = ""
        for link in links:
            if not isinstance(link, dict):
                continue
            lang = str(link.get("lang") or "").strip()
            slug = str(link.get("slug") or "").strip()
            if lang == "ja" and not ja_link_slug:
                ja_link_slug = slug
            elif lang == "en" and not en_link_slug:
                en_link_slug = slug

        # Before: check if both current slugs are published
        ja_pub_before = ja_link_slug in pub_slugs if ja_link_slug else False
        en_pub_before = en_link_slug in pub_slugs if en_link_slug else False
        if ja_pub_before and en_pub_before:
            before_paired += 1

        # After: EN slug becomes en-{slug}, check if that's published
        proposed_en = entry["proposed_slug"]
        en_pub_after = proposed_en in pub_slugs
        if ja_pub_before and en_pub_after:
            after_paired += 1

    return {
        "safe_normalize_count": len(safe_entries),
        "before_paired_live": before_paired,
        "after_paired_live": after_paired,
        "paired_live_delta": after_paired - before_paired,
        "note": (
            "Estimate based on safe_normalize entries only. "
            "Actual paired_live depends on full sibling map rebuild."
        ),
    }


# ---------------------------------------------------------------------------
# Main plan builder
# ---------------------------------------------------------------------------


def build_normalization_plan(
    ghost_db_path: str = GHOST_DB_DEFAULT,
    prediction_db_path: str = PREDICTION_DB_DEFAULT,
    drift_report_path: str | Path = _DRIFT_REPORT_PATH,
) -> dict[str, Any]:
    """Build the full normalization plan from Ghost DB and prediction_db."""

    # Load drift mismatches
    mismatches = _load_drift_mismatches(drift_report_path)

    # Load Ghost posts
    all_posts = load_ghost_posts(ghost_db_path, compute_oracle=True)
    pub_slugs = published_slugs_set(all_posts)
    dft_slugs = draft_slugs_set(all_posts)

    # Load prediction_db
    pred_db = load_prediction_db(prediction_db_path)

    # Build reverse slug index (slug → [pid, ...]) for ambiguity detection
    reverse_index = _build_reverse_slug_index(pred_db)

    # Collect all EN article_links slugs for collision detection
    all_en_link_slugs: set[str] = set()
    for pred in pred_db.get("predictions", []):
        for link in pred.get("article_links") or []:
            if not isinstance(link, dict):
                continue
            if str(link.get("lang") or "").strip() == "en":
                slug = str(link.get("slug") or "").strip()
                if slug:
                    all_en_link_slugs.add(slug)

    # Classify each mismatch entry individually
    queue: list[dict[str, Any]] = []
    for drift in mismatches:
        pid = str(drift.get("prediction_id") or "").strip()
        slug = str(drift.get("slug") or "").strip()
        if not pid or not slug:
            continue

        classification = classify_mismatch_entry(
            prediction_id=pid,
            current_slug=slug,
            pub_slugs=pub_slugs,
            dft_slugs=dft_slugs,
            reverse_index=reverse_index,
            all_en_link_slugs=all_en_link_slugs,
        )
        queue.append(classification)

    # Sort: safe_normalize first, then by category, then by prediction_id
    category_order = {
        "safe_normalize": 0,
        "draft_only": 1,
        "ghost_missing": 2,
        "db_stale": 3,
        "unsafe_ambiguous": 4,
    }
    queue.sort(key=lambda x: (
        category_order.get(x["safety_category"], 99),
        x["prediction_id"],
    ))

    # Build summary
    category_counts = Counter(e["safety_category"] for e in queue)

    # paired_live impact estimate
    impact = _estimate_paired_live_impact(queue, pred_db, pub_slugs)

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "drift_report_source": str(drift_report_path),
        "total_pattern_mismatches": len(mismatches),
        "total_classified": len(queue),
        "summary": {
            "by_safety_category": dict(sorted(category_counts.items())),
            "safe_normalize": category_counts.get("safe_normalize", 0),
            "unsafe_ambiguous": category_counts.get("unsafe_ambiguous", 0),
            "ghost_missing": category_counts.get("ghost_missing", 0),
            "draft_only": category_counts.get("draft_only", 0),
            "db_stale": category_counts.get("db_stale", 0),
        },
        "paired_live_impact": impact,
        "queue": queue,
    }


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------


def write_normalization_plan(
    result: dict[str, Any],
    report_dir: str | Path = _REPORT_DIR,
) -> tuple[str, str]:
    """Write JSON and Markdown reports."""
    report_dir = Path(report_dir)
    os.makedirs(report_dir, exist_ok=True)

    json_path = str(report_dir / "prediction_slug_normalization_plan.json")
    md_path = str(report_dir / "prediction_slug_normalization_plan.md")

    # --- JSON ---
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # --- Markdown ---
    summary = result["summary"]
    impact = result["paired_live_impact"]
    queue = result["queue"]

    lines = [
        "# Prediction Slug Normalization Plan (Dry-Run)",
        "",
        f"生成日時: {result['generated_at']}",
        f"元データ: `{result['drift_report_source']}`",
        f"パターン不一致合計: **{result['total_pattern_mismatches']}件**",
        f"分類済み: **{result['total_classified']}件**",
        "",
        "## 安全カテゴリ別サマリー",
        "",
        "| カテゴリ | 件数 | 説明 |",
        "|---------|------|------|",
        f"| safe_normalize | {summary['safe_normalize']} | Ghost published に en-{{slug}} が存在、一意マッピング |",
        f"| draft_only | {summary['draft_only']} | en-{{slug}} が Ghost draft のみ存在 |",
        f"| ghost_missing | {summary['ghost_missing']} | 現slug は Ghost に存在するが en-{{slug}} は不在 |",
        f"| db_stale | {summary['db_stale']} | 現slug も en-{{slug}} も Ghost に不在 |",
        f"| unsafe_ambiguous | {summary['unsafe_ambiguous']} | slug衝突 or 複数 prediction_id マッピング |",
        "",
        "## paired_live 影響推定",
        "",
        f"- safe_normalize 対象: **{impact['safe_normalize_count']}件**",
        f"- 変更前 paired_live: **{impact['before_paired_live']}件**",
        f"- 変更後 paired_live (推定): **{impact['after_paired_live']}件**",
        f"- 差分 (delta): **+{impact['paired_live_delta']}件**",
        f"- 備考: {impact['note']}",
        "",
    ]

    # --- safe_normalize table ---
    safe_entries = [e for e in queue if e["safety_category"] == "safe_normalize"]
    if safe_entries:
        lines += [
            "## safe_normalize 一覧",
            "",
            "| # | prediction_id | 現slug | 提案slug | 現slug Ghost状態 | en-slug Ghost状態 |",
            "|---|---------------|--------|---------|-----------------|-----------------|",
        ]
        for i, e in enumerate(safe_entries, 1):
            cur_state = "published" if e["current_in_ghost_pub"] else (
                "draft" if e["current_in_ghost_draft"] else "missing"
            )
            lines.append(
                f"| {i} | {e['prediction_id']} | `{e['current_slug'][:55]}` "
                f"| `{e['proposed_slug'][:55]}` | {cur_state} | published |"
            )
        lines.append("")

    # --- draft_only table ---
    draft_entries = [e for e in queue if e["safety_category"] == "draft_only"]
    if draft_entries:
        lines += [
            "## draft_only 一覧",
            "",
            "| # | prediction_id | 現slug | 提案slug |",
            "|---|---------------|--------|---------|",
        ]
        for i, e in enumerate(draft_entries, 1):
            lines.append(
                f"| {i} | {e['prediction_id']} | `{e['current_slug'][:55]}` "
                f"| `{e['proposed_slug'][:55]}` |"
            )
        lines.append("")

    # --- ghost_missing table ---
    missing_entries = [e for e in queue if e["safety_category"] == "ghost_missing"]
    if missing_entries:
        lines += [
            "## ghost_missing 一覧",
            "",
            "| # | prediction_id | 現slug | 現slug Ghost状態 | 理由 |",
            "|---|---------------|--------|-----------------|------|",
        ]
        for i, e in enumerate(missing_entries, 1):
            cur_state = "published" if e["current_in_ghost_pub"] else (
                "draft" if e["current_in_ghost_draft"] else "missing"
            )
            lines.append(
                f"| {i} | {e['prediction_id']} | `{e['current_slug'][:55]}` "
                f"| {cur_state} | {e['reason']} |"
            )
        lines.append("")

    # --- db_stale table ---
    stale_entries = [e for e in queue if e["safety_category"] == "db_stale"]
    if stale_entries:
        lines += [
            "## db_stale 一覧",
            "",
            "| # | prediction_id | 現slug |",
            "|---|---------------|--------|",
        ]
        for i, e in enumerate(stale_entries, 1):
            lines.append(
                f"| {i} | {e['prediction_id']} | `{e['current_slug'][:55]}` |"
            )
        lines.append("")

    # --- unsafe_ambiguous table ---
    ambiguous_entries = [e for e in queue if e["safety_category"] == "unsafe_ambiguous"]
    if ambiguous_entries:
        lines += [
            "## unsafe_ambiguous 一覧",
            "",
            "| # | prediction_id | 現slug | 提案slug | 理由 |",
            "|---|---------------|--------|---------|------|",
        ]
        for i, e in enumerate(ambiguous_entries, 1):
            lines.append(
                f"| {i} | {e['prediction_id']} | `{e['current_slug'][:45]}` "
                f"| `{e['proposed_slug'][:45]}` | {e['reason'][:80]} |"
            )
        lines.append("")

    # Footer
    lines += [
        "---",
        "",
        "*このレポートはドライラン分類です。prediction_dbの変更は一切行っていません。*",
        f"*safe_normalize 以外のカテゴリは個別調査が必要です。*",
        "",
    ]

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return json_path, md_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Build prediction slug normalization plan (dry-run classifier)"
    )
    parser.add_argument(
        "--ghost-db",
        default=GHOST_DB_DEFAULT,
        help=f"Path to Ghost SQLite database (default: {GHOST_DB_DEFAULT})",
    )
    parser.add_argument(
        "--prediction-db",
        default=PREDICTION_DB_DEFAULT,
        help=f"Path to prediction_db.json (default: {PREDICTION_DB_DEFAULT})",
    )
    parser.add_argument(
        "--drift-report",
        default=str(_DRIFT_REPORT_PATH),
        help="Path to prediction_slug_drift_report.json",
    )
    args = parser.parse_args()

    result = build_normalization_plan(
        ghost_db_path=args.ghost_db,
        prediction_db_path=args.prediction_db,
        drift_report_path=args.drift_report,
    )

    json_path, md_path = write_normalization_plan(result)

    # Machine-readable stdout for pipeline integration
    print(f"normalization_plan_json={json_path}")
    print(f"normalization_plan_md={md_path}")
    print(f"total_pattern_mismatches={result['total_pattern_mismatches']}")
    print(f"total_classified={result['total_classified']}")
    for cat, count in sorted(result["summary"]["by_safety_category"].items()):
        print(f"category_{cat}={count}")
    impact = result["paired_live_impact"]
    print(f"paired_live_before={impact['before_paired_live']}")
    print(f"paired_live_after={impact['after_paired_live']}")
    print(f"paired_live_delta=+{impact['paired_live_delta']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
