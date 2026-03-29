#!/usr/bin/env python3
"""Compare key local repo files against the VPS source of truth."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = os.environ.get("NOWPATTERN_VPS_HOST", "root@163.44.124.123")

TARGETS = [
    {
        "name": "prediction_db",
        "kind": "json_prediction_db",
        "local": REPO_ROOT / "scripts" / "prediction_db.json",
        "remote": "/opt/shared/scripts/prediction_db.json",
    },
    {
        "name": "prediction_page_builder",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "prediction_page_builder.py",
        "remote": "/opt/shared/scripts/prediction_page_builder.py",
    },
    {
        "name": "reader_prediction_api",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "reader_prediction_api.py",
        "remote": "/opt/shared/scripts/reader_prediction_api.py",
    },
    {
        "name": "refresh_prediction_db_meta",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "refresh_prediction_db_meta.py",
        "remote": "/opt/shared/scripts/refresh_prediction_db_meta.py",
    },
    {
        "name": "prediction_state_utils",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "prediction_state_utils.py",
        "remote": "/opt/shared/scripts/prediction_state_utils.py",
    },
    {
        "name": "prediction_state_integrity_gate",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "prediction_state_integrity_gate.py",
        "remote": "/opt/shared/scripts/prediction_state_integrity_gate.py",
    },
    {
        "name": "playwright_e2e_predictions",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "playwright_e2e_predictions.py",
        "remote": "/opt/shared/scripts/playwright_e2e_predictions.py",
    },
    {
        "name": "fix_global_language_switcher",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "fix_global_language_switcher.py",
        "remote": "/opt/shared/scripts/fix_global_language_switcher.py",
    },
    {
        "name": "fix_ghost_content_links",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "fix_ghost_content_links.py",
        "remote": "/opt/shared/scripts/fix_ghost_content_links.py",
    },
    {
        "name": "live_site_availability_check",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "live_site_availability_check.py",
        "remote": "/opt/shared/scripts/live_site_availability_check.py",
    },
    {
        "name": "site_guard_runner",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "site_guard_runner.py",
        "remote": "/opt/shared/scripts/site_guard_runner.py",
    },
    {
        "name": "site_ui_smoke_audit",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "site_ui_smoke_audit.py",
        "remote": "/opt/shared/scripts/site_ui_smoke_audit.py",
    },
    {
        "name": "install_site_ui_guard",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "install_site_ui_guard.py",
        "remote": "/opt/shared/scripts/install_site_ui_guard.py",
    },
    {
        "name": "install_en_article_route_guard",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "install_en_article_route_guard.py",
        "remote": "/opt/shared/scripts/install_en_article_route_guard.py",
    },
    {
        "name": "ghost_ui_settings",
        "kind": "ghost_ui_settings",
        "local": REPO_ROOT / "scripts" / "fix_global_language_switcher.py",
        "remote": "/var/www/nowpattern/content/data/ghost.db",
    },
    {
        "name": "ghost_content_hygiene",
        "kind": "ghost_content_hygiene",
        "local": REPO_ROOT / "scripts" / "fix_ghost_content_links.py",
        "remote": "/var/www/nowpattern/content/data/ghost.db",
    },
]


def choose_ssh_bin() -> str:
    override = os.environ.get("NP_SSH_BIN")
    if override and Path(override).exists():
        return override

    windows_builtin = Path(r"C:\Windows\System32\OpenSSH\ssh.exe")
    if windows_builtin.exists():
        return str(windows_builtin)

    candidate = shutil.which("ssh")
    if candidate and ".sbx-denybin" not in candidate.lower():
        return candidate

    raise FileNotFoundError("No usable ssh binary found. Set NP_SSH_BIN if needed.")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def summarize_prediction_db_bytes(data: bytes) -> dict:
    payload = json.loads(data.decode("utf-8"))
    preds = payload.get("predictions") if isinstance(payload, dict) else payload
    preds = preds or []
    status_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}
    resolution_criteria_present = 0
    authoritative_sources_present = 0
    initial_prob_present = 0

    for pred in preds:
        status = str(pred.get("status") or "NONE")
        tier = str(pred.get("official_score_tier") or "NONE")
        status_counts[status] = status_counts.get(status, 0) + 1
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        if pred.get("resolution_criteria") is not None:
            resolution_criteria_present += 1
        if "authoritative_sources" in pred:
            authoritative_sources_present += 1
        if pred.get("initial_prob") is not None:
            initial_prob_present += 1

    return {
        "kind": "json_prediction_db",
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "predictions": len(preds),
        "status_counts": status_counts,
        "official_score_tier_counts": tier_counts,
        "resolution_criteria_present": resolution_criteria_present,
        "authoritative_sources_present": authoritative_sources_present,
        "initial_prob_present": initial_prob_present,
    }


def summarize_text_bytes(data: bytes) -> dict:
    text = data.decode("utf-8")
    return {
        "kind": "text",
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "lines": text.count("\n") + (0 if not text else 1),
    }


def load_fix_global_language_switcher_module():
    path = REPO_ROOT / "scripts" / "fix_global_language_switcher.py"
    spec = importlib.util.spec_from_file_location("np_fix_global_language_switcher", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summarize_local_ghost_ui_settings() -> dict:
    module = load_fix_global_language_switcher_module()
    return {
        "kind": "ghost_ui_settings",
        "has_language_switcher": True,
        "has_ui_guard": True,
        "portal_button_signup_text": getattr(module, "DEFAULT_PORTAL_SIGNUP_TEXT", ""),
        "portal_button_style": getattr(module, "DEFAULT_PORTAL_BUTTON_STYLE", ""),
        "portal_button": getattr(module, "DEFAULT_PORTAL_BUTTON", ""),
        "portal_plans": getattr(module, "DEFAULT_PORTAL_PLANS", ""),
    }


def summarize_local_ghost_content_hygiene() -> dict:
    return {
        "kind": "ghost_content_hygiene",
        "stale_en_article_links": 0,
        "stale_en_predictions_links": 0,
        "stale_full_en_article_links": 0,
        "settings_stale_hits": 0,
    }


def summarize_local(target: dict) -> dict:
    path = Path(target["local"])
    if not path.exists():
        return {"missing": True, "path": str(path)}

    if target["kind"] == "ghost_ui_settings":
        summary = summarize_local_ghost_ui_settings()
    elif target["kind"] == "ghost_content_hygiene":
        summary = summarize_local_ghost_content_hygiene()
    else:
        data = path.read_bytes()
        summary = (
            summarize_prediction_db_bytes(data)
            if target["kind"] == "json_prediction_db"
            else summarize_text_bytes(data)
        )
    summary["path"] = str(path)
    return summary


def summarize_remote(ssh_bin: str, host: str, target: dict) -> dict:
    remote_path = target["remote"]
    if host in {"local", "localhost", "self"}:
        path = Path(remote_path)
        if not path.exists():
            raise FileNotFoundError(f"remote path not found in local mode: {remote_path}")
        if target["kind"] == "ghost_ui_settings":
            summary = summarize_remote_local_ghost_ui_settings(path)
        elif target["kind"] == "ghost_content_hygiene":
            summary = summarize_remote_local_ghost_content_hygiene(path)
        else:
            data = path.read_bytes()
            summary = (
                summarize_prediction_db_bytes(data)
                if target["kind"] == "json_prediction_db"
                else summarize_text_bytes(data)
            )
        summary["path"] = remote_path
        return summary

    py_code = r"""
