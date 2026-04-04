#!/usr/bin/env python3
"""Push and install the site UI hardening stack on the VPS."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = os.environ.get("NOWPATTERN_VPS_HOST", "root@163.44.124.123")
TARGETS = [
    "mission_contract",
    "mission_contract_audit",
    "agent_bootstrap_context",
    "runtime_boundary",
    "product_lexicon",
    "public_lexicon_compat",
    "public_lexicon",
    "update_about_pages",
    "seo_structured_data",
    "content_release_scope",
    "release_governor",
    "mistake_registry_data",
    "prediction_db",
    "prediction_page_builder",
    "refresh_prediction_db_meta",
    "prediction_state_utils",
    "prediction_state_integrity_gate",
    "prediction_deploy_gate",
    "prediction_integrity_policy",
    "build_article_release_manifest",
    "publish_path_guard_audit",
    "article_truth_guard",
    "article_factcheck_postprocess",
    "article_release_guard",
    "nowpattern_publisher",
    "nowpattern_article_builder",
    "nowpattern_deep_pattern_generate",
    "breaking_news_watcher",
    "breaking_pipeline_helper",
    "ghost_webhook_server",
    "ghost_content_gate",
    "qa_sentinel",
    "ghost_to_tweet_queue",
    "auto_tweet",
    "x_swarm_dispatcher",
    "substack_notes_poster",
    "neo_queue_dispatcher",
    "playwright_e2e_predictions",
    "fix_global_language_switcher",
    "fix_ghost_content_links",
    "patch_ghost_theme_en_urls",
    "repair_ghost_post_authors",
    "repair_internal_draft_links",
    "repair_article_source_urls",
    "repair_cross_language_article_links",
    "live_site_availability_check",
    "check_ghost_article_routes",
    "site_guard_runner",
    "site_ui_smoke_audit",
    "install_site_ui_guard",
    "install_en_article_route_guard",
    "install_uuid_preview_route_guard",
    "check_live_repo_drift",
    "ghost_write_surface_audit",
    "release_guard_canary",
    "ecosystem_governance_audit",
    "lexicon_contract_audit",
    "cron_governance_audit",
    "site_article_source_audit",
    "public_article_rotation",
    "site_link_crawler",
    "article_anchor_integrity_audit",
    "site_dev_page_audit",
    "stateful_user_journey_audit",
    "ecosystem_mission_control",
    "install_ecosystem_mission_control",
    "test_release_governor",
    "test_mission_contract",
    "test_agent_bootstrap_context",
    "test_public_lexicon",
    "test_prediction_tracker_regressions",
    "test_prediction_deploy_gate",
    "test_cron_governance_audit",
    "test_repair_internal_draft_links",
    "test_repair_article_source_urls",
    "test_repair_cross_language_article_links",
    "test_refresh_prediction_db_meta",
    "test_public_article_rotation",
    "test_site_article_source_audit",
    "test_site_link_crawler",
    "test_install_site_ui_guard",
    "test_mistake_guard_contracts",
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


def run_checked(command: list[str], workdir: Path) -> None:
    result = subprocess.run(
        command,
        cwd=str(workdir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "").strip() or (result.stdout or "").strip() or f"command failed: {command}")
    if (result.stdout or "").strip():
        print(result.stdout.strip())


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Deploy site UI guard/source-fix stack to VPS.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="VPS ssh target, e.g. root@163.44.124.123")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without running them")
    args = parser.parse_args()

    push_cmd = ["python", "scripts/push_prediction_platform_sources.py", "--host", args.host]
    for target in TARGETS:
        push_cmd.extend(["--target", target])

    remote_cmd = " && ".join(
        [
            "python3 /opt/shared/scripts/mission_contract.py --summary",
            "python3 /opt/shared/scripts/agent_bootstrap_context.py --summary",
            "python3 /opt/shared/scripts/mission_contract_audit.py",
            "python3 /opt/shared/scripts/lexicon_contract_audit.py",
            "python3 /opt/shared/scripts/test_mission_contract.py",
            "python3 /opt/shared/scripts/test_agent_bootstrap_context.py",
            "python3 /opt/shared/scripts/test_public_lexicon.py",
            "python3 /opt/shared/scripts/test_install_site_ui_guard.py",
            "python3 /opt/shared/scripts/test_public_article_rotation.py",
            "python3 /opt/shared/scripts/test_site_article_source_audit.py",
            "python3 /opt/shared/scripts/test_repair_article_source_urls.py",
            "python3 /opt/shared/scripts/test_repair_cross_language_article_links.py",
            "python3 /opt/shared/scripts/test_refresh_prediction_db_meta.py",
            "python3 /opt/shared/scripts/test_site_link_crawler.py",
            "python3 /opt/shared/scripts/stateful_user_journey_audit.py --base-url https://nowpattern.com --json-out /opt/shared/reports/stateful_user_journey_audit.json",
            "python3 /opt/shared/scripts/test_release_governor.py",
            "python3 /opt/shared/scripts/fix_global_language_switcher.py",
            "python3 /opt/shared/scripts/update_about_pages.py",
            "python3 /opt/shared/scripts/install_en_article_route_guard.py --quiet",
            "python3 /opt/shared/scripts/install_uuid_preview_route_guard.py --quiet",
            "python3 /opt/shared/scripts/fix_ghost_content_links.py --quiet --table settings --table posts",
            "python3 /opt/shared/scripts/repair_cross_language_article_links.py",
            "python3 /opt/shared/scripts/check_ghost_article_routes.py --repair --quiet",
            "python3 /opt/shared/scripts/install_site_ui_guard.py",
            "python3 /opt/shared/scripts/install_ecosystem_mission_control.py",
            "python3 /opt/shared/scripts/ecosystem_governance_audit.py --json-out /opt/shared/reports/site_guard/ecosystem_governance.json",
            "python3 /opt/shared/scripts/prediction_deploy_gate.py --refresh",
            "python3 /opt/shared/scripts/prediction_page_builder.py --update --lang both",
            "python3 /opt/shared/scripts/check_live_repo_drift.py --host local",
        ]
    )

    if args.dry_run:
        print("WOULD RUN:")
        print("  " + " ".join(shlex.quote(part) for part in push_cmd))
        print(f"  ssh {args.host} {shlex.quote(remote_cmd)}")
        return 0

    run_checked(push_cmd, REPO_ROOT)
    ssh_bin = choose_ssh_bin()
    run_checked([ssh_bin, args.host, remote_cmd], REPO_ROOT)
    print("OK: deployed site UI guard stack")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
