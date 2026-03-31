#!/usr/bin/env python3
"""Audit published Ghost posts for release/distribution readiness."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import ssl
import time
import urllib.request
from collections import Counter
from urllib.parse import urlparse

from content_release_scope import SKIP_SLUGS
from mission_contract import MISSION_CONTRACT_VERSION, mission_contract_hash
from canonical_public_lexicon import LEXICON_VERSION
from release_governor import evaluate_governed_release

GHOST_DB = "/var/www/nowpattern/content/data/ghost.db"
CRON_ENV = "/opt/cron-env.sh"
GHOST_URL = "https://nowpattern.com"
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_REPORT_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "reports")
MANIFEST_PATH = (
    "/opt/shared/reports/article_release_manifest.json"
    if os.path.exists("/opt/shared")
    else os.path.join(_LOCAL_REPORT_DIR, "article_release_manifest.json")
)
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
    token = ghost_jwt(admin_api_key)
    current_updated_at = updated_at
    for attempt in range(3):
        body = json.dumps(
            {"posts": [{"id": post_id, "status": "draft", "updated_at": current_updated_at}]}
        ).encode()
        req = urllib.request.Request(
            f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/",
            data=body,
            method="PUT",
            headers={
                "Authorization": "Ghost " + token,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as resp:
                return resp.status == 200
        except Exception:
            try:
                meta_req = urllib.request.Request(
                    f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/?fields=updated_at",
                    headers={"Authorization": "Ghost " + token},
                )
                with urllib.request.urlopen(meta_req, timeout=20, context=ssl_ctx()) as resp:
                    data = json.loads(resp.read())
                    current_updated_at = data["posts"][0]["updated_at"]
            except Exception:
                pass
            time.sleep(1 + attempt)
    return False


def build_public_url(slug: str, tag_slugs: set[str]) -> str:
    if "lang-en" in tag_slugs and slug.startswith("en-"):
        return f"{GHOST_URL}/en/{slug[3:]}/"
    if "lang-en" in tag_slugs:
        return f"{GHOST_URL}/en/{slug}/"
    return f"{GHOST_URL}/{slug}/"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-source-fetchability", action="store_true")
    parser.add_argument("--apply-draft-truth-failures", action="store_true")
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
        WHERE p.status='published' AND p.type='post'
        GROUP BY p.id, p.slug, p.title, p.html, p.updated_at
        ORDER BY p.published_at DESC
        """
    ).fetchall()
    con.close()

    posts: list[dict[str, object]] = []
    counts = {
        "published_total": 0,
        "public_truth_allowed": 0,
        "distribution_allowed": 0,
        "truth_blocked": 0,
        "distribution_blocked": 0,
        "high_risk_unapproved": 0,
        "drafted_truth_failures": 0,
        "draft_failures": 0,
    }
    lane_counts: Counter[str] = Counter()
    risk_flag_counts: Counter[str] = Counter()
    review_queue_samples: list[dict[str, object]] = []

    for row in rows:
        slug = row["slug"]
        if slug in SKIP_SLUGS:
            continue
        tag_slugs = set((row["tag_slugs"] or "").split())
        release = evaluate_governed_release(
            title=row["title"] or "",
            html=row["html"] or "",
            tags=tag_slugs,
            site_url=GHOST_URL,
            status="published",
            channel="distribution",
            require_external_sources=True,
            check_source_fetchability=args.check_source_fetchability,
        )
        truth_only_errors = [
            err for err in release["errors"] if not err.startswith("HUMAN_APPROVAL_REQUIRED:")
        ]
        public_truth_allowed = not truth_only_errors
        distribution_allowed = not release["errors"]

        entry = {
            "slug": slug,
            "url": build_public_url(slug, tag_slugs),
            "tag_slugs": sorted(tag_slugs),
            "public_truth_allowed": public_truth_allowed,
            "distribution_allowed": distribution_allowed,
            "truth_only_errors": truth_only_errors,
            "release_errors": release["errors"],
            "risk_flags": release["risk_flags"],
            "human_approval_required": release["human_approval_required"],
            "human_approval_present": release["human_approval_present"],
            "release_lane": release["release_lane"],
        }
        posts.append(entry)
        lane_counts[release["release_lane"]] += 1
        risk_flag_counts.update(release["risk_flags"])
        if release["release_lane"] == "human_review_required" and len(review_queue_samples) < 50:
            review_queue_samples.append(
                {
                    "slug": slug,
                    "url": entry["url"],
                    "risk_flags": release["risk_flags"],
                    "release_errors": release["errors"],
                }
            )

        counts["published_total"] += 1
        counts["public_truth_allowed"] += int(public_truth_allowed)
        counts["distribution_allowed"] += int(distribution_allowed)
        counts["truth_blocked"] += int(not public_truth_allowed)
        counts["distribution_blocked"] += int(not distribution_allowed)
        counts["high_risk_unapproved"] += int(
            release["human_approval_required"] and not release["human_approval_present"]
        )

        if args.apply_draft_truth_failures and truth_only_errors:
            if not admin_api_key:
                counts["draft_failures"] += 1
            elif draft_post(str(row["id"]), str(row["updated_at"]), admin_api_key):
                counts["drafted_truth_failures"] += 1
            else:
                counts["draft_failures"] += 1

        if args.limit and len(posts) >= args.limit:
            break

    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "site_host": urlparse(GHOST_URL).netloc,
        "mission_contract_version": MISSION_CONTRACT_VERSION,
        "mission_contract_hash": mission_contract_hash(),
        "lexicon_version": LEXICON_VERSION,
        "check_source_fetchability": args.check_source_fetchability,
        "counts": counts,
        "lane_counts": dict(sorted(lane_counts.items())),
        "risk_flag_counts": dict(sorted(risk_flag_counts.items())),
        "review_queue": {
            "count": lane_counts.get("human_review_required", 0),
            "samples": review_queue_samples,
        },
        "posts": posts,
    }
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"manifest={MANIFEST_PATH}")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
