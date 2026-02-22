#!/usr/bin/env python3
"""Nowpattern タクソノミーページ更新スクリプト

Ghost上の4つのタクソノミーページを taxonomy.json から動的生成して更新する。
- taxonomy-ja / taxonomy-en: タクソノミー一覧 + 3層フィルターJS
- taxonomy-guide-ja / taxonomy-guide-en: 使い方ガイド

使い方:
  python3 update_taxonomy_pages.py [--dry-run]
"""

import json
import time
import hashlib
import hmac
import base64
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

GHOST_URL = "https://nowpattern.com"
GHOST_API_KEY = ""
TAXONOMY_PATH = "/opt/shared/scripts/nowpattern_taxonomy.json"
CONTENT_API_KEY = "75626da2b27b59aa68e2bcdc6d"

try:
    with open("/opt/cron-env.sh") as f:
        for line in f:
            if "NOWPATTERN_GHOST_ADMIN_API_KEY" in line:
                GHOST_API_KEY = line.split("=", 1)[1].strip().strip("'").strip('"')
                break
except FileNotFoundError:
    GHOST_API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")


def make_jwt(api_key):
    key_id, secret = api_key.split(":")
    iat = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iat": iat, "exp": iat + 300, "aud": "/admin/"}
    def b64url(data):
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
    h = b64url(json.dumps(header).encode())
    p = b64url(json.dumps(payload).encode())
    sig = hmac.new(bytes.fromhex(secret), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{b64url(sig)}"


def load_taxonomy():
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# --- 色定義（フィルターとコンテンツで統一） ---
CG = "#2563eb"  # Genre: Blue
CE = "#16a34a"  # Event: Green
CD = "#FF1A75"  # Dynamics: Pink
CAT_COLORS = {"支配": "#dc2626", "対立": "#f59e0b", "崩壊": "#6b7280", "転換": "#3b82f6"}


# =============================================================================
# フィルターJS生成（codeinjection_foot用）
# =============================================================================
def build_filter_js(tax, lang="ja"):
    """3層フィルターJSを taxonomy.json から動的生成"""
    genres = tax["genres"]
    events = tax["events"]
    dynamics = tax["dynamics"]

    name_key = "name_ja" if lang == "ja" else "name_en"
    lang_tag = "lang-ja" if lang == "ja" else "lang-en"
    locale = "ja-JP" if lang == "ja" else "en-US"

    g_arr = json.dumps([{"s": g["slug"], "n": g[name_key]} for g in genres], ensure_ascii=False)
    e_arr = json.dumps([{"s": e["slug"], "n": e[name_key]} for e in events], ensure_ascii=False)
    d_arr = json.dumps([{"s": d["slug"], "n": d[name_key]} for d in dynamics], ensure_ascii=False)

    if lang == "ja":
        labels = {
            "title": "記事を探す — 3層フィルター",
            "intro": "各層から1つずつ選んで「検索」→ 該当記事が表示されます。下の表のタグ名クリックでも検索できます。",
            "genre": "ジャンル（Genre）",
            "event": "イベント（Event）",
            "dynamics": "力学 / NOW Pattern",
            "search": "この組み合わせで検索",
            "reset": "リセット",
            "results": "検索結果",
            "no_results": "この組み合わせの記事はまだありません。",
            "select": "1つ以上のタグを選んでください。",
            "loading": "検索中...",
            "period": "期間",
            "all_years": "全期間",
        }
    else:
        labels = {
            "title": "Find Articles — 3-Layer Filter",
            "intro": "Select one from each layer and click Search. You can also click tag names in the table below.",
            "genre": "Genre",
            "event": "Event",
            "dynamics": "Dynamics / NOW Pattern",
            "search": "Search this combination",
            "reset": "Reset",
            "results": "Results",
            "no_results": "No articles found for this combination yet.",
            "select": "Please select at least one tag.",
            "loading": "Searching...",
            "period": "Period",
            "all_years": "All time",
        }

    L = json.dumps(labels, ensure_ascii=False)

    js = f"""<script>
(function() {{
  var CK = "{CONTENT_API_KEY}";
  var LANG = "{lang_tag}";
  var LOCALE = "{locale}";
  var G = {g_arr};
  var E = {e_arr};
  var D = {d_arr};
  var CG = "{CG}", CE = "{CE}", CD = "{CD}";
  var CLR = {{genre:CG, event:CE, dynamics:CD}};
  var L = {L};
  var sel = {{genre:null, event:null, dynamics:null}};

  var contentEl = document.querySelector(".gh-content") || document.querySelector(".post-content") || document.querySelector("article");
  if (!contentEl) return;

  var wrap = document.createElement("div");
  wrap.id = "np-filter";
  wrap.style.cssText = "max-width:900px;margin:0 auto 40px auto;padding:24px;background:#f8f6f0;border-radius:12px;border:1px solid #e0dcd4;";

  var h = '<h2 style="color:#1a1a2e;margin:0 0 8px 0;font-size:1.3em;">'+L.title+'</h2>';
  h += '<p style="color:#666;font-size:0.9em;margin:0 0 20px 0;">'+L.intro+'</p>';

  var layers = [
    {{id:"genre", label:L.genre, color:CG, tags:G}},
    {{id:"event", label:L.event, color:CE, tags:E}},
    {{id:"dynamics", label:L.dynamics, color:CD, tags:D}}
  ];

  layers.forEach(function(ly) {{
    h += '<div style="margin-bottom:14px;">';
    h += '<div style="font-weight:700;color:'+ly.color+';margin-bottom:6px;font-size:0.85em;">● '+ly.label+' ('+ly.tags.length+')</div>';
    h += '<div id="np-'+ly.id+'-chips" style="display:flex;flex-wrap:wrap;gap:5px;">';
    ly.tags.forEach(function(t) {{
      h += '<button data-slug="'+t.s+'" data-layer="'+ly.id+'" style="border:2px solid '+ly.color+';background:#fff;color:'+ly.color+';padding:3px 12px;border-radius:18px;font-size:0.8em;cursor:pointer;font-weight:500;transition:all 0.15s;">'+t.n+'</button>';
    }});
    h += '</div></div>';
  }});

  h += '<div style="margin:18px 0 0 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">';
  h += '<button id="np-btn-search" style="background:#1a1a2e;color:#fff;border:none;padding:9px 22px;border-radius:6px;font-size:0.9em;cursor:pointer;font-weight:600;">'+L.search+'</button>';
  h += '<button id="np-btn-reset" style="background:#ddd;color:#333;border:none;padding:9px 16px;border-radius:6px;font-size:0.9em;cursor:pointer;">'+L.reset+'</button>';
  h += '<div style="margin-left:8px;display:flex;align-items:center;gap:6px;">';
  h += '<span style="font-size:0.8em;color:#888;">'+L.period+':</span>';
  h += '<select id="np-year" style="padding:7px 12px;border:1px solid #ccc;border-radius:6px;font-size:0.85em;background:#fff;cursor:pointer;">';
  h += '<option value="">'+L.all_years+'</option>';
  var curYear = new Date().getFullYear();
  for (var y = curYear; y >= 2026; y--) {{
    h += '<option value="'+y+'">'+y+'</option>';
  }}
  h += '</select></div>';
  h += '</div>';

  h += '<div id="np-results" style="display:none;margin-top:20px;padding-top:16px;border-top:2px solid #e0dcd4;">';
  h += '<h3 id="np-res-title" style="color:#1a1a2e;margin:0 0 12px 0;">'+L.results+'</h3>';
  h += '<div id="np-res-list"></div></div>';

  wrap.innerHTML = h;
  contentEl.insertBefore(wrap, contentEl.firstChild);

  function toggleChip(btn, layer, slug) {{
    var co = CLR[layer];
    var container = document.getElementById("np-"+layer+"-chips");
    if (sel[layer] === slug) {{
      sel[layer] = null;
      btn.style.background = "#fff";
      btn.style.color = co;
    }} else {{
      container.querySelectorAll("button").forEach(function(b) {{
        b.style.background = "#fff"; b.style.color = co;
      }});
      sel[layer] = slug;
      btn.style.background = co;
      btn.style.color = "#fff";
    }}
  }}

  document.querySelectorAll("#np-filter button[data-slug]").forEach(function(btn) {{
    btn.addEventListener("click", function() {{
      toggleChip(btn, btn.dataset.layer, btn.dataset.slug);
    }});
  }});

  function doSearch() {{
    var slugs = [LANG];
    if (sel.genre) slugs.push(sel.genre);
    if (sel.event) slugs.push(sel.event);
    if (sel.dynamics) slugs.push(sel.dynamics);
    if (slugs.length < 2) {{ alert(L.select); return; }}

    var resDiv = document.getElementById("np-results");
    var resList = document.getElementById("np-res-list");
    var resTitle = document.getElementById("np-res-title");
    resDiv.style.display = "block";
    resList.innerHTML = '<p style="color:#888;">'+L.loading+'</p>';

    var f = slugs.map(function(s){{ return "tag:"+s; }}).join("%2B");
    var yearVal = document.getElementById("np-year").value;
    if (yearVal) {{
      f += "%2Bpublished_at:>='" + yearVal + "-01-01'%2Bpublished_at:<'" + (parseInt(yearVal)+1) + "-01-01'";
    }}
    fetch("/ghost/api/content/posts/?key="+CK+"&filter="+f+"&limit=30&fields=title,url,excerpt,published_at")
      .then(function(r){{ return r.json(); }})
      .then(function(data) {{
        var posts = data.posts || [];
        resTitle.textContent = L.results + " (" + posts.length + ")";
        if (!posts.length) {{
          resList.innerHTML = '<p style="color:#888;font-style:italic;">'+L.no_results+'</p>';
          return;
        }}
        var out = "";
        posts.forEach(function(p) {{
          var dt = new Date(p.published_at).toLocaleDateString(LOCALE, {{year:"numeric",month:"long",day:"numeric"}});
          out += '<div style="padding:12px 0;border-bottom:1px solid #e8e8e8;">';
          out += '<a href="'+p.url+'" style="color:#1a1a2e;font-weight:600;font-size:1em;text-decoration:none;">'+p.title+'</a>';
          out += '<div style="color:#888;font-size:0.8em;margin-top:3px;">'+dt+'</div>';
          if (p.excerpt) out += '<div style="color:#555;font-size:0.85em;margin-top:5px;line-height:1.5;">'+p.excerpt.substring(0,120)+'...</div>';
          out += '</div>';
        }});
        resList.innerHTML = out;
      }})
      .catch(function(e){{ resList.innerHTML = '<p style="color:red;">Error: '+e.message+'</p>'; }});
  }}

  document.getElementById("np-btn-search").addEventListener("click", doSearch);

  document.getElementById("np-btn-reset").addEventListener("click", function() {{
    sel = {{genre:null, event:null, dynamics:null}};
    ["genre","event","dynamics"].forEach(function(ly) {{
      var co = CLR[ly];
      var c = document.getElementById("np-"+ly+"-chips");
      if(c) c.querySelectorAll("button").forEach(function(b){{ b.style.background="#fff"; b.style.color=co; }});
    }});
    document.getElementById("np-year").value = "";
    document.getElementById("np-results").style.display = "none";
  }});
}})();
</script>"""
    return js


# =============================================================================
# ページHTML生成（白背景 + フィルターと色統一）
# =============================================================================
def build_taxonomy_ja(tax):
    """日本語タクソノミーページHTML — 白背景、フィルターと色統一"""
    genres = tax["genres"]
    events = tax["events"]
    dynamics = tax["dynamics"]

    cats = {"支配": [], "対立": [], "崩壊": [], "転換": []}
    for d in dynamics:
        cat = d.get("category", "")
        if cat in cats:
            cats[cat].append(d)

    html = f"""
<div style="max-width: 900px; margin: 0 auto; padding: 20px; font-family: 'Noto Sans JP', sans-serif; color: #1a1a2e;">

<h2 style="color: #1a1a2e; border-bottom: 2px solid {CG}; padding-bottom: 8px;">Nowpattern 3層タクソノミー</h2>
<p style="color: #555;">全ての記事を <strong>ジャンル({len(genres)})</strong> × <strong>イベント({len(events)})</strong> × <strong>力学({len(dynamics)})</strong> の3層で分類します。</p>
<p style="color: #888; font-size: 0.9em;"><a href="/taxonomy-en/" style="color: {CG};">English Version</a> | <a href="/taxonomy-guide-ja/" style="color: {CG};">使い方ガイド</a></p>

<hr style="border-color: #e0dcd4;">

<h3 style="color: {CG};">第1層: ジャンル — 何についての記事か（{len(genres)}個）</h3>
<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
<tr style="background: #f0f4ff;"><th style="padding: 8px; text-align: left; color: {CG}; font-size: 0.85em;">タグ</th><th style="padding: 8px; text-align: left; color: {CG}; font-size: 0.85em;">説明</th></tr>
"""
    for g in genres:
        html += f'<tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;"><a href="/tag/{g["slug"]}/?lang=ja" style="color:{CG};text-decoration:none;font-weight:500;">#{g["name_ja"]}</a></td><td style="padding: 8px; color: #555; font-size: 0.9em;">{g["description_ja"]}</td></tr>\n'

    html += f"""</table>

<hr style="border-color: #e0dcd4;">

<h3 style="color: {CE};">第2層: イベント — 何が起きたか（{len(events)}個）</h3>
<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
<tr style="background: #f0fdf4;"><th style="padding: 8px; text-align: left; color: {CE}; font-size: 0.85em;">タグ</th><th style="padding: 8px; text-align: left; color: {CE}; font-size: 0.85em;">説明</th></tr>
"""
    for e in events:
        html += f'<tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;"><a href="/tag/{e["slug"]}/?lang=ja" style="color:{CE};text-decoration:none;font-weight:500;">#{e["name_ja"]}</a></td><td style="padding: 8px; color: #555; font-size: 0.9em;">{e["description_ja"]}</td></tr>\n'

    html += f"""</table>

<hr style="border-color: #e0dcd4;">

<h3 style="color: {CD};">第3層: 力学 / NOW Pattern — なぜそうなるのか（{len(dynamics)}個 = 4×4）</h3>
<p style="color: #555;">表面のニュースの裏にある<strong>構造的パターン</strong>。4つのファミリー × 4つの力学。</p>
"""

    cat_labels = {"支配": "誰がルールを書くのか", "対立": "なぜ衝突が止まらないのか", "崩壊": "なぜ制度が機能しなくなるのか", "転換": "なぜ局面が変わるのか"}
    for cat_name, cat_dynamics in cats.items():
        if not cat_dynamics:
            continue
        cat_color = CAT_COLORS.get(cat_name, CD)
        html += f"""
<h4 style="color: {cat_color}; margin-top: 24px;">■ {cat_name} — {cat_labels.get(cat_name, "")}</h4>
<table style="width: 100%; border-collapse: collapse; margin: 8px 0 20px 0;">
<tr style="background: #fff5f9;"><th style="padding: 8px; text-align: left; color: {CD}; font-size: 0.85em;">パターン</th><th style="padding: 8px; text-align: left; color: {CD}; font-size: 0.85em;">定義</th></tr>
"""
        for d in cat_dynamics:
            html += f'<tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;"><a href="/tag/{d["slug"]}/?lang=ja" style="color:{CD};text-decoration:none;font-weight:500;">#{d["name_ja"]}</a></td><td style="padding: 8px; color: #555; font-size: 0.9em;">{d["description_ja"]}</td></tr>\n'
        html += "</table>\n"

    html += f"""
<hr style="border-color: #e0dcd4;">
<p style="color: #888; font-size: 0.85em;"><a href="/taxonomy-guide-ja/" style="color: {CG};">3層ガイド（使い方の解説）</a> | <a href="/taxonomy-en/" style="color: {CG};">English Version</a></p>
</div>
"""
    return html


def build_taxonomy_en(tax):
    """英語タクソノミーページHTML — 白背景、フィルターと色統一"""
    genres = tax["genres"]
    events = tax["events"]
    dynamics = tax["dynamics"]

    cats = {"支配": [], "対立": [], "崩壊": [], "転換": []}
    for d in dynamics:
        cat = d.get("category", "")
        if cat in cats:
            cats[cat].append(d)

    cat_en = {"支配": "Dominance", "対立": "Conflict", "崩壊": "Collapse", "転換": "Transition"}
    cat_labels_en = {"支配": "Who writes the rules?", "対立": "Why can't conflicts stop?", "崩壊": "Why do institutions fail?", "転換": "Why do paradigms shift?"}

    html = f"""
<div style="max-width: 900px; margin: 0 auto; padding: 20px; font-family: sans-serif; color: #1a1a2e;">

<h2 style="color: #1a1a2e; border-bottom: 2px solid {CG}; padding-bottom: 8px;">Nowpattern 3-Layer Taxonomy</h2>
<p style="color: #555;">Every article is classified by <strong>Genre({len(genres)})</strong> × <strong>Event({len(events)})</strong> × <strong>Dynamics({len(dynamics)})</strong>.</p>
<p style="color: #888; font-size: 0.9em;"><a href="/taxonomy-ja/" style="color: {CG};">日本語版</a> | <a href="/taxonomy-guide-en/" style="color: {CG};">How to Use Guide</a></p>

<hr style="border-color: #e0dcd4;">

<h3 style="color: {CG};">Layer 1: Genre — What is this about? ({len(genres)})</h3>
<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
<tr style="background: #f0f4ff;"><th style="padding: 8px; text-align: left; color: {CG}; font-size: 0.85em;">Tag</th><th style="padding: 8px; text-align: left; color: {CG}; font-size: 0.85em;">Description</th></tr>
"""
    for g in genres:
        html += f'<tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;"><a href="/tag/{g["slug"]}/?lang=en" style="color:{CG};text-decoration:none;font-weight:500;">#{g["name_en"]}</a></td><td style="padding: 8px; color: #555; font-size: 0.9em;">{g["description_en"]}</td></tr>\n'

    html += f"""</table>

<hr style="border-color: #e0dcd4;">

<h3 style="color: {CE};">Layer 2: Event — What happened? ({len(events)})</h3>
<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
<tr style="background: #f0fdf4;"><th style="padding: 8px; text-align: left; color: {CE}; font-size: 0.85em;">Tag</th><th style="padding: 8px; text-align: left; color: {CE}; font-size: 0.85em;">Description</th></tr>
"""
    for e in events:
        html += f'<tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;"><a href="/tag/{e["slug"]}/?lang=en" style="color:{CE};text-decoration:none;font-weight:500;">#{e["name_en"]}</a></td><td style="padding: 8px; color: #555; font-size: 0.9em;">{e["description_en"]}</td></tr>\n'

    html += f"""</table>

<hr style="border-color: #e0dcd4;">

<h3 style="color: {CD};">Layer 3: Dynamics / NOW Pattern — Why does this happen? ({len(dynamics)} = 4×4)</h3>
<p style="color: #555;">The <strong>structural patterns</strong> beneath the surface news. 4 families × 4 dynamics each.</p>
"""

    for cat_ja, cat_dynamics in cats.items():
        if not cat_dynamics:
            continue
        cat_name = cat_en.get(cat_ja, cat_ja)
        cat_label = cat_labels_en.get(cat_ja, "")
        cat_color = CAT_COLORS.get(cat_ja, CD)
        html += f"""
<h4 style="color: {cat_color}; margin-top: 24px;">■ {cat_name} — {cat_label}</h4>
<table style="width: 100%; border-collapse: collapse; margin: 8px 0 20px 0;">
<tr style="background: #fff5f9;"><th style="padding: 8px; text-align: left; color: {CD}; font-size: 0.85em;">Pattern</th><th style="padding: 8px; text-align: left; color: {CD}; font-size: 0.85em;">Definition</th></tr>
"""
        for d in cat_dynamics:
            html += f'<tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;"><a href="/tag/{d["slug"]}/?lang=en" style="color:{CD};text-decoration:none;font-weight:500;">#{d["name_en"]}</a></td><td style="padding: 8px; color: #555; font-size: 0.9em;">{d["description_en"]}</td></tr>\n'
        html += "</table>\n"

    html += f"""
<hr style="border-color: #e0dcd4;">
<p style="color: #888; font-size: 0.85em;"><a href="/taxonomy-guide-en/" style="color: {CG};">3-Layer Guide</a> | <a href="/taxonomy-ja/" style="color: {CG};">日本語版</a></p>
</div>
"""
    return html


def build_guide_ja(tax):
    """日本語ガイドページHTML — 白背景"""
    dynamics = tax["dynamics"]
    cats = {"支配": [], "対立": [], "崩壊": [], "転換": []}
    for d in dynamics:
        cat = d.get("category", "")
        if cat in cats:
            cats[cat].append(d)

    html = f"""
<div style="max-width: 900px; margin: 0 auto; padding: 20px; font-family: 'Noto Sans JP', sans-serif; color: #1a1a2e;">

<h2 style="color: #1a1a2e; border-bottom: 2px solid {CG}; padding-bottom: 8px;">なぜNowpatternはニュースを3層に分けるのか</h2>

<p style="color: #555; line-height: 1.8;">ニュースサイトはジャンル（「政治」「経済」）だけで分類します。<br>
しかし本当に知りたいのは <strong>「なぜそれが起きたのか」</strong> と <strong>「次に何が起きるのか」</strong> です。</p>

<p style="color: #555; line-height: 1.8;">Nowpatternは3つの問いで記事を分類します:</p>

<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
<tr style="background: #f8f6f0;"><th style="padding: 10px; color: #1a1a2e;">層</th><th style="padding: 10px; color: #1a1a2e;">問い</th><th style="padding: 10px; color: #1a1a2e;">例</th></tr>
<tr style="border-bottom: 1px solid #eee;"><td style="padding: 10px; color: {CG}; font-weight: 600;">ジャンル</td><td style="padding: 10px; color: #555;">何についての記事？</td><td style="padding: 10px; color: #555;">地政学、暗号資産、テクノロジー</td></tr>
<tr style="border-bottom: 1px solid #eee;"><td style="padding: 10px; color: {CE}; font-weight: 600;">イベント</td><td style="padding: 10px; color: #555;">何が起きた？</td><td style="padding: 10px; color: #555;">軍事衝突、規制・法改正、市場ショック</td></tr>
<tr style="border-bottom: 1px solid #eee;"><td style="padding: 10px; color: {CD}; font-weight: 600;">力学</td><td style="padding: 10px; color: #555;">なぜそうなる？</td><td style="padding: 10px; color: #555;">プラットフォーム支配、対立の螺旋、危機便乗</td></tr>
</table>

<h3 style="color: {CD}; margin-top: 32px;">力学（NOW Pattern）{len(dynamics)}パターン — 4×4構造</h3>
<p style="color: #555;">ニュースの裏にある「構造的パターン」を4つのファミリーに分類しています。</p>
"""

    cat_examples = {
        "支配": "「規制の捕獲」は暗号資産でも農業でも医薬品でも同じパターンで起きます。",
        "対立": "「対立の螺旋」はロシア-ウクライナ紛争と米中貿易戦争で同じパターンです。",
        "崩壊": "「制度の劣化」はFDAの承認プロセスでもNATOの意思決定でも同じパターンです。",
        "転換": "「危機便乗」はコロナ禍の規制緩和でもトランプ政権の排ガス規制撤廃でも同じパターンです。",
    }
    cat_labels = {"支配": "誰がルールを書くのか", "対立": "なぜ衝突が止まらないのか", "崩壊": "なぜ制度が機能しなくなるのか", "転換": "なぜ局面が変わるのか"}

    for cat_name, cat_dynamics in cats.items():
        if not cat_dynamics:
            continue
        cat_color = CAT_COLORS.get(cat_name, CD)
        html += f"""
<h4 style="color: {cat_color}; margin-top: 24px;">■ {cat_name} — {cat_labels.get(cat_name, "")}</h4>
<ul style="list-style: none; padding: 0;">
"""
        for d in cat_dynamics:
            html += f'<li style="margin: 8px 0; padding: 10px; background: #f8f6f0; border-left: 3px solid {cat_color}; border-radius: 4px;"><strong style="color: {CD};">{d["name_ja"]}</strong><span style="color: #888;"> ({d["name_en"]})</span><br><span style="color: #555; font-size: 0.9em;">{d["description_ja"]}</span></li>\n'
        html += "</ul>\n"
        html += f'<p style="color: #888; font-size: 0.85em; font-style: italic;">{cat_examples.get(cat_name, "")}</p>\n'

    html += f"""
<h3 style="color: {CG}; margin-top: 32px;">読者の活用方法</h3>
<ul style="color: #555; line-height: 1.8;">
<li><strong>ジャンル検索</strong>: 「暗号資産」タグで暗号資産ニュースだけを表示</li>
<li><strong>構造理解</strong>: 「規制の捕獲」タグでジャンルを横断して同じパターンの記事を読む</li>
<li><strong>比較分析</strong>: 同じ力学タグの異なるジャンル記事を並べて、パターンの普遍性を確認</li>
</ul>

<p style="color: #888; font-size: 0.85em;"><a href="/taxonomy-ja/" style="color: {CG};">全タグ一覧</a> | <a href="/taxonomy-guide-en/" style="color: {CG};">English Version</a></p>
</div>
"""
    return html


def build_guide_en(tax):
    """英語ガイドページHTML — 白背景"""
    dynamics = tax["dynamics"]
    cats = {"支配": [], "対立": [], "崩壊": [], "転換": []}
    for d in dynamics:
        cat = d.get("category", "")
        if cat in cats:
            cats[cat].append(d)

    cat_en = {"支配": "Dominance", "対立": "Conflict", "崩壊": "Collapse", "転換": "Transition"}
    cat_labels_en = {"支配": "Who writes the rules?", "対立": "Why can't conflicts stop?", "崩壊": "Why do institutions fail?", "転換": "Why do paradigms shift?"}

    html = f"""
<div style="max-width: 900px; margin: 0 auto; padding: 20px; font-family: sans-serif; color: #1a1a2e;">

<h2 style="color: #1a1a2e; border-bottom: 2px solid {CG}; padding-bottom: 8px;">Why Nowpattern Uses a 3-Layer Tag System</h2>

<p style="color: #555; line-height: 1.8;">Most news sites classify articles by topic alone ("Politics", "Economy").<br>
But what you really want to know is <strong>why something happened</strong> and <strong>what comes next</strong>.</p>

<p style="color: #555; line-height: 1.8;">Nowpattern classifies every article with three questions:</p>

<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
<tr style="background: #f8f6f0;"><th style="padding: 10px; color: #1a1a2e;">Layer</th><th style="padding: 10px; color: #1a1a2e;">Question</th><th style="padding: 10px; color: #1a1a2e;">Example</th></tr>
<tr style="border-bottom: 1px solid #eee;"><td style="padding: 10px; color: {CG}; font-weight: 600;">Genre</td><td style="padding: 10px; color: #555;">What is this about?</td><td style="padding: 10px; color: #555;">Geopolitics, Crypto, Technology</td></tr>
<tr style="border-bottom: 1px solid #eee;"><td style="padding: 10px; color: {CE}; font-weight: 600;">Event</td><td style="padding: 10px; color: #555;">What happened?</td><td style="padding: 10px; color: #555;">Military Conflict, Regulation, Market Shock</td></tr>
<tr style="border-bottom: 1px solid #eee;"><td style="padding: 10px; color: {CD}; font-weight: 600;">Dynamics</td><td style="padding: 10px; color: #555;">Why does this happen?</td><td style="padding: 10px; color: #555;">Platform Power, Escalation Spiral, Shock Doctrine</td></tr>
</table>

<h3 style="color: {CD}; margin-top: 32px;">Dynamics (NOW Pattern) — {len(dynamics)} Patterns in 4×4 Structure</h3>
<p style="color: #555;">The structural patterns beneath the surface news, organized into 4 families.</p>
"""

    cat_examples_en = {
        "支配": "Regulatory Capture looks the same whether it's DeFi lobbying the SEC or pesticide manufacturers influencing EPA standards.",
        "対立": "Escalation Spiral appears in Russia-Ukraine just as it does in US-China trade wars.",
        "崩壊": "Institutional Decay manifests equally in FDA approval processes and NATO decision-making.",
        "転換": "Shock Doctrine operates during COVID deregulation just as during Trump's emission rollbacks.",
    }

    for cat_ja, cat_dynamics in cats.items():
        if not cat_dynamics:
            continue
        cat_name = cat_en.get(cat_ja, cat_ja)
        cat_label = cat_labels_en.get(cat_ja, "")
        cat_color = CAT_COLORS.get(cat_ja, CD)
        html += f"""
<h4 style="color: {cat_color}; margin-top: 24px;">■ {cat_name} — {cat_label}</h4>
<ul style="list-style: none; padding: 0;">
"""
        for d in cat_dynamics:
            html += f'<li style="margin: 8px 0; padding: 10px; background: #f8f6f0; border-left: 3px solid {cat_color}; border-radius: 4px;"><strong style="color: {CD};">{d["name_en"]}</strong><br><span style="color: #555; font-size: 0.9em;">{d["description_en"]}</span></li>\n'
        html += "</ul>\n"
        html += f'<p style="color: #888; font-size: 0.85em; font-style: italic;">{cat_examples_en.get(cat_ja, "")}</p>\n'

    html += f"""
<h3 style="color: {CG}; margin-top: 32px;">How to Use Tags</h3>
<ul style="color: #555; line-height: 1.8;">
<li><strong>Genre search</strong>: Click "Crypto & Web3" to see only crypto articles</li>
<li><strong>Pattern search</strong>: Click "Regulatory Capture" to see the same pattern across different genres</li>
<li><strong>Cross-domain comparison</strong>: Compare articles with the same dynamics tag across different genres</li>
</ul>

<p style="color: #888; font-size: 0.85em;"><a href="/taxonomy-en/" style="color: {CG};">Full Tag List</a> | <a href="/taxonomy-guide-ja/" style="color: {CG};">日本語版</a></p>
</div>
"""
    return html


# =============================================================================
# Ghost API 更新
# =============================================================================
def update_ghost_page(page_id, html, updated_at, codeinjection_foot=None, dry_run=False):
    """Ghost Admin APIでページを更新（lexical HTML card + code injection）"""
    import urllib3
    urllib3.disable_warnings()
    import requests

    if dry_run:
        print(f"  [DRY-RUN] Would update page {page_id} (content: {len(html)} chars" +
              (f", footer JS: {len(codeinjection_foot)} chars" if codeinjection_foot else "") + ")")
        return True

    token = make_jwt(GHOST_API_KEY)
    lexical_doc = {
        "root": {
            "children": [{"type": "html", "version": 1, "html": html}],
            "direction": None, "format": "", "indent": 0,
            "type": "root", "version": 1,
        }
    }

    url = f"{GHOST_URL}/ghost/api/admin/pages/{page_id}/"
    headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}
    page_data = {"lexical": json.dumps(lexical_doc), "updated_at": updated_at}

    if codeinjection_foot is not None:
        page_data["codeinjection_foot"] = codeinjection_foot

    body = {"pages": [page_data]}

    resp = requests.put(url, json=body, headers=headers, verify=False, timeout=30)
    if resp.status_code == 200:
        new_updated = resp.json()["pages"][0]["updated_at"]
        print(f"  OK: Page updated (content: {len(html)} chars" +
              (f", footer JS: {len(codeinjection_foot)} chars" if codeinjection_foot else "") + ")")
        return new_updated
    else:
        print(f"  ERROR {resp.status_code}: {resp.text[:300]}")
        return False


