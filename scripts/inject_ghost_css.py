"""
Ghost Custom CSS Injector for Nowpattern.

Ghost Admin → Code injection → Site Header に Nowpattern CSS を注入する。
Ghost 5.130: Integration APIではSettings PUT不可のため、SQLite直接更新方式。

VPS上で実行: python3 /opt/shared/scripts/inject_ghost_css.py
注入後はGhost再起動が必要: systemctl restart ghost-nowpattern
"""

import sys
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import os
import re
import sqlite3

# ---------------------------------------------------------------------------
# Ghost DB path
# ---------------------------------------------------------------------------

DEFAULT_GHOST_DB = "/var/www/nowpattern/content/data/ghost.db"

# ---------------------------------------------------------------------------
# Nowpattern Custom CSS
# ---------------------------------------------------------------------------

NOWPATTERN_CSS = """<style>
/* Nowpattern Custom Styles v3.0 */
.np-pattern-box {
  background: #121e30;
  border-radius: 8px;
  padding: 24px 28px;
  margin: 24px 0;
}
.np-pattern-box h2 {
  font-size: 1.3em;
  color: #c9a84c;
  margin: 0 0 12px 0;
  letter-spacing: 0.1em;
}
.np-pattern-tag {
  color: #c9a84c;
  font-size: 1.1em;
  font-weight: bold;
  margin: 0 0 16px 0;
}
.np-pattern-summary {
  color: #e0dcd4;
  font-style: italic;
  margin: 0 0 16px 0;
}
.np-pattern-body {
  color: #ffffff;
  line-height: 1.7;
}
.np-pattern-body strong {
  color: #c9a84c;
}
.np-section-hr {
  border: none;
  border-top: 1px solid #e0dcd4;
  margin: 24px 0;
}
.np-why-box {
  border-left: 4px solid #c9a84c;
  padding: 12px 16px;
  margin: 0 0 24px 0;
  background: #f8f6f0;
}
.np-why-box strong {
  color: #c9a84c;
}
.np-footer {
  font-size: 0.9em;
  color: #666;
  padding-top: 8px;
}
.np-footer a {
  color: #c9a84c;
}
.np-diagram {
  text-align: center;
  margin: 24px 0;
}
.np-diagram img {
  max-width: 100%;
  border-radius: 4px;
}
/* Tag Badges v1.0 */
.np-tag-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 8px 0;
}
.np-tag-genre {
  display: inline-block;
  background: #1a3a5c;
  color: #e0f0ff;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: 600;
  letter-spacing: 0.05em;
}
.np-tag-event {
  display: inline-block;
  background: #3a3a3a;
  color: #e0dcd4;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: 600;
  letter-spacing: 0.05em;
}
.np-tag-dynamics {
  display: inline-block;
  background: #121e30;
  color: #c9a84c;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: bold;
  letter-spacing: 0.05em;
  border: 1px solid #c9a84c;
}
</style>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def inject_css():
    db_path = os.environ.get("GHOST_DB_PATH", DEFAULT_GHOST_DB)

    if not os.path.exists(db_path):
        print(f"ERROR: Ghost DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Step 1: 現在の codeinjection_head を読む
    cur.execute("SELECT value FROM settings WHERE key = 'codeinjection_head'")
    row = cur.fetchone()
    current_head = (row[0] or "") if row else ""
    print(f"Current codeinjection_head: {len(current_head)} chars")

    # Step 2: 既存のNowpattern CSSを置換 or 新規追加
    marker = "/* Nowpattern Custom Styles"
    if marker in current_head:
        pattern = r'<style>\s*/\* Nowpattern Custom Styles.*?</style>'
        new_head = re.sub(pattern, NOWPATTERN_CSS.strip(), current_head, flags=re.DOTALL)
        print("Replacing existing Nowpattern CSS...")
    else:
        new_head = (current_head + "\n" + NOWPATTERN_CSS.strip()).strip()
        print("Adding Nowpattern CSS for the first time...")

    # Step 3: SQLite更新
    cur.execute("UPDATE settings SET value = ? WHERE key = 'codeinjection_head'", (new_head,))
    conn.commit()
    conn.close()

    print(f"OK: Ghost Custom CSS injected ({len(NOWPATTERN_CSS)} chars)")
    print(f"Total codeinjection_head: {len(new_head)} chars")
    print("NOTE: Run 'systemctl restart ghost-nowpattern' to apply changes")


if __name__ == "__main__":
    inject_css()
