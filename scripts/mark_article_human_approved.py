#!/usr/bin/env python3
"""Mark a Ghost post as human-approved for high-risk publication/distribution."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import time
import urllib.parse
import urllib.request

APPROVAL_TAGS = ("human-approved", "truth-reviewed")
CRON_ENV = "/opt/cron-env.sh"
GHOST_URL = "https://nowpattern.com"


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


def ghost_request(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Ghost {token}"})
    with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as resp:
        return json.loads(resp.read())


def fetch_post_by_slug(slug: str, token: str) -> dict:
    quoted = urllib.parse.quote(slug, safe="")
    data = ghost_request(
        f"{GHOST_URL}/ghost/api/admin/posts/slug/{quoted}/?include=tags",
        token,
    )
    posts = data.get("posts", [])
    return posts[0] if posts else {}


def fetch_post_by_id(post_id: str, token: str) -> dict:
    data = ghost_request(
        f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/?include=tags",
        token,
    )
    posts = data.get("posts", [])
    return posts[0] if posts else {}


def update_tags(post: dict, token: str) -> bool:
    tag_slugs = {tag.get("slug") for tag in post.get("tags", []) if tag.get("slug")}
    for slug in APPROVAL_TAGS:
        tag_slugs.add(slug)
    body = json.dumps(
        {
            "posts": [
                {
                    "id": post["id"],
                    "updated_at": post["updated_at"],
                    "tags": [{"slug": slug} for slug in sorted(tag_slugs)],
                }
            ]
        }
    ).encode()
    req = urllib.request.Request(
        f"{GHOST_URL}/ghost/api/admin/posts/{post['id']}/",
        data=body,
        method="PUT",
        headers={
            "Authorization": f"Ghost {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as resp:
        return resp.status == 200


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug")
    parser.add_argument("--id")
    args = parser.parse_args()

    if not args.slug and not args.id:
        print("ERROR: pass --slug or --id")
        return 1

    env = load_env()
    admin_api_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not admin_api_key:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not set")
        return 1

    token = ghost_jwt(admin_api_key)
    post = fetch_post_by_slug(args.slug, token) if args.slug else fetch_post_by_id(args.id, token)
    if not post:
        print("ERROR: post not found")
        return 1

    if update_tags(post, token):
        print(f"OK: human-approved tags added to {post.get('slug')}")
        return 0
    print("ERROR: update failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
