#!/usr/bin/env python3
"""Quick verification of taxonomy page updates"""
import json, time, hashlib, hmac, base64, sqlite3
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

for slug, lang_param in [("taxonomy-ja", "?lang=ja"), ("taxonomy-en", "?lang=en")]:
    r = requests.get(
        f"https://nowpattern.com/ghost/api/admin/pages/?limit=1&filter=slug:{slug}&formats=lexical",
        headers={"Authorization": f"Ghost {token}"}, verify=False
    )
    page = r.json()["pages"][0]
    lex = json.loads(page["lexical"])
    html = lex["root"]["children"][0]["html"]
    has_pill = "border-radius:20px" in html
    has_table = "<table" in html
    has_lang = lang_param in html
    status = "OK" if (not has_pill and has_table and has_lang) else "FAIL"
    print(f"{slug}: {status} | pills={has_pill} tables={has_table} lang={has_lang} len={len(html)}")

# Check site JS
conn = sqlite3.connect("/var/www/nowpattern/content/data/ghost.db")
cur = conn.execute("SELECT value FROM settings WHERE key='codeinjection_foot'")
row = cur.fetchone()
conn.close()
if row and row[0]:
    js = row[0]
    has_tag = "isTag" in js
    has_lang = 'get("lang")' in js
    print(f"site-js: OK | tag_filter={has_tag} lang_param={has_lang} len={len(js)}")
else:
    print("site-js: EMPTY")
