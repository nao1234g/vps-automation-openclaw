#!/usr/bin/env python3
"""Normalize EN public URLs at the Ghost theme/source layer."""

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
DEFAULT_SERVICE = "ghost-nowpattern.service"
DEFAULT_SITE_URL = "https://nowpattern.com"

CARD_TEMPLATE_PATH = Path("partials/post-card.hbs")
POST_TEMPLATE_PATH = Path("post.hbs")

CARD_OLD = '<a class="gh-card-link" href="{{url}}">'
CARD_NEW = '<a class="gh-card-link" href="{{#if canonical_url}}{{canonical_url}}{{else}}{{url}}{{/if}}">'

JSONLD_OLD = '"url":"{{url absolute="true"}}"'
JSONLD_NEW = '"url":"{{#if canonical_url}}{{canonical_url}}{{else}}{{url absolute="true"}}{{/if}}"'


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


def patch_text_once(content: str, old: str, new: str) -> tuple[str, int]:
    if new in content:
        return content, 0
    count = content.count(old)
    if count <= 0:
        raise ValueError(f"expected snippet not found: {old[:80]}")
    return content.replace(old, new), count


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


def restart_service(service_name: str, dry_run: bool) -> None:
    if dry_run:
        return
    subprocess.run(["systemctl", "restart", service_name], check=True)


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Patch Ghost theme EN URLs and canonical_url records.")
    parser.add_argument("--db", default=str(DEFAULT_GHOST_DB), help="Path to ghost.db")
    parser.add_argument("--theme-root", default=str(DEFAULT_THEME_ROOT), help="Path to active Ghost theme root")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL, help="Canonical public site URL")
    parser.add_argument("--service", default=DEFAULT_SERVICE, help="Ghost systemd service to restart")
    parser.add_argument("--dry-run", action="store_true", help="Report planned changes without writing")
    parser.add_argument("--skip-db", action="store_true", help="Skip canonical_url normalization")
    parser.add_argument("--skip-theme", action="store_true", help="Skip theme template patching")
    parser.add_argument("--no-restart", action="store_true", help="Do not restart Ghost after patching")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    db_path = Path(args.db)
    theme_root = Path(args.theme_root)
    if not db_path.exists() and not args.skip_db:
        raise FileNotFoundError(f"ghost db not found: {db_path}")
    if not theme_root.exists() and not args.skip_theme:
        raise FileNotFoundError(f"theme root not found: {theme_root}")

    report: dict[str, object] = {
        "site_url": normalize_site_url(args.site_url),
        "db": str(db_path),
        "theme_root": str(theme_root),
        "dry_run": args.dry_run,
        "db_changes": {},
        "theme_changes": [],
        "restarted": False,
    }

    any_change = False
    if not args.skip_db:
        db_changes = normalize_en_canonical_urls(db_path, args.site_url, args.dry_run)
        report["db_changes"] = db_changes
        any_change = any_change or bool(db_changes.get("canonical_urls_changed"))

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
        any_change = any_change or any(item["changed"] for item in theme_changes)

    if any_change and not args.no_restart:
        restart_service(args.service, args.dry_run)
        report["restarted"] = not args.dry_run

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
