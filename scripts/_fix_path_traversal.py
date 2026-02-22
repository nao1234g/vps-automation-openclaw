#!/usr/bin/env python3
"""Remove overly aggressive path traversal patterns from NEO security middleware."""

import re

for bot_dir in ["/opt/claude-code-telegram", "/opt/claude-code-telegram-neo2"]:
    path = f"{bot_dir}/src/bot/middleware/security.py"
    try:
        with open(path, "r") as f:
            content = f.read()

        # Remove /etc/, /var/, /usr/, /sys/, /proc/ patterns
        # Keep only ../ and ~/ which are genuinely dangerous
        lines = content.split("\n")
        new_lines = []
        skip_next = False
        for line in lines:
            # Skip lines with overly broad system path patterns
            if any(p in line for p in [
                r'r"\/etc\/',
                r'r"\/var\/',
                r'r"\/usr\/',
                r'r"\/sys\/',
                r'r"\/proc\/',
            ]):
                continue
            new_lines.append(line)

        new_content = "\n".join(new_lines)
        with open(path, "w") as f:
            f.write(new_content)
        print(f"OK: {bot_dir} - removed system path patterns")
    except Exception as e:
        print(f"ERROR: {bot_dir} - {e}")
