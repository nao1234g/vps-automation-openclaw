#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lexical nativeフォーマットの記事から全テキストを抽出する
"""
import json, os, time, hashlib, hmac, base64, re
import urllib3; urllib3.disable_warnings()
import requests

API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
GHOST_URL = "https://nowpattern.com"

ARTICLES = [
    # English
    ("699779e45850354f44049bbe", "Munich 2026"),
    ("699779e05850354f44049bb1", "Sewage Spill"),
    ("699779dd5850354f44049ba8", "Russia Drones"),
    ("699779d95850354f44049b9d", "Trump NATO"),
    ("6997259e5850354f44049b8b", "New START"),
    ("69967cdf5850354f44049b77", "Bitcoin Mining"),
    ("69967cdc5850354f44049b6a", "Bundesbank Stablecoin"),
    ("69967cce5850354f44049b5f", "Russia Crypto"),
    ("6996289d5850354f44049b3d", "Colby NATO"),
    # Japanese broken
    ("69967ce55850354f44049b80", "RWA Growth"),
    ("6995d4285850354f44049b25", "Trump EV"),
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

def extract_text_from_node(node):
    """lexical nodeから再帰的にテキストを抽出"""
    ntype = node.get("type", "")
    parts = []

    if ntype in ("text", "extended-text"):
        parts.append(node.get("text", ""))

    elif ntype == "html":
        html = node.get("html", "")
        text = re.sub(r"<[^>]+>", " ", html)
        parts.append(text.strip())

    elif ntype in ("heading", "extended-heading"):
        tag = node.get("tag", "h2")
        inner = " ".join(extract_text_from_node(c) for c in node.get("children", []))
        parts.append(f"\n[{tag.upper()}] {inner}")

    elif ntype == "paragraph":
        inner = " ".join(extract_text_from_node(c) for c in node.get("children", []))
        if inner.strip():
            parts.append(inner)

    elif ntype in ("list", "listitem"):
        for c in node.get("children", []):
            inner = extract_text_from_node(c)
            if inner.strip():
                parts.append(f"• {inner}")

    elif ntype == "quote":
        inner = " ".join(extract_text_from_node(c) for c in node.get("children", []))
        parts.append(f"> {inner}")

    elif ntype == "horizontalrule":
        parts.append("---")

    else:
        # その他のノード（image, embed等）は再帰
        for c in node.get("children", []):
            parts.append(extract_text_from_node(c))

    return "\n".join(p for p in parts if p)

def extract_all_text(lex_str):
    if not lex_str:
        return ""
    try:
        doc = json.loads(lex_str)
        children = doc.get("root", {}).get("children", [])
        parts = [extract_text_from_node(c) for c in children]
        return "\n".join(p for p in parts if p.strip())
    except Exception as e:
        return f"ERROR: {e}"

with open("full_content.txt", "w", encoding="utf-8") as f:
    for pid, label in ARTICLES:
        r = requests.get(
            f"{GHOST_URL}/ghost/api/admin/posts/{pid}/?fields=id,title,slug,lexical,updated_at",
            headers=hdrs(), verify=False, timeout=20)
        data = r.json().get("posts", [{}])[0]
        title = data.get("title", "")
        updated_at = data.get("updated_at", "")
        lex = data.get("lexical", "")

        text = extract_all_text(lex)

        f.write(f"{'='*70}\n")
        f.write(f"ID: {pid}\n")
        f.write(f"LABEL: {label}\n")
        f.write(f"TITLE: {title}\n")
        f.write(f"UPDATED_AT: {updated_at}\n")
        f.write(f"{'='*70}\n")
        f.write(text)
        f.write("\n\n")
        print(f"OK: {label} ({len(text)} chars)")

print("Done -> full_content.txt")
