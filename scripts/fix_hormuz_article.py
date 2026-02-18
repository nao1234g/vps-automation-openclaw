"""
既存のホルムズ海峡記事をGhost API ?source=html で更新する修正スクリプト。
"""
import sys, os, json
sys.path.insert(0, "/opt/shared/scripts")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests

from nowpattern_article_builder import build_deep_pattern_html
from nowpattern_publisher import make_ghost_jwt, update_ghost_post
from gen_dynamics_diagram import generate_dynamics_diagram

# Load env
env = {}
with open("/opt/cron-env.sh") as f:
    for line in f:
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            kv = line[7:]
            k, v = kv.split("=", 1)
            v = v.strip('"').strip("'")
            env[k] = v

api_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
ghost_url = "https://nowpattern.com"
post_id = "699535ab4e0b36dac67af1df"

# Step 1: Get updated_at
token = make_ghost_jwt(api_key)
headers = {"Authorization": f"Ghost {token}"}
resp = requests.get(
    f"{ghost_url}/ghost/api/admin/posts/{post_id}/",
    headers=headers, verify=False, timeout=15,
)
post_data = resp.json()["posts"][0]
updated_at = post_data["updated_at"]
print(f"Current updated_at: {updated_at}")
print(f"Current html length: {len(post_data.get('html', '') or '')}")

