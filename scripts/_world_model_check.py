#!/usr/bin/env python3
"""World model check: content pipeline, X posting, service health"""
import json, subprocess, os, sqlite3

# === Content pipeline ===
print("=== CONTENT PIPELINE ===")
try:
    ghost_db = '/var/www/nowpattern/content/data/ghost.db'
    conn = sqlite3.connect(ghost_db)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM posts WHERE type='post' AND status='published'")
    total = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM posts WHERE type='post' AND status='published' AND created_at > datetime('now', '-1 day')")
    today = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM posts WHERE type='post' AND status='published' AND created_at > datetime('now', '-7 day')")
    week = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM posts WHERE type='post' AND status='published' AND custom_excerpt LIKE '%lang-ja%' OR tags LIKE '%lang-ja%'")
    # Just count by slug pattern for JA
    cur.execute("SELECT count(*) FROM posts WHERE type='post' AND status='published' AND slug NOT LIKE 'en-%'")
    ja_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM posts WHERE type='post' AND status='published' AND slug LIKE 'en-%'")
    en_count = cur.fetchone()[0]
    conn.close()
    print("  Total published: %d" % total)
    print("  Last 24h: %d" % today)
    print("  Last 7d: %d  (avg/day: %.1f)" % (week, week/7))
    print("  JA (~not en-): %d  EN (en-*): %d" % (ja_count, en_count))
except Exception as e:
    print("  ERROR: %s" % e)

print()

# === X posting logs ===
print("=== X POSTING ===")
x_log_paths = [
    '/opt/shared/logs/x_auto_post.log',
    '/opt/shared/logs/x-auto-post.log',
    '/opt/shared/logs/x_post.log',
    '/opt/shared/logs/x_swarm.log',
    '/opt/shared/logs/x-swarm-dispatcher.log',
]
found_log = None
for path in x_log_paths:
    if os.path.exists(path):
        found_log = path
        lines = open(path).readlines()
        print("  Log: %s  (%d lines)" % (path, len(lines)))
        print("  --- Last 15 lines ---")
        for l in lines[-15:]:
            print("  " + l.rstrip())
        break
if not found_log:
    print("  No X posting log found. Checking /opt/shared/logs/...")
    logs = os.listdir('/opt/shared/logs/')
    x_logs = [l for l in logs if 'x' in l.lower() or 'twitter' in l.lower() or 'tweet' in l.lower()]
    print("  Possible X logs: %s" % x_logs)

print()

# === Prediction hit_miss normalization check ===
print("=== HIT_MISS FIELD INCONSISTENCY ===")
db = json.load(open('/opt/shared/scripts/prediction_db.json'))
resolved = [p for p in db['predictions'] if p.get('brier_score') is not None]
from collections import Counter
hm = Counter(p.get('hit_miss','null') for p in resolved)
print("  Values found: %s" % dict(hm))
print("  Normalized: hits=%d misses=%d" % (
    sum(hm.get(k,0) for k in ['correct','hit']),
    sum(hm.get(k,0) for k in ['wrong','incorrect','miss'])
))

print()

# === Recent evolution log ===
print("=== RECENT EVOLUTION LOG ===")
elog_path = '/opt/shared/logs/evolution_loop.log'
if os.path.exists(elog_path):
    lines = open(elog_path).readlines()
    print("  Total lines: %d  Last run entry:" % len(lines))
    for l in lines[-10:]:
        print("  " + l.rstrip())

print()

# === Check page rebuild progress ===
print("=== PAGE REBUILD STATUS ===")
rebuild_log = '/opt/shared/logs/page_rebuild.log'
if os.path.exists(rebuild_log):
    lines = open(rebuild_log).readlines()
    print("  Lines so far: %d" % len(lines))
    for l in lines[-10:]:
        print("  " + l.rstrip())
else:
    print("  Log not created yet")

# Also check prediction_page.log
pp_log = '/opt/shared/polymarket/prediction_page.log'
if os.path.exists(pp_log):
    lines = open(pp_log).readlines()
    print("\n  prediction_page.log last 5 lines:")
    for l in lines[-5:]:
        print("  " + l.rstrip())
