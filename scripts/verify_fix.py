#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
iat = int(datetime.datetime.now().timestamp())
tok = jwt.encode({"iat": iat, "exp": iat + 300, "aud": "/admin/"}, bytes.fromhex(sec), algorithm="HS256", headers={"alg": "HS256", "typ": "JWT", "kid": kid})
slug = "horumuzuno3shi-jian-shi-jie-noshi-you-20-gazhi-matutari"
r = requests.get(f"https://nowpattern.com/ghost/api/admin/posts/slug/{slug}/?formats=lexical,html", headers={"Authorization": f"Ghost {tok}"}, verify=False)
post = r.json()["posts"][0]
html = post.get("html", "") or ""
lex_str = post.get("lexical", "") or ""
print(f"HTML length: {len(html)}")
print(f"np-tag-badge in HTML: {'np-tag-badge' in html}")
print(f"np-tag-badge in Lexical: {'np-tag-badge' in lex_str}")
print(f"np-fast-read in HTML: {'np-fast-read' in html}")
border = len(re.findall(r'border-bottom.*?1px solid', html))
print(f"border-bottom divs: {border}")
genre_bold = len(re.findall(r'<strong>.*?(?:Genre|\u30b8\u30e3\u30f3\u30eb)', html))
print(f"Bold Genre tags: {genre_bold}")
