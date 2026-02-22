#!/usr/bin/env python3
"""
X 引用リポスト専用スクリプト — Nowpattern Breaking Pipeline Phase 4
v3.0: リンクを本文に含める（2025年10月ペナルティ撤廃対応）

breaking_queue.json から「記事生成済み」のツイートを取り出し、
分析コメント + nowpattern.comリンク付きで引用リポスト。

v3.0変更点（2026-02-22）:
  - 2025年10月にXの外部リンクペナルティが撤廃された
  - リンク付き投稿のリーチが約8倍に回復
  - リプライ分離方式は不要になった → 本文にリンクを直接含める
  - クリック率も向上（リプライを開く手間が不要）

認証: OAuth1（公式Twitter API v2） — Cloudflareに弾かれない

使い方:
  python3 x_quote_repost.py              # 通常実行（1件投稿）
  python3 x_quote_repost.py --batch 5    # 5件まとめて投稿（ランダム間隔）
  python3 x_quote_repost.py --dry-run    # 投稿せずに確認のみ

cron: */5 * * * * source /opt/cron-env.sh && python3 /opt/shared/scripts/x_quote_repost.py
"""

import json
import os
import re
import sys
import time
import random
import argparse
from datetime import datetime, timezone

import requests
from requests_oauthlib import OAuth1

QUEUE_FILE = "/opt/shared/scripts/breaking_queue.json"
POSTED_FILE = "/opt/shared/scripts/breaking_posted.json"
POST_INTERVAL_MIN = 300   # 最小間隔: 5分
POST_INTERVAL_MAX = 1200  # 最大間隔: 20分（ランダム）
X_MAX_CHARS = 1400

MANDATORY_HASHTAGS = ["#Nowpattern", "#ニュース分析"]

DYNAMIC_HASHTAGS = {
    "地政学": {"ja": "#地政学", "en": "#Geopolitics"},
    "経済": {"ja": "#経済分析", "en": "#Economy"},
    "金融": {"ja": "#金融市場", "en": "#Finance"},
    "AI": {"ja": "#AI", "en": "#AI"},
    "暗号資産": {"ja": "#暗号資産", "en": "#Crypto"},
    "政治": {"ja": "#政治", "en": "#Politics"},
    "エネルギー": {"ja": "#エネルギー", "en": "#Energy"},
    "テック": {"ja": "#テック", "en": "#Tech"},
    "国際": {"ja": "#国際情勢", "en": "#WorldNews"},
    "総合": {"ja": "", "en": ""},
    "速報": {"ja": "#速報", "en": "#Breaking"},
}

TOPIC_KEYWORDS = {
    "Trump": {"ja": "#トランプ", "en": "#Trump"},
    "トランプ": {"ja": "#トランプ", "en": "#Trump"},
    "Bitcoin": {"ja": "#BTC", "en": "#Bitcoin"},
    "ビットコイン": {"ja": "#BTC", "en": "#Bitcoin"},
    "BTC": {"ja": "#BTC", "en": "#Bitcoin"},
    "Ethereum": {"ja": "#ETH", "en": "#Ethereum"},
    "ETH": {"ja": "#ETH", "en": "#Ethereum"},
    "EU": {"ja": "#EU", "en": "#EU"},
    "China": {"ja": "#中国", "en": "#China"},
    "中国": {"ja": "#中国", "en": "#China"},
    "Iran": {"ja": "#イラン", "en": "#Iran"},
    "イラン": {"ja": "#イラン", "en": "#Iran"},
    "Ukraine": {"ja": "#ウクライナ", "en": "#Ukraine"},
    "ウクライナ": {"ja": "#ウクライナ", "en": "#Ukraine"},
    "日銀": {"ja": "#日銀", "en": "#BOJ"},
    "BOJ": {"ja": "#日銀", "en": "#BOJ"},
    "Fed": {"ja": "#FRB", "en": "#Fed"},
    "OpenAI": {"ja": "#OpenAI", "en": "#OpenAI"},
    "tariff": {"ja": "#関税", "en": "#Tariffs"},
    "関税": {"ja": "#関税", "en": "#Tariffs"},
}


def build_hashtags(cat, lang, text=""):
    tags = list(MANDATORY_HASHTAGS)
    lang_key = "ja" if lang == "ja" else "en"
    cat_tag = DYNAMIC_HASHTAGS.get(cat, {}).get(lang_key, "")
    if cat_tag and cat_tag not in tags:
        tags.append(cat_tag)
    for keyword, tag_map in TOPIC_KEYWORDS.items():
        if keyword.lower() in text.lower():
            topic_tag = tag_map.get(lang_key, "")
            if topic_tag and topic_tag not in tags:
                tags.append(topic_tag)
                break
    return " ".join(t for t in tags if t)


def enforce_hashtags(text, cat="", lang="ja", source_text=""):
    hashtag_str = build_hashtags(cat, lang, source_text or text)
    new_tags = [t for t in hashtag_str.split() if t not in text]
    if new_tags:
        text = text.rstrip() + "\n\n" + " ".join(new_tags)
    return text


def extract_tweet_id(tweet_url):
    """tweet_url からtweet_idを抽出"""
    m = re.search(r'/status/(\d+)', tweet_url)
    return m.group(1) if m else None


