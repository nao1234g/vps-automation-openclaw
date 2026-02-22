#!/usr/bin/env python3
"""
X (Twitter) 自動投稿スクリプト（Twikit）
使い方:
  python3 x-auto-post.py "ツイート内容"
  python3 x-auto-post.py "ツイート内容" --quote-url "https://x.com/Reuters/status/123456"

引用リポスト: --quote-url で元ツイートURLを指定すると引用リポストになります。
ハッシュタグ自動付与: #Nowpattern と #ニュース分析 が含まれていなければ自動追加。
"""

import sys
import asyncio
import argparse
from twikit import Client
import os

COOKIES_FILE = '/opt/.x-cookies.json'

# ---------- 必須ハッシュタグ ----------
MANDATORY_HASHTAGS = ["#Nowpattern", "#ニュース分析"]


def enforce_hashtags(text: str) -> str:
    """必須ハッシュタグが欠けていれば末尾に追加する"""
    missing = [tag for tag in MANDATORY_HASHTAGS if tag not in text]
    if missing:
        text = text.rstrip() + "\n\n" + " ".join(missing)
        print(f'⚠️  必須ハッシュタグを自動追加: {" ".join(missing)}')
    return text


async def post_tweet(text, quote_url=None):
    """ツイートを投稿（quote_url指定時は引用リポスト）"""
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
        if quote_url:
            print(f'🔁 引用リポスト投稿中... (元: {quote_url})')
            tweet = await client.create_tweet(text=text, attachment_url=quote_url)
        else:
            print('🐦 ツイートを投稿中...')
            tweet = await client.create_tweet(text=text)
        print(f'✅ ツイート投稿完了！')
        print(f'📎 URL: https://x.com/nowpattern/status/{tweet.id}')

    except Exception as e:
        print(f'❌ エラー発生: {e}')
        print('⚠️  Cookie が期限切れの可能性があります。x-login.py を再実行してください。')
        raise

def main():
    parser = argparse.ArgumentParser(description='X (Twitter) 自動投稿')
    parser.add_argument('text', help='ツイート内容')
    parser.add_argument('--quote-url', help='引用リポスト元のツイートURL')
    args = parser.parse_args()

    tweet_text = args.text

    # 必須ハッシュタグを強制付与
    tweet_text = enforce_hashtags(tweet_text)

    asyncio.run(post_tweet(tweet_text, quote_url=args.quote_url))

if __name__ == '__main__':
    main()
