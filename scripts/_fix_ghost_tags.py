#!/usr/bin/env python3
"""Fix missing and mismatched Ghost tags"""
import json, time, hashlib, hmac, base64
import urllib3; urllib3.disable_warnings()
import requests

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
headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}

# Load taxonomy
with open("/opt/shared/scripts/nowpattern_taxonomy.json") as f:
    tax = json.load(f)
dyn_map = {d["slug"]: d for d in tax["dynamics"]}

# 1. Create missing tags
for slug in ["p-path-dependency", "p-winner-takes-all"]:
    d = dyn_map[slug]
    desc = d["description_en"] + " / " + d["description_ja"]
    body = {"tags": [{"name": d["name_en"], "slug": slug, "description": desc}]}
    r = requests.post("https://nowpattern.com/ghost/api/admin/tags/", json=body, headers=headers, verify=False)
    if r.status_code == 201:
        print(f"CREATED: {slug} -> {d['name_en']}")
    else:
        print(f"ERROR creating {slug}: {r.status_code} {r.text[:200]}")

# 2. Rename mismatched tags
renames = {
    "p-institutional-rot": "Institutional Decay",
    "p-collective-failure": "Coordination Failure",
}

r = requests.get("https://nowpattern.com/ghost/api/admin/tags/?limit=all",
                  headers={"Authorization": f"Ghost {token}"}, verify=False)
all_tags = {t["slug"]: t for t in r.json()["tags"]}

for slug, new_name in renames.items():
    if slug in all_tags:
        tag = all_tags[slug]
        d = dyn_map[slug]
        desc = d["description_en"] + " / " + d["description_ja"]
        body = {"tags": [{"name": new_name, "description": desc, "updated_at": tag["updated_at"]}]}
        r = requests.put(f"https://nowpattern.com/ghost/api/admin/tags/{tag['id']}/",
                         json=body, headers=headers, verify=False)
        if r.status_code == 200:
            print(f"RENAMED: {slug} -> {new_name}")
        else:
            print(f"ERROR renaming {slug}: {r.status_code} {r.text[:200]}")
    else:
        print(f"NOT FOUND: {slug}")

print("Done")
