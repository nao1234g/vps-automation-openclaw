#!/usr/bin/env python3
"""Refresh prediction_db.json meta fields from the canonical predictions array."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from prediction_state_utils import (
    canonical_prediction_status,
    infer_final_verdict,
    normalize_score_tier,
    normalize_verdict,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = REPO_ROOT / "scripts" / "prediction_db.json"


def wilson_approx_bounds(hit: int, scored: int) -> tuple[float, float]:
    if scored <= 0:
        return 0.0, 0.0
    p = hit / scored
    se = math.sqrt(p * (1.0 - p) / scored)
    return round(max(0.0, p - 1.96 * se) * 100.0, 1), round(min(1.0, p + 1.96 * se) * 100.0, 1)


def canonicalize_prediction_statuses(payload: dict) -> int:
    preds = payload.get("predictions", [])
    changed = 0
    for pred in preds:
        inferred_verdict = infer_final_verdict(pred)
        if inferred_verdict and inferred_verdict != normalize_verdict(pred.get("verdict")):
            pred["verdict"] = inferred_verdict
            if inferred_verdict == "HIT" and not pred.get("hit_miss"):
                pred["hit_miss"] = "correct"
            elif inferred_verdict == "MISS" and not pred.get("hit_miss"):
                pred["hit_miss"] = "incorrect"
            changed += 1
        canonical_status = canonical_prediction_status(pred)
        if pred.get("status") != canonical_status:
            pred["status"] = canonical_status
            changed += 1
    return changed


def infer_article_link_lang(article: dict) -> str:
    url = str(article.get("url") or "").strip().lower()
    slug = str(article.get("slug") or "").strip().lower()
    if "/en/" in url or slug.startswith("en-"):
        return "en"
    if url or slug:
        return "ja"
    return ""


def canonicalize_prediction_article_links(payload: dict) -> int:
    preds = payload.get("predictions", [])
    changed = 0
    for pred in preds:
        for article in pred.get("article_links") or []:
            if not isinstance(article, dict):
                continue
            inferred_lang = infer_article_link_lang(article)
            current_lang = str(article.get("lang") or "").strip().lower()
            if inferred_lang and current_lang != inferred_lang:
                article["lang"] = inferred_lang
                changed += 1
    return changed


def compute_meta(payload: dict) -> tuple[dict, dict]:
    preds = payload.get("predictions", [])
    total = len(preds)
    hit = sum(1 for p in preds if normalize_verdict(p.get("verdict")) == "HIT")
    miss = sum(1 for p in preds if normalize_verdict(p.get("verdict")) == "MISS")
    not_scored = sum(1 for p in preds if normalize_verdict(p.get("verdict")) == "NOT_SCORED")
    scored = hit + miss
    resolved_like = scored + not_scored

    brier_values = [
        float(p["brier_score"])
        for p in preds
        if normalize_verdict(p.get("verdict")) in {"HIT", "MISS"} and p.get("brier_score") is not None
    ]
    avg_brier = round(sum(brier_values) / len(brier_values), 4) if brier_values else None

    status_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}
    for pred in preds:
        status_key = canonical_prediction_status(pred)
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
        tier_key = normalize_score_tier(pred.get("official_score_tier"))
        tier_counts[tier_key] = tier_counts.get(tier_key, 0) + 1

    accuracy_pct = round(hit / scored * 100.0, 1) if scored > 0 else 0.0
    ci_lo, ci_hi = wilson_approx_bounds(hit, scored)
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    meta_updates = {
        "total_predictions": total,
        "scored_predictions": scored,
        "accuracy_pct": accuracy_pct,
        "official_brier_avg": avg_brier,
        "resolution_coverage_pct": round((resolved_like / total) * 100.0, 1) if total > 0 else 0.0,
        "status_counts": status_counts,
        "official_brier_avg_initial_prob": avg_brier,
        "official_brier_avg_initial_prob_n": scored,
        "accuracy_formula": "HIT/(HIT+MISS)",
        "accuracy_n": scored,
        "accuracy_hit": hit,
        "accuracy_miss": miss,
        "accuracy_ci_lo": ci_lo,
        "accuracy_ci_hi": ci_hi,
        "accuracy_updated_at": now_iso,
    }

    score_summary = dict(payload.get("meta", {}).get("score_provenance_summary", {}) or {})
    score_summary["tier_counts"] = tier_counts
    meta_updates["score_provenance_summary"] = score_summary

    return meta_updates, {
        "total_predictions": total,
        "hit": hit,
        "miss": miss,
        "not_scored": not_scored,
        "scored": scored,
        "avg_brier": avg_brier,
        "status_counts": status_counts,
        "tier_counts": tier_counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh prediction_db meta fields from canonical predictions.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to prediction_db.json")
    parser.add_argument("--dry-run", action="store_true", help="Print planned updates without writing")
    args = parser.parse_args()

    db_path = Path(args.db)
    payload = json.loads(db_path.read_text(encoding="utf-8"))
    payload.setdefault("meta", {})
    changed = canonicalize_prediction_statuses(payload)
    article_link_lang_updates = canonicalize_prediction_article_links(payload)

    meta_updates, summary = compute_meta(payload)
    payload["meta"].update(meta_updates)
    summary["canonical_status_updates"] = changed
    summary["article_link_lang_updates"] = article_link_lang_updates

    if args.dry_run:
        print(json.dumps({"db": str(db_path), "summary": summary, "meta_updates": meta_updates}, ensure_ascii=False, indent=2))
        return 0

    db_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"db": str(db_path), "summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
