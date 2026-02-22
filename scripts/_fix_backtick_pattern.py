#!/usr/bin/env python3
"""Remove backtick command injection pattern - too aggressive for markdown messages."""

for bot_dir in ["/opt/claude-code-telegram", "/opt/claude-code-telegram-neo2"]:
    path = f"{bot_dir}/src/bot/middleware/security.py"
    try:
        with open(path, "r") as f:
            content = f.read()

        # Remove the backtick pattern from dangerous_patterns
        # r"`[^`]*`" matches ANY backtick-quoted text (markdown code blocks!)
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            if '`[^`]*`' in line:
                continue  # Skip backtick pattern
            new_lines.append(line)

        new_content = "\n".join(new_lines)
        with open(path, "w") as f:
            f.write(new_content)
        print(f"OK: {bot_dir} - removed backtick pattern")
    except Exception as e:
        print(f"ERROR: {bot_dir} - {e}")
