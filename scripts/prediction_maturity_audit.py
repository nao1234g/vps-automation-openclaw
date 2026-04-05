#!/usr/bin/env python3
"""Audit post-recovery prediction maturity with machine-readable metrics.

This is intentionally lighter than Playwright-based UI audits. It focuses on:
- M1: publicly scored sample growth and backlog compression
- M2: human baseline readiness
- M3: EN card completeness beyond shell integrity
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import socket
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import prediction_page_builder as ppb  # noqa: E402


LEGACY_EN_PLACEHOLDERS = (
    "English question copy pending.",
    "English trigger summary pending.",
    "English criteria summary pending.",
    "English scenario summary pending.",
    "English resolution summary pending.",
    "English evidence summary pending.",
)

GENERIC_EN_FALLBACKS = (
    "This forecast is judged against the published YES/NO resolution rule shown on this card.",
    "The key event is defined in the source forecast record and linked evidence trail.",
    "Resolution follows the published YES/NO condition for this forecast.",
    "This forecast resolved as accurate against its published YES/NO rule.",
    "This forecast resolved as missed against its published YES/NO rule.",
    "This forecast has a recorded resolution against its published YES/NO rule.",
    "The supporting evidence bundle for this resolution is recorded and fingerprinted below.",
    "case in the published scenario split",
)

TRACKER_BUTTON_PATTERNS = {
    "all": re.compile(r'data-view="all">[^<]*<span>(\d+)</span>'),
    "in_play": re.compile(r'data-view="inplay">[^<]*<span>(\d+)</span>'),
    "awaiting": re.compile(r'data-view="awaiting">[^<]*<span>(\d+)</span>'),
    "resolved": re.compile(r'data-view="resolved">[^<]*<span>(\d+)</span>'),
}


@dataclass
class FetchResult:
    url: str
    status: int
    body: str
    final_url: str
    content_type: str


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    return ctx


def fetch_text(url: str, timeout_seconds: int = 20, retries: int = 3) -> FetchResult:
    last_error: Exception | None = None
    for attempt in range(1, max(retries, 1) + 1):
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "nowpattern-prediction-maturity-audit/1.0"},
        )
        try:
            with urllib.request.urlopen(request, context=ssl_context(), timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
                return FetchResult(
                    url=url,
                    status=response.status,
                    body=body,
                    final_url=response.geturl(),
                    content_type=response.headers.get("content-type", ""),
                )
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt >= retries:
                raise
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_error = exc
            if attempt >= retries:
                raise
        time.sleep(min(2.0 * attempt, 6.0))
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"fetch_text failed without a captured exception for {url}")


def parse_tracker_counts(html: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, pattern in TRACKER_BUTTON_PATTERNS.items():
        match = pattern.search(html)
        counts[key] = int(match.group(1)) if match else 0
    return counts


def count_phrase_hits(text: str, phrases: tuple[str, ...]) -> dict[str, int]:
    return {phrase: text.count(phrase) for phrase in phrases}


def sum_hits(hit_map: dict[str, int]) -> int:
    return sum(hit_map.values())


def pct_progress(current: float, target: float) -> float:
    if target <= 0:
        return 100.0
    if current <= 0:
        return 0.0
    return round(min(current / target, 1.0) * 100.0, 1)


def ratio_progress(actual_ratio: float, target_ratio: float) -> float:
    if actual_ratio <= 0:
        return 100.0
    if actual_ratio <= target_ratio:
        return 100.0
    return round(min(target_ratio / actual_ratio, 1.0) * 100.0, 1)


def fallback_progress(generic_fallback_count: int, soft_cap: int = 50) -> float:
    if generic_fallback_count <= 0:
        return 100.0
    if soft_cap <= 0:
        return 0.0
    return round(max(0.0, 1.0 - (generic_fallback_count / soft_cap)) * 100.0, 1)


def local_canonical_snapshot() -> dict[str, Any]:
    db = ppb.load_prediction_db()
    stats = ppb._canonical_public_stats(db)
    return {
        "total": int(stats.get("total") or 0),
        "resolved": int(stats.get("resolved") or 0),
        "scorable": int(stats.get("scorable") or stats.get("public_brier_n") or 0),
        "not_scorable": int(stats.get("not_scorable") or 0),
        "accuracy_pct": stats.get("accuracy_pct"),
        "public_brier_index": stats.get("public_brier_index"),
    }


def evaluate_maturity(base_url: str) -> dict[str, Any]:
    canonical = local_canonical_snapshot()

    leaderboard = json.loads(fetch_text(urljoin(base_url, "/reader-predict/leaderboard")).body)
    top_forecasters = json.loads(fetch_text(urljoin(base_url, "/reader-predict/top-forecasters")).body)
    tracker_ja = fetch_text(urljoin(base_url, "/predictions/")).body
    tracker_en = fetch_text(urljoin(base_url, "/en/predictions/")).body
    leaderboard_en = fetch_text(urljoin(base_url, "/en/leaderboard/")).body

    ja_counts = parse_tracker_counts(tracker_ja)
    en_counts = parse_tracker_counts(tracker_en)
    legacy_en_hits = count_phrase_hits(tracker_en, LEGACY_EN_PLACEHOLDERS)
    generic_en_hits = count_phrase_hits(tracker_en, GENERIC_EN_FALLBACKS)

    scorable = canonical["scorable"]
    resolved = canonical["resolved"]
    awaiting = en_counts.get("awaiting", 0)

    m1_sample_progress = pct_progress(scorable, 150)
    backlog_ratio = (awaiting / resolved) if resolved else 0.0
    m1_backlog_progress = ratio_progress(backlog_ratio, 0.5)
    m1_progress = round((m1_sample_progress * 0.6) + (m1_backlog_progress * 0.4), 1)

    human = leaderboard.get("human_competition") or top_forecasters.get("human_competition") or {}
    sample = human.get("sample") or {}
    thresholds = human.get("thresholds") or {}
    unique_voters = int(sample.get("unique_voters") or 0)
    total_votes = int(sample.get("total_votes") or 0)
    resolved_votes = int(sample.get("resolved_votes") or 0)
    m2_unique_progress = pct_progress(unique_voters, float(thresholds.get("min_unique_voters") or 25))
    m2_vote_progress = pct_progress(total_votes, float(thresholds.get("min_total_votes") or 200))
    m2_resolved_progress = pct_progress(resolved_votes, float(thresholds.get("min_resolved_votes") or 20))
    m2_progress = round((m2_unique_progress + m2_vote_progress + m2_resolved_progress) / 3.0, 1)

    legacy_placeholder_count = sum_hits(legacy_en_hits)
    generic_fallback_count = sum_hits(generic_en_hits)
    m3_progress = round(
        ((100.0 if legacy_placeholder_count == 0 else 0.0) * 0.5)
        + (fallback_progress(generic_fallback_count) * 0.5),
        1,
    )

    recommendations: list[str] = []
    if awaiting > resolved:
        recommendations.append(
            f"Resolution backlog still dominates: awaiting={awaiting} vs resolved={resolved}. Compress the awaiting queue before marketing the score moat."
        )
    if scorable < 150:
        recommendations.append(
            f"Publicly scored sample is still {scorable}/150 ({m1_sample_progress:.1f}%). Prioritize more scored cases over more raw total predictions."
        )
    if not human.get("ready"):
        recommendations.append(
            f"Human baseline is still below unlock thresholds: {unique_voters} voters / {total_votes} votes / {resolved_votes} resolved votes."
        )
    if generic_fallback_count > 0:
        recommendations.append(
            f"EN tracker still leans on {generic_fallback_count} generic fallback snippets. Replace them with field-specific English substance before claiming content maturity."
        )

    return {
        "generated_at_epoch": int(time.time()),
        "base_url": base_url.rstrip("/"),
        "canonical_local": canonical,
        "live": {
            "leaderboard": leaderboard,
            "top_forecasters": top_forecasters,
            "tracker_ja": {
                "toolbar_counts": ja_counts,
                "vote_widget_count": tracker_ja.count('class="np-reader-vote"'),
                "sample_kpi_note_present": "重要KPIは総予測数ではなく公開採点サンプルです。" in tracker_ja,
            },
            "tracker_en": {
                "toolbar_counts": en_counts,
                "vote_widget_count": tracker_en.count('class="np-reader-vote"'),
                "sample_kpi_note_present": "The moat KPI is the publicly scored sample" in tracker_en,
                "legacy_placeholder_hits": legacy_en_hits,
                "legacy_placeholder_count": legacy_placeholder_count,
                "generic_fallback_hits": generic_en_hits,
                "generic_fallback_count": generic_fallback_count,
            },
            "leaderboard_en": {
                "baseline_building_copy_present": "baseline-building mode" in leaderboard_en,
                "human_baseline_cta_present": "Build the Human Baseline" in leaderboard_en,
                "beta_badge_present": "AI benchmark only (beta)" in leaderboard_en,
            },
        },
        "maturity": {
            "m1_scored_sample_and_backlog": {
                "progress_pct": m1_progress,
                "sample_progress_pct": m1_sample_progress,
                "backlog_progress_pct": m1_backlog_progress,
                "target_publicly_scored": 150,
                "current_publicly_scored": scorable,
                "awaiting_count": awaiting,
                "resolved_count": resolved,
                "awaiting_to_resolved_ratio": round(backlog_ratio, 3),
                "status": "good" if m1_progress >= 75 else "watch" if m1_progress >= 40 else "blocked",
            },
            "m2_human_baseline": {
                "progress_pct": m2_progress,
                "human_public_ready": bool(human.get("ready")),
                "unique_voters": unique_voters,
                "total_votes": total_votes,
                "resolved_votes": resolved_votes,
                "unique_voter_progress_pct": m2_unique_progress,
                "total_vote_progress_pct": m2_vote_progress,
                "resolved_vote_progress_pct": m2_resolved_progress,
                "thresholds": thresholds,
                "status": "good" if m2_progress >= 75 else "watch" if m2_progress >= 40 else "blocked",
            },
            "m3_en_card_completeness": {
                "progress_pct": m3_progress,
                "legacy_placeholder_count": legacy_placeholder_count,
                "generic_fallback_count": generic_fallback_count,
                "status": "good" if m3_progress >= 75 else "watch" if m3_progress >= 40 else "blocked",
            },
        },
        "recommendations": recommendations,
    }


def markdown_summary(report: dict[str, Any]) -> str:
    m1 = report["maturity"]["m1_scored_sample_and_backlog"]
    m2 = report["maturity"]["m2_human_baseline"]
    m3 = report["maturity"]["m3_en_card_completeness"]
    lines = [
        "# Prediction Maturity Audit",
        "",
        f"- Generated at epoch: `{report['generated_at_epoch']}`",
        f"- Base URL: `{report['base_url']}`",
        "",
        "## Snapshot",
        "",
        f"- Canonical local: `{report['canonical_local']['total']} total / {report['canonical_local']['resolved']} resolved / {report['canonical_local']['scorable']} publicly scored`",
        f"- M1 scored sample/backlog: `{m1['progress_pct']:.1f}%`",
        f"- M2 human baseline: `{m2['progress_pct']:.1f}%`",
        f"- M3 EN card completeness: `{m3['progress_pct']:.1f}%`",
        "",
        "## Recommendations",
        "",
    ]
    recommendations = report.get("recommendations") or ["No blocking recommendation."]
    lines.extend(f"- {item}" for item in recommendations)
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Audit post-recovery prediction maturity.")
    parser.add_argument("--base-url", default="https://nowpattern.com", help="Public base URL")
    parser.add_argument("--json-out", help="Optional JSON report path")
    parser.add_argument("--md-out", help="Optional Markdown report path")
    args = parser.parse_args()

    report = evaluate_maturity(args.base_url.rstrip("/") + "/")

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.md_out:
        out_path = Path(args.md_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown_summary(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "m1_progress_pct": report["maturity"]["m1_scored_sample_and_backlog"]["progress_pct"],
                "m2_progress_pct": report["maturity"]["m2_human_baseline"]["progress_pct"],
                "m3_progress_pct": report["maturity"]["m3_en_card_completeness"]["progress_pct"],
            },
            ensure_ascii=False,
        )
    )
    print("PASS: prediction maturity audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
