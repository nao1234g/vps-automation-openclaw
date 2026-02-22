#!/usr/bin/env python3
"""Check existing articles for tag badge URLs."""
import os, json, jwt, datetime, requests, urllib3, re
urllib3.disable_warnings()

env = {}
with open("/opt/cron-env.sh") as f:
    for line in f:
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[7:].split("=", 1)
            env[k] = v.strip().strip("\"'")

key = env["NOWPATTERN_GHOST_ADMIN_API_KEY"]
kid, sec = key.split(":")
GHOST_URL = "https://nowpattern.com"

def token():
    iat = int(datetime.datetime.now().timestamp())
    return jwt.encode({"iat": iat, "exp": iat + 300, "aud": "/admin/"},
        bytes.fromhex(sec), algorithm="HS256",
        headers={"alg": "HS256", "typ": "JWT", "kid": kid})

def headers():
    return {"Authorization": f"Ghost {token()}", "Content-Type": "application/json"}

# Get all posts
r = requests.get(f"{GHOST_URL}/ghost/api/admin/posts/?limit=all&formats=html", headers=headers(), verify=False)
posts = r.json()["posts"]
print(f"Total posts: {len(posts)}\n")

has_tag_badges = 0
has_old_slugs = 0

for p in posts:
    html = p.get("html", "") or ""
    # Look for tag badges
    has_genre = "Genre:" in html or "ジャンル:" in html
    has_event = "Event:" in html or "イベント:" in html
    has_dynamics = "Dynamics:" in html or "力学:" in html

    # Find all /tag/ links
    tag_links = re.findall(r'href="/tag/([^/"]+)/"', html)

    if has_genre or has_event or has_dynamics or tag_links:
        has_tag_badges += 1
        print(f"[HAS TAGS] {p['title'][:60]}")
        if tag_links:
            unique_links = sorted(set(tag_links))
            for tl in unique_links:
                # Check if it's an old slug (no prefix) vs new slug (genre-/event-/dynamics-)
                is_new = tl.startswith("genre-") or tl.startswith("event-") or tl.startswith("dynamics-")
                status = "NEW" if is_new else "OLD"
                print(f"  [{status}] /tag/{tl}/")
                if not is_new:
                    has_old_slugs += 1
        else:
            print("  (has tag labels but no links)")
        print()

print(f"\n--- Summary ---")
print(f"Posts with tag badges: {has_tag_badges}/{len(posts)}")
print(f"Old slug URLs found: {has_old_slugs}")
