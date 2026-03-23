#!/usr/bin/env python3
"""Fix Ghost DB genre-geopolitics tag pollution (540 duplicates -> 1 canonical)."""
import sqlite3, sys, re
from datetime import datetime

DB = '/var/www/nowpattern/content/data/ghost.db'
DRY_RUN = '--apply' not in sys.argv

print('=== Ghost genre-geopolitics fix ===')
print('Mode:', 'DRY-RUN (pass --apply to execute)' if DRY_RUN else 'APPLY')
print()

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Get canonical tag
cur.execute("SELECT id, slug, name FROM tags WHERE slug='genre-geopolitics'")
canonical = cur.fetchone()
canonical_id, canonical_slug, canonical_name = canonical
print('Canonical tag: id=' + canonical_id[:8] + '... name=[' + canonical_name + ']')

# Get all duplicate tag IDs
cur.execute("SELECT id, slug FROM tags WHERE slug LIKE 'genre-geopolitics-%'")
dup_tags = cur.fetchall()
dup_ids = [r[0] for r in dup_tags]
print('Duplicate tags count:', len(dup_ids))

if len(dup_ids) == 0:
    print('[OK] No duplicates found. Already clean.')
    conn.close()
    sys.exit(0)

placeholders = ','.join('?' for _ in dup_ids)

# Posts using duplicates
cur.execute('SELECT DISTINCT post_id FROM posts_tags WHERE tag_id IN (' + placeholders + ')', dup_ids)
affected_post_ids = [r[0] for r in cur.fetchall()]
print('Posts using duplicate tags:', len(affected_post_ids))

# Check which already have canonical
cur.execute('SELECT DISTINCT post_id FROM posts_tags WHERE tag_id=?', (canonical_id,))
already_canonical = {r[0] for r in cur.fetchall()}
print('Posts already having canonical tag:', len(already_canonical))
posts_needing_canonical = [p for p in affected_post_ids if p not in already_canonical]
print('Posts needing canonical tag added:', len(posts_needing_canonical))

if not DRY_RUN:
    # Step 1: Add canonical tag to posts that don't have it
    inserted = 0
    for post_id in posts_needing_canonical:
        cur.execute('SELECT MAX(sort_order) FROM posts_tags WHERE post_id=?', (post_id,))
        max_sort = cur.fetchone()[0] or 0
        new_id = (post_id + canonical_id)[:24]
        try:
            cur.execute(
                'INSERT OR IGNORE INTO posts_tags (id, post_id, tag_id, sort_order) VALUES (?, ?, ?, ?)',
                (new_id, post_id, canonical_id, max_sort + 1)
            )
            inserted += 1
        except Exception as e:
            print('  WARN insert failed for post ' + post_id[:8] + ': ' + str(e))
    print('[DONE] Inserted canonical tag for', inserted, 'posts')

    # Step 2: Delete duplicate tag associations
    cur.execute('DELETE FROM posts_tags WHERE tag_id IN (' + placeholders + ')', dup_ids)
    deleted_assoc = cur.rowcount
    print('[DONE] Deleted', deleted_assoc, 'duplicate tag associations from posts_tags')

    # Step 3: Delete duplicate tags
    cur.execute('DELETE FROM tags WHERE slug LIKE \'genre-geopolitics-%\'')
    deleted_tags = cur.rowcount
    print('[DONE] Deleted', deleted_tags, 'duplicate tags from tags table')

    # Step 4: Fix canonical tag name
    cur.execute("UPDATE tags SET name='Geopolitics & Security' WHERE id=?", (canonical_id,))
    print('[DONE] Updated canonical tag name: genre-geopolitics -> Geopolitics & Security')

    conn.commit()
    print()
    print('[SAVED] All changes committed to SQLite DB')
    print('NEXT STEP: systemctl restart ghost-nowpattern  (or flush Ghost cache)')

    # Verify
    print()
    print('=== POST-FIX VERIFICATION ===')
    cur.execute("SELECT COUNT(*) FROM tags WHERE slug LIKE 'genre-geopolitics%'")
    remaining = cur.fetchone()[0]
    print('Remaining genre-geopolitics* tags:', remaining, '(should be 1)')
    cur.execute("SELECT COUNT(DISTINCT post_id) FROM posts_tags WHERE tag_id=?", (canonical_id,))
    posts_with_canonical = cur.fetchone()[0]
    print('Posts with canonical genre-geopolitics tag:', posts_with_canonical)
else:
    print()
    print('[DRY-RUN] Would do:')
    print('  1. Add canonical genre-geopolitics tag to', len(posts_needing_canonical), 'posts')
    print('  2. Delete', len(dup_ids), 'duplicate tag associations from posts_tags')
    print('  3. Delete', len(dup_ids), 'duplicate tags from tags table')
    print('  4. Rename canonical tag: [' + canonical_name + '] -> [Geopolitics & Security]')
    print()
    print('Run with --apply to execute')

conn.close()
