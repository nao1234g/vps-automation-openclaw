#!/usr/bin/env python3
"""Check all Ghost post slugs and find 404 pattern."""
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

r = requests.get(
    "https://nowpattern.com/ghost/api/admin/posts/?limit=all&fields=title,slug,url,status",
    headers={"Authorization": f"Ghost {token}"},
    verify=False
)
posts = r.json().get("posts", [])

broken = []
working = []
for p in posts:
    s = p["slug"]
    u = p["url"]
    is404 = "/404/" in u
    status = "404!" if is404 else "OK"
    print(f"  len={len(s):3d} {status:4s} {s[:90]}")
    if is404:
        broken.append(p)
    else:
        working.append(p)

print(f"\nBroken (404): {len(broken)}")
print(f"Working: {len(working)}")

if broken:
    broken_lens = [len(p["slug"]) for p in broken]
    working_lens = [len(p["slug"]) for p in working]
    print(f"\nBroken slug lengths: min={min(broken_lens)}, max={max(broken_lens)}")
    print(f"Working slug lengths: min={min(working_lens)}, max={max(working_lens)}")

    # Try to fix: update slugs to shorter versions
    print("\n=== Attempting to fix by shortening slugs ===")
    for p in broken:
        old_slug = p["slug"]
        # Shorten to max 100 chars
        new_slug = old_slug[:100].rstrip("-")
        print(f"  {old_slug[:50]}... (len={len(old_slug)}) -> {new_slug[:50]}... (len={len(new_slug)})")
