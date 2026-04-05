#!/usr/bin/env python3
"""Lightweight live updater for /predictions/ and /en/predictions/.

This bypasses the heavyweight snapshot/deploy-gate path in prediction_page_builder.py
and only regenerates the public tracker HTML plus JSON-LD/widget injections.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prediction_page_builder import (  # noqa: E402
    PREDICTIONS_SLUG_EN,
    PREDICTIONS_SLUG_JA,
    _canonical_public_stats,
    _tracker_page_metadata,
    _write_tracker_payload_report,
    _update_dataset_in_head,
    _update_reader_vote_widget_in_foot,
    build_page_html,
    build_rows,
    ghost_request,
    load_embed_data,
    load_env,
    load_prediction_db,
    update_ghost_page,
)


def _best_effort(label: str, fn, *args, **kwargs) -> bool:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            fn(*args, **kwargs)
            return True
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"WARN: {label} attempt {attempt}/3 failed: {exc}")
            if attempt < 3:
                time.sleep(1.5)
    print(f"WARN: {label} skipped after repeated failures: {last_error}")
    return False


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=("ja", "en", "both"), default="both")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    env = load_env()
    api_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not api_key:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not found")
        return 1

    pred_db = load_prediction_db()
    embed_data = load_embed_data()
    public_stats = _canonical_public_stats(pred_db)
    ghost_result = ghost_request(
        "GET",
        "/posts/?limit=all&filter=status:published&include=tags&formats=html&fields=id,slug,title,url,html,published_at",
        api_key,
    )
    ghost_posts = ghost_result.get("posts", [])

    page_specs = (
        ("ja", PREDICTIONS_SLUG_JA),
        ("en", PREDICTIONS_SLUG_EN),
    )
    if args.lang != "both":
        page_specs = tuple(spec for spec in page_specs if spec[0] == args.lang)

    for lang, slug in page_specs:
        rows = build_rows(pred_db, ghost_posts, embed_data, lang)
        _write_tracker_payload_report(lang, rows)
        html = build_page_html(rows, public_stats, lang)
        seo = _tracker_page_metadata(public_stats, lang)
        update_ghost_page(
            api_key,
            slug,
            html,
            seo["title"],
            meta_title=seo["meta_title"],
            meta_description=seo["meta_description"],
            custom_excerpt=seo["meta_description"],
        )
        _best_effort(
            f"dataset-head:{slug}",
            _update_dataset_in_head,
            api_key,
            slug,
            public_stats,
            lang,
            pred_db.get("predictions", []),
        )
        _best_effort(
            f"vote-widget-foot:{slug}",
            _update_reader_vote_widget_in_foot,
            api_key,
            slug,
            lang,
        )
        print(f"Updated tracker page: {lang}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