def build_site_js(tax):
    """Site-level JS: language filter + tag page title/description localization"""
    # Build slug → {ja, en, dj, de} mapping from taxonomy
    tag_map = {}
    for g in tax["genres"]:
        tag_map[g["slug"]] = {"ja": g["name_ja"], "en": g["name_en"],
                              "dj": g["description_ja"], "de": g["description_en"]}
    for e in tax["events"]:
        tag_map[e["slug"]] = {"ja": e["name_ja"], "en": e["name_en"],
                              "dj": e["description_ja"], "de": e["description_en"]}
    for d in tax["dynamics"]:
        tag_map[d["slug"]] = {"ja": d["name_ja"], "en": d["name_en"],
                              "dj": d["description_ja"], "de": d["description_en"]}
    map_json = json.dumps(tag_map, ensure_ascii=False, separators=(",", ":"))

    return f"""<script>
(function(){{
  var path=window.location.pathname;
  var params=new URLSearchParams(window.location.search);
  var lang=params.get("lang");
  var isHome=(path==="/")||/^\\/page\\/\\d+\\/$/.test(path);
  var isEn=(path==="/en/")||/^\\/en\\/page\\/\\d+\\/$/.test(path);
  var isTag=/^\\/tag\\//.test(path);
  var hasLang=isTag&&lang;
  if(!isHome&&!isEn&&!hasLang) return;
  var articles=document.querySelectorAll("article.gh-card");
  articles.forEach(function(a){{
    var lk=a.querySelector("a[href]");
    if(!lk) return;
    var hr=lk.getAttribute("href");
    var en=hr.indexOf("/en/")===0;
    if(isHome&&en) a.style.display="none";
    if(isEn&&!en) a.style.display="none";
    if(hasLang&&lang==="ja"&&en) a.style.display="none";
    if(hasLang&&lang==="en"&&!en) a.style.display="none";
  }});
  if(hasLang){{
    var TM={map_json};
    var m=path.match(/^\\/tag\\/([^\\/]+)/);
    if(m&&TM[m[1]]){{
      var t=TM[m[1]];
      var nm=(lang==="ja")?t.ja:t.en;
      var ds=(lang==="ja")?t.dj:t.de;
      var h1=document.querySelector("h1.gh-article-title");
      if(h1) h1.textContent=nm;
      var pd=document.querySelector("p.gh-article-excerpt");
      if(pd) pd.textContent=ds;
    }}
  }}
}})();
</script>"""


