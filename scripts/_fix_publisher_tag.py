#!/usr/bin/env python3
"""Fix the lang_tag line in nowpattern_publisher.py"""
path = "/opt/shared/scripts/nowpattern_publisher.py"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "lang_tag = " in line and "language ==" in line:
        lines[i] = '    lang_tag = "\u65e5\u672c\u8a9e" if language == "ja" else "English"\n'
        print(f"Fixed line {i+1}: {lines[i].strip()}")
        break

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Done!")
