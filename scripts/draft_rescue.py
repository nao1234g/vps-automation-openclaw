#!/usr/bin/env python3
"""
draft_rescue.py — Ghost CMS Draft Rescue Script

Analyzes and fixes draft articles that are mislabeled or stuck.

Usage:
  python3 draft_rescue.py --analyze              # Full analysis report
  python3 draft_rescue.py --dry-run              # Show what would be fixed (no changes)
  python3 draft_rescue.py --fix-tags --limit 10  # Fix lang tags for first 10 mislabeled
  python3 draft_rescue.py --publish --limit 10   # Publish first 10 ready drafts

Categories:
  MISLABELED  = English content with lang-ja tag (needs tag fix + slug fix)
  EN_READY    = English draft with correct lang-en tag (needs quality check)
  JA_READY    = Japanese draft with correct lang-ja tag (needs quality check)
  NO_LANG     = Missing language tag entirely

Safety:
  - --dry-run shows changes without executing
  - --limit caps the number of posts modified per run
  - All changes are logged to /opt/shared/logs/draft_rescue.log
  - No destructive operations (only tag updates, slug renames, status changes)

Created: 2026-03-25 (Night Mode Track B)
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

LOG_FILE = "/opt/shared/logs/draft_rescue.log"
CRON_ENV = "/opt/cron-env.sh"


def load_env():
    """Load environment from cron-env.sh"""
    env = {}
    try:
        for line in open(CRON_ENV):
            if line.startswith("export "):
                k, _, v = line[7:].strip().partition("=")
                env[k] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        print(f"[ERROR] {CRON_ENV} not found", file=sys.stderr)
        sys.exit(2)
    return env


def ghost_jwt(admin_key):
    """Generate Ghost Admin API JWT token"""
    kid, secret = admin_key.split(":")
    iat = int(time.time())
    header = json.dumps({"alg": "HS256", "typ": "JWT", "kid": kid}).encode()
    payload = json.dumps({"iat": iat, "exp": iat + 300, "aud": "/admin/"}).encode()

    def b64url(data):
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    h = b64url(header)
    p = b64url(payload)
    sig = hmac.new(bytes.fromhex(secret), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{b64url(sig)}"


def ghost_api(url, token, method="GET", data=None):
    """Make Ghost Admin API request"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "Authorization": f"Ghost {token}",
        "Content-Type": "application/json",
    }

    if data:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(resp.read())


