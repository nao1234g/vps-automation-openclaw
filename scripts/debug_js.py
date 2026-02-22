#!/usr/bin/env python3
"""Extract the filter JS from taxonomy page and check for syntax issues."""
import re, requests, urllib3
urllib3.disable_warnings()

html = requests.get("https://nowpattern.com/taxonomy-ja/", verify=False).text

# Find the codeinjection_foot script (should be the last script block)
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
print(f"Total scripts: {len(scripts)}")

# Find our filter script (has doSearch and createElement)
for i, s in enumerate(scripts):
    if "doSearch" in s and "createElement" in s:
        print(f"\nFilter script found at index {i}, {len(s)} chars")

        # Check bracket balance
        open_curly = s.count("{")
        close_curly = s.count("}")
        open_paren = s.count("(")
        close_paren = s.count(")")
        open_bracket = s.count("[")
        close_bracket = s.count("]")

        print(f"  Curly braces: {{ = {open_curly}, }} = {close_curly} {'OK' if open_curly == close_curly else 'MISMATCH!'}")
        print(f"  Parentheses: ( = {open_paren}, ) = {close_paren} {'OK' if open_paren == close_paren else 'MISMATCH!'}")
        print(f"  Brackets: [ = {open_bracket}, ] = {close_bracket} {'OK' if open_bracket == close_bracket else 'MISMATCH!'}")

        # Check key parts exist
        print(f"  Has 'var layers': {'var layers' in s}")
        print(f"  Has 'np-btn-search': {'np-btn-search' in s}")
        print(f"  Has 'contentEl': {'contentEl' in s}")
        print(f"  Has 'insertBefore': {'insertBefore' in s}")
        print(f"  Has 'innerHTML': {'innerHTML' in s}")
        print(f"  Has 'addEventListener': {'addEventListener' in s}")

        # Show first 500 chars
        print(f"\n  First 500 chars:\n{s[:500]}")
        break
