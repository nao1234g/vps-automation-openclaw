#!/usr/bin/env python3
"""Compare key local repo files against the VPS source of truth."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = os.environ.get("NOWPATTERN_VPS_HOST", "root@163.44.124.123")
GHOST_TEXT_TYPE_MARKERS = ("CHAR", "CLOB", "TEXT", "VARCHAR", "JSON")
GHOST_CONTENT_FIELD_HINTS = {
    "html",
    "lexical",
    "mobiledoc",
    "custom_excerpt",
    "canonical_url",
    "meta_title",
    "meta_description",
    "og_title",
    "og_description",
    "twitter_title",
    "twitter_description",
    "codeinjection_head",
    "codeinjection_foot",
    "value",
}
GHOST_ACTIVE_HYGIENE_TABLES = {"posts", "settings"}
URL_SLOT_PREFIX = r"(?:href|src|content|action|data-href|data-url|canonical(?:_url)?|url)"
STALE_EN_ARTICLE_RE = re.compile(
    rf"{URL_SLOT_PREFIX}\s*[:=]\s*[\"'](?:https?://(?:www\.)?nowpattern\.com)?/en/en-(?!predictions/)[^\"']*",
    flags=re.IGNORECASE,
)
STALE_EN_PREDICTIONS_RE = re.compile(
    rf"{URL_SLOT_PREFIX}\s*[:=]\s*[\"'](?:https?://(?:www\.)?nowpattern\.com)?/en/en-predictions/[^\"']*",
    flags=re.IGNORECASE,
)
STALE_FULL_EN_ARTICLE_RE = re.compile(
    rf"{URL_SLOT_PREFIX}\s*[:=]\s*[\"']https?://(?:www\.)?nowpattern\.com/en/en-(?!predictions/)[^\"']*",
    flags=re.IGNORECASE,
)

TARGETS = [
    {
        "name": "mission_contract",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "mission_contract.py",
        "remote": "/opt/shared/scripts/mission_contract.py",
    },
    {
        "name": "mission_contract_audit",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "mission_contract_audit.py",
        "remote": "/opt/shared/scripts/mission_contract_audit.py",
    },
    {
        "name": "agent_bootstrap_context",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "agent_bootstrap_context.py",
        "remote": "/opt/shared/scripts/agent_bootstrap_context.py",
    },
    {
        "name": "runtime_boundary",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "runtime_boundary.py",
        "remote": "/opt/shared/scripts/runtime_boundary.py",
    },
    {
        "name": "product_lexicon",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "product_lexicon.py",
        "remote": "/opt/shared/scripts/product_lexicon.py",
    },
    {
        "name": "public_lexicon_compat",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "public_lexicon.py",
        "remote": "/opt/shared/scripts/public_lexicon.py",
    },
    {
        "name": "public_lexicon",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "canonical_public_lexicon.py",
        "remote": "/opt/shared/scripts/canonical_public_lexicon.py",
    },
    {
        "name": "release_governor",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "release_governor.py",
        "remote": "/opt/shared/scripts/release_governor.py",
    },
    {
        "name": "change_freeze_guard",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "change_freeze_guard.py",
        "remote": "/opt/shared/scripts/change_freeze_guard.py",
    },
    {
        "name": "credibility_budget_guard",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "credibility_budget_guard.py",
        "remote": "/opt/shared/scripts/credibility_budget_guard.py",
    },
    {
        "name": "one_pass_completion_gate",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "one_pass_completion_gate.py",
        "remote": "/opt/shared/scripts/one_pass_completion_gate.py",
    },
    {
        "name": "one_pass_completion_policy",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "one_pass_completion_policy.json",
        "remote": "/opt/shared/scripts/one_pass_completion_policy.json",
    },
    {
        "name": "test_change_freeze_guard",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_change_freeze_guard.py",
        "remote": "/opt/shared/scripts/test_change_freeze_guard.py",
    },
    {
        "name": "test_credibility_budget_guard",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_credibility_budget_guard.py",
        "remote": "/opt/shared/scripts/test_credibility_budget_guard.py",
    },
    {
        "name": "test_one_pass_completion_gate",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_one_pass_completion_gate.py",
        "remote": "/opt/shared/scripts/test_one_pass_completion_gate.py",
    },
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
        "name": "prediction_deploy_gate",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "prediction_deploy_gate.py",
        "remote": "/opt/shared/scripts/prediction_deploy_gate.py",
    },
    {
        "name": "prediction_integrity_policy",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "prediction_integrity_policy.json",
        "remote": "/opt/shared/scripts/prediction_integrity_policy.json",
    },
    {
        "name": "build_article_release_manifest",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "build_article_release_manifest.py",
        "remote": "/opt/shared/scripts/build_article_release_manifest.py",
    },
    {
        "name": "publish_path_guard_audit",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "publish_path_guard_audit.py",
        "remote": "/opt/shared/scripts/publish_path_guard_audit.py",
    },
    {
        "name": "article_truth_guard",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "article_truth_guard.py",
        "remote": "/opt/shared/scripts/article_truth_guard.py",
    },
    {
        "name": "article_factcheck_postprocess",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "article_factcheck_postprocess.py",
        "remote": "/opt/shared/scripts/article_factcheck_postprocess.py",
    },
    {
        "name": "article_release_guard",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "article_release_guard.py",
        "remote": "/opt/shared/scripts/article_release_guard.py",
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
        "name": "patch_ghost_theme_en_urls",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "patch_ghost_theme_en_urls.py",
        "remote": "/opt/shared/scripts/patch_ghost_theme_en_urls.py",
    },
    {
        "name": "repair_ghost_post_authors",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "repair_ghost_post_authors.py",
        "remote": "/opt/shared/scripts/repair_ghost_post_authors.py",
    },
    {
        "name": "repair_internal_draft_links",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "repair_internal_draft_links.py",
        "remote": "/opt/shared/scripts/repair_internal_draft_links.py",
    },
    {
        "name": "repair_article_source_urls",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "repair_article_source_urls.py",
        "remote": "/opt/shared/scripts/repair_article_source_urls.py",
    },
    {
        "name": "repair_cross_language_article_links",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "repair_cross_language_article_links.py",
        "remote": "/opt/shared/scripts/repair_cross_language_article_links.py",
    },
    {
        "name": "live_site_availability_check",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "live_site_availability_check.py",
        "remote": "/opt/shared/scripts/live_site_availability_check.py",
    },
    {
        "name": "check_ghost_article_routes",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "check_ghost_article_routes.py",
        "remote": "/opt/shared/scripts/check_ghost_article_routes.py",
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
        "name": "install_uuid_preview_route_guard",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "install_uuid_preview_route_guard.py",
        "remote": "/opt/shared/scripts/install_uuid_preview_route_guard.py",
    },
    {
        "name": "ghost_write_surface_audit",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "ghost_write_surface_audit.py",
        "remote": "/opt/shared/scripts/ghost_write_surface_audit.py",
    },
    {
        "name": "release_guard_canary",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "release_guard_canary.py",
        "remote": "/opt/shared/scripts/release_guard_canary.py",
    },
    {
        "name": "prediction_ops_scheduler",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "prediction_ops_scheduler.py",
        "remote": "/opt/shared/scripts/prediction_ops_scheduler.py",
    },
    {
        "name": "ecosystem_governance_audit",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "ecosystem_governance_audit.py",
        "remote": "/opt/shared/scripts/ecosystem_governance_audit.py",
    },
    {
        "name": "lexicon_contract_audit",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "lexicon_contract_audit.py",
        "remote": "/opt/shared/scripts/lexicon_contract_audit.py",
    },
    {
        "name": "cron_governance_audit",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "cron_governance_audit.py",
        "remote": "/opt/shared/scripts/cron_governance_audit.py",
    },
    {
        "name": "site_article_source_audit",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "site_article_source_audit.py",
        "remote": "/opt/shared/scripts/site_article_source_audit.py",
    },
    {
        "name": "public_article_rotation",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "public_article_rotation.py",
        "remote": "/opt/shared/scripts/public_article_rotation.py",
    },
    {
        "name": "site_link_crawler",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "site_link_crawler.py",
        "remote": "/opt/shared/scripts/site_link_crawler.py",
    },
    {
        "name": "auto_tweet",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "auto_tweet.py",
        "remote": "/opt/shared/scripts/auto_tweet.py",
    },
    {
        "name": "x_swarm_dispatcher",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "x_swarm_dispatcher.py",
        "remote": "/opt/shared/scripts/x_swarm_dispatcher.py",
    },
    {
        "name": "substack_notes_poster",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "substack_notes_poster.py",
        "remote": "/opt/shared/scripts/substack_notes_poster.py",
    },
    {
        "name": "neo_queue_dispatcher",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "neo_queue_dispatcher.py",
        "remote": "/opt/shared/scripts/neo_queue_dispatcher.py",
    },
    {
        "name": "test_mission_contract",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_mission_contract.py",
        "remote": "/opt/shared/scripts/test_mission_contract.py",
    },
    {
        "name": "test_agent_bootstrap_context",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_agent_bootstrap_context.py",
        "remote": "/opt/shared/scripts/test_agent_bootstrap_context.py",
    },
    {
        "name": "test_public_lexicon",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_public_lexicon.py",
        "remote": "/opt/shared/scripts/test_public_lexicon.py",
    },
    {
        "name": "test_public_article_rotation",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_public_article_rotation.py",
        "remote": "/opt/shared/scripts/test_public_article_rotation.py",
    },
    {
        "name": "test_site_article_source_audit",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_site_article_source_audit.py",
        "remote": "/opt/shared/scripts/test_site_article_source_audit.py",
    },
    {
        "name": "test_repair_article_source_urls",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_repair_article_source_urls.py",
        "remote": "/opt/shared/scripts/test_repair_article_source_urls.py",
    },
    {
        "name": "test_repair_cross_language_article_links",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_repair_cross_language_article_links.py",
        "remote": "/opt/shared/scripts/test_repair_cross_language_article_links.py",
    },
    {
        "name": "test_refresh_prediction_db_meta",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_refresh_prediction_db_meta.py",
        "remote": "/opt/shared/scripts/test_refresh_prediction_db_meta.py",
    },
    {
        "name": "test_site_link_crawler",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_site_link_crawler.py",
        "remote": "/opt/shared/scripts/test_site_link_crawler.py",
    },
    {
        "name": "test_install_site_ui_guard",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_install_site_ui_guard.py",
        "remote": "/opt/shared/scripts/test_install_site_ui_guard.py",
    },
    {
        "name": "test_prediction_ops_scheduler",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "test_prediction_ops_scheduler.py",
        "remote": "/opt/shared/scripts/test_prediction_ops_scheduler.py",
    },
    {
        "name": "install_prediction_ops_scheduler",
        "kind": "text",
        "local": REPO_ROOT / "scripts" / "install_prediction_ops_scheduler.py",
        "remote": "/opt/shared/scripts/install_prediction_ops_scheduler.py",
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


def count_stale_en_article_links(value: str) -> int:
    return len(STALE_EN_ARTICLE_RE.findall(value))


def count_stale_en_predictions_links(value: str) -> int:
    return len(STALE_EN_PREDICTIONS_RE.findall(value))


def count_stale_full_en_article_links(value: str) -> int:
    return len(STALE_FULL_EN_ARTICLE_RE.findall(value))


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
        "scanned_tables": sorted(GHOST_ACTIVE_HYGIENE_TABLES),
    }


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def ghost_text_targets(cur, allowed_tables: set[str] | None = None) -> list[tuple[str, list[str]]]:
    tables = cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    targets: list[tuple[str, list[str]]] = []
    for row in tables:
        table_name = row[0]
        if allowed_tables and table_name not in allowed_tables:
            continue
        pragma = list(cur.execute(f"PRAGMA table_info({quote_ident(table_name)})"))
        columns = []
        for col in pragma:
            column_name = col[1]
            column_type = str(col[2] or "").upper()
            is_text_like = any(marker in column_type for marker in GHOST_TEXT_TYPE_MARKERS) or column_name in GHOST_CONTENT_FIELD_HINTS
            if is_text_like:
                columns.append(column_name)
        if columns:
            targets.append((table_name, columns))
    return targets


def summarize_ghost_content_hygiene_connection(con) -> dict:
    cur = con.cursor()
    summary = {
        "kind": "ghost_content_hygiene",
        "stale_en_article_links": 0,
        "stale_en_predictions_links": 0,
        "stale_full_en_article_links": 0,
        "settings_stale_hits": 0,
        "scanned_tables": sorted(GHOST_ACTIVE_HYGIENE_TABLES),
    }

    for table_name, columns in ghost_text_targets(cur, GHOST_ACTIVE_HYGIENE_TABLES):
        select_sql = "SELECT " + ", ".join(quote_ident(column) for column in columns) + f" FROM {quote_ident(table_name)}"
        for row in cur.execute(select_sql):
            for value in row:
                if not isinstance(value, str) or not value:
                    continue
                summary["stale_en_article_links"] += count_stale_en_article_links(value)
                summary["stale_en_predictions_links"] += count_stale_en_predictions_links(value)
                summary["stale_full_en_article_links"] += count_stale_full_en_article_links(value)
                if table_name == "settings":
                    summary["settings_stale_hits"] += (
                        count_stale_en_article_links(value) + count_stale_en_predictions_links(value)
                    )

    return summary


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
import re
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

URL_SLOT_PREFIX = r"(?:href|src|content|action|data-href|data-url|canonical(?:_url)?|url)"
STALE_EN_ARTICLE_RE = re.compile(
    rf"{URL_SLOT_PREFIX}\s*[:=]\s*[\"'](?:https?://(?:www\.)?nowpattern\.com)?/en/en-(?!predictions/)[^\"']*",
    re.IGNORECASE,
)
STALE_EN_PREDICTIONS_RE = re.compile(
    rf"{URL_SLOT_PREFIX}\s*[:=]\s*[\"'](?:https?://(?:www\.)?nowpattern\.com)?/en/en-predictions/[^\"']*",
    re.IGNORECASE,
)
STALE_FULL_EN_ARTICLE_RE = re.compile(
    rf"{URL_SLOT_PREFIX}\s*[:=]\s*[\"']https?://(?:www\.)?nowpattern\.com/en/en-(?!predictions/)[^\"']*",
    re.IGNORECASE,
)

def count_stale_en_article_links(value):
    return len(STALE_EN_ARTICLE_RE.findall(value))

def count_stale_en_predictions_links(value):
    return len(STALE_EN_PREDICTIONS_RE.findall(value))

def count_stale_full_en_article_links(value):
    return len(STALE_FULL_EN_ARTICLE_RE.findall(value))

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
        "scanned_tables": sorted({"posts", "settings"}),
    }

    def quote_ident(name):
        return '"' + name.replace('"', '""') + '"'

    rows = cur.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    table_names = [row[0] for row in rows if isinstance(row[0], str)]

    allowed_tables = {"posts", "settings"}
    for table_name in table_names:
        if table_name not in allowed_tables:
            continue
        pragma = list(cur.execute(f"PRAGMA table_info({quote_ident(table_name)})"))
        scan_fields = []
        for col in pragma:
            column_name = col[1]
            column_type = str(col[2] or "").upper()
            if (
                any(marker in column_type for marker in ("CHAR", "CLOB", "TEXT", "VARCHAR", "JSON"))
                or column_name in {
                    "html",
                    "lexical",
                    "mobiledoc",
                    "custom_excerpt",
                    "canonical_url",
                    "meta_title",
                    "meta_description",
                    "og_title",
                    "og_description",
                    "twitter_title",
                    "twitter_description",
                    "codeinjection_head",
                    "codeinjection_foot",
                    "value",
                }
            ):
                scan_fields.append(column_name)
        if not scan_fields:
            continue

        select_sql = "SELECT " + ", ".join(quote_ident(field) for field in scan_fields) + f" FROM {quote_ident(table_name)}"
        for row in cur.execute(select_sql):
            for value in row:
                if not isinstance(value, str) or not value:
                    continue
                summary["stale_en_article_links"] += count_stale_en_article_links(value)
                summary["stale_en_predictions_links"] += count_stale_en_predictions_links(value)
                summary["stale_full_en_article_links"] += count_stale_full_en_article_links(value)
                if table_name == "settings":
                    summary["settings_stale_hits"] += (
                        count_stale_en_article_links(value) + count_stale_en_predictions_links(value)
                    )

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
    summary = summarize_ghost_content_hygiene_connection(con)
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