def log(msg):
    """Log to file and stdout"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def has_japanese(text):
    """Check if text contains Japanese characters"""
    return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text or ""))


# ─────────────────────────────────────────────
# Fetch all drafts
# ─────────────────────────────────────────────

def fetch_all_drafts(ghost_url, token, include_html=False):
    """Fetch all draft posts with tags"""
    all_drafts = []
    page = 1
    formats = "&formats=html" if include_html else ""
    while True:
        url = (
            f"{ghost_url}/ghost/api/admin/posts/"
            f"?status=draft&limit=100&page={page}&include=tags"
            f"&fields=id,slug,title,status,created_at,updated_at{formats}"
        )
        try:
            data = ghost_api(url, token)
            posts = data.get("posts", [])
            if not posts:
                break
            all_drafts.extend(posts)
            meta = data.get("meta", {}).get("pagination", {})
            if page >= meta.get("pages", 1):
                break
            page += 1
        except Exception as e:
            log(f"[ERROR] Fetch page {page}: {e}")
            break
    return all_drafts


# ─────────────────────────────────────────────
# Classify drafts
# ─────────────────────────────────────────────

def classify_drafts(drafts):
    """Classify drafts into categories"""
    categories = {
        "mislabeled": [],     # EN content with lang-ja tag
        "en_ready": [],       # EN content with lang-en tag
        "ja_ready": [],       # JA content with lang-ja tag
        "no_lang": [],        # Missing language tag
    }

    for d in drafts:
        tags = {t.get("slug", ""): t for t in d.get("tags", [])}
        tag_slugs = set(tags.keys())
        slug = d.get("slug", "")
        title = d.get("title", "") or ""
        html = d.get("html", "") or ""
        content_sample = title + " " + html[:500]

        has_ja_tag = "lang-ja" in tag_slugs
        has_en_tag = "lang-en" in tag_slugs
        content_is_jp = has_japanese(content_sample)

        if not has_ja_tag and not has_en_tag:
            categories["no_lang"].append(d)
        elif has_ja_tag and not content_is_jp:
            categories["mislabeled"].append(d)
        elif has_en_tag:
            categories["en_ready"].append(d)
        elif has_ja_tag and content_is_jp:
            categories["ja_ready"].append(d)
        else:
            categories["no_lang"].append(d)

    return categories


# ─────────────────────────────────────────────
# Analyze command
# ─────────────────────────────────────────────

def cmd_analyze(ghost_url, token):
    """Full analysis report"""
    log("=== Draft Rescue Analysis ===")
    drafts = fetch_all_drafts(ghost_url, token)
    log(f"Total drafts fetched: {len(drafts)}")

    cats = classify_drafts(drafts)

    log(f"\n--- Classification ---")
    log(f"  MISLABELED (EN content + lang-ja): {len(cats['mislabeled'])}")
    log(f"  EN_READY   (EN content + lang-en): {len(cats['en_ready'])}")
    log(f"  JA_READY   (JA content + lang-ja): {len(cats['ja_ready'])}")
    log(f"  NO_LANG    (missing lang tag):      {len(cats['no_lang'])}")

    # Tag composition of mislabeled
    if cats["mislabeled"]:
        log(f"\n--- Mislabeled Sample (first 10) ---")
        for d in cats["mislabeled"][:10]:
            tags = [t.get("slug", "") for t in d.get("tags", [])]
            has_genre = any(t.startswith("genre-") for t in tags)
            has_event = any(t.startswith("event-") for t in tags)
            has_pattern = any(t.startswith("p-") for t in tags)
            log(f"  [{d['slug'][:45]}]")
            log(f"    title: {(d.get('title','') or '')[:60]}")
            log(f"    genre: {'Y' if has_genre else 'N'} | event: {'Y' if has_event else 'N'} | pattern: {'Y' if has_pattern else 'N'}")

    # Duplicate slug check
    slugs = [d["slug"] for d in drafts]
    dupes = {s: slugs.count(s) for s in set(slugs) if slugs.count(s) > 1}
    if dupes:
        log(f"\n--- Duplicate Slugs: {len(dupes)} ---")
        for s, c in sorted(dupes.items(), key=lambda x: -x[1])[:10]:
            log(f"  {s}: {c} copies")

    # Summary
    total_fixable = len(cats["mislabeled"])
    total_publishable = len(cats["en_ready"]) + len(cats["ja_ready"])
    log(f"\n--- Summary ---")
    log(f"  Fixable (tag + slug repair): {total_fixable}")
    log(f"  Potentially publishable (already correct tags): {total_publishable}")
    log(f"  Total rescue candidates: {total_fixable + total_publishable}")

    return cats


# ─────────────────────────────────────────────
# Dry-run command
# ─────────────────────────────────────────────

def cmd_dry_run(ghost_url, token, limit=10):
    """Show what would be fixed without making changes"""
    log(f"=== Dry Run (limit={limit}) ===")
    drafts = fetch_all_drafts(ghost_url, token)
    cats = classify_drafts(drafts)

    mislabeled = cats["mislabeled"][:limit]
    log(f"\nWould fix {len(mislabeled)} mislabeled articles:")

    for i, d in enumerate(mislabeled, 1):
        old_slug = d["slug"]
        new_slug = f"en-{old_slug}" if not old_slug.startswith("en-") else old_slug
        tags = [t.get("slug", "") for t in d.get("tags", [])]

        log(f"\n  [{i}] {(d.get('title','') or '')[:60]}")
        log(f"    slug: {old_slug} -> {new_slug}")
        log(f"    tag change: lang-ja -> lang-en")
        log(f"    existing tags: {', '.join(tags[:5])}...")

    log(f"\n--- Dry Run Complete ---")
    log(f"  Would fix: {len(mislabeled)} articles")
    log(f"  Remaining mislabeled: {len(cats['mislabeled']) - len(mislabeled)}")
    return mislabeled


# ─────────────────────────────────────────────
# Fix tags command
# ─────────────────────────────────────────────

def cmd_fix_tags(ghost_url, token, limit=10, dry_run=False):
    """Fix mislabeled articles: lang-ja -> lang-en + slug prefix"""
    log(f"=== Fix Tags (limit={limit}, dry_run={dry_run}) ===")
    drafts = fetch_all_drafts(ghost_url, token)
    cats = classify_drafts(drafts)

    mislabeled = cats["mislabeled"][:limit]
    fixed = 0
    errors = 0

    for i, d in enumerate(mislabeled, 1):
        post_id = d["id"]
        old_slug = d["slug"]
        new_slug = f"en-{old_slug}" if not old_slug.startswith("en-") else old_slug
        title = (d.get("title", "") or "")[:60]

        # Build new tag list: replace lang-ja with lang-en
        new_tags = []
        for t in d.get("tags", []):
            if t.get("slug") == "lang-ja":
                new_tags.append({"slug": "lang-en", "name": "English"})
            else:
                new_tags.append({"slug": t.get("slug", ""), "name": t.get("name", "")})

        # Add lang-en if not present
        if not any(t.get("slug") == "lang-en" for t in new_tags):
            new_tags.append({"slug": "lang-en", "name": "English"})

        if dry_run:
            log(f"  [{i}/{len(mislabeled)}] DRY-RUN: {title}")
            log(f"    slug: {old_slug} -> {new_slug}")
            fixed += 1
            continue

        # Get current post with updated_at for collision detection
        try:
            url = f"{ghost_url}/ghost/api/admin/posts/{post_id}/"
            current = ghost_api(url, token)
            updated_at = current["posts"][0]["updated_at"]

            # Update via Ghost Admin API
            update_data = {
                "posts": [{
                    "slug": new_slug,
                    "tags": new_tags,
                    "updated_at": updated_at,
                }]
            }
            result = ghost_api(
                f"{ghost_url}/ghost/api/admin/posts/{post_id}/",
                token, method="PUT", data=update_data
            )
            log(f"  [{i}/{len(mislabeled)}] FIXED: {title}")
            log(f"    slug: {old_slug} -> {result['posts'][0]['slug']}")
            fixed += 1
            time.sleep(0.5)  # Rate limit protection
        except Exception as e:
            log(f"  [{i}/{len(mislabeled)}] ERROR: {title} — {e}")
            errors += 1

    log(f"\n--- Fix Tags Complete ---")
    log(f"  Fixed: {fixed}")
    log(f"  Errors: {errors}")
    log(f"  Remaining mislabeled: {len(cats['mislabeled']) - len(mislabeled)}")
    return fixed, errors


# ─────────────────────────────────────────────
# Publish command
# ─────────────────────────────────────────────

def cmd_publish(ghost_url, token, limit=10, category="en_ready", dry_run=False):
    """Publish ready drafts"""
    log(f"=== Publish (limit={limit}, category={category}, dry_run={dry_run}) ===")
    drafts = fetch_all_drafts(ghost_url, token)
    cats = classify_drafts(drafts)

    if category not in cats:
        log(f"[ERROR] Unknown category: {category}")
        return 0, 0

    candidates = cats[category][:limit]
    published = 0
    errors = 0

    for i, d in enumerate(candidates, 1):
        post_id = d["id"]
        title = (d.get("title", "") or "")[:60]

        if dry_run:
            log(f"  [{i}/{len(candidates)}] DRY-RUN PUBLISH: {title}")
            published += 1
            continue

        try:
            # Get current post
            url = f"{ghost_url}/ghost/api/admin/posts/{post_id}/"
            current = ghost_api(url, token)
            updated_at = current["posts"][0]["updated_at"]

            # Publish
            update_data = {
                "posts": [{
                    "status": "published",
                    "updated_at": updated_at,
                }]
            }
            result = ghost_api(
                f"{ghost_url}/ghost/api/admin/posts/{post_id}/",
                token, method="PUT", data=update_data
            )
            log(f"  [{i}/{len(candidates)}] PUBLISHED: {title}")
            published += 1
            time.sleep(1)  # Rate limit protection
        except Exception as e:
            log(f"  [{i}/{len(candidates)}] ERROR: {title} — {e}")
            errors += 1

    log(f"\n--- Publish Complete ---")
    log(f"  Published: {published}")
    log(f"  Errors: {errors}")
    return published, errors


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ghost CMS Draft Rescue Script")
    parser.add_argument("--analyze", action="store_true", help="Full analysis report")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fixed")
    parser.add_argument("--fix-tags", action="store_true", help="Fix mislabeled lang tags + slugs")
    parser.add_argument("--publish", action="store_true", help="Publish ready drafts")
    parser.add_argument("--limit", type=int, default=10, help="Max posts to process (default: 10)")
    parser.add_argument("--category", type=str, default="en_ready",
                        help="Category to publish: en_ready, ja_ready, mislabeled")
    args = parser.parse_args()

    env = load_env()
    ghost_url = env.get("NOWPATTERN_GHOST_URL", "")
    admin_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")

    if not ghost_url or not admin_key:
        print("[ERROR] Missing NOWPATTERN_GHOST_URL or NOWPATTERN_GHOST_ADMIN_API_KEY")
        sys.exit(2)

    token = ghost_jwt(admin_key)

    if args.analyze:
        cmd_analyze(ghost_url, token)
    elif args.dry_run:
        cmd_dry_run(ghost_url, token, limit=args.limit)
    elif args.fix_tags:
        cmd_fix_tags(ghost_url, token, limit=args.limit)
    elif args.publish:
        cmd_publish(ghost_url, token, limit=args.limit, category=args.category)
    else:
        # Default: analyze
        cmd_analyze(ghost_url, token)


if __name__ == "__main__":
    main()
