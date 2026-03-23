#!/usr/bin/env python3
"""Analyze duplicate Ghost articles and generate removal plan."""
import sqlite3, json
from collections import defaultdict
from unicodedata import normalize as unorm
import re

DB = '/var/www/nowpattern/content/data/ghost.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
SELECT id, slug, title, created_at, updated_at, status
FROM posts
WHERE type='post' AND status='published'
ORDER BY created_at ASC
""")
all_posts = cur.fetchall()

def norm_title(t):
    return unorm('NFKC', t or '').lower().strip()

by_title = defaultdict(list)
for row in all_posts:
    pid, slug, title, ca, ua, status = row
    key = norm_title(title)
    by_title[key].append({'id': pid, 'slug': slug, 'title': title, 'created_at': ca})

dup_groups = {k: v for k, v in by_title.items() if len(v) > 1}
print(f'Duplicate title groups: {len(dup_groups)}')
print(f'Total posts in dup groups: {sum(len(v) for v in dup_groups.values())}')

keep_list = []
remove_list = []

for key, posts in sorted(dup_groups.items(), key=lambda x: x[1][0]['created_at']):
    posts_sorted = sorted(posts, key=lambda p: p['created_at'])
    keep_list.append(posts_sorted[0])
    for p in posts_sorted[1:]:
        remove_list.append({'remove': p, 'keep': posts_sorted[0]})

print(f'To KEEP (oldest per group): {len(keep_list)}')
print(f'To DRAFT (duplicates): {len(remove_list)}')

numbered = [r for r in remove_list if re.search(r'-\d+$', r['remove']['slug'])]
other    = [r for r in remove_list if r not in numbered]
print(f'\nRemoval breakdown:')
print(f'  Numbered slugs (-2/-3/...): {len(numbered)}')
print(f'  Other variant slugs: {len(other)}')

print('\n=== ALL REMOVAL CANDIDATES ===')
for r in remove_list:
    rp = r['remove']
    kp = r['keep']
    print(f'  DRAFT: {rp["slug"]}')
    print(f'  KEEP:  {kp["slug"]}')
    print(f'  Title: {rp["title"][:70]}')
    print()

# Save slugs to a JSON file for the fix script
out = {
    'total_to_draft': len(remove_list),
    'slugs_to_draft': [r['remove']['slug'] for r in remove_list],
    'pairs': [{'draft': r['remove']['slug'], 'keep': r['keep']['slug']} for r in remove_list]
}
with open('/opt/shared/scripts/duplicate_posts_plan.json', 'w') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f'[SAVED] /opt/shared/scripts/duplicate_posts_plan.json')

conn.close()
