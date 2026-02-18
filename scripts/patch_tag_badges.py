"""Patch nowpattern_article_builder.py to add tag badge system."""
import re

filepath = "/opt/shared/scripts/nowpattern_article_builder.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

changes = 0

# ===========================================================================
# 1. Add tag badge styles to _STYLES dict
# ===========================================================================
anchor = '    "fact_list": \'style="line-height: 1.8; padding-left: 20px;"\','
insert_after = anchor + """
    "tag_bar": 'class="np-tag-bar" style="display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 8px 0;"',
    "tag_genre": 'class="np-tag-genre" style="display: inline-block; background: #1a3a5c; color: #e0f0ff; padding: 4px 12px; border-radius: 4px; font-size: 0.8em; font-weight: 600; letter-spacing: 0.05em;"',
    "tag_event": 'class="np-tag-event" style="display: inline-block; background: #3a3a3a; color: #e0dcd4; padding: 4px 12px; border-radius: 4px; font-size: 0.8em; font-weight: 600; letter-spacing: 0.05em;"',
    "tag_dynamics": 'class="np-tag-dynamics" style="display: inline-block; background: #121e30; color: #c9a84c; padding: 4px 12px; border-radius: 4px; font-size: 0.8em; font-weight: bold; letter-spacing: 0.05em; border: 1px solid #c9a84c;"',"""

if anchor in content:
    content = content.replace(anchor, insert_after)
    changes += 1
    print("1. Tag badge styles added")
else:
    print("1. SKIP: styles anchor not found")

# ===========================================================================
# 2. Add _build_tag_badges helper function before build_deep_pattern_html
# ===========================================================================
func_start = "def build_deep_pattern_html("
helper_func = '''def _build_tag_badges(genre_tags: str, event_tags: str, dynamics_tags: str) -> str:
    """3種類のタグをバッジとして表示するHTMLを生成"""
    lines = []

    # ジャンルタグ（青系）
    genres = [g.strip() for g in genre_tags.replace("/", ",").replace("\\u3001", ",").split(",") if g.strip()]
    if genres:
        badges = " ".join(f'<span {_STYLES["tag_genre"]}>{g}</span>' for g in genres)
        lines.append(f'<div {_STYLES["tag_bar"]}>{badges}</div>')

    # イベントタグ（グレー系）
    events = [e.strip() for e in event_tags.replace("/", ",").replace("\\u3001", ",").split(",") if e.strip()]
    if events:
        badges = " ".join(f'<span {_STYLES["tag_event"]}>{e}</span>' for e in events)
        lines.append(f'<div {_STYLES["tag_bar"]}>{badges}</div>')

    # 力学タグ（金色）
    dynamics = [d.strip() for d in dynamics_tags.replace(" \\u00d7 ", ",").replace("\\u00d7", ",").replace("/", ",").replace("\\u3001", ",").split(",") if d.strip()]
    if dynamics:
        badges = " ".join(f'<span {_STYLES["tag_dynamics"]}>{d}</span>' for d in dynamics)
        lines.append(f'<div {_STYLES["tag_bar"]}>{badges}</div>')

    return "\\n".join(lines)


def build_deep_pattern_html('''

if func_start in content:
    content = content.replace(func_start, helper_func, 1)
    changes += 1
    print("2. Tag badge builder function added")
else:
    print("2. SKIP: function start not found")

# ===========================================================================
# 3. Insert tag_badges_html generation + top badges into template
# ===========================================================================
old_template = '    template = f"""<!-- Why it matters'
new_template = """    tag_badges_html = _build_tag_badges(genre_tags, event_tags, dynamics_tags)

    template = f\"\"\"<!-- Tag Badges (top) -->
<div style="margin: 0 0 20px 0;">
{tag_badges_html}
</div>

<!-- Why it matters"""

if old_template in content:
    content = content.replace(old_template, new_template)
    changes += 1
    print("3. Top tag badges added to template")
else:
    print("3. SKIP: template start not found")

# ===========================================================================
# 4. Replace footer plain-text tags with badge HTML
# ===========================================================================
old_footer = '  <p><strong>Tags:</strong> {genre_tags} / {event_tags}</p>\n  <p><strong>NOW PATTERN:</strong> {dynamics_tags}</p>'
new_footer = '  {tag_badges_html}'

if old_footer in content:
    content = content.replace(old_footer, new_footer)
    changes += 1
    print("4. Footer tags updated to badge style")
else:
    print("4. SKIP: footer tags not found")

# ===========================================================================
# 5. Also patch Speed Log template (build_speed_log_html)
# ===========================================================================
old_sl_footer = '  <p><strong>Tags:</strong> {genre_tags} / {event_tags}</p>'
# Only replace if it's still in the speed log area (after the deep pattern fix)
if old_sl_footer in content:
    new_sl_footer = '  {_build_tag_badges(genre_tags, event_tags, dynamics_tag)}'
    content = content.replace(old_sl_footer, new_sl_footer)
    changes += 1
    print("5. Speed Log footer tags also updated")
else:
    print("5. SKIP: Speed Log footer tags not found (may already be fixed)")

# ===========================================================================
# Write
# ===========================================================================
if changes > 0:
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\nOK: {changes} changes applied to {filepath}")
else:
    print("\nERROR: No changes applied")
