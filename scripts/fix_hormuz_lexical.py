"""Re-update Hormuz article using lexical HTML card to preserve all styles."""
import requests, urllib3, json, hashlib, hmac, time, base64, os, sys
urllib3.disable_warnings()

sys.path.insert(0, "/opt/shared/scripts")

with open("/opt/cron-env.sh", "r") as f:
    for line in f:
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[7:].split("=", 1)
            os.environ[k] = v.strip('"').strip("'")

key = os.environ["NOWPATTERN_GHOST_ADMIN_API_KEY"]
key_id, secret = key.split(":")

iat = int(time.time())
def b64url(d): return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
h = b64url(json.dumps({"alg": "HS256", "typ": "JWT", "kid": key_id}).encode())
p = b64url(json.dumps({"iat": iat, "exp": iat + 300, "aud": "/admin/"}).encode())
sig = hmac.new(bytes.fromhex(secret), (h + "." + p).encode(), hashlib.sha256).digest()
token = h + "." + p + "." + b64url(sig)

# Step 1: Get current updated_at
r = requests.get(
    "https://nowpattern.com/ghost/api/admin/posts/699535ab4e0b36dac67af1df/",
    headers={"Authorization": "Ghost " + token}, verify=False)
post = r.json()["posts"][0]
updated_at = post["updated_at"]
print(f"Current updated_at: {updated_at}")

# Step 2: Generate HTML
from nowpattern_article_builder import build_deep_pattern_html
from gen_dynamics_diagram import generate_dynamics_diagram

diagram_svg = generate_dynamics_diagram(
    title="ホルムズ海峡危機の力学",
    nodes=[
        {"id": "iran", "label": "イラン (IRGC)", "x": 100, "y": 80},
        {"id": "us", "label": "米国", "x": 400, "y": 80},
        {"id": "gulf", "label": "湾岸諸国", "x": 100, "y": 250},
        {"id": "oil", "label": "石油市場", "x": 400, "y": 250},
        {"id": "talks", "label": "核交渉", "x": 250, "y": 160},
    ],
    edges=[
        {"from": "iran", "to": "oil", "label": "封鎖", "type": "dominance"},
        {"from": "oil", "to": "gulf", "label": "$93急騰", "type": "feedback"},
        {"from": "iran", "to": "talks", "label": "交渉テコ", "type": "capture"},
        {"from": "us", "to": "talks", "label": "制裁圧力", "type": "dominance"},
        {"from": "gulf", "to": "oil", "label": "迂回パイプライン", "type": "resistance"},
        {"from": "oil", "to": "us", "label": "ガソリン価格上昇", "type": "feedback"},
    ],
)

