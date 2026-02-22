#!/usr/bin/env python3
"""Create 'Why We Categorize This Way' explanation pages (JA + EN) as Ghost Pages.
Explains the 3-layer taxonomy rationale with visual examples.
"""
import os, sys, json, jwt, datetime, requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
GHOST_URL = "https://nowpattern.com"
if not API_KEY or ":" not in API_KEY:
    print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not set"); sys.exit(1)
key_id, key_secret = API_KEY.split(":")

def ghost_token():
    iat = int(datetime.datetime.now().timestamp())
    return jwt.encode({"iat": iat, "exp": iat + 300, "aud": "/admin/"},
        bytes.fromhex(key_secret), algorithm="HS256",
        headers={"alg": "HS256", "typ": "JWT", "kid": key_id})

def ghost_headers():
    return {"Authorization": f"Ghost {ghost_token()}", "Content-Type": "application/json"}

# Colors
C_GENRE = "#2563eb"
C_EVENT = "#16a34a"
C_DYNAMICS = "#FF1A75"
C_BG = "#f8f6f0"

CSS = """<style>
.np-guide { max-width: 800px; margin: 0 auto; font-size: 1.05em; line-height: 1.8; }
.np-guide h2 { margin-top: 2em; padding-bottom: 6px; }
.np-guide h2.genre { color: {C_GENRE}; border-bottom: 3px solid {C_GENRE}; }
.np-guide h2.event { color: {C_EVENT}; border-bottom: 3px solid {C_EVENT}; }
.np-guide h2.dynamics { color: {C_DYNAMICS}; border-bottom: 3px solid {C_DYNAMICS}; }
.np-guide .layer-box { border-radius: 8px; padding: 16px 20px; margin: 16px 0; }
.np-guide .layer-box.genre { background: #eef4ff; border-left: 5px solid {C_GENRE}; }
.np-guide .layer-box.event { background: #eefbf3; border-left: 5px solid {C_EVENT}; }
.np-guide .layer-box.dynamics { background: #fff0f5; border-left: 5px solid {C_DYNAMICS}; }
.np-guide .example-card { background: #fff; border: 1px solid #e0dcd4; border-radius: 8px; padding: 16px 20px; margin: 16px 0; }
.np-guide .tag { display: inline-block; border-radius: 14px; padding: 2px 12px; font-size: 0.85em; color: #fff; margin: 2px 4px; font-weight: 600; }
.np-guide .tag.genre { background: {C_GENRE}; }
.np-guide .tag.event { background: {C_EVENT}; }
.np-guide .tag.dynamics { background: {C_DYNAMICS}; }
.np-guide table { width: 100%; border-collapse: collapse; margin: 16px 0; }
.np-guide th { background: #1a1a2e; color: #fff; padding: 10px 14px; text-align: left; font-size: 0.9em; }
.np-guide td { padding: 10px 14px; border-bottom: 1px solid #e8e8e8; vertical-align: top; }
.np-guide .cta { background: #1a1a2e; color: #fff; padding: 20px 24px; border-radius: 8px; margin: 24px 0; text-align: center; }
.np-guide .cta a { color: #c9a84c; font-weight: 700; text-decoration: none; }
.np-guide .cta a:hover { text-decoration: underline; }
.np-guide .compare { display: flex; gap: 16px; margin: 16px 0; }
.np-guide .compare > div { flex: 1; padding: 14px; border-radius: 8px; }
.np-guide .compare .before { background: #f5f5f5; border: 1px solid #ddd; }
.np-guide .compare .after { background: #eef4ff; border: 1px solid {C_GENRE}; }
</style>""".replace("{C_GENRE}", C_GENRE).replace("{C_EVENT}", C_EVENT).replace("{C_DYNAMICS}", C_DYNAMICS)


