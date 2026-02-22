#!/usr/bin/env python3
"""
X ツイート収集スクリプト — Nowpattern Breaking Pipeline 起点

30+メディアアカウントの最新ツイートを巡回し、
キーワードスコアリング + エンゲージメント閾値でフィルタして
breaking_queue.json に保存する。

使い方:
  python3 x_tweet_collector.py              # 通常実行
  python3 x_tweet_collector.py --dry-run    # 収集のみ、キュー書き込みなし
  python3 x_tweet_collector.py --max 50     # 最大50ツイートをキューに追加

cron: */10 * * * * source /opt/cron-env.sh && python3 /opt/shared/scripts/x_tweet_collector.py
"""

import asyncio
import json
import os
import sys
import time
import argparse
from datetime import datetime, timezone, timedelta

COOKIES_FILE = "/opt/.x-cookies.json"
QUEUE_FILE = "/opt/shared/scripts/breaking_queue.json"
POSTED_FILE = "/opt/shared/scripts/breaking_posted.json"
MAX_QUEUE = 100
REQUEST_DELAY = 20  # 秒（50 req/15min 制限を守る）

# =====================================================================
# 巡回対象メディアアカウント
# =====================================================================
MEDIA_ACCOUNTS = [
    # ===== 日本語メディア =====
    {"account": "nhk_news", "lang": "ja", "cat": "総合"},
    {"account": "coin_post", "lang": "ja", "cat": "暗号資産"},
    {"account": "JpCointelegraph", "lang": "ja", "cat": "暗号資産"},
    {"account": "Nikkei", "lang": "ja", "cat": "経済"},
    {"account": "YahooNewsTopics", "lang": "ja", "cat": "総合"},
    # ===== 英語 — 総合ニュース =====
    {"account": "Reuters", "lang": "en", "cat": "総合"},
    {"account": "BBCWorld", "lang": "en", "cat": "総合"},
    {"account": "AJEnglish", "lang": "en", "cat": "国際"},
    {"account": "guardian", "lang": "en", "cat": "総合"},
    {"account": "WSJ", "lang": "en", "cat": "経済"},
    {"account": "AP", "lang": "en", "cat": "総合"},
    {"account": "TIME", "lang": "en", "cat": "総合"},
    # ===== 英語 — 政治・地政学 =====
    {"account": "thehill", "lang": "en", "cat": "政治"},
    {"account": "ForeignPolicy", "lang": "en", "cat": "地政学"},
    # ===== 英語 — テック・AI =====
    {"account": "techreview", "lang": "en", "cat": "AI"},
    {"account": "TechCrunch", "lang": "en", "cat": "AI"},
    # ===== 英語 — 暗号資産 =====
    {"account": "CoinDesk", "lang": "en", "cat": "暗号資産"},
    {"account": "Cointelegraph", "lang": "en", "cat": "暗号資産"},
    {"account": "WatcherGuru", "lang": "en", "cat": "暗号資産"},
    # ===== 英語 — 経済 =====
    {"account": "CNBC", "lang": "en", "cat": "経済"},
    {"account": "FT", "lang": "en", "cat": "経済"},
    # ===== 速報系 =====
    {"account": "MarioNawfal", "lang": "en", "cat": "速報"},
]

# =====================================================================
# キーワードスコアリング
# =====================================================================
KEYWORDS = {
    "AI": ["AI", "artificial intelligence", "LLM", "AGI", "ChatGPT", "Claude",
           "Gemini", "OpenAI", "Anthropic", "機械学習", "生成AI", "人工知能",
           "neural network", "deep learning", "GPT", "automation"],
    "暗号資産": ["bitcoin", "BTC", "crypto", "blockchain", "Ethereum", "ETH",
                "stablecoin", "DeFi", "NFT", "Web3", "CBDC", "ビットコイン",
                "暗号資産", "仮想通貨", "ステーブルコイン"],
    "地政学": ["geopolitics", "military", "Taiwan", "Ukraine", "sanctions",
              "NATO", "nuclear", "missile", "地政学", "安全保障", "軍事",
              "制裁", "紛争", "戦争"],
    "政治": ["politics", "election", "president", "Trump", "congress",
            "legislation", "政治", "選挙", "政府", "大統領", "首相"],
    "経済": ["economy", "inflation", "interest rate", "Fed", "GDP",
            "recession", "tariff", "経済", "金融", "インフレ", "金利",
            "関税", "半導体"],
}

# エンゲージメント閾値（最低いいね数）
MIN_LIKES = 10


def score_tweet(text, cat):
    """ツイートのキーワードスコアを計算"""
    score = 0
    text_lower = text.lower()

    for category, words in KEYWORDS.items():
        for word in words:
            if word.lower() in text_lower:
                score += 2 if category == cat else 1

    return score


