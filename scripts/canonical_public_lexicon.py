#!/usr/bin/env python3
"""Canonical public vocabulary and metrics for Nowpattern."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from report_authority import load_authoritative_json
from runtime_boundary import shared_or_local_path


SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_DIR = shared_or_local_path(
    script_file=__file__,
    shared_path="/opt/shared/reports",
    local_path=SCRIPT_DIR.parent / "reports",
)
SNAPSHOT_PATH = REPORT_DIR / "content_release_snapshot.json"
DEFAULT_OPERATING_SINCE = "2026"
LEXICON_VERSION = "2026-03-31-public-lexicon-v4"


BRAND_COPY = {
    "ja": {
        "platform_name": "検証可能な予測プラットフォーム",
        "oracle_subtitle": "予測オラクル",
        "about_title": "Nowpatternとは | 検証可能な予測プラットフォーム",
        "about_meta_title": "Nowpatternとは | 検証可能な予測プラットフォーム",
        "about_meta_description": (
            "Nowpatternは、分析・予測・判定記録を同じ公開ルールで運用する、"
            "検証可能な予測プラットフォームです。"
        ),
    },
    "en": {
        "platform_name": "Verifiable Forecast Platform",
        "oracle_subtitle": "Prediction Oracle",
        "about_title": "About Nowpattern | Verifiable Forecast Platform",
        "about_meta_title": "About Nowpattern | Verifiable Forecast Platform",
        "about_meta_description": (
            "Nowpattern is a verifiable forecast platform that publishes analysis, "
            "forecasts, and resolution records under one public rule set."
        ),
    },
}


TRACKER_COPY = {
    "ja": {
        "view_all": "すべて",
        "view_in_play": "進行中",
        "view_awaiting": "判定待ち",
        "view_resolved": "判定済み",
        "section_in_play": "進行中の予測",
        "section_awaiting": "判定待ちの予測",
        "section_resolved": "判定済みの予測",
        "section_awaiting_note": "イベントは発生済みですが、証拠確認と判定記録の最終反映を待っている予測です。",
        "compact_status": "判定待ち",
        "compact_article_link": "分析記事を見る",
        "compact_fallback_link": "英語記事を見る",
        "search_placeholder": "キーワードで絞り込み...",
        "last_updated": "最終更新: {now}",
    },
    "en": {
        "view_all": "All",
        "view_in_play": "In Play",
        "view_awaiting": "Awaiting Verification",
        "view_resolved": "Resolved",
        "section_in_play": "Forecasts In Play",
        "section_awaiting": "Forecasts Awaiting Verification",
        "section_resolved": "Resolved Forecasts",
        "section_awaiting_note": "The event has occurred, but the evidence check and resolution record are still being finalized.",
        "compact_status": "Awaiting Verification",
        "compact_article_link": "Open analysis article",
        "compact_fallback_link": "Open Japanese article",
        "search_placeholder": "Filter by keyword...",
        "last_updated": "Last updated: {now}",
    },
}


ABOUT_COPY = {
    "ja": {
        "hero_title": "検証可能な予測プラットフォーム",
        "hero_intro": (
            "Nowpatternは、ニュース解説だけで終わらず、分析から予測を公開し、"
            "その予測を判定まで追いかけるためのプラットフォームです。"
        ),
        "hero_body": (
            "公開トラッカー、分析記事、判定基準、整合性監査のすべてが、"
            "同じ語彙と同じ公開ルールでつながっています。"
            "公開トラッカーでは予測自体を先に公開し、同じ言語の記事リンクは利用可能になり次第表示します。"
        ),
        "metric_registered": "全登録予測数",
        "metric_public_cards": "公開中の予測カード",
        "metric_resolved_cards": "判定済み公開カード",
        "metric_operating_since": "運用開始",
        "card_registered_note": "prediction DB に登録されている全予測",
        "card_public_note": "日本語の公開トラッカー上で現在表示している予測カード",
        "card_resolved_note": "日本語の公開トラッカー上で判定済みになっているカード",
        "card_operating_note": "公開運用を開始した年",
        "section_how_title": "Nowpatternでできること",
        "section_how_points": [
            "予測の背景にある分析記事を読む",
            "進行中・判定待ち・判定済みの予測を追う",
            "判定基準と整合性監査を確認する",
        ],
        "footer_links": [
            ("予測トラッカー", "/predictions/"),
            ("力学で探す", "/taxonomy/"),
            ("予測手法", "/forecasting-methodology/"),
            ("整合性・監査", "/integrity-audit/"),
        ],
    },
    "en": {
        "hero_title": "Verifiable Forecast Platform",
        "hero_intro": (
            "Nowpattern is not just a news explainer. It is a forecast platform that turns "
            "analysis into public forecasts and carries those forecasts through resolution."
        ),
        "hero_body": (
            "Public tracker cards, source articles, resolution rules, and integrity pages all follow "
            "the same vocabulary and the same public release rules. The public tracker can show the "
            "forecast before article publication, and same-language article links appear as they go live."
        ),
        "metric_registered": "Registered Forecasts",
        "metric_public_cards": "Public Tracker Cards",
        "metric_resolved_cards": "Resolved Public Cards",
        "metric_operating_since": "Operating Since",
        "card_registered_note": "All forecasts registered in the prediction database",
        "card_public_note": "Forecast cards currently visible on the English public tracker",
        "card_resolved_note": "English public tracker cards that already show a resolved outcome",
        "card_operating_note": "Year public operations began",
        "section_how_title": "What You Can Do Here",
        "section_how_points": [
            "Read the analysis article behind a forecast",
            "Track forecasts in play, awaiting verification, and resolved",
            "Inspect resolution rules and integrity audits",
        ],
        "footer_links": [
            ("Prediction Tracker", "/en/predictions/"),
            ("Explore Dynamics", "/en/taxonomy/"),
            ("Forecasting Methodology", "/en/forecasting-methodology/"),
            ("Integrity & Audit", "/en/integrity-audit/"),
        ],
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    return load_authoritative_json(path)


def load_release_snapshot() -> dict[str, Any]:
    return _read_json(SNAPSHOT_PATH)


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_brand_copy(lang: str) -> dict[str, str]:
    return dict(BRAND_COPY["en" if lang == "en" else "ja"])


def get_tracker_copy(lang: str) -> dict[str, str]:
    return dict(TRACKER_COPY["en" if lang == "en" else "ja"])


def get_about_copy(lang: str) -> dict[str, Any]:
    return dict(ABOUT_COPY["en" if lang == "en" else "ja"])


def get_public_metric_bundle(lang: str, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    lang_key = "en" if lang == "en" else "ja"
    payload = snapshot or load_release_snapshot()
    tracker = payload.get("tracker_summary") or {}
    coverage = ((tracker.get("coverage") or {}).get(lang_key) or {})
    return {
        "registered_forecasts": _safe_int(tracker.get("formal_prediction_total")),
        "public_tracker_cards": _safe_int(coverage.get("public_rows")),
        "resolved_public_cards": _safe_int(coverage.get("public_resolved_rows")),
        "in_play_public_cards": _safe_int(coverage.get("public_in_play_rows")),
        "awaiting_public_cards": _safe_int(coverage.get("public_awaiting_rows")),
        "operating_since": DEFAULT_OPERATING_SINCE,
    }