def update_site_codeinjection(js, dry_run=False):
    """Update Ghost site-level codeinjection_foot via SQLite (API returns 501)"""
    import subprocess
    import glob as globmod

    if dry_run:
        print(f"  [DRY-RUN] Would update site codeinjection_foot ({len(js)} chars)")
        return True

    # Find Ghost DB
    db_candidates = [
        "/var/www/nowpattern/content/data/ghost-local.db",
        "/var/www/nowpattern/content/data/ghost.db",
    ]
    db_path = None
    for p in db_candidates:
        if os.path.exists(p):
            db_path = p
            break
    if not db_path:
        found = globmod.glob("/var/www/nowpattern/content/data/*.db")
        if found:
            db_path = found[0]
    if not db_path:
        print("  ERROR: Ghost SQLite DB not found")
        return False

    print(f"  DB: {db_path}")
    escaped = js.replace("'", "''")
    sql = f"UPDATE settings SET value = '{escaped}' WHERE key = 'codeinjection_foot';"

    result = subprocess.run(
        ["sqlite3", db_path, sql],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr}")
        return False

    print(f"  OK: Site codeinjection_foot updated ({len(js)} chars)")

    # Restart Ghost to pick up DB changes
    print("  Restarting Ghost...")
    restart = subprocess.run(
        ["systemctl", "restart", "ghost-nowpattern"],
        capture_output=True, text=True, timeout=30
    )
    if restart.returncode == 0:
        print("  OK: Ghost restarted (wait ~5s before API calls)")
    else:
        print(f"  WARN: Ghost restart issue: {restart.stderr}")

    return True


