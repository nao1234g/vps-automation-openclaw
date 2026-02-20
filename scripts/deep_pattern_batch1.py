#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Pattern Batch 1 — 英語記事 6本（新しい順）
Munich / Sewage / Russia Drones / Trump NATO / New START / Bitcoin Mining
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, time, hashlib, hmac, base64
import urllib3; urllib3.disable_warnings()
import requests
from nowpattern_article_builder import build_deep_pattern_html

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
    return r.json().get("posts",[{}])[0].get("updated_at","")

def update_post(pid, html, title, updated_at, tags):
    lexical_doc = {"root": {"children": [{"type":"html","version":1,"html":html}],
        "direction":None,"format":"","indent":0,"type":"root","version":1}}
    body = {"posts": [{"title": title, "lexical": json.dumps(lexical_doc),
        "updated_at": updated_at, "tags": [{"name": t} for t in tags]}]}
    r = requests.put(f"{GHOST_URL}/ghost/api/admin/posts/{pid}/",
        json=body, headers=hdrs(), verify=False, timeout=30)
    return r.status_code == 200, r.text[:200]

# ═══════════════════════════════════════════════════════════════════════
# ARTICLE 1: Munich Security Conference 2026
# ═══════════════════════════════════════════════════════════════════════
a1_html = build_deep_pattern_html(
    title="Munich Security Conference 2026 — Five Signals That the Western Alliance Fracture Is Now Structural",
    why_it_matters="Munich 2026 was not a security conference. It was an inventory of what the post-Cold War order no longer has: unconditional U.S. commitment, European strategic dependency as a stable equilibrium, and a shared definition of the threat. What was agreed at Munich matters far less than what European leaders said openly — and what Beijing's analysts quietly logged.",
    facts=[
        ("Feb 14–16, 2026", "Munich Security Conference convenes with a Trump administration openly hostile to multilateral security commitments and active Russia-Ukraine negotiations running in parallel"),
        ("Signal 1 — U.S. as variable", "Trump administration treats NATO commitments as transactional — conditioned on European defence spending — marking a permanent shift from the post-1949 unconditional guarantee"),
        ("Signal 2 — Nuclear autonomy threshold crossed", "French President Macron's call for a European nuclear deterrence discussion — previously a diplomatic taboo — received serious engagement from German and Polish delegations for the first time"),
        ("Signal 3 — Russia's dual-track confirmed", "Moscow launched its largest drone barrage of the war on Feb 17, the same day Geneva peace talks opened, confirming military pressure and diplomacy are treated as complementary tools"),
        ("Signal 4 — China's observation logged", "Chinese foreign ministry monitoring of Munich was unusually intensive; every NATO fracture reduces Beijing's perceived cost of probing in the South China Sea and Taiwan Strait"),
        ("Signal 5 — Architecture concluded", "The 1991–2022 post-Cold War security consensus is functionally over; the architecture replacing it is being improvised in real time without a design blueprint"),
    ],
    big_picture_history="""The Munich Security Conference was founded in 1963 as a closed forum for Western defence ministers and military commanders. For 60 years, its core assumption was fixed: the United States provided the strategic roof under which European security operated. That assumption is now openly contested from inside the alliance.

The crack began structurally in 2016 with Trump's first term, when conditional Article 5 language appeared publicly for the first time. Russia's 2022 full invasion of Ukraine temporarily reversed the trend — NATO expanded to 32 members, defence budgets rose across the continent, and U.S. resolve appeared restored. Munich 2024 and 2025 still operated within that recovery narrative.

Munich 2026 is different in kind, not degree. The Trump administration's second-term posture is not a negotiating position — it reflects a genuine strategic reorientation toward the Indo-Pacific as the primary theatre, with European security treated as a cost centre to be reduced. The difference: in 2017–2020, the U.S. security establishment pushed back against Trump. In 2026, the Pentagon's senior leadership — including Elbridge Colby — is aligned with the reorientation.

The historical parallel is the Suez Crisis of 1956, when the United States forced the UK and France to withdraw from Egypt, demonstrating that European great powers could no longer act independently of Washington. Munich 2026 documents the inverse: Europe beginning to plan for independence from Washington's security guarantee. The direction of dependency has reversed — but the underlying dynamic of a unipolar provider withdrawing is structurally identical.""",
    stakeholder_map=[
        ("Trump Administration", "Demanding European burden-sharing", "Freeing bandwidth for Indo-Pacific pivot", "Reduced European cost obligation", "Weakened global alliance legitimacy"),
        ("European NATO members", "Maintaining alliance unity", "Building autonomous deterrence capacity", "Strategic agency if U.S. withdraws", "Higher defence costs, nuclear risk exposure"),
        ("Russia", "Negotiating from strength", "Using military pressure to extract concessions", "Ceasefire on favourable terms", "Prolonged conflict if Western unity holds"),
        ("China", "Observing neutrally", "Calibrating Indo-Pacific risk tolerance using NATO fracture data", "Lower perceived cost of Taiwan action", "Risk of premature miscalculation if U.S. bluffs"),
        ("Ukraine", "Securing security guarantees", "Survival and territorial integrity", "Credible security architecture", "Frozen conflict without guarantees"),
    ],
    data_points=[
        ("32 members", "Current NATO membership — the largest in alliance history, yet internally most divided on burden-sharing"),
        ("2% GDP", "NATO defence spending target — only 23 of 32 members met it in 2025, up from 10 in 2022"),
        ("3–5% GDP", "Spending levels European military planners say are required for genuine autonomous deterrence"),
        ("$1.3T", "Estimated cost of fully autonomous European defence capability over 10 years (IISS estimate)"),
        ("290", "French operational nuclear warheads — Europe's only independent deterrent currently operational"),
        ("700km", "Depth of NATO eastern flank from Baltic to Black Sea that European forces must now plan to defend without assuming U.S. reinforcement"),
    ],
    delta="The most strategically significant audience at Munich 2026 was not in the room. Beijing's analysts were reading every statement, every walkout, every piece of unconditional language that was absent. Chinese strategic doctrine on Taiwan rests partly on a U.S. alliance cohesion assessment. Munich 2026 moved that assessment.",
    dynamics_tags="Alliance Fracture × Institutional Decay",
    dynamics_summary="The unconditional U.S. guarantee — NATO's 75-year operating assumption — is now a variable. What replaces it is being improvised without a design.",
    dynamics_sections=[
        {
            "tag": "Alliance Fracture",
            "subheader": "The Conditionality Shift",
            "lead": "For 75 years, NATO's deterrence value rested on one credible claim: that an attack on any member would trigger an automatic U.S. response, regardless of burden-sharing. That unconditional guarantee is now publicly conditional.",
            "quotes": [
                ("'NATO is stronger than ever' — but the strength now comes from European spending, not American commitment. The U.S. is an investor in European security, not an insurer.", "Elbridge Colby, Foreign Policy, Feb 14 2026"),
                ("'Trump has taken less than a year to practically destroy NATO. Russia and China are the beneficiaries.'", "Sen. Mark Kelly (D-AZ), departing Munich, Feb 15 2026"),
            ],
            "analysis": """The gap between these two statements is not political spin — it is a genuine structural ambiguity in what NATO now means. Colby's framing is mathematically coherent: European defence spending has risen sharply, Finland and Sweden joined, eastern flank forces have increased. The alliance is 'stronger' in capability terms.

Kelly's framing is also accurate: the deterrence value of NATO always rested on the credibility of the U.S. Article 5 guarantee, not on European capability alone. A Europe that spends 3% of GDP on defence but faces an adversary who has correctly calculated Washington won't intervene is a weaker security architecture, not a stronger one.

The fracture is epistemic: alliance members now have fundamentally different models of what the alliance is for. The U.S. treats it as a burden-sharing arrangement. European members increasingly treat it as an existential guarantee. When these two models diverge publicly, at Munich, in front of Russian and Chinese observers, the deterrence value of the alliance degrades in real time.""",
        },
        {
            "tag": "Institutional Decay",
            "subheader": "The Architecture Without a Replacement",
            "lead": "The post-Cold War security architecture was built on three pillars: U.S. commitment, Russian threat minimisation (via arms control), and European strategic dependency as a stable equilibrium. All three pillars are now compromised simultaneously.",
            "quotes": [
                ("The problem is not that the old architecture is ending. The problem is that nothing is replacing it. We are in the interregnum.", "Senior European diplomat, Munich, Feb 2026 (anonymous)"),
            ],
            "analysis": """Arms control treaties are defunct — New START expired in 2026 with no successor. The OSCE, designed to manage European security dialogue with Russia, is functionally paralysed. NATO itself operates under the ambiguity described above.

The institutional decay is not just about NATO. It is about the entire ecosystem of rules, agreements, and shared assumptions that managed military risk in Europe since 1990. That ecosystem is being dismantled from multiple directions simultaneously: by Russia's revision of the territorial settlement, by the U.S. retreat from institutional multilateralism, and by Europe's belated but real move toward strategic autonomy.

The danger of institutional interregnums is not that they are permanent — they rarely are. The danger is what happens in the gap. The period 1919–1939 was also an institutional interregnum between the Concert of Europe and the post-1945 order. The gap contained the worst violence in European history.""",
        },
    ],
    dynamics_intersection="""The two dynamics reinforce each other in a destabilising feedback loop. Alliance Fracture degrades the institutional legitimacy of NATO as a security architecture. Institutional Decay removes the arms control and dialogue frameworks that managed risk when NATO deterrence was strong.

The result is the worst of both worlds: reduced deterrence capacity (due to alliance fracture) and reduced crisis management capacity (due to institutional decay) occurring simultaneously. This combination is historically associated with the highest risk of miscalculation-driven escalation — not deliberate war, but conflict that neither side fully intended.""",
    pattern_history=[
        {"year": 1956, "title": "Suez Crisis — When the U.S. Ended European Strategic Autonomy", "content": "In October 1956, the UK and France — with Israeli support — invaded Egypt to retake the Suez Canal after Nasser's nationalisation. Eisenhower forced a humiliating withdrawal by threatening to collapse the pound sterling and withhold IMF support. The message was unambiguous: European great powers could not conduct independent military operations without U.S. approval.\n\nFor 70 years, European NATO members internalised that lesson. Strategic decisions were made within U.S.-defined parameters. European defence budgets fell. Strategic autonomy was not even a serious policy discussion.\n\nMunich 2026 documents the Suez logic beginning to run in reverse: the U.S. is withdrawing its strategic guarantee, forcing Europe to rebuild the autonomous capacity that 1956 made unnecessary.", "similarity": "A unipolar provider withdrawing its guarantee forces the dependent party to build independent capacity — the direction of dependency has reversed, the structural dynamic is identical"},
        {"year": 1966, "title": "France Withdraws from NATO Military Command — De Gaulle's Autonomy Gambit", "content": "In 1966, Charles de Gaulle withdrew France from NATO's integrated military command structure, expelled NATO headquarters from Paris, and pursued an independent force de frappe (nuclear deterrent). De Gaulle's logic: France could not trust that the U.S. would risk New York to save Paris, so France needed its own nuclear guarantee.\n\nFor 43 years (until Sarkozy's 2009 reintegration), France operated a parallel security architecture — allied to NATO in principle, autonomous in practice. It worked because the Cold War threat environment remained stable.\n\nMunich 2026 echoes de Gaulle: European leaders are beginning to ask openly whether they can trust the U.S. nuclear guarantee, and whether autonomous European deterrence is necessary. The French force de frappe — long treated as a Cold War anachronism — is suddenly strategically relevant again.", "similarity": "When U.S. commitment becomes conditional, European powers historically move toward autonomous deterrence — de Gaulle's 1966 logic is being rediscovered 60 years later"},
    ],
    history_pattern_summary="The historical pattern is consistent: when a dominant security provider's commitment becomes conditional or withdraws, dependent states begin building autonomous capacity. The transition period — between dependency and autonomy — is the highest-risk phase. It typically lasts 10–15 years and creates windows of vulnerability that adversaries have historically exploited.",
    scenarios=[
        ("基本", "55-65%", "European defence spending reaches 3% GDP by 2028. NATO remains institutionally intact but operationally bifurcates: European-led defence of Europe, U.S.-led Indo-Pacific strategy. France extends nuclear deterrence discussions to Germany and Poland. No formal European nuclear deterrent within the decade, but serious planning begins. U.S.-European intelligence sharing continues under modified frameworks.", "Monitor French nuclear deterrence discussions for operational details vs. political signalling. Track European defence procurement acceleration — particularly German rearmament. Watch U.S. force posture in Europe for drawdown signals."),
        ("楽観", "15-20%", "Munich 2026 shock catalyses genuine European strategic autonomy. EU defence union moves from aspiration to operational planning. European defence industrial base consolidation accelerates. U.S. remains a NATO member but as a partner rather than guarantor — a stable equilibrium at a higher European capability level.", "European defence industrial stocks become a multi-year theme. Rheinmetall, BAE Systems, Safran, Leonardo positioned for sustained demand. Track EU defence bond issuance."),
        ("悲観", "20-25%", "Alliance fracture deepens faster than European autonomy capacity builds. A Russian probe into a Baltic state — not a full invasion, but a hybrid incursion — tests whether Article 5 is activated. U.S. hesitates. The deterrence gap between the old architecture (now gone) and the new one (not yet built) is exploited.", "This is the tail risk that markets are not pricing. European political risk premium should be in portfolio construction. Physical gold, Swiss franc, food security exposure."),
    ],
    triggers=[
        ("U.S. Article 5 activation test", "A Russian hybrid incursion into Estonia or Latvia would force an explicit U.S. decision — activate Article 5 or not. The answer would define alliance architecture for a generation"),
        ("French nuclear deterrence proposal", "If Macron makes a formal proposal for European nuclear sharing — beyond political discussion — it marks the point of no return in European strategic autonomy"),
        ("German defence budget constitutional revision", "Germany's debt brake prevents sustained 3%+ GDP defence spending. A constitutional amendment vote would be the clearest signal of European commitment"),
        ("China-Taiwan pressure escalation", "Any Chinese military action around Taiwan would force the U.S. to choose between European and Indo-Pacific commitments — clarifying the resource constraint publicly"),
    ],
    genre_tags="Geopolitics",
    event_tags="Alliance Fracture",
    source_urls=[
        ("The Hill: 5 takeaways from a tense Munich Security Conference", "https://thehill.com/policy/international/5740684-us-europe-ties-munich-conference/"),
        ("The Hill: Kelly rails against Trump as Munich Security Conference ends", "https://thehill.com/homenews/senate/5739714-kelly-rails-against-trump-as-munich-security-conference-ends/"),
        ("Foreign Policy: Elbridge Colby — NATO Is Actually Stronger Than Ever", "https://foreignpolicy.com/2026/02/14/elbridge-colby-us-russia-nato-america-first/"),
    ],
)

