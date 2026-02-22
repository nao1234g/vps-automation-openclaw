#!/usr/bin/env python3
"""Check the actual tag badge HTML in existing articles."""
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

# Get 2 posts (1 JA, 1 EN)
r = requests.get(f"{GHOST_URL}/ghost/api/admin/posts/?limit=all&formats=html", headers=headers(), verify=False)
posts = r.json()["posts"]

# Find first JA and first EN
ja_post = None
en_post = None
for p in posts:
    html = p.get("html", "") or ""
    if not ja_post and "ジャンル:" in html:
        ja_post = p
    if not en_post and "Genre:" in html:
        en_post = p
    if ja_post and en_post:
        break

for label, post in [("JA", ja_post), ("EN", en_post)]:
    if not post:
        print(f"{label}: No post found")
        continue
    html = post.get("html", "") or ""
    print(f"=== {label}: {post['title'][:60]} ===")
    # Find the tag badge section (usually near the top)
    # Look for lines containing Genre/Event/Dynamics or ジャンル/イベント/力学
    lines = html.split("\n")
    for i, line in enumerate(lines):
        if any(kw in line for kw in ["Genre:", "Event:", "Dynamics:", "ジャンル:", "イベント:", "力学:"]):
            # Print this line and surrounding context
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            for j in range(start, end):
                print(f"  L{j}: {lines[j][:200]}")
            print()
    print()
