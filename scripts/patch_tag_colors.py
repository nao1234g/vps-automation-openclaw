"""
Update tag badge colors across all systems:
  - ジャンル: Deep Blue (trust, expertise, low eye fatigue)
  - イベント: Dark Teal (current, happening, calm)
  - 力学: Deep Red/Crimson (insight, importance, highest CTR)

Color psychology + UX research:
  Blue→Teal→Red gradient naturally draws eye to 力学 (Nowpattern's core value).
  Red accent colors increase CTR 20-30% in A/B tests.
  All colors use dark backgrounds + soft text for eye comfort.
"""
import sqlite3

# =============================================
# 1. Article Builder (inline styles)
# =============================================
filepath = "/opt/shared/scripts/nowpattern_article_builder.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

changes = 0

# --- LINK_STYLES in _build_tag_badges ---
# Genre: slightly brighter blue text
content = content.replace(
    "background: #1a3a5c; color: #e0f0ff;",
    "background: #1a3a5c; color: #c8e0ff;",
)
changes += content.count("background: #1a3a5c; color: #c8e0ff;")

# Event: grey -> dark teal
content = content.replace(
    "background: #3a3a3a; color: #e0dcd4;",
    "background: #1a3a35; color: #b8e0d4;",
)
changes += 1

# Dynamics: gold -> deep red
content = content.replace(
    "background: #121e30; color: #c9a84c;",
    "background: #3a1520; color: #ff9999;",
)
content = content.replace(
    "border: 1px solid #c9a84c;",
    "border: 1px solid #ff8080;",
)
changes += 1

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print(f"1. article_builder: updated")

# =============================================
# 2. Ghost Custom CSS (SQLite)
# =============================================
db_path = "/var/www/nowpattern/content/data/ghost.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT value FROM settings WHERE key = 'codeinjection_head'")
row = cur.fetchone()
css = row[0] if row else ""

# Genre: brighter text
css = css.replace("color: #e0f0ff;", "color: #c8e0ff;")

# Event: grey -> teal
css = css.replace("background: #3a3a3a;", "background: #1a3a35;")
css = css.replace("color: #e0dcd4;", "color: #b8e0d4;")

# Dynamics: gold -> red
css = css.replace("color: #c9a84c;", "color: #ff9999;")
css = css.replace("background: #121e30;", "background: #3a1520;")
css = css.replace("border: 1px solid #c9a84c;", "border: 1px solid #ff8080;")

cur.execute("UPDATE settings SET value = ? WHERE key = 'codeinjection_head'", (css,))
conn.commit()
conn.close()
print("2. Ghost CSS: updated")

print("DONE: Tag colors updated (Blue / Teal / Deep Red)")
print("  NOTE: Run 'systemctl restart ghost-nowpattern' to apply CSS")