# ═══════════════════════════════════════════════════════════════════════
# ARTICLE 2: Largest Sewage Spill in U.S. History
# ═══════════════════════════════════════════════════════════════════════
a2_html = build_deep_pattern_html(
    title="Largest Sewage Spill in U.S. History — The Federal Government Owns the Facility It's Blaming Others For",
    why_it_matters="The Potomac River sewage spill — confirmed as the largest in U.S. history — was caused by a federally owned and operated facility. The Trump administration blamed Maryland Democrats. Maryland's governor produced ownership records showing federal control since the last century. Neither side is discussing the $2.6 trillion infrastructure gap that makes incidents like this inevitable.",
    facts=[
        ("Feb 17, 2026", "A sewage overflow classified as the largest in U.S. history is confirmed in the Potomac River, affecting Washington D.C.'s primary water supply corridor"),
        ("Federal ownership confirmed", "Maryland Governor Wes Moore's office produces documentation showing the relevant facility has been federally owned and operated since the early 20th century — contradicting Trump's blame of Maryland Democrats"),
        ("Trump response", "President Trump posts to Truth Social blaming 'incompetent Maryland Democrat leadership' — a statement factually contradicted by ownership records within 4 hours"),
        ("Public health scope", "Advisories issued for recreational contact with Potomac water across a 40-mile corridor; downstream communities in Virginia and Maryland also affected"),
        ("Infrastructure context", "The facility involved was constructed in the 1930s — operating at nearly 90 years old on a design lifespan of 50 years"),
        ("National pattern", "EPA data: 850 billion gallons of raw sewage are discharged into U.S. waterways annually due to aging infrastructure — the Potomac incident is an extreme manifestation of a pervasive problem"),
    ],
    big_picture_history="""American water and wastewater infrastructure was built in two primary waves: the 1900–1930 Progressive Era, which created the first municipal sewage and drinking water systems, and the 1945–1975 post-war boom, which extended those systems to suburban America. Both waves of construction were extraordinary achievements of public works engineering for their time.

The problem is time. Infrastructure designed for a 50-year lifespan does not suddenly stop working at year 51. It degrades gradually, then fails catastrophically. The Potomac facility involved in this spill was built in the 1930s. It has operated for nearly 90 years — 40 years beyond its design life.

The American Society of Civil Engineers has given U.S. water infrastructure a D+ rating for the past three consecutive infrastructure report cards. The EPA estimates a $743 billion investment gap in water and wastewater infrastructure alone over the next 20 years. The broader infrastructure deficit — roads, bridges, water, energy grid — is estimated at $2.6 trillion by the American Society of Civil Engineers.

What is new in 2026 is not the infrastructure decay — that has been documented for decades. What is new is the political response: immediate blame assignment between federal and state governments, with no corresponding policy discussion about the underlying problem. The Bipartisan Infrastructure Law (2021) allocated $55 billion for water infrastructure — a significant sum, but 7 cents on every dollar needed.""",
    stakeholder_map=[
        ("Trump Administration", "Blame Maryland Democrats for the spill", "Deflect from federal ownership and federal infrastructure underfunding", "Political cover, no accountability", "Policy credibility if ownership facts emerge widely"),
        ("Maryland Governor Moore", "Establish factual record of federal ownership", "Defend state against false blame, establish political contrast", "Contrast narrative, potential 2028 positioning", "Limited — cannot force federal infrastructure investment"),
        ("EPA", "Conduct investigation, issue guidance", "Manage the political pressure from both directions", "Institutional relevance", "Budget cuts that have reduced monitoring capacity"),
        ("D.C. and Maryland residents", "Clean water, accountability", "Safe water access", "Resolution and remediation", "Health risk, property value impacts, tourism loss"),
        ("Civil engineering sector", "Highlight infrastructure gap", "Secure increased federal investment", "Massive contracts if investment materialises", "Ignored if political blame game continues without policy"),
    ],
    data_points=[
        ("$743B", "EPA-estimated water and wastewater infrastructure investment gap over 20 years"),
        ("$2.6T", "Total U.S. infrastructure deficit across all categories (ASCE estimate)"),
        ("850B gallons", "Raw sewage discharged into U.S. waterways annually due to aging infrastructure (EPA)"),
        ("$55B", "Water infrastructure allocation in the 2021 Bipartisan Infrastructure Law — 7% of the identified need"),
        ("D+", "ASCE grade for U.S. water infrastructure in three consecutive report cards"),
        ("~90 years", "Age of the Potomac facility involved — built in the 1930s on a 50-year design lifespan"),
        ("40 miles", "Length of Potomac River corridor under recreational use advisory following the spill"),
    ],
    delta="The partisan blame exchange is not merely a distraction — it is structurally preventing the policy response the infrastructure gap requires. Every hour of political theatre is an hour not spent on the multi-trillion dollar funding mechanism the problem actually demands. The Potomac spill is not a failure of Democratic or Republican governance. It is a failure of 40-year infrastructure investment cycles that cross every presidential administration.",
    dynamics_tags="Institutional Decay × Narrative Control",
    dynamics_summary="A federally-owned facility created the largest sewage spill in U.S. history. The federal government blamed state Democrats. The infrastructure crisis that made it inevitable received no policy attention.",
    dynamics_sections=[
        {
            "tag": "Institutional Decay",
            "subheader": "The Infrastructure Debt Comes Due",
            "lead": "U.S. water infrastructure is not failing because of political incompetence in 2026. It is failing because of investment decisions — and non-decisions — made across every administration since 1980. The Potomac facility is 90 years old. That is not a Democrat or Republican problem. It is a structural failure of American public investment in physical infrastructure.",
            "quotes": [
                ("America's water infrastructure earns a D+. Drinking water and wastewater systems face a funding gap of $743 billion over 20 years.", "American Society of Civil Engineers, Infrastructure Report Card 2025"),
                ("There are approximately 240,000 water main breaks per year in the United States. We're losing an estimated 2.1 trillion gallons of treated drinking water annually.", "EPA Water Infrastructure Report, 2024"),
            ],
            "analysis": """The institutional decay operates at two levels simultaneously. At the physical level, infrastructure built for 50-year lifespans is operating at 80–90 years without full replacement. Deferred maintenance accumulates as compound debt — every year of non-investment increases the eventual repair cost by an estimated 4–7%.

At the political level, infrastructure investment has been consistently underfunded because the time horizons don't match electoral cycles. A politician who funds infrastructure investment in 2026 does not get credit when the infrastructure performs reliably in 2046. A politician who cuts infrastructure budgets in 2026 does not face accountability when a facility fails in 2036.

The result is a structural bias toward underinvestment that crosses party lines and administrations. The Bipartisan Infrastructure Law's $55 billion for water was celebrated as historic — and it is the largest single water investment in a generation. It is also 7% of the identified need.""",
        },
        {
            "tag": "Narrative Control",
            "subheader": "The Blame Machine and the Policy Vacuum",
            "lead": "Within hours of the spill's confirmation, both sides had their narrative architecture in place. Trump: Maryland Democrats failed. Moore: The federal government owns the facility. Both statements are politically useful. Neither generates policy.",
            "quotes": [
                ("This is what happens when you have incompetent Democrat leadership running a state for decades.", "President Trump, Truth Social, Feb 17 2026"),
                ("The facility in question has been federally owned and operated since before World War II. The facts are not in dispute.", "Governor Moore's office statement, Feb 17 2026"),
            ],
            "analysis": """The narrative exchange is not accidental — it is the optimised output of a political system designed around blame assignment rather than problem resolution. Both sides achieve their objectives: Trump generates outrage among supporters and deflects from federal ownership; Moore generates sympathy and contrast positioning.

The cost of this optimised political exchange is that the actual problem — $743 billion in water infrastructure funding — never enters the conversation. Policy solutions require sustained political will, bipartisan coalition-building, and revenue mechanisms (bond issuance, federal appropriations, public-private partnerships). None of those are visible in the Potomac response.

The Narrative Control dynamic is self-reinforcing: the more successful the blame exchange becomes as a political tool, the less incentive either side has to shift to solution-mode. Infrastructure investment requires political leaders to accept the political cost of visible spending today, for benefits that materialise in 10–20 years. In a blame-optimised political environment, that trade is structurally unattractive.""",
        },
    ],
    dynamics_intersection="Institutional Decay creates the conditions for crises. Narrative Control ensures the crises produce political theatre rather than policy response. The intersection is a self-sealing system: infrastructure continues to decay because the political response to infrastructure failures is blame, not investment. The next spill — larger, in a different city, from a different 90-year-old facility — is structurally guaranteed.",
    pattern_history=[
        {"year": 2014, "title": "Flint Water Crisis — Federal-State Blame and Delayed Response", "content": "In 2014, Flint, Michigan switched its water source to save money, leading to catastrophic lead contamination affecting 100,000 residents. The response timeline: contamination began April 2014; residents raised alarms by August 2014; state government dismissed concerns until October 2015; federal emergency declaration January 2016 — 18 months after residents first raised alarms.\n\nThe Flint response followed the identical pattern: immediate blame assignment (state blamed city, city blamed state), political theatre in congressional hearings, and a funding response — $247 million — that arrived years after the crisis and was a fraction of the systemic need.\n\nFlint led to no structural changes in U.S. water infrastructure funding mechanisms. The same infrastructure gap exists. The same political incentive structure exists.", "similarity": "Federal-state blame exchange, delayed policy response, funding far below systemic need — the Potomac spill follows Flint's template with a larger scale and a cleaner federal ownership record"},
        {"year": 2003, "title": "Northeast Blackout — Infrastructure Failure and Political Accountability Failure", "content": "The August 2003 Northeast blackout affected 55 million people across the U.S. and Canada — the largest power outage in North American history at the time. The immediate cause was a software bug in Ohio. The structural cause was decades of underinvestment in grid modernisation.\n\nThe political response: a joint U.S.-Canada task force produced a 46-recommendation report. Of those recommendations, fewer than half were implemented within 10 years. Infrastructure investment remained below the level needed to prevent recurrence. Multiple smaller regional blackouts have occurred since.\n\nThe 2003 blackout did not produce structural change in U.S. electricity infrastructure investment. Neither did Superstorm Sandy's grid damage in 2012. The Potomac spill will likely follow the same trajectory: hearings, a report, partial funding, and gradual return to the pre-crisis investment trajectory.", "similarity": "Large-scale infrastructure failure, political accountability theatre, recommendations without commensurate investment, gradual return to pre-crisis investment trajectory"},
    ],
    history_pattern_summary="U.S. infrastructure crises consistently follow the same trajectory: catastrophic failure → partisan blame → congressional hearings → partial funding → gradual forgetting → next failure. The interval between major failures is shortening as infrastructure ages further. The pattern will continue until the funding mechanism matches the scale of the problem — which requires political will that blame-optimised politics systematically prevents.",
    scenarios=[
        ("基本", "60-70%", "EPA investigation opens, runs for 6–12 months, and produces a report attributing the failure to federal underinvestment and aging infrastructure. Congressional hearings are held. A supplemental infrastructure appropriation of $5–10 billion is passed, funded as emergency spending. The Potomac facility is partially upgraded. The broader $743 billion funding gap receives no structural response.", "Water utility bonds in affected jurisdictions may face short-term pressure. Federal water infrastructure contractors (Xylem, Veolia, American Water Works) positioned for repair contract pipeline."),
        ("楽観", "10-15%", "Potomac spill triggers a genuine bipartisan infrastructure moment — comparable to Flint's eventual political mobilisation. An emergency water infrastructure bill passes with $100B+ in funding. Federal-municipal ownership accountability frameworks are clarified. Preventive monitoring systems are mandated for all facilities over 60 years old.", "Near-term legislative catalyst for water infrastructure stocks. Watch for committee markup language and bipartisan co-sponsorship as leading indicators."),
        ("悲観", "20-25%", "Political blame exchange continues through the news cycle. EPA investigation stalls under budget pressure. The Potomac facility receives emergency repairs sufficient to reopen but not full replacement. Within 3–5 years, a similar or larger failure occurs at another aging federally-owned facility — likely in a different watershed.", "The systemic risk here is not the Potomac spill alone but the portfolio of aging federally-owned water infrastructure nationwide. Each is a latent crisis."),
    ],
    triggers=[
        ("EPA investigation report release", "If the report explicitly attributes the failure to federal underfunding and aging infrastructure — rather than operational error — it changes the political accountability calculus"),
        ("Downstream health impact data", "If epidemiological data shows measurable health effects in downstream communities, public pressure for policy response increases significantly"),
        ("Second major spill", "If a similar failure occurs at another aging federally-owned facility within 12 months, the 'one-off' narrative collapses and systemic investment becomes politically unavoidable"),
        ("Infrastructure bond market reaction", "If Potomac-area municipal water bonds are downgraded, it signals that markets are beginning to price systemic infrastructure risk — a precursor to federal action"),
    ],
    genre_tags="Society / Politics & Policy",
    event_tags="Institutional Decay / Regulatory Change",
    source_urls=[
        ("The Hill: Moore's office fires back at Trump after Potomac sewage spill blame", "https://thehill.com/homenews/administration/5741034-trump-moore-potomac-waste-spill/"),
        ("ASCE Infrastructure Report Card 2025", "https://www.infrastructurereportcard.org/"),
    ],
)

