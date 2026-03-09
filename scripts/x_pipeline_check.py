#!/usr/bin/env python3
"""
x_pipeline_check.py — X配信パイプライン状態確認 + テスト投稿

VPSで実行:
  python3 /opt/shared/scripts/x_pipeline_check.py --check     # 認証状態のみ確認
  python3 /opt/shared/scripts/x_pipeline_check.py --test      # テスト投稿（--dry-run付き）
  python3 /opt/shared/scripts/x_pipeline_check.py --post "テキスト"  # 実投稿
"""

import os
import sys
import json

CRON_ENV = "/opt/cron-env.sh"

REQUIRED_KEYS = [
    "TWITTER_API_KEY",
    "TWITTER_API_SECRET",
    "TWITTER_ACCESS_TOKEN",
    "TWITTER_ACCESS_TOKEN_SECRET",
]


def load_env():
    env = {}
    if not os.path.exists(CRON_ENV):
        print(f"ERROR: {CRON_ENV} not found")
        return env
    with open(CRON_ENV) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                k, v = line[7:].split("=", 1)
                env[k] = v.strip().strip("\"'")
    return env


def check_credentials():
    """X API認証情報の存在確認"""
    print("=== X API Credentials Check ===\n")
    env = load_env()

    all_ok = True
    for key in REQUIRED_KEYS:
        val = env.get(key, "")
        if val:
            print(f"  ✅ {key}: {val[:8]}...{val[-4:]}")
        else:
            print(f"  ❌ {key}: NOT SET")
            all_ok = False

    if all_ok:
        print("\n  All credentials present. Ready to post.")
    else:
        print("\n  Missing credentials. Add them to /opt/cron-env.sh:")
        print('  export TWITTER_API_KEY="your_key"')
        print('  export TWITTER_API_SECRET="your_secret"')
        print('  export TWITTER_ACCESS_TOKEN="your_token"')
        print('  export TWITTER_ACCESS_TOKEN_SECRET="your_token_secret"')
        print("\n  Get credentials at: https://developer.x.com/en/portal/dashboard")

    return all_ok, env


def verify_auth(env):
    """X API v2でアカウント情報を取得して認証を検証"""
    print("\n=== Verifying X API auth ===\n")
    try:
        from requests_oauthlib import OAuth1
        import requests
    except ImportError:
        print("  ERROR: pip install requests-oauthlib")
        return False

    auth = OAuth1(
        env["TWITTER_API_KEY"],
        env["TWITTER_API_SECRET"],
        env["TWITTER_ACCESS_TOKEN"],
        env["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    resp = requests.get(
        "https://api.twitter.com/2/users/me",
        auth=auth,
        timeout=15,
    )
    if resp.status_code == 200:
        user = resp.json().get("data", {})
        print(f"  ✅ Authenticated as: @{user.get('username', '?')} (id: {user.get('id', '?')})")
        print(f"     Name: {user.get('name', '?')}")
        return True
    else:
        print(f"  ❌ Auth failed: HTTP {resp.status_code}")
        print(f"     {resp.text[:300]}")
        return False


def test_post(env, text=None):
    """テスト投稿"""
    if not text:
        text = "🔬 Nowpattern prediction system test — this tweet will be deleted.\n\n#Nowpattern #ニュース分析"

    print(f"\n=== Test Post ===\n")
    print(f"  Text: {text[:100]}...")

    try:
        from requests_oauthlib import OAuth1
        import requests
    except ImportError:
        print("  ERROR: pip install requests-oauthlib")
        return

    auth = OAuth1(
        env["TWITTER_API_KEY"],
        env["TWITTER_API_SECRET"],
        env["TWITTER_ACCESS_TOKEN"],
        env["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    resp = requests.post(
        "https://api.twitter.com/2/tweets",
        auth=auth,
        json={"text": text},
        timeout=30,
    )
    if resp.status_code in (200, 201):
        tid = resp.json().get("data", {}).get("id", "")
        print(f"  ✅ Posted! https://x.com/nowpattern/status/{tid}")
    else:
        print(f"  ❌ Failed: HTTP {resp.status_code}")
        print(f"     {resp.text[:500]}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="X pipeline check")
    parser.add_argument("--check", action="store_true", help="Check credentials only")
    parser.add_argument("--test", action="store_true", help="Verify auth + test post")
    parser.add_argument("--post", default="", help="Post specific text")
    args = parser.parse_args()

    ok, env = check_credentials()
    if not ok:
        sys.exit(1)

    if args.check:
        verify_auth(env)
    elif args.test:
        if verify_auth(env):
            test_post(env)
    elif args.post:
        verify_auth(env)
        test_post(env, text=args.post)
    else:
        verify_auth(env)


if __name__ == "__main__":
    main()
