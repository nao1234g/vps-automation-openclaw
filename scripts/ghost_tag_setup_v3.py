#!/usr/bin/env python3
"""Ghost タグ v3.0 セットアップスクリプト

新タクソノミー v3.0 (力学16 × イベント19 × ジャンル12) のタグを Ghost に作成する。
既存タグと重複する場合はスキップ。

使い方:
  python3 ghost_tag_setup_v3.py [--dry-run]
"""

import json
import time
import hashlib
import hmac
import base64
import sys
import os

# --- Ghost API設定（VPS上の /opt/cron-env.sh から読み込み） ---
GHOST_URL = "https://nowpattern.com"
GHOST_API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")

# cron-env.sh から読み込み（VPS上で実行時）
if not GHOST_API_KEY:
    try:
        with open("/opt/cron-env.sh") as f:
            for line in f:
                if "NOWPATTERN_GHOST_ADMIN_API_KEY" in line:
                    GHOST_API_KEY = line.split("=", 1)[1].strip().strip("'").strip('"')
                    break
    except FileNotFoundError:
        pass

if not GHOST_API_KEY:
    print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not found")
    sys.exit(1)


def make_jwt(api_key):
    key_id, secret = api_key.split(":")
    iat = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iat": iat, "exp": iat + 300, "aud": "/admin/"}
    def b64url(data):
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
    h = b64url(json.dumps(header).encode())
    p = b64url(json.dumps(payload).encode())
    sig = hmac.new(bytes.fromhex(secret), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{b64url(sig)}"


# --- v3.0 タクソノミー定義 ---

# 新しいイベントタグ（Ghost上に存在しない4つ）
NEW_EVENT_TAGS = [
    {"name": "Deal & Restructuring", "slug": "event-deal"},
    {"name": "Competition & Rivalry", "slug": "event-competition"},
    {"name": "Scandal & Trust Crisis", "slug": "event-trust"},
    {"name": "Social Change & Opinion", "slug": "event-social-shift"},
]

# 新しい力学タグ v3.0（全16個 — 既存と名前/slugが合わないものを作成）
V3_DYNAMICS_TAGS = [
    # 支配
    {"name": "Platform Power", "slug": "p-platform"},
    {"name": "Regulatory Capture", "slug": "p-capture"},
    {"name": "Narrative War", "slug": "p-narrative"},
    {"name": "Imperial Overreach", "slug": "p-overreach"},
    # 対立
    {"name": "Escalation Spiral", "slug": "p-escalation"},
    {"name": "Alliance Strain", "slug": "p-alliance"},
    {"name": "Path Dependency", "slug": "p-path-dep"},
    {"name": "Backlash Pendulum", "slug": "p-backlash"},
    # 崩壊
    {"name": "Institutional Decay", "slug": "p-decay"},
    {"name": "Coordination Failure", "slug": "p-coord-fail"},
    {"name": "Moral Hazard", "slug": "p-moral-hazard"},
    {"name": "Contagion Cascade", "slug": "p-contagion"},
    # 転換
    {"name": "Shock Doctrine", "slug": "p-shock"},
    {"name": "Tech Leapfrog", "slug": "p-leapfrog"},
    {"name": "Winner Takes All", "slug": "p-winner"},
    {"name": "Legitimacy Void", "slug": "p-legitimacy"},
]


def main():
    import urllib3
    urllib3.disable_warnings()
    import requests

    dry_run = "--dry-run" in sys.argv
    token = make_jwt(GHOST_API_KEY)
    headers = {
        "Authorization": f"Ghost {token}",
        "Content-Type": "application/json",
    }

    # 1. 既存タグ取得
    r = requests.get(
        f"{GHOST_URL}/ghost/api/admin/tags/?limit=all",
        headers=headers, verify=False, timeout=30
    )
    existing = {t["slug"]: t for t in r.json().get("tags", [])}
    print(f"Existing tags: {len(existing)}")

    # 2. 新タグ作成
    all_new_tags = NEW_EVENT_TAGS + V3_DYNAMICS_TAGS
    created = 0
    skipped = 0

    for tag_def in all_new_tags:
        slug = tag_def["slug"]
        name = tag_def["name"]

        if slug in existing:
            # slug一致 → 名前が違う場合はUPDATE
            old_name = existing[slug]["name"]
            if old_name != name:
                if dry_run:
                    print(f"  [DRY-RUN] RENAME: '{old_name}' -> '{name}' (slug: {slug})")
                else:
                    tag_id = existing[slug]["id"]
                    r = requests.put(
                        f"{GHOST_URL}/ghost/api/admin/tags/{tag_id}/",
                        json={"tags": [{"name": name}]},
                        headers=headers, verify=False, timeout=30
                    )
                    if r.status_code == 200:
                        print(f"  RENAMED: '{old_name}' -> '{name}' (slug: {slug})")
                        created += 1
                    else:
                        print(f"  ERROR renaming {slug}: {r.status_code} {r.text[:200]}")
            else:
                print(f"  SKIP: '{name}' (slug: {slug}) already exists")
                skipped += 1
        else:
            # slug不一致 → 新規作成
            if dry_run:
                print(f"  [DRY-RUN] CREATE: '{name}' (slug: {slug})")
            else:
                r = requests.post(
                    f"{GHOST_URL}/ghost/api/admin/tags/",
                    json={"tags": [{"name": name, "slug": slug}]},
                    headers=headers, verify=False, timeout=30
                )
                if r.status_code == 201:
                    print(f"  CREATED: '{name}' (slug: {slug})")
                    created += 1
                else:
                    print(f"  ERROR creating {slug}: {r.status_code} {r.text[:200]}")

    print(f"\nDone: {created} created/renamed, {skipped} skipped")

    # 3. 旧タグのリスト（参考表示 — NEO-ONEレビュー完了後に削除予定）
    old_slugs = [
        "p-exit-game", "p-institutional-rot", "p-systemic-fragility",
        "p-financial-coercion", "p-capital-flight", "p-blowback",
        "p-resource-power", "p-silent-crisis", "p-collective-failure",
        "p-deterrence-failure",
    ]
    print("\n--- 旧タグ（記事レビュー完了後に削除予定） ---")
    for slug in old_slugs:
        if slug in existing:
            t = existing[slug]
            print(f"  {t['name']} (slug: {slug}, posts: {t.get('count', {}).get('posts', '?')})")


if __name__ == "__main__":
    main()
