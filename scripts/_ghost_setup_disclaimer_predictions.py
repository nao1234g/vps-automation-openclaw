#!/usr/bin/env python3
"""
Ghost CMS: ディスクレーマー自動挿入 + 予測トラックレコードページ作成
VPS上で実行: python3 /tmp/_ghost_setup.py
"""
import json, hashlib, hmac, time, base64, sys

try:
    import urllib3
    urllib3.disable_warnings()
    import requests
except ImportError:
    print("ERROR: pip install requests urllib3")
    sys.exit(1)

GHOST_URL = "http://localhost:2368"
API_KEY = "6995030a3b8c7ab6f20bfe27:c071ad0cfe5b40b44a57890899d3edda40f6caede282ca2eda66a82980634d2c"

def make_jwt(api_key):
    kid, secret = api_key.split(":")
    iat = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": kid}
    payload = {"iat": iat, "exp": iat + 300, "aud": "/admin/"}
    def b64url(d):
        return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
    h = b64url(json.dumps(header).encode())
    p = b64url(json.dumps(payload).encode())
    si = f"{h}.{p}"
    sig = hmac.new(bytes.fromhex(secret), si.encode(), hashlib.sha256).digest()
    return f"{si}.{b64url(sig)}"

token = make_jwt(API_KEY)
headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}

# =============================================
# TASK 1: Disclaimer (Code Injection Footer)
# =============================================
print("=== TASK 1: Add Disclaimer ===")

disclaimer_html = '''
<style>
.np-disclaimer {
  margin: 40px auto 0;
  max-width: 720px;
  padding: 20px 24px;
  border-top: 1px solid rgba(255,255,255,0.15);
  font-size: 12px;
  line-height: 1.6;
  color: rgba(255,255,255,0.45);
  text-align: center;
}
.np-disclaimer a {
  color: rgba(255,255,255,0.55);
  text-decoration: underline;
}
</style>
<div class="np-disclaimer">
  <strong>Disclaimer</strong><br>
  \u672c\u30b5\u30a4\u30c8\u306e\u8a18\u4e8b\u306f\u60c5\u5831\u63d0\u4f9b\u30fb\u6559\u80b2\u76ee\u7684\u306e\u307f\u3067\u3042\u308a\u3001\u6295\u8cc7\u52a9\u8a00\u3067\u306f\u3042\u308a\u307e\u305b\u3093\u3002\u8a18\u8f09\u3055\u308c\u305f\u30b7\u30ca\u30ea\u30aa\u3068\u78ba\u7387\u306f\u5206\u6790\u8005\u306e\u898b\u89e3\u3067\u3042\u308a\u3001\u5c06\u6765\u306e\u7d50\u679c\u3092\u4fdd\u8a3c\u3059\u308b\u3082\u306e\u3067\u306f\u3042\u308a\u307e\u305b\u3093\u3002\u904e\u53bb\u306e\u4e88\u6e2c\u7cbe\u5ea6\u306f\u5c06\u6765\u306e\u7cbe\u5ea6\u3092\u4fdd\u8a3c\u3057\u307e\u305b\u3093\u3002\u7279\u5b9a\u306e\u91d1\u878d\u5546\u54c1\u306e\u58f2\u8cb7\u3092\u63a8\u5968\u3057\u3066\u3044\u307e\u305b\u3093\u3002\u6295\u8cc7\u5224\u65ad\u306f\u8aad\u8005\u81ea\u8eab\u306e\u8cac\u4efb\u3067\u884c\u3063\u3066\u304f\u3060\u3055\u3044\u3002<br>
  This content is for informational and educational purposes only and does not constitute investment advice. Scenarios and probabilities are analytical opinions, not guarantees of future outcomes. Past prediction accuracy does not guarantee future accuracy. We do not recommend buying or selling any specific financial instruments. Investment decisions are solely the reader\u2019s responsibility.<br>
  <a href="/predictions/">Prediction Track Record</a>
</div>
'''

r = requests.get(f"{GHOST_URL}/ghost/api/admin/settings/", headers=headers, verify=False)
print(f"GET settings: {r.status_code}")

if r.status_code == 200:
    settings = r.json().get("settings", [])
    current_foot = ""
    for s in settings:
        if s.get("key") == "codeinjection_foot":
            current_foot = s.get("value", "") or ""
            print(f"Current footer length: {len(current_foot)} chars")

    if "np-disclaimer" not in current_foot:
        new_foot = current_foot + disclaimer_html
        body = {"settings": [{"key": "codeinjection_foot", "value": new_foot}]}
        r2 = requests.put(f"{GHOST_URL}/ghost/api/admin/settings/", json=body, headers=headers, verify=False)
        print(f"PUT settings: {r2.status_code}")
        if r2.status_code == 200:
            print("OK: Disclaimer added!")
        else:
            print(f"ERROR: {r2.text[:300]}")
    else:
        print("SKIP: Disclaimer already exists")