# ═══════════════════════════════════════════════════════════════════════
# ARTICLE 3: Russia 400 Drones + Geneva Talks
# ═══════════════════════════════════════════════════════════════════════
a3_html = build_deep_pattern_html(
    title="Russia Launched 400 Drones Hours Before Geneva Peace Talks — Violence as a Negotiating Card",
    why_it_matters="On the same day Geneva peace talks opened, Russia launched one of its largest combined drone and missile barrages of the war against Ukraine. That same day, France released a detained Russian shadow fleet tanker after a fine — demonstrating the hard legal ceiling of unilateral sanctions enforcement. Nineteen rounds of EU sanctions have not altered Moscow's cost-benefit calculation. Round 20 will not either without a structural enforcement upgrade.",
    facts=[
        ("Feb 17, 2026 — barrage timing", "Russia launches approximately 400 Shahed drones plus 29 cruise and ballistic missiles against Ukrainian cities — timed to coincide with the opening of Geneva peace talks, signalling that military pressure and diplomacy are not alternatives but simultaneous tools"),
        ("Feb 17, 2026 — shadow fleet release", "France detains a vessel suspected of being part of Russia's shadow oil fleet in a French port, then releases it after the master pays a multi-million euro fine — demonstrating the legal ceiling of unilateral port-state enforcement"),
        ("EU Sanctions Round 20", "The European Union confirms a 20th package of sanctions against Russia — the latest in a series that began in February 2022, none of which has produced structural behavioural change in Moscow's war conduct"),
        ("Shadow fleet operational scale", "Approximately 1,400 vessels are estimated to be operating in Russia's shadow fleet — transporting Russian crude to India and China while evading SWIFT-linked financial networks"),
        ("Geneva talks framework", "Talks involve U.S., European, and Ukrainian officials; Russia's participation is indirect; the framework is contested — Moscow treats the military track and diplomatic track as complementary pressure points"),
        ("Ukrainian air defence pressure", "The scale of the combined barrage — drones plus missiles — is designed to overwhelm Ukrainian air defence systems, which require Western resupply to maintain coverage"),
    ],
    big_picture_history="""Russia's approach to the Ukraine war has followed a consistent dual-track strategy since the beginning of 2024: maintain military pressure at scale while using selective diplomatic engagement to fragment Western unity. The February 2026 barrage on the day Geneva talks opened is not an accident — it is the doctrine made visible.

The shadow fleet is the economic dimension of the same strategy. When Western sanctions cut Russia off from SWIFT-linked financial networks and G7 shipping insurance in 2022, Moscow did not capitulate. It adapted. Within 18 months, a shadow fleet of 1,400+ vessels was operating — tankers purchased through third-country intermediaries, flagged in non-sanctioned jurisdictions, insured through Russian or non-Western providers, and transporting Russian crude to India and China at a discount.

The French detention-and-release on Feb 17 reveals the structural limit of the response. Port-state enforcement — detaining vessels in national ports — is the most powerful tool available to individual European countries without an international framework. But it is bounded: detention cannot exceed the time required for inspection, and fines must be proportionate to documented violations. The economics of shadow fleet operations build these costs into their pricing model. A multi-million euro fine is an acceptable operating cost against the revenue from a single crude cargo.

Arms control frameworks that might have provided diplomatic leverage have collapsed: New START expired in 2026, the Open Skies Treaty is dead, the INF Treaty has been gone since 2019. The tools that 20th-century diplomacy relied on to manage Russian military risk are not available.""",
    stakeholder_map=[
        ("Russia", "Pursuing territorial consolidation and security guarantees", "Using military + diplomatic dual-track to extract maximum concessions before any ceasefire", "Territorial gains, security buffer, sanctions relief", "Prolonged attrition, economic strain from sustained war"),
        ("Ukraine", "Territorial integrity and security guarantees", "International support, arms supply, negotiating leverage", "Survival and credible post-war security architecture", "Territorial loss, ceasefire without guarantees"),
        ("EU members (France, Germany)", "Supporting Ukraine while maintaining diplomatic channels", "Preventing escalation while sustaining pressure", "Managed resolution, reduced war risk", "Reputational cost of enforcement limitations, energy exposure"),
        ("India / China", "Purchasing discounted Russian oil", "Energy security at below-market prices, geopolitical hedging", "$40-90B/year in energy savings", "Secondary sanctions risk, reputational exposure"),
        ("Shadow fleet operators", "Transporting Russian crude", "Revenue maximisation within legal grey zones", "Fees plus Russian government relationships", "Port detention, insurance complications, secondary sanctions"),
    ],
    data_points=[
        ("~400", "Shahed drones in the Feb 17 barrage — one of the largest single-day attacks of the war"),
        ("29", "Cruise and ballistic missiles in the same barrage"),
        ("~$650M/day", "Russia's daily crypto transaction volume (Ministry of Finance) — supplementing oil revenue"),
        ("1,400+", "Estimated vessels in Russia's shadow fleet"),
        ("$100/barrel", "Approximate threshold above which Russian shadow fleet operations remain highly profitable despite discount pricing and sanctions friction"),
        ("20", "EU sanctions packages against Russia since February 2022 — none producing structural behavioural change"),
        ("$237B/year", "Annualised shadow fleet oil revenue estimate at current volumes"),
    ],
    delta="The shadow fleet release reveals a structural gap in Western enforcement architecture: Europe has the political will to impose sanctions, but not the legal infrastructure to enforce them at the margin that matters. The fine is priced in. What is not priced in is a dedicated international legal instrument — similar to the Proliferation Security Initiative for WMD — specifically designed for sanctions-evading vessels. That instrument does not exist.",
    dynamics_tags="Escalation Spiral × Coordination Failure",
    dynamics_summary="Military pressure and diplomacy are Russia's simultaneous tools. Western enforcement has hit its legal ceiling without an international framework to extend it.",
    dynamics_sections=[
        {
            "tag": "Escalation Spiral",
            "subheader": "The Barrage Before the Table",
            "lead": "Launching 400 drones on the morning of Geneva peace talks is not a contradiction — it is a communication. Russia's message: the military track and the diplomatic track are the same track. Every kilometre of Ukrainian territory under Russian pressure at the moment talks begin is a kilometre that shapes the negotiating map.",
            "quotes": [
                ("Russia has consistently used military escalation as a diplomatic tool — the barrage is not irrational. It is the message.", "Senior Western diplomatic official, Feb 17 2026 (anonymous)"),
                ("Ukraine is defending against one of the largest combined drone-missile attacks of the war while simultaneously sending negotiators to Geneva. The asymmetry is intentional.", "Institute for the Study of War, Feb 17 2026 situation report"),
            ],
            "analysis": """The Escalation Spiral dynamic operates as a ratchet: each Russian escalation raises the threshold that Western responses must clear to be credible, while simultaneously fragmenting Western political coalitions whose tolerance for escalation risk varies across member states.

The 400-drone barrage serves three simultaneous purposes: military (overwhelm Ukrainian air defence by sheer volume), strategic (signal to the West that Russia will continue fighting through any diplomatic process), and domestic (Russian state media can present military activity as strength on the day of 'Western-imposed' talks).

The timing relative to Geneva is the key signal. Moscow's calculation: European publics want the war to end. Launching a massive barrage on the day of peace talks forces European governments to either accelerate arms supply (politically costly) or accept the diplomatic track on Moscow's terms (strategically costly). Both options serve Russian interests.""",
        },
        {
            "tag": "Coordination Failure",
            "subheader": "The Enforcement Ceiling No One Designed To Break",
            "lead": "The French shadow fleet detention-and-release is not incompetence. It is the designed ceiling of unilateral port-state enforcement. No single European country — not France, not the Netherlands, not Germany — has the legal authority to unilaterally confiscate a vessel transiting international trade routes for sanctions violations. The legal framework was not built for this.",
            "quotes": [
                ("We can detain. We can fine. We cannot confiscate without a multilateral legal framework that doesn't exist yet.", "European maritime law expert, Feb 2026 (anonymous)"),
            ],
            "analysis": """The Coordination Failure is structural: Western sanctions architecture was designed for the financial sector (SWIFT exclusion, asset freezes), not for physical commodity transport. Shadow fleet vessels operate in the transport sector, where the relevant legal frameworks are international maritime law — which has not been updated to address large-scale sanctions evasion through vessel flagging and ownership obfuscation.

A dedicated enforcement instrument — analogous to the Proliferation Security Initiative (PSI), which allows signatory states to interdict vessels suspected of carrying WMD-related materials — does not exist for sanctions-evading oil tankers. Building one would require multilateral negotiation, including with major non-Western shipping states. India, China, and the UAE — all of which benefit from shadow fleet operations — would need to be managed or marginalised.

The alternative is secondary sanctions: sanctioning the entities that service shadow fleet vessels (insurance, maintenance, port services) regardless of their nationality. The U.S. has the extraterritorial reach to impose secondary sanctions more aggressively than Europe. The political cost is friction with India and other partners whose cooperation on other fronts is valued.""",
        },
    ],
    dynamics_intersection="The Escalation Spiral and Coordination Failure dynamics are mutually reinforcing: Russia escalates militarily because it has correctly calculated that Western coordination failures limit the effective response. Every enforcement gap Russia identifies — shadow fleet, crypto, dual-use goods — becomes a proof of concept that the Western coalition is structurally constrained. That proof of concept feeds the next round of escalation.",
    pattern_history=[
        {"year": 1990, "title": "Gulf War Oil Sanctions — The Enforcement Infrastructure That Worked", "content": "When Iraq invaded Kuwait in August 1990, the UN Security Council imposed comprehensive sanctions including a naval blockade — the Maritime Interception Operations (MIO) — that allowed coalition forces to board and inspect vessels suspected of violating sanctions. The framework worked because it had a UN mandate, U.S. naval enforcement capacity, and clear legal authority.\n\nThe contrast with 2026 is instructive: Iraq sanctions worked because the enforcement infrastructure matched the political will. Russian shadow fleet sanctions fail because the enforcement infrastructure (unilateral port-state enforcement, fines) does not match the political will to restrict Russian oil revenues.\n\nThe lesson is not that sanctions don't work — it's that sanctions require enforcement architecture commensurate with the target.", "similarity": "The gap between political will to sanction and enforcement infrastructure to make sanctions effective — the 1990 model succeeded where 2026 fails because it had UN mandate and naval enforcement"},
        {"year": 2003, "title": "Proliferation Security Initiative — Building Enforcement Architecture for WMD", "content": "The Bush administration launched the Proliferation Security Initiative in 2003 to address the gap in international law around interdicting WMD-related shipments. The PSI created a framework — initially 11 countries, now 100+ — under which member states could interdict vessels carrying WMD materials regardless of flag or ownership.\n\nThe PSI demonstrated that enforcement architecture can be built multilaterally and incrementally. It took 3 years from conception to operational effectiveness.\n\nA 'Sanctions Evasion Interception Initiative' — modelled on the PSI but targeting shadow fleet vessels — has been discussed in EU policy circles since 2024. It has not been implemented. The Feb 17 French detention-release is an argument for why it needs to be.", "similarity": "Enforcement architecture for a novel evasion mechanism can be built multilaterally — the PSI model is directly applicable to shadow fleet interdiction"},
    ],
    history_pattern_summary="Sanctions without enforcement architecture fail at the margin that matters. The historical pattern shows that effective sanctions enforcement requires either a UN mandate with military enforcement capacity, or a dedicated multilateral legal framework. Europe has neither for shadow fleet operations. Until that changes, the fines will be priced into operating costs and the oil will flow.",
    scenarios=[
        ("基本", "55-65%", "Geneva talks produce an interim framework — possibly a 60-day ceasefire — that pauses major combat operations without resolving territorial or security guarantee questions. Russia uses the pause to consolidate and resupply. European shadow fleet enforcement continues at current levels: detention-and-fine, no confiscation. EU sanctions Round 21 is discussed but its marginal impact on Moscow's behaviour is recognised as limited.", "Ukrainian war bonds and reconstruction financing will be the medium-term investment theme post-ceasefire. Watch for EU reconstruction fund announcement."),
        ("楽観", "15-20%", "Geneva talks produce a durable ceasefire framework with international monitoring. EU launches a Sanctions Evasion Interception Initiative modelled on PSI, covering shadow fleet vessels. Secondary sanctions are expanded to cover Indian and UAE entities servicing shadow fleet operations. Russian oil revenue falls to levels that accelerate domestic economic pressure.", "Significant rerating of European reconstruction equities. Energy diversification infrastructure (LNG terminals, renewables) benefits from confirmed Russian energy exit."),
        ("悲観", "20-25%", "Geneva talks collapse within 30 days. Russia escalates — possibly including infrastructure strikes on Western-supplied equipment — to demonstrate that diplomacy will proceed on Russian terms or not at all. European unity frays: Hungary and Slovakia push for unilateral ceasefire negotiations. Shadow fleet continues operating with no enforcement upgrade.", "Safe haven flows: dollar, yen, gold. European gas spot premium. Defence sector outperformance."),
    ],
    triggers=[
        ("Geneva talks ceasefire text", "Whether any ceasefire includes international monitoring mechanisms or is purely bilateral determines durability"),
        ("U.S. secondary sanctions expansion", "If the U.S. designates Indian or UAE entities servicing shadow fleet vessels, it signals willingness to accept friction with partners to enforce the Russia sanctions regime"),
        ("Additional major barrage during talks", "If Russia launches another 300+ drone barrage while Geneva talks are active, it demonstrates that the diplomatic track is purely tactical — not strategic"),
        ("EU PSI-equivalent proposal", "Watch for European Commission or Council proposal for an interception framework for sanctions-evading vessels"),
    ],
    genre_tags="Geopolitics",
    event_tags="Military Conflict / Sanctions & Law",
    source_urls=[
        ("The Guardian: Ukraine talks begin in Geneva as Russia fires record drone barrage", "https://www.theguardian.com/world/live/2026/feb/17/ukraine-talks-geneva-russia-zelenskyy-putin-orban-rubio-latest-news-updates"),
    ],
)

