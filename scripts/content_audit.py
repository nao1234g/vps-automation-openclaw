#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英語問題記事の詳細コンテンツを取得・診断するスクリプト"""
import json, os, time, hashlib, hmac, base64, re
import urllib3; urllib3.disable_warnings()
import requests

API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
GHOST_URL = "https://nowpattern.com"

# 英語記事（タイトル修正済みだが内容が不明のもの）
EN_ARTICLE_IDS = [
    ("699779e45850354f44049bbe", "Munich 2026: 5 signals"),
    ("699779e05850354f44049bb1", "Largest sewage spill"),
    ("699779dd5850354f44049ba8", "Russia 400 drones"),
    ("699779d95850354f44049b9d", "Trump destroyed NATO"),
    ("6997259e5850354f44049b8b", "New START expired"),
    ("69967cdf5850354f44049b77", "Bitcoin miners grid demand"),
    ("69967cdc5850354f44049b6a", "Bundesbank euro stablecoins"),
    ("69967cce5850354f44049b5f", "Russia crypto $650M"),
    ("6996289d5850354f44049b3d", "Colby NATO stronger than ever"),
]

# 日本語記事（フォーマット崩れ）
JA_BROKEN_IDS = [
    ("69967ce55850354f44049b80", "RWA 13.5% growth"),
    ("6995d4285850354f44049b25", "Trump EV regulation"),
    ("6995d4215850354f44049b13", "Rubio Wang Yi"),
]

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

def strip_html(html):
    return re.sub(r"<[^>]+>", " ", html).strip()

with open("content_audit.txt", "w", encoding="utf-8") as f:
    f.write("=== 英語記事（内容確認） ===\n\n")
    for pid, label in EN_ARTICLE_IDS:
        r = requests.get(
            f"{GHOST_URL}/ghost/api/admin/posts/{pid}/?fields=id,title,slug,lexical,html,status",
            headers=hdrs(), verify=False, timeout=20)
        data = r.json().get("posts", [{}])[0]
        title = data.get("title", "")
        lex = data.get("lexical", "") or ""
        html = data.get("html", "") or ""

        # lexical から HTML 抽出
        lex_html = ""
        if lex:
            try:
                doc = json.loads(lex)
                lex_html = "\n".join(c.get("html","") for c in doc.get("root",{}).get("children",[]) if c.get("type")=="html")
            except: pass

        content = strip_html(lex_html or html)[:800]
        has_now_pattern = "NOW PATTERN" in (lex_html or html)
        has_tags = bool(re.search(r"Genre:|#Geopolitics|#Politics|#Technology|#Crypto", lex_html or html))
        f.write(f"[{label}]\n")
        f.write(f"title: {title}\n")
        f.write(f"lexical_len: {len(lex)} | html_len: {len(html)}\n")
        f.write(f"has_NOW_PATTERN: {has_now_pattern} | has_tags_header: {has_tags}\n")
        f.write(f"content_preview: {content[:400]}\n\n")
        print(f"OK: {label}")

    f.write("\n=== 日本語フォーマット崩れ記事 ===\n\n")
    for pid, label in JA_BROKEN_IDS:
        r = requests.get(
            f"{GHOST_URL}/ghost/api/admin/posts/{pid}/?fields=id,title,slug,lexical,html,status",
            headers=hdrs(), verify=False, timeout=20)
        data = r.json().get("posts", [{}])[0]
        title = data.get("title", "")
        lex = data.get("lexical", "") or ""
        html_raw = data.get("html", "") or ""
        lex_html = ""
        if lex:
            try:
                doc = json.loads(lex)
                lex_html = "\n".join(c.get("html","") for c in doc.get("root",{}).get("children",[]) if c.get("type")=="html")
            except: pass

        content = strip_html(lex_html or html_raw)[:800]
        f.write(f"[{label}]\n")
        f.write(f"title: {title}\n")
        f.write(f"lexical_len: {len(lex)} | html_len: {len(html_raw)}\n")
        f.write(f"content_preview: {content[:600]}\n\n")
        print(f"OK: {label}")

print("Done -> content_audit.txt")
