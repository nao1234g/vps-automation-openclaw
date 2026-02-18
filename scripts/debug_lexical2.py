"""Check current lexical structure of Hormuz article."""
import requests, urllib3, json, hashlib, hmac, time, base64, os
urllib3.disable_warnings()

with open("/opt/cron-env.sh", "r") as f:
    for line in f:
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[7:].split("=", 1)
            os.environ[k] = v

key = os.environ["NOWPATTERN_GHOST_ADMIN_API_KEY"]
key_id, secret = key.split(":")
iat = int(time.time())
def b64url(d): return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
h = b64url(json.dumps({"alg": "HS256", "typ": "JWT", "kid": key_id}).encode())
p = b64url(json.dumps({"iat": iat, "exp": iat + 300, "aud": "/admin/"}).encode())
sig = hmac.new(bytes.fromhex(secret), (h + "." + p).encode(), hashlib.sha256).digest()
token = h + "." + p + "." + b64url(sig)

r = requests.get(
    "https://nowpattern.com/ghost/api/admin/posts/699535ab4e0b36dac67af1df/?formats=lexical",
    headers={"Authorization": "Ghost " + token},
    verify=False,
)
post = r.json()["posts"][0]
lex = json.loads(post["lexical"])
children = lex["root"]["children"]
print("Total children:", len(children))
for i, c in enumerate(children[:5]):
    t = c.get("type", "?")
    s = json.dumps(c, ensure_ascii=False)[:250]
    print(f"[{i}] type={t} | {s}")
print("...")
