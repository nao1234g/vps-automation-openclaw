#!/usr/bin/env python3
"""Refined duplicate analysis - exclude bilingual pairs (JA+EN same content)."""
import sqlite3, json, re
from collections import defaultdict
from unicodedata import normalize as unorm

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

def is_en(slug):
    return slug.startswith('en-')

by_title = defaultdict(list)
for row in all_posts:
    pid, slug, title, ca, ua, status = row
    key = norm_title(title)
    by_title[key].append({'id': pid, 'slug': slug, 'title': title, 'created_at': ca, 'is_en': is_en(slug)})

dup_groups = {k: v for k, v in by_title.items() if len(v) > 1}
print(f'All title groups with duplicates: {len(dup_groups)}')

remove_list = []
bilingual_pairs = []
true_dups = []

for key, posts in dup_groups.items():
    en_posts = [p for p in posts if p['is_en']]
    ja_posts = [p for p in posts if not p['is_en']]

    # Case 1: mix of JA and EN with same title = bilingual pairs (KEEP ALL)
    if en_posts and ja_posts and len(posts) == len(en_posts) + len(ja_posts):
        # Check if it's truly just 1 JA + 1 EN = legitimate bilingual pair
        if len(ja_posts) == 1 and len(en_posts) == 1:
            bilingual_pairs.append({'ja': ja_posts[0]['slug'], 'en': en_posts[0]['slug'], 'title': posts[0]['title']})
            continue
        # Otherwise, there might be duplicates within JA or EN sets
        # Handle JA duplicates within a mixed group
        if len(ja_posts) > 1:
            ja_sorted = sorted(ja_posts, key=lambda p: p['created_at'])
            for p in ja_sorted[1:]:
                remove_list.append({'remove': p, 'keep': ja_sorted[0], 'reason': 'JA duplicate (title matched EN too)'})
                true_dups.append(p)
        if len(en_posts) > 1:
            en_sorted = sorted(en_posts, key=lambda p: p['created_at'])
            for p in en_sorted[1:]:
                remove_list.append({'remove': p, 'keep': en_sorted[0], 'reason': 'EN duplicate (title matched JA too)'})
                true_dups.append(p)
        continue

    # Case 2: all same lang (all JA or all EN) = true duplicates
    posts_sorted = sorted(posts, key=lambda p: p['created_at'])
    for p in posts_sorted[1:]:
        remove_list.append({'remove': p, 'keep': posts_sorted[0], 'reason': 'same-lang duplicate'})
        true_dups.append(p)

print(f'\nBilingual pairs (JA+EN, SKIP - legitimate): {len(bilingual_pairs)}')
print(f'True duplicates to DRAFT: {len(remove_list)}')

# Analyze removal candidates
numbered = [r for r in remove_list if re.search(r'-\d+$', r['remove']['slug'])]
other    = [r for r in remove_list if r not in numbered]
en_to_draft = [r for r in remove_list if r['remove']['is_en']]
ja_to_draft = [r for r in remove_list if not r['remove']['is_en']]

print(f'\nBreakdown of true duplicates:')
print(f'  JA duplicates: {len(ja_to_draft)}')
print(f'  EN duplicates: {len(en_to_draft)}')
print(f'  Numbered slug (-2/-3/...): {len(numbered)}')
print(f'  Other variant: {len(other)}')

print('\n=== TRUE DUPLICATES TO DRAFT ===')
for r in remove_list:
    rp = r['remove']
    kp = r['keep']
    lang = 'EN' if rp['is_en'] else 'JA'
    print(f'  [{lang}] DRAFT: {rp["slug"]}')
    print(f'         KEEP:  {kp["slug"]}')
    print(f'         Title: {rp["title"][:60]}')
    print(f'         Reason: {r["reason"]}')
    print()

print('\n=== BILINGUAL PAIRS (legitimate, DO NOT draft) ===')
for bp in bilingual_pairs[:5]:
    print(f'  JA: {bp["ja"]}')
    print(f'  EN: {bp["en"]}')
    print(f'  Title: {bp["title"][:60]}')
    print()
if len(bilingual_pairs) > 5:
    print(f'  ... and {len(bilingual_pairs)-5} more')

# Save plan
out = {
    'total_to_draft': len(remove_list),
    'bilingual_pairs_skipped': len(bilingual_pairs),
    'slugs_to_draft': [r['remove']['slug'] for r in remove_list],
    'pairs': [{'draft': r['remove']['slug'], 'keep': r['keep']['slug'], 'title': r['remove']['title'][:60], 'reason': r['reason']} for r in remove_list]
}
with open('/opt/shared/scripts/duplicate_posts_plan.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f'\n[SAVED] /opt/shared/scripts/duplicate_posts_plan.json ({len(remove_list)} to draft)')

conn.close()
