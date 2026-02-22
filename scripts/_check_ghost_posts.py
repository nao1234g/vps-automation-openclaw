#!/usr/bin/env python3
"""Check Ghost posts and test their URLs."""
import requests, jwt, datetime, urllib3
urllib3.disable_warnings()

with open("/opt/cron-env.sh") as f:
    for line in f:
        if "NOWPATTERN_GHOST_ADMIN_API_KEY" in line:
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

kid, secret = key.split(":")
iat = int(datetime.datetime.now().timestamp())
header = {"alg": "HS256", "typ": "JWT", "kid": kid}
payload = {"iat": iat, "exp": iat + 300, "aud": "/admin/"}
token = jwt.encode(payload, bytes.fromhex(secret), algorithm="HS256", headers=header)

BASE = "https://nowpattern.com/ghost/api/admin"
r = requests.get(
    f"{BASE}/posts/?limit=10&order=published_at%20desc&fields=id,title,slug,status,url,published_at",
    headers={"Authorization": f"Ghost {token}"},
    verify=False
)
posts = r.json().get("posts", [])
print(f"Latest {len(posts)} posts:")
for p in posts:
    slug = p.get("slug", "")
    url = p.get("url", "")
    st = p.get("status", "")
    title = p.get("title", "")[:80]

    # Test if URL returns 200
    try:
        resp = requests.get(url, verify=False, timeout=5, allow_redirects=True)
        code = resp.status_code
    except Exception as e:
        code = f"ERR: {e}"

    print(f"  [{st}] HTTP {code} | {url}")
    print(f"         title: {title}")
    print(f"         slug: {slug}")
    print()