import hashlib
import json
import pathlib
import sqlite3
import sys

path = pathlib.Path(sys.argv[1])
kind = sys.argv[2]
data = path.read_bytes() if kind != "ghost_ui_settings" else b""

def summarize_prediction_db(raw):
    payload = json.loads(raw.decode("utf-8"))
    preds = payload.get("predictions") if isinstance(payload, dict) else payload
    preds = preds or []
    status_counts = {}
    tier_counts = {}
    resolution_criteria_present = 0
    authoritative_sources_present = 0
    initial_prob_present = 0
    for pred in preds:
        status = str(pred.get("status") or "NONE")
        tier = str(pred.get("official_score_tier") or "NONE")
        status_counts[status] = status_counts.get(status, 0) + 1
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        if pred.get("resolution_criteria") is not None:
            resolution_criteria_present += 1
        if "authoritative_sources" in pred:
            authoritative_sources_present += 1
        if pred.get("initial_prob") is not None:
            initial_prob_present += 1
    return {
        "kind": "json_prediction_db",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "predictions": len(preds),
        "status_counts": status_counts,
        "official_score_tier_counts": tier_counts,
        "resolution_criteria_present": resolution_criteria_present,
        "authoritative_sources_present": authoritative_sources_present,
        "initial_prob_present": initial_prob_present,
    }

