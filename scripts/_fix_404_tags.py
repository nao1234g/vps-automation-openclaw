#!/usr/bin/env python3
"""Fix Ghost 404 articles by replacing wrong tag (lang-ja slug lang-ja-2) with correct tag (日本語 slug lang-ja)."""
import requests, jwt, datetime, urllib3, time
urllib3.disable_warnings()

with open("/opt/cron-env.sh") as f:
    for line in f:
        if "NOWPATTERN_GHOST_ADMIN_API_KEY" in line:
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

kid, secret = key.split(":")

def get_token():
    iat = int(datetime.datetime.now().timestamp())
    header = {"alg": "HS256", "typ": "JWT", "kid": kid}
    payload = {"iat": iat, "exp": iat + 300, "aud": "/admin/"}
    return jwt.encode(payload, bytes.fromhex(secret), algorithm="HS256", headers=header)

BASE = "https://nowpattern.com/ghost/api/admin"

# Get broken posts (with tags)
token = get_token()
r = requests.get(
    f"{BASE}/posts/?limit=all&include=tags&fields=id,title,slug,url,status,updated_at",
    headers={"Authorization": f"Ghost {token}"},
    verify=False
)
posts = r.json().get("posts", [])
broken = [p for p in posts if "/404/" in p.get("url", "")]
print(f"Found {len(broken)} broken articles")

for p in broken:
    post_id = p["id"]
    title = p["title"][:60]
    updated_at = p["updated_at"]
    tags = p.get("tags", [])

    print(f"\nFixing: {title}")
    tag_names = [t["name"] for t in tags]
    print(f"  Current tags: {tag_names}")

    # Replace wrong tag names with correct ones
    new_tags = []
    for t in tags:
        tname = t["name"]
        if tname == "lang-ja":
            new_tags.append({"name": "\u65e5\u672c\u8a9e"})  # 日本語
            print("  -> Replacing 'lang-ja' with correct tag")
        elif tname == "lang-en":
            new_tags.append({"name": "English"})
            print("  -> Replacing 'lang-en' with correct tag")
        else:
            new_tags.append({"name": tname})

    token = get_token()
    headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}
    resp = requests.put(
        f"{BASE}/posts/{post_id}/",
        json={"posts": [{"tags": new_tags, "updated_at": updated_at}]},
        headers=headers,
        verify=False
    )

    if resp.status_code == 200:
        new_url = resp.json()["posts"][0].get("url", "")
        print(f"  -> Updated! New URL: {new_url}")

        time.sleep(1)
        test = requests.get(new_url, verify=False, timeout=5, allow_redirects=True)
        print(f"  -> HTTP test: {test.status_code}")
    else:
        print(f"  -> ERROR: {resp.status_code} {resp.text[:150]}")

    time.sleep(1)

print("\nDone!")
