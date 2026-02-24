#!/usr/bin/env python3
"""Detailed Lexical node inspection for one article."""
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

# Get first article with full lexical
r = requests.get("https://nowpattern.com/ghost/api/admin/posts/?limit=1&formats=lexical,html",
    headers=hdr(), verify=False)
post = r.json()["posts"][0]
print(f"Title: {post['title'][:60]}")

# Check HTML output
html = post.get("html", "") or ""
print(f"\nHTML length: {len(html)}")
print(f"np-pattern-box in HTML: {'np-pattern-box' in html}")

# Show all np-pattern-box occurrences in HTML
for m in re.finditer(r'np-pattern-box', html):
    start = max(0, m.start() - 50)
    end = min(len(html), m.end() + 100)
    print(f"  HTML context: ...{html[start:end]}...")

# Parse Lexical
lex = json.loads(post.get("lexical", "{}") or "{}")
nodes = lex.get("root", {}).get("children", [])
print(f"\nLexical nodes: {len(nodes)}")

# Show ALL html-type nodes (these are the HTML card nodes)
for i, node in enumerate(nodes):
    ntype = node.get("type", "?")
    if ntype == "html":
        h = node.get("html", "")
        print(f"\n  === HTML Node [{i}] ({len(h)} chars) ===")
        print(f"  {h[:300]}")
        if len(h) > 300:
            print(f"  ...({len(h) - 300} more chars)")