def build_ja_guide():
    html = CSS + '<div class="np-guide">\n'
    html += "<h1>なぜNowpatternはニュースを3層に分けるのか</h1>\n"

    html += "<p>ニュースサイトの多くは「政治」「経済」「テクノロジー」のように1つのカテゴリで記事を分類します。"
    html += "しかし、世界で起きていることを本当に理解するには、それだけでは足りません。</p>\n"

    html += "<p><strong>Nowpatternは、すべての記事を3つの問いで構造化します。</strong></p>\n"

    # The 3 questions
    html += '<div class="layer-box genre">'
    html += f'<strong style="color:{C_GENRE};">Layer 1: ジャンル（Genre）</strong><br>'
    html += '「<strong>何についての記事か？</strong>」— 地政学、暗号資産、エネルギー、テクノロジーなど、記事の主題領域。</div>\n'

    html += '<div class="layer-box event">'
    html += f'<strong style="color:{C_EVENT};">Layer 2: イベント（Event）</strong><br>'
    html += '「<strong>何が起きたか？</strong>」— 軍事衝突、規制変更、市場ショックなど、ニュースのきっかけ（トリガー）。</div>\n'

    html += '<div class="layer-box dynamics">'
    html += f'<strong style="color:{C_DYNAMICS};">Layer 3: 力学 / NOW Pattern（Dynamics）</strong><br>'
    html += '「<strong>なぜそうなるのか？</strong>」— エスカレーション、規制の虜、ショック・ドクトリンなど、表面のニュースの裏にある構造的パターン。</div>\n'

    # Why 3 layers?
    html += '<h2 style="color: #1a1a2e; border-bottom: 3px solid #1a1a2e;">なぜ1つではなく3つなのか</h2>\n'

    html += '<div class="compare"><div class="before">'
    html += '<strong>従来のニュースサイト</strong><br>'
    html += '「政治」に分類された記事が1000件。<br>軍事も外交も法律も全部「政治」。<br>'
    html += '<em>→ 探したい記事が見つからない</em>'
    html += '</div><div class="after">'
    html += '<strong>Nowpattern</strong><br>'
    html += f'<span class="tag genre">地政学・安全保障</span> × <span class="tag event">軍事衝突</span> × <span class="tag dynamics">エスカレーション</span><br>'
    html += '3つの軸で絞り込むと、「なぜ戦争がエスカレートするのか」のパターンだけが見える。<br>'
    html += '<em>→ 構造が見える</em>'
    html += '</div></div>\n'

    # Concrete example
    html += '<h2 style="color: #1a1a2e; border-bottom: 3px solid #1a1a2e;">具体例: 同じジャンルでも力学が違う</h2>\n'

    html += '<div class="example-card">'
    html += '<strong>「イランがホルムズ海峡を封鎖」</strong><br>'
    html += f'<span class="tag genre">地政学・安全保障</span> <span class="tag genre">エネルギー</span> '
    html += f'<span class="tag event">軍事衝突</span> '
    html += f'<span class="tag dynamics">エスカレーション</span> <span class="tag dynamics">資源パワー</span><br>'
    html += '<em>→ 力学は「資源を人質にした交渉術」</em>'
    html += '</div>\n'

    html += '<div class="example-card">'
    html += '<strong>「ルビオ＝王毅会談」</strong><br>'
    html += f'<span class="tag genre">地政学・安全保障</span> <span class="tag genre">経済・貿易</span> '
    html += f'<span class="tag event">制裁・経済戦争</span> '
    html += f'<span class="tag dynamics">出口ゲーム</span> <span class="tag dynamics">ナラティブ・コントロール</span><br>'
    html += '<em>→ 力学は「双方が"勝った"と見せたい外交劇」</em>'
    html += '</div>\n'

    html += '<p>どちらも「地政学」の記事ですが、<strong>裏で動いている力学がまったく違います</strong>。'
    html += '3層目の「力学」があるからこそ、「同じジャンルの別パターン」を見分けられるのです。</p>\n'

    # NOW Pattern
    html += f'<h2 class="dynamics">NOW Pattern（力学）が核心</h2>\n'
    html += "<p>Nowpatternの名前の由来は、この3層目 —「NOW Pattern」— にあります。</p>\n"
    html += "<p>ニュースの表面だけを追うと「何が起きたか」は分かります。"
    html += "しかし「<strong>なぜそうなるのか</strong>」を理解しないと、次に何が起きるかは予測できません。</p>\n"
    html += "<p>NOW Patternは、歴史上繰り返されてきた構造的パターンに名前を付けたものです：</p>\n"

    html += '<table>'
    html += f'<tr><th>パターン名</th><th>一言で言うと</th><th>例</th></tr>\n'
    html += f'<tr><td><span class="tag dynamics">エスカレーション</span></td><td>相互報復の悪循環</td><td>ロシア-ウクライナの段階的激化</td></tr>\n'
    html += f'<tr><td><span class="tag dynamics">規制の虜</span></td><td>規制する側が業界に取り込まれる</td><td>DeFiロビー団体によるSEC政策への影響</td></tr>\n'
    html += f'<tr><td><span class="tag dynamics">ショック・ドクトリン</span></td><td>危機に乗じた政策変更</td><td>トランプの排ガス規制撤廃</td></tr>\n'
    html += f'<tr><td><span class="tag dynamics">出口ゲーム</span></td><td>全員が「勝った」と言える着地点探し</td><td>ジュネーブ停戦交渉</td></tr>\n'
    html += '</table>\n'

    html += '<p>全20パターンの一覧は <a href="/taxonomy-ja/">タクソノミー（全タグ一覧）</a> で確認できます。</p>\n'

    # How to use
    html += '<h2 style="color: #1a1a2e; border-bottom: 3px solid #1a1a2e;">読者としての使い方</h2>\n'
    html += '<table>'
    html += '<tr><th>やりたいこと</th><th>方法</th></tr>\n'
    html += '<tr><td>暗号資産ニュースだけ読みたい</td><td><span class="tag genre">暗号資産・Web3</span> タグをクリック</td></tr>\n'
    html += '<tr><td>「なぜ規制が変わるのか」を理解したい</td><td><span class="tag dynamics">規制の虜</span> タグで横断検索</td></tr>\n'
    html += '<tr><td>同じパターンの事例を比較したい</td><td>同じ力学タグの記事を並べて読む</td></tr>\n'
    html += '<tr><td>ジャンルを超えた構造の共通点を見つけたい</td><td>力学タグが同じ記事を異なるジャンルから探す</td></tr>\n'
    html += '</table>\n'

    # CTA
    html += '<div class="cta">'
    html += '<strong>全タグ一覧を見る</strong><br>'
    html += '<a href="/taxonomy-ja/">→ Nowpattern タクソノミー（全タグ一覧）</a>'
    html += '</div>\n'

    html += '</div>\n'
    return html


