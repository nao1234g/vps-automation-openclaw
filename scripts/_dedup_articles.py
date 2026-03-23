#!/usr/bin/env python3
"""
重複記事を DRAFT に移動するスクリプト
同じタイトルの記事群のうち、最も新しいもの（published_at が最新）を残し、
古いものを DRAFT に変更する。
"""
import json, os, sys, datetime, requests, urllib3, time
from collections import defaultdict

try:
    import jwt as pyjwt
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'PyJWT'], capture_output=True)
    import jwt as pyjwt

urllib3.disable_warnings()

# Load env
env = {}
try:
    for line in open('/opt/cron-env.sh'):
        if line.startswith('export '):
            k, _, v = line[7:].strip().partition('=')
            env[k] = v.strip().strip('"').strip("'")
except FileNotFoundError:
    pass

api_key = env.get('NOWPATTERN_GHOST_ADMIN_API_KEY', os.environ.get('NOWPATTERN_GHOST_ADMIN_API_KEY', ''))
ghost_url = env.get('NOWPATTERN_GHOST_URL', 'https://nowpattern.com')
kid, sec = api_key.split(':')


def make_token():
    payload = {
        'iat': int(datetime.datetime.now().timestamp()),
        'exp': int(datetime.datetime.now().timestamp()) + 600,
        'aud': '/admin/'
    }
    return pyjwt.encode(payload, bytes.fromhex(sec), algorithm='HS256', headers={'kid': kid})


def get_headers():
    return {'Authorization': f'Ghost {make_token()}', 'Content-Type': 'application/json'}


# Fetch all published posts
print('Fetching all published posts...')
all_posts = []
page = 1
while True:
    r = requests.get(
        f'{ghost_url}/ghost/api/admin/posts/?limit=100&page={page}&status=published'
        f'&fields=id,title,slug,published_at,updated_at',
        headers=get_headers(), verify=False
    )
    data = r.json()
    posts = data.get('posts', [])
    if not posts:
        break
    all_posts.extend(posts)
    meta = data.get('meta', {}).get('pagination', {})
    if page >= meta.get('pages', 1):
        break
    page += 1
    time.sleep(0.5)

print(f'Total published posts: {len(all_posts)}')

# Group by exact title
title_groups = defaultdict(list)
for p in all_posts:
    title_groups[p['title']].append(p)

# Find duplicates
dupes = {title: posts for title, posts in title_groups.items() if len(posts) > 1}
print(f'Duplicate title groups: {len(dupes)}')

total_to_draft = 0
drafted = 0
errors = 0

for title, posts in sorted(dupes.items(), key=lambda x: -len(x[1])):
    # Sort by published_at descending (most recent first) → keep newest
    posts.sort(key=lambda p: p.get('published_at') or '', reverse=True)
    keep = posts[0]
    to_draft = posts[1:]
    print(f'  [{len(posts)}] {title[:60]}')
    print(f'    KEEP : {keep["slug"][:50]} ({(keep.get("published_at") or "")[:10]})')

    for p in to_draft:
        total_to_draft += 1
        print(f'    DRAFT: {p["slug"][:50]} ({(p.get("published_at") or "")[:10]})')
        r = requests.put(
            f'{ghost_url}/ghost/api/admin/posts/{p["id"]}/',
            headers=get_headers(),
            json={'posts': [{'status': 'draft', 'updated_at': p.get('updated_at')}]},
            verify=False
        )
        if r.status_code == 200:
            drafted += 1
        else:
            errors += 1
            print(f'    ERROR {r.status_code}: {r.text[:100]}')
        time.sleep(0.3)

print(f'\nDone: {drafted}/{total_to_draft} posts set to DRAFT, {errors} errors')
