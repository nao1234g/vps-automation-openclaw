#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check primary tag ordering for homepage card display."""
import json, sys, datetime
sys.stdout.reconfigure(encoding="utf-8")
import jwt, requests, urllib3
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

def tok():
    iat = int(datetime.datetime.now().timestamp())
    return jwt.encode({"iat": iat, "exp": iat + 300, "aud": "/admin/"},
        bytes.fromhex(sec), algorithm="HS256",
        headers={"alg": "HS256", "typ": "JWT", "kid": kid})

def hdr():
    return {"Authorization": f"Ghost {tok()}", "Content-Type": "application/json"}

GHOST = "https://nowpattern.com"

# Genre names for checking
GENRES = {
    "Technology", "Geopolitics & Security", "Economy & Trade",
    "Finance & Markets", "Business & Industry", "Crypto & Web3",
    "Energy", "Environment & Climate", "Governance & Law",
    "Society", "Culture, Entertainment & Sports",
    "Media & Information", "Health & Science",
}

r = requests.get(f"{GHOST}/ghost/api/admin/posts/?limit=all&include=tags&fields=id,slug,title",
    headers=hdr(), verify=False)
posts = r.json()["posts"]

print(f"Total posts: {len(posts)}")
print()
print("Primary tag (first tag) for each article:")
print(f"{'Slug':<50} {'Primary Tag':<25} {'Has Genre?'}")
print("-" * 100)

no_genre_primary = []
for p in posts:
    tags = [t["name"] for t in p.get("tags", [])]
    primary = tags[0] if tags else "(none)"
    has_genre = any(t in GENRES for t in tags)
    genre_is_primary = primary in GENRES

    slug = p["slug"][:48]
    marker = "OK" if genre_is_primary else ("NO GENRE PRIMARY" if has_genre else "NO GENRE TAG")
    print(f"  {slug:<50} {primary:<25} {marker}")

    if not genre_is_primary and has_genre:
        no_genre_primary.append({
            "post": p,
            "tags": tags,
            "primary": primary,
        })

print(f"\nArticles with genre tag NOT as primary: {len(no_genre_primary)}")
if no_genre_primary:
    print("\nThese need tag reordering (genre first):")
    for item in no_genre_primary:
        genres = [t for t in item["tags"] if t in GENRES]
        print(f"  {item['post']['slug'][:48]}")
        print(f"    Current: {item['tags'][:5]}")
        print(f"    Genre:   {genres}")