html = build_deep_pattern_html(
    title="イランがホルムズ海峡を一時封鎖した構造 — 世界の石油の20%を人質にとる交渉術",
    why_it_matters="世界の石油輸送の20%が通過するホルムズ海峡をイランが初めて実際に封鎖した。1988年タンカー戦争以来の直接行使であり、核交渉の構造が根本的に変わった。",
    facts=[
        ("72時間封鎖", "イラン革命防衛隊がホルムズ海峡を全面封鎖。商船の通過を完全停止"),
        ("$93/バレル", "ブレント原油が即座に急騰。2022年ウクライナ危機以来の高値圏"),
        ("日量2000万バレル", "世界の石油供給の約20%が封鎖により一時停止"),
    ],
    delta="イランがホルムズ海峡を72時間封鎖。石油市場が瞬時に反応し、ブレント原油が$93に急騰。1988年タンカー戦争以来の直接封鎖行使で、核交渉のテコとして「石油カード」を使う構造が再起動した。",
    big_picture_history="ホルムズ海峡は世界の石油輸送の約20%（日量1,700〜2,100万バレル）が通過する、地球上で最も重要なチョークポイントである。幅は最狭部で約33km。イランはこの海峡の北岸を支配しており、封鎖能力を持つ唯一の国家である。\n\n歴史的に、イランがこのカードを切るのは「追い詰められた時」である。1980年代のイラン・イラク戦争では両国がタンカーを攻撃し合い（タンカー戦争）、米海軍が護衛に出動した。2011-12年には経済制裁強化に反発して封鎖を示唆し、原油価格が15%急騰した。2019年にはタンカー2隻が機雷攻撃を受け、米・イラン間の緊張が極限に達した。\n\nしかし、実際に「全面封鎖」を実行したことは一度もなかった。封鎖はイラン自身の石油輸出も止めるため、自傷行為になるからだ。今回の72時間限定封鎖は、その禁忌を初めて破ったことに歴史的意義がある。",
    stakeholder_map=[
        ("イラン革命防衛隊（IRGC）", "核の平和利用の権利を守る", "制裁解除と体制保証を取引材料に。ハメネイ最高指導者の権力基盤強化", "原油価格上昇で制裁の穴埋め、交渉での主導権、国内求心力", "国際的孤立深化、軍事報復リスク、自国石油輸出の停止"),
        ("米国トランプ政権", "イランの核武装を阻止する", "ガソリン価格の国内政治への影響を最小化しつつ、強硬姿勢を維持したい", "中東同盟国との関係強化、軍産複合体", "ガソリン価格高騰→支持率低下、軍事介入のコスト"),
        ("サウジアラビア・UAE", "地域の安定と石油市場の秩序", "脱ホルムズ依存を加速し、イランとの勢力均衡を維持", "OPEC+での影響力拡大、迂回ルートの戦略価値上昇", "直接的な軍事紛争への巻き込まれ、石油施設への報復攻撃リスク"),
        ("中国・インド（石油輸入国）", "エネルギー安全保障の確保", "安価なイラン産原油の確保を続けたい。封鎖は双方に痛手", "イランとの二国間取引での価格交渉力", "石油供給途絶、経済成長への打撃"),
        ("石油トレーダー・投機筋", "市場の効率的な価格発見", "地政学リスクプレミアムからの利益最大化", "ボラティリティ上昇による短期利益", "予測不能な政治的解決による急落リスク"),
    ],
    dynamics_tags="危機便乗 × 対立の螺旋 × 経路依存",
    dynamics_sections=[
        {"tag": "危機便乗", "tag_en": "Crisis Exploitation", "explanation": "イランは核交渉の行き詰まりという「危機」を利用して、ホルムズ海峡封鎖という極端なカードを切った。封鎖による原油価格急騰は、制裁で疲弊したイラン経済への短期的なカンフル剤にもなる。"},
        {"tag": "対立の螺旋", "tag_en": "Escalation Spiral", "explanation": "制裁→封鎖→原油急騰→報復の脅威→さらなる軍事的緊張。各ステップが次のエスカレーションを正当化する構造。"},
        {"tag": "経路依存", "tag_en": "Path Dependency", "explanation": "世界の石油インフラがホルムズ海峡に依存する構造は数十年かけて形成された。代替ルート（パイプライン等）の整備は進むが、20%という依存度は容易に変わらない。"},
    ],
    genre_tags="地政学・安全保障, エネルギー・環境",
    event_tags="軍事衝突, 制裁・経済戦争, 資源紛争",
    scenarios=[
        {"label": "楽観", "probability": "20%", "title": "早期妥協", "content": "48時間以内に封鎖解除。米国が制裁の一部緩和を約束し、核交渉の枠組み再開で合意。原油は$80台に戻る。"},
        {"label": "基本", "probability": "55%", "title": "長期封鎖→段階的交渉", "content": "1-2週間の封鎖継続。原油は$100を突破。国際社会の仲介（中国・インド）で段階的解除と引き換えに制裁緩和の交渉開始。"},
        {"label": "悲観", "probability": "25%", "title": "軍事衝突", "content": "封鎖中に偶発的衝突が発生。米海軍とIRGC海軍の直接交戦。原油は$120超。地域全体の不安定化。"},
    ],
    pattern_history=[
        {"year": "1988", "title": "タンカー戦争（イラン・イラク戦争）", "content": "両国がタンカーを攻撃し合い、米海軍がペルシャ湾に展開。イラン海軍艦艇を撃沈。", "similarity": "軍事力の直接行使という点で最も近い先例。ただし1988年は戦争の一環であり、今回のような独立した封鎖行為とは文脈が異なる。"},
        {"year": "2012", "title": "EU対イラン石油禁輸+ホルムズ封鎖示唆", "content": "イランが封鎖を「示唆」しただけで原油が15%急騰。", "similarity": "脅しだけで市場を動かせた2012年と比較すると、今回は実際に封鎖を実行した分、インパクトが格段に大きい。"},
        {"year": "2019", "title": "タンカー攻撃事件（オマーン湾）", "content": "タンカー2隻が攻撃を受け、米がイランの関与を断定。", "similarity": "偶発的衝突のリスクが最も近い先例。"},
    ],
    source_urls=[
        ("Reuters: Iran closes Strait of Hormuz", "https://www.reuters.com/world/middle-east/"),
        ("IEA Oil Market Report", "https://www.iea.org/reports/oil-market-report-february-2026"),
        ("IISS Strategic Assessment", "https://www.iiss.org/research-paper/2026/02/hormuz-crisis/"),
    ],
    diagram_html=diagram_svg,
)

print(f"HTML generated: {len(html)} chars")

# Step 3: Send as lexical HTML card (preserves ALL HTML structure)
lexical_doc = {
    "root": {
        "children": [
            {
                "type": "html",
                "version": 1,
                "html": html
            }
        ],
        "direction": None,
        "format": "",
        "indent": 0,
        "type": "root",
        "version": 1
    }
}

url = "https://nowpattern.com/ghost/api/admin/posts/699535ab4e0b36dac67af1df/"
body = {
    "posts": [{
        "lexical": json.dumps(lexical_doc),
        "updated_at": updated_at,
    }]
}
resp = requests.put(url, json=body,
    headers={"Authorization": "Ghost " + token, "Content-Type": "application/json"},
    verify=False, timeout=30)

if resp.status_code == 200:
    pd = resp.json()["posts"][0]
    print(f"OK: Updated via lexical html card")
    print(f"html field: {len(pd.get('html', ''))} chars")
    print(f"lexical field: {len(pd.get('lexical', ''))} chars")
else:
    print(f"ERROR {resp.status_code}: {resp.text[:500]}")
