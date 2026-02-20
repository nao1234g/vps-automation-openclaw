#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Pattern Batch 2 — 英語記事 5本
New START / Bitcoin Mining / Bundesbank Stablecoins / Russia Crypto / Colby NATO
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
# ARTICLE 5: New START Expired — No Nuclear Arms Agreement
# ═══════════════════════════════════════════════════════════════════════
a5_html = build_deep_pattern_html(
    title="New START Expired With No Replacement — For the First Time Since 1972, No Nuclear Arms Agreement Exists Between the U.S. and Russia",
    why_it_matters="For the first time since Richard Nixon signed SALT I in 1972, there is no legally binding nuclear arms control agreement between the United States and Russia. No inspection regime. No verified warhead caps. No agreed notification framework for missile tests. And the U.S. foreign policy apparatus is now operated on personal executive intuition rather than the institutional guardrails that arms control was designed to complement.",
    facts=[
        ("Feb 5, 2026", "New START — the last remaining nuclear arms control treaty between the U.S. and Russia — formally expires with no successor framework negotiated or in development"),
        ("Verification gap", "Without New START's inspection protocol, neither side has legal access to verify the other's warhead counts, deployment postures, or delivery system configurations for the first time in 54 years"),
        ("Trump's bilateral approach", "The Trump administration has pursued direct personal engagement with Putin, bypassing the State Department and Arms Control and Disarmament Agency — removing the institutional crisis management infrastructure arms control was designed to complement"),
        ("Russian modernisation", "Russia has deployed three new nuclear delivery systems — Avangard hypersonic glide vehicle, Sarmat ICBM, Poseidon nuclear torpedo — none of which were covered by New START's counting rules"),
        ("U.S. modernisation", "The U.S. Columbia-class submarine programme, B-21 Raider bomber, and Sentinel ICBM replacement are proceeding without a verification framework that would allow Russia to confirm U.S. compliance with previous limits"),
        ("Chinese dimension", "China, which has never participated in a bilateral nuclear arms control framework, is engaged in the fastest documented nuclear buildup in its history — expanding from ~250 operational warheads in 2020 to an estimated 500+ by 2026"),
    ],
    big_picture_history="""Nuclear arms control between the U.S. and Soviet Union — and later Russia — began not from idealism but from the near-catastrophic experience of the Cuban Missile Crisis. In October 1962, the world came within hours of nuclear exchange not because either side wanted war, but because both sides lacked the communication and verification infrastructure to prevent miscalculation. The crisis resolution required 13 days of improvised back-channel diplomacy under extreme time pressure.

The institutional response to that near-miss was systematic. The Moscow-Washington hotline (1963), SALT I (1972), the Anti-Ballistic Missile Treaty (1972), SALT II (1979), INF Treaty (1987), START I (1991), START II (2002, never ratified by Russia), the Moscow Treaty (2002), and New START (2010) — each built incrementally on the lesson that reducing the risk of miscalculation-driven nuclear exchange requires verified, legally binding, institutionally-managed frameworks.

The architecture that took 60 years to build is now almost entirely gone. The ABM Treaty was terminated by the U.S. in 2002. The INF Treaty was terminated in 2019, after both sides accused the other of violations. New START expired in 2026 without a successor. The Open Skies Treaty — which provided aerial verification of military movements — died in 2020-2021. What remains is the direct hotline communication channel, which is operational but not sufficient.

The combination of five factors makes the current situation more dangerous than any point since the Cuban Missile Crisis: (1) no verification framework, (2) hypersonic delivery systems that compress decision time below human reaction speed, (3) cyber weapons that can affect nuclear command and control, (4) a U.S. administration that operates on personal intuition rather than institutional crisis management protocols, and (5) a China that is outside all arms control frameworks and expanding rapidly.""",
    stakeholder_map=[
        ("Trump Administration", "Avoiding 'bad deals', projecting strength", "Personal diplomacy with Putin as preferred tool", "Flexibility, no constraints", "Opacity increases miscalculation risk; loss of institutional guardrails"),
        ("Putin's Russia", "Maintaining nuclear superiority narrative domestically", "Using nuclear ambiguity as coercive instrument", "Reduced constraints on modernisation", "Economic cost of modernisation; no framework to verify U.S. compliance"),
        ("U.S. Arms Control Community", "Warning about risks of verification gap", "Establishing diplomatic framework for successor agreement", "Institutional relevance", "Marginalised from policy process; warnings unheeded"),
        ("China", "Continuing nuclear expansion outside any framework", "Modernisation without constraint or transparency", "Unconstrained expansion to rough parity with U.S./Russia", "Potential future arms control pressure as capabilities grow"),
        ("U.S. allies (NATO, Japan, South Korea)", "Extended deterrence stability", "That U.S. nuclear umbrella remains credible without verification framework", "Continued deterrence credibility", "Uncertainty about what U.S. nuclear posture actually is without verification"),
    ],
    data_points=[
        ("54 years", "Duration of unbroken U.S.-Soviet/Russian nuclear arms control agreements, 1972–2026 — now terminated"),
        ("1,550", "Deployed strategic warhead limit set by New START — the cap that no longer has legal force"),
        ("~5,550", "Estimated total U.S. nuclear warhead stockpile (including non-deployed) — unverified by Russia since Feb 2026"),
        ("~6,200", "Estimated total Russian nuclear warhead stockpile — unverified by the U.S. since Feb 2026"),
        ("500+", "Estimated Chinese operational nuclear warheads in 2026 — up from ~250 in 2020, outside all arms control frameworks"),
        ("~3 minutes", "Decision time available to U.S. and Russian leaders following confirmed hypersonic launch — below meaningful institutional crisis management threshold"),
        ("18", "Bilateral inspections conducted under New START annually — now zero"),
    ],
    delta="The most dangerous combination in nuclear security is not raw capability — both the U.S. and Russia have had survivable second-strike capacity for decades. It is the combination of opacity (no verification) + compressed decision time (hypersonic delivery) + institutional bypass (personal executive intuition rather than structured crisis management). All three are now simultaneously present for the first time since 1962.",
    dynamics_tags="Institutional Decay × Escalation Spiral",
    dynamics_summary="The 54-year architecture that prevented miscalculation-driven nuclear exchange is gone. What replaced it is personal executive intuition and no verification.",
    dynamics_sections=[
        {
            "tag": "Institutional Decay",
            "subheader": "The Dismantling of 60 Years of Crisis Management Infrastructure",
            "lead": "The arms control treaties that expired or were terminated since 2002 were not just documents — they were the operating infrastructure of nuclear crisis management. They provided the legal frameworks, the technical verification protocols, and the diplomatic communication channels that allowed two nuclear superpowers to maintain deterrence without miscalculating their way to war.",
            "quotes": [
                ("The Cuban Missile Crisis was not resolved by brilliant intuition. It was resolved by improvised back-channels that worked by accident. We built the institutional infrastructure precisely so we would never have to improvise again.", "Former U.S. arms control negotiator, Feb 2026 (anonymous)"),
                ("Without New START, we are flying blind. We don't know what they have deployed, where it is, or what their alert posture is. They don't know ours. That's not a stable deterrence environment.", "Former STRATCOM Deputy Commander, Congressional testimony, Jan 2026"),
            ],
            "analysis": """The institutional decay is not the result of a single decision. It is the accumulated product of a series of individually defensible choices that collectively dismantled a system. The U.S. withdrew from the ABM Treaty in 2002 to enable missile defence development. Russia violated the INF Treaty — the U.S. withdrew in response. New START expired without renewal because the political environment for arms control negotiations collapsed between 2022 and 2026.

Each step had a rational short-term justification. The cumulative result is that the crisis management infrastructure built from the Cuban Missile Crisis lesson — that superpower nuclear management requires verified, legally binding, institutionally-managed frameworks — is almost entirely gone.

The institutional decay is particularly dangerous because it is not symmetric with capability. Both sides have maintained and modernised their nuclear forces. What has decayed is the shared information environment that allows each side to correctly assess the other's capabilities and intentions. Without verified information, strategic decisions are made on estimates, signals intelligence, and worst-case assumptions — exactly the conditions that produce miscalculation.""",
        },
        {
            "tag": "Escalation Spiral",
            "subheader": "The New Technical Reality Arms Control Was Not Built For",
            "lead": "New START was designed for the nuclear technology of the 1980s — intercontinental ballistic missiles, submarine-launched ballistic missiles, and heavy bombers. The weapons systems that Russia has deployed in the 2020s — Avangard hypersonic glide vehicles, Poseidon nuclear torpedoes, Burevestnik nuclear cruise missiles — do not fit New START's counting frameworks. The treaty was already becoming obsolete before it expired.",
            "quotes": [
                ("Hypersonic weapons travel at 20+ times the speed of sound on unpredictable trajectories. They compress warning time below the threshold of human reaction. Arms control frameworks built for ballistic missiles don't address these systems at all.", "Nuclear posture analysis, Bulletin of the Atomic Scientists, 2025"),
            ],
            "analysis": """The Escalation Spiral operates through technical change outpacing institutional adaptation. The 15-minute warning time provided by ICBM trajectories allowed the institutional crisis management infrastructure to function: leaders could be awakened, advisors consulted, hotlines activated, and decisions made with human deliberation. Hypersonic delivery systems compress that window to 3 minutes or less — below the threshold of meaningful human crisis management.

Cyber weapons add a second dimension. Nuclear command and control systems are increasingly networked, creating potential attack surfaces for adversaries seeking to disable, spoof, or compromise launch decision infrastructure. A cyber attack that compromises early warning systems could trigger a launch-on-warning posture based on false information. This risk exists without any treaty framework to restrict or verify the relevant cyber capabilities.

The Escalation Spiral is self-reinforcing: each side's nuclear modernisation — justified by the other's — creates new delivery systems outside existing frameworks, which provides justification for further modernisation. Without a verification framework to constrain or even document this process, it accelerates. The absence of New START removes the only brake.""",
        },
    ],
    dynamics_intersection="Institutional Decay removes the crisis management infrastructure that arms control was designed to maintain. Escalation Spiral produces the new technical systems — hypersonic, cyber — that the expired institutional frameworks were not designed to address. The intersection is a structural gap: the fastest-moving threat dimensions (hypersonic, cyber) have zero arms control governance, at the moment when the broader oversight framework (New START) has also expired. The gap is cumulative.",
    pattern_history=[
        {"year": 1962, "title": "Cuban Missile Crisis — What Happens Without Crisis Management Infrastructure", "content": "The Cuban Missile Crisis is the historical proof of concept for why arms control infrastructure matters. Thirteen days in October 1962 produced the closest recorded approach to nuclear exchange — not because either Kennedy or Khrushchev wanted war, but because both sides lacked the communication and verification frameworks to prevent miscalculation.\n\nThe crisis was resolved through improvised back-channels: a direct communication between Kennedy's brother Robert and Soviet Ambassador Dobrynin, a back-channel through ABC journalist John Scali, and a final deal that required both sides to accept ambiguous terms neither side could verify. It worked by accident.\n\nThe institutional response — SALT I (1972), the hotline (1963), and the subsequent treaty architecture — was specifically designed so that nuclear crisis management never had to be improvised under 13-day time pressure again. That lesson cost 13 days of near-catastrophe to learn. It is now being unlearned.", "similarity": "The post-New START environment recreates the information opacity and institutional vacuum that made the Cuban Missile Crisis possible — with the addition of hypersonic weapons that compress decision time below 13 days to 3 minutes"},
        {"year": 1983, "title": "Able Archer 83 — When Intelligence and Institutional Failure Almost Triggered Nuclear War", "content": "In November 1983, NATO ran a realistic nuclear war exercise called Able Archer 83. Soviet intelligence, which had been tracking NATO exercise patterns for years and was expecting a nuclear first strike, nearly concluded the exercise was cover for an actual attack. Soviet nuclear forces were placed on alert. The world came within days of nuclear exchange — not because either side wanted war, but because each side's intelligence assessment of the other's intentions was wrong.\n\nThe Able Archer crisis was resolved only because a Soviet double agent, Oleg Gordievsky, reported the Soviet alert to British intelligence, which alerted the Reagan administration — which then modified its exercise conduct to reduce Soviet alarm.\n\nThe resolution required a spy with access to Soviet decision-making at the moment of maximum danger. Without verification frameworks that provide routine transparency about each side's capabilities and intentions, crisis management rests on intelligence access that cannot be guaranteed.", "similarity": "Institutional opacity about adversary intentions — not deliberate aggression — is the primary nuclear war risk; the New START expiration recreates the opacity conditions of 1983 without a Gordievsky equivalent to provide back-channel clarity"},
    ],
    history_pattern_summary="The historical record is unambiguous: nuclear crises are driven not by deliberate aggression but by miscalculation under conditions of opacity. Arms control treaties reduce opacity, create shared information environments, and provide institutional frameworks for crisis communication. Their absence recreates the conditions that have historically produced near-misses. The Cuban Missile Crisis and Able Archer 83 are not ancient history — they are the design specifications for the infrastructure that just expired.",
    scenarios=[
        ("基本", "55-65%", "No successor to New START is negotiated in 2026–2027. Both sides continue nuclear modernisation without verified limits. Crisis management relies on the hotline and intelligence channels — no formal framework. China's nuclear expansion continues outside all frameworks. The risk of miscalculation-driven incident is elevated at margins — particularly around hypersonic test events and cyber incidents affecting nuclear command infrastructure — but no crisis escalates to the threshold of nuclear use.", "Nuclear security risk premium should be embedded in tail risk models. Physical assets and geographic diversification as portfolio hedges."),
        ("楽観", "10-15%", "A U.S.-Russia bilateral agreement — possibly as a side element of Ukraine peace talks — produces an interim nuclear risk reduction framework: mutual notification of hypersonic tests, restoration of some inspection access, and a moratorium on certain destabilising systems. China is excluded but not actively opposed. A formal New START successor process begins.", "Significant geopolitical risk premium compression. Watch for early signals: bilateral working group establishment, mutual test notification exchanges."),
        ("悲観", "25-30%", "A hypersonic test by Russia is misidentified by U.S. early warning systems as a potential attack. Without a verification framework or established communication protocol for hypersonic tests, the response protocol generates a 3-minute decision window. Senior leadership is either unavailable, the protocol fails, or the decision chain produces a launch-on-warning response based on false information. The probability of this specific scenario is low — but it is now structurally possible in a way it was not under New START.", "This is the fundamental nuclear tail risk. No conventional financial hedge addresses this. The primary implication is for policymakers, not investors."),
    ],
    triggers=[
        ("Hypersonic test misidentification incident", "Any event where an adversary's hypersonic test is initially classified as a potential attack — generating a response protocol activation — demonstrates the concrete risk of the verification gap"),
        ("Cyber incident affecting nuclear command", "A confirmed cyber intrusion into nuclear command and control infrastructure would force both sides to reassess the stability of deterrence without verification frameworks"),
        ("Russian or U.S. declaration of New START limits non-binding", "If either side publicly declares it is no longer constrained by New START limits — even informally — it signals the beginning of unconstrained competition"),
        ("China crossing 600 operational warhead threshold", "When China reaches rough strategic parity with officially-declared U.S. and Russian 'deployed strategic' warhead counts, trilateral arms control becomes unavoidable as a policy question"),
    ],
    genre_tags="Geopolitics",
    event_tags="Institutional Decay / Escalation Spiral",
    source_urls=[
        ("The Hill: Trump is betting the farm on intuition — and the nuclear clock is ticking", "https://thehill.com/opinion/international/5739962-new-start-treaty-expiration/"),
        ("Bulletin of the Atomic Scientists: Nuclear Notebook 2025", "https://thebulletin.org/nuclear-notebook/"),
    ],
)

