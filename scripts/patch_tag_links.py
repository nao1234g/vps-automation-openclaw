"""Patch nowpattern_article_builder.py to make tags clickable links to Ghost tag pages.

Tags become clickable #hashtag links:
  ジャンル：#地政学・安全保障 #エネルギー・環境
  イベント：#軍事衝突 #制裁・経済戦争
  力学：#危機便乗 #対立の螺旋

Each tag links to https://nowpattern.com/tag/{slug}/ showing all articles with that tag.
"""
import re

filepath = "/opt/shared/scripts/nowpattern_article_builder.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# ===========================================================================
# 1. Replace _build_tag_badges function with clickable link version
# ===========================================================================
old_func_pattern = r'def _build_tag_badges\(genre_tags: str, event_tags: str, dynamics_tags: str\) -> str:.*?return "\\n"\.join\(lines\)'

new_func = r'''def _build_tag_badges(genre_tags: str, event_tags: str, dynamics_tags: str) -> str:
    """3種類のタグをクリック可能なハッシュタグリンクとして表示するHTMLを生成。
    各タグはGhostのタグページ（/tag/{slug}/）にリンクし、同じタグの記事一覧が見られる。"""
    import urllib.parse
    lines = []

    # タグ種類ごとのインラインスタイル（<a>タグ用）
    LINK_STYLES = {
        "genre": "display: inline-block; background: #1a3a5c; color: #e0f0ff; padding: 4px 12px; border-radius: 4px; font-size: 0.8em; font-weight: 600; letter-spacing: 0.05em; text-decoration: none;",
        "event": "display: inline-block; background: #3a3a3a; color: #e0dcd4; padding: 4px 12px; border-radius: 4px; font-size: 0.8em; font-weight: 600; letter-spacing: 0.05em; text-decoration: none;",
        "dynamics": "display: inline-block; background: #121e30; color: #c9a84c; padding: 4px 12px; border-radius: 4px; font-size: 0.8em; font-weight: bold; letter-spacing: 0.05em; border: 1px solid #c9a84c; text-decoration: none;",
    }

    def make_slug(tag_name):
        """タグ名からGhost互換のスラッグを生成"""
        slug = tag_name.strip().lower()
        slug = slug.replace(" ", "-").replace("\u3000", "-")
        slug = slug.replace("\u30fb", "-").replace("\u00b7", "-")
        slug = urllib.parse.quote(slug, safe="-")
        return slug

    def make_tag_link(tag_name, style_key):
        """クリック可能なハッシュタグリンクを生成"""
        slug = make_slug(tag_name)
        url = f"https://nowpattern.com/tag/{slug}/"
        style = LINK_STYLES[style_key]
        return f'<a href="{url}" style="{style}">#{tag_name}</a>'

    LABEL_STYLE = "font-size: 0.75em; color: #888; margin-right: 4px;"

    # ジャンルタグ（青系）
    genres = [g.strip() for g in genre_tags.replace("/", ",").replace("\u3001", ",").split(",") if g.strip()]
    if genres:
        badges = " ".join(make_tag_link(g, "genre") for g in genres)
        lines.append(f'<div {_STYLES["tag_bar"]}><span style="{LABEL_STYLE}">\u30b8\u30e3\u30f3\u30eb\uff1a</span>{badges}</div>')

    # イベントタグ（グレー系）
    events = [e.strip() for e in event_tags.replace("/", ",").replace("\u3001", ",").split(",") if e.strip()]
    if events:
        badges = " ".join(make_tag_link(e, "event") for e in events)
        lines.append(f'<div {_STYLES["tag_bar"]}><span style="{LABEL_STYLE}">\u30a4\u30d9\u30f3\u30c8\uff1a</span>{badges}</div>')

    # 力学タグ（金色）
    dynamics = [d.strip() for d in dynamics_tags.replace(" \u00d7 ", ",").replace("\u00d7", ",").replace("/", ",").replace("\u3001", ",").split(",") if d.strip()]
    if dynamics:
        badges = " ".join(make_tag_link(d, "dynamics") for d in dynamics)
        lines.append(f'<div {_STYLES["tag_bar"]}><span style="{LABEL_STYLE}">\u529b\u5b66\uff1a</span>{badges}</div>')

    return "\n".join(lines)'''

match = re.search(old_func_pattern, content, re.DOTALL)
if match:
    content = content[:match.start()] + new_func + content[match.end():]
    print("OK: _build_tag_badges replaced with clickable link version")
else:
    print("ERROR: Could not find _build_tag_badges function")
    idx = content.find("def _build_tag_badges")
    if idx >= 0:
        print(f"Found at pos {idx}")
        print(repr(content[idx:idx+100]))
    import sys
    sys.exit(1)

# ===========================================================================
# 2. Add text-decoration: none to CSS styles (for Ghost global CSS fallback)
# ===========================================================================
css_updates = [
    ('letter-spacing: 0.05em;"\'', 'tag_genre'),
    ('letter-spacing: 0.05em;"\'', 'tag_event'),
    ('border: 1px solid #c9a84c;"\'', 'tag_dynamics'),
]

# Add text-decoration: none to existing tag styles
for style_key in ["tag_genre", "tag_event", "tag_dynamics"]:
    old_pattern = f'    "{style_key}":'
    idx = content.find(old_pattern)
    if idx >= 0 and "text-decoration: none" not in content[idx:idx+300]:
        # Find the closing ;"\' of this style
        end_idx = content.find('"\'', idx + len(old_pattern))
        if end_idx > 0:
            content = content[:end_idx] + ' text-decoration: none;' + content[end_idx:]
            print(f"OK: Added text-decoration:none to {style_key}")

# ===========================================================================
# 3. Write
# ===========================================================================
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("DONE: All patches applied - tags are now clickable #hashtag links")
