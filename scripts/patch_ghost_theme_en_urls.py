#!/usr/bin/env python3
"""Normalize EN public URLs and fixed-page language templates.

This script keeps the canonical/card URL contract in sync and makes sure
English fixed pages render through the English layout template.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_GHOST_DB = Path("/var/www/nowpattern/content/data/ghost.db")
DEFAULT_THEME_ROOT = Path("/var/www/nowpattern/content/themes/source")
DEFAULT_ROUTES_PATH = Path("/var/www/nowpattern/content/settings/routes.yaml")
DEFAULT_CADDY_REDIRECTS_PATH = Path("/etc/caddy/nowpattern-redirects.txt")
DEFAULT_SERVICE = "ghost-nowpattern.service"
DEFAULT_CADDY_SERVICE = "caddy"
DEFAULT_SITE_URL = "https://nowpattern.com"

CARD_TEMPLATE_PATH = Path("partials/post-card.hbs")
POST_TEMPLATE_PATH = Path("post.hbs")
PAGE_TEMPLATE_PATH = Path("page.hbs")
PAGE_EN_TEMPLATE_PATH = Path("page-en.hbs")
CARD_OLD = '<a class="gh-card-link" href="{{url}}">'
CARD_NEW = '<a class="gh-card-link" href="{{#if canonical_url}}{{canonical_url}}{{else}}{{url}}{{/if}}">'

JSONLD_OLD = '"url":"{{url absolute="true"}}"'
JSONLD_NEW = '"url":"{{#if canonical_url}}{{canonical_url}}{{else}}{{url absolute="true"}}{{/if}}"'
PAGE_DEFAULT_EXTENDS = "{{!< default}}"
PAGE_EN_EXTENDS = "{{!< default-en}}"
PREDICTION_METHODOLOGY_ROUTES = (
    "  /forecasting-methodology/:\n"
    "    data: page.forecasting-methodology\n"
    "    template: page\n"
    "  /forecast-scoring-and-resolution/:\n"
    "    data: page.forecast-scoring-and-resolution\n"
    "    template: page\n"
    "  /forecast-integrity-and-audit/:\n"
    "    data: page.forecast-integrity-and-audit\n"
    "    template: page\n"
    "  /en/forecasting-methodology/:\n"
    "    data: page.en-forecasting-methodology\n"
    "    template: page\n"
    "  /en/forecast-scoring-and-resolution/:\n"
    "    data: page.en-forecast-scoring-and-resolution\n"
    "    template: page\n"
    "  /en/forecast-integrity-and-audit/:\n"
    "    data: page.en-forecast-integrity-and-audit\n"
    "    template: page\n"
)
STALE_METHODOLOGY_REDIRECTS = (
    "redir /forecasting-methodology/ /forecast-rules/ permanent",
    "redir /en/forecasting-methodology/ /en/forecast-rules/ permanent",
    "redir /forecast-scoring-and-resolution/ /scoring-guide/ permanent",
    "redir /en/forecast-scoring-and-resolution/ /en/scoring-guide/ permanent",
    "redir /forecast-integrity-and-audit/ /integrity-audit/ permanent",
    "redir /en/forecast-integrity-and-audit/ /en/integrity-audit/ permanent",
)


@dataclass
class FilePatchResult:
    path: str
    changed: bool
    replacements: int


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def normalize_site_url(site_url: str) -> str:
    return site_url.rstrip("/")


def backup_file(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d%H%M%S")
    backup_path = path.with_name(f"{path.name}.bak-en-urls-{stamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def patch_text_once(content: str, old: str | tuple[str, ...], new: str) -> tuple[str, int]:
    if new in content:
        return content, 0
    olds = old if isinstance(old, tuple) else (old,)
    for candidate in olds:
        count = content.count(candidate)
        if count > 0:
            return content.replace(candidate, new), count
    raise ValueError(f"expected snippet not found: {olds[0][:80]}")


def patch_theme_file(path: Path, replacements: list[tuple[str, str]], dry_run: bool) -> FilePatchResult:
    content = path.read_text(encoding="utf-8")
    updated = content
    total = 0
    for old, new in replacements:
        updated, count = patch_text_once(updated, old, new)
        total += count
    changed = updated != content
    if changed and not dry_run:
        backup_file(path)
        path.write_text(updated, encoding="utf-8")
    return FilePatchResult(path=str(path), changed=changed, replacements=total)


def ensure_en_page_template(theme_root: Path, dry_run: bool) -> FilePatchResult:
    source_path = theme_root / PAGE_TEMPLATE_PATH
    target_path = theme_root / PAGE_EN_TEMPLATE_PATH
    if not source_path.exists():
        raise FileNotFoundError(f"page template not found: {source_path}")

    source_text = source_path.read_text(encoding="utf-8")
    if PAGE_EN_EXTENDS in source_text:
        desired = source_text
    elif PAGE_DEFAULT_EXTENDS in source_text:
        desired = source_text.replace(PAGE_DEFAULT_EXTENDS, PAGE_EN_EXTENDS, 1)
    else:
        desired = f"{PAGE_EN_EXTENDS}\n{source_text}"

    current = target_path.read_text(encoding="utf-8") if target_path.exists() else None
    changed = current != desired
    if changed and not dry_run:
        if target_path.exists():
            backup_file(target_path)
        target_path.write_text(desired, encoding="utf-8")
    return FilePatchResult(path=str(target_path), changed=changed, replacements=1 if changed else 0)


def patch_routes_for_en_pages(routes_path: Path, dry_run: bool) -> FilePatchResult:
    content = routes_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    updated = list(lines)
    in_routes = False
    current_en_route = False
    current_en_page_data = False
    replacements = 0

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "routes:":
            in_routes = True
            current_en_route = False
            current_en_page_data = False
            continue
        if stripped in {"collections:", "taxonomies:"}:
            in_routes = False
            current_en_route = False
            current_en_page_data = False
            continue
        if not in_routes:
            continue
        if line.startswith("  /") and stripped.endswith(":"):
            current_en_route = stripped.startswith("/en/")
            current_en_page_data = False
            continue
        if current_en_route and stripped.startswith("data: "):
            current_en_page_data = stripped.startswith("data: page.en-")
            continue
        if current_en_route and current_en_page_data and stripped == "template: page":
            updated[idx] = line.replace("template: page", "template: page-en", 1)
            replacements += 1

    updated_text = "\n".join(updated)
    if content.endswith("\n"):
        updated_text += "\n"
    changed = updated_text != content
    if changed and not dry_run:
        backup_file(routes_path)
        routes_path.write_text(updated_text, encoding="utf-8")
    return FilePatchResult(path=str(routes_path), changed=changed, replacements=replacements)


def ensure_prediction_methodology_routes(routes_path: Path, dry_run: bool) -> FilePatchResult:
    content = routes_path.read_text(encoding="utf-8")
    required_markers = (
        "/forecasting-methodology/:",
        "/forecast-scoring-and-resolution/:",
        "/forecast-integrity-and-audit/:",
        "/en/forecasting-methodology/:",
        "/en/forecast-scoring-and-resolution/:",
        "/en/forecast-integrity-and-audit/:",
    )
    if all(marker in content for marker in required_markers):
        return FilePatchResult(path=str(routes_path), changed=False, replacements=0)
    if "routes:\n" not in content:
        raise ValueError("routes.yaml missing routes: header")
    updated = content.replace("routes:\n", "routes:\n" + PREDICTION_METHODOLOGY_ROUTES, 1)
    changed = updated != content
    if changed and not dry_run:
        backup_file(routes_path)
        routes_path.write_text(updated, encoding="utf-8")
    return FilePatchResult(path=str(routes_path), changed=changed, replacements=len(required_markers) if changed else 0)


def remove_stale_methodology_redirects(redirects_path: Path, dry_run: bool) -> FilePatchResult:
    content = redirects_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    stale_lines = set(STALE_METHODOLOGY_REDIRECTS)
    filtered = [line for line in lines if line.strip() not in stale_lines]
    removed = len(lines) - len(filtered)
    updated = "\n".join(filtered)
    if content.endswith("\n"):
        updated += "\n"
    changed = updated != content
    if changed and not dry_run:
        backup_file(redirects_path)
        redirects_path.write_text(updated, encoding="utf-8")
    return FilePatchResult(path=str(redirects_path), changed=changed, replacements=removed)


def target_public_en_url(site_url: str, slug: str) -> str | None:
    if not slug.startswith("en-") or len(slug) <= 3:
        return None
    return f"{normalize_site_url(site_url)}/en/{slug[3:]}/"


def normalize_en_canonical_urls(db_path: Path, site_url: str, dry_run: bool) -> dict[str, int]:
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    rows = list(
        cur.execute(
            """
            SELECT id, slug, canonical_url
            FROM posts
            WHERE status = 'published'
              AND slug LIKE 'en-%'
            """
        )
    )
    changed = 0
    skipped = 0
    for post_id, slug, canonical_url in rows:
        target = target_public_en_url(site_url, str(slug or ""))
        if not target:
            skipped += 1
            continue
        if canonical_url == target:
            continue
        changed += 1
        if not dry_run:
            cur.execute(
                "UPDATE posts SET canonical_url = ? WHERE id = ?",
                (target, post_id),
            )
    if changed and not dry_run:
        con.commit()
    con.close()
    return {
        "published_en_posts": len(rows),
        "canonical_urls_changed": changed,
        "canonical_urls_skipped": skipped,
    }


def run_systemctl(service_name: str, action: str, dry_run: bool) -> None:
    if dry_run:
        return
    subprocess.run(["systemctl", action, service_name], check=True)


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(
        description="Patch Ghost EN URLs, canonical_url records, and English fixed-page templates."
    )
    parser.add_argument("--db", default=str(DEFAULT_GHOST_DB), help="Path to ghost.db")
    parser.add_argument("--theme-root", default=str(DEFAULT_THEME_ROOT), help="Path to active Ghost theme root")
    parser.add_argument("--routes", default=str(DEFAULT_ROUTES_PATH), help="Path to Ghost routes.yaml")
    parser.add_argument("--redirects", default=str(DEFAULT_CADDY_REDIRECTS_PATH), help="Path to Caddy redirects file")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL, help="Canonical public site URL")
    parser.add_argument("--service", default=DEFAULT_SERVICE, help="Ghost systemd service to restart")
    parser.add_argument("--caddy-service", default=DEFAULT_CADDY_SERVICE, help="Caddy systemd service to reload")
    parser.add_argument("--dry-run", action="store_true", help="Report planned changes without writing")
    parser.add_argument("--skip-db", action="store_true", help="Skip canonical_url normalization")
    parser.add_argument("--skip-theme", action="store_true", help="Skip theme template patching")
    parser.add_argument("--skip-page-lang", action="store_true", help="Skip English page template and routes patching")
    parser.add_argument("--skip-caddy", action="store_true", help="Skip stale Caddy redirect cleanup")
    parser.add_argument("--no-restart", action="store_true", help="Do not restart Ghost after patching")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    db_path = Path(args.db)
    theme_root = Path(args.theme_root)
    routes_path = Path(args.routes)
    redirects_path = Path(args.redirects)
    if not db_path.exists() and not args.skip_db:
        raise FileNotFoundError(f"ghost db not found: {db_path}")
    if not theme_root.exists() and not args.skip_theme:
        raise FileNotFoundError(f"theme root not found: {theme_root}")
    if not routes_path.exists() and not args.skip_page_lang:
        raise FileNotFoundError(f"routes file not found: {routes_path}")
    if not redirects_path.exists() and not args.skip_caddy:
        raise FileNotFoundError(f"redirects file not found: {redirects_path}")

    report: dict[str, object] = {
        "site_url": normalize_site_url(args.site_url),
        "db": str(db_path),
        "theme_root": str(theme_root),
        "routes": str(routes_path),
        "redirects": str(redirects_path),
        "dry_run": args.dry_run,
        "db_changes": {},
        "theme_changes": [],
        "page_lang_changes": [],
        "caddy_changes": {},
        "restarted": False,
        "caddy_reloaded": False,
    }

    ghost_change = False
    caddy_change = False
    if not args.skip_db:
        db_changes = normalize_en_canonical_urls(db_path, args.site_url, args.dry_run)
        report["db_changes"] = db_changes
        ghost_change = ghost_change or bool(db_changes.get("canonical_urls_changed"))

    if not args.skip_theme:
        card_result = patch_theme_file(
            theme_root / CARD_TEMPLATE_PATH,
            [(CARD_OLD, CARD_NEW)],
            args.dry_run,
        )
        post_result = patch_theme_file(
            theme_root / POST_TEMPLATE_PATH,
            [(JSONLD_OLD, JSONLD_NEW)],
            args.dry_run,
        )
        theme_changes = [asdict(card_result), asdict(post_result)]
        report["theme_changes"] = theme_changes
        ghost_change = ghost_change or any(item["changed"] for item in theme_changes)

    if not args.skip_page_lang:
        page_en_result = ensure_en_page_template(theme_root, args.dry_run)
        methodology_routes_result = ensure_prediction_methodology_routes(routes_path, args.dry_run)
        routes_result = patch_routes_for_en_pages(routes_path, args.dry_run)
        page_lang_changes = [asdict(page_en_result), asdict(methodology_routes_result), asdict(routes_result)]
        report["page_lang_changes"] = page_lang_changes
        ghost_change = ghost_change or any(item["changed"] for item in page_lang_changes)

    if not args.skip_caddy:
        caddy_result = remove_stale_methodology_redirects(redirects_path, args.dry_run)
        report["caddy_changes"] = asdict(caddy_result)
        caddy_change = caddy_result.changed

    if ghost_change and not args.no_restart:
        run_systemctl(args.service, "restart", args.dry_run)
        report["restarted"] = not args.dry_run
    if caddy_change and not args.no_restart:
        run_systemctl(args.caddy_service, "reload", args.dry_run)
        report["caddy_reloaded"] = not args.dry_run

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
