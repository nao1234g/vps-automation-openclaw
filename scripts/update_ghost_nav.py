#!/usr/bin/env python3
"""Update Ghost navigation: JA base, simple JA/EN structure."""
import sqlite3, json

DB_PATH = "/var/www/nowpattern/content/data/ghost.db"

new_nav = [
    {"label": "ホーム", "url": "/"},
    {"label": "日本語", "url": "/taxonomy-ja/"},
    {"label": "English", "url": "/taxonomy-en/"},
]

new_secondary = [
    {"label": "なぜ3層か？", "url": "/taxonomy-guide-ja/"},
    {"label": "Why 3 Layers?", "url": "/taxonomy-guide-en/"},
]

conn = sqlite3.connect(DB_PATH)
conn.execute("UPDATE settings SET value = ? WHERE key = 'navigation';", (json.dumps(new_nav),))
conn.execute("UPDATE settings SET value = ? WHERE key = 'secondary_navigation';", (json.dumps(new_secondary),))
conn.commit()

for key in ["navigation", "secondary_navigation"]:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    print("{}:".format(key))
    for item in json.loads(row[0]):
        print("  {} -> {}".format(item["label"], item["url"]))
conn.close()
print("\nDone. Restart Ghost to apply.")
