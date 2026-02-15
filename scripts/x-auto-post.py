#!/usr/bin/env python3
"""
X (Twitter) 自動投稿スクリプト（Twikit）
使い方: python3 x-auto-post.py "ツイート内容"
"""

import sys
import asyncio
from twikit import Client
import os

COOKIES_FILE = '/opt/.x-cookies.json'

async def post_tweet(text):
    """ツイートを投稿"""
    client = Client('en-US')

    print('🔐 X にログイン中...')

    # Cookie ファイルが存在する場合は Cookie でログイン
    if os.path.exists(COOKIES_FILE):
        print('📂 Cookie ファイルを読み込み中...')
        client.load_cookies(COOKIES_FILE)
    else:
        print('⚠️  Cookie ファイルが見つかりません')
        print('初回ログインが必要です。x-login.py を実行してください。')
        sys.exit(1)

    try:
        print('🐦 ツイートを投稿中...')
        tweet = await client.create_tweet(text=text)
        print(f'✅ ツイート投稿完了！')
        print(f'📎 URL: https://x.com/aisaintel/status/{tweet.id}')

    except Exception as e:
        print(f'❌ エラー発生: {e}')
        print('⚠️  Cookie が期限切れの可能性があります。x-login.py を再実行してください。')
        raise

def main():
    if len(sys.argv) < 2:
        print('使い方: python3 x-auto-post.py "ツイート内容"')
        sys.exit(1)

    tweet_text = sys.argv[1]
    asyncio.run(post_tweet(tweet_text))

if __name__ == '__main__':
    main()
