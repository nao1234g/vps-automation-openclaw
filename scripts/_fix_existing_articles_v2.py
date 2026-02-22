#!/usr/bin/env python3
"""Fix existing Ghost articles using HTML source mode (?source=html)."""

import requests
import jwt
import datetime
import json
import re
import urllib3
import time
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

# Get all posts with HTML format
token = get_token()
headers = {"Authorization": f"Ghost {token}"}
r = requests.get(f"{BASE}/posts/?limit=all&formats=html", headers=headers, verify=False)
posts = r.json().get("posts", [])
print(f"Total posts: {len(posts)}")

fixed_count = 0
for post in posts:
    title = post.get("title", "")
    html = post.get("html", "")
    post_id = post.get("id")
    updated_at = post.get("updated_at")

    if not html:
        print(f"  SKIP (no html): {title[:60]}")
        continue

    original = html
    is_ja = bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', title))

    if is_ja:
        # Section headers: English -> Japanese
        html = re.sub(r'(>)\s*Why it matters:\s*(</?)' , r'\1なぜ重要か:\2', html)
        html = re.sub(r'(>)\s*Why it matters\s*(</?)' , r'\1なぜ重要か\2', html)
        html = re.sub(r'(>)\s*What happened\s*(</?)' , r'\1何が起きたか\2', html)
        html = re.sub(r'(>)\s*The Big Picture\s*(</?)' , r'\1全体像\2', html)
        html = re.sub(r'(>)\s*Pattern History\s*(</?)' , r'\1パターン史\2', html)
        html = re.sub(r"(>)\s*What'?s Next\s*(</?)' ", r'\1今後のシナリオ\2', html)
        # More robust What's Next matching
        html = html.replace(">What's Next<", ">今後のシナリオ<")
        html = html.replace(">What's Next<", ">今後のシナリオ<")  # curly apostrophe
        html = html.replace(">What&#x27;s Next<", ">今後のシナリオ<")
        # Between the Lines
        html = html.replace(">Between the Lines — 行間を読む<", ">行間を読む — 報道が言っていないこと<")
        # Tag: 力学 -> 力学(Nowpattern)
        html = html.replace(">力学:<", ">力学(Nowpattern):<")

    # English articles: tag label
    html = html.replace(">Dynamics:<", ">Dynamics(Nowpattern):<")

    # Fix シナリオシナリオ (all articles)
    html = html.replace("シナリオシナリオ", "シナリオ")

    if html != original:
        token = get_token()
        headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}
        payload = {
            "posts": [{
                "html": html,
                "updated_at": updated_at,
            }]
        }
        r2 = requests.put(
            f"{BASE}/posts/{post_id}/?source=html",
            json=payload,
            headers=headers,
            verify=False
        )
        if r2.status_code == 200:
            fixed_count += 1
            print(f"  FIXED: {title[:60]}")
        else:
            print(f"  ERROR ({r2.status_code}): {title[:60]} - {r2.text[:200]}")
        time.sleep(0.5)
    else:
        print(f"  OK (no changes): {title[:60]}")

print(f"\nDone. Fixed {fixed_count} of {len(posts)} articles.")
