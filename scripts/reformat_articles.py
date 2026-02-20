#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存の build_speed_log_html / _build_tag_badges を使って
9英語記事 + 3日本語記事を正しいSpeed Logフォーマットで再更新する。
英語記事はラベルを Genre: / Event: / Dynamics: / Base scenario: に変更。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json, time, hashlib, hmac, base64
import urllib3; urllib3.disable_warnings()
import requests

# nowpattern_article_builder から正規の関数とスタイルをインポート
from nowpattern_article_builder import _STYLES, _build_facts_html

API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
GHOST_URL = "https://nowpattern.com"

def make_jwt(key):
    kid, secret = key.split(":")
    iat = int(time.time())
    def b64u(d): return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
    h = b64u(json.dumps({"alg":"HS256","typ":"JWT","kid":kid}).encode())
    p = b64u(json.dumps({"iat":iat,"exp":iat+300,"aud":"/admin/"}).encode())
    s = f"{h}.{p}"
    sig = hmac.new(bytes.fromhex(secret), s.encode(), hashlib.sha256).digest()
    return f"{s}.{b64u(sig)}"

def hdrs():
    return {"Authorization": f"Ghost {make_jwt(API_KEY)}", "Content-Type": "application/json"}

def get_updated_at(pid):
    r = requests.get(f"{GHOST_URL}/ghost/api/admin/posts/{pid}/?fields=updated_at",
        headers=hdrs(), verify=False, timeout=15)
    return r.json().get("posts", [{}])[0].get("updated_at", "")

# ─── タグバッジ生成（日本語 / 英語ラベル切替）─────────────────────────
def _build_tag_badges_en(genre_tags: str, event_tags: str, dynamics_tags: str) -> str:
    """英語記事用: Genre / Event / Dynamics ラベル"""
    import unicodedata

    def slugify(name: str) -> str:
        s = unicodedata.normalize("NFKC", name.lower())
        s = s.replace(" ", "-").replace("&", "and").replace("/", "-")
        s = "".join(c for c in s if c.isalnum() or c in "-_")
        return s.strip("-") or "tag"

    rows = []
    genres = [g.strip() for g in genre_tags.replace("/", ",").split(",") if g.strip()]
    if genres:
        spans = "".join(f'<a href="/tag/{slugify(g)}/" {_STYLES["tag_genre"]}>#{g}</a>' for g in genres)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>Genre:</span>{spans}</div>')

    events = [e.strip() for e in event_tags.replace("/", ",").split(",") if e.strip()]
    if events:
        spans = "".join(f'<a href="/tag/{slugify(e)}/" {_STYLES["tag_event"]}>#{e}</a>' for e in events)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>Event:</span>{spans}</div>')

    dynamics = [d.strip() for d in dynamics_tags.replace(" × ", ",").replace("×", ",").replace("/", ",").split(",") if d.strip()]
    if dynamics:
        spans = "".join(f'<a href="/tag/{slugify(d)}/" {_STYLES["tag_dynamics"]}>#{d}</a>' for d in dynamics)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>Dynamics:</span>{spans}</div>')

    return "\n".join(rows)

def _build_tag_badges_ja(genre_tags: str, event_tags: str, dynamics_tags: str) -> str:
    """日本語記事用: ジャンル / イベント / 力学 ラベル"""
    import unicodedata

    def slugify(name: str) -> str:
        s = unicodedata.normalize("NFKC", name.lower())
        s = s.replace(" ", "-").replace("・", "-").replace("/", "-")
        s = "".join(c for c in s if c.isalnum() or c in "-_")
        return s.strip("-") or "tag"

    rows = []
    genres = [g.strip() for g in genre_tags.replace("/", ",").replace("、", ",").split(",") if g.strip()]
    if genres:
        spans = "".join(f'<a href="/tag/{slugify(g)}/" {_STYLES["tag_genre"]}>#{g}</a>' for g in genres)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>ジャンル:</span>{spans}</div>')

    events = [e.strip() for e in event_tags.replace("/", ",").replace("、", ",").split(",") if e.strip()]
    if events:
        spans = "".join(f'<a href="/tag/{slugify(e)}/" {_STYLES["tag_event"]}>#{e}</a>' for e in events)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>イベント:</span>{spans}</div>')

    dynamics = [d.strip() for d in dynamics_tags.replace(" × ", ",").replace("×", ",").replace("/", ",").replace("、", ",").split(",") if d.strip()]
    if dynamics:
        spans = "".join(f'<a href="/tag/{slugify(d)}/" {_STYLES["tag_dynamics"]}>#{d}</a>' for d in dynamics)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>力学:</span>{spans}</div>')

    return "\n".join(rows)

