#!/usr/bin/env python3
"""
AISA Auto Tweet Script v2 — Link-in-reply strategy
====================================================
Posts tweet from queue, then immediately replies with link.

X Algorithm awareness:
- Links in main tweet = suppressed reach (unless X Premium)
- Links in reply = no penalty
- Self-reply = conversation start (boosts engagement)

Reads from /opt/shared/scripts/tweet_queue.json
Queue format: each tweet can have optional "link" field.
If "link" exists, it's stripped from main text and posted as a self-reply.
"""
import json
import os
import sys
import re
import time
from datetime import datetime
from requests_oauthlib import OAuth1
import requests

# Load env
CRON_ENV = "/opt/cron-env.sh"
if os.path.exists(CRON_ENV):
    with open(CRON_ENV) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                k, v = line[7:].split("=", 1)
                v = v.strip().strip("'\"")
                os.environ[k] = v

API_KEY = os.getenv('TWITTER_API_KEY')
API_SECRET = os.getenv('TWITTER_API_SECRET')
ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')

# Telegram notification
TG_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

QUEUE_FILE = '/opt/shared/scripts/tweet_queue.json'


def send_telegram(text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    try:
        requests.post(
            f'https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage',
            json={'chat_id': TG_CHAT_ID, 'text': text, 'disable_web_page_preview': True},
            timeout=10,
        )
    except Exception:
        pass


def get_auth():
    return OAuth1(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)


def extract_links(text):
    """Extract URLs from tweet text and return (clean_text, links)."""
    url_pattern = r'https?://\S+'
    links = re.findall(url_pattern, text)
    clean_text = re.sub(url_pattern, '', text).strip()
    # Clean up leftover arrows pointing to removed links (e.g., "👇\n")
    clean_text = re.sub(r'\s*👇\s*$', '', clean_text).strip()
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    return clean_text, links


def post_tweet(text, auth, reply_to=None):
    """Post a tweet, optionally as a reply."""
    payload = {'text': text}
    if reply_to:
        payload['reply'] = {'in_reply_to_tweet_id': reply_to}

    r = requests.post(
        'https://api.twitter.com/2/tweets',
        json=payload,
        auth=auth,
        timeout=30,
    )
    if r.status_code in (200, 201):
        data = r.json()
        tweet_id = data['data']['id']
        return True, tweet_id
    else:
        return False, r.text[:200]


def main():
    if not os.path.exists(QUEUE_FILE):
        print("No queue file found")
        return

    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)

    pending = [t for t in queue['tweets'] if t['status'] == 'pending']
    if not pending:
        print("No pending tweets in queue")
        return

    tweet = pending[0]
    auth = get_auth()
    original_text = tweet['text']
    link = tweet.get('link', '')

    if not tweet.get('distribution_approved'):
        tweet['status'] = 'failed'
        tweet['error'] = 'distribution_not_approved'
        print("FAILED: queue entry not approved for distribution")
        with open(QUEUE_FILE, 'w') as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
        return

    if link:
        try:
            probe = requests.get(link, timeout=15, allow_redirects=True)
            if probe.status_code != 200:
                tweet['status'] = 'failed'
                tweet['error'] = f'link_status_{probe.status_code}'
                print(f"FAILED: linked article not reachable ({probe.status_code})")
                with open(QUEUE_FILE, 'w') as f:
                    json.dump(queue, f, indent=2, ensure_ascii=False)
                return
        except Exception as e:
            tweet['status'] = 'failed'
            tweet['error'] = f'link_probe_error:{e}'
            print(f"FAILED: linked article probe error: {e}")
            with open(QUEUE_FILE, 'w') as f:
                json.dump(queue, f, indent=2, ensure_ascii=False)
            return

    # Strategy: strip links from main tweet, post them as self-reply
    clean_text, links = extract_links(original_text)
    # Also check for explicit "link" field
    explicit_link = tweet.get('link', '')
    if explicit_link and explicit_link not in links:
        links.append(explicit_link)

    print(f"Posting tweet: {tweet['name']}")
    if links:
        print(f"  Links will be posted as self-reply: {links}")
        print(f"  Main tweet (no links): {clean_text[:100]}...")

    # Post main tweet (link-free)
    post_text = clean_text if links else original_text
    success, result = post_tweet(post_text, auth)

    if success:
        tweet['status'] = 'posted'
        tweet['posted_at'] = datetime.now().isoformat()
        tweet['tweet_id'] = result
        tweet['url'] = f"https://x.com/nowpattern/status/{result}"
        print(f"SUCCESS: {tweet['url']}")

        # Post link as self-reply
        if links:
            time.sleep(3)  # Small delay before self-reply
            link_text = "Full analysis: " + links[0]
            if len(links) > 1:
                link_text = "\n".join(links)
            reply_ok, reply_result = post_tweet(link_text, auth, reply_to=result)
            if reply_ok:
                tweet['link_reply_id'] = reply_result
                print(f"  Link posted as reply: {reply_result}")
            else:
                print(f"  Link reply failed: {reply_result}")

        send_telegram(f"Posted: {tweet['name']}\n{tweet['url']}")
    else:
        tweet['status'] = 'failed'
        tweet['error'] = result
        print(f"FAILED: {result}")
        send_telegram(f"Tweet failed: {tweet['name']}\n{result}")

    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
