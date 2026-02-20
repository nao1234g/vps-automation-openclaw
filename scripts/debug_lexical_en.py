#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英語記事のlexical構造を詳細確認"""
import json, os, time, hashlib, hmac, base64
import urllib3; urllib3.disable_warnings()
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

# Munich記事をサンプルで詳細確認
pid = "699779e45850354f44049bbe"
r = requests.get(
    f"{GHOST_URL}/ghost/api/admin/posts/{pid}/?fields=id,title,lexical",
    headers=hdrs(), verify=False, timeout=20)
data = r.json().get("posts", [{}])[0]
lex = data.get("lexical", "")

doc = json.loads(lex)
children = doc.get("root", {}).get("children", [])

with open("lexical_debug.txt", "w", encoding="utf-8") as f:
    f.write(f"Total children: {len(children)}\n\n")
    for i, child in enumerate(children[:5]):
        f.write(f"--- child[{i}] ---\n")
        f.write(f"type: {child.get('type')}\n")
        # 各typeの内容を確認
        if child.get("type") == "html":
            f.write(f"html: {child.get('html','')[:300]}\n")
        elif child.get("type") == "paragraph":
            # paragraph nodeにはchildren
            inner = child.get("children", [])
            text = " ".join(c.get("text","") for c in inner if c.get("type")=="text")
            f.write(f"text: {text[:300]}\n")
        else:
            f.write(f"raw: {json.dumps(child)[:300]}\n")
        f.write("\n")

print("Done -> lexical_debug.txt")
