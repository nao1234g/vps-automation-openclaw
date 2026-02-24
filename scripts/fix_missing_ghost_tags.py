#!/usr/bin/env python3
"""
fix_missing_ghost_tags.py — Lexical JSON直接操作で記事タグ重複を除去 + Ghostタグ割り当て

修復内容:
  1. np-tag-badge（ベージュ背景の正しいタグバッジ）は残す
  2. border-bottom divや<p><strong>Genre/ジャンル:</strong>等の重複タグを除去
  3. Ghost記事タグを割り当て（ホームページカード表示用）

方式: Lexical JSONの children 配列を直接編集 → PUT lexical で更新
（?source=html は使わない — Ghost Lexical変換で np-tag-badge クラスが消えるため）

VPS上で実行:
  python3 fix_missing_ghost_tags.py --report
  python3 fix_missing_ghost_tags.py --slug <slug>
  python3 fix_missing_ghost_tags.py --apply-all
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
import hmac
import hashlib
import base64
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timezone

# ── 設定 ─────────────────────────────────────────────────────────
CRON_ENV = "/opt/cron-env.sh"
GHOST_URL = os.environ.get("NOWPATTERN_GHOST_URL", "https://nowpattern.com")

def load_env():
    env = {}
    if not os.path.exists(CRON_ENV):
        return env
    with open(CRON_ENV) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                k, v = line[7:].split("=", 1)
                env[k] = v.strip().strip("\"'")
    return env

env = load_env()
GHOST_API_KEY = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")

# ── Ghost Admin API ──────────────────────────────────────────────

def _ghost_jwt(api_key):
    key_id, secret = api_key.split(":")
    iat = int(datetime.now(timezone.utc).timestamp())
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "kid": key_id, "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"iat": iat, "exp": iat + 300, "aud": "/admin/"}).encode()
    ).rstrip(b"=").decode()
    sig_input = f"{header}.{payload}".encode()
    signature = hmac.new(bytes.fromhex(secret), sig_input, hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"

def ghost_request(method, path, data=None):
    url = f"{GHOST_URL}/ghost/api/admin{path}"
    token = _ghost_jwt(GHOST_API_KEY)
    headers = {
        "Authorization": f"Ghost {token}",
        "Content-Type": "application/json",
        "Accept-Version": "v5.0",
    }
    body = json.dumps(data).encode() if data else None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read())

# ── タクソノミー ─────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_taxonomy():
    paths = [
        os.path.join(SCRIPT_DIR, "nowpattern_taxonomy.json"),
        "/opt/shared/scripts/nowpattern_taxonomy.json",
    ]
    tax = None
    for p in paths:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                tax = json.load(f)
            break
    if not tax:
        return {}, {}

    ja_to_en = {}
    slug_to_en = {}
    for layer in ["genres", "events", "dynamics"]:
        for item in tax.get(layer, []):
            ja = item.get("name_ja", "")
            en = item.get("name_en", "") or item.get("name", "")
            slug = item.get("slug", "")
            if ja and en:
                ja_to_en[ja] = en
                ja_to_en[en] = en
            if slug and en:
                slug_to_en[slug] = en
    return ja_to_en, slug_to_en

JA_TO_EN, SLUG_TO_EN = load_taxonomy()

GENRE_NAMES_EN = {
    "Technology", "Geopolitics & Security", "Economy & Trade",
    "Finance & Markets", "Business & Industry", "Crypto & Web3",
    "Energy", "Environment & Climate", "Governance & Law",
    "Society", "Culture, Entertainment & Sports",
    "Media & Information", "Health & Science",
}

# ── 重複タグ判定（Lexical HTML node単位） ──────────────────────

def is_duplicate_tag_node(html_content):
    """Lexical HTML nodeが重複タグセクションかどうか判定。
    Returns True if this node should be REMOVED."""
    h = html_content

    # KEEP: np-tag-badge（正しいタグバッジ）
    if "np-tag-badge" in h:
        return False
    # KEEP: np-fast-read, np-summary, np-pattern-box, np-why-box etc.
    if any(cls in h for cls in ["np-fast-read", "np-summary", "np-pattern-box",
                                 "np-why-box", "np-footer", "np-diagram",
                                 "np-section-hr", "np-pattern-tag",
                                 "np-pattern-summary", "np-pattern-body"]):
        return False

    # REMOVE: border-bottom div with tag links
    if "border-bottom" in h and ("1px solid #e0dcd4" in h or "1px solid #e8e4dc" in h):
        if any(kw in h for kw in ["/tag/", "Genre", "Event", "Dynamics",
                                   "\u30b8\u30e3\u30f3\u30eb", "\u30a4\u30d9\u30f3\u30c8", "\u529b\u5b66"]):
            return True

    # REMOVE: standalone <p><strong>Genre/ジャンル:</strong>...<a>...</a></p>
    if re.match(r'\s*<p>\s*<strong>\s*(?:Genre|Event|Dynamics|\u30b8\u30e3\u30f3\u30eb|\u30a4\u30d9\u30f3\u30c8|\u529b\u5b66)', h):
        if "/tag/" in h:
            return True

    # REMOVE: standalone <p>イベント:...</p> or <p>力学:...</p>
    if re.match(r'\s*<p>\s*(?:Genre|Event|Dynamics|\u30b8\u30e3\u30f3\u30eb|\u30a4\u30d9\u30f3\u30c8|\u529b\u5b66)\s*[:：]', h):
        if "/tag/" in h:
            return True

    return False


def is_duplicate_tag_paragraph(node):
    """Lexical paragraph/heading node内のテキストが重複タグか判定。
    paragraph type nodeの中にGenre:/ジャンル: テキストが含まれる場合。"""
    if node.get("type") not in ("paragraph", "heading"):
        return False
    text = json.dumps(node)
    if any(kw in text for kw in ["Genre:", "Event:", "Dynamics:",
                                  "\u30b8\u30e3\u30f3\u30eb:", "\u30a4\u30d9\u30f3\u30c8:", "\u529b\u5b66:"]):
        if "/tag/" in text:
            return True
    return False


def extract_tag_names_from_html(html):
    """HTMLからタグslug→英語名を抽出"""
    tags_en = set()
    tag_links = re.findall(r'/tag/([^/"?\s]+)', html)
    for slug in tag_links:
        en = SLUG_TO_EN.get(slug, "")
        if en:
            tags_en.add(en)
    return tags_en


def detect_language(html):
    ja = sum(1 for m in ["\u30b8\u30e3\u30f3\u30eb", "\u30a4\u30d9\u30f3\u30c8", "\u529b\u5b66", "\u8981\u7d04"] if m in (html or ""))
    en = sum(1 for m in ["Genre", "Event", "Dynamics", "Summary"] if m in (html or ""))
    return "ja" if ja >= en else "en"


# ── メイン ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nowpattern Lexical\u30bf\u30b0\u4fee\u5fa9")
    parser.add_argument("--report", action="store_true", help="\u4f55\u304c\u5909\u308f\u308b\u304b\u5831\u544a\u306e\u307f")
    parser.add_argument("--slug", type=str, help="1\u8a18\u4e8b\u306e\u307f\uff08slug\u3092\u6307\u5b9a\uff09")
    parser.add_argument("--apply-all", action="store_true", help="\u5168\u8a18\u4e8b\u306b\u9069\u7528")
    args = parser.parse_args()

    if not GHOST_API_KEY:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not found")
        sys.exit(1)

    is_report = args.report or (not args.apply_all and not args.slug)

    print("=" * 60)
    print("Nowpattern Lexical Tag Fix")
    print("=" * 60)
    print(f"Mode: {'REPORT (no changes)' if is_report else 'APPLY'}")
    if args.slug:
        print(f"Target: {args.slug}")
    print()

    # Fetch posts
    if args.slug:
        result = ghost_request("GET", f"/posts/slug/{args.slug}/?formats=lexical,html&include=tags")
    else:
        result = ghost_request("GET", "/posts/?limit=all&formats=lexical,html&include=tags")
    posts = result.get("posts", [])
    print(f"Posts fetched: {len(posts)}\n")

    # Ghost tags for assignment
    tag_result = ghost_request("GET", "/tags/?limit=all")
    ghost_tags = {t["name"]: t["id"] for t in tag_result.get("tags", [])}

    needs_lexical_fix = []
    needs_tag_fix = []

    for post in posts:
        html = post.get("html", "") or ""
        lex_str = post.get("lexical", "") or ""
        title = post["title"]
        slug = post.get("slug", "")
        existing_tags = [t["name"] for t in post.get("tags", [])]

        if not lex_str:
            continue

        lex = json.loads(lex_str)
        nodes = lex.get("root", {}).get("children", [])

        # Find duplicate nodes to remove
        remove_indices = []
        for i, node in enumerate(nodes):
            if node.get("type") == "html":
                h = node.get("html", "")
                if is_duplicate_tag_node(h):
                    remove_indices.append(i)
            elif is_duplicate_tag_paragraph(node):
                remove_indices.append(i)

        # Ghost tag check
        extracted_en = extract_tag_names_from_html(html)
        lang = detect_language(html)
        missing_tags = []
        for fixed in ["Nowpattern", "Deep Pattern"]:
            if fixed not in existing_tags:
                missing_tags.append(fixed)
        lang_tag = "\u65e5\u672c\u8a9e" if lang == "ja" else "English"
        if lang_tag not in existing_tags:
            missing_tags.append(lang_tag)
        for en in extracted_en:
            if en not in existing_tags:
                missing_tags.append(en)

        if remove_indices:
            needs_lexical_fix.append({
                "post": post,
                "remove_indices": remove_indices,
                "lex": lex,
            })

        if missing_tags:
            needs_tag_fix.append({
                "post": post,
                "missing": missing_tags,
                "existing": existing_tags,
            })

    # Report
    print("=" * 60)
    print(f"Lexical duplicate removal: {len(needs_lexical_fix)} posts")
    print(f"Ghost tag assignment: {len(needs_tag_fix)} posts")
    print("=" * 60)

    if needs_lexical_fix:
        print("\nDuplicate Lexical nodes to remove:")
        for item in needs_lexical_fix:
            title = item["post"]["title"][:50]
            slug = item["post"]["slug"][:40]
            indices = item["remove_indices"]
            print(f"\n  [{slug}] {title}")
            print(f"    Remove {len(indices)} node(s): {indices}")
            nodes = item["lex"]["root"]["children"]
            for idx in indices:
                h = nodes[idx].get("html", "") if nodes[idx].get("type") == "html" else json.dumps(nodes[idx])
                print(f"      Node[{idx}]: {h[:120]}...")

    if needs_tag_fix:
        print("\nGhost tags to add:")
        for item in needs_tag_fix:
            title = item["post"]["title"][:50]
            slug = item["post"]["slug"][:40]
            missing = ", ".join(item["missing"][:5])
            print(f"\n  [{slug}] {title}")
            print(f"    Add: {missing}")

    if is_report:
        print("\nREPORT MODE. To apply:")
        print("  --slug <slug>  : fix one article")
        print("  --apply-all    : fix all articles")
        return

    # Apply fixes
    print("\nApplying fixes...")
    ok = 0
    fail = 0

    # Lexical fix
    for item in needs_lexical_fix:
        post = item["post"]
        lex = item["lex"]
        title = post["title"][:50]
        remove_set = set(item["remove_indices"])

        # Remove duplicate nodes (reverse order to keep indices valid)
        new_children = [n for i, n in enumerate(lex["root"]["children"]) if i not in remove_set]
        lex["root"]["children"] = new_children

        try:
            fresh = ghost_request("GET", f"/posts/{post['id']}/?include=tags")
            updated_at = fresh["posts"][0]["updated_at"]

            ghost_request("PUT", f"/posts/{post['id']}/", {
                "posts": [{
                    "lexical": json.dumps(lex),
                    "mobiledoc": None,
                    "updated_at": updated_at,
                }]
            })
            print(f"  OK Lexical: {title} (removed {len(remove_set)} nodes)")
            ok += 1
        except Exception as e:
            print(f"  FAIL Lexical: {title} -- {e}")
            fail += 1
        time.sleep(0.5)

    # Ghost tag assignment
    for item in needs_tag_fix:
        post = item["post"]
        title = post["title"][:50]
        all_tags = list(item["existing"]) + item["missing"]

        tag_objects = []
        for name in all_tags:
            if name in ghost_tags:
                tag_objects.append({"id": ghost_tags[name]})
            else:
                tag_objects.append({"name": name})

        try:
            fresh = ghost_request("GET", f"/posts/{post['id']}/?include=tags")
            updated_at = fresh["posts"][0]["updated_at"]

            ghost_request("PUT", f"/posts/{post['id']}/", {
                "posts": [{"tags": tag_objects, "updated_at": updated_at}]
            })
            print(f"  OK Tags: {title}")
            ok += 1
        except Exception as e:
            print(f"  FAIL Tags: {title} -- {e}")
            fail += 1
        time.sleep(0.3)

    print(f"\n{'='*60}")
    print(f"Done: {ok} success / {fail} failed")


if __name__ == "__main__":
    main()
