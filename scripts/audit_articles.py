#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, sys, re, time, hashlib, hmac, base64
import urllib3
urllib3.disable_warnings()
import requests

API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
GHOST_URL = "https://nowpattern.com"

def make_jwt(key):
    kid, secret = key.split(":")
    iat = int(time.time())
    def b64u(d): return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
    h = b64u(json.dumps({"alg":"HS256","typ":"JWT","kid":kid}).encode())
    p = b64u(json.dumps({"iat":iat,"exp":iat+300,"aud":"/admin/"}).encode())
    s = f"{h}.{p}"
    sig = hmac.new(bytes.fromhex(secret), s.encode(), hashlib.sha256).digest()
    return f"{s}.{b64u(sig)}"

def hdrs():
    return {"Authorization": f"Ghost {make_jwt(API_KEY)}", "Content-Type": "application/json"}

posts, page = [], 1
while True:
    r = requests.get(
        f"{GHOST_URL}/ghost/api/admin/posts/?limit=50&page={page}&fields=id,title,slug,lexical,status",
        headers=hdrs(), verify=False, timeout=30)
    data = r.json()
    batch = data.get("posts", [])
    posts.extend(batch)
    meta = data.get("meta", {}).get("pagination", {})
    if page >= meta.get("pages", 1):
        break
    page += 1

results = []
for p in posts:
    title = p.get("title", "")
    slug  = p.get("slug", "")
    lex   = p.get("lexical", "")
    html  = ""
    if lex:
        try:
            doc = json.loads(lex)
            html = "\n".join(c.get("html","") for c in doc.get("root",{}).get("children",[]) if c.get("type")=="html")
        except:
            pass

    issues = []

    # 1. タイトルに「観測ログ」
    if "\u89b3\u6e2c\u30ed\u30b0" in title:
        issues.append("TITLE=観測ログ")

    # 2. 記事冒頭にジャンルタグなし
    if html:
        top500 = html[:800]
        if "\u30b8\u30e3\u30f3\u30eb:" not in top500 and "#\u30c6\u30af\u30ce\u30ed\u30b8" not in top500 and "genre" not in top500.lower():
            issues.append("NO_GENRE_TAGS")

    # 3. NOW PATTERNセクションなし
    if html and "NOW PATTERN" not in html:
        issues.append("NO_NOW_PATTERN")

    # 4. Tagsフッター残存
    if re.search(r"<strong[^>]*>Tags:</strong>", html, re.IGNORECASE):
        issues.append("TAGS_FOOTER_REMAINING")

    if issues:
        results.append({"title": title, "slug": slug, "id": p["id"], "issues": issues})

outfile = "audit_out.txt"
with open(outfile, "w", encoding="utf-8") as f:
    f.write(f"Total articles: {len(posts)}\n")
    f.write(f"Issues found:   {len(results)}\n\n")
    f.write("="*60 + "\n\n")
    for i, a in enumerate(results, 1):
        f.write(f"[{i}] {a['title']}\n")
        f.write(f"    slug:   {a['slug']}\n")
        f.write(f"    id:     {a['id']}\n")
        f.write(f"    issues: {' | '.join(a['issues'])}\n\n")

print(f"Done. {len(results)} issues -> {outfile}")
