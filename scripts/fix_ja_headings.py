#!/usr/bin/env python3
"""
日本語記事の英語見出しを日本語に統一するスクリプト
Ghost Admin API で記事を取得・更新する
"""

import json
import requests
import jwt
import time
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------- 設定 ----------
GHOST_URL = "https://nowpattern.com"
ADMIN_API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")

# ---------- 見出しマッピング ----------
HEADING_MAP = {
    "What Happened": "何が起きたか",
    "What happened": "何が起きたか",
    "The Big Picture": "全体像",
    "NOW Pattern": "NOW パターン",
    "Pattern History": "パターンの歴史",
    "What's Next": "今後の展望",
    "What\u2019s Next": "今後の展望",
    "Why It Matters": "なぜ重要か",
    "Why it matters": "なぜ重要か",
    "Key Players": "主要プレイヤー",
    "Stakeholder Map": "利害関係者マップ",
    "By the Numbers": "データで見る構造",
    "Historical Context": "歴史的文脈",
    "Triggers to Watch": "注目すべきトリガー",
    "Base case": "基本シナリオ",
    "Bull case": "楽観シナリオ",
    "Bear case": "悲観シナリオ",
}


def get_admin_token():
    """Ghost Admin API の JWT トークンを生成"""
    kid, secret = ADMIN_API_KEY.split(":")
    iat = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": kid}
    payload = {"iat": iat, "exp": iat + 300, "aud": "/admin/"}
    return jwt.encode(payload, bytes.fromhex(secret), algorithm="HS256", headers=header)


def get_all_posts():
    """Admin API で lang-ja 記事を取得"""
    token = get_admin_token()
    headers = {"Authorization": f"Ghost {token}"}
    posts = []
    page = 1
    while True:
        url = f"{GHOST_URL}/ghost/api/admin/posts/?limit=50&page={page}&formats=lexical&filter=tag:lang-ja"
        resp = requests.get(url, headers=headers, verify=False)
        data = resp.json()
        batch = data.get("posts", [])
        if not batch:
            break
        posts.extend(batch)
        meta = data.get("meta", {}).get("pagination", {})
        if page >= meta.get("pages", 1):
            break
        page += 1
    return posts


def fix_lexical_headings(lexical_str):
    """lexical JSON 内の英語見出しを日本語に置換"""
    if not lexical_str:
        return lexical_str, 0

    changed = 0
    result = lexical_str

    for eng, jpn in HEADING_MAP.items():
        if eng in result:
            result = result.replace(eng, jpn)
            changed += 1

    return result, changed


def update_post(post_id, updated_at, new_lexical):
    """Admin API で記事を更新"""
    token = get_admin_token()
    url = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/"
    headers = {
        "Authorization": f"Ghost {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "posts": [
            {
                "lexical": new_lexical,
                "updated_at": updated_at,
            }
        ]
    }
    resp = requests.put(url, json=payload, headers=headers, verify=False)
    return resp.status_code, resp.text


def main():
    if not ADMIN_API_KEY:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY が未設定です")
        print("source /opt/cron-env.sh を実行してください")
        return

    print("=== 日本語記事の英語見出し修正スクリプト ===")
    print()

    posts = get_all_posts()
    print(f"lang-ja 記事: {len(posts)} 件取得")
    print()

    total_fixed = 0

    for post in posts:
        title = post.get("title", "")
        post_id = post.get("id", "")
        updated_at = post.get("updated_at", "")
        lexical = post.get("lexical", "")

        new_lexical, changes = fix_lexical_headings(lexical)

        if changes > 0:
            print(f"  [{changes} 箇所] {title}")
            status, body = update_post(post_id, updated_at, new_lexical)
            if status == 200:
                print(f"    -> 更新成功")
                total_fixed += 1
            else:
                print(f"    -> 更新失敗 (HTTP {status})")
                # Show short error
                try:
                    err = json.loads(body)
                    msg = err.get("errors", [{}])[0].get("message", body[:200])
                    print(f"       {msg}")
                except Exception:
                    print(f"       {body[:200]}")
        else:
            print(f"  [OK] {title}")

    print()
    print(f"=== 完了: {total_fixed} 記事を修正しました ===")


if __name__ == "__main__":
    main()
