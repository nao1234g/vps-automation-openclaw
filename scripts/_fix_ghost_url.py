#!/usr/bin/env python3
"""Find and fill ghost_url for predictions missing them.
Strategy: Search Ghost DB for articles matching prediction titles or article_title fields.
"""
import json, sqlite3
from unicodedata import normalize as unorm

GHOST_DB = '/var/www/nowpattern/content/data/ghost.db'
PRED_DB = '/opt/shared/scripts/prediction_db.json'
DRY_RUN = '--apply' not in __import__('sys').argv

if DRY_RUN:
    print('DRY-RUN mode. Pass --apply to execute.\n')

db = json.load(open(PRED_DB, encoding='utf-8'))
preds = db['predictions']

conn = sqlite3.connect(GHOST_DB)
cur = conn.cursor()
cur.execute("""
    SELECT slug, title, custom_excerpt
    FROM posts
    WHERE type='post' AND status='published'
""")
ghost_posts = cur.fetchall()
conn.close()

def norm(t):
    return unorm('NFKC', str(t or '')).lower().strip()

# Build ghost index
ghost_by_slug = {row[0]: row for row in ghost_posts}
ghost_titles = [(norm(row[1]), row[0], row[1]) for row in ghost_posts]

def find_ghost_url(pred):
    """Try to find a matching Ghost article."""
    # Try article_title / title field
    for title_field in ['article_title', 'title', 'article_title_en']:
        t = pred.get(title_field, '')
        if not t:
            continue
        n = norm(t)
        # Exact match
        for ghost_norm, slug, ghost_title in ghost_titles:
            if ghost_norm == n:
                return f'https://nowpattern.com/{slug}/', slug, 'exact', title_field
        # Partial match (first 30 chars)
        for ghost_norm, slug, ghost_title in ghost_titles:
            if n[:30] and n[:30] in ghost_norm:
                return f'https://nowpattern.com/{slug}/', slug, 'partial', title_field

    # Try resolution_question
    rq = norm(pred.get('resolution_question', ''))
    if rq:
        for ghost_norm, slug, ghost_title in ghost_titles:
            if rq[:20] and rq[:20] in ghost_norm:
                return f'https://nowpattern.com/{slug}/', slug, 'rq_partial', 'resolution_question'

    return None, None, None, None

no_ghost = [p for p in preds if not p.get('ghost_url')]
print(f'Predictions missing ghost_url: {len(no_ghost)}\n')

found = 0
not_found = 0
for p in no_ghost:
    pid = p.get('prediction_id', '?')
    title = p.get('title') or p.get('article_title', '')
    url, slug, match_type, field = find_ghost_url(p)
    if url:
        print(f'[FOUND-{match_type}] {pid}: {title[:50]}')
        print(f'  Field: {field} -> URL: {url}')
        if not DRY_RUN:
            p['ghost_url'] = url
            p['ghost_slug'] = slug
        found += 1
    else:
        print(f'[NOT-FOUND] {pid}: {title[:50]}')
        not_found += 1
    print()

if not DRY_RUN and found > 0:
    with open(PRED_DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f'[SAVED] {PRED_DB}')

print(f'=== SUMMARY ===')
print(f'  Found: {found}  Not found: {not_found}')
print(f'\nNote: NP-2026-0113~0122 are long-term predictions.')
print(f'They may not have dedicated Ghost articles yet. ghost_url can be')
print(f'added when articles are created for them.')