# Step 2: Regenerate article HTML
diagram_svg = generate_dynamics_diagram(
    diagram_type="flow",
    title="ホルムズ海峡の力学構造",
    nodes=[
        {"id": "iran", "label": "イラン\nIRGC", "type": "power"},
        {"id": "us", "label": "米国\nトランプ政権", "type": "power"},
        {"id": "oil", "label": "世界石油市場\n日量1300万バレル", "type": "affected"},
        {"id": "gulf", "label": "湾岸諸国\nサウジ・UAE", "type": "neutral"},
        {"id": "talks", "label": "核協議\nジュネーブ", "type": "regulator"},
    ],
    edges=[
        {"from": "iran", "to": "oil", "label": "封鎖カード", "type": "dominance"},
        {"from": "us", "to": "iran", "label": "軍事圧力", "type": "dominance"},
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
    dynamics_sections=[
        {
            "tag": "危機便乗",
            "subheader": "Crisis Exploitation",
            "lead": "イランは核交渉が行き詰まるたびに「ホルムズカード」をちらつかせてきた。今回は初めてそれを実行に移した。",
            "quotes": [
                ("もし我々の石油が輸出できないなら、この地域の誰の石油も輸出させない", "イラン革命防衛隊司令官（2018年の発言、今回実行）"),
                ("72時間の封鎖は「警告射撃」であり、次は期限を設けない", "匿名のイラン外交筋（ロイター）"),
            ],
            "analysis": "危機便乗の力学が明確に作動している。イランは追い詰められた状況（制裁強化、核合意崩壊、国内経済危機）を「封鎖実行」の正当化に利用した。これは典型的な「弱者の恫喝」戦略であり、失うものが少ない側が大きなリスクを取ることで交渉力を獲得するメカニズムである。\n\n重要なのは、72時間という期限を自ら設けた点だ。これは「完全な封鎖」ではなく「封鎖できるという証明」であり、次の交渉ラウンドでの最大の武器となる。市場がパニックで反応したことが、このカードの有効性を証明してしまった。",
        },
        {
            "tag": "対立の螺旋",
            "subheader": "Escalation Spiral",
            "lead": "制裁→経済悪化→強硬姿勢→さらなる制裁という悪循環が、ついに物理的な封鎖に到達した。",
            "quotes": [
                ("イランを追い詰めすぎた。追い詰められた動物は噛みつく", "元CIA中東担当（CNN）"),
                ("エスカレーションのラダーで次のステップは軍事衝突しかない", "英国際戦略研究所（IISS）"),
            ],
            "analysis": "2018年のトランプ第1期でのJCPOA（核合意）離脱以降、米・イラン関係は一貫して悪化の螺旋を辿ってきた。制裁強化→イランの経済苦境→ウラン濃縮度引き上げ→さらなる制裁→ミサイル開発加速→地域紛争への介入拡大→そして今回の海峡封鎖。\n\nこの螺旋構造の本質は、双方にエスカレーションを止めるインセンティブがないことだ。トランプ政権は「強硬姿勢」が支持基盤に受けるため妥協できず、イラン側は体制維持のために「屈しない」姿勢を示す必要がある。合理的な妥協点は存在するが、国内政治がそれを許さない。",
        },
        {
            "tag": "経路依存",
            "subheader": "Path Dependency",
            "lead": "湾岸諸国はホルムズ依存からの脱却を30年間試みてきたが、構造的に不可能だった。",
            "quotes": [
                ("代替ルートは存在するが、ホルムズの容量を完全に代替することは物理的に不可能", "IEAエグゼクティブディレクター"),
                ("我々は1日500万バレルの迂回能力を持つ。しかしホルムズは2000万バレルだ", "サウジアラムコ幹部"),
            ],
            "analysis": "経路依存の力学がここで最も強く作用している。世界は「ホルムズ海峡が閉鎖されない」という前提で石油インフラを構築してきた。サウジのEast-Westパイプライン（日量500万バレル）やUAEのフジャイラ・パイプライン（日量150万バレル）は代替として機能するが、合計650万バレルではホルムズの2,000万バレルの3分の1にすぎない。\n\nこの経路依存は意図的なものでもある。安価な海上輸送に依存する方が経済合理的であり、迂回パイプラインの建設コスト（数百億ドル）を正当化できる政治家はいなかった。今回の封鎖により、その「合理的な怠慢」のツケが一気に顕在化した。",
        },
    ],
    scenarios=[
        ("交渉再開シナリオ", "55%", "72時間封鎖の「成果」を持ってイランが交渉テーブルに戻る。米国も国内ガソリン価格対策としてバックチャネル交渉を開始。3-6ヶ月以内に暫定合意の枠組みが成立。原油は$80-85に回帰。", "エネルギー関連株は一時的な急騰後に正常化。中期的にはENI、Shellなど中東エクスポージャーの大きい企業を注視。"),
        ("慢性的緊張シナリオ", "35%", "交渉は再開するが実質的な進展なし。イランが「次の封鎖」を示唆し続け、$5-10の地政学リスクプレミアムが原油価格に恒常的に上乗せされる。湾岸諸国が迂回パイプライン建設を加速。", "パイプライン建設企業（McDermott、Saipem等）、防衛関連（Raytheon、Lockheed Martin）に長期的な恩恵。原油価格は$85-95のレンジ。"),
        ("軍事衝突シナリオ", "10%", "米艦隊とIRGC高速艇の偶発的衝突がエスカレーション。限定的な軍事行動が発生するが、双方とも全面戦争を回避。しかし石油市場は$110+に急騰し、世界的なインフレ圧力が再燃。", "金（Gold）、国債、スイスフランなど安全資産へ逃避。エネルギー自給率の高い国（ノルウェー、カナダ）の資産が相対的に有利。"),
    ],
    pattern_history=[
        {"year": "1988", "title": "タンカー戦争（プレイング・マンティス作戦）", "content": "米海軍がイラン海軍フリゲート艦を撃沈。ペルシャ湾での直接軍事衝突。原油は一時的に急騰したが、冷戦構造下で全面戦争には発展せず。", "similarity": "海峡での軍事的緊張→原油急騰→外交的解決のパターンが類似。しかし今回は米の中東プレゼンスが大幅に縮小しており、同じ抑止力が効くかは不明。"},
        {"year": "2012", "title": "EU対イラン石油禁輸+ホルムズ封鎖示唆", "content": "イランが封鎖を「示唆」しただけで原油が15%急騰。実際には封鎖せず、最終的にJCPOA（核合意）への道を開いた。", "similarity": "脅しだけで市場を動かせた2012年と比較すると、今回は実際に封鎖を実行した分だけ、脅しの信憑性と市場インパクトが格段に大きい。"},
        {"year": "2019", "title": "タンカー攻撃事件（オマーン湾）", "content": "日本のタンカーを含む2隻が攻撃を受け、米がイランの関与を断定。トランプが軍事攻撃を「10分前に中止」した事件。", "similarity": "偶発的衝突のリスクが最も近い先例。今回も72時間の封鎖中に偶発的衝突が起きれば、2019年以上のエスカレーションに繋がる可能性。"},
    ],
    source_urls=[
        ("Reuters: Iran closes Strait of Hormuz", "https://www.reuters.com/world/middle-east/"),
        ("IEA Oil Market Report", "https://www.iea.org/reports/oil-market-report-february-2026"),
        ("IISS Strategic Assessment", "https://www.iiss.org/research-paper/2026/02/hormuz-crisis/"),
    ],
    genre_tags="地政学・安全保障, エネルギー・環境",
    event_tags="軍事衝突, 制裁・経済戦争, 資源紛争",
    dynamics_tags="危機便乗 × 対立の螺旋 × 経路依存",
    diagram_html=diagram_svg,
)

print(f"HTML generated: {len(html)} chars")

# Step 3: Update via ?source=html
result = update_ghost_post(
    post_id=post_id,
    html=html,
    updated_at=updated_at,
    ghost_url=ghost_url,
    admin_api_key=api_key,
)

if "error" in result:
    print(f"FAILED: {result}")
else:
    html_len = len(result.get("html", "") or "")
    print(f"SUCCESS: html_length={html_len}")
    print(f"Slug: {result.get('slug', '')}")
    print(f"URL: {ghost_url}/{result.get('slug', '')}/")
