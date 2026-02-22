#!/usr/bin/env python3
"""Assign taxonomy tags to all 27 existing Nowpattern posts."""

import os, sys, json, jwt, datetime, time
import requests, urllib3
urllib3.disable_warnings()

CRON_ENV = "/opt/cron-env.sh"
GHOST_URL = "https://nowpattern.com"

def load_env():
    env = {}
    with open(CRON_ENV) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                k, v = line[7:].split("=", 1)
                env[k] = v.strip().strip("\"'")
    return env

env = load_env()
API_KEY = env["NOWPATTERN_GHOST_ADMIN_API_KEY"]
kid, secret = API_KEY.split(":")

def token():
    iat = int(datetime.datetime.now().timestamp())
    return jwt.encode(
        {"iat": iat, "exp": iat + 300, "aud": "/admin/"},
        bytes.fromhex(secret), algorithm="HS256",
        headers={"alg": "HS256", "typ": "JWT", "kid": kid}
    )

def headers():
    return {"Authorization": f"Ghost {token()}", "Content-Type": "application/json"}

# Tag mapping: post_id -> list of tag names
# Based on article titles and content analysis
TAG_MAP = {
    # === EN Deep Patterns ===
    # Iran Hormuz (long) - Geopolitics, Energy, Military, Escalation, Resource Power, Exit Game
    "6995b1dbece23218fbeedd19": [
        "Nowpattern", "Deep Pattern", "English",
        "Geopolitics & Security", "Energy",
        "Military Conflict", "Resource & Energy Crisis",
        "Escalation Spiral", "Resource Power", "Exit Game"
    ],
    # EU vs US Tech War - Technology, Governance, Regulation, Platform Dominance, Blowback
    "6995af68ece23218fbeedcca": [
        "Nowpattern", "Deep Pattern", "English",
        "Technology", "Governance & Law",
        "Regulation & Law Change",
        "Platform Dominance", "Blowback"
    ],
    # Geneva 6 Hours - Geopolitics, Military, Escalation, Exit Game, Alliance Strain
    "6995af0fece23218fbeedcc3": [
        "Nowpattern", "Deep Pattern", "English",
        "Geopolitics & Security",
        "Military Conflict", "Treaty & Alliance Change",
        "Escalation Spiral", "Exit Game", "Alliance Strain"
    ],
    # Navalny Dart-Frog Poison - Geopolitics, Governance, Judicial, Deterrence Failure, Institutional Rot
    "6995aed0ece23218fbeedcbb": [
        "Nowpattern", "Deep Pattern", "English",
        "Geopolitics & Security", "Governance & Law",
        "Judicial Action",
        "Deterrence Failure", "Institutional Rot"
    ],
    # 3 Hours of Hormuz - Geopolitics, Energy, Military, Resource, Escalation, Resource Power
    "6995ada1168f1a053528f4b1": [
        "Nowpattern", "Deep Pattern", "English",
        "Geopolitics & Security", "Energy",
        "Military Conflict", "Resource & Energy Crisis",
        "Escalation Spiral", "Resource Power"
    ],
    # Munich Security Conf - Geopolitics, Treaty/Alliance, Alliance Strain, Legitimacy Void
    "699779e45850354f44049bbe": [
        "Nowpattern", "Deep Pattern", "English",
        "Geopolitics & Security",
        "Treaty & Alliance Change",
        "Alliance Strain", "Legitimacy Void"
    ],
    # Largest Sewage Spill - Environment, Governance, Disaster, Institutional Rot, Systemic Fragility
    "699779e05850354f44049bb1": [
        "Nowpattern", "Deep Pattern", "English",
        "Environment & Climate", "Governance & Law",
        "Disaster & Accident",
        "Institutional Rot", "Systemic Fragility"
    ],
    # Russia 400 Drones before Geneva - Geopolitics, Military, Escalation, Exit Game
    "699779dd5850354f44049ba8": [
        "Nowpattern", "Deep Pattern", "English",
        "Geopolitics & Security",
        "Military Conflict",
        "Escalation Spiral", "Exit Game"
    ],
    # Trump Destroyed NATO - Geopolitics, Treaty/Alliance, Alliance Strain, Deterrence Failure
    "699779d95850354f44049b9d": [
        "Nowpattern", "Deep Pattern", "English",
        "Geopolitics & Security",
        "Treaty & Alliance Change",
        "Alliance Strain", "Deterrence Failure"
    ],
    # New START Expired - Geopolitics, Treaty/Alliance, Deterrence Failure, Escalation
    "6997259e5850354f44049b8b": [
        "Nowpattern", "Deep Pattern", "English",
        "Geopolitics & Security",
        "Treaty & Alliance Change",
        "Deterrence Failure", "Escalation Spiral"
    ],
    # Bitcoin Miners Grid - Energy, Crypto, Regulation, Resource Power, Narrative Control
    "69967cdf5850354f44049b77": [
        "Nowpattern", "Deep Pattern", "English",
        "Energy", "Crypto & Web3",
        "Regulation & Law Change",
        "Resource Power", "Narrative Control"
    ],
    # Bundesbank Euro Stablecoins - Finance, Crypto, Regulation, Financial Coercion, Platform Dominance
    "69967cdc5850354f44049b6a": [
        "Nowpattern", "Deep Pattern", "English",
        "Finance & Markets", "Crypto & Web3",
        "Regulation & Law Change",
        "Financial Coercion", "Platform Dominance"
    ],
    # Russia $650M Crypto - Crypto, Geopolitics, Sanctions, Financial Coercion, Blowback
    "69967cce5850354f44049b5f": [
        "Nowpattern", "Deep Pattern", "English",
        "Crypto & Web3", "Geopolitics & Security",
        "Sanctions & Economic Warfare",
        "Financial Coercion", "Blowback"
    ],
    # Colby NATO Stronger - Geopolitics, Treaty/Alliance, Alliance Strain, Narrative Control
    "6996289d5850354f44049b3d": [
        "Nowpattern", "Deep Pattern", "English",
        "Geopolitics & Security",
        "Treaty & Alliance Change",
        "Alliance Strain", "Narrative Control"
    ],

    # === JA Deep Patterns (Ghost tags are registered with EN names) ===
    # ホルムズの3時間
    "69959de6cc483075babd7f4d": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Geopolitics & Security", "Energy",
        "Military Conflict", "Resource & Energy Crisis",
        "Escalation Spiral", "Resource Power"
    ],
    # ジュネーブの6時間
    "69959e38cc483075babd7f57": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Geopolitics & Security",
        "Military Conflict", "Treaty & Alliance Change",
        "Escalation Spiral", "Exit Game"
    ],
    # 毒蛙とクレムリン
    "69959f2dcc483075babd7f60": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Geopolitics & Security", "Governance & Law",
        "Judicial Action",
        "Deterrence Failure", "Institutional Rot"
    ],
    # イランがホルムズ封鎖
    "699535ab4e0b36dac67af1df": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Geopolitics & Security", "Energy",
        "Military Conflict", "Resource & Energy Crisis",
        "Escalation Spiral", "Resource Power"
    ],
    # EU vs テック戦争
    "6995aeb6ece23218fbeedca9": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Technology", "Governance & Law",
        "Regulation & Law Change",
        "Platform Dominance", "Blowback"
    ],
    # AIエージェントが買い物
    "69966ebf5850354f44049b46": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Technology", "Business & Industry",
        "Tech Breakthrough",
        "Platform Dominance", "Tech Leapfrog"
    ],
    # Hyperliquid DeFi lobbying
    "699793255850354f44049bc9": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Crypto & Web3", "Governance & Law",
        "Regulation & Law Change",
        "Regulatory Capture", "Narrative Control"
    ],
    # RWA 13.5%成長
    "69967ce55850354f44049b80": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Finance & Markets", "Crypto & Web3",
        "Market Shock",
        "Capital Flight", "Tech Leapfrog"
    ],
    # 大統領企業 ETF申請
    "6995d42c5850354f44049b32": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Crypto & Web3", "Governance & Law",
        "Regulation & Law Change",
        "Regulatory Capture", "Moral Hazard"
    ],
    # トランプ排ガス規制撤廃
    "6995d4285850354f44049b25": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Energy", "Environment & Climate",
        "Regulation & Law Change",
        "Shock Doctrine", "Blowback"
    ],
    # トランプ イラン体制転換
    "6995d4255850354f44049b1c": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Geopolitics & Security",
        "Military Conflict",
        "Escalation Spiral", "Deterrence Failure"
    ],
    # ルビオ王毅会談
    "6995d4215850354f44049b13": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Geopolitics & Security", "Economy & Trade",
        "Sanctions & Economic Warfare",
        "Exit Game", "Narrative Control"
    ],
    # 米イスラエル イラン制裁
    "6995d4165850354f44049b08": [
        "Nowpattern", "Deep Pattern", "\u65e5\u672c\u8a9e",
        "Geopolitics & Security",
        "Sanctions & Economic Warfare",
        "Financial Coercion", "Alliance Strain"
    ],
}