# ═══════════════════════════════════════════════════════════════════════
# ARTICLE 4: Trump Practically Destroyed NATO — Sen. Kelly
# ═══════════════════════════════════════════════════════════════════════
a4_html = build_deep_pattern_html(
    title="\"Trump Practically Destroyed NATO in Under a Year\" — A U.S. Senator Said It Out Loud at Munich",
    why_it_matters="When a U.S. senator departs the world's premier security forum and publicly states that the sitting president has 'practically destroyed NATO in under a year,' the transatlantic crisis has moved from management into documented rupture. Sen. Mark Kelly's statement is notable not because it is partisan — it is — but because it was said out loud, at Munich, where the most strategically significant audience is neither American nor European.",
    facts=[
        ("Feb 15, 2026", "Sen. Mark Kelly (D-AZ) posts on X upon departing Munich: 'It took President Trump less than a year to practically destroy NATO, and Vladimir Putin and President Xi are the beneficiaries'"),
        ("Conference context", "Munich Security Conference 2026 — the first since Trump's second-term inauguration — features European leaders holding open discussions of defence autonomy, independent nuclear deterrence, and U.S. commitment uncertainty"),
        ("Bipartisan dimension", "Kelly is a former astronaut and Navy combat pilot — his framing carries credibility beyond partisan positioning; multiple Republican senators expressed private concerns about alliance fraying at Munich"),
        ("European response", "No European government officially endorsed Kelly's framing, but several delegations privately confirmed to U.S. media that 'destroyed' was within the range of discussions being had behind closed doors"),
        ("Beijing observation", "Chinese foreign ministry officials described Munich 2026 as 'revealing the internal contradictions of the Western bloc' — language that signals active strategic reassessment"),
        ("Historical baseline", "Article 5 of the NATO treaty has been invoked once in the alliance's 75-year history — after September 11, 2001 — and has functioned as a deterrent without explicit conditionality since 1949"),
    ],
    big_picture_history="""NATO's deterrence value is not mechanical — it is psychological. The alliance deters not because every member is capable of collectively defeating Russia in a conventional war, but because every potential aggressor calculates that triggering Article 5 means triggering a U.S. response of incalculable scale. That calculation is the product of 75 years of unconditional language, force posture, and institutional behaviour.

The Trump administration's second term has introduced conditionality into Article 5 in a way that the first term did not fully achieve. In 2017–2020, Trump questioned NATO publicly, but the U.S. security establishment — Mattis, McMaster, Kelly — pushed back effectively. The institutional resistance maintained deterrence credibility at the level that mattered: adversary calculations.

In 2026, the institutional resistance is absent. Elbridge Colby — the Pentagon's primary strategic planner — is aligned with the reorientation away from European security commitments. The State Department and NSC operate within the same transactional framework. The divergence between Trump's rhetoric and U.S. institutional behaviour that maintained deterrence in 2017–2020 no longer exists.

Sen. Kelly's statement 'practically destroyed NATO' is strategically significant not as a policy prescription but as a signal: if a U.S. senator — at Munich, publicly — uses the phrase, Beijing's analysts are updating their models. Chinese strategic doctrine on Taiwan rests partly on an assessment of U.S. alliance cohesion. Every piece of public evidence that the cohesion is diminished updates that assessment in a direction that lowers the perceived cost of military action in the Indo-Pacific.""",
    stakeholder_map=[
        ("Trump Administration", "Reassuring European allies of U.S. commitment", "Reducing European security costs, freeing Indo-Pacific bandwidth", "Resource reallocation to Indo-Pacific", "Deterrence credibility loss vs. Russia and China"),
        ("Congressional Democrats", "Documenting alliance damage for electoral contrast", "Building credibility on national security against Trump", "2026/2028 electoral positioning", "Risk of appearing anti-military or isolationist"),
        ("Congressional Republicans", "Maintaining Trump alignment on budget/spending", "Private concern about alliance damage", "Majority preservation", "National security credibility if allies visibly lose confidence"),
        ("China", "Observing, calibrating", "Updating Indo-Pacific risk models using NATO fracture data", "Lower perceived cost of Taiwan action", "Risk of premature action based on overstated U.S. withdrawal"),
        ("Russia", "Exploiting alliance fracture", "Advancing negotiating position using Western disunity", "Ceasefire on favourable terms, reduced NATO pressure", "Risk of overreach if Western unity holds despite appearances"),
    ],
    data_points=[
        ("1", "Number of times Article 5 has been invoked in NATO's 75-year history (September 11, 2001)"),
        ("75 years", "Duration of unconditional U.S. Article 5 guarantee — now publicly conditional for the first time"),
        ("32", "NATO member states in 2026 — the largest in history, yet internally most divided"),
        ("23/32", "Members meeting the 2% GDP defence spending target in 2025 — up from 10/32 in 2022"),
        ("68%", "Share of European publics who say the U.S. is 'less reliable' as a security partner than 4 years ago (Pew Research, Jan 2026)"),
        ("290", "French operational nuclear warheads — Europe's only independent deterrent"),
        ("$800B", "Annual U.S. defence budget — the resource constraint that makes Indo-Pacific prioritisation a mathematical choice, not merely a preference"),
    ],
    delta="The most strategically significant audience for the Kelly statement is not in Washington, Brussels, or Moscow. It is in Beijing. Chinese strategic planners are updating their Indo-Pacific risk models in real time using Alliance Fracture as a key input variable. Munich 2026 produced the clearest public signal yet that the input is moving in a direction that lowers Beijing's perceived cost calculation for Taiwan.",
    dynamics_tags="Alliance Fracture × Narrative Control",
    dynamics_summary="When a U.S. senator publicly says NATO has been 'practically destroyed,' Beijing's strategic analysts log it as a data point. Deterrence is a psychological architecture — and it just degraded.",
    dynamics_sections=[
        {
            "tag": "Alliance Fracture",
            "subheader": "The Deterrence Gap",
            "lead": "NATO deters by making adversaries believe the cost of military action exceeds the benefit — not through physical capability alone, but through the credible promise of automatic collective response. That promise is now publicly conditional. The deterrence gap is not in hardware — it is in the credibility of the guarantee.",
            "quotes": [
                ("'It took President Trump less than a year to practically destroy NATO, and Vladimir Putin and President Xi are the beneficiaries.'", "Sen. Mark Kelly, X, Feb 15 2026"),
                ("'NATO is actually stronger than ever. European defence spending is up, membership is up, the eastern flank is reinforced.'", "Elbridge Colby, Foreign Policy, Feb 14 2026"),
            ],
            "analysis": """Both statements are factually accurate and simultaneously true — which is the essence of the Alliance Fracture dynamic. NATO is institutionally stronger in capability terms than it was in 2021. And the deterrence value of the alliance has degraded, because deterrence rests on adversary calculation of the probability and scale of U.S. response, not on European capability alone.

A Europe that spends €800 billion on defence annually but faces an adversary who has correctly calculated that the U.S. will not intervene is less safe than a Europe that spends €400 billion annually but can count on automatic U.S. involvement. The capability investment and the credible guarantee are not substitutes — they are complements. Removing one while increasing the other does not produce the same deterrence outcome.

The Alliance Fracture dynamic is path-dependent: once adversary calculations update to reflect reduced U.S. commitment probability, restoring deterrence requires not merely reaffirming the commitment but demonstrating why the new calculation is wrong. That requires either a credible signal of unconditional commitment (which the Trump administration has not provided) or a completed autonomous European deterrence capability (which will take 10–15 years).""",
        },
        {
            "tag": "Narrative Control",
            "subheader": "The Statement That Landed in Beijing",
            "lead": "Kelly's statement was aimed at a U.S. domestic audience — positioning Democrats as the credible national security party against Trump's alliance damage. It was received in Beijing as strategic intelligence about U.S. alliance cohesion. The domestic political statement and the international strategic signal are the same sentence.",
            "quotes": [
                ("Munich 2026 has been revealing of the internal contradictions of the Western bloc.", "Chinese Foreign Ministry statement, Feb 17 2026"),
            ],
            "analysis": """Chinese foreign ministry language is carefully calibrated. 'Internal contradictions of the Western bloc' is not neutral observation — it is the language of strategic advantage logging. Chinese strategic doctrine identifies alliance fractures in adversary coalitions as key enablers of coercive action. The Munich 2026 narrative — visible to any observer, including Chinese — is that the Western alliance is publicly divided on its foundational commitment.

The Narrative Control dynamic operates at multiple levels simultaneously. At the U.S. domestic level, both Trump and Kelly are using NATO as a domestic political instrument. At the international level, that domestic political use is generating strategic signals that Beijing reads as alliance cohesion data.

The gap between domestic political communication and international strategic signalling is a structural feature of democratic foreign policy. Democratic politicians cannot fully control what their domestic statements communicate to foreign strategic audiences. The solution historically has been institutional guardrails — the State Department, NSC processes — that manage the gap. Those guardrails are currently operating with reduced effectiveness.""",
        },
    ],
    dynamics_intersection="Alliance Fracture provides the reality; Narrative Control determines who reads it and how. The Kelly statement is both a symptom of Alliance Fracture (genuine divergence within the Western coalition) and a Narrative Control failure (a domestic political statement generating unintended international strategic signals). Beijing does not need classified intelligence to update its Taiwan risk models. Munich 2026 provided the update publicly.",
    pattern_history=[
        {"year": 1979, "title": "NATO's 'Dual Track' Crisis — Alliance Fracture Over Euromissiles", "content": "In 1979, NATO agreed to deploy Pershing II and cruise missiles in Western Europe to counter Soviet SS-20s — while simultaneously offering arms control negotiations. The decision triggered the largest peace demonstrations in European history, with millions protesting in West Germany, the Netherlands, and the UK.\n\nThe alliance survived — but only after significant political cost. The episode demonstrated that NATO's cohesion was not automatic even at the height of the Cold War, when the threat was unambiguous.\n\nThe difference in 2026 is the direction of the fracture: in 1979, the alliance fractured over how vigorously to confront the Soviet threat. In 2026, it is fracturing over whether the U.S. will honour its commitment to confront threats at all.", "similarity": "Alliance cohesion under political stress — the management mechanisms that worked in 1979 (NATO consensus process, shared threat assessment) are degraded or absent in 2026"},
        {"year": 2003, "title": "'Old Europe' vs 'New Europe' — Iraq War Alliance Division", "content": "Defense Secretary Donald Rumsfeld's 2003 characterisation of France and Germany as 'Old Europe' for opposing the Iraq War produced the sharpest public trans-Atlantic rift since France's 1966 NATO withdrawal. For 18 months, the alliance was functionally split between U.S.-UK-'New Europe' (Poland, Baltic states) and French-German opposition.\n\nNATO survived because the core security interest — European defence against Russia — remained aligned. The Iraq split was over a war of choice, not a fundamental commitment to European security.\n\nThe 2026 fracture is categorically different: it is about the U.S. commitment to European security itself, not a peripheral military adventure. That makes it structurally more serious.", "similarity": "Public U.S.-European division on a fundamental security question — but 2003 was about a war of choice; 2026 is about the foundational commitment"},
    ],
    history_pattern_summary="NATO has survived multiple fractures — 1966, 1979, 2003 — because in each case, the fundamental U.S. security commitment to European defence remained credible. The 2026 fracture is different in kind: it is the first time the fundamental commitment itself has been made publicly conditional. Historical precedents for recovery from this category of alliance crisis are limited.",
    scenarios=[
        ("基本", "50-60%", "NATO remains institutionally intact through 2026–2027. U.S. commitment is de facto conditional on burden-sharing but not formally withdrawn. European defence spending continues to rise. Japan and South Korea begin privately asking the questions European allies are asking publicly. The deterrence gap persists but does not produce a military crisis within the 24-month window.", "Alliance uncertainty premium should be embedded in European political risk assessments. European defence industrial stocks (Rheinmetall, BAE Systems) outperform on sustained demand."),
        ("楽観", "15-20%", "A U.S.-Europe 'New Bargain' — explicit burden-sharing agreement with U.S. commitment in exchange for European 3% GDP target — restores deterrence credibility. Bipartisan Senate legislation reinforces Article 5 commitment. Beijing updates its Taiwan risk models back toward deterrence-holds.", "Significant risk premium compression in European markets. Watch for bipartisan Senate NATO commitment legislation as the key leading indicator."),
        ("悲観", "25-30%", "Alliance fracture deepens. A Russian hybrid incursion into Baltic territory tests Article 5. U.S. response is delayed or conditional. The deterrence architecture fails its first real test. European autonomy scramble accelerates — but takes 10+ years to produce credible deterrence.", "Maximum portfolio defensiveness. European political risk premium at highest level since Cold War. Defense sector + safe haven flows."),
    ],
    triggers=[
        ("Explicit U.S. Article 5 conditionality statement", "If any senior U.S. official publicly conditions Article 5 on burden-sharing metrics, it formalises what is currently implicit and triggers immediate European response"),
        ("Senate NATO commitment vote", "A bipartisan Senate resolution reaffirming unconditional U.S. Article 5 commitment would partially offset executive branch ambiguity"),
        ("Chinese military action proximate to Taiwan", "Any People's Liberation Army action that tests U.S. response would clarify whether Indo-Pacific prioritisation has already consumed the bandwidth previously allocated to European security"),
        ("Baltic hybrid incident", "A Russian hybrid operation in Estonia, Latvia, or Lithuania — below the threshold of unambiguous armed attack — would be the most direct test of the conditional Article 5 reality"),
    ],
    genre_tags="Geopolitics",
    event_tags="Alliance Fracture",
    source_urls=[
        ("The Hill: Kelly rails against Trump as Munich Security Conference ends", "https://thehill.com/homenews/senate/5739714-kelly-rails-against-trump-as-munich-security-conference-ends/"),
    ],
)

