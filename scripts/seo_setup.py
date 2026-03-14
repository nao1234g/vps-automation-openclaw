#!/usr/bin/env python3
"""
seo_setup.py — nowpattern.com SEO初期設定 + IndexNow通知

VPSで実行:
  python3 /opt/shared/scripts/seo_setup.py --check          # 現状チェックのみ
  python3 /opt/shared/scripts/seo_setup.py --indexnow        # Bing/Yandexに全URLを通知
  python3 /opt/shared/scripts/seo_setup.py --setup-gsc-html  # GSC HTML認証ファイル配置

前提:
  - Ghost CMSが稼働中（nowpattern.com）
  - /opt/cron-env.sh にGhost Admin API Keyあり
  - Caddyが /var/www/nowpattern/ をドキュメントルートとして配信
"""

import json
import os
import sys
import hashlib
import secrets
import urllib.request
import urllib.parse
import ssl

GHOST_URL = "https://nowpattern.com"
SITEMAP_URL = f"{GHOST_URL}/sitemap.xml"
CADDY_WEBROOT = "/var/www/nowpattern/content"
INDEXNOW_KEY_PATH = "/var/www/nowpattern/content"


def check_seo():
    """現在のSEO状態をチェック"""
    print("=== SEO Check ===\n")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    checks = [
        ("sitemap.xml", f"{GHOST_URL}/sitemap.xml"),
        ("robots.txt", f"{GHOST_URL}/robots.txt"),
        ("sitemap-posts.xml", f"{GHOST_URL}/sitemap-posts.xml"),
    ]

    for name, url in checks:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Nowpattern-SEO/1.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                status = resp.status
                size = len(resp.read())
            print(f"  ✅ {name}: HTTP {status} ({size} bytes)")
        except Exception as e:
            print(f"  ❌ {name}: {e}")

    # Check for GSC verification
    gsc_files = [
        "/var/www/nowpattern/content/google*.html",
    ]
    print(f"\n  GSC verification: ", end="")
    import glob
    found = glob.glob("/var/www/nowpattern/content/google*.html")
    if found:
        print(f"✅ Found: {found}")
    else:
        print("❌ Not found. Run --setup-gsc-html after getting verification code from GSC.")

    # Check IndexNow key
    print(f"  IndexNow key: ", end="")
    key_files = glob.glob(f"{INDEXNOW_KEY_PATH}/*.txt")
    indexnow_keys = [f for f in key_files if len(os.path.basename(f).replace('.txt', '')) == 32]
    if indexnow_keys:
        print(f"✅ Found: {indexnow_keys[0]}")
    else:
        print("❌ Not found. Run --indexnow to generate and submit.")


def get_all_urls():
    """sitemap-posts.xmlから全URLを取得"""
    import xml.etree.ElementTree as ET
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    urls = []
    for sitemap in ["sitemap-posts.xml", "sitemap-pages.xml"]:
        try:
            req = urllib.request.Request(
                f"{GHOST_URL}/{sitemap}",
                headers={"User-Agent": "Nowpattern-SEO/1.0"}
            )
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            for loc in root.findall(".//sm:loc", ns):
                if loc.text:
                    urls.append(loc.text.strip())
        except Exception as e:
            print(f"  WARN: {sitemap}: {e}")
    return urls


def setup_indexnow():
    """IndexNow APIキーを生成し、Bing/Yandexに全URLを通知"""
    print("=== IndexNow Setup ===\n")

    # Generate or load key
    key_file = os.path.join(INDEXNOW_KEY_PATH, "indexnow_key.txt")
    if os.path.exists(key_file):
        with open(key_file) as f:
            key = f.read().strip()
        print(f"  Using existing key: {key[:8]}...")
    else:
        key = secrets.token_hex(16)
        # Write key file to webroot (must be accessible at /{key}.txt)
        key_url_file = os.path.join(INDEXNOW_KEY_PATH, f"{key}.txt")
        with open(key_url_file, "w") as f:
            f.write(key)
        with open(key_file, "w") as f:
            f.write(key)
        print(f"  Generated new key: {key[:8]}...")
        print(f"  Key file: {key_url_file}")

    # Get all URLs
    urls = get_all_urls()
    print(f"  Found {len(urls)} URLs to submit")

    if not urls:
        print("  No URLs found. Aborting.")
        return

    # Submit to IndexNow (Bing endpoint)
    payload = {
        "host": "nowpattern.com",
        "key": key,
        "keyLocation": f"https://nowpattern.com/{key}.txt",
        "urlList": urls[:10000],
    }

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            print(f"  ✅ IndexNow submitted: HTTP {resp.status} ({len(urls)} URLs)")
    except urllib.error.HTTPError as e:
        print(f"  Response: HTTP {e.code}")
        if e.code == 200 or e.code == 202:
            print(f"  ✅ IndexNow accepted ({len(urls)} URLs)")
        else:
            print(f"  ❌ IndexNow failed: {e.read().decode()[:200]}")
    except Exception as e:
        print(f"  ❌ IndexNow failed: {e}")


def setup_gsc_html(verification_code=""):
    """Google Search Console HTML認証ファイルを配置"""
    if not verification_code:
        print("Usage: --setup-gsc-html --code google1234567890abcdef.html")
        print("  1. Go to https://search.google.com/search-console")
        print("  2. Add property: nowpattern.com")
        print("  3. Choose 'HTML file' verification method")
        print("  4. Copy the filename (e.g., google1234567890abcdef.html)")
        print("  5. Run: python3 seo_setup.py --setup-gsc-html --code <filename>")
        return

    filepath = os.path.join(CADDY_WEBROOT, verification_code)
    content = f"google-site-verification: {verification_code}"
    with open(filepath, "w") as f:
        f.write(content)
    print(f"  ✅ Created: {filepath}")
    print(f"  Verify at: {GHOST_URL}/{verification_code}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SEO setup for nowpattern.com")
    parser.add_argument("--check", action="store_true", help="Check current SEO state")
    parser.add_argument("--indexnow", action="store_true", help="Submit all URLs via IndexNow")
    parser.add_argument("--setup-gsc-html", action="store_true", help="Setup GSC HTML verification")
    parser.add_argument("--code", default="", help="GSC verification filename")
    args = parser.parse_args()

    if args.check:
        check_seo()
    elif args.indexnow:
        setup_indexnow()
    elif args.setup_gsc_html:
        setup_gsc_html(args.code)
    else:
        check_seo()
        print("\n--- Run with --indexnow to submit URLs to Bing/Yandex ---")
        print("--- Run with --setup-gsc-html for Google verification ---")


if __name__ == "__main__":
    main()