def post_tweet(auth, text, quote_tweet_id=None, reply_to_id=None):
    """Twitter API v2 で投稿。quote_tweet_idがあれば引用リポスト、reply_to_idがあればリプライ。"""
    payload = {"text": text[:X_MAX_CHARS]}
    if quote_tweet_id:
        payload["quote_tweet_id"] = str(quote_tweet_id)
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": str(reply_to_id)}
    resp = requests.post(
        "https://api.twitter.com/2/tweets",
        auth=auth,
        json=payload,
        timeout=30
    )
    return resp


def load_queue():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_queue(queue):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def load_posted():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_posted(posted):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(posted, f, ensure_ascii=False, indent=2)


def get_ready_items(queue):
    return [q for q in queue if q.get("status") == "article_ready"]


def quote_repost(item, auth, dry_run=False):
    """1件の引用リポストを投稿（v3.0: リンクを本文に含める）

    2025年10月にXの外部リンクペナルティが撤廃されたため、
    分析コメント + nowpattern.comリンク + ハッシュタグを1投稿にまとめる。
    リプライ分離は不要（クリック率も向上）。
    """
    tweet_url = item.get("tweet_url", "")
    ghost_url = item.get("ghost_url", "")
    comment = item.get("x_comment", "")

    tweet_id = extract_tweet_id(tweet_url) if tweet_url else None

    if not tweet_id:
        print(f"  SKIP: tweet_id を抽出できません（url: {tweet_url}）")
        return False

    if not comment:
        cat = item.get("cat", "")
        text_preview = item.get("text", "")[:100]
        comment = f"📊 {cat} | 深層分析\n\n{text_preview}..."

    # v3.0: リンクを本文に直接含める（ペナルティ撤廃済み）
    cat = item.get("cat", "")
    lang = item.get("lang", "ja")
    source_text = item.get("text", "")

    if ghost_url:
        if lang == "ja":
            comment = comment.rstrip() + f"\n\n📖 深層分析の全文はこちら:\n{ghost_url}"
        else:
            comment = comment.rstrip() + f"\n\n📖 Full Deep Pattern analysis:\n{ghost_url}"

    comment = enforce_hashtags(comment, cat=cat, lang=lang, source_text=source_text)

    if len(comment) > X_MAX_CHARS:
        comment = comment[:X_MAX_CHARS - 3] + "..."

    if dry_run:
        print(f"  [DRY-RUN] 引用リポスト: {comment[:100]}...")
        print(f"            引用元: {tweet_url} (id={tweet_id})")
        if ghost_url:
            print(f"            リンク（本文内）: {ghost_url}")
        return True

    # v3.0: 1投稿で完結（分析 + リンク + ハッシュタグ）
    resp = post_tweet(auth, comment, quote_tweet_id=tweet_id)

    if resp.status_code == 201:
        data = resp.json().get("data", {})
        new_tweet_id = data.get("id", "")
        posted_url = f"https://x.com/aisaintel/status/{new_tweet_id}"
        print(f"  ✅ 引用リポスト完了: {posted_url}")
        item["posted_tweet_url"] = posted_url
        item["posted_at"] = datetime.now(timezone.utc).isoformat()
        return True
    elif resp.status_code == 403:
        try:
            error_detail = resp.json()
        except Exception:
            error_detail = resp.text[:200]
        print(f"  ❌ 403 Forbidden: {error_detail}")
        return False
    elif resp.status_code == 429:
        print(f"  ⚠️ レート制限（429）。次の実行で再試行します。")
        return False
    else:
        print(f"  ❌ 投稿失敗 HTTP {resp.status_code}: {resp.text[:200]}")
        return False


def run_quote_reposts(auth, batch_size=1, dry_run=False):
    queue = load_queue()
    posted = load_posted()
    ready = get_ready_items(queue)

    print(f"📋 キュー: {len(queue)} 件、article_ready: {len(ready)} 件")

    if not ready:
        print("引用リポスト対象がありません。")
        return

    posted_count = 0

    for item in ready[:batch_size]:
        success = quote_repost(item, auth, dry_run=dry_run)

        if success and not dry_run:
            item["status"] = "posted"
            posted.append(item)
            posted_count += 1

        if not dry_run and posted_count < batch_size and posted_count < len(ready):
            delay = random.randint(POST_INTERVAL_MIN, POST_INTERVAL_MAX)
            print(f"  ⏳ 次の投稿まで {delay // 60}分{delay % 60}秒待機（ランダム間隔）")
            time.sleep(delay)

    if not dry_run:
        queue = [q for q in queue if q.get("status") != "posted"]
        save_queue(queue)
        save_posted(posted)

    print(f"\n=== 完了: {posted_count} 件の引用リポストを投稿 ===")


def main():
    parser = argparse.ArgumentParser(description="X 引用リポスト（Nowpattern Breaking Pipeline）")
    parser.add_argument("--batch", type=int, default=1, help="一度に投稿する件数（デフォルト: 1）")
    parser.add_argument("--dry-run", action="store_true", help="投稿せずに確認のみ")
    args = parser.parse_args()

    api_key = os.environ.get("TWITTER_API_KEY", "")
    api_secret = os.environ.get("TWITTER_API_SECRET", "")
    acc_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
    acc_secret = os.environ.get("TWITTER_ACCESS_SECRET", "")

    if not all([api_key, api_secret, acc_token, acc_secret]):
        print("ERROR: Twitter認証情報が不足しています。")
        print("  環境変数を確認: TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET")
        sys.exit(1)

    auth = OAuth1(api_key, api_secret, acc_token, acc_secret)

    run_quote_reposts(auth, batch_size=args.batch, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
