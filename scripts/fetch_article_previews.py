#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""各問題記事の先頭300文字を取得してタイトル確認用ファイルに出力"""
import json, os, sys, re, time, hashlib, hmac, base64
import urllib3; urllib3.disable_warnings()
import requests

API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
GHOST_URL = "https://nowpattern.com"

# 問題記事のID一覧（audit_out.txtから）
PROBLEM_IDS = [
    ("699793255850354f44049bc9", "[1] 分散型取引所ハイパーリキッド、DeFiを巡る政策提言団体を米国で設立"),
    ("699779e45850354f44049bbe", "[2] 5 signals from Munich 2026: U.S.-Europe alliance fractures"),
    ("699779e05850354f44049bb1", "[3] Largest sewage spill in U.S. history"),
    ("699779dd5850354f44049ba8", "[4] Russia fires 400 drones + 29 missiles at Ukraine before Geneva talks"),
    ("699779d95850354f44049b9d", "[5] Sen. Kelly: Trump practically destroyed NATO"),
    ("699779d55850354f44049b94", "[6] New START expired. No replacement."),
    ("6997259e5850354f44049b8b", "[7] New START expired. No replacement. (dup)"),
    ("69967ce55850354f44049b80", "[8] 現実資産トークン化（RWA）市場、13.5%成長"),
    ("69967cdf5850354f44049b77", "[9] Paradigm: Bitcoin miners are flexible grid demand"),
    ("69967cdc5850354f44049b6a", "[10] Bundesbank chief Nagel backs euro stablecoins"),
    ("69967cce5850354f44049b5f", "[11] Russia's daily crypto volume: $650M+"),
    ("69967cca5850354f44049b56", "[12] Colby says NATO is stronger than ever"),
    ("6996289d5850354f44049b3d", "[13] Colby says NATO is stronger than ever (dup)"),
    ("6995d42c5850354f44049b32", "[14] トランプ・メディアがBTC・ETH・CROのETFをSECに申請"),
    ("6995d4285850354f44049b25", "[15] トランプが自動車排ガス規制を撤廃"),
    ("6995d4255850354f44049b1c", "[16] 体制転換が最善とトランプが発言、空母2隻で中東圧力"),
    ("6995d4215850354f44049b13", "[17] ルビオ＝王毅会談"),
    ("6995d4165850354f44049b08", "[18] 米・イスラエルがイランへの経済制裁強化で合意"),
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

def extract_html(lex):
    if not lex: return ""
    try:
        doc = json.loads(lex)
        return "\n".join(c.get("html","") for c in doc.get("root",{}).get("children",[]) if c.get("type")=="html")
    except: return ""

def strip_html(html):
    return re.sub(r"<[^>]+>", "", html).strip()

with open("articles_preview.txt", "w", encoding="utf-8") as f:
    for pid, label in PROBLEM_IDS:
        r = requests.get(
            f"{GHOST_URL}/ghost/api/admin/posts/{pid}/?fields=id,title,slug,lexical,updated_at",
            headers=hdrs(), verify=False, timeout=20)
        data = r.json().get("posts", [{}])[0]
        title = data.get("title", "")
        slug  = data.get("slug", "")
        html  = extract_html(data.get("lexical",""))
        text  = strip_html(html)[:600].replace("\n", " ").strip()

        f.write(f"{'='*70}\n")
        f.write(f"{label}\n")
        f.write(f"現タイトル: {title}\n")
        f.write(f"SLUG: {slug}\n")
        f.write(f"本文冒頭: {text}\n\n")
        print(f"OK: {label}")

print("Done -> articles_preview.txt")
