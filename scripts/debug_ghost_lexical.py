"""Debug: check what Ghost stores in lexical for the tag section."""
import requests, urllib3, json, hashlib, hmac, time, base64, os
urllib3.disable_warnings()

# Load API key from cron-env
with open("/opt/cron-env.sh", "r") as f:
    for line in f:
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[7:].split("=", 1)
            os.environ[k] = v

key = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
key_id, secret = key.split(":")

iat = int(time.time())
header = json.dumps({"alg": "HS256", "typ": "JWT", "kid": key_id}).encode()
payload = json.dumps({"iat": iat, "exp": iat + 300, "aud": "/admin/"}).encode()
def b64url(d): return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
h = b64url(header)
p = b64url(payload)
sig = hmac.new(bytes.fromhex(secret), f"{h}.{p}".encode(), hashlib.sha256).digest()
token = f"{h}.{p}.{b64url(sig)}"

r = requests.get(
    "https://nowpattern.com/ghost/api/admin/posts/699535ab4e0b36dac67af1df/?formats=html,lexical",
    headers={"Authorization": f"Ghost {token}"},
    verify=False,
)
post = r.json()["posts"][0]

# Show the html field (what Ghost renders)
html = post.get("html", "")
print("=== HTML length:", len(html))

# Find tag section in html
import re
tag_section = re.search(r'(ジャンル.*?経路依存.*?</div>)', html, re.DOTALL)
if tag_section:
    print("=== TAG SECTION IN HTML ===")
    print(tag_section.group(0)[:1000])
else:
    # Try broader search
    idx = html.find("ジャンル")
    if idx >= 0:
        print("=== Found ジャンル at pos", idx, "===")
        print(html[max(0,idx-100):idx+500])
    else:
        print("=== ジャンル NOT FOUND in html ===")
        print("First 500 chars:", html[:500])

# Show lexical structure
lexical = post.get("lexical", "")
if lexical:
    lex = json.loads(lexical)
    children = lex.get("root", {}).get("children", [])
    print(f"\n=== LEXICAL: {len(children)} top-level children ===")
    for i, child in enumerate(children[:5]):
        s = json.dumps(child, ensure_ascii=False)
        print(f"[{i}] type={child.get('type','')} | {s[:200]}")
