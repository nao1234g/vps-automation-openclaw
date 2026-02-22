#!/usr/bin/env python3
"""Diagnose and fix Ghost 404 articles."""
import requests, jwt, datetime, urllib3, json, time
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

# Get all posts
token = get_token()
headers = {"Authorization": f"Ghost {token}"}
r = requests.get(f"{BASE}/posts/?limit=all&fields=id,title,slug,url,status,updated_at&formats=html", headers=headers, verify=False)
posts = r.json().get("posts", [])

broken = [p for p in posts if "/404/" in p.get("url", "")]
print(f"Found {len(broken)} broken (404) articles\n")

for p in broken:
    post_id = p["id"]
    old_slug = p["slug"]
    title = p["title"]
    updated_at = p["updated_at"]
    html = p.get("html", "")

    print(f"=== Fixing: {title[:70]}")
    print(f"  old slug: {old_slug} (len={len(old_slug)})")

    # Try 1: Just re-save the post with same slug (triggers Ghost to rebuild routes)
    token = get_token()
    headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}
    payload = {
        "posts": [{
            "slug": old_slug,
            "updated_at": updated_at,
        }]
    }
    r2 = requests.put(f"{BASE}/posts/{post_id}/", json=payload, headers=headers, verify=False)
    if r2.status_code == 200:
        new_url = r2.json().get("posts", [{}])[0].get("url", "")
        new_slug = r2.json().get("posts", [{}])[0].get("slug", "")
        print(f"  re-saved: url={new_url}")

        # Test URL
        test = requests.get(new_url, verify=False, timeout=5, allow_redirects=True)
        print(f"  HTTP test: {test.status_code}")

        if test.status_code == 404:
            # Try 2: Create a shorter slug
            short_slug = old_slug[:80].rstrip("-")
            print(f"  Trying shorter slug: {short_slug} (len={len(short_slug)})")

            updated_at2 = r2.json().get("posts", [{}])[0].get("updated_at", "")
            token = get_token()
            headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}
            payload2 = {
                "posts": [{
                    "slug": short_slug,
                    "updated_at": updated_at2,
                }]
            }
            r3 = requests.put(f"{BASE}/posts/{post_id}/", json=payload2, headers=headers, verify=False)
            if r3.status_code == 200:
                new_url2 = r3.json().get("posts", [{}])[0].get("url", "")
                test2 = requests.get(new_url2, verify=False, timeout=5, allow_redirects=True)
                print(f"  new url: {new_url2} -> HTTP {test2.status_code}")
            else:
                print(f"  ERROR: {r3.status_code} {r3.text[:200]}")
    else:
        print(f"  ERROR: {r2.status_code} {r2.text[:200]}")

    time.sleep(1)
    print()