def build_en_guide():
    html = CSS + '<div class="np-guide">\n'
    html += "<h1>Why Nowpattern Uses a 3-Layer Tag System</h1>\n"

    html += "<p>Most news sites sort articles into a single category: \"Politics,\" \"Business,\" \"Tech.\" "
    html += "But to truly understand what's happening in the world, one dimension isn't enough.</p>\n"

    html += "<p><strong>Nowpattern structures every article with three questions.</strong></p>\n"

    # The 3 questions
    html += '<div class="layer-box genre">'
    html += f'<strong style="color:{C_GENRE};">Layer 1: Genre</strong><br>'
    html += '"<strong>What is this about?</strong>" — The subject domain: geopolitics, crypto, energy, technology, etc.</div>\n'

    html += '<div class="layer-box event">'
    html += f'<strong style="color:{C_EVENT};">Layer 2: Event</strong><br>'
    html += '"<strong>What happened?</strong>" — The trigger: military conflict, regulation change, market shock, etc.</div>\n'

    html += '<div class="layer-box dynamics">'
    html += f'<strong style="color:{C_DYNAMICS};">Layer 3: Dynamics / NOW Pattern</strong><br>'
    html += '"<strong>Why does this happen?</strong>" — The structural pattern: escalation spiral, regulatory capture, shock doctrine, etc.</div>\n'

    # Why 3 layers?
    html += '<h2 style="color: #1a1a2e; border-bottom: 3px solid #1a1a2e;">Why Three Layers Instead of One?</h2>\n'

    html += '<div class="compare"><div class="before">'
    html += '<strong>Traditional News Sites</strong><br>'
    html += '1,000 articles tagged "Politics."<br>Military, diplomacy, law — all lumped together.<br>'
    html += '<em>→ You can\'t find what you\'re looking for</em>'
    html += '</div><div class="after">'
    html += '<strong>Nowpattern</strong><br>'
    html += f'<span class="tag genre">Geopolitics</span> × <span class="tag event">Military Conflict</span> × <span class="tag dynamics">Escalation</span><br>'
    html += 'Filter by three axes and you see only "why wars escalate" — the structural pattern.<br>'
    html += '<em>→ The structure becomes visible</em>'
    html += '</div></div>\n'

    # Concrete example
    html += '<h2 style="color: #1a1a2e; border-bottom: 3px solid #1a1a2e;">Example: Same Genre, Different Dynamics</h2>\n'

    html += '<div class="example-card">'
    html += '<strong>"Iran Blocks the Strait of Hormuz"</strong><br>'
    html += f'<span class="tag genre">Geopolitics</span> <span class="tag genre">Energy</span> '
    html += f'<span class="tag event">Military Conflict</span> '
    html += f'<span class="tag dynamics">Escalation</span> <span class="tag dynamics">Resource Power</span><br>'
    html += '<em>→ The dynamics: "holding resources hostage as leverage"</em>'
    html += '</div>\n'

    html += '<div class="example-card">'
    html += '<strong>"Rubio–Wang Yi Summit"</strong><br>'
    html += f'<span class="tag genre">Geopolitics</span> <span class="tag genre">Economy & Trade</span> '
    html += f'<span class="tag event">Sanctions</span> '
    html += f'<span class="tag dynamics">Exit Game</span> <span class="tag dynamics">Narrative Control</span><br>'
    html += '<em>→ The dynamics: "both sides need to claim victory"</em>'
    html += '</div>\n'

    html += '<p>Both are "geopolitics" articles, but the <strong>underlying dynamics are completely different</strong>. '
    html += 'The third layer — dynamics — is what lets you tell them apart.</p>\n'

    # NOW Pattern
    html += f'<h2 class="dynamics">NOW Pattern: The Core of Nowpattern</h2>\n'
    html += "<p>Nowpattern gets its name from this third layer — the \"NOW Pattern.\"</p>\n"
    html += "<p>Following the news surface tells you <em>what</em> happened. "
    html += "Understanding the underlying pattern tells you <strong>why</strong> — and helps predict what comes next.</p>\n"
    html += "<p>NOW Patterns are recurring structural forces that have repeated throughout history:</p>\n"

    html += '<table>'
    html += '<tr><th>Pattern</th><th>In a Nutshell</th><th>Example</th></tr>\n'
    html += f'<tr><td><span class="tag dynamics">Escalation Spiral</span></td><td>Tit-for-tat retaliation cycles</td><td>Russia-Ukraine progressive escalation</td></tr>\n'
    html += f'<tr><td><span class="tag dynamics">Regulatory Capture</span></td><td>Regulators co-opted by the regulated</td><td>DeFi lobby shaping SEC policy</td></tr>\n'
    html += f'<tr><td><span class="tag dynamics">Shock Doctrine</span></td><td>Policy change during crisis</td><td>Trump rolling back emissions rules</td></tr>\n'
    html += f'<tr><td><span class="tag dynamics">Exit Game</span></td><td>Everyone seeks a "we won" landing</td><td>Geneva ceasefire negotiations</td></tr>\n'
    html += '</table>\n'

    html += '<p>See all 20 patterns in the <a href="/taxonomy-en/">full taxonomy reference</a>.</p>\n'

    # How to use
    html += '<h2 style="color: #1a1a2e; border-bottom: 3px solid #1a1a2e;">How to Use Tags as a Reader</h2>\n'
    html += '<table>'
    html += '<tr><th>You Want To...</th><th>How</th></tr>\n'
    html += '<tr><td>Read only crypto news</td><td>Click the <span class="tag genre">Crypto & Web3</span> tag</td></tr>\n'
    html += '<tr><td>Understand "why regulations change"</td><td>Browse the <span class="tag dynamics">Regulatory Capture</span> tag</td></tr>\n'
    html += '<tr><td>Compare similar patterns</td><td>Read articles with the same dynamics tag</td></tr>\n'
    html += '<tr><td>Find cross-domain structural similarities</td><td>Look for the same dynamics tag across different genres</td></tr>\n'
    html += '</table>\n'

    # CTA
    html += '<div class="cta">'
    html += '<strong>Explore All Tags</strong><br>'
    html += '<a href="/taxonomy-en/">→ Nowpattern Taxonomy (All Tags)</a>'
    html += '</div>\n'

    html += '</div>\n'
    return html