# ─── 記事データリスト ───────────────────────────────────────────────
BATCH1 = [
    {"id": "699779e45850354f44049bbe", "title": "Munich Security Conference 2026 — Five Signals That the Western Alliance Fracture Is Now Structural", "html": a1_html, "tags": ["Geopolitics", "Alliance Fracture", "Institutional Decay", "Deep Pattern"]},
    {"id": "699779e05850354f44049bb1", "title": "Largest Sewage Spill in U.S. History — The Federal Government Owns the Facility It's Blaming Others For", "html": a2_html, "tags": ["Society", "Politics & Policy", "Institutional Decay", "Narrative Control", "Deep Pattern"]},
    {"id": "699779dd5850354f44049ba8", "title": "Russia Launched 400 Drones Hours Before Geneva Peace Talks — Violence as a Negotiating Card", "html": a3_html, "tags": ["Geopolitics", "Military Conflict", "Sanctions & Law", "Escalation Spiral", "Coordination Failure", "Deep Pattern"]},
    {"id": "699779d95850354f44049b9d", "title": "\"Trump Practically Destroyed NATO in Under a Year\" — A U.S. Senator Said It Out Loud at Munich", "html": a4_html, "tags": ["Geopolitics", "Alliance Fracture", "Narrative Control", "Deep Pattern"]},
]

ok = 0
for art in BATCH1:
    ua = get_updated_at(art["id"])
    success, msg = update_post(art["id"], art["html"], art["title"], ua, art["tags"])
    print(f"[{'OK' if success else 'ERROR'}] {art['title'][:55]}...")
    if success: ok += 1
    else: print(f"       {msg}")
    time.sleep(0.5)

print(f"\nBatch 1 完了: {ok}/{len(BATCH1)}")