# Get all Ghost tags for name->id mapping
r = requests.get(f"{GHOST_URL}/ghost/api/admin/tags/?limit=all", headers=headers(), verify=False)
ghost_tags = {t["name"]: t["id"] for t in r.json()["tags"]}
print(f"Ghost tags loaded: {len(ghost_tags)}")

# Process each post
success = 0
failed = 0

for post_id, tag_names in TAG_MAP.items():
    # First get the post to get updated_at
    r = requests.get(f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/", headers=headers(), verify=False)
    if r.status_code != 200:
        print(f"SKIP: Cannot find post {post_id}: {r.status_code}")
        failed += 1
        continue

    post = r.json()["posts"][0]
    updated_at = post["updated_at"]
    title = post["title"][:50]

    # Resolve tag names to IDs
    tag_objects = []
    for name in tag_names:
        if name in ghost_tags:
            tag_objects.append({"id": ghost_tags[name]})
        else:
            print(f"  WARNING: Tag '{name}' not found in Ghost")

    # Update the post with tags
    payload = {
        "posts": [{
            "tags": tag_objects,
            "updated_at": updated_at,
        }]
    }

    r = requests.put(
        f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/",
        json=payload, headers=headers(), verify=False
    )

    if r.status_code == 200:
        assigned = len(tag_objects)
        print(f"OK: {title}  ({assigned} tags)")
        success += 1
    else:
        print(f"FAIL: {title}  {r.status_code} {r.text[:200]}")
        failed += 1

    time.sleep(0.2)

print(f"\nDone: {success} success, {failed} failed")
