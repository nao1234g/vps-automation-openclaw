#!/usr/bin/env python3
"""Generate managed Caddy redirects for Ghost /p/<uuid>/ preview-style URLs."""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
from pathlib import Path


DEFAULT_GHOST_DB = Path("/var/www/nowpattern/content/data/ghost.db")
DEFAULT_CADDYFILE = Path("/etc/caddy/Caddyfile")
DEFAULT_OUTPUT = Path("/etc/caddy/nowpattern-preview-routes.txt")
IMPORT_LINE = "import /etc/caddy/nowpattern-preview-routes.txt"
IMPORT_MARKER = "# np-preview-routes"
INSERT_BEFORE_CANDIDATES = [
    "\timport /etc/caddy/nowpattern-en-article-routes.txt # np-en-article-routes",
    "\timport /etc/caddy/nowpattern-redirects.txt",
]


def canonical_path_for_slug(slug: str) -> str | None:
    slug = (slug or "").strip().strip("/")
    if not slug:
        return None
    if slug.startswith("en-"):
        return f"/en/{slug[3:]}/"
    return f"/{slug}/"


def load_uuid_routes(db_path: Path) -> list[tuple[str, str]]:
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    rows = list(
        cur.execute(
            """
            SELECT uuid, slug
            FROM posts
            WHERE status = 'published'
              AND type IN ('post', 'page')
              AND uuid IS NOT NULL
              AND slug IS NOT NULL
            ORDER BY published_at DESC, updated_at DESC
            """
        )
    )
    con.close()

    routes: list[tuple[str, str]] = []
    seen: set[str] = set()
    for uuid_value, slug in rows:
        canonical = canonical_path_for_slug(slug)
        if not uuid_value or not canonical or uuid_value in seen:
            continue
        seen.add(uuid_value)
        routes.append((uuid_value, canonical))
    return routes


def build_route_file(routes: list[tuple[str, str]]) -> str:
    lines = [
        "# Managed by install_uuid_preview_route_guard.py",
        "# Redirect Ghost preview-style /p/<uuid>/ URLs to canonical public paths.",
    ]
    for uuid_value, canonical in routes:
        lines.append(f"redir /p/{uuid_value} {canonical} permanent")
        lines.append(f"redir /p/{uuid_value}/ {canonical} permanent")
    return "\n".join(lines).rstrip() + "\n"


def ensure_caddy_import(caddyfile: Path) -> bool:
    original = caddyfile.read_text(encoding="utf-8")
    if IMPORT_LINE in original:
        return False
    for marker in INSERT_BEFORE_CANDIDATES:
        if marker in original:
            updated = original.replace(
                marker,
                f"\t{IMPORT_LINE} {IMPORT_MARKER}\n{marker}",
                1,
            )
            caddyfile.write_text(updated, encoding="utf-8")
            return True
    raise RuntimeError(f"could not find insertion marker in {caddyfile}")


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
    parser = argparse.ArgumentParser(description="Install managed Caddy redirects for Ghost /p/<uuid>/ preview URLs.")
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

    routes = load_uuid_routes(db_path)
    route_file = build_route_file(routes)

    output_changed = write_if_changed(output_path, route_file)
    import_changed = ensure_caddy_import(caddyfile)
    changed = output_changed or import_changed

    if changed:
        run_checked(["caddy", "validate", "--config", str(caddyfile)])
        run_checked(["systemctl", "reload", "caddy"])
        print(f"OK: installed UUID preview route guard ({len(routes)} managed routes)")
        print(f"  output_changed={output_changed} import_changed={import_changed}")
    elif not args.quiet:
        print(f"OK: UUID preview route guard already current ({len(routes)} managed routes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
