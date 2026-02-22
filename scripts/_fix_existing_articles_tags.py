#!/usr/bin/env python3
"""Fix existing Japanese articles that display English dynamics tag names.
Scans all published JA posts, checks for English tag names in HTML, and re-renders the tag badge section."""
import json, time, hashlib, hmac, base64, re
import urllib3; urllib3.disable_warnings()
import requests

# --- Ghost JWT ---
with open("/opt/cron-env.sh") as f:
    for line in f:
        if "NOWPATTERN_GHOST_ADMIN_API_KEY" in line:
            key = line.split("=", 1)[1].strip().strip("'").strip('"')
            break

kid, secret = key.split(":")
iat = int(time.time())
def b64url(d): return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
h = b64url(json.dumps({"alg":"HS256","typ":"JWT","kid":kid}).encode())
p = b64url(json.dumps({"iat":iat,"exp":iat+300,"aud":"/admin/"}).encode())
sig = hmac.new(bytes.fromhex(secret), f"{h}.{p}".encode(), hashlib.sha256).digest()
token = f"{h}.{p}.{b64url(sig)}"
headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}

# --- Load taxonomy for translation ---
with open("/opt/shared/scripts/nowpattern_taxonomy.json", encoding="utf-8") as f:
    tax = json.load(f)

en_to_ja = {}
for d in tax["dynamics"]:
    en_to_ja[d["name_en"]] = d["name_ja"]
for e in tax["events"]:
    en_to_ja[e["name_en"]] = e["name_ja"]
for g in tax["genres"]:
    en_to_ja[g["name_en"]] = g["name_ja"]

print(f"Translation table: {len(en_to_ja)} entries")

# --- Get all JA posts ---
r = requests.get(
    "https://nowpattern.com/ghost/api/admin/posts/?limit=all&include=tags&formats=lexical",
    headers={"Authorization": f"Ghost {token}"}, verify=False
)
posts = r.json().get("posts", [])
ja_posts = [p for p in posts if any(t["slug"] == "lang-ja" for t in p.get("tags", []))]
print(f"Total posts: {len(posts)}, JA posts: {len(ja_posts)}")

# --- Check and fix ---
fixed_count = 0
for post in ja_posts:
    lexical_str = post.get("lexical", "")
    if not lexical_str:
        continue

    needs_fix = False
    for en_name in en_to_ja:
        # Check if English tag name appears as a displayed tag (e.g., #Imperial Overreach)
        if f">{en_name}<" in lexical_str or f"#{en_name}<" in lexical_str:
            needs_fix = True
            break

    if not needs_fix:
        continue

    print(f"\n--- Fixing: {post['title'][:60]} (id={post['id']})")

    # Parse lexical to get HTML
    try:
        lexical = json.loads(lexical_str)
    except json.JSONDecodeError:
        print(f"  SKIP: Cannot parse lexical JSON")
        continue

    html_nodes = [n for n in lexical.get("root", {}).get("children", []) if n.get("type") == "html"]
    if not html_nodes:
        print(f"  SKIP: No HTML nodes found")
        continue

    html = html_nodes[0].get("html", "")
    original_html = html

    # Replace English tag names with Japanese in display text
    for en_name, ja_name in en_to_ja.items():
        # Replace in tag badge links: >#EnglishName< → >#日本語名<
        html = html.replace(f">#{en_name}</a>", f">#{ja_name}</a>")
        # Replace in NOW PATTERN section tag display
        html = html.replace(f">{en_name}<", f">{ja_name}<")

    if html == original_html:
        print(f"  No changes needed (pattern not matched)")
        continue

    # Update the lexical doc
    html_nodes[0]["html"] = html
    new_lexical = json.dumps(lexical, ensure_ascii=False)

    body = {
        "posts": [{
            "lexical": new_lexical,
            "updated_at": post["updated_at"],
        }]
    }

    r2 = requests.put(
        f"https://nowpattern.com/ghost/api/admin/posts/{post['id']}/",
        json=body, headers=headers, verify=False, timeout=30
    )

    if r2.status_code == 200:
        fixed_count += 1
        print(f"  OK: Fixed")
    else:
        print(f"  ERROR {r2.status_code}: {r2.text[:200]}")

    time.sleep(0.5)  # Rate limiting

print(f"\n=== Done: {fixed_count} articles fixed ===")