def main():
    import urllib3
    urllib3.disable_warnings()
    import requests

    dry_run = "--dry-run" in sys.argv
    skip_site_js = "--skip-site-js" in sys.argv

    tax = load_taxonomy()
    print(f"Taxonomy v{tax['version']}: {len(tax['genres'])} genres, {len(tax['events'])} events, {len(tax['dynamics'])} dynamics")

    # --- Step 1: Update site-level JS (before pages, since it restarts Ghost) ---
    if not skip_site_js:
        print("\n--- Site-level codeinjection_foot ---")
        site_js = build_site_js(tax)
        update_site_codeinjection(site_js, dry_run=dry_run)
        if not dry_run:
            import time as _time
            print("  Waiting 8s for Ghost to start...")
            _time.sleep(8)

    # --- Step 2: Build filter JS for JA and EN ---
    filter_js_ja = build_filter_js(tax, lang="ja")
    filter_js_en = build_filter_js(tax, lang="en")
    print(f"Filter JS: JA={len(filter_js_ja)} chars, EN={len(filter_js_en)} chars")

    # Get page IDs and updated_at
    token = make_jwt(GHOST_API_KEY)
    r = requests.get(
        f"{GHOST_URL}/ghost/api/admin/pages/?limit=all&fields=id,slug,updated_at",
        headers={"Authorization": f"Ghost {token}"},
        verify=False, timeout=30
    )
    pages = {p["slug"]: p for p in r.json().get("pages", [])}

    # Build and update each page
    page_configs = {
        "taxonomy-ja": ("Nowpattern タクソノミー", build_taxonomy_ja, filter_js_ja),
        "taxonomy-en": ("Nowpattern Taxonomy", build_taxonomy_en, filter_js_en),
        "taxonomy-guide-ja": ("3層ガイド（日本語）", build_guide_ja, None),
        "taxonomy-guide-en": ("3-Layer Guide (English)", build_guide_en, None),
    }

    for slug, (label, builder, filter_js) in page_configs.items():
        print(f"\n--- {label} ({slug}) ---")
        if slug not in pages:
            print(f"  SKIP: Page '{slug}' not found in Ghost")
            continue

        page = pages[slug]
        html = builder(tax)
        result = update_ghost_page(
            page["id"], html, page["updated_at"],
            codeinjection_foot=filter_js, dry_run=dry_run
        )
        if result:
            print(f"  ✅ {label} updated")

    print("\n=== Done ===")


if __name__ == "__main__":
    if not GHOST_API_KEY:
        print("ERROR: Ghost API key not found")
        sys.exit(1)
    main()