def summarize_text(raw):
    text = raw.decode("utf-8")
    return {
        "kind": "text",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "lines": text.count("\n") + (0 if not text else 1),
    }

def summarize_ghost_ui_settings(db_path):
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    def get_value(key):
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    head = get_value("codeinjection_head") or ""
    summary = {
        "kind": "ghost_ui_settings",
        "has_language_switcher": "<!-- Language Switcher v" in head,
        "has_ui_guard": "<!-- Global UI Guard v" in head,
        "portal_button_signup_text": get_value("portal_button_signup_text") or "",
        "portal_button_style": get_value("portal_button_style") or "",
        "portal_button": get_value("portal_button") or "",
        "portal_plans": get_value("portal_plans") or "",
    }
    con.close()
    return summary


def summarize_ghost_content_hygiene(db_path):
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    summary = {
        "kind": "ghost_content_hygiene",
        "stale_en_article_links": 0,
        "stale_en_predictions_links": 0,
        "stale_full_en_article_links": 0,
        "settings_stale_hits": 0,
    }

    def accumulate_table(table_name):
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cur.fetchall()}
        scan_fields = [
            field
            for field in ("html", "lexical", "mobiledoc", "custom_excerpt", "canonical_url", "codeinjection_head", "codeinjection_foot")
            if field in columns
        ]
        if not scan_fields:
            return
        select_sql = "SELECT " + ", ".join(scan_fields) + f" FROM {table_name}"
        rows = cur.execute(select_sql)
        for row in rows:
            for value in row:
                if not isinstance(value, str) or not value:
                    continue
                summary["stale_en_article_links"] += value.count("/en/en-")
                summary["stale_en_predictions_links"] += value.count("/en-predictions/")
                summary["stale_full_en_article_links"] += value.lower().count("https://nowpattern.com/en/en-")

    accumulate_table("posts")
    accumulate_table("pages")

    for key in ("codeinjection_head", "codeinjection_foot"):
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        value = row[0] if row else ""
        if isinstance(value, str) and value:
            summary["settings_stale_hits"] += value.count("/en/en-") + value.count("/en-predictions/")

    con.close()
    return summary

