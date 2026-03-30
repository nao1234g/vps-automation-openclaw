#!/usr/bin/env python3
"""
ghost_to_tweet_queue.py v2 — Ghostの最新JP記事からXツイートキューを補充
"""
import json, os, sys, time, sqlite3, requests, argparse
from datetime import datetime, timezone, timedelta

from article_release_guard import evaluate_release_blockers

for line in open('/opt/cron-env.sh'):
    line = line.strip()
    if line.startswith('export ') and '=' in line:
        k, _, v = line[7:].partition('=')
        os.environ[k] = v.strip().strip('"\'')

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
QUEUE_FILE     = '/opt/shared/scripts/tweet_queue.json'
GHOST_DB_PATH  = '/var/www/nowpattern/content/data/ghost.db'
SITE_URL       = 'https://nowpattern.com'
JST            = timezone(timedelta(hours=9))

def get_recent_jp_articles(limit=30):
    db = sqlite3.connect(GHOST_DB_PATH, timeout=5)
    db.row_factory = sqlite3.Row
    rows = db.execute('''
        SELECT p.slug, p.title, p.custom_excerpt, p.published_at, p.html,
               GROUP_CONCAT(t.slug, ' ') AS tag_slugs
        FROM posts p
        LEFT JOIN posts_tags pt_all ON pt_all.post_id = p.id
        LEFT JOIN tags t ON t.id = pt_all.tag_id
        WHERE p.status = 'published'
          AND p.type = 'post'
          AND p.slug NOT LIKE 'en-%'
          AND EXISTS (
              SELECT 1 FROM posts_tags pt
              JOIN tags t ON t.id = pt.tag_id
              WHERE pt.post_id = p.id AND t.slug = 'lang-ja'
          )
        GROUP BY p.slug, p.title, p.custom_excerpt, p.published_at, p.html
        ORDER BY p.published_at DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    db.close()
    return [dict(r) for r in rows]

def generate_tweet(title, excerpt):
    url = (f"https://generativelanguage.googleapis.com/v1beta/"
           f"models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}")
    excerpt_str = (excerpt or '')[:200]
    prompt = f"""以下の記事タイトルと抜粋からXポスト用のテキストを1つ生成してください。

タイトル: {title}
抜粋: {excerpt_str}

ルール（厳守）:
- 最大200文字以内
- 冒頭に絵文字を1つだけ使う
- 好奇心ギャップ型：「なぜ？」「実は...」「意外な構造」を意識
- 「Nowpattern」という単語は使わない
- ハッシュタグ（#）は含めない（スクリプトが後で追加）
- URLは含めない（スクリプトが後で追加）
- 体言止め・短文・切れ味のある文体
- ポストテキストのみ出力（説明・前置き・引用符なし）"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 200, "temperature": 0.8}
    }
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    text = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    lines = [l for l in text.split('\n') if not l.strip().startswith('#') and 'http' not in l]
    return '\n'.join(lines).strip()

def load_queue():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE) as f:
            data = json.load(f)
        if isinstance(data, dict) and 'tweets' in data:
            return data
    return {"tweets": []}

def save_queue(queue):
    with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=30)
    args = parser.parse_args()

    queue = load_queue()
    existing_slugs = {t.get('source_slug') for t in queue.get('tweets', [])}
    pending_count = len([t for t in queue['tweets'] if t.get('status') == 'pending'])
    print(f"Current queue: {len(queue['tweets'])} total, {pending_count} pending")

    articles = get_recent_jp_articles(limit=args.limit)
    print(f"Ghost JP articles: {len(articles)} recent published")

    added = 0
    for article in articles:
        slug = article['slug']
        if slug in existing_slugs:
            continue

        title   = article['title']
        excerpt = article.get('custom_excerpt') or ''
        html    = article.get('html') or ''
        art_url = f"{SITE_URL}/{slug}/"

        release_block = evaluate_release_blockers(
            title=title,
            html=html,
            tags=(article.get('tag_slugs') or '').split(),
            site_url=SITE_URL,
            status='published',
            channel='x',
            require_external_sources=True,
            check_source_fetchability=True,
        )
        if release_block["errors"]:
            print(f"  SKIP release-blocker {slug[:40]}: {', '.join(release_block['errors'])}")
            continue

        try:
            tweet_text = generate_tweet(title, excerpt)
        except Exception as e:
            print(f"  Gemini error for {slug[:30]}: {e}")
            tweet_text = f"📊 {title[:150]}"

        entry = {
            "name":        slug,
            "text":        tweet_text,
            "link":        art_url,
            "status":      "pending",
            "created_at":  datetime.now(JST).isoformat(),
            "source_slug": slug,
            "tweet_url":   None,
            "distribution_approved": True,
            "release_block": {
                "risk_flags": release_block["risk_flags"],
                "human_approval_required": release_block["human_approval_required"],
                "human_approval_present": release_block["human_approval_present"],
            },
        }

        if args.dry_run:
            print(f"  [DRY] {title[:50]}")
            print(f"        → {tweet_text[:100]}...")
        else:
            queue['tweets'].append(entry)
            existing_slugs.add(slug)
            print(f"  ✅ {slug[:40]}")

        added += 1
        time.sleep(0.3)

    if added == 0:
        print("No new articles to queue.")
        return

    if not args.dry_run:
        save_queue(queue)
        new_pending = len([t for t in queue['tweets'] if t.get('status') == 'pending'])
        print(f"\nAdded {added} tweets. Queue now: {new_pending} pending")
    else:
        print(f"\n[DRY-RUN] Would add {added} entries.")

if __name__ == '__main__':
    main()
