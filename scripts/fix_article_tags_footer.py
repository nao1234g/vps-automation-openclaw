#!/usr/bin/env python3
"""
既存のGhost記事フッターから Tags / NOW PATTERN 行を削除するスクリプト。

使い方（VPS上で実行）:
  source /opt/cron-env.sh && python3 scripts/fix_article_tags_footer.py

対象: nowpattern.comの全公開済み記事
"""
import json
import os
import re
import sys

# VPS上の環境変数からAPIキーを取得
API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
GHOST_URL = "https://nowpattern.com"

if not API_KEY:
    print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY が設定されていません")
    print("実行方法: source /opt/cron-env.sh && python3 scripts/fix_article_tags_footer.py")
    sys.exit(1)

import hashlib
import hmac
import time
import urllib3
urllib3.disable_warnings()

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)


def make_jwt(admin_api_key: str) -> str:
    import base64
    key_id, secret = admin_api_key.split(":")
    iat = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iat": iat, "exp": iat + 300, "aud": "/admin/"}

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    h = b64url(json.dumps(header).encode())
    p = b64url(json.dumps(payload).encode())
    signing_input = f"{h}.{p}"
    secret_bytes = bytes.fromhex(secret)
    sig = hmac.new(secret_bytes, signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{b64url(sig)}"


def get_auth_headers():
    token = make_jwt(API_KEY)
    return {
        "Authorization": f"Ghost {token}",
        "Content-Type": "application/json",
    }


def remove_tags_footer_from_html(html: str) -> tuple[str, bool]:
    """
    フッター内の以下の行を削除する:
      <p><strong>Tags:</strong> ... </p>
      <p><strong>NOW PATTERN:</strong> ... </p>
    戻り値: (修正後のHTML, 変更があったか)
    """
    original = html

    # <p><strong>Tags:</strong> ... </p>  を削除（改行・空白を考慮）
    html = re.sub(
        r'<p[^>]*>\s*<strong[^>]*>Tags:</strong>[^<]*(?:<[^/][^>]*>[^<]*</[^>]+>[^<]*)*</p>\s*',
        '',
        html,
        flags=re.IGNORECASE | re.DOTALL
    )

    # <p><strong>NOW PATTERN:</strong> ... </p> を削除
    html = re.sub(
        r'<p[^>]*>\s*<strong[^>]*>NOW PATTERN:</strong>[^<]*(?:<[^/][^>]*>[^<]*</[^>]+>[^<]*)*</p>\s*',
        '',
        html,
        flags=re.IGNORECASE | re.DOTALL
    )

    return html, html != original


def fetch_all_posts():
    """Ghost APIから全記事を取得"""
    posts = []
    page = 1
    while True:
        headers = get_auth_headers()
        resp = requests.get(
            f"{GHOST_URL}/ghost/api/admin/posts/?limit=50&page={page}&fields=id,title,slug,lexical,updated_at",
            headers=headers,
            verify=False,
            timeout=30
        )
        if resp.status_code != 200:
            print(f"ERROR fetching posts: {resp.status_code} {resp.text[:200]}")
            break
        data = resp.json()
        batch = data.get("posts", [])
        posts.extend(batch)
        meta = data.get("meta", {}).get("pagination", {})
        if page >= meta.get("pages", 1):
            break
        page += 1
    return posts


def update_post(post_id: str, new_html: str, updated_at: str):
    """Ghost記事を更新"""
    headers = get_auth_headers()
    lexical_doc = {
        "root": {
            "children": [{"type": "html", "version": 1, "html": new_html}],
            "direction": None, "format": "", "indent": 0,
            "type": "root", "version": 1,
        }
    }
    body = {
        "posts": [{"lexical": json.dumps(lexical_doc), "updated_at": updated_at}]
    }
    resp = requests.put(
        f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/",
        json=body,
        headers=headers,
        verify=False,
        timeout=30
    )
    return resp.status_code == 200, resp.text[:200]


def extract_html_from_lexical(lexical_str: str) -> str:
    """lexical JSONからHTMLを抽出"""
    if not lexical_str:
        return ""
    try:
        doc = json.loads(lexical_str)
        parts = []
        for child in doc.get("root", {}).get("children", []):
            if child.get("type") == "html":
                parts.append(child.get("html", ""))
        return "\n".join(parts)
    except Exception:
        return ""


def main():
    print(f"🔍 Ghost記事を取得中... ({GHOST_URL})")
    posts = fetch_all_posts()
    print(f"📄 {len(posts)}件の記事を取得")

    fixed = 0
    for post in posts:
        post_id = post["id"]
        title = post["title"]
        slug = post.get("slug", "")
        lexical_str = post.get("lexical", "")
        updated_at = post.get("updated_at", "")

        if not lexical_str:
            continue

        html = extract_html_from_lexical(lexical_str)
        if not html:
            continue

        new_html, changed = remove_tags_footer_from_html(html)
        if not changed:
            continue

        print(f"\n🔧 修正中: {title}")
        print(f"   slug: {slug}")
        ok, msg = update_post(post_id, new_html, updated_at)
        if ok:
            print(f"   ✅ 完了")
            fixed += 1
        else:
            print(f"   ❌ エラー: {msg}")

    print(f"\n✅ 完了: {fixed}件の記事を修正しました")


if __name__ == "__main__":
    main()
