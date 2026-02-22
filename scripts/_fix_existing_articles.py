#!/usr/bin/env python3
"""Fix existing Ghost articles: English headers -> Japanese, シナリオシナリオ bug, tag labels."""

import requests
import jwt
import datetime
import json
import re
import urllib3
import time
urllib3.disable_warnings()

# Load Ghost API key
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

# Get all posts
token = get_token()
headers = {"Authorization": f"Ghost {token}"}
r = requests.get(f"{BASE}/posts/?limit=all&formats=lexical", headers=headers, verify=False)
posts = r.json().get("posts", [])
print(f"Total posts: {len(posts)}")

fixed_count = 0
for post in posts:
    title = post.get("title", "")
    lexical = post.get("lexical", "")
    lang = post.get("custom_excerpt", "")  # Not reliable for language detection
    post_id = post.get("id")
    updated_at = post.get("updated_at")

    if not lexical:
        continue

    original = lexical

    # Detect language from title (Japanese characters = ja)
    is_ja = bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', title))

    if is_ja:
        # Fix English section headers -> Japanese (in lexical JSON)
        lexical = lexical.replace(">Why it matters:<", ">なぜ重要か:<")
        lexical = lexical.replace(">Why it matters:</", ">なぜ重要か:</")
        lexical = lexical.replace(">What happened<", ">何が起きたか<")
        lexical = lexical.replace(">What happened</", ">何が起きたか</")
        lexical = lexical.replace(">The Big Picture<", ">全体像<")
        lexical = lexical.replace(">The Big Picture</", ">全体像</")
        lexical = lexical.replace(">Pattern History<", ">パターン史<")
        lexical = lexical.replace(">Pattern History</", ">パターン史</")
        lexical = lexical.replace(">What's Next<", ">今後のシナリオ<")
        lexical = lexical.replace(">What's Next</", ">今後のシナリオ</")
        lexical = lexical.replace(">What\\'s Next<", ">今後のシナリオ<")
        lexical = lexical.replace(">What\\'s Next</", ">今後のシナリオ</")
        # Between the Lines
        lexical = lexical.replace(">Between the Lines — 行間を読む<", ">行間を読む — 報道が言っていないこと<")
        lexical = lexical.replace(">Between the Lines — 行間を読む</", ">行間を読む — 報道が言っていないこと</")
        # Tag labels
        lexical = lexical.replace("力学:<", "力学(Nowpattern):<")
        lexical = lexical.replace("力学:</", "力学(Nowpattern):</")
    else:
        # English articles: fix tag label
        lexical = lexical.replace("Dynamics:<", "Dynamics(Nowpattern):<")
        lexical = lexical.replace("Dynamics:</", "Dynamics(Nowpattern):</")

    # Fix シナリオシナリオ bug (both languages)
    lexical = lexical.replace("シナリオシナリオ", "シナリオ")

    if lexical != original:
        # Update the post
        token = get_token()
        headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}
        payload = {
            "posts": [{
                "lexical": lexical,
                "updated_at": updated_at,
            }]
        }
        r2 = requests.put(
            f"{BASE}/posts/{post_id}/?source=lexical",
            json=payload,
            headers=headers,
            verify=False
        )
        if r2.status_code == 200:
            fixed_count += 1
            print(f"  FIXED: {title[:60]}")
        else:
            print(f"  ERROR ({r2.status_code}): {title[:60]} - {r2.text[:100]}")
        time.sleep(0.5)  # Rate limit
    else:
        print(f"  OK: {title[:60]}")

print(f"\nDone. Fixed {fixed_count} of {len(posts)} articles.")
