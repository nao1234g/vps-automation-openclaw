"""Patch rss-post-quote-rt.py to add tag links + CTA to X posts.

Adds to the end of each tweet:
  ━━
  ジャンル #地政学 → https://nowpattern.com/tag/genre-geopolitics/
  力学 #エスカレーション螺旋 → https://nowpattern.com/tag/p-escalation-spiral/
  📖 詳細分析（7000字）→ https://nowpattern.com/slug/
"""

filepath = "/opt/shared/scripts/rss-post-quote-rt.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

changes = 0

# ===========================================================================
# 1. Add taxonomy loader + tag footer builder function after build_hashtags
# ===========================================================================
insert_after = """    # 固定タグ先頭 + 動的タグ
    all_tags = fixed_tags + dynamic_tags
    return " ".join(all_tags)"""

tag_footer_func = '''


# ---------------------------------------------------------------------------
# Nowpattern Tag Footer for X posts
# ---------------------------------------------------------------------------

NOWPATTERN_TAXONOMY = None

def _load_taxonomy():
    """タクソノミーファイルを一度だけ読み込みキャッシュする"""
    global NOWPATTERN_TAXONOMY
    if NOWPATTERN_TAXONOMY is not None:
        return NOWPATTERN_TAXONOMY
    taxonomy_path = "/opt/shared/scripts/nowpattern_taxonomy.json"
    try:
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            NOWPATTERN_TAXONOMY = json.load(f)
    except Exception:
        NOWPATTERN_TAXONOMY = {"genres": [], "patterns": []}
    return NOWPATTERN_TAXONOMY


def build_tag_footer(article):
    """
    X投稿の末尾に付けるタグリンク + CTA。
    ━━
    ジャンル #地政学 → nowpattern.com/tag/...
    力学 #エスカレーション螺旋 → nowpattern.com/tag/...
    📖 詳細分析（○字）→ nowpattern.com/...
    """
    taxonomy = _load_taxonomy()
    genre_slug = article.get("ghost_genre", "")
    pattern_slug = article.get("ghost_pattern", "")
    ghost_url = article.get("ghost_url", "")

    if not genre_slug and not pattern_slug and not ghost_url:
        return ""

    lines = []

    # ジャンル
    if genre_slug:
        genre_info = next((g for g in taxonomy.get("genres", []) if g["slug"] == genre_slug), None)
        if genre_info:
            tag_url = "https://nowpattern.com/tag/genre-" + genre_slug + "/"
            lines.append("ジャンル #" + genre_info["name"] + " → " + tag_url)

    # 力学パターン
    if pattern_slug:
        pattern_info = next((p for p in taxonomy.get("patterns", []) if p["slug"] == pattern_slug), None)
        if pattern_info:
            tag_url = "https://nowpattern.com/tag/" + pattern_slug + "/"
            lines.append("力学 #" + pattern_info["name"] + " → " + tag_url)

    # CTA with word count
    if ghost_url:
        analysis_full = article.get("analysis_full", "")
        word_count = len(analysis_full) if analysis_full else 0
        if word_count > 0:
            lines.append("📖 詳細分析（" + str(word_count) + "字）→ " + ghost_url)
        else:
            lines.append("📖 詳細はこちら → " + ghost_url)

    if not lines:
        return ""
    return "━━\\n" + "\\n".join(lines)'''

if insert_after in content:
    content = content.replace(insert_after, insert_after + tag_footer_func)
    changes += 1
    print("1. OK: build_tag_footer function added")
else:
    print("1. ERROR: Could not find insertion point for build_tag_footer")
    # Debug
    if "all_tags = fixed_tags + dynamic_tags" in content:
        print("  Found 'all_tags' line but context differs")
    import sys
    sys.exit(1)

# ===========================================================================
# 2. Modify build_x_post to append tag footer
# ===========================================================================
old_grok_return = '''    if grok_text:
        return grok_text.strip()'''

new_grok_return = '''    if grok_text:
        tag_footer = build_tag_footer(article)
        if tag_footer:
            return (grok_text.strip() + "\\n\\n" + tag_footer).strip()
        return grok_text.strip()'''

if old_grok_return in content:
    content = content.replace(old_grok_return, new_grok_return)
    changes += 1
    print("2. OK: Grok return path updated with tag footer")
else:
    print("2. SKIP: Grok return already modified or not found")

# Also update fallback return
old_fallback = '''    hook = analysis if analysis else title[:100]
    hashtag_line = f"\\n\\n{hashtags}" if hashtags else ""
    return (hook + hashtag_line).strip()'''

new_fallback = '''    hook = analysis if analysis else title[:100]
    hashtag_line = f"\\n\\n{hashtags}" if hashtags else ""
    tag_footer = build_tag_footer(article)
    footer_line = f"\\n\\n{tag_footer}" if tag_footer else ""
    return (hook + hashtag_line + footer_line).strip()'''

if old_fallback in content:
    content = content.replace(old_fallback, new_fallback)
    changes += 1
    print("3. OK: Fallback return path updated with tag footer")
else:
    print("3. SKIP: Fallback already modified or not found")

# ===========================================================================
# Write
# ===========================================================================
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print(f"DONE: {changes} changes applied")
