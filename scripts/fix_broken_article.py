#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix the broken nasa-mars-ai-autonomous-driving JA article.
Rebuild np-tag-badge that was lost during ?source=html conversion."""
import json, sys, datetime, re
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

# Step 1: Get the broken article
print("=== Step 1: Get broken article ===")
r = requests.get(f"{GHOST}/ghost/api/admin/posts/slug/nasa-mars-ai-autonomous-driving/?formats=lexical,html&include=tags",
    headers=hdr(), verify=False)
broken = r.json()["posts"][0]
print(f"Title: {broken['title']}")
print(f"Tags: {[t['name'] for t in broken.get('tags', [])]}")

html = broken.get("html", "") or ""
lex_str = broken.get("lexical", "") or ""
print(f"HTML length: {len(html)}")
print(f"np-tag-badge in HTML: {'np-tag-badge' in html}")
print(f"np-tag-badge in Lexical: {'np-tag-badge' in lex_str}")

# Step 2: Get the EN version to see its tag badge structure
print("\n=== Step 2: Get EN version for reference ===")
# The EN version slug
en_slugs = [
    "nasa-achieves-autonomous-ai-driving-on-mars-the-beginning-of-the-end-for-28-years-of-human-piloting",
    "nasa-achieves-ai-autonomous-driving-on-mars-the-beginning-of-the-end-for-28-years-of-human-piloting",
]
en_post = None
for slug in en_slugs:
    r2 = requests.get(f"{GHOST}/ghost/api/admin/posts/slug/{slug}/?formats=lexical,html",
        headers=hdr(), verify=False)
    data = r2.json()
    if "posts" in data:
        en_post = data["posts"][0]
        print(f"EN article found: {en_post['title'][:60]}")
        break

if en_post:
    en_lex = json.loads(en_post.get("lexical", "{}") or "{}")
    en_nodes = en_lex.get("root", {}).get("children", [])
    # Find np-tag-badge node
    for i, node in enumerate(en_nodes):
        if node.get("type") == "html" and "np-tag-badge" in node.get("html", ""):
            print(f"EN tag badge found at node [{i}]:")
            print(f"  {node['html'][:300]}...")
            break
else:
    print("EN version not found, trying to find any article with np-tag-badge")
    r3 = requests.get(f"{GHOST}/ghost/api/admin/posts/?limit=5&formats=lexical",
        headers=hdr(), verify=False)
    for p in r3.json()["posts"]:
        lex = p.get("lexical", "") or ""
        if "np-tag-badge" in lex:
            lex_json = json.loads(lex)
            for node in lex_json["root"]["children"]:
                if node.get("type") == "html" and "np-tag-badge" in node.get("html", ""):
                    print(f"Reference badge from: {p['title'][:40]}")
                    print(f"  {node['html'][:300]}...")
                    break
            break

# Step 3: Check what tags this article should have (from Ghost tags)
print("\n=== Step 3: Determine correct tags ===")
tags = [t["name"] for t in broken.get("tags", [])]
print(f"Ghost tags: {tags}")

# Based on the article content (NASA Mars AI), the tags should be:
# Genre: Technology, Health & Science
# Event: Tech Breakthrough
# Dynamics: Tech Leapfrog
# This is a JA article about NASA AI autonomous driving on Mars

# Step 4: Build the JA tag badge HTML
print("\n=== Step 4: Build np-tag-badge HTML ===")

tag_badge_html = '''<div class="np-tag-badge" style="margin:20px 0;padding:16px 20px;background:#f8f6f0;border-radius:6px;font-size:0.9em;line-height:2">
<div class="np-tag-row"><strong>\u30b8\u30e3\u30f3\u30eb:</strong> <a href="https://nowpattern.com/tag/technology/" style="color:#c9a84c;text-decoration:none;font-weight:600">#\u30c6\u30af\u30ce\u30ed\u30b8\u30fc</a> <a href="https://nowpattern.com/tag/health-science/" style="color:#c9a84c;text-decoration:none;font-weight:600">#\u5065\u5eb7\u30fb\u79d1\u5b66</a></div>
<div class="np-tag-row"><strong>\u30a4\u30d9\u30f3\u30c8:</strong> <a href="https://nowpattern.com/tag/event-tech-breakthrough/" style="color:#16a34a;text-decoration:none;font-weight:600">#\u6280\u8853\u9032\u5c55</a></div>
<div class="np-tag-row"><strong>\u529b\u5b66:</strong> <a href="https://nowpattern.com/tag/dynamics-tech-leapfrog/" style="color:#FF1A75;text-decoration:none;font-weight:600">#\u5f8c\u767a\u9006\u8ee2</a></div>
</div>'''

print(f"Badge HTML: {len(tag_badge_html)} chars")

# Step 5: Insert into Lexical JSON
print("\n=== Step 5: Insert into Lexical ===")
lex = json.loads(lex_str)
nodes = lex["root"]["children"]
print(f"Current nodes: {len(nodes)}")

# Show current node types
for i, node in enumerate(nodes[:10]):
    ntype = node.get("type", "?")
    if ntype == "html":
        h = node.get("html", "")[:80]
        print(f"  [{i}] html: {h}...")
    else:
        print(f"  [{i}] {ntype}")

# Find where to insert (after np-fast-read, before np-summary)
insert_pos = None
for i, node in enumerate(nodes):
    if node.get("type") == "html":
        h = node.get("html", "")
        if "np-fast-read" in h:
            insert_pos = i + 1
            break
        if "np-summary" in h:
            insert_pos = i
            break

if insert_pos is None:
    # Insert at position 3 (typical position after fast-read)
    insert_pos = min(3, len(nodes))

print(f"Will insert at position: {insert_pos}")

# Check if --apply flag
if "--apply" in sys.argv:
    # Insert the tag badge node
    new_node = {"type": "html", "version": 1, "html": tag_badge_html}
    nodes.insert(insert_pos, new_node)
    lex["root"]["children"] = nodes

    # Get fresh updated_at
    r4 = requests.get(f"{GHOST}/ghost/api/admin/posts/{broken['id']}/?include=tags",
        headers=hdr(), verify=False)
    updated_at = r4.json()["posts"][0]["updated_at"]

    # Update
    payload = {
        "posts": [{
            "lexical": json.dumps(lex),
            "mobiledoc": None,
            "updated_at": updated_at,
        }]
    }
    r5 = requests.put(f"{GHOST}/ghost/api/admin/posts/{broken['id']}/",
        json=payload, headers=hdr(), verify=False)
    if r5.status_code == 200:
        print("OK: np-tag-badge rebuilt successfully")
        # Verify
        r6 = requests.get(f"{GHOST}/ghost/api/admin/posts/{broken['id']}/?formats=html",
            headers=hdr(), verify=False)
        new_html = r6.json()["posts"][0].get("html", "") or ""
        print(f"New HTML length: {len(new_html)}")
        print(f"np-tag-badge in new HTML: {'np-tag-badge' in new_html}")
    else:
        print(f"FAIL: {r5.status_code} {r5.text[:300]}")
else:
    print("\nDry run. Use --apply to actually fix the article.")
