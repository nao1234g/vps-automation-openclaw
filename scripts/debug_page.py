#!/usr/bin/env python3
"""Debug: verify filter JS and content classes."""
import re, requests, urllib3
urllib3.disable_warnings()

html = requests.get("https://nowpattern.com/taxonomy-ja/", verify=False).text

print("=== JS Filter Code ===")
print("np-genre-chips in JS:", "np-genre-chips" in html)
print("insertBefore in JS:", "insertBefore" in html)
print("createElement in JS:", "createElement" in html)
print("doSearch in JS:", "doSearch" in html)
print("np-btn-search in JS:", "np-btn-search" in html)

print("\n=== Content Area Classes ===")
classes = re.findall(r'class="([^"]*)"', html)
content_classes = [c for c in classes if "content" in c.lower() or "post" in c.lower() or "article" in c.lower()]
for c in sorted(set(content_classes)):
    print(f"  {c}")

print("\n=== Article tag ===")
articles = re.findall(r"<article[^>]*>", html)
for a in articles[:3]:
    print(f"  {a}")
