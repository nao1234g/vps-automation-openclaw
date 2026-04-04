#!/usr/bin/env python3
"""Lightweight live updater for /predictions/ and /en/predictions/.

This bypasses the heavyweight snapshot/deploy-gate path in prediction_page_builder.py
and only regenerates the public tracker HTML plus JSON-LD/widget injections.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prediction_page_builder import (  # noqa: E402
    PREDICTIONS_SLUG_EN,
    PREDICTIONS_SLUG_JA,
    _canonical_public_stats,
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


def main() -> int:
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

    for lang, slug, title in (
        ("ja", PREDICTIONS_SLUG_JA, "予測トラッカー — Nowpatternの分析 vs 市場"),
        ("en", PREDICTIONS_SLUG_EN, "Prediction Tracker — Nowpattern vs Market"),
    ):
        rows = build_rows(pred_db, ghost_posts, embed_data, lang)
        html = build_page_html(rows, public_stats, lang)
        update_ghost_page(api_key, slug, html, title)
        _update_dataset_in_head(api_key, slug, public_stats, lang, pred_db.get("predictions", []))
        _update_reader_vote_widget_in_foot(api_key, slug, lang)
        print(f"Updated tracker page: {lang}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
