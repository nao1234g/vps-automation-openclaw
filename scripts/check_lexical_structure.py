#!/usr/bin/env python3
"""Check Lexical structure of Nowpattern articles for tag duplicate analysis."""
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
    return {"Authorization": f"Ghost {tok()}"}

# Get first 10 posts and check Lexical structure
r = requests.get("https://nowpattern.com/ghost/api/admin/posts/?limit=10&formats=lexical,html", headers=hdr(), verify=False)
all_posts = r.json().get("posts", [])
print(f"Posts fetched: {len(all_posts)}")

for p in all_posts:
    lex_str = p.get("lexical", "") or ""
    has_pb = "np-pattern-box" in lex_str
    html = p.get("html", "") or ""
    dup_count = len(re.findall(r'border-bottom.*?1px solid #e0dcd4', html))
    print(f"  {p['slug'][:50]:50s}  pb={has_pb}  dups={dup_count}  {p['title'][:35]}")

# Find first article with np-pattern-box in Lexical for detailed inspection
target = None
for p in all_posts:
    if "np-pattern-box" in (p.get("lexical", "") or ""):
        target = p
        break

if target:
    lex = json.loads(target.get("lexical", "{}") or "{}")
    nodes = lex.get("root", {}).get("children", [])
    html = target.get("html", "") or ""
    print(f"\n=== DETAILED: {target['title'][:50]} ===")
    print(f"Nodes: {len(nodes)}, HTML: {len(html)} chars")

    for i, node in enumerate(nodes):
        if node.get("type") == "html":
            h = node.get("html", "")
            keywords = ["np-pattern-box", "border-bottom", "Genre", "Event", "Dynamics",
                        "\u30b8\u30e3\u30f3\u30eb", "\u30a4\u30d9\u30f3\u30c8", "\u529b\u5b66"]
            if any(kw in h for kw in keywords):
                label = "PATTERN-BOX" if "np-pattern-box" in h else "DUPLICATE" if "border-bottom" in h else "TAG"
                print(f"  Node[{i}] html ({len(h)}ch) [{label}]: {h[:150]}...")
else:
    print("\nNo article with np-pattern-box found in first 10 posts!")

# Check the broken article
print(f"\n=== BROKEN: nasa-mars-ai-autonomous-driving ===")
r = requests.get("https://nowpattern.com/ghost/api/admin/posts/slug/nasa-mars-ai-autonomous-driving/?formats=lexical", headers=hdr(), verify=False)
post = r.json()["posts"][0]
lex_str = post.get("lexical", "{}") or "{}"
print(f"np-pattern-box in Lexical: {'np-pattern-box' in lex_str}")
