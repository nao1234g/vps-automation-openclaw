#!/usr/bin/env python3
"""Inventory and audit every Ghost Admin write-capable script in the repo.

Goals:
- Prevent "active 12 paths are guarded" from hiding untracked write-capable helpers.
- Force every Ghost write surface into an explicit governance class.
- Fail if a new write-capable path appears without being classified.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = [REPO_ROOT / "scripts", REPO_ROOT / ".claude"]

MUTATING_PATTERNS = (
    re.compile(r"requests\.(put|post|delete)\s*\(", re.IGNORECASE),
    re.compile(r'ghost_request\("?(PUT|POST|DELETE)"?', re.IGNORECASE),
    re.compile(r'method\s*=\s*"(PUT|POST|DELETE)"', re.IGNORECASE),
    re.compile(r"/ghost/api/admin/.+\?source=html", re.IGNORECASE),
)

INSTRUCTION_ONLY_HINTS = (
    "Ghost Admin API で更新",
    "PUT /ghost/api/admin/posts",
    "Ghost Admin APIで更新",
)

GOVERNANCE_CLASSES = {
    "audited_active_release",
    "audited_active_guard",
    "audited_active_maintenance",
    "manual_maintenance",
    "emergency_repair",
    "dormant_batch",
    "instructional_only",
}

ACTIVE_GOVERNED_CLASSES = {
    "audited_active_release",
    "audited_active_guard",
    "audited_active_maintenance",
}

CLASSIFIED_SURFACES: dict[str, str] = {
    "scripts/a1-bulk-en-translator.py": "dormant_batch",
    "scripts/a3-schema-injector.py": "manual_maintenance",
    "scripts/a3_feature_image.py": "manual_maintenance",
    "scripts/a4-hreflang-injector.py": "audited_active_maintenance",
    "scripts/a4-hreflang-reset.py": "manual_maintenance",
    "scripts/ai_redteam.py": "manual_maintenance",
    "scripts/article_schema_self_test.py": "audited_active_guard",
    "scripts/assign_tags_to_posts.py": "manual_maintenance",
    "scripts/batch_format_upgrade.py": "manual_maintenance",
    "scripts/build_article_release_manifest.py": "audited_active_guard",
    "scripts/builder_patch_faqpage.py": "manual_maintenance",
    "scripts/c1-newsletter-setup.py": "audited_active_maintenance",
    "scripts/create_tag_pages.py": "manual_maintenance",
    "scripts/create_taxonomy_guide.py": "manual_maintenance",
    "scripts/dedup2.py": "manual_maintenance",
    "scripts/dedup_articles.py": "manual_maintenance",
    "scripts/deep_pattern_batch1.py": "dormant_batch",
    "scripts/deep_pattern_batch2.py": "dormant_batch",
    "scripts/deep_pattern_batch3.py": "dormant_batch",
    "scripts/draft_rescue.py": "emergency_repair",
    "scripts/fix_article_tags.py": "manual_maintenance",
    "scripts/fix_article_tags_footer.py": "manual_maintenance",
    "scripts/fix_broken_article.py": "emergency_repair",
    "scripts/fix_hormuz_lexical.py": "emergency_repair",
    "scripts/fix_ja_headings.py": "manual_maintenance",
    "scripts/fix_missing_ghost_tags.py": "manual_maintenance",
    "scripts/fix_tag_urls.py": "manual_maintenance",
    "scripts/ghost_contract_test.py": "audited_active_guard",
    "scripts/ghost_integrity_check.py": "audited_active_guard",
    "scripts/ghost_tag_updater.py": "manual_maintenance",
    "scripts/ghost_tag_setup_v3.py": "manual_maintenance",
    "scripts/ghost_webhook_server.py": "audited_active_guard",
    "scripts/ghost_write_surface_audit.py": "manual_maintenance",
    "scripts/image_audit_autofix.py": "audited_active_maintenance",
    "scripts/internal-link-builder.py": "audited_active_maintenance",
    "scripts/internal_link_enhancer.py": "audited_active_maintenance",
    "scripts/jp_en_pairing_checker.py": "audited_active_guard",
    "scripts/link_integrity_checker.py": "audited_active_guard",
    "scripts/manifold_widget_injector.py": "manual_maintenance",
    "scripts/mark_article_human_approved.py": "manual_maintenance",
    "scripts/meta_desc_batch.py": "manual_maintenance",
    "scripts/migrate_prediction_links.py": "manual_maintenance",
    "scripts/neo_queue_dispatcher.py": "instructional_only",
    "scripts/news-analyst-pipeline.py": "dormant_batch",
    "scripts/nowpattern-ghost-post.py": "dormant_batch",
    "scripts/nowpattern_article_patcher.py": "manual_maintenance",
    "scripts/nowpattern_post_audit.py": "audited_active_guard",
    "scripts/nowpattern_publish_gateway.py": "dormant_batch",
    "scripts/nowpattern_publisher.py": "audited_active_release",
    "scripts/patch_stakeholder_table.py": "manual_maintenance",
    "scripts/phase7_public_rules_pages.py": "manual_maintenance",
    "scripts/prediction_auto_update.py": "audited_active_maintenance",
    "scripts/prediction_ogp_generator.py": "audited_active_maintenance",
    "scripts/prediction_page_builder.py": "audited_active_release",
    "scripts/publish_predictions_articles.py": "dormant_batch",
    "scripts/qa_sentinel.py": "audited_active_guard",
    "scripts/quarantine_unverifiable_articles.py": "emergency_repair",
    "scripts/regen_pattern_history.py": "manual_maintenance",
    "scripts/register_ghost_webhook.py": "manual_maintenance",
    "scripts/repair_article_tags.py": "manual_maintenance",
    "scripts/repair_speed_log_tags.py": "manual_maintenance",
    "scripts/reformat_articles.py": "manual_maintenance",
    "scripts/rollback_meta_desc.py": "emergency_repair",
    "scripts/semantic_qa.py": "manual_maintenance",
    "scripts/slug_repair.py": "emergency_repair",
    "scripts/slug_repair2.py": "emergency_repair",
    "scripts/translation_qa.py": "audited_active_guard",
    "scripts/unsplash_image_assigner.py": "manual_maintenance",
    "scripts/update_article_titles.py": "manual_maintenance",
    "scripts/update_integrity_audit_pages.py": "manual_maintenance",
    "scripts/update_about_pages.py": "audited_active_maintenance",
    "scripts/update_predictions_page.py": "manual_maintenance",
    "scripts/update_taxonomy_pages.py": "manual_maintenance",
    "scripts/_dedup_articles.py": "manual_maintenance",
    "scripts/_fix_404_articles.py": "emergency_repair",
    "scripts/_fix_404_republish.py": "emergency_repair",
    "scripts/_fix_404_tags.py": "emergency_repair",
    "scripts/_fix_existing_articles.py": "emergency_repair",
    "scripts/_fix_existing_articles_tags.py": "emergency_repair",
    "scripts/_fix_existing_articles_v2.py": "emergency_repair",
    "scripts/_fix_ghost_tags.py": "manual_maintenance",
    "scripts/_ghost_setup_disclaimer_predictions.py": "manual_maintenance",
    "scripts/_recreate_404_articles.py": "emergency_repair",
}

ACTIVE_AUDITED_REQUIREMENTS = {
    "scripts/build_article_release_manifest.py": ["evaluate_governed_release", "release_governor"],
    "scripts/ghost_webhook_server.py": ["evaluate_governed_release", "release_governor"],
    "scripts/nowpattern_publisher.py": ["assert_governed_release_ready", "release_governor"],
    "scripts/prediction_page_builder.py": ["prediction_deploy_gate.py", "--skip-deploy-gate"],
    "scripts/qa_sentinel.py": ["evaluate_governed_release", "release_governor"],
}


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _contains_instruction_only(text: str) -> bool:
    return any(hint in text for hint in INSTRUCTION_ONLY_HINTS)


def discover_mutating_candidates() -> list[str]:
    discovered: list[str] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "ghost/api/admin" not in text and 'ghost_request("' not in text:
                continue
            if _contains_instruction_only(text) and not any(p.search(text) for p in MUTATING_PATTERNS):
                discovered.append(_relative(path))
                continue
            if any(p.search(text) for p in MUTATING_PATTERNS):
                discovered.append(_relative(path))
    return sorted(set(discovered))


def run_audit() -> dict[str, object]:
    failures: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    discovered = discover_mutating_candidates()
    discovered_set = set(discovered)
    classified_set = set(CLASSIFIED_SURFACES)

    unknown = sorted(discovered_set - classified_set)
    stale = sorted(classified_set - discovered_set)

    for path in unknown:
        failures.append({"path": path, "error": "unclassified_ghost_write_surface"})

    for path in stale:
        warnings.append({"path": path, "warning": "classified_surface_not_currently_detected"})

    for path in discovered:
        klass = CLASSIFIED_SURFACES.get(path)
        if klass and klass not in GOVERNANCE_CLASSES:
            failures.append({"path": path, "error": f"invalid_governance_class:{klass}"})
            continue
        if path in ACTIVE_AUDITED_REQUIREMENTS:
            file_path = REPO_ROOT / path
            text = file_path.read_text(encoding="utf-8", errors="replace")
            missing = [token for token in ACTIVE_AUDITED_REQUIREMENTS[path] if token not in text]
            if missing:
                failures.append({"path": path, "error": "missing_required_tokens", "missing": missing})

    counts = Counter(CLASSIFIED_SURFACES.get(path, "unclassified") for path in discovered)
    return {
        "discovered_total": len(discovered),
        "classified_total": len(CLASSIFIED_SURFACES),
        "class_counts": dict(sorted(counts.items())),
        "failures": failures,
        "warnings": warnings,
        "discovered": discovered,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit all Ghost Admin write-capable scripts.")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    report = run_audit()
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
