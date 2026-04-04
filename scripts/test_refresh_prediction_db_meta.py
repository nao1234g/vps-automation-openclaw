#!/usr/bin/env python3
"""Regression checks for prediction_db canonical refresh helpers."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import refresh_prediction_db_meta as rpm  # noqa: E402


def test_canonicalize_prediction_article_links_infers_en_from_url() -> None:
    payload = {
        "predictions": [
            {
                "prediction_id": "NP-TEST-1",
                "article_links": [
                    {
                        "slug": "sample-english-article",
                        "url": "https://nowpattern.com/en/sample-english-article/",
                        "lang": "ja",
                    }
                ],
            }
        ]
    }
    changed = rpm.canonicalize_prediction_article_links(payload)
    assert changed == 1, changed
    assert payload["predictions"][0]["article_links"][0]["lang"] == "en"


def test_canonicalize_prediction_article_links_infers_en_from_slug_prefix() -> None:
    payload = {
        "predictions": [
            {
                "prediction_id": "NP-TEST-2",
                "article_links": [
                    {
                        "slug": "en-sample-english-article",
                        "url": "",
                        "lang": "",
                    }
                ],
            }
        ]
    }
    changed = rpm.canonicalize_prediction_article_links(payload)
    assert changed == 1, changed
    assert payload["predictions"][0]["article_links"][0]["lang"] == "en"


def run() -> None:
    test_canonicalize_prediction_article_links_infers_en_from_url()
    test_canonicalize_prediction_article_links_infers_en_from_slug_prefix()
    print("PASS: refresh_prediction_db_meta article-link normalization checks")


if __name__ == "__main__":
    run()