def create_ghost_page(title, slug, html_content, meta_title, meta_description):
    url = f"{GHOST_URL}/ghost/api/admin/pages/?source=html"
    payload = {"pages": [{"title": title, "slug": slug, "html": html_content,
        "status": "published", "meta_title": meta_title, "meta_description": meta_description}]}
    r = requests.post(url, json=payload, headers=ghost_headers(), verify=False)
    if r.status_code == 201:
        page = r.json()["pages"][0]
        print(f"OK: {title} -> {GHOST_URL}/{page['slug']}/")
        return page
    else:
        print(f"ERROR {r.status_code}: {r.text[:500]}")
        return None


def main():
    print("=== Creating Taxonomy Guide Pages ===\n")

    for slug in ["taxonomy-guide-ja", "taxonomy-guide-en"]:
        url = f"{GHOST_URL}/ghost/api/admin/pages/slug/{slug}/"
        r = requests.get(url, headers=ghost_headers(), verify=False)
        if r.status_code == 200:
            page = r.json()["pages"][0]
            print(f"Deleting old '{slug}'...")
            requests.delete(f"{GHOST_URL}/ghost/api/admin/pages/{page['id']}/", headers=ghost_headers(), verify=False)

    ja_html = build_ja_guide()
    print(f"\nJA: {len(ja_html)} chars")
    create_ghost_page(
        "なぜNowpatternはニュースを3層に分けるのか", "taxonomy-guide-ja", ja_html,
        "なぜ3層タグシステムなのか | Nowpattern",
        "Nowpatternが全記事を「ジャンル×イベント×力学」の3層で構造化する理由と使い方。")

    en_html = build_en_guide()
    print(f"\nEN: {len(en_html)} chars")
    create_ghost_page(
        "Why Nowpattern Uses a 3-Layer Tag System", "taxonomy-guide-en", en_html,
        "Why a 3-Layer Tag System | Nowpattern",
        "Why Nowpattern structures every article with Genre, Event, and Dynamics tags — and how to use them.")

    print(f"\nDone: {GHOST_URL}/taxonomy-guide-ja/ | {GHOST_URL}/taxonomy-guide-en/")


if __name__ == "__main__":
    main()
