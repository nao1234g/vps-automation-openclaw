#!/usr/bin/env python3
"""Comprehensive nowpattern.com site audit"""
import json, time, hashlib, hmac, base64, os, subprocess
import urllib3; urllib3.disable_warnings()
import requests
from collections import Counter

with open("/opt/cron-env.sh") as f:
    for line in f:
        if "NOWPATTERN_GHOST_ADMIN_API_KEY" in line:
            key = line.split("=", 1)[1].strip().strip("'").strip('"')
            break

kid, secret = key.split(":")
iat = int(time.time())
def b64url(d): return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
h = b64url(json.dumps({"alg":"HS256","typ":"JWT","kid":kid}).encode())
p = b64url(json.dumps({"iat":iat,"exp":iat+300,"aud":"/admin/"}).encode())
sig = hmac.new(bytes.fromhex(secret), f"{h}.{p}".encode(), hashlib.sha256).digest()
token = f"{h}.{p}.{b64url(sig)}"
hdr = {"Authorization": f"Ghost {token}"}

print("=" * 60)
print("NOWPATTERN.COM — FULL SITE AUDIT")
print("=" * 60)

# --- Posts ---
r = requests.get("https://nowpattern.com/ghost/api/admin/posts/?limit=all&include=tags",
                  headers=hdr, verify=False)
posts = r.json().get("posts", [])
print(f"\n📝 POSTS: {len(posts)} total")

status_count = Counter(p["status"] for p in posts)
for s, c in status_count.items():
    print(f"  {s}: {c}")

ja = [p for p in posts if any(t["slug"] == "lang-ja" for t in p.get("tags", []))]
en = [p for p in posts if any(t["slug"] == "lang-en" for t in p.get("tags", []))]
no_lang = [p for p in posts if not any(t["slug"] in ("lang-ja", "lang-en") for t in p.get("tags", []))]
print(f"  lang-ja: {len(ja)}")
print(f"  lang-en: {len(en)}")
print(f"  no lang tag: {len(no_lang)}")

# Genre distribution
genre_counter = Counter()
event_counter = Counter()
dynamics_counter = Counter()
for p in posts:
    for t in p.get("tags", []):
        slug = t["slug"]
        if slug.startswith("genre-"): genre_counter[t["name"]] += 1
        elif slug.startswith("event-"): event_counter[t["name"]] += 1
        elif slug.startswith("p-"): dynamics_counter[t["name"]] += 1

print(f"\n📊 TAG USAGE:")
print(f"  Genres used: {len(genre_counter)}/13")
for g, c in genre_counter.most_common(13):
    print(f"    {g}: {c}")
print(f"  Events used: {len(event_counter)}/19")
for e, c in event_counter.most_common(19):
    print(f"    {e}: {c}")
print(f"  Dynamics used: {len(dynamics_counter)}/16")
for d, c in dynamics_counter.most_common(16):
    print(f"    {d}: {c}")

# Sample titles
print(f"\n📰 RECENT ARTICLES (last 5):")
for p in posts[:5]:
    tags = ", ".join(t["slug"] for t in p.get("tags", []) if not t["slug"].startswith("lang-"))
    print(f"  [{p['status']}] {p['title'][:60]}")
    print(f"    tags: {tags}")
    print(f"    published: {p.get('published_at', 'N/A')}")

# No-lang posts
if no_lang:
    print(f"\n⚠️ POSTS WITHOUT LANG TAG ({len(no_lang)}):")
    for p in no_lang[:10]:
        print(f"  {p['title'][:50]} [{p['status']}]")

# --- Members ---
r2 = requests.get("https://nowpattern.com/ghost/api/admin/members/?limit=1",
                   headers=hdr, verify=False)
members = r2.json().get("meta", {}).get("pagination", {}).get("total", 0)
print(f"\n👥 MEMBERS: {members}")

# --- Pages ---
r3 = requests.get("https://nowpattern.com/ghost/api/admin/pages/?limit=all&fields=slug,title,status",
                   headers=hdr, verify=False)
pages = r3.json().get("pages", [])
print(f"\n📄 PAGES: {len(pages)}")
for pg in pages:
    print(f"  {pg['slug']} ({pg['status']}): {pg['title']}")

# --- Tags ---
r4 = requests.get("https://nowpattern.com/ghost/api/admin/tags/?limit=all&fields=slug,name,count&include=count.posts",
                   headers=hdr, verify=False)
tags = r4.json().get("tags", [])
used = [t for t in tags if t.get("count", {}).get("posts", 0) > 0]
unused = [t for t in tags if t.get("count", {}).get("posts", 0) == 0]
print(f"\n🏷️ TAGS: {len(tags)} total, {len(used)} with posts, {len(unused)} unused")

# --- Cron ---
print(f"\n⏰ CRONTAB (nowpattern related):")
result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
for line in result.stdout.split("\n"):
    if "nowpattern" in line.lower() or "ghost" in line.lower():
        print(f"  {line.strip()}")

# --- Ghost config ---
print(f"\n⚙️ GHOST STATUS:")
result = subprocess.run(["systemctl", "is-active", "ghost-nowpattern"], capture_output=True, text=True)
print(f"  Service: {result.stdout.strip()}")

# --- Disk usage ---
result = subprocess.run(["du", "-sh", "/var/www/nowpattern/"], capture_output=True, text=True)
print(f"  Disk: {result.stdout.strip()}")

# --- routes.yaml ---
print(f"\n🔀 ROUTES.YAML:")
with open("/var/www/nowpattern/content/settings/routes.yaml") as f:
    print(f.read())

print("\n" + "=" * 60)
print("AUDIT COMPLETE")
