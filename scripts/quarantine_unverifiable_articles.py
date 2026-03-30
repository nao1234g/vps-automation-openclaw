#!/usr/bin/env python3
"""Quarantine published Ghost posts that fail source/truth integrity."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import ssl
import time
import urllib.request

from article_release_guard import evaluate_release_blockers

GHOST_DB = "/var/www/nowpattern/content/data/ghost.db"
CRON_ENV = "/opt/cron-env.sh"
GHOST_URL = "https://nowpattern.com"
REPORT_PATH = "/opt/shared/reports/quarantine_unverifiable_articles.json"
SKIP_SLUGS = {
    "about",
    "en-about",
    "predictions",
    "en-predictions",
    "members",
    "en-members",
    "taxonomy",
    "en-taxonomy",
    "taxonomy-guide",
    "en-taxonomy-guide",
    "taxonomy-ja",
}


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if os.path.exists(CRON_ENV):
        with open(CRON_ENV, encoding="utf-8") as f:
            for line in f:
                if line.startswith("export "):
                    key, _, value = line[7:].partition("=")
                    env[key.strip()] = value.strip().strip('"').strip("'")
    env.update(os.environ)
    return env


def ghost_jwt(admin_api_key: str) -> str:
    import base64
    import hashlib
    import hmac

    kid, secret = admin_api_key.split(":")
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "kid": kid, "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    now = int(time.time())
    payload = base64.urlsafe_b64encode(
        json.dumps({"iat": now, "exp": now + 300, "aud": "/admin/"}).encode()
    ).rstrip(b"=").decode()
    sig = hmac.new(bytes.fromhex(secret), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"


def ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def draft_post(post_id: str, updated_at: str, admin_api_key: str) -> bool:
    body = json.dumps({"posts": [{"id": post_id, "status": "draft", "updated_at": updated_at}]}).encode()
    req = urllib.request.Request(
        f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/",
        data=body,
        method="PUT",
        headers={
            "Authorization": "Ghost " + ghost_jwt(admin_api_key),
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--mode",
        choices=["source-section-only", "all-truth-errors", "all-release-errors"],
        default="source-section-only",
    )
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    env = load_env()
    admin_api_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")

    con = sqlite3.connect(GHOST_DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT p.id, p.slug, p.title, p.html, p.updated_at,
               GROUP_CONCAT(t.slug, ' ') AS tag_slugs
        FROM posts p
        LEFT JOIN posts_tags pt ON pt.post_id = p.id
        LEFT JOIN tags t ON t.id = pt.tag_id
        WHERE status='published' AND type='post'
        GROUP BY p.id, p.slug, p.title, p.html, p.updated_at
        ORDER BY published_at DESC
        """
    ).fetchall()
    con.close()

    affected: list[dict[str, object]] = []
    for row in rows:
        slug = row["slug"]
        if slug in SKIP_SLUGS:
            continue
        release_block = evaluate_release_blockers(
            title=row["title"] or "",
            html=row["html"] or "",
            tags=(row["tag_slugs"] or "").split(),
            site_url=GHOST_URL,
            status="published",
            channel="public",
            require_external_sources=True,
            check_source_fetchability=True,
        )
        errors = release_block["errors"]
        ext_urls = release_block["external_urls"]
        if args.mode == "source-section-only":
            if "BROKEN_SOURCE_SECTION" not in errors:
                continue
        elif args.mode == "all-truth-errors":
            truth_only = [e for e in errors if not e.startswith("HUMAN_APPROVAL_REQUIRED")]
            if not truth_only:
                continue
        elif not errors:
            continue
        affected.append(
            {
                "id": row["id"],
                "slug": slug,
                "title": row["title"],
                "updated_at": row["updated_at"],
                "errors": errors,
                "external_sources": ext_urls,
            }
        )
        if args.limit and len(affected) >= args.limit:
            break

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump({"mode": args.mode, "count": len(affected), "posts": affected}, f, ensure_ascii=False, indent=2)

    print(f"mode={args.mode} affected={len(affected)} report={REPORT_PATH}")
    for post in affected[:50]:
        print(f"{post['slug']} | {', '.join(post['errors'])}")

    if not args.apply:
        return 0
    if not admin_api_key:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not set")
        return 1

    drafted = 0
    failed = 0
    for post in affected:
        ok = draft_post(str(post["id"]), str(post["updated_at"]), admin_api_key)
        if ok:
            drafted += 1
        else:
            failed += 1
    print(f"drafted={drafted} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
