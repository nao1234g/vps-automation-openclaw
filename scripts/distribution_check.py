#!/usr/bin/env python3
"""
distribution_check.py — 全配信チャネルの状態を一括確認

VPSで実行:
  python3 /opt/shared/scripts/distribution_check.py

確認項目:
  1. Ghost CMS — 記事数、最新記事
  2. X API — 認証状態
  3. note — Cookie有効性
  4. Substack — Cookie/API有効性
  5. Telegram — Bot接続確認
"""

import os
import sys
import json
import ssl
import urllib.request

CRON_ENV = "/opt/cron-env.sh"
GHOST_URL = "https://nowpattern.com"


def load_env():
    env = {}
    if os.path.exists(CRON_ENV):
        with open(CRON_ENV) as f:
            for line in f:
                line = line.strip()
                if line.startswith("export ") and "=" in line:
                    k, v = line[7:].split("=", 1)
                    env[k] = v.strip().strip("\"'")
    return env


def check_ghost(env):
    print("\n=== 1. Ghost CMS ===")
    api_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not api_key:
        print("  ❌ NOWPATTERN_GHOST_ADMIN_API_KEY not set")
        return
    try:
        import hmac, hashlib, base64
        from datetime import datetime, timezone
        kid, secret = api_key.split(":")
        iat = int(datetime.now(timezone.utc).timestamp())
        header = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","kid":kid,"typ":"JWT"}).encode()).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(json.dumps({"iat":iat,"exp":iat+300,"aud":"/admin/"}).encode()).rstrip(b"=").decode()
        sig = base64.urlsafe_b64encode(hmac.new(bytes.fromhex(secret),f"{header}.{payload}".encode(),hashlib.sha256).digest()).rstrip(b"=").decode()
        token = f"{header}.{payload}.{sig}"

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            f"{GHOST_URL}/ghost/api/admin/posts/?limit=1&fields=title,published_at",
            headers={"Authorization": f"Ghost {token}", "Accept-Version": "v5.0"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read())
        total = data.get("meta", {}).get("pagination", {}).get("total", "?")
        latest = data.get("posts", [{}])[0]
        print(f"  ✅ Ghost OK — {total}記事")
        print(f"     最新: {latest.get('title', '?')[:50]} ({latest.get('published_at', '?')[:10]})")
    except Exception as e:
        print(f"  ❌ Ghost error: {e}")


def check_x(env):
    print("\n=== 2. X API ===")
    keys = ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET"]
    missing = [k for k in keys if not env.get(k)]
    if missing:
        print(f"  ❌ Missing: {', '.join(missing)}")
        return
    try:
        from requests_oauthlib import OAuth1
        import requests
        auth = OAuth1(env["TWITTER_API_KEY"], env["TWITTER_API_SECRET"],
                      env["TWITTER_ACCESS_TOKEN"], env["TWITTER_ACCESS_TOKEN_SECRET"])
        resp = requests.get("https://api.twitter.com/2/users/me", auth=auth, timeout=10)
        if resp.status_code == 200:
            u = resp.json().get("data", {})
            print(f"  ✅ X OK — @{u.get('username', '?')}")
        else:
            print(f"  ❌ X auth failed: HTTP {resp.status_code}")
    except ImportError:
        print("  ⚠️  requests_oauthlib not installed")
    except Exception as e:
        print(f"  ❌ X error: {e}")


def check_note(env):
    print("\n=== 3. note.com ===")
    cookie_file = "/opt/.note-cookies.json"
    if os.path.exists(cookie_file):
        mtime = os.path.getmtime(cookie_file)
        from datetime import datetime
        age_days = (datetime.now().timestamp() - mtime) / 86400
        print(f"  Cookie file: {cookie_file} (age: {age_days:.0f} days)")
        if age_days > 30:
            print("  ⚠️  Cookie may be expired (>30 days). Re-login may be needed.")
        else:
            print("  ✅ Cookie file recent")
    else:
        print(f"  ❌ Cookie file not found: {cookie_file}")

    # Check queue
    queue_file = "/opt/shared/note-queue.json"
    if os.path.exists(queue_file):
        with open(queue_file) as f:
            queue = json.load(f)
        pending = [q for q in queue if q.get("status") == "pending"]
        print(f"  Queue: {len(pending)} pending / {len(queue)} total")
    else:
        print(f"  Queue: not found at {queue_file}")


def check_substack(env):
    print("\n=== 4. Substack ===")
    cookies = env.get("SUBSTACK_COOKIES", "")
    if cookies:
        print(f"  ✅ SUBSTACK_COOKIES set ({len(cookies)} chars)")
    else:
        print("  ❌ SUBSTACK_COOKIES not set in cron-env")

    # Check container
    try:
        import subprocess
        r = subprocess.run(["docker", "ps", "--filter", "name=substack", "--format", "{{.Names}} {{.Status}}"],
                          capture_output=True, text=True, timeout=5)
        if r.stdout.strip():
            print(f"  ✅ Container: {r.stdout.strip()}")
        else:
            print("  ❌ substack container not running")
    except Exception:
        print("  ⚠️  Cannot check Docker (not available)")


def check_telegram(env):
    print("\n=== 5. Telegram ===")
    bot_token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if not bot_token:
        print("  ❌ TELEGRAM_BOT_TOKEN not set")
        return
    if not chat_id:
        print("  ❌ TELEGRAM_CHAT_ID not set")
        return
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if data.get("ok"):
            bot = data["result"]
            print(f"  ✅ Bot: @{bot.get('username', '?')} ({bot.get('first_name', '?')})")
        else:
            print(f"  ❌ Bot API error: {data}")
    except Exception as e:
        print(f"  ❌ Telegram error: {e}")


def main():
    print("=" * 50)
    print("  Nowpattern Distribution Channel Status")
    print("=" * 50)

    env = load_env()
    check_ghost(env)
    check_x(env)
    check_note(env)
    check_substack(env)
    check_telegram(env)

    print("\n" + "=" * 50)
    print("  Done. Fix ❌ items before starting distribution.")
    print("=" * 50)


if __name__ == "__main__":
    main()