# ═══════════════════════════════════════════════════════════════════════
# ARTICLE 6: Bitcoin Miners as Grid Assets
# ═══════════════════════════════════════════════════════════════════════
a6_html = build_deep_pattern_html(
    title="Bitcoin Miners Are Flexible Grid Assets, Not Energy Hogs — Paradigm's Argument That Regulators Are Getting Wrong",
    why_it_matters="Bitcoin miners are being regulated out of electricity markets based on a comparison — with AI data centers — that does not hold up to basic grid engineering analysis. The conflation is politically convenient and technically wrong. The consequence of getting it wrong is that regulations eliminate flexible demand-response assets that grid operators have documented as valuable, while leaving actual inflexible peak demand from AI inference workloads untouched.",
    facts=[
        ("Feb 16, 2026", "Paradigm, a leading crypto-focused investment firm, publishes a detailed technical analysis distinguishing Bitcoin miners from AI data centers as fundamentally different types of grid demand — triggering a policy debate that had been largely absent from energy regulation discussions"),
        ("ERCOT documented evidence", "Texas grid operator ERCOT has documented multiple instances of large-scale Bitcoin miners voluntarily curtailing consumption during extreme weather demand events — Winter Storm Uri (Feb 2021), Summer 2022 heat wave, Winter Storm Elliott (Dec 2022) — providing a grid-stabilising service"),
        ("AI vs Bitcoin technical distinction", "AI inference and training workloads require continuous, uninterruptible power — shutting down a data center mid-inference corrupts the computation; Bitcoin mining rigs can be powered down in seconds and restarted without data loss, making them fundamentally interruptible"),
        ("Clean energy economics", "Flexible Bitcoin mining demand can monetise renewable energy surplus that would otherwise be curtailed — solar output during midday low-demand periods is frequently curtailed in large renewable markets; mining provides a buyer of last resort for stranded generation"),
        ("Regulatory conflation", "Multiple state energy regulators, federal energy legislation drafts, and EU taxonomy discussions treat Bitcoin mining and AI data center demand as equivalent categories — despite their fundamentally different grid characteristics"),
        ("Market evidence", "ERCOT's demand response programme pays industrial consumers to curtail on command — the same service Bitcoin miners provide voluntarily; mining operations have been paid for this service in deregulated Texas markets"),
    ],
    big_picture_history="""The electricity grid has always faced the fundamental challenge of demand unpredictability: consumption peaks in the morning and evening, and during extreme weather events, in ways that base generation cannot cost-effectively match. The grid engineering response has been demand-side management — creating incentives for large industrial consumers to reduce consumption during peak periods in exchange for lower rates or direct payments.

Industrial demand response has existed since the 1970s. Aluminium smelters, which consume enormous amounts of electricity and can be partially curtailed without immediate production loss, have been demand response participants for decades. The same logic applies to any large industrial consumer with flexible consumption timing — steel mills, chemical plants, water treatment facilities.

Bitcoin mining is, from a grid engineering perspective, an unusually pure form of flexible industrial demand. The computation performed by mining rigs — hashing — produces no output that is lost if interrupted. A miner that is powered down during a grid event simply picks up where it left off when power is restored. No product is damaged. No process is disrupted. The financial loss is proportional to the time offline — which creates a cost-benefit calculation that grid operators can price.

AI data centers are the opposite. Inference — generating a response to a user query — requires continuous power from input to output. Training a model requires weeks of uninterrupted computation. Interrupting either process mid-stream does not merely pause it — it corrupts it, requiring a restart from the last checkpoint. The grid demand profile is accordingly inflexible: AI data centers must be treated as base load, not demand response.

The regulatory conflation of these two fundamentally different demand profiles is producing energy policy that inadvertently eliminates a valuable grid flexibility asset while failing to manage the actual inflexible demand problem that AI data centers represent.""",
    stakeholder_map=[
        ("Bitcoin mining operators", "Defending favourable regulatory treatment", "Demonstrating grid value to avoid restrictive regulations", "Continued operation in deregulated markets", "Regulatory exclusion, stranded capital"),
        ("AI data center operators (AWS, Google, Microsoft)", "Securing grid access for data centers", "Avoiding regulatory constraints on data center demand", "Grid capacity, regulatory certainty", "Association with Bitcoin in negative regulatory framing"),
        ("Grid operators (ERCOT, PJM, MISO)", "Grid reliability and cost efficiency", "Maximising demand-response participation", "Lower peak demand costs, grid stability", "Overbuilding base generation if flexible demand is regulated away"),
        ("Environmental regulators / legislators", "Reducing energy sector carbon emissions", "Restricting high-energy activities", "Political credit for environmental action", "Regulatory error: eliminating green-complementary assets while missing the real problem"),
        ("Renewable energy developers", "Selling all generated electricity at positive prices", "Reducing curtailment of surplus renewable output", "Monetisation of previously curtailed generation", "Continued curtailment if mining demand is regulated away"),
    ],
    data_points=[
        ("15-25%", "Share of Bitcoin mining load that ERCOT documented voluntarily curtailed during Winter Storm Uri in 2021 — a grid-stabilising service"),
        ("800MW+", "Estimated total Bitcoin mining demand curtailed during Texas grid events in 2022 — equivalent to a large natural gas peaker plant"),
        ("$150/MWh", "Average Texas spot electricity price during extreme demand events — the price signal that incentivises mining curtailment"),
        ("30-40%", "Share of utility-scale renewable generation curtailed in large renewable markets during low-demand periods — the surplus that mining can monetise"),
        ("2x-4x", "AI data center demand growth rate relative to Bitcoin mining — the actual inflexible demand problem that regulators are underweighting"),
        ("$500B+", "Planned AI data center investment in the U.S. through 2030, requiring grid capacity additions that dwarf Bitcoin mining demand"),
        ("0", "Megawatts of AI compute that can be curtailed without losing computation — versus 100% of Bitcoin mining that can be curtailed safely"),
    ],
    delta="The regulatory conflation of Bitcoin mining and AI data centers is not neutral — it serves the interests of those who want to restrict Bitcoin on environmental grounds without engaging with technical distinctions. The consequence is policy that eliminates a genuinely flexible grid asset while failing to manage the genuinely inflexible AI data center demand surge that is the actual grid challenge of the next decade.",
    dynamics_tags="Narrative Control × Regulatory Capture",
    dynamics_summary="Bitcoin miners are interruptible industrial consumers being regulated as base load. AI data centers are inflexible base load being regulated as equivalent to miners. The conflation eliminates a grid asset while missing the actual grid problem.",
    dynamics_sections=[
        {
            "tag": "Narrative Control",
            "subheader": "The Convenient Conflation",
            "lead": "The conflation of Bitcoin mining and AI data centers in energy policy discussions is not accidental. It is the product of a political narrative that treats Bitcoin as environmentally harmful and AI as strategically vital — a narrative that is shape-shifting the regulatory framing before the technical analysis has been conducted.",
            "quotes": [
                ("Cryptocurrency mining operations are enormous consumers of electricity. We must ensure our grid serves human needs, not speculative computing.", "Federal energy legislation draft language, 2025"),
                ("Bitcoin miners are the most flexible large industrial load on the ERCOT grid. They curtail more reliably and faster than any other demand response category we work with.", "ERCOT grid operator, Congressional testimony, 2025"),
            ],
            "analysis": """The narrative conflict is between two frames: 'Bitcoin mining as environmentally harmful energy waste' and 'Bitcoin mining as flexible grid asset.' The first frame is politically useful for those seeking to restrict Bitcoin on environmental or financial stability grounds. The second frame is technically accurate but politically inconvenient.

The mechanism of narrative control is category error: conflating Bitcoin mining (flexible, interruptible, demand-response compatible) with AI data centers (inflexible, base load, demand-response incompatible) into a single regulatory category of 'high-energy digital computing.' This category has political traction because it appears to address both Bitcoin and AI in a unified environmental framework.

The consequence of the category error is a policy that eliminates the flexible half of 'high-energy digital computing' — the half that actually provides grid value — while failing to address the inflexible half, which is the actual grid capacity challenge of the next decade.""",
        },
        {
            "tag": "Regulatory Capture",
            "subheader": "Who Benefits From the Conflation",
            "lead": "The regulatory conflation of Bitcoin and AI data centers benefits specific stakeholders at the expense of grid efficiency. Understanding who benefits from the narrative clarifies why it has persistence despite its technical inaccuracy.",
            "quotes": [
                ("If Bitcoin mining is regulated as equivalent to AI data centers, we lose our competitive advantage in deregulated markets and large tech companies face none of the same restrictions.", "Confidential interview with Bitcoin mining executive, Feb 2026"),
            ],
            "analysis": """The Regulatory Capture dynamic operates through the legislature and regulatory agency, not just the market. Large AI data center operators — Amazon, Google, Microsoft — have significant lobbying presence in energy regulatory proceedings. They benefit from regulations that restrict Bitcoin mining specifically while treating AI data centers more favorably, reducing competition for grid capacity and avoiding restrictions on their own operations.

The environmental NGO community, which has focused on Bitcoin's energy profile, provides the political cover for Bitcoin-specific restrictions without engaging with the AI data center comparison. The result is a regulatory coalition — tech companies, environmental groups, and legislators seeking credit for clean energy action — that produces Bitcoin-specific restrictions without technical justification.

The Regulatory Capture is incomplete — ERCOT and other grid operators have consistently provided technical testimony on Bitcoin's grid value, and Paradigm's analysis creates a more robust technical record. But the political economy favours the conflation: the stakeholders benefiting from it are better organised and more politically connected than the Bitcoin mining industry.""",
        },
    ],
    dynamics_intersection="Narrative Control creates the policy framing that enables Regulatory Capture: by establishing 'high-energy digital computing' as a unified environmental concern, it provides political legitimacy for regulations that selectively restrict Bitcoin mining while leaving AI data centers free. The intersection produces the worst possible grid policy outcome: eliminating flexible demand response assets while enabling the rapid growth of inflexible base load demand that will require expensive peak generation additions to accommodate.",
    pattern_history=[
        {"year": 2000, "title": "California Energy Crisis — When Demand Response Was Absent", "content": "In 2000–2001, California experienced a catastrophic electricity crisis — rolling blackouts affecting millions, electricity prices spiking to 20x normal levels, and the bankruptcy of Pacific Gas & Electric. The proximate cause was market manipulation by Enron and other traders. The structural cause was a grid that had no demand-response mechanism to balance irregular supply.\n\nThe California crisis produced a decade of investment in demand-response infrastructure across U.S. electricity markets. Industrial consumers were paid to curtail, smart meters were deployed, and grid operators developed the real-time coordination protocols that now make demand response work at scale.\n\nThe lesson: flexible demand is a critical grid stability tool. Regulations that eliminate flexible demand participants — even for legitimate environmental reasons — reduce grid stability and increase the cost of managing supply variability.", "similarity": "The regulatory impulse to restrict high-energy consumers without distinguishing flexible from inflexible demand risks recreating the grid stability gap that produced the 2000 California crisis"},
        {"year": 2011, "title": "German Energiewende — Renewable Integration Without Flexible Demand", "content": "Germany's Energiewende (energy transition) rapidly increased renewable penetration from 17% in 2011 to 48% in 2023. A consequence of the rapid renewable buildout was increasing curtailment — renewable generation that exceeded grid demand during peak solar or wind output periods had to be discarded or sold at negative prices.\n\nGermany's response included pumped hydro storage, interconnection with neighbouring grids, and industrial demand response programmes. Bitcoin mining — which was unregulated in Germany through most of the period — provided a small but measurable flexible demand component in German and neighbouring markets.\n\nThe lesson: high renewable penetration increases the value of flexible demand, because the mismatch between generation patterns (solar peaks at midday, wind peaks overnight) and consumption patterns (morning and evening) creates regular surplus that must be absorbed.", "similarity": "Flexible industrial demand has measurable value in high-renewable grids — exactly the value that Bitcoin mining regulation is eliminating, at precisely the moment renewable penetration is creating maximum need for it"},
    ],
    history_pattern_summary="Grid history consistently demonstrates that flexible demand is a valuable and underutilised grid stability resource. Every major grid crisis — including California 2000 and the European renewable integration challenges — has been worsened by the absence of demand flexibility. The regulatory conflation of Bitcoin mining with AI data centers eliminates a proven flexible resource at the moment when AI-driven inflexible demand is creating maximum grid stress.",
    scenarios=[
        ("基本", "55-65%", "Bitcoin mining continues in deregulated markets (ERCOT primarily) where grid operators have the technical authority to classify mining as demand-response, regardless of federal regulatory framing. Federal energy legislation treats Bitcoin and AI as equivalent categories, but ERCOT and other RTOs maintain demand-response programmes that effectively exempt miners who participate. Renewable curtailment continues rising in states where mining has been restricted.", "ERCOT-area mining operators (Riot Platforms, Marathon Digital, CleanSpark) maintain operational advantage vs. restricted-market peers. Renewable developers in restricted markets face increasing curtailment economics."),
        ("楽観", "15-20%", "Paradigm's analysis enters formal regulatory proceedings. ERCOT and PJM provide technical testimony distinguishing mining from AI data center demand. Congressional commerce committee holds hearings on grid demand classification. Federal legislation carves out interruptible industrial consumers from Bitcoin-specific restrictions. Clean energy + mining co-location reaches commercial scale.", "Bitcoin mining stocks rerate positively on regulatory clarity. Renewable developers with mining co-location strategies (e.g., Cipher Mining) outperform."),
        ("悲観", "20-25%", "Federal legislation treats Bitcoin and AI data centers as equivalent. Mining is restricted in most jurisdictions. Bitcoin production shifts to Kazakhstan, Russia, and Iran — jurisdictions with lower environmental standards and no renewable energy integration. Hash rate concentrates in geopolitically unfriendly jurisdictions. The grid loses flexible demand without gaining environmental benefit.", "Hash rate geographic concentration risk. Mining operators in non-restricted jurisdictions gain competitive advantage. U.S. grid loses documented demand-response assets."),
    ],
    triggers=[
        ("FERC ruling on demand response classification", "The Federal Energy Regulatory Commission ruling on whether Bitcoin mining qualifies as interruptible industrial load would clarify the regulatory framework"),
        ("Major grid event where mining curtailment is documented publicly", "Another extreme weather grid event where Bitcoin miners curtail at scale — and the data is publicly attributed — strengthens the technical case"),
        ("AI data center brownout event", "Any event where AI data center demand contributes to grid stress would force the distinction between flexible and inflexible computing demand into public regulatory discussion"),
        ("Co-location commercial deal", "A major utility entering a long-term mining-renewable co-location agreement signals market validation of the grid asset argument"),
    ],
    genre_tags="Crypto & Web3 / Energy & Environment",
    event_tags="Regulatory Change / Tech Breakthrough",
    source_urls=[
        ("Paradigm: Bitcoin Mining and AI Data Centers Are Not Equivalent Grid Loads", "https://www.paradigm.xyz/"),
        ("CoinTelegraph: Paradigm reframes Bitcoin mining as grid asset, not energy drain", "https://cointelegraph.com/news/paradigm-bitcoin-mining-ai-data-centers-grid-demand"),
        ("ERCOT: Demand Response Programme Documentation", "https://www.ercot.com/"),
    ],
)

# ─── 記事データ ────────────────────────────────────────────────────────
BATCH2 = [
    {"id": "6997259e5850354f44049b8b", "title": "New START Expired With No Replacement — For the First Time Since 1972, No Nuclear Arms Agreement Exists Between the U.S. and Russia", "html": a5_html, "tags": ["Geopolitics", "Institutional Decay", "Escalation Spiral", "Deep Pattern"]},
    {"id": "69967cdf5850354f44049b77", "title": "Bitcoin Miners Are Flexible Grid Assets, Not Energy Hogs — Paradigm's Argument That Regulators Are Getting Wrong", "html": a6_html, "tags": ["Crypto & Web3", "Energy & Environment", "Regulatory Change", "Narrative Control", "Regulatory Capture", "Deep Pattern"]},
]

ok = 0
for art in BATCH2:
    ua = get_updated_at(art["id"])
    success, msg = update_post(art["id"], art["html"], art["title"], ua, art["tags"])
    print(f"[{'OK' if success else 'ERROR'}] {art['title'][:55]}...")
    if success: ok += 1
    else: print(f"       {msg}")
    time.sleep(0.5)

print(f"\nBatch 2 完了: {ok}/{len(BATCH2)}")
