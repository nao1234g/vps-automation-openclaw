#!/usr/bin/env python3
"""Generate managed Caddy routes for published EN-prefixed Ghost articles."""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
from pathlib import Path


DEFAULT_GHOST_DB = Path("/var/www/nowpattern/content/data/ghost.db")
DEFAULT_CADDYFILE = Path("/etc/caddy/Caddyfile")
DEFAULT_OUTPUT = Path("/etc/caddy/nowpattern-en-article-routes.txt")
IMPORT_LINE = "import /etc/caddy/nowpattern-en-article-routes.txt"
IMPORT_MARKER = "# np-en-article-routes"
INSERT_BEFORE = "# ── EN articles URL fix (2026-03-29) ────────────────────────────────────"


def load_published_en_prefixed_slugs(db_path: Path) -> list[str]:
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    rows = list(
        cur.execute(
            """
            SELECT slug
            FROM posts
            WHERE status = 'published'
              AND type = 'post'
              AND slug LIKE 'en-%'
            ORDER BY slug
            """
        )
    )
    con.close()
    stripped = []
    seen: set[str] = set()
    for (slug,) in rows:
        if not slug or not slug.startswith("en-"):
            continue
        canonical = slug[3:]
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        stripped.append(canonical)
    return stripped


def build_route_file(slugs: list[str]) -> str:
    lines = [
        "# Managed by install_en_article_route_guard.py",
        "# Canonical /en/<slug>/ paths for published Ghost posts whose real slug is en-<slug>.",
    ]
    for index, slug in enumerate(slugs, start=1):
        matcher = f"@np_en_article_{index:04d}"
        canonical = f"/en/{slug}"
        target = f"/en/en-{slug}/"
        lines.extend(
            [
                f"{matcher} path {canonical} {canonical}/",
                f"handle {matcher} {{",
                f"\trewrite * {target}",
                "\treverse_proxy localhost:2368",
                "}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def ensure_caddy_import(caddyfile: Path) -> bool:
    original = caddyfile.read_text(encoding="utf-8")
    if IMPORT_LINE in original:
        return False
    if INSERT_BEFORE not in original:
        raise RuntimeError(f"could not find insertion marker in {caddyfile}")
    updated = original.replace(
        INSERT_BEFORE,
        f"\t{IMPORT_LINE} {IMPORT_MARKER}\n\n\t{INSERT_BEFORE}",
        1,
    )
    caddyfile.write_text(updated, encoding="utf-8")
    return True


def write_if_changed(path: Path, content: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def run_checked(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"command failed: {' '.join(command)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install managed Caddy routes for EN-prefixed Ghost articles.")
    parser.add_argument("--db", default=str(DEFAULT_GHOST_DB), help="Path to Ghost sqlite DB")
    parser.add_argument("--caddyfile", default=str(DEFAULT_CADDYFILE), help="Path to Caddyfile")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to managed Caddy import file")
    parser.add_argument("--quiet", action="store_true", help="Suppress no-op output")
    args = parser.parse_args()

    db_path = Path(args.db)
    caddyfile = Path(args.caddyfile)
    output_path = Path(args.output)

    if not db_path.exists():
        raise FileNotFoundError(f"ghost db not found: {db_path}")
    if not caddyfile.exists():
        raise FileNotFoundError(f"caddyfile not found: {caddyfile}")

    slugs = load_published_en_prefixed_slugs(db_path)
    route_file = build_route_file(slugs)

    output_changed = write_if_changed(output_path, route_file)
    import_changed = ensure_caddy_import(caddyfile)
    changed = output_changed or import_changed

    if changed:
        run_checked(["caddy", "validate", "--config", str(caddyfile)])
        run_checked(["systemctl", "reload", "caddy"])
        print(f"OK: installed EN article route guard ({len(slugs)} managed routes)")
        print(f"  output_changed={output_changed} import_changed={import_changed}")
    elif not args.quiet:
        print(f"OK: EN article route guard already current ({len(slugs)} managed routes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