else:
    print(f"ERROR: {r.text[:300]}")

# =============================================
# TASK 2: Create /predictions/ page
# =============================================
print("\n=== TASK 2: Create /predictions/ Page ===")

r3 = requests.get(f"{GHOST_URL}/ghost/api/admin/pages/?filter=slug:predictions&limit=1", headers=headers, verify=False)
existing = r3.json().get("pages", [])
if existing:
    print(f"SKIP: /predictions/ already exists (id={existing[0]['id']})")
else:
    predictions_html = '''<div style="max-width:800px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">

<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:12px;padding:32px;margin-bottom:32px;border:1px solid rgba(255,26,117,0.3);">
<h2 style="color:#FF1A75;margin:0 0 12px;font-size:24px;">Prediction Track Record</h2>
<p style="color:rgba(255,255,255,0.7);margin:0;font-size:16px;line-height:1.6;">
Nowpattern\u306f\u5168\u3066\u306e\u8a18\u4e8b\u30673\u3064\u306e\u30b7\u30ca\u30ea\u30aa\uff08\u697d\u89b3\u30fb\u57fa\u672c\u30fb\u60b2\u89b3\uff09\u3068\u78ba\u7387\u3092\u63d0\u793a\u3057\u3001\u305d\u306e\u7d50\u679c\u3092\u8ffd\u8de1\u3057\u307e\u3059\u3002<br>
\u4e88\u6e2c\u7cbe\u5ea6\u306f <strong style="color:#FF1A75;">Brier Score</strong> \u3067\u5b9a\u91cf\u8a55\u4fa1\u3002\u900f\u660e\u6027\u3053\u305d\u304c\u4fe1\u983c\u306e\u57fa\u76e4\u3067\u3059\u3002
</p>
</div>

<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:32px;">
<div style="background:#1a1a2e;border-radius:8px;padding:20px;text-align:center;border:1px solid rgba(255,255,255,0.1);">
<div style="font-size:36px;font-weight:700;color:#FF1A75;" id="np-pred-total">\u2014</div>
<div style="font-size:13px;color:rgba(255,255,255,0.5);margin-top:4px;">Total Predictions</div>
</div>
<div style="background:#1a1a2e;border-radius:8px;padding:20px;text-align:center;border:1px solid rgba(255,255,255,0.1);">
<div style="font-size:36px;font-weight:700;color:#4ecdc4;" id="np-pred-resolved">\u2014</div>
<div style="font-size:13px;color:rgba(255,255,255,0.5);margin-top:4px;">Resolved</div>
</div>
<div style="background:#1a1a2e;border-radius:8px;padding:20px;text-align:center;border:1px solid rgba(255,255,255,0.1);">
<div style="font-size:36px;font-weight:700;color:#ffd93d;" id="np-pred-brier">\u2014</div>
<div style="font-size:13px;color:rgba(255,255,255,0.5);margin-top:4px;">Brier Score</div>
</div>
</div>

<div style="background:#1a1a2e;border-radius:12px;padding:24px;margin-bottom:24px;border:1px solid rgba(255,255,255,0.1);">
<h3 style="color:#fff;margin:0 0 16px;font-size:18px;">Brier Score\u3068\u306f</h3>
<table style="width:100%;border-collapse:collapse;font-size:14px;">
<tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
<td style="padding:8px 12px;color:rgba(255,255,255,0.7);">0.00</td>
<td style="padding:8px 12px;color:rgba(255,255,255,0.5);">\u5b8c\u74a7\u306a\u4e88\u6e2c\uff08\u7406\u8ad6\u4e0a\u306e\u4e0a\u9650\uff09</td>
</tr>
<tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
<td style="padding:8px 12px;color:#4ecdc4;font-weight:600;">0.10 - 0.15</td>
<td style="padding:8px 12px;color:rgba(255,255,255,0.5);">\u30b9\u30fc\u30d1\u30fc\u30d5\u30a9\u30fc\u30ad\u30e3\u30b9\u30bf\u30fc\u7d1a</td>
</tr>
<tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
<td style="padding:8px 12px;color:#ffd93d;">0.15 - 0.25</td>
<td style="padding:8px 12px;color:rgba(255,255,255,0.5);">\u5e73\u5747\u7684\u306a\u5c02\u9580\u5bb6\u30ec\u30d9\u30eb</td>
</tr>
<tr>
<td style="padding:8px 12px;color:#ff6b6b;">0.25+</td>
<td style="padding:8px 12px;color:rgba(255,255,255,0.5);">\u300c\u5168\u90e850/50\u300d\u3068\u540c\u3058\uff08\u30b9\u30ad\u30eb\u306a\u3057\uff09</td>
</tr>
</table>
</div>

<div style="background:#1a1a2e;border-radius:12px;padding:24px;margin-bottom:24px;border:1px solid rgba(255,255,255,0.1);">
<h3 style="color:#fff;margin:0 0 16px;font-size:18px;">\u65b9\u6cd5\u8ad6</h3>
<ol style="color:rgba(255,255,255,0.7);font-size:14px;line-height:1.8;padding-left:20px;margin:0;">
<li>\u5168\u8a18\u4e8b\u306b3\u3064\u306e\u30b7\u30ca\u30ea\u30aa\uff08\u697d\u89b3\u30fb\u57fa\u672c\u30fb\u60b2\u89b3\uff09\u3068\u78ba\u7387\u3092\u63d0\u793a</li>
<li>\u5404\u30b7\u30ca\u30ea\u30aa\u306b\u30c8\u30ea\u30ac\u30fc\u30a4\u30d9\u30f3\u30c8\uff08\u691c\u8a3c\u6642\u671f\uff09\u3092\u8a2d\u5b9a</li>
<li>\u30c8\u30ea\u30ac\u30fc\u5230\u9054\u6642\u306b\u7d50\u679c\u3092\u81ea\u52d5\u5224\u5b9a</li>
<li>Brier Score = (1/N) \u00d7 \u03a3(\u4e88\u6e2c\u78ba\u7387 - \u5b9f\u969b\u306e\u7d50\u679c)\u00b2 \u3067\u7cbe\u5ea6\u8a08\u7b97</li>
<li>\u56db\u534a\u671f\u3054\u3068\u306b\u7cbe\u5ea6\u30ec\u30dd\u30fc\u30c8\u3092\u516c\u958b</li>
</ol>
</div>

<div style="background:linear-gradient(135deg,#16213e,#0f3460);border-radius:12px;padding:24px;border:1px solid rgba(78,205,196,0.3);">
<h3 style="color:#4ecdc4;margin:0 0 12px;font-size:18px;">\u306a\u305c\u4e88\u6e2c\u3092\u8ffd\u8de1\u3059\u308b\u306e\u304b</h3>
<p style="color:rgba(255,255,255,0.7);font-size:14px;line-height:1.8;margin:0;">
\u591a\u304f\u306e\u30cb\u30e5\u30fc\u30b9\u30e1\u30c7\u30a3\u30a2\u306f\u4e88\u6e2c\u3092\u51fa\u3057\u3066\u3082\u3001\u5f53\u305f\u3063\u305f\u304b\u5916\u308c\u305f\u304b\u3092\u691c\u8a3c\u3057\u307e\u305b\u3093\u3002<br>
Nowpattern\u306f<strong style="color:#fff;">\u5168\u3066\u306e\u4e88\u6e2c\u3092\u8a18\u9332\u3057\u3001\u7d50\u679c\u3092\u516c\u958b</strong>\u3057\u307e\u3059\u3002<br>
\u3053\u306e\u900f\u660e\u6027\u304c\u3001\u6642\u9593\u3068\u3068\u3082\u306b\u6700\u5927\u306e\u30e2\u30fc\u30c8\uff08\u53c2\u5165\u969c\u58c1\uff09\u306b\u306a\u308a\u307e\u3059\u3002<br>
<br>
<em style="color:rgba(255,255,255,0.5);">\u4e88\u6e2c\u7cbe\u5ea6\u30c7\u30fc\u30bf\u306f\u8a18\u4e8b\u84c4\u7a4d\u306b\u4f34\u3044\u66f4\u65b0\u3055\u308c\u307e\u3059\u3002</em>
</p>
</div>

</div>'''

    lexical_doc = {
        "root": {
            "children": [{"type": "html", "version": 1, "html": predictions_html}],
            "direction": None, "format": "", "indent": 0,
            "type": "root", "version": 1,
        }
    }

    body = {
        "pages": [{
            "title": "Prediction Track Record",
            "slug": "predictions",
            "lexical": json.dumps(lexical_doc),
            "status": "published",
            "tags": [{"name": "Nowpattern", "slug": "nowpattern"}],
        }]
    }

    r4 = requests.post(f"{GHOST_URL}/ghost/api/admin/pages/", json=body, headers=headers, verify=False)
    print(f"POST page: {r4.status_code}")
    if r4.status_code == 201:
        page = r4.json()["pages"][0]
        print(f"OK: Created -> {page.get('url', '')}")
    else:
        print(f"ERROR: {r4.text[:500]}")

print("\n=== DONE ===")
