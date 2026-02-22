#!/usr/bin/env python3
"""
Firefox から X (twitter.com / x.com) の Cookie を抽出して
Twikit 形式の JSON ファイルに保存するスクリプト

使い方:
  1. VPS のデスクトップ環境で Firefox を開いて x.com にログイン
  2. Firefox を閉じる
  3. python3 extract_x_cookies.py

出力: /opt/.x-cookies.json（Twikit の load_cookies で読み込み可能）
"""

import json
import os
import glob
import sqlite3
import shutil
import tempfile
import sys

OUTPUT_FILE = "/opt/.x-cookies.json"

# Firefox のプロファイルディレクトリ候補
FIREFOX_PROFILE_DIRS = [
    os.path.expanduser("~/.mozilla/firefox/"),
    "/home/neocloop/.mozilla/firefox/",
    "/root/.mozilla/firefox/",
]


def find_cookies_db():
    """Firefox の cookies.sqlite を見つける"""
    for base_dir in FIREFOX_PROFILE_DIRS:
        if not os.path.isdir(base_dir):
            continue

        # profiles.ini からデフォルトプロファイルを探す
        profiles_ini = os.path.join(base_dir, "profiles.ini")
        if os.path.exists(profiles_ini):
            with open(profiles_ini, "r") as f:
                content = f.read()
                # デフォルトプロファイルのパスを抽出
                for line in content.splitlines():
                    if line.startswith("Path="):
                        path = line.split("=", 1)[1]
                        cookie_db = os.path.join(base_dir, path, "cookies.sqlite")
                        if os.path.exists(cookie_db):
                            return cookie_db

        # パターンマッチでも探す
        matches = glob.glob(os.path.join(base_dir, "*.default*", "cookies.sqlite"))
        if matches:
            return matches[0]

    return None


def extract_cookies(db_path):
    """cookies.sqlite から x.com / twitter.com の Cookie を抽出"""
    # Firefox がロック中の場合に備えてコピーして読む
    tmp_dir = tempfile.mkdtemp()
    tmp_db = os.path.join(tmp_dir, "cookies.sqlite")
    shutil.copy2(db_path, tmp_db)

    try:
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        # x.com と twitter.com の両方のドメインからcookieを取得
        cursor.execute("""
            SELECT name, value, host
            FROM moz_cookies
            WHERE host LIKE '%x.com%'
               OR host LIKE '%twitter.com%'
            ORDER BY name
        """)

        cookies = {}
        for name, value, host in cursor.fetchall():
            cookies[name] = value

        conn.close()
        return cookies
    finally:
        os.remove(tmp_db)
        os.rmdir(tmp_dir)


def main():
    print("=== Firefox → Twikit Cookie 抽出ツール ===")
    print()

    db_path = find_cookies_db()
    if not db_path:
        print("ERROR: Firefox の cookies.sqlite が見つかりません")
        print()
        print("確認事項:")
        print("  1. Firefox で x.com にログイン済みか？")
        print("  2. Firefox を閉じたか？（開いているとDBがロックされることがあります）")
        print()
        print("検索パス:")
        for d in FIREFOX_PROFILE_DIRS:
            print(f"  {d}")
        sys.exit(1)

    print(f"📂 Cookie DB: {db_path}")

    cookies = extract_cookies(db_path)

    if not cookies:
        print("ERROR: x.com / twitter.com の Cookie が見つかりません")
        print("Firefox で x.com にログインしてから再実行してください")
        sys.exit(1)

    # 重要な Cookie が含まれているかチェック
    important_keys = ["auth_token", "ct0"]
    missing = [k for k in important_keys if k not in cookies]
    if missing:
        print(f"WARNING: 重要な Cookie が見つかりません: {', '.join(missing)}")
        print("X にログインしていない可能性があります")

    # 保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)

    print(f"✅ {len(cookies)} 個の Cookie を保存しました: {OUTPUT_FILE}")
    print()
    print("含まれる Cookie:")
    for name in sorted(cookies.keys()):
        value_preview = cookies[name][:20] + "..." if len(cookies[name]) > 20 else cookies[name]
        marker = " ⭐" if name in important_keys else ""
        print(f"  {name}: {value_preview}{marker}")

    print()
    print("次のステップ:")
    print("  python3 /opt/shared/scripts/x_tweet_collector.py --dry-run --max 5")


if __name__ == "__main__":
    main()
