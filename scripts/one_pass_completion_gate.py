#!/usr/bin/env python3
"""Single-shot completion gate for truth/UI/crawl/drift/governance proof."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from canonical_public_lexicon import LEXICON_VERSION
from mission_contract import MISSION_CONTRACT_VERSION, assert_mission_handshake, mission_contract_hash
from report_authority import load_authoritative_json


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORT_DIR = Path("/opt/shared/reports") if Path("/opt/shared").exists() else REPO_ROOT / "reports"
POLICY_PATH = SCRIPT_DIR / "one_pass_completion_policy.json"
REPORT_PATH = REPORT_DIR / "one_pass_completion_gate.json"
DEFAULT_SUBPROCESS_TIMEOUT_SECONDS = int(os.environ.get("NOWPATTERN_ONE_PASS_SUBPROCESS_TIMEOUT_SECONDS") or 900)
PREDICTION_GATE_TIMEOUT_SECONDS = int(
    os.environ.get("NOWPATTERN_ONE_PASS_PREDICTION_GATE_TIMEOUT_SECONDS") or 1800
)
GOVERNANCE_TIMEOUT_SECONDS = int(
    os.environ.get("NOWPATTERN_ONE_PASS_GOVERNANCE_TIMEOUT_SECONDS") or DEFAULT_SUBPROCESS_TIMEOUT_SECONDS
)
SITE_UI_TIMEOUT_SECONDS = int(
    os.environ.get("NOWPATTERN_ONE_PASS_SITE_UI_TIMEOUT_SECONDS") or DEFAULT_SUBPROCESS_TIMEOUT_SECONDS
)
E2E_TIMEOUT_SECONDS = int(
    os.environ.get("NOWPATTERN_ONE_PASS_E2E_TIMEOUT_SECONDS") or DEFAULT_SUBPROCESS_TIMEOUT_SECONDS
)
FULL_CRAWL_TIMEOUT_SECONDS = int(
    os.environ.get("NOWPATTERN_ONE_PASS_FULL_CRAWL_TIMEOUT_SECONDS") or DEFAULT_SUBPROCESS_TIMEOUT_SECONDS
)
DRIFT_TIMEOUT_SECONDS = int(
    os.environ.get("NOWPATTERN_ONE_PASS_DRIFT_TIMEOUT_SECONDS") or 300
)
IS_LIVE_HOST = Path(__file__).resolve().as_posix().startswith("/opt/shared/")
DEPLOY_GATE_REPORT_PATH = REPORT_DIR / "content_release_snapshot.json"
GOVERNANCE_REPORT_PATH = REPORT_DIR / "ecosystem_governance_audit.json"
FULL_CRAWL_REPORT_PATH = REPORT_DIR / "synthetic_user_crawler" / "latest.json"
SITE_UI_REPORT_PATH = REPORT_DIR / "site_ui_smoke_audit.json"
E2E_REPORT_PATH = REPORT_DIR / "playwright_e2e_predictions.json"
MISSION_HANDSHAKE = assert_mission_handshake(
    "one_pass_completion_gate",
    "prove a release is truly green across truth, UI, crawl, governance, drift, and backlog thresholds",
)


def _load_policy() -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "base_url": "https://nowpattern.com",
        "min_distribution_allowed_ratio_pct": 30.0,
        "max_high_risk_unapproved_ratio_pct": 25.0,
        "require_truth_blocked_zero": True,
        "require_orphan_zero": True,
        "max_report_age_seconds": 6 * 60 * 60,
        "reuse_fresh_artifacts_seconds": 45 * 60,
    }
    if POLICY_PATH.exists():
        disk = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        if isinstance(disk, dict):
            defaults.update(disk)
    return defaults


def _run(command: list[str], timeout_seconds: int = DEFAULT_SUBPROCESS_TIMEOUT_SECONDS) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "").strip()
        stderr = (exc.stderr or "").strip()
        output = "\n".join(part for part in [stdout, stderr, f"TIMEOUT:{timeout_seconds}s"] if part).strip()
        return 124, output
    output = "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part).strip()
    return proc.returncode, output


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=str(path.parent)) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_artifact(path: Path, *, refresh: bool) -> dict[str, Any]:
    if refresh or IS_LIVE_HOST:
        return _load_json(path)
    return load_authoritative_json(path)


def _artifact_age_seconds(payload: dict[str, Any]) -> int | None:
    if not payload:
        return None
    epoch = int(payload.get("generated_at_epoch") or 0)
    if epoch > 0:
        return int(time.time()) - epoch
    generated_at = payload.get("generated_at")
    if isinstance(generated_at, str):
        try:
            parsed = datetime.strptime(generated_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            return int(time.time() - parsed.timestamp())
        except Exception:
            return None
    return None


def _artifact_ok(name: str, payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    if name == "prediction_deploy_gate":
        return bool(payload.get("ok"))
    if name == "ecosystem_governance_audit":
        return int(payload.get("failed") or 0) == 0
    if name == "synthetic_user_crawler":
        return int(payload.get("failed") or 0) == 0
    if name == "site_ui_smoke_audit":
        return int((payload.get("summary") or {}).get("failed") or 0) == 0
    if name == "playwright_e2e_predictions":
        return bool(payload.get("ok"))
    return False


def _parse_json_object(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    for line in text.splitlines():
        candidate = line.strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            try:
                parsed = json.loads(candidate)
            except Exception:
                continue
            if isinstance(parsed, dict):
                return parsed
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def evaluate_completion(
    *,
    deploy_gate: dict[str, Any],
    governance_failed: int,
    crawl_failed: int,
    ui_failed: int,
    e2e_ok: bool,
    drift_ok: bool,
    policy: dict[str, Any],
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    manifest_counts = deploy_gate.get("manifest_counts") or {}
    tracker_summary = deploy_gate.get("tracker_summary") or {}
    operational = deploy_gate.get("operational_metrics") or {}

    published_total = int(manifest_counts.get("published_total") or 0)
    truth_blocked = int(manifest_counts.get("truth_blocked") or 0)
    high_risk_unapproved = int(manifest_counts.get("high_risk_unapproved") or 0)
    distribution_allowed = int(manifest_counts.get("distribution_allowed") or 0)
    orphans = int(tracker_summary.get("orphan_oracle_articles") or 0)
    ratio = float(operational.get("distribution_allowed_ratio_pct") or 0.0)
    backlog_ratio = float(operational.get("approval_backlog_ratio_pct") or 0.0)

    if policy.get("require_truth_blocked_zero", True) and truth_blocked != 0:
        failures.append(f"truth_blocked_remaining:{truth_blocked}")
    if policy.get("require_orphan_zero", True) and orphans != 0:
        failures.append(f"orphan_oracle_articles_remaining:{orphans}")
    min_ratio = float(policy.get("min_distribution_allowed_ratio_pct", 0.0) or 0.0)
    if ratio < min_ratio:
        failures.append(f"distribution_allowed_ratio_below_threshold:{ratio}<{min_ratio}")
    max_backlog = float(policy.get("max_high_risk_unapproved_ratio_pct", 100.0) or 100.0)
    if backlog_ratio > max_backlog:
        failures.append(f"high_risk_unapproved_ratio_exceeded:{backlog_ratio}>{max_backlog}")
    if governance_failed != 0:
        failures.append(f"governance_failed:{governance_failed}")
    if crawl_failed != 0:
        failures.append(f"full_crawl_failed:{crawl_failed}")
    if ui_failed != 0:
        failures.append(f"site_ui_failed:{ui_failed}")
    if not e2e_ok:
        failures.append("prediction_e2e_failed")
    if not drift_ok:
        failures.append("live_repo_drift_detected")

    if published_total and high_risk_unapproved:
        warnings.append(f"high_risk_unapproved_remaining:{high_risk_unapproved}/{published_total}")
    if published_total and distribution_allowed == published_total:
        warnings.append("distribution_allowed_full_parity_reached")
    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the one-pass completion proof gate.")
    parser.add_argument("--refresh", action="store_true", help="Refresh dependent reports before evaluation")
    parser.add_argument(
        "--force-refresh-all",
        action="store_true",
        help="Force every dependent artifact to rerun even if a fresh green report already exists.",
    )
    parser.add_argument("--base-url", default=None, help="Override base URL")
    parser.add_argument("--json-out", default=str(REPORT_PATH), help="Optional JSON report path")
    args = parser.parse_args()

    policy = _load_policy()
    base_url = (args.base_url or policy.get("base_url") or "https://nowpattern.com").rstrip("/")
    drift_host = "local" if IS_LIVE_HOST else os.environ.get("NOWPATTERN_VPS_HOST", "root@163.44.124.123")

    refresh_commands: list[tuple[str, list[str], int, Path]] = [
        (
            "prediction_deploy_gate",
            [
                sys.executable,
                str(SCRIPT_DIR / "prediction_deploy_gate.py"),
                "--json-out",
                str(DEPLOY_GATE_REPORT_PATH),
            ],
            PREDICTION_GATE_TIMEOUT_SECONDS,
            DEPLOY_GATE_REPORT_PATH,
        ),
        (
            "synthetic_user_crawler",
            [
                sys.executable,
                str(SCRIPT_DIR / "synthetic_user_crawler.py"),
                "--base-url",
                base_url,
                "--json-out",
                str(FULL_CRAWL_REPORT_PATH),
            ],
            FULL_CRAWL_TIMEOUT_SECONDS,
            FULL_CRAWL_REPORT_PATH,
        ),
        (
            "ecosystem_governance_audit",
            [
                sys.executable,
                str(SCRIPT_DIR / "ecosystem_governance_audit.py"),
                "--json-out",
                str(GOVERNANCE_REPORT_PATH),
            ],
            GOVERNANCE_TIMEOUT_SECONDS,
            GOVERNANCE_REPORT_PATH,
        ),
        (
            "site_ui_smoke_audit",
            [
                sys.executable,
                str(SCRIPT_DIR / "site_ui_smoke_audit.py"),
                "--base-url",
                base_url,
                "--json-out",
                str(SITE_UI_REPORT_PATH),
            ],
            SITE_UI_TIMEOUT_SECONDS,
            SITE_UI_REPORT_PATH,
        ),
        (
            "playwright_e2e_predictions",
            [
                sys.executable,
                str(SCRIPT_DIR / "playwright_e2e_predictions.py"),
                "--lang",
                "both",
                "--device",
                "both",
                "--json-out",
                str(E2E_REPORT_PATH),
            ],
            E2E_TIMEOUT_SECONDS,
            E2E_REPORT_PATH,
        ),
    ]
    if args.refresh:
        refresh_commands[0][1].extend(["--refresh", "--check-source-fetchability"])

    raw_results: dict[str, dict[str, Any]] = {}
    reuse_fresh_artifacts_seconds = int(policy.get("reuse_fresh_artifacts_seconds", 45 * 60) or 45 * 60)
    for name, command, timeout_seconds, artifact_path in refresh_commands:
        skipped = False
        rc = 0
        output = ""
        existing_payload = _load_json(artifact_path) if args.refresh and artifact_path.exists() else {}
        artifact_age = _artifact_age_seconds(existing_payload)
        if (
            args.refresh
            and not args.force_refresh_all
            and existing_payload
            and artifact_age is not None
            and artifact_age <= reuse_fresh_artifacts_seconds
            and _artifact_ok(name, existing_payload)
        ):
            skipped = True
        elif args.refresh:
            rc, output = _run(command, timeout_seconds=timeout_seconds)
        raw_results[name] = {
            "ok": skipped or rc == 0,
            "returncode": rc,
            "command": command,
            "timeout_seconds": timeout_seconds,
            "output": output,
            "json": _parse_json_object(output),
            "skipped_refresh": skipped,
            "artifact_path": str(artifact_path),
            "artifact_age_seconds": artifact_age,
        }

    deploy_json = _load_artifact(DEPLOY_GATE_REPORT_PATH, refresh=args.refresh)
    governance_json = _load_artifact(GOVERNANCE_REPORT_PATH, refresh=args.refresh)
    crawl_json = _load_artifact(FULL_CRAWL_REPORT_PATH, refresh=args.refresh)
    smoke_report = _load_artifact(SITE_UI_REPORT_PATH, refresh=args.refresh)
    e2e_report = _load_artifact(E2E_REPORT_PATH, refresh=args.refresh)

    drift_command = [
        sys.executable,
        str(SCRIPT_DIR / "check_live_repo_drift.py"),
        "--host",
        drift_host,
    ]
    drift_rc, drift_output = _run(drift_command, timeout_seconds=DRIFT_TIMEOUT_SECONDS)
    raw_results["check_live_repo_drift"] = {
        "ok": drift_rc == 0,
        "returncode": drift_rc,
        "command": drift_command,
        "timeout_seconds": DRIFT_TIMEOUT_SECONDS,
        "output": drift_output,
        "json": _parse_json_object(drift_output),
    }
    drift_ok = bool(raw_results["check_live_repo_drift"]["ok"])

    smoke_summary = (smoke_report.get("summary") or {}) if smoke_report else {}
    e2e_ok = bool(e2e_report.get("ok")) if e2e_report else False

    failures, warnings = evaluate_completion(
        deploy_gate=deploy_json,
        governance_failed=int(governance_json.get("failed") or 0),
        crawl_failed=int(crawl_json.get("failed") or 0),
        ui_failed=int(smoke_summary.get("failed") or 0),
        e2e_ok=e2e_ok,
        drift_ok=drift_ok,
        policy=policy,
    )
    max_report_age_seconds = int(policy.get("max_report_age_seconds", 6 * 60 * 60) or 6 * 60 * 60)
    artifact_map = {
        "prediction_deploy_gate": deploy_json,
        "ecosystem_governance_audit": governance_json,
        "synthetic_user_crawler": crawl_json,
        "site_ui_smoke_audit": smoke_report,
        "playwright_e2e_predictions": e2e_report,
    }
    for name, payload in artifact_map.items():
        if not payload:
            failures.append(f"{name}_missing_report")
            continue
        age_seconds = _artifact_age_seconds(payload)
        if age_seconds is None:
            failures.append(f"{name}_missing_generated_at")
        elif age_seconds > max_report_age_seconds:
            failures.append(f"{name}_stale:{age_seconds}>{max_report_age_seconds}")

    if args.refresh and not raw_results["prediction_deploy_gate"]["ok"]:
        failures.append(f"prediction_deploy_gate_command_failed:{raw_results['prediction_deploy_gate']['returncode']}")
    if not deploy_json:
        failures.append("prediction_deploy_gate_missing_json")
    if args.refresh and not raw_results["ecosystem_governance_audit"]["ok"]:
        failures.append(f"governance_command_failed:{raw_results['ecosystem_governance_audit']['returncode']}")
    if not governance_json:
        failures.append("governance_missing_json")
    if args.refresh and not raw_results["synthetic_user_crawler"]["ok"]:
        failures.append(f"full_crawl_command_failed:{raw_results['synthetic_user_crawler']['returncode']}")
    if not crawl_json:
        failures.append("full_crawl_missing_json")
    if args.refresh and not raw_results["site_ui_smoke_audit"]["ok"]:
        failures.append(f"site_ui_command_failed:{raw_results['site_ui_smoke_audit']['returncode']}")
    if not smoke_report:
        failures.append("site_ui_missing_json")
    if args.refresh and not raw_results["playwright_e2e_predictions"]["ok"]:
        failures.append(
            f"prediction_e2e_command_failed:{raw_results['playwright_e2e_predictions']['returncode']}"
        )
    if not e2e_report:
        failures.append("prediction_e2e_missing_report")

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_epoch": int(time.time()),
        "mission_contract_version": MISSION_CONTRACT_VERSION,
        "mission_contract_hash": mission_contract_hash(),
        "lexicon_version": LEXICON_VERSION,
        "policy": policy,
        "mission_handshake": MISSION_HANDSHAKE,
        "checks": {
            "prediction_deploy_gate": {
                "ok": bool(deploy_json.get("ok")) and ("prediction_deploy_gate_missing_json" not in failures),
                "json": deploy_json,
            },
            "ecosystem_governance_audit": {
                "ok": int(governance_json.get("failed") or 0) == 0 and bool(governance_json),
                "failed": governance_json.get("failed"),
                "total": governance_json.get("total"),
            },
            "synthetic_user_crawler": {
                "ok": int(crawl_json.get("failed") or 0) == 0 and bool(crawl_json),
                "failed": crawl_json.get("failed"),
                "total": crawl_json.get("total"),
            },
            "site_ui_smoke_audit": {
                "ok": int(smoke_summary.get("failed") or 0) == 0 and bool(smoke_report),
                "summary": smoke_summary,
            },
            "playwright_e2e_predictions": {
                "ok": e2e_ok,
                "summary": e2e_report.get("summary") if e2e_report else {},
                "results": e2e_report.get("results") if e2e_report else [],
            },
            "check_live_repo_drift": {
                "ok": drift_ok,
                "output_tail": raw_results["check_live_repo_drift"]["output"][-1200:],
            },
        },
        "failures": failures,
        "warnings": warnings,
        "ok": not failures,
    }

    out_path = Path(args.json_out)
    _write_json_atomic(out_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
