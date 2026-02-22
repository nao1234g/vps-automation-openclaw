#!/usr/bin/env python3
"""Fix tag badge URLs in all existing Nowpattern articles.
Extract tag names from badge text, look up correct taxonomy slug, replace URLs.
"""
import os, sys, json, jwt, datetime, time, re, requests, urllib3
urllib3.disable_warnings()

GHOST_URL = "https://nowpattern.com"

env = {}
with open("/opt/cron-env.sh") as f:
    for line in f:
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[7:].split("=", 1)
            env[k] = v.strip().strip("\"'")

key = env["NOWPATTERN_GHOST_ADMIN_API_KEY"]
kid, sec = key.split(":")

def token():
    iat = int(datetime.datetime.now().timestamp())
    return jwt.encode({"iat": iat, "exp": iat + 300, "aud": "/admin/"},
        bytes.fromhex(sec), algorithm="HS256",
        headers={"alg": "HS256", "typ": "JWT", "kid": kid})

def headers():
    return {"Authorization": f"Ghost {token()}", "Content-Type": "application/json"}

# Load taxonomy for slug resolution
TAX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nowpattern_taxonomy.json")
with open(TAX_PATH, encoding="utf-8") as f:
    TAX = json.load(f)

# Build tag name → new slug mapping (both JA and EN names)
NAME_TO_SLUG = {}
for g in TAX["genres"]:
    NAME_TO_SLUG[g["name_ja"]] = g["slug"]
    NAME_TO_SLUG[g["name_en"]] = g["slug"]
for e in TAX["events"]:
    NAME_TO_SLUG[e["name_ja"]] = e["slug"]
    NAME_TO_SLUG[e["name_en"]] = e["slug"]
for d in TAX["dynamics"]:
    NAME_TO_SLUG[d["name_ja"]] = d["slug"]
    NAME_TO_SLUG[d["name_en"]] = d["slug"]

print(f"Taxonomy lookup: {len(NAME_TO_SLUG)} name→slug entries")

# Get all posts
r = requests.get(f"{GHOST_URL}/ghost/api/admin/posts/?limit=all&formats=html", headers=headers(), verify=False)
posts = r.json()["posts"]
print(f"Total posts: {len(posts)}\n")


def fix_tag_badges(html):
    """Find tag badge <a> elements, extract display name, replace URL with correct slug."""
    if not html:
        return html, 0

    changes = 0

    # Pattern: <a href="...tag/OLD_SLUG/" style="...">#{TAG_NAME}</a>
    # or: <a href="...tag/OLD_SLUG/" style="...">#TAG_NAME</a>
    def replace_badge_link(match):
        nonlocal changes
        full_match = match.group(0)
        prefix = match.group(1)  # "https://nowpattern.com" or ""
        old_slug = match.group(2)
        rest = match.group(3)  # style and other attributes
        tag_name = match.group(4)  # display name (after #)

        # Look up correct slug from display name
        new_slug = NAME_TO_SLUG.get(tag_name)
        if not new_slug:
            # Try without stripping
            return full_match

        # Check if slug is already correct
        if old_slug == new_slug:
            return full_match

        changes += 1
        return f'<a href="{prefix}/tag/{new_slug}/"{rest}>#{tag_name}</a>'

    # Match tag badge links: <a href="URL/tag/SLUG/" ATTRS>#NAME</a>
    html = re.sub(
        r'<a href="(https://nowpattern\.com)?/tag/([^/"]+)/"([^>]*)>#([^<]+)</a>',
        replace_badge_link,
        html
    )

    return html, changes


# Process each post
success = 0
skipped = 0
failed = 0

DRY_RUN = "--dry-run" in sys.argv
VERBOSE = "--verbose" in sys.argv or DRY_RUN

for post in posts:
    html = post.get("html", "") or ""
    title = post["title"][:55]

    fixed_html, num_changes = fix_tag_badges(html)

    if num_changes == 0:
        if VERBOSE:
            # Check if there are any tag links at all
            tag_links = re.findall(r'href="[^"]*?/tag/([^/"]+)/"', html)
            if tag_links:
                print(f"[SKIP] {title}: {len(tag_links)} tag links already correct")
            else:
                print(f"[SKIP] {title}: no tag links found")
        skipped += 1
        continue

    if DRY_RUN:
        print(f"[DRY] {title}: {num_changes} URL fixes needed")
        # Show details
        old_links = re.findall(r'href="[^"]*?/tag/([^/"]+)/"[^>]*>#([^<]+)', html)
        new_links = re.findall(r'href="[^"]*?/tag/([^/"]+)/"[^>]*>#([^<]+)', fixed_html)
        for (old_slug, name), (new_slug, _) in zip(old_links, new_links):
            if old_slug != new_slug:
                print(f"  #{name}: {old_slug} -> {new_slug}")
        success += 1
        continue

    # Get fresh post data for updated_at
    r = requests.get(f"{GHOST_URL}/ghost/api/admin/posts/{post['id']}/", headers=headers(), verify=False)
    if r.status_code != 200:
        print(f"FAIL: Cannot get {title}: {r.status_code}")
        failed += 1
        continue

    updated_at = r.json()["posts"][0]["updated_at"]

    # Update the post with fixed HTML
    payload = {"posts": [{"html": fixed_html, "updated_at": updated_at}]}
    r = requests.put(
        f"{GHOST_URL}/ghost/api/admin/posts/{post['id']}/?source=html",
        json=payload, headers=headers(), verify=False
    )

    if r.status_code == 200:
        print(f"OK: {title} ({num_changes} URLs fixed)")
        success += 1
    else:
        print(f"FAIL: {title} {r.status_code} {r.text[:200]}")
        failed += 1

    time.sleep(0.3)

print(f"\nDone: {success} updated, {skipped} skipped, {failed} failed")