def load_queue():
    """既存キューを読み込む"""
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_posted():
    """投稿済みリストを読み込む"""
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_queue(queue):
    """キューを保存"""
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def is_duplicate(tweet_id, queue, posted):
    """重複チェック"""
    existing_ids = {item.get("tweet_id") for item in queue}
    posted_ids = {item.get("tweet_id") for item in posted}
    return tweet_id in existing_ids or tweet_id in posted_ids


async def collect_tweets(dry_run=False, max_queue=MAX_QUEUE):
    """メディアアカウントからツイートを収集"""
    try:
        from twikit import Client
    except ImportError:
        print("ERROR: twikit がインストールされていません。pip install twikit を実行してください。")
        sys.exit(1)

    client = Client("en-US")

    if not os.path.exists(COOKIES_FILE):
        print(f"ERROR: Cookie ファイルが見つかりません: {COOKIES_FILE}")
        sys.exit(1)

    client.load_cookies(COOKIES_FILE)
    print(f"📂 Cookie 読み込み完了")

    queue = load_queue()
    posted = load_posted()
    pending_count = len([q for q in queue if q.get("status") == "pending"])
    print(f"📋 現在のキュー: {len(queue)} 件（うち pending: {pending_count}）")

    candidates = []
    errors = 0

    for i, media in enumerate(MEDIA_ACCOUNTS):
        account = media["account"]
        lang = media["lang"]
        cat = media["cat"]

        print(f"  [{i+1}/{len(MEDIA_ACCOUNTS)}] @{account} を検索中...")

        try:
            tweets = await client.search_tweet(
                f"from:{account}",
                "Latest",
                count=20
            )

            for tweet in tweets:
                tweet_id = str(tweet.id)

                if is_duplicate(tweet_id, queue, posted):
                    continue

                likes = getattr(tweet, "favorite_count", 0) or 0
                if likes < MIN_LIKES:
                    continue

                text = getattr(tweet, "text", "") or ""
                score = score_tweet(text, cat)

                # URLを抽出
                urls = []
                if hasattr(tweet, "urls") and tweet.urls:
                    urls = [u for u in tweet.urls if u]

                screen_name = getattr(tweet.user, "screen_name", account) if hasattr(tweet, "user") else account
                tweet_url = f"https://x.com/{screen_name}/status/{tweet_id}"

                candidates.append({
                    "tweet_id": tweet_id,
                    "tweet_url": tweet_url,
                    "account": account,
                    "lang": lang,
                    "cat": cat,
                    "text": text[:500],
                    "likes": likes,
                    "retweets": getattr(tweet, "retweet_count", 0) or 0,
                    "replies": getattr(tweet, "reply_count", 0) or 0,
                    "score": score,
                    "article_urls": urls[:3],
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "status": "pending",
                })

            print(f"    -> {len(tweets) if tweets else 0} ツイート取得")

        except Exception as e:
            print(f"    -> ERROR: {e}")
            errors += 1

        # レート制限を守る
        if i < len(MEDIA_ACCOUNTS) - 1:
            await asyncio.sleep(REQUEST_DELAY)

    # スコア + いいね数でソート（高い順）
    candidates.sort(key=lambda x: (x["score"], x["likes"]), reverse=True)

    # 上限まで切り詰め
    slots_available = max_queue - pending_count
    new_items = candidates[:max(0, slots_available)]

    print()
    print(f"=== 収集結果 ===")
    print(f"  巡回アカウント: {len(MEDIA_ACCOUNTS)}")
    print(f"  候補ツイート: {len(candidates)}")
    print(f"  キュー追加: {len(new_items)}")
    print(f"  エラー: {errors}")

    if new_items:
        print()
        print("--- 追加するツイート（上位10件） ---")
        for item in new_items[:10]:
            print(f"  [{item['score']}点 / {item['likes']}❤️] @{item['account']}: {item['text'][:80]}...")

    if not dry_run and new_items:
        queue.extend(new_items)
        save_queue(queue)
        print(f"\n✅ {len(new_items)} 件をキューに追加しました")
    elif dry_run:
        print(f"\n🔍 dry-run モード: キューへの書き込みはスキップしました")

    return new_items


def main():
    parser = argparse.ArgumentParser(description="X ツイート収集（Nowpattern Breaking Pipeline）")
    parser.add_argument("--dry-run", action="store_true", help="収集のみ、キュー書き込みなし")
    parser.add_argument("--max", type=int, default=MAX_QUEUE, help=f"最大キュー数（デフォルト: {MAX_QUEUE}）")
    args = parser.parse_args()

    asyncio.run(collect_tweets(dry_run=args.dry_run, max_queue=args.max))


if __name__ == "__main__":
    main()
