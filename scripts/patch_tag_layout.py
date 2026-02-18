"""Fix tag badge layout: vertical stacking + remove footer duplicates.

Changes:
1. Each tag row gets explicit display:block + margin-bottom for vertical stacking
2. Remove tag_badges_html from footer section
"""
import re

filepath = "/opt/shared/scripts/nowpattern_article_builder.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

changes = 0

# ===========================================================================
# 1. Fix _build_tag_badges: use display:block rows with clear margins
# ===========================================================================
old_func_pattern = r'def _build_tag_badges\(genre_tags: str, event_tags: str, dynamics_tags: str\) -> str:.*?return "\\n"\.join\(lines\)'

new_func = r'''def _build_tag_badges(genre_tags: str, event_tags: str, dynamics_tags: str) -> str:
    """3種類のタグをクリック可能なハッシュタグリンクとして表示するHTMLを生成。
    各タグはGhostのタグページ（/tag/{slug}/）にリンクし、同じタグの記事一覧が見られる。"""
    import urllib.parse
    lines = []

    LINK_STYLES = {
        "genre": "display: inline-block; background: #1a3a5c; color: #e0f0ff; padding: 4px 12px; border-radius: 4px; font-size: 0.8em; font-weight: 600; letter-spacing: 0.05em; text-decoration: none;",
        "event": "display: inline-block; background: #3a3a3a; color: #e0dcd4; padding: 4px 12px; border-radius: 4px; font-size: 0.8em; font-weight: 600; letter-spacing: 0.05em; text-decoration: none;",
        "dynamics": "display: inline-block; background: #121e30; color: #c9a84c; padding: 4px 12px; border-radius: 4px; font-size: 0.8em; font-weight: bold; letter-spacing: 0.05em; border: 1px solid #c9a84c; text-decoration: none;",
    }
    ROW_STYLE = "display: block; margin: 0 0 6px 0;"
    LABEL_STYLE = "font-size: 0.75em; color: #888; margin-right: 4px;"

    def make_slug(tag_name):
        slug = tag_name.strip().lower()
        slug = slug.replace(" ", "-").replace("\u3000", "-")
        slug = slug.replace("\u30fb", "-").replace("\u00b7", "-")
        slug = urllib.parse.quote(slug, safe="-")
        return slug

    def make_tag_link(tag_name, style_key):
        slug = make_slug(tag_name)
        url = f"https://nowpattern.com/tag/{slug}/"
        style = LINK_STYLES[style_key]
        return f'<a href="{url}" style="{style}">#{tag_name}</a>'

    # ジャンルタグ（青系）
    genres = [g.strip() for g in genre_tags.replace("/", ",").replace("\u3001", ",").split(",") if g.strip()]
    if genres:
        badges = " ".join(make_tag_link(g, "genre") for g in genres)
        lines.append(f'<div style="{ROW_STYLE}"><span style="{LABEL_STYLE}">\u30b8\u30e3\u30f3\u30eb\uff1a</span>{badges}</div>')

    # イベントタグ（グレー系）
    events = [e.strip() for e in event_tags.replace("/", ",").replace("\u3001", ",").split(",") if e.strip()]
    if events:
        badges = " ".join(make_tag_link(e, "event") for e in events)
        lines.append(f'<div style="{ROW_STYLE}"><span style="{LABEL_STYLE}">\u30a4\u30d9\u30f3\u30c8\uff1a</span>{badges}</div>')

    # 力学タグ（金色）
    dynamics = [d.strip() for d in dynamics_tags.replace(" \u00d7 ", ",").replace("\u00d7", ",").replace("/", ",").replace("\u3001", ",").split(",") if d.strip()]
    if dynamics:
        badges = " ".join(make_tag_link(d, "dynamics") for d in dynamics)
        lines.append(f'<div style="{ROW_STYLE}"><span style="{LABEL_STYLE}">\u529b\u5b66\uff1a</span>{badges}</div>')

    return "\n".join(lines)'''

match = re.search(old_func_pattern, content, re.DOTALL)
if match:
    content = content[:match.start()] + new_func + content[match.end():]
    changes += 1
    print("1. OK: _build_tag_badges updated with block-level rows")
else:
    print("1. ERROR: Could not find _build_tag_badges")
    import sys
    sys.exit(1)

# ===========================================================================
# 2. Remove footer tag_badges_html
# ===========================================================================
# Replace "  {tag_badges_html}\n  {related_html}" with just "  {related_html}"
old_footer = '  {tag_badges_html}\n  {related_html}'
new_footer = '  {related_html}'
if old_footer in content:
    content = content.replace(old_footer, new_footer)
    changes += 1
    print("2. OK: Removed tag badges from footer")
else:
    print("2. SKIP: Footer tag badges not found (may already be removed)")

# ===========================================================================
# 3. Write
# ===========================================================================
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print(f"DONE: {changes} changes applied")