# ─── Speed Log HTML 生成（日英共通テンプレート）────────────────────────
def build_speed_log(lang, genre_tags, event_tags, dynamics_tags,
                    why_it_matters, facts, dynamics_tag, dynamics_one_liner,
                    base_scenario, source_title, source_url):

    tag_badges = (_build_tag_badges_en if lang == "en" else _build_tag_badges_ja)(
        genre_tags, event_tags, dynamics_tags
    )
    facts_html = _build_facts_html(facts)
    base_label = "Base scenario" if lang == "en" else "基本シナリオ"

    source_line = ""
    if source_url and source_title:
        source_line = f'<p><strong>Source:</strong> <a href="{source_url}" {_STYLES["footer_link"]}>{source_title}</a></p>'

    return f"""<!-- Tag Badges -->
<div style="margin: 0 0 20px 0; padding-bottom: 12px; border-bottom: 1px solid #e0dcd4;">
{tag_badges}
</div>

<!-- Why it matters -->
<blockquote {_STYLES["why_box"]}>
  <strong {_STYLES["why_strong"]}>Why it matters:</strong> {why_it_matters}
</blockquote>

<hr {_STYLES["hr"]}>

<h2 {_STYLES["h2"]}>What happened</h2>
{facts_html}

<hr {_STYLES["hr"]}>

<div {_STYLES["pattern_box"]}>
  <h2 {_STYLES["pattern_h2"]}>NOW PATTERN</h2>
  <p {_STYLES["pattern_tag"]}>{dynamics_tag}</p>
  <p {_STYLES["pattern_body"]}>{dynamics_one_liner}</p>
</div>

<hr {_STYLES["hr"]}>

<h2 {_STYLES["h2"]}>What's Next</h2>
<p><strong>{base_label}:</strong> {base_scenario}</p>

<hr {_STYLES["hr"]}>

<div {_STYLES["footer"]}>
  {source_line}
</div>"""

