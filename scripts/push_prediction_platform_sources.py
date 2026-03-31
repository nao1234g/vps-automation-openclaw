#!/usr/bin/env python3
"""Push local prediction platform source files from this repo to the VPS."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = os.environ.get("NOWPATTERN_VPS_HOST", "root@163.44.124.123")
TARGETS = [
    {
        "name": "mission_contract",
        "local": REPO_ROOT / "scripts" / "mission_contract.py",
        "remote": "/opt/shared/scripts/mission_contract.py",
    },
    {
        "name": "mission_contract_audit",
        "local": REPO_ROOT / "scripts" / "mission_contract_audit.py",
        "remote": "/opt/shared/scripts/mission_contract_audit.py",
    },
    {
        "name": "agent_bootstrap_context",
        "local": REPO_ROOT / "scripts" / "agent_bootstrap_context.py",
        "remote": "/opt/shared/scripts/agent_bootstrap_context.py",
    },
    {
        "name": "product_lexicon",
        "local": REPO_ROOT / "scripts" / "product_lexicon.py",
        "remote": "/opt/shared/scripts/product_lexicon.py",
    },
    {
        "name": "public_lexicon_compat",
        "local": REPO_ROOT / "scripts" / "public_lexicon.py",
        "remote": "/opt/shared/scripts/public_lexicon.py",
    },
    {
        "name": "public_lexicon",
        "local": REPO_ROOT / "scripts" / "canonical_public_lexicon.py",
        "remote": "/opt/shared/scripts/canonical_public_lexicon.py",
    },
    {
        "name": "update_about_pages",
        "local": REPO_ROOT / "scripts" / "update_about_pages.py",
        "remote": "/opt/shared/scripts/update_about_pages.py",
    },
    {
        "name": "seo_structured_data",
        "local": REPO_ROOT / "scripts" / "seo_structured_data.py",
        "remote": "/opt/shared/scripts/seo_structured_data.py",
    },
    {
        "name": "content_release_scope",
        "local": REPO_ROOT / "scripts" / "content_release_scope.py",
        "remote": "/opt/shared/scripts/content_release_scope.py",
    },
    {
        "name": "release_governor",
        "local": REPO_ROOT / "scripts" / "release_governor.py",
        "remote": "/opt/shared/scripts/release_governor.py",
    },
    {
        "name": "mistake_registry_data",
        "local": REPO_ROOT / "data" / "mistake_registry.json",
        "remote": "/opt/shared/data/mistake_registry.json",
    },
    {
        "name": "prediction_db",
        "local": REPO_ROOT / "scripts" / "prediction_db.json",
        "remote": "/opt/shared/scripts/prediction_db.json",
    },
    {
        "name": "prediction_page_builder",
        "local": REPO_ROOT / "scripts" / "prediction_page_builder.py",
        "remote": "/opt/shared/scripts/prediction_page_builder.py",
    },
    {
        "name": "reader_prediction_api",
        "local": REPO_ROOT / "scripts" / "reader_prediction_api.py",
        "remote": "/opt/shared/scripts/reader_prediction_api.py",
    },
    {
        "name": "refresh_prediction_db_meta",
        "local": REPO_ROOT / "scripts" / "refresh_prediction_db_meta.py",
        "remote": "/opt/shared/scripts/refresh_prediction_db_meta.py",
    },
    {
        "name": "prediction_state_utils",
        "local": REPO_ROOT / "scripts" / "prediction_state_utils.py",
        "remote": "/opt/shared/scripts/prediction_state_utils.py",
    },
    {
        "name": "prediction_state_integrity_gate",
        "local": REPO_ROOT / "scripts" / "prediction_state_integrity_gate.py",
        "remote": "/opt/shared/scripts/prediction_state_integrity_gate.py",
    },
    {
        "name": "prediction_deploy_gate",
        "local": REPO_ROOT / "scripts" / "prediction_deploy_gate.py",
        "remote": "/opt/shared/scripts/prediction_deploy_gate.py",
    },
    {
        "name": "prediction_integrity_policy",
        "local": REPO_ROOT / "scripts" / "prediction_integrity_policy.json",
        "remote": "/opt/shared/scripts/prediction_integrity_policy.json",
    },
    {
        "name": "build_article_release_manifest",
        "local": REPO_ROOT / "scripts" / "build_article_release_manifest.py",
        "remote": "/opt/shared/scripts/build_article_release_manifest.py",
    },
    {
        "name": "publish_path_guard_audit",
        "local": REPO_ROOT / "scripts" / "publish_path_guard_audit.py",
        "remote": "/opt/shared/scripts/publish_path_guard_audit.py",
    },
    {
        "name": "article_truth_guard",
        "local": REPO_ROOT / "scripts" / "article_truth_guard.py",
        "remote": "/opt/shared/scripts/article_truth_guard.py",
    },
    {
        "name": "article_factcheck_postprocess",
        "local": REPO_ROOT / "scripts" / "article_factcheck_postprocess.py",
        "remote": "/opt/shared/scripts/article_factcheck_postprocess.py",
    },
    {
        "name": "article_release_guard",
        "local": REPO_ROOT / "scripts" / "article_release_guard.py",
        "remote": "/opt/shared/scripts/article_release_guard.py",
    },
    {
        "name": "nowpattern_publisher",
        "local": REPO_ROOT / "scripts" / "nowpattern_publisher.py",
        "remote": "/opt/shared/scripts/nowpattern_publisher.py",
    },
    {
        "name": "nowpattern_article_builder",
        "local": REPO_ROOT / "scripts" / "nowpattern_article_builder.py",
        "remote": "/opt/shared/scripts/nowpattern_article_builder.py",
    },
    {
        "name": "nowpattern_deep_pattern_generate",
        "local": REPO_ROOT / "scripts" / "nowpattern-deep-pattern-generate.py",
        "remote": "/opt/shared/scripts/nowpattern-deep-pattern-generate.py",
    },
    {
        "name": "breaking_news_watcher",
        "local": REPO_ROOT / "scripts" / "breaking-news-watcher.py",
        "remote": "/opt/shared/scripts/breaking-news-watcher.py",
    },
    {
        "name": "breaking_pipeline_helper",
        "local": REPO_ROOT / "scripts" / "breaking_pipeline_helper.py",
        "remote": "/opt/shared/scripts/breaking_pipeline_helper.py",
    },
    {
        "name": "ghost_webhook_server",
        "local": REPO_ROOT / "scripts" / "ghost_webhook_server.py",
        "remote": "/opt/shared/scripts/ghost_webhook_server.py",
    },
    {
        "name": "ghost_content_gate",
        "local": REPO_ROOT / "scripts" / "ghost_content_gate.py",
        "remote": "/opt/shared/scripts/ghost_content_gate.py",
    },
    {
        "name": "qa_sentinel",
        "local": REPO_ROOT / "scripts" / "qa_sentinel.py",
        "remote": "/opt/shared/scripts/qa_sentinel.py",
    },
    {
        "name": "ghost_to_tweet_queue",
        "local": REPO_ROOT / "scripts" / "ghost_to_tweet_queue.py",
        "remote": "/opt/shared/scripts/ghost_to_tweet_queue.py",
    },
    {
        "name": "auto_tweet",
        "local": REPO_ROOT / "scripts" / "auto_tweet.py",
        "remote": "/opt/shared/scripts/auto_tweet.py",
    },
    {
        "name": "x_swarm_dispatcher",
        "local": REPO_ROOT / "scripts" / "x_swarm_dispatcher.py",
        "remote": "/opt/shared/scripts/x_swarm_dispatcher.py",
    },
    {
        "name": "substack_notes_poster",
        "local": REPO_ROOT / "scripts" / "substack_notes_poster.py",
        "remote": "/opt/shared/scripts/substack_notes_poster.py",
    },
    {
        "name": "neo_queue_dispatcher",
        "local": REPO_ROOT / "scripts" / "neo_queue_dispatcher.py",
        "remote": "/opt/shared/scripts/neo_queue_dispatcher.py",
    },
    {
        "name": "playwright_e2e_predictions",
        "local": REPO_ROOT / "scripts" / "playwright_e2e_predictions.py",
        "remote": "/opt/shared/scripts/playwright_e2e_predictions.py",
    },
    {
        "name": "fix_global_language_switcher",
        "local": REPO_ROOT / "scripts" / "fix_global_language_switcher.py",
        "remote": "/opt/shared/scripts/fix_global_language_switcher.py",
    },
    {
        "name": "fix_ghost_content_links",
        "local": REPO_ROOT / "scripts" / "fix_ghost_content_links.py",
        "remote": "/opt/shared/scripts/fix_ghost_content_links.py",
    },
    {
        "name": "live_site_availability_check",
        "local": REPO_ROOT / "scripts" / "live_site_availability_check.py",
        "remote": "/opt/shared/scripts/live_site_availability_check.py",
    },
    {
        "name": "check_ghost_article_routes",
        "local": REPO_ROOT / "scripts" / "check_ghost_article_routes.py",
        "remote": "/opt/shared/scripts/check_ghost_article_routes.py",
    },
    {
        "name": "site_guard_runner",
        "local": REPO_ROOT / "scripts" / "site_guard_runner.py",
        "remote": "/opt/shared/scripts/site_guard_runner.py",
    },
    {
        "name": "site_ui_smoke_audit",
        "local": REPO_ROOT / "scripts" / "site_ui_smoke_audit.py",
        "remote": "/opt/shared/scripts/site_ui_smoke_audit.py",
    },
    {
        "name": "install_site_ui_guard",
        "local": REPO_ROOT / "scripts" / "install_site_ui_guard.py",
        "remote": "/opt/shared/scripts/install_site_ui_guard.py",
    },
    {
        "name": "install_en_article_route_guard",
        "local": REPO_ROOT / "scripts" / "install_en_article_route_guard.py",
        "remote": "/opt/shared/scripts/install_en_article_route_guard.py",
    },
    {
        "name": "install_uuid_preview_route_guard",
        "local": REPO_ROOT / "scripts" / "install_uuid_preview_route_guard.py",
        "remote": "/opt/shared/scripts/install_uuid_preview_route_guard.py",
    },
    {
        "name": "check_live_repo_drift",
        "local": REPO_ROOT / "scripts" / "check_live_repo_drift.py",
        "remote": "/opt/shared/scripts/check_live_repo_drift.py",
    },
    {
        "name": "ghost_write_surface_audit",
        "local": REPO_ROOT / "scripts" / "ghost_write_surface_audit.py",
        "remote": "/opt/shared/scripts/ghost_write_surface_audit.py",
    },
    {
        "name": "release_guard_canary",
        "local": REPO_ROOT / "scripts" / "release_guard_canary.py",
        "remote": "/opt/shared/scripts/release_guard_canary.py",
    },
    {
        "name": "ecosystem_governance_audit",
        "local": REPO_ROOT / "scripts" / "ecosystem_governance_audit.py",
        "remote": "/opt/shared/scripts/ecosystem_governance_audit.py",
    },
    {
        "name": "lexicon_contract_audit",
        "local": REPO_ROOT / "scripts" / "lexicon_contract_audit.py",
        "remote": "/opt/shared/scripts/lexicon_contract_audit.py",
    },
    {
        "name": "cron_governance_audit",
        "local": REPO_ROOT / "scripts" / "cron_governance_audit.py",
        "remote": "/opt/shared/scripts/cron_governance_audit.py",
    },
    {
        "name": "site_article_source_audit",
        "local": REPO_ROOT / "scripts" / "site_article_source_audit.py",
        "remote": "/opt/shared/scripts/site_article_source_audit.py",
    },
    {
        "name": "article_anchor_integrity_audit",
        "local": REPO_ROOT / "scripts" / "article_anchor_integrity_audit.py",
        "remote": "/opt/shared/scripts/article_anchor_integrity_audit.py",
    },
    {
        "name": "site_dev_page_audit",
        "local": REPO_ROOT / "scripts" / "site_dev_page_audit.py",
        "remote": "/opt/shared/scripts/site_dev_page_audit.py",
    },
    {
        "name": "ecosystem_mission_control",
        "local": REPO_ROOT / "scripts" / "ecosystem_mission_control.py",
        "remote": "/opt/shared/scripts/ecosystem_mission_control.py",
    },
    {
        "name": "install_ecosystem_mission_control",
        "local": REPO_ROOT / "scripts" / "install_ecosystem_mission_control.py",
        "remote": "/opt/shared/scripts/install_ecosystem_mission_control.py",
    },
    {
        "name": "test_release_governor",
        "local": REPO_ROOT / "scripts" / "test_release_governor.py",
        "remote": "/opt/shared/scripts/test_release_governor.py",
    },
    {
        "name": "test_mission_contract",
        "local": REPO_ROOT / "scripts" / "test_mission_contract.py",
        "remote": "/opt/shared/scripts/test_mission_contract.py",
    },
    {
        "name": "test_agent_bootstrap_context",
        "local": REPO_ROOT / "scripts" / "test_agent_bootstrap_context.py",
        "remote": "/opt/shared/scripts/test_agent_bootstrap_context.py",
    },
    {
        "name": "test_public_lexicon",
        "local": REPO_ROOT / "scripts" / "test_public_lexicon.py",
        "remote": "/opt/shared/scripts/test_public_lexicon.py",
    },
    {
        "name": "test_prediction_tracker_regressions",
        "local": REPO_ROOT / "scripts" / "test_prediction_tracker_regressions.py",
        "remote": "/opt/shared/scripts/test_prediction_tracker_regressions.py",
    },
    {
        "name": "test_prediction_deploy_gate",
        "local": REPO_ROOT / "scripts" / "test_prediction_deploy_gate.py",
        "remote": "/opt/shared/scripts/test_prediction_deploy_gate.py",
    },
    {
        "name": "test_cron_governance_audit",
        "local": REPO_ROOT / "scripts" / "test_cron_governance_audit.py",
        "remote": "/opt/shared/scripts/test_cron_governance_audit.py",
    },
    {
        "name": "test_mistake_guard_contracts",
        "local": REPO_ROOT / "scripts" / "test_mistake_guard_contracts.py",
        "remote": "/opt/shared/scripts/test_mistake_guard_contracts.py",
    },
]


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


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


def choose_scp_bin() -> str:
    override = os.environ.get("NP_SCP_BIN")
    if override and Path(override).exists():
        return override

    windows_builtin = Path(r"C:\Windows\System32\OpenSSH\scp.exe")
    if windows_builtin.exists():
        return str(windows_builtin)

    candidate = shutil.which("scp")
    if candidate and ".sbx-denybin" not in candidate.lower():
        return candidate

    raise FileNotFoundError("No usable scp binary found. Set NP_SCP_BIN if needed.")


def push_bytes(ssh_bin: str, host: str, remote_path: str, data: bytes) -> None:
    remote_cmd = (
        "python3 -c \"import pathlib,sys; "
        "path=pathlib.Path(sys.argv[1]); "
        "path.parent.mkdir(parents=True, exist_ok=True); "
        "path.write_bytes(sys.stdin.buffer.read())\" "
        + "'" + remote_path.replace("'", "'\"'\"'") + "'"
    )
    result = subprocess.run(
        [ssh_bin, host, remote_cmd],
        input=data,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or f"failed to push {remote_path}")


def push_with_scp(scp_bin: str, host: str, local_path: Path, remote_path: str) -> None:
    result = subprocess.run(
        [scp_bin, str(local_path), f"{host}:{remote_path}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or f"failed to push {local_path} via scp")


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Push local prediction platform files to VPS.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="VPS ssh target, e.g. root@163.44.124.123")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be pushed without writing files")
    parser.add_argument(
        "--target",
        action="append",
        choices=[target["name"] for target in TARGETS],
        help="Push only the named target. Can be passed multiple times.",
    )
    args = parser.parse_args()

    ssh_bin = choose_ssh_bin()
    try:
        scp_bin = choose_scp_bin()
    except FileNotFoundError:
        scp_bin = ""
    selected = set(args.target or [])
    targets = [target for target in TARGETS if not selected or target["name"] in selected]

    for target in targets:
        local_path = target["local"]
        remote_path = target["remote"]
        if args.dry_run:
            print(f"WOULD PUSH {target['name']}: {local_path} -> {remote_path}")
            continue
        if scp_bin:
            push_with_scp(scp_bin, args.host, local_path, remote_path)
        else:
            data = local_path.read_bytes()
            push_bytes(ssh_bin, args.host, remote_path, data)
        print(f"PUSHED {target['name']}: {local_path} -> {remote_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
