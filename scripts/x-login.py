#!/usr/bin/env python3
"""
X (Twitter) 初回ログインスクリプト（Twikit）
使い方: python3 x-login.py
"""

import asyncio
from twikit import Client
import sys

COOKIES_FILE = '/opt/.x-cookies.json'

async def login():
    """X にログインして Cookie を保存"""
    client = Client('en-US')

    # ログイン情報（環境変数または引数から取得）
    username = sys.argv[1] if len(sys.argv) > 1 else input('ユーザー名: ')
    email = sys.argv[2] if len(sys.argv) > 2 else input('メールアドレス: ')
    password = sys.argv[3] if len(sys.argv) > 3 else input('パスワード: ')

    print('🔐 X にログイン中...')

    try:
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password
        )

        # Cookie を保存
        client.save_cookies(COOKIES_FILE)
        print(f'✅ ログイン成功！Cookie を保存しました: {COOKIES_FILE}')

    except Exception as e:
        print(f'❌ ログイン失敗: {e}')
        raise

if __name__ == '__main__':
    asyncio.run(login())