# ─── 12記事のデータ ────────────────────────────────────────────────────
ARTICLES = [
    {
        "id": "699779e45850354f44049bbe",
        "lang": "en",
        "title": "Munich Security Conference 2026 — Five Signals That the Western Alliance Fracture Is Now Structural",
        "genre_tags": "Geopolitics",
        "event_tags": "Alliance Fracture",
        "dynamics_tags": "Alliance Fracture × Institutional Decay",
        "why_it_matters": "Munich 2026 documented the functional end of the post-Cold War security consensus. What was agreed matters less than what European leaders openly said — and what Beijing quietly noted.",
        "facts": [
            ("Feb 14–16, 2026", "Munich Security Conference convenes amid active Russia-Ukraine talks and a Trump administration openly hostile to multilateral commitments"),
            ("Signal 1: U.S. belligerence", "Trump's transactional view of alliances confirmed as a permanent variable, not a temporary disruption"),
            ("Signal 2: European autonomy threshold", "French-led discussions of independent European nuclear deterrence frameworks — politically inconceivable 24 months ago"),
            ("Signal 3: Russia's dual-track", "Moscow treats military pressure and diplomatic engagement as complementary, not alternative strategies"),
            ("Signal 4: China's strategic observation", "Every visible NATO fracture reduces Beijing's perceived cost of probing in the Indo-Pacific"),
            ("Signal 5: Architecture concluded", "The post-Cold War security consensus 1991–2022 is functionally over; what replaces it is being built in real time"),
        ],
        "dynamics_tag": "Alliance Fracture × Institutional Decay",
        "dynamics_one_liner": "The unconditional nature of the U.S. Article 5 commitment — NATO's foundational assumption — is now openly contested. The most strategically significant audience at Munich was not in the room: it was in Beijing.",
        "base_scenario": "European defence spending continues rising; formal U.S. commitments narrow toward Indo-Pacific priority; NATO remains nominally intact but operationally bifurcated.",
        "source_title": "The Hill: 5 takeaways from a tense Munich Security Conference",
        "source_url": "https://thehill.com/policy/international/5740684-us-europe-ties-munich-conference/",
    },
    {
        "id": "699779e05850354f44049bb1",
        "lang": "en",
        "title": "Largest Sewage Spill in U.S. History — The Federal Government Owns the Facility It's Blaming Others For",
        "genre_tags": "Society / Politics & Policy",
        "event_tags": "Institutional Decay / Regulatory Change",
        "dynamics_tags": "Institutional Decay × Narrative Control",
        "why_it_matters": "The Potomac sewage spill — the largest in U.S. history — was caused by a federally owned facility. Trump blamed Maryland Democrats. The real story is a multi-trillion dollar infrastructure backlog that predates every administration being blamed.",
        "facts": [
            ("Feb 17, 2026", "Maryland Governor Moore's office contradicts Trump: the federal government has owned and operated the relevant facility since the last century"),
            ("Scale", "Classified as the largest sewage spill in U.S. history — public health and environmental implications extend well beyond one news cycle"),
            ("Infrastructure context", "U.S. water and wastewater infrastructure, largely built 1940–1970, is at or beyond design lifespan across dozens of cities nationwide"),
            ("Jurisdictional dispute", "Factual ownership is a question for federal agency review and legal adjudication — not social media exchanges between elected officials"),
        ],
        "dynamics_tag": "Institutional Decay × Narrative Control",
        "dynamics_one_liner": "U.S. infrastructure accountability has become a partisan blame game, not an engineering or public health problem. The Potomac spill is a symptom of a multi-trillion dollar deferred maintenance backlog — the political exchange is a costly distraction from the structural issue.",
        "base_scenario": "Federal-state blame exchange continues; EPA investigation opens but produces no actionable accountability within the news cycle; infrastructure investment bill stalls in partisan gridlock.",
        "source_title": "The Hill: Moore's office fires back at Trump after Potomac sewage spill blame",
        "source_url": "https://thehill.com/homenews/administration/5741034-trump-moore-potomac-waste-spill/",
    },
    {
        "id": "699779dd5850354f44049ba8",
        "lang": "en",
        "title": "Russia Launched 400 Drones Hours Before Geneva Peace Talks — Violence as a Negotiating Card",
        "genre_tags": "Geopolitics",
        "event_tags": "Military Conflict / Sanctions & Law",
        "dynamics_tags": "Escalation Spiral × Coordination Failure",
        "why_it_matters": "Russia launched one of its largest barrages of the war on the same day Geneva peace talks opened — while France released a Russian shadow fleet tanker after a fine. Nineteen rounds of sanctions have not altered Moscow's cost-benefit analysis. Round 20 will not either.",
        "facts": [
            ("Feb 17, 2026", "Russia launches ~400 drones + 29 missiles against Ukraine hours before Geneva peace talks — a deliberate signal that military pressure and diplomacy are complementary"),
            ("Shadow fleet release", "France detains then releases a suspected Russian shadow fleet tanker after a multimillion-euro fine — the legal ceiling of unilateral enforcement"),
            ("Sanctions Round 20", "EU confirms a 20th package of sanctions against Russia; 19 prior rounds have not produced structural behavioural change in Moscow"),
            ("Asian energy reach", "A significant portion of Russian crude reaching India and China transits via vessels operating outside SWIFT-linked financial systems"),
        ],
        "dynamics_tag": "Escalation Spiral × Coordination Failure",
        "dynamics_one_liner": "Europe's enforcement infrastructure is not built to match its stated resolve. Fines are priced into shadow fleet operational economics — detention periods are legally bounded without an international sanctions-enforcement framework specifically designed for these vessels.",
        "base_scenario": "Geneva talks produce a ceasefire framework; Russia continues hybrid pressure during negotiations; Europe's enforcement capacity remains constrained without a dedicated international legal instrument.",
        "source_title": "The Guardian: Ukraine talks begin in Geneva as Russia fires record drone barrage",
        "source_url": "https://www.theguardian.com/world/live/2026/feb/17/ukraine-talks-geneva-russia-zelenskyy-putin-orban-rubio-latest-news-updates",
    },
    {
        "id": "699779d95850354f44049b9d",
        "lang": "en",
        "title": "\"Trump Practically Destroyed NATO in Under a Year\" — A U.S. Senator Said It Out Loud at Munich",
        "genre_tags": "Geopolitics",
        "event_tags": "Alliance Fracture",
        "dynamics_tags": "Alliance Fracture × Narrative Control",
        "why_it_matters": "Sen. Mark Kelly's statement — \"less than a year to practically destroy NATO\" — was made by a U.S. senator departing the world's premier security forum. When America's own legislators use the word 'destroy', the transatlantic crisis has moved from management into open rupture.",
        "facts": [
            ("Feb 15, 2026", "Sen. Mark Kelly (D-AZ) posts on X: Trump has taken 'less than a year to practically destroy' NATO; Russia and China are benefiting from the resulting instability"),
            ("Conference atmosphere", "European leaders held open discussions of defence autonomy timelines — including independent nuclear deterrence — that were politically inconceivable 24 months ago"),
            ("Bipartisan concern", "Congressional anxiety about U.S. alliance erosion spans party lines, providing institutional weight against executive discretion"),
            ("Beijing signal", "Every visible NATO fracture reduces Beijing's perceived cost of probing in the South China Sea and across the Taiwan Strait"),
        ],
        "dynamics_tag": "Alliance Fracture × Narrative Control",
        "dynamics_one_liner": "The most strategically significant audience for Kelly's statement is not in Washington or Brussels — it is in Beijing. Chinese strategic planners calibrate risk tolerance based on U.S. alliance cohesion assessments. Every public fracture is a green-light calculation update.",
        "base_scenario": "NATO remains institutionally intact; U.S. commitment becomes explicitly conditional on European burden-sharing; Japan and South Korea begin asking publicly what European allies are asking privately.",
        "source_title": "The Hill: Kelly rails against Trump as Munich Security Conference ends",
        "source_url": "https://thehill.com/homenews/senate/5739714-kelly-rails-against-trump-as-munich-security-conference-ends/",
    },
    {
        "id": "6997259e5850354f44049b8b",
        "lang": "en",
        "title": "New START Expired With No Replacement — For the First Time Since 1972, No Nuclear Arms Agreement Exists Between the U.S. and Russia",
        "genre_tags": "Geopolitics",
        "event_tags": "Institutional Decay / Escalation Spiral",
        "dynamics_tags": "Institutional Decay × Escalation Spiral",
        "why_it_matters": "For the first time since Nixon signed SALT I in 1972, there is no legally binding nuclear arms control agreement between the U.S. and Russia. No inspection regime. No verified warhead limits. And U.S. foreign policy is now run on personal intuition, not institutional guardrails.",
        "facts": [
            ("2026", "New START — the last formal nuclear arms control agreement between the U.S. and Russia — expires with no successor framework in place"),
            ("Verification gap", "Without New START, no legal inspection regime exists to verify warhead counts or deployment postures for either side"),
            ("Trump's diplomacy model", "Direct personal engagement with adversary leaders bypasses State Department and NSC institutional processes — removing crisis management infrastructure"),
            ("Weaponised supply chains", "Export controls, rare earth dependencies, and financial sanctions create escalation pathways structurally harder to control than conventional military ones"),
            ("Cuban Missile Crisis lesson", "That crisis was resolved through structured back-channels and institutional protocols — the infrastructure being dismantled now was built from those lessons"),
        ],
        "dynamics_tag": "Institutional Decay × Escalation Spiral",
        "dynamics_one_liner": "The most dangerous combination in nuclear security is not capability — both sides have had survivable second-strike capacity for decades. It is opacity (no verification) + speed (hypersonic delivery) + decision-making by personal intuition rather than structured crisis management protocols.",
        "base_scenario": "No new arms control framework in 2026; Russian and U.S. nuclear modernisation continues without mutual visibility; risk of miscalculation elevated at the margins of any direct confrontation.",
        "source_title": "The Hill: Trump is betting the farm on intuition — and the nuclear clock is ticking",
        "source_url": "https://thehill.com/opinion/international/5739962-new-start-treaty-expiration/",
    },
    {
        "id": "69967cdf5850354f44049b77",
        "lang": "en",
        "title": "Bitcoin Miners Are Flexible Grid Assets, Not Energy Hogs — Paradigm's Argument That Regulators Are Getting Wrong",
        "genre_tags": "Crypto & Web3 / Energy & Environment",
        "event_tags": "Regulatory Change / Tech Breakthrough",
        "dynamics_tags": "Narrative Control × Regulatory Capture",
        "why_it_matters": "Bitcoin miners are being regulated out of markets based on a comparison that doesn't hold up to basic grid engineering. The conflation with AI data centers is politically convenient and analytically wrong — the regulatory difference has major consequences for clean energy economics.",
        "facts": [
            ("Feb 16, 2026", "Paradigm publishes analysis: Bitcoin miners function as interruptible, flexible demand resources — a fundamentally different grid characteristic from AI data centers"),
            ("ERCOT evidence", "Texas grid operator documented large-scale Bitcoin miners voluntarily curtailing consumption during extreme weather demand spikes — actively stabilising the grid"),
            ("AI vs Bitcoin distinction", "AI inference/training = inflexible baseload that strains peak capacity; Bitcoin mining rigs can be powered down in seconds and restarted without data loss"),
            ("Clean energy opportunity", "Flexible mining demand can monetise renewable energy surplus that would otherwise be curtailed — a direct complement to intermittent solar and wind"),
            ("Regulatory risk", "Conflating miners and AI data centers eliminates flexible grid-balancing assets while leaving actual peak demand growth untouched"),
        ],
        "dynamics_tag": "Narrative Control × Regulatory Capture",
        "dynamics_one_liner": "The conflation of Bitcoin mining and AI data centers in energy policy is not accidental — it is politically convenient for those who want to restrict both on environmental grounds without engaging with technical distinctions. The consequence is regulation that eliminates grid-stabilising assets.",
        "base_scenario": "Grid operators in deregulated markets (ERCOT) continue demand-response programmes with Bitcoin miners; federal energy regulation applies AI data center standards to mining, creating regulatory arbitrage across state lines.",
        "source_title": "CoinTelegraph: Paradigm reframes Bitcoin mining as grid asset, not energy drain",
        "source_url": "https://cointelegraph.com/news/paradigm-bitcoin-mining-ai-data-centers-grid-demand",
    },
    {
        "id": "69967cdc5850354f44049b6a",
        "lang": "en",
        "title": "Bundesbank President Backs Euro Stablecoins — Europe Declares Digital Monetary Sovereignty a National Security Priority",
        "genre_tags": "Economy & Finance / Crypto & Web3",
        "event_tags": "Regulatory Change / Geopolitics",
        "dynamics_tags": "Platform Power × Alliance Fracture",
        "why_it_matters": "When a G7 central bank president publicly endorses private stablecoins, something structural has shifted. Bundesbank President Nagel's move is not fintech enthusiasm — it is a geopolitical alarm triggered by the U.S. GENIUS Act, which threatens to entrench dollar dominance in blockchain financial infrastructure.",
        "facts": [
            ("Feb 16, 2026", "Bundesbank President Joachim Nagel publicly endorses euro-pegged stablecoins and CBDCs as instruments giving the EU 'more independence' from dollar-pegged coins legitimised by the GENIUS Act"),
            ("GENIUS Act threat", "Creates a compliant regulatory pathway for USD-pegged stablecoins (USDC, USDT) — threatening to entrench dollar dominance in blockchain-based financial infrastructure at scale"),
            ("MiCA moat", "EU's MiCA requires euro-denomination reserves and EU-based issuers, creating a regulatory advantage for European stablecoin projects over U.S. competitors"),
            ("Yen exposure", "Japan's digital yen project is years behind both the digital euro and potential dollar-pegged stablecoin proliferation — a monetary sovereignty gap widening in real time"),
        ],
        "dynamics_tag": "Platform Power × Alliance Fracture",
        "dynamics_one_liner": "Monetary sovereignty in the 21st century will partly be determined by who controls the digital payment rails. The euro-dollar stablecoin competition is a direct extension of reserve currency geopolitics into blockchain infrastructure — and creates an immediate strategic problem for every non-USD, non-EUR financial system.",
        "base_scenario": "Euro-pegged stablecoins gain institutional adoption under MiCA; GENIUS Act stablecoins dominate DeFi and cross-border retail payments; the yen's role in international digital finance is further marginalised without an accelerated digital yen deployment.",
        "source_title": "CoinTelegraph: Germany's central bank president touts stablecoin and CBDC benefits for EU",
        "source_url": "https://cointelegraph.com/news/germany-central-bank-president-stablecoins",
    },
    {
        "id": "69967cce5850354f44049b5f",
        "lang": "en",
        "title": "Russia's $650M Daily Crypto Volume Confirmed by Its Own Ministry of Finance — Sanctions Evasion Is Now a Formalised Economic System",
        "genre_tags": "Crypto & Web3 / Geopolitics",
        "event_tags": "Sanctions & Law / Regulatory Change",
        "dynamics_tags": "Crisis Exploitation × Institutional Decay",
        "why_it_matters": "$650 million every single day. Russia's Ministry of Finance has put a number on what Western regulators spent three years trying to suppress. Spring legislation will not liberalise Russian crypto — it will construct a state-controlled infrastructure designed to make sanctions evasion permanent, scalable, and legally defensible.",
        "facts": [
            ("Feb 16, 2026", "Russia's Ministry of Finance confirms daily crypto turnover exceeds $650M — annualised ~$237B, placing Russia among the world's largest crypto economies by volume"),
            ("Legislative timeline", "Government and central bank officials fast-tracking comprehensive crypto regulation for the spring 2026 parliamentary session — a formal pivot from prohibition to state-managed utilisation"),
            ("Use cases confirmed", "International trade settlement bypassing SWIFT, oligarch asset preservation, military procurement financing, and retail ruble-hedging"),
            ("State surveillance model", "Russian crypto regulation will not resemble Western frameworks — it will grant the state full visibility into flows, taxation capacity, and strategic direction of crypto infrastructure"),
            ("Template risk", "North Korea, Iran, and Venezuela are studying Moscow's adaptation — this is the emerging template for every sanctions-exposed authoritarian state"),
        ],
        "dynamics_tag": "Crisis Exploitation × Institutional Decay",
        "dynamics_one_liner": "Russia has transformed a sanctions-era grey market into a formalised state-controlled economic system. Spring legislation entrenches, rather than eliminates, crypto-based sanctions evasion — and exports a surveillance-crypto governance model to every authoritarian state watching closely.",
        "base_scenario": "Russia passes spring crypto legislation; daily volumes continue growing; Western regulators face pressure to act on exchanges processing Russian flows while lacking jurisdiction over the underlying infrastructure.",
        "source_title": "CoinDesk: Russia's daily crypto turnover is over $650 million, Ministry of Finance says",
        "source_url": "https://www.coindesk.com/business/2026/02/16/russia-s-daily-crypto-turnover-is-over-usd650-million-ministry-of-finance-says",
    },
    {
        "id": "6996289d5850354f44049b3d",
        "lang": "en",
        "title": "Colby Says NATO Is \"Stronger Than Ever\" — His Real Message: Europe Must Defend Itself So the U.S. Can Pivot to China",
        "genre_tags": "Geopolitics",
        "event_tags": "Alliance Fracture / Geopolitics",
        "dynamics_tags": "Alliance Fracture × Platform Power",
        "why_it_matters": "Elbridge Colby — the Pentagon's 'deny China' strategist — says NATO is 'stronger than ever.' Strip away the reassurance: the U.S. is explicitly conditioning European security on European self-sufficiency, deliberately freeing American strategic bandwidth for the Pacific.",
        "facts": [
            ("Feb 14, 2026", "Foreign Policy publishes Colby's interview asserting NATO's strength while addressing White House commitment to European security — first major statement post-Munich from the Pentagon's top policymaker"),
            ("Colby's framework", "Identifies China as the 'pacing threat' requiring primary U.S. strategic focus; repositions Ukraine as a resource-allocation problem competing with Indo-Pacific priorities"),
            ("Empirical basis", "European defence spending risen sharply since 2022; Finland and Sweden joined NATO; eastern flank reinforced — the factual basis for 'stronger than ever'"),
            ("Conditional reassurance", "U.S. commitment implicitly contingent on Europeans continuing to increase burden-sharing — the same transactional logic will be applied to Japan, South Korea, and the Philippines"),
            ("Tokyo implication", "The question 'will the U.S. actually come?' — asked privately in European capitals — will be asked openly in Tokyo within two years if the current trajectory continues"),
        ],
        "dynamics_tag": "Alliance Fracture × Platform Power",
        "dynamics_one_liner": "Every dollar Europe spends on its own defence is a dollar that buys U.S. bandwidth in the Indo-Pacific. Colby's reassurance is mathematically conditional — and Tokyo knows it. Japan's acceleration of counterstrike capabilities is the direct response to this calculus.",
        "base_scenario": "European defence spending hits 3% GDP targets by 2027; U.S. force posture in Europe reduces; NATO remains collective in name while operationally bifurcating between European-led and U.S.-led Indo-Pacific strategy.",
        "source_title": "Foreign Policy: Elbridge Colby — 'NATO Is Actually Stronger Than Ever'",
        "source_url": "https://foreignpolicy.com/2026/02/14/elbridge-colby-us-russia-nato-america-first/",
    },
    # ── 日本語記事 ──────────────────────────────────────────────────────
    {
        "id": "69967ce55850354f44049b80",
        "lang": "ja",
        "title": "暗号資産市場が1兆ドル縮小する中、現実資産トークン化（RWA）が13.5%成長した理由",
        "genre_tags": "暗号資産・Web3 / 経済・金融",
        "event_tags": "資本移動・投資 / 技術進展",
        "dynamics_tags": "プラットフォーム支配 × 後発逆転",
        "why_it_matters": "暗号資産市場全体が1兆ドル縮小した同時期に、トークン化されたRWA（現実資産）のオンチェーン総価値が13.5%増加した。BlackRock・JPMorgan・Goldman Sachsの参入が示すのは「投機からインフラへ」という構造的転換だ。",
        "facts": [
            ("13.5%増", "暗号資産市場が過去30日で約1兆ドル減少する中、RWAオンチェーン総価値は同期間に13.5%増加"),
            ("機関投資家が牽引", "BlackRock（BUIDL）、JPMorgan Chase、Goldman SachsがRWA市場の主要プレイヤーとして確認"),
            ("ブロックチェーン別純増", "Ethereum +17億ドル、Arbitrum +8.8億ドル、Solana +5.3億ドル"),
            ("トークン化国債", "発行残高が100億ドル超に到達——政府債務がオンチェーンで流通し始めた"),
            ("ウォレット数増加", "RWAを保有するユニークウォレットアドレス数が増加——機関だけでなく個人の参入も始まっている"),
        ],
        "dynamics_tag": "プラットフォーム支配 × 後発逆転",
        "dynamics_one_liner": "「本物の金融」がブロックチェーン技術を活用し始めている。BlackRockが動いたとき、それは単なるトレンドではなく構造的な変化だ。RWA市場の成長は「投機的デジタルカジノ」から「実用的金融インフラ」へのシフトを示している。",
        "base_scenario": "機関投資家のRWA参入が加速し2027年末に発行残高5,000億ドル超へ。暗号資産市場全体のボラティリティとは無相関な成長が続き、伝統的金融とDeFiの境界が消え始める。",
        "source_title": "CoinTelegraph: Tokenized RWAs climb 13.5% despite $1T crypto market drawdown",
        "source_url": "https://cointelegraph.com/news/tokenized-rwas-climb-despite-crypto-market-rout",
    },
    {
        "id": "6995d4285850354f44049b25",
        "lang": "ja",
        "title": "トランプが排ガス規制を撤廃 — EV義務化消滅でトヨタが有利、テスラは逆風",
        "genre_tags": "政治・政策 / エネルギー・環境",
        "event_tags": "規制変更 / 公共政策・税制",
        "dynamics_tags": "ショック・ドクトリン × 経路依存",
        "why_it_matters": "トランプ政権が2009年のオバマ決定を覆し、自動車排ガス規制を撤廃した。米国の「2035年EV義務化」が実質消滅し、欧州・中国がEV規制を維持する中で、日本の自動車産業は「国ごとに異なる未来」への対応を迫られる。",
        "facts": [
            ("規制撤廃", "トランプ政権がオバマ政権の「温室効果ガスは公衆衛生への脅威」という決定を取り消し、排ガス規制を撤廃"),
            ("EV義務化消滅", "「2035年EV義務化」路線から完全転換。EV移行への政府義務がなくなった"),
            ("トヨタ有利", "ハイブリッド車が強みの日本勢にとって短期的な息継ぎのチャンス。米国でのガソリン・HV販売継続が容認される"),
            ("テスラ逆風", "米国市場での優遇措置・補助金が消滅。EV専業メーカーへの逆風が強まる"),
            ("石油株にプラス", "ガソリン需要の下落ペースが遅くなり、エクソンモービル・シェブロンなどに長期的なポジティブ材料"),
            ("長期リスク", "中国BYDが世界市場でEVシェアを拡大する中、日本がガソリン車に足を引っ張られる構造的リスクが残る"),
        ],
        "dynamics_tag": "ショック・ドクトリン × 経路依存",
        "dynamics_one_liner": "米国だけがEV義務化から撤退したとき、グローバルで戦う自動車メーカーは「どの市場の基準で車を設計するか」という根本的なジレンマに直面する。短期的恩恵と長期的な競争劣位が同時に発生する経路依存の罠だ。",
        "base_scenario": "2026年は日本の自動車大手が米国でHV・ガソリン車の販売を維持し業績が回復。しかし2028年以降、欧州・中国のEV基準に適合できないモデルの市場縮小が顕在化し始める。",
        "source_title": "NHK: 米トランプ政権 自動車排ガス規制撤廃を発表（2026年2月13日）",
        "source_url": "https://www3.nhk.or.jp/news/html/20260213/k10015050631000.html",
    },
    {
        "id": "6995d4215850354f44049b13",
        "lang": "ja",
        "title": "ルビオ＝王毅会談の裏側 — 関税・台湾・半導体、米中「取引外交」の優先順位",
        "genre_tags": "地政学・安全保障 / 政治・政策",
        "event_tags": "選挙・政権 / 市場変動",
        "dynamics_tags": "面子の出口 × 対立の螺旋",
        "why_it_matters": "ルビオ国務長官と王毅外相がミュンヘンで会談。「対話と協力を強化」という外交言語の裏で進むのは4月トランプ訪中に向けた実務調整だ。関税・台湾・半導体のどれを先に解決するかで、2026年後半のグローバル市場の方向性が決まる。",
        "facts": [
            ("会談実施", "ルビオ国務長官と王毅外相がドイツ・ミュンヘンで会談。中国外務省は「対話と協力を強化」と発表"),
            ("4月訪中の地ならし", "実態は4月予定のトランプ大統領訪中に向けた事務的調整——どの問題をどの順番で解決するかの整理"),
            ("関税の構図", "米：中国製品への60%関税維持 / 中：即時撤廃を要求"),
            ("台湾の構図", "米：武器売却権を保持 / 中：売却反対・一つの中国原則"),
            ("半導体の構図", "米：先端半導体の対中輸出規制維持 / 中：規制撤廃を要求"),
            ("訪中成立の条件", "関税の段階的削減合意 / 台湾武器売却の一時停止 / フェンタニル対策協力——いずれかの「手土産」が必要"),
        ],
        "dynamics_tag": "面子の出口 × 対立の螺旋",
        "dynamics_one_liner": "米中どちらも「譲歩した」と見られることなく対話を継続する構造的な必要性がある。ルビオ＝王毅会談は本音を隠したまま撤退するための儀式的な動き——4月訪中の成否が2026年後半のグローバル市場の方向性を決める分水嶺だ。",
        "base_scenario": "4月訪中が実現し関税の一部段階的削減で合意。中国株・人民元が上昇しグローバル市場にリスクオン。ただし構造問題（台湾・半導体）は先送りされ2027年に再燃するリスクが残る。",
        "source_title": "NHK: 米国務長官と中国外相が会談 トランプ大統領 訪中に向け調整か（2026年2月14日）",
        "source_url": "https://www3.nhk.or.jp/news/html/20260214/k10015051441000.html",
    },
]

