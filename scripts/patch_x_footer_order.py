"""Fix build_tag_footer: CTA first, then separator, then tags. Round word count."""

filepath = "/opt/shared/scripts/rss-post-quote-rt.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Find and replace the entire function
start_marker = 'def build_tag_footer(article):'
start = content.find(start_marker)
if start < 0:
    print("ERROR: build_tag_footer not found")
    import sys; sys.exit(1)

# Find the end: next function def at same indent level
end = content.find('\ndef ', start + 10)
if end < 0:
    end = content.find('\nNOWPATTERN_TAXONOMY', start + 10)

old_func = content[start:end]

new_func = '''def build_tag_footer(article):
    """
    X\u6295\u7a3f\u306e\u672b\u5c3e\u306b\u4ed8\u3051\u308bCTA + \u30bf\u30b0\u30ea\u30f3\u30af\u3002
    \U0001f4d6 \u8a73\u7d30\u5206\u6790\uff08\u7d04X00\u5b57\uff09\u7d9a\u304d\u306f\u3053\u3061\u3089\u2192 URL
    \u2501\u2501
    \u30b8\u30e3\u30f3\u30eb #\u5730\u653f\u5b66 \u2192 nowpattern.com/tag/...
    \u529b\u5b66 #\u30a8\u30b9\u30ab\u30ec\u30fc\u30b7\u30e7\u30f3\u87ba\u65cb \u2192 nowpattern.com/tag/...
    """
    taxonomy = _load_taxonomy()
    genre_slug = article.get("ghost_genre", "")
    pattern_slug = article.get("ghost_pattern", "")
    ghost_url = article.get("ghost_url", "")

    if not genre_slug and not pattern_slug and not ghost_url:
        return ""

    result_lines = []

    # CTA first (with rounded word count)
    if ghost_url:
        analysis_full = article.get("analysis_full", "")
        char_count = len(analysis_full) if analysis_full else 0
        if char_count > 0:
            rounded = round(char_count / 100) * 100
            result_lines.append("\U0001f4d6 \u8a73\u7d30\u5206\u6790\uff08\u7d04" + str(rounded) + "\u5b57\uff09\u7d9a\u304d\u306f\u3053\u3061\u3089\u2192 " + ghost_url)
        else:
            result_lines.append("\U0001f4d6 \u8a73\u7d30\u306f\u3053\u3061\u3089\u2192 " + ghost_url)

    # Separator
    result_lines.append("\u2501\u2501")

    # Tag lines
    if genre_slug:
        genre_info = next((g for g in taxonomy.get("genres", []) if g["slug"] == genre_slug), None)
        if genre_info:
            tag_url = "https://nowpattern.com/tag/genre-" + genre_slug + "/"
            result_lines.append("\u30b8\u30e3\u30f3\u30eb #" + genre_info["name"] + " \u2192 " + tag_url)

    if pattern_slug:
        pattern_info = next((p for p in taxonomy.get("patterns", []) if p["slug"] == pattern_slug), None)
        if pattern_info:
            tag_url = "https://nowpattern.com/tag/" + pattern_slug + "/"
            result_lines.append("\u529b\u5b66 #" + pattern_info["name"] + " \u2192 " + tag_url)

    if len(result_lines) <= 1:
        return ""
    return "\\n".join(result_lines)

'''

content = content[:start] + new_func + content[end:]

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("OK: build_tag_footer updated (CTA first, rounded word count)")
