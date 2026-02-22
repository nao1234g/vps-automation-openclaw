#!/usr/bin/env python3
"""Final consistency check: taxonomy.json vs Ghost tags"""
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

r = requests.get("https://nowpattern.com/ghost/api/admin/tags/?limit=all",
                  headers={"Authorization": f"Ghost {token}"}, verify=False)
ghost_tags = {t["slug"]: t for t in r.json()["tags"]}

with open("/opt/shared/scripts/nowpattern_taxonomy.json") as f:
    tax = json.load(f)

all_tax = []
for g in tax["genres"]:
    all_tax.append(("Genre", g["slug"], g["name_ja"], g["name_en"]))
for e in tax["events"]:
    all_tax.append(("Event", e["slug"], e["name_ja"], e["name_en"]))
for d in tax["dynamics"]:
    all_tax.append(("Dynamics", d["slug"], d["name_ja"], d["name_en"]))

print(f"Taxonomy: {len(all_tax)} tags (13G + 19E + 16D)")
print(f"Ghost: {len(ghost_tags)} tags total")
print()

ok = 0
issues = []
for layer, slug, name_ja, name_en in all_tax:
    if slug not in ghost_tags:
        issues.append(f"  MISSING: [{layer}] {slug} ({name_en})")
    elif ghost_tags[slug]["name"] != name_en:
        issues.append(f"  MISMATCH: [{layer}] {slug}: Ghost='{ghost_tags[slug]['name']}' Expected='{name_en}'")
    else:
        ok += 1

if issues:
    print(f"ISSUES ({len(issues)}):")
    for i in issues:
        print(i)
else:
    print(f"ALL {ok} taxonomy tags verified in Ghost")

# Quick check: lang-ja / lang-en tags
for lt in ["lang-ja", "lang-en"]:
    if lt in ghost_tags:
        print(f"  {lt}: '{ghost_tags[lt]['name']}' (slug={ghost_tags[lt]['slug']})")
    else:
        print(f"  {lt}: MISSING!")
