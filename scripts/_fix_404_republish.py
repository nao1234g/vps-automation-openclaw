#!/usr/bin/env python3
"""Fix 404 articles by unpublishing and republishing."""
import requests, jwt, datetime, urllib3, time
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

# Get broken posts
token = get_token()
r = requests.get(f"{BASE}/posts/?limit=all&fields=id,title,slug,url,status,updated_at",
                 headers={"Authorization": f"Ghost {token}"}, verify=False)
posts = r.json().get("posts", [])
broken = [p for p in posts if "/404/" in p.get("url", "")]
print(f"Found {len(broken)} broken articles\n")

for p in broken:
    post_id = p["id"]
    title = p["title"][:70]
    updated_at = p["updated_at"]
    slug = p["slug"]

    print(f"Fixing: {title}")

    # Step 1: Unpublish (draft)
    token = get_token()
    headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}
    r1 = requests.put(f"{BASE}/posts/{post_id}/",
                      json={"posts": [{"status": "draft", "updated_at": updated_at}]},
                      headers=headers, verify=False)
    if r1.status_code != 200:
        print(f"  ERROR unpublish: {r1.status_code} {r1.text[:100]}")
        continue
    updated_at = r1.json()["posts"][0]["updated_at"]
    print(f"  -> draft OK")
    time.sleep(2)

    # Step 2: Republish
    token = get_token()
    headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}
    r2 = requests.put(f"{BASE}/posts/{post_id}/",
                      json={"posts": [{"status": "published", "updated_at": updated_at}]},
                      headers=headers, verify=False)
    if r2.status_code != 200:
        print(f"  ERROR republish: {r2.status_code} {r2.text[:100]}")
        continue
    new_url = r2.json()["posts"][0].get("url", "")
    new_slug = r2.json()["posts"][0].get("slug", "")
    print(f"  -> published OK: {new_url}")

    # Step 3: Test
    time.sleep(2)
    test = requests.get(new_url, verify=False, timeout=5, allow_redirects=True)
    print(f"  -> HTTP test: {test.status_code}")
    print()
