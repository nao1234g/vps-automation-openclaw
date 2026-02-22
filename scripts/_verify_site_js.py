#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect("/var/www/nowpattern/content/data/ghost.db")
cur = conn.execute("SELECT value FROM settings WHERE key='codeinjection_foot'")
row = cur.fetchone()
conn.close()
js = row[0] if row else ""
print(f"Site JS length: {len(js)}")
print(f"Has TM mapping: {'TM=' in js}")
print(f"Has gh-article-title: {'gh-article-title' in js}")
print(f"Has gh-article-excerpt: {'gh-article-excerpt' in js}")

checks = ["genre-geopolitics", "genre-crypto", "event-military-conflict", "dynamics-platform-power"]
for c in checks:
    found = c in js
    print(f"  {c}: {'FOUND' if found else 'MISSING'}")

# Extract a sample mapping
import re
m = re.search(r'"genre-geopolitics":\{([^}]+)\}', js)
if m:
    print(f"\nSample mapping (genre-geopolitics): {m.group(0)[:200]}")