# ─── Ghost更新 ───────────────────────────────────────────────────────
def update_post(pid, html, title, updated_at):
    lexical_doc = {
        "root": {
            "children": [{"type": "html", "version": 1, "html": html}],
            "direction": None, "format": "", "indent": 0,
            "type": "root", "version": 1,
        }
    }
    body = {"posts": [{"title": title, "lexical": json.dumps(lexical_doc), "updated_at": updated_at}]}
    r = requests.put(f"{GHOST_URL}/ghost/api/admin/posts/{pid}/",
        json=body, headers=hdrs(), verify=False, timeout=30)
    return r.status_code == 200, r.text[:300]

ok_count = 0
for art in ARTICLES:
    updated_at = get_updated_at(art["id"])
    html = build_speed_log(
        lang=art["lang"],
        genre_tags=art["genre_tags"],
        event_tags=art["event_tags"],
        dynamics_tags=art["dynamics_tags"],
        why_it_matters=art["why_it_matters"],
        facts=art["facts"],
        dynamics_tag=art["dynamics_tag"],
        dynamics_one_liner=art["dynamics_one_liner"],
        base_scenario=art["base_scenario"],
        source_title=art["source_title"],
        source_url=art["source_url"],
    )
    ok, msg = update_post(art["id"], html, art["title"], updated_at)
    status = "OK" if ok else "ERROR"
    print(f"[{status}] {art['title'][:55]}...")
    if ok:
        ok_count += 1
    else:
        print(f"       {msg}")

print(f"\n完了: {ok_count}/{len(ARTICLES)} 件更新")
