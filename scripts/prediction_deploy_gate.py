#!/usr/bin/env python3
"""Refresh and validate the release snapshot used by prediction/publication deploys."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
import re

from mission_contract import MISSION_CONTRACT_VERSION, mission_contract_hash
from canonical_public_lexicon import LEXICON_VERSION

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = (
    "/opt/shared/reports"
    if os.path.exists("/opt/shared")
    else os.path.join(os.path.dirname(SCRIPT_DIR), "reports")
)
MANIFEST_PATH = os.path.join(REPORT_DIR, "article_release_manifest.json")
TRACKER_PATH = os.path.join(REPORT_DIR, "prediction_article_integrity.json")
SNAPSHOT_PATH = os.path.join(REPORT_DIR, "content_release_snapshot.json")
POLICY_PATH = os.path.join(SCRIPT_DIR, "prediction_integrity_policy.json")
GOVERNANCE_PATH = os.path.join(REPORT_DIR, "ecosystem_governance_audit.json")


def _load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part).strip()
    return proc.returncode, output


def _load_policy(tracker: dict) -> dict:
    policy = {
        "required_langs": ["ja", "en"],
        "max_orphan_oracle_articles": 197,
        "max_manifest_tracker_count_delta": 0,
        "max_report_timestamp_delta_seconds": 1800,
        "max_mojibake_strings": 0,
    }
    disk = _load_json(POLICY_PATH)
    if isinstance(disk, dict):
        policy.update(disk)
    tracker_policy = tracker.get("policy")
    if isinstance(tracker_policy, dict):
        policy.update({k: v for k, v in tracker_policy.items() if v is not None})
    return policy


ISO_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
JST_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} JST$")
MOJIBAKE_TOKENS = ("繧", "縺", "繝", "譌", "蛻", "逶", "荳", "鬮", "驥", "豁ｩ")


def _parse_report_timestamp(value: str) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    if ISO_TS_RE.match(value):
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if JST_TS_RE.match(value):
        jst = timezone(timedelta(hours=9))
        return datetime.strptime(value, "%Y-%m-%d %H:%M JST").replace(tzinfo=jst).astimezone(timezone.utc)
    return None


def _count_suspicious_mojibake(value) -> int:
    total = 0
    if isinstance(value, dict):
        for item in value.values():
            total += _count_suspicious_mojibake(item)
        return total
    if isinstance(value, list):
        for item in value:
            total += _count_suspicious_mojibake(item)
        return total
    if not isinstance(value, str):
        return 0
    score = sum(value.count(token) for token in MOJIBAKE_TOKENS)
    return 1 if score >= 3 else 0


def _build_snapshot(manifest: dict, tracker: dict, failures: list[str], warnings: list[str]) -> dict:
    manifest_counts = manifest.get("counts", {}) if isinstance(manifest, dict) else {}
    tracker_langs = tracker.get("langs", {}) if isinstance(tracker, dict) else {}
    published_total = int(manifest_counts.get("published_total") or 0)
    distribution_allowed = int(manifest_counts.get("distribution_allowed") or 0)
    approval_backlog = int(manifest_counts.get("high_risk_unapproved") or 0)
    distribution_ratio = round((distribution_allowed / published_total) * 100, 2) if published_total else 0.0
    approval_backlog_ratio = round((approval_backlog / published_total) * 100, 2) if published_total else 0.0
    coverage = {}
    formal_prediction_total = int(tracker.get("formal_prediction_total") or 0)
    for lang, payload in tracker_langs.items():
        public_rows = int(payload.get("public_rows") or 0)
        hidden_rows = int(payload.get("hidden_no_live_article") or 0)
        coverage[lang] = {
            "public_rows": public_rows,
            "public_in_play_rows": int(payload.get("public_in_play_rows") or 0),
            "public_awaiting_rows": int(payload.get("public_awaiting_rows") or 0),
            "public_resolved_rows": int(payload.get("public_resolved_rows") or 0),
            "hidden_no_live_article": hidden_rows,
            "coverage_pct": round((public_rows / formal_prediction_total) * 100, 2) if formal_prediction_total else 0.0,
        }
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mission_contract_version": MISSION_CONTRACT_VERSION,
        "mission_contract_hash": mission_contract_hash(),
        "lexicon_version": LEXICON_VERSION,
        "manifest_generated_at": manifest.get("generated_at", ""),
        "tracker_generated_at": tracker.get("generated_at", ""),
        "manifest_counts": manifest_counts,
        "tracker_summary": {
            "ghost_published_posts_total": tracker.get("ghost_published_posts_total"),
            "ghost_published_posts_release_scope": tracker.get("ghost_published_posts_release_scope"),
            "formal_prediction_total": tracker.get("formal_prediction_total"),
            "orphan_oracle_articles": (tracker.get("orphan_oracle_articles") or {}).get("count"),
            "coverage": coverage,
        },
        "operational_metrics": {
            "distribution_allowed_ratio_pct": distribution_ratio,
            "approval_backlog_ratio_pct": approval_backlog_ratio,
        },
        "failures": failures,
        "warnings": warnings,
        "ok": not failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Refresh manifest and tracker integrity before validating")
    parser.add_argument("--check-source-fetchability", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []

    if args.refresh:
        manifest_cmd = [sys.executable, os.path.join(SCRIPT_DIR, "build_article_release_manifest.py")]
        if args.check_source_fetchability:
            manifest_cmd.append("--check-source-fetchability")
        rc, out = _run(manifest_cmd)
        if rc != 0:
            failures.append(f"manifest_refresh_failed:{rc}")
            if out:
                warnings.append(f"manifest_refresh_output:{out[:500]}")

        tracker_cmd = [
            sys.executable,
            os.path.join(SCRIPT_DIR, "prediction_page_builder.py"),
            "--integrity-only",
            "--lang",
            "both",
            "--skip-deploy-gate",
        ]
        rc, out = _run(tracker_cmd)
        if rc != 0:
            failures.append(f"tracker_refresh_failed:{rc}")
            if out:
                warnings.append(f"tracker_refresh_output:{out[:500]}")

        governance_cmd = [
            sys.executable,
            os.path.join(SCRIPT_DIR, "ecosystem_governance_audit.py"),
            "--json-out",
            GOVERNANCE_PATH,
        ]
        rc, out = _run(governance_cmd)
        if rc != 0:
            failures.append(f"governance_refresh_failed:{rc}")
            if out:
                warnings.append(f"governance_refresh_output:{out[:500]}")

    manifest = _load_json(MANIFEST_PATH)
    tracker = _load_json(TRACKER_PATH)
    governance = _load_json(GOVERNANCE_PATH)
    if not manifest:
        failures.append("missing_article_release_manifest")
    if not tracker:
        failures.append("missing_prediction_article_integrity")
    if governance and int(governance.get("failed") or 0) > 0:
        failures.append(f"governance_audit_failed:{governance.get('failed')}")

    policy = _load_policy(tracker)
    required_langs = policy.get("required_langs") or ["ja", "en"]
    max_delta = int(policy.get("max_manifest_tracker_count_delta", 0))
    max_orphans = int(policy.get("max_orphan_oracle_articles", 0))
    max_report_timestamp_delta_seconds = int(policy.get("max_report_timestamp_delta_seconds", 1800))
    max_mojibake_strings = int(policy.get("max_mojibake_strings", 0))

    manifest_counts = manifest.get("counts", {}) if isinstance(manifest, dict) else {}
    tracker_langs = tracker.get("langs", {}) if isinstance(tracker, dict) else {}

    published_total = int(manifest_counts.get("published_total") or 0)
    tracker_published = int(tracker.get("ghost_published_posts_release_scope") or 0)
    if abs(published_total - tracker_published) > max_delta:
        failures.append(
            f"manifest_tracker_published_mismatch:{published_total}!={tracker_published}"
        )

    truth_blocked = int(manifest_counts.get("truth_blocked") or 0)
    if truth_blocked > 0:
        failures.append(f"truth_blocked_remaining:{truth_blocked}")

    missing_langs = [lang for lang in required_langs if lang not in tracker_langs]
    if missing_langs:
        failures.append("missing_integrity_langs:" + ",".join(missing_langs))

    for lang in required_langs:
        payload = tracker_langs.get(lang) or {}
        for key in (
            "public_rows",
            "public_in_play_rows",
            "public_awaiting_rows",
            "public_resolved_rows",
            "hidden_no_live_article",
            "same_lang_analysis",
            "cross_lang_fallback",
        ):
            if key not in payload:
                failures.append(f"missing_tracker_field:{lang}.{key}")

    orphan_count = int((tracker.get("orphan_oracle_articles") or {}).get("count") or 0)
    if orphan_count > max_orphans:
        failures.append(f"orphan_oracle_articles_exceeded:{orphan_count}>{max_orphans}")

    manifest_ts = _parse_report_timestamp(manifest.get("generated_at", ""))
    tracker_ts = _parse_report_timestamp(tracker.get("generated_at", ""))
    if manifest_ts and tracker_ts:
        ts_delta = abs(int((manifest_ts - tracker_ts).total_seconds()))
        if ts_delta > max_report_timestamp_delta_seconds:
            failures.append(
                f"report_timestamp_delta_exceeded:{ts_delta}>{max_report_timestamp_delta_seconds}"
            )
    else:
        warnings.append("report_timestamp_unparseable")

    mojibake_hits = _count_suspicious_mojibake(manifest) + _count_suspicious_mojibake(tracker)
    if mojibake_hits > max_mojibake_strings:
        failures.append(f"mojibake_strings_exceeded:{mojibake_hits}>{max_mojibake_strings}")

    distribution_allowed = int(manifest_counts.get("distribution_allowed") or 0)
    high_risk_unapproved = int(manifest_counts.get("high_risk_unapproved") or 0)
    if published_total and distribution_allowed <= 5:
        warnings.append(f"distribution_allowed_very_low:{distribution_allowed}/{published_total}")
    if published_total and high_risk_unapproved:
        warnings.append(f"high_risk_unapproved_backlog:{high_risk_unapproved}/{published_total}")

    snapshot = _build_snapshot(manifest, tracker, failures, warnings)
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2)

    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