summary = (
    summarize_prediction_db(data)
    if kind == "json_prediction_db"
    else summarize_ghost_ui_settings(path)
    if kind == "ghost_ui_settings"
    else summarize_ghost_content_hygiene(path)
    if kind == "ghost_content_hygiene"
    else summarize_text(data)
)
print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
"""
    remote_cmd = "python3 -c {code} {path} {kind}".format(
        code=shlex.quote(py_code),
        path=shlex.quote(remote_path),
        kind=shlex.quote(target["kind"]),
    )
    result = subprocess.run(
        [ssh_bin, host, remote_cmd],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "remote summary failed")
    summary = json.loads(result.stdout.strip())
    summary["path"] = remote_path
    return summary


def compare_target(local_summary: dict, remote_summary: dict) -> list[str]:
    issues: list[str] = []
    if local_summary.get("missing"):
        issues.append(f"missing locally: {local_summary['path']}")
        return issues

    if local_summary.get("kind") == "ghost_ui_settings":
        for key in [
            "has_language_switcher",
            "has_ui_guard",
            "portal_button_signup_text",
            "portal_button_style",
            "portal_button",
            "portal_plans",
        ]:
            if local_summary.get(key) != remote_summary.get(key):
                issues.append(f"{key} drift: local={local_summary.get(key)!r} remote={remote_summary.get(key)!r}")
        return issues

    if local_summary.get("kind") == "ghost_content_hygiene":
        for key in [
            "stale_en_article_links",
            "stale_en_predictions_links",
            "stale_full_en_article_links",
            "settings_stale_hits",
        ]:
            if local_summary.get(key) != remote_summary.get(key):
                issues.append(f"{key} drift: local={local_summary.get(key)!r} remote={remote_summary.get(key)!r}")
        return issues

    keys = [
        "sha256",
        "bytes",
        "lines",
        "predictions",
        "resolution_criteria_present",
        "authoritative_sources_present",
        "initial_prob_present",
        "status_counts",
        "official_score_tier_counts",
    ]
    for key in keys:
        if key in remote_summary or key in local_summary:
            if local_summary.get(key) != remote_summary.get(key):
                issues.append(f"{key} drift: local={local_summary.get(key)!r} remote={remote_summary.get(key)!r}")
    return issues


def summarize_remote_local_ghost_ui_settings(db_path: Path) -> dict:
    import sqlite3

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    def get_value(key):
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    head = get_value("codeinjection_head") or ""
    summary = {
        "kind": "ghost_ui_settings",
        "has_language_switcher": "<!-- Language Switcher v" in head,
        "has_ui_guard": "<!-- Global UI Guard v" in head,
        "portal_button_signup_text": get_value("portal_button_signup_text") or "",
        "portal_button_style": get_value("portal_button_style") or "",
        "portal_button": get_value("portal_button") or "",
        "portal_plans": get_value("portal_plans") or "",
    }
    con.close()
    return summary


def summarize_remote_local_ghost_content_hygiene(db_path: Path) -> dict:
    import sqlite3

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    cur.execute("PRAGMA table_info(posts)")
    post_columns = {row[1] for row in cur.fetchall()}
    scan_fields = [
        field
        for field in ("html", "lexical", "mobiledoc", "custom_excerpt", "canonical_url", "codeinjection_head", "codeinjection_foot")
        if field in post_columns
    ]

    summary = {
        "kind": "ghost_content_hygiene",
        "stale_en_article_links": 0,
        "stale_en_predictions_links": 0,
        "stale_full_en_article_links": 0,
        "settings_stale_hits": 0,
    }

    def accumulate_table(table_name: str) -> None:
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cur.fetchall()}
        fields = [field for field in scan_fields if field in columns]
        if not fields:
            return
        select_sql = "SELECT " + ", ".join(fields) + f" FROM {table_name}"
        rows = cur.execute(select_sql)
        for row in rows:
            for value in row:
                if not isinstance(value, str) or not value:
                    continue
                summary["stale_en_article_links"] += value.count("/en/en-")
                summary["stale_en_predictions_links"] += value.count("/en-predictions/")
                summary["stale_full_en_article_links"] += value.lower().count("https://nowpattern.com/en/en-")

    accumulate_table("posts")
    accumulate_table("pages")

    for key in ("codeinjection_head", "codeinjection_foot"):
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        value = row[0] if row else ""
        if isinstance(value, str) and value:
            summary["settings_stale_hits"] += value.count("/en/en-") + value.count("/en-predictions/")

    con.close()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare local repo state with live VPS truth.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="VPS ssh target, e.g. root@163.44.124.123")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable text")
    args = parser.parse_args()

    ssh_bin = choose_ssh_bin()
    report = {"host": args.host, "ssh_bin": ssh_bin, "targets": []}
    any_drift = False

    for target in TARGETS:
        local_summary = summarize_local(target)
        remote_summary = summarize_remote(ssh_bin, args.host, target)
        issues = compare_target(local_summary, remote_summary)
        if issues:
            any_drift = True
        report["targets"].append(
            {
                "name": target["name"],
                "local": local_summary,
                "remote": remote_summary,
                "issues": issues,
            }
        )

    if args.json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"Live repo drift check against {args.host}")
        for item in report["targets"]:
            print(f"- {item['name']}")
            if item["issues"]:
                for issue in item["issues"]:
                    print(f"  DRIFT: {issue}")
            else:
                print("  OK: local and remote match")

    return 1 if any_drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
