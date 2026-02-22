#!/usr/bin/env python3
"""Recreate 404 articles: delete broken ones and create fresh copies."""
import requests, jwt, datetime, urllib3, time, json
urllib3.disable_warnings()

with open("/opt/cron-env.sh") as f:
    for line in f:
        if "NOWPATTERN_GHOST_ADMIN_API_KEY" in line:
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

kid, secret = key.split(":")

def get_token():
    iat = int(datetime.datetime.now().timestamp())
    header = {"alg": "HS256", "typ": "JWT", "kid": kid}
    payload = {"iat": iat, "exp": iat + 300, "aud": "/admin/"}
    return jwt.encode(payload, bytes.fromhex(secret), algorithm="HS256", headers=header)

BASE = "https://nowpattern.com/ghost/api/admin"

# Get broken posts (full data)
token = get_token()
r = requests.get(f"{BASE}/posts/?limit=all&formats=html",
                 headers={"Authorization": f"Ghost {token}"}, verify=False)
posts = r.json().get("posts", [])
broken = [p for p in posts if "/404/" in p.get("url", "")]
print(f"Found {len(broken)} broken articles to recreate\n")

for p in broken:
    post_id = p["id"]
    title = p["title"]
    html = p.get("html", "")
    tags = p.get("tags", [])
    slug = p.get("slug", "")

    # Use a cleaner, shorter slug
    # Take first 70 chars of slug
    new_slug = slug[:70].rstrip("-")
    print(f"Recreating: {title[:70]}")
    print(f"  old slug: {slug[:60]}... (len={len(slug)})")
    print(f"  new slug: {new_slug} (len={len(new_slug)})")

    # Step 1: Delete the broken post
    token = get_token()
    headers = {"Authorization": f"Ghost {token}"}
    rd = requests.delete(f"{BASE}/posts/{post_id}/", headers=headers, verify=False)
    if rd.status_code == 204:
        print(f"  deleted OK")
    else:
        print(f"  delete ERROR: {rd.status_code} {rd.text[:100]}")
        continue

    time.sleep(2)

    # Step 2: Create new post with same content
    token = get_token()
    headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}

    tag_names = [{"name": t["name"]} for t in tags] if tags else []

    new_post = {
        "posts": [{
            "title": title,
            "html": html,
            "slug": new_slug,
            "status": "published",
            "tags": tag_names,
        }]
    }

    rc = requests.post(f"{BASE}/posts/?source=html",
                       json=new_post, headers=headers, verify=False)
    if rc.status_code == 201:
        new_url = rc.json()["posts"][0].get("url", "")
        new_slug_actual = rc.json()["posts"][0].get("slug", "")
        print(f"  created OK: {new_url}")
        print(f"  actual slug: {new_slug_actual}")

        time.sleep(2)
        test = requests.get(new_url, verify=False, timeout=5, allow_redirects=True)
        print(f"  HTTP test: {test.status_code}")
    else:
        print(f"  create ERROR: {rc.status_code} {rc.text[:200]}")
    print()
