import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('163.44.124.123', username='root', password='MySecurePass2026!')

# 1. Get one full card HTML from homepage
cmd1 = r'''curl -s https://nowpattern.com/ --insecure | python3 -c "
import sys, re
html = sys.stdin.read()
card = re.search(r'<article class=.gh-card[^>]*>.*?</article>', html, re.DOTALL)
if card:
    print(card.group()[:3000])
print('---TAGS---')
tags = set()
for m in re.finditer(r'class=.gh-card ([^\"]+).', html):
    for c in m.group(1).split():
        if c.startswith('tag-'):
            tags.add(c)
for t in sorted(tags):
    print(t)
"
'''
stdin1, stdout1, stderr1 = ssh.exec_command(cmd1, timeout=30)
out1 = stdout1.read().decode('utf-8', errors='replace')
err1 = stderr1.read().decode('utf-8', errors='replace')
print("=== CARD HTML + TAG CLASSES ===")
print(out1)
if err1.strip():
    print("STDERR:", err1[:500])

# 2. Get Ghost tag slugs
cmd2 = """python3 << 'PYEOF'
import json, datetime, jwt, requests, urllib3
urllib3.disable_warnings()
env = {}
with open("/opt/cron-env.sh") as f:
    for line in f:
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[7:].split("=", 1)
            env[k] = v.strip().strip('"').strip("'")
key = env["NOWPATTERN_GHOST_ADMIN_API_KEY"]
kid, sec = key.split(":")
iat = int(datetime.datetime.now().timestamp())
tok = jwt.encode({"iat": iat, "exp": iat + 300, "aud": "/admin/"}, bytes.fromhex(sec), algorithm="HS256", headers={"alg": "HS256", "typ": "JWT", "kid": kid})
r = requests.get("https://nowpattern.com/ghost/api/admin/tags/?limit=all", headers={"Authorization": f"Ghost {tok}"}, verify=False)
tags = r.json()["tags"]
for t in tags:
    slug = t["slug"]
    name = t["name"]
    print(f"{slug:45s} | {name}")
PYEOF
"""
stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=30)
out2 = stdout2.read().decode('utf-8', errors='replace')
err2 = stderr2.read().decode('utf-8', errors='replace')
print("\n=== GHOST TAG SLUGS ===")
print(out2)
if err2.strip():
    print("STDERR:", err2[:500])

# 3. Check codeinjection_foot and head for existing tag JS
cmd3 = """python3 << 'PYEOF'
import sqlite3, re
conn = sqlite3.connect("/var/www/nowpattern/content/data/ghost.db")
cur = conn.cursor()
for key in ["codeinjection_head", "codeinjection_foot"]:
    cur.execute(f"SELECT value FROM settings WHERE key = '{key}'")
    row = cur.fetchone()
    val = (row[0] or "") if row else ""
    print(f"--- {key}: {len(val)} chars ---")
    scripts = re.findall(r'<script>(.*?)</script>', val, re.DOTALL)
    for i, s in enumerate(scripts):
        if "card" in s.lower() or "tag" in s.lower() or "taxonomy" in s.lower():
            print(f"  Script {i+1} ({len(s)} chars, tag/card related):")
            print(s[:1500])
            if len(s) > 1500:
                print("...")
conn.close()
PYEOF
"""
stdin3, stdout3, stderr3 = ssh.exec_command(cmd3, timeout=30)
out3 = stdout3.read().decode('utf-8', errors='replace')
err3 = stderr3.read().decode('utf-8', errors='replace')
print("\n=== CODEINJECTION SCRIPTS ===")
print(out3)
if err3.strip():
    print("STDERR:", err3[:500])

ssh.close()
