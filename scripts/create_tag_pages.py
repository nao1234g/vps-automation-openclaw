#!/usr/bin/env python3
"""Create Nowpattern taxonomy pages (JA + EN).
- Filter UI is 100% JS-generated (Ghost strips HTML divs with IDs)
- All JS goes into codeinjection_foot (Ghost strips <script> from HTML)
- Language separation: JA shows only JA articles, EN only EN
- Tag table links trigger the JS filter
"""

import os, sys, json, jwt, datetime, requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
GHOST_URL = "https://nowpattern.com"
CONTENT_KEY = "75626da2b27b59aa68e2bcdc6d"
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

TAXONOMY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nowpattern_taxonomy.json")
with open(TAXONOMY_PATH, encoding="utf-8") as f:
    TAX = json.load(f)

C_GENRE = "#2563eb"
C_EVENT = "#16a34a"
C_DYNAMICS = "#FF1A75"
_LINK_COLORS = {"genre": C_GENRE, "event": C_EVENT, "dynamics": C_DYNAMICS}


def _tag_link(slug, label, cls):
    c = _LINK_COLORS.get(cls, "#333")
    return (f'<a href="javascript:void(0)" data-np-slug="{slug}" data-np-layer="{cls}" '
            f'style="color:{c};font-weight:600;text-decoration:none;cursor:pointer;">#{label}</a>')


def _build_filter_js(lang):
    """Build complete JS that creates filter UI + handles interactions."""
    is_ja = lang == "ja"
    lang_tag = "日本語" if is_ja else "English"
    locale = "ja-JP" if is_ja else "en-US"

    genres_js = json.dumps([{"s": g["slug"], "n": g["name_ja"] if is_ja else g["name_en"]} for g in TAX["genres"]], ensure_ascii=False)
    events_js = json.dumps([{"s": e["slug"], "n": e["name_ja"] if is_ja else e["name_en"]} for e in TAX["events"]], ensure_ascii=False)
    dynamics_js = json.dumps([{"s": d["slug"], "n": d["name_ja"] if is_ja else d["name_en"]} for d in TAX["dynamics"]], ensure_ascii=False)

    # Labels
    if is_ja:
        L = {
            "title": "記事を探す — 3層フィルター",
            "intro": "各層から1つずつ選んで「検索」→ 該当記事が表示されます。下の表のタグ名クリックでも検索できます。",
            "genre": "● ジャンル（Genre）",
            "event": "● イベント（Event）",
            "dynamics": "● 力学 / NOW Pattern",
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
        L = {
            "title": "Find Articles — 3-Layer Filter",
            "intro": "Select one tag from each layer, then click Find. You can also click any tag in the tables below.",
            "genre": "● Genre",
            "event": "● Event",
            "dynamics": "● Dynamics / NOW Pattern",
            "search": "Find Articles",
            "reset": "Reset",
            "results": "Results",
            "no_results": "No articles match this combination yet.",
            "select": "Select at least one tag.",
            "loading": "Searching...",
            "period": "Period",
            "all_years": "All time",
        }

    labels_js = json.dumps(L, ensure_ascii=False)

    return f"""<script>
(function() {{
  var CK = "{CONTENT_KEY}";
  var LANG = "{lang_tag}";
  var LOCALE = "{locale}";
  var G = {genres_js};
  var E = {events_js};
  var D = {dynamics_js};
  var CG = "{C_GENRE}", CE = "{C_EVENT}", CD = "{C_DYNAMICS}";
  var CLR = {{genre:CG, event:CE, dynamics:CD}};
  var L = {labels_js};
  var sel = {{genre:null, event:null, dynamics:null}};

  // Find the article content area to prepend filter
  var contentEl = document.querySelector(".gh-content") || document.querySelector(".post-content") || document.querySelector("article");
  if (!contentEl) return;

  // Create filter container
  var wrap = document.createElement("div");
  wrap.id = "np-filter";
  wrap.style.cssText = "max-width:900px;margin:0 auto 40px auto;padding:24px;background:#f8f6f0;border-radius:12px;border:1px solid #e0dcd4;";

  var h = '<h2 style="color:#1a1a2e;margin:0 0 8px 0;font-size:1.3em;">'+L.title+'</h2>';
  h += '<p style="color:#666;font-size:0.9em;margin:0 0 20px 0;">'+L.intro+'</p>';

  // 3 layers
  var layers = [
    {{id:"genre", label:L.genre, color:CG, tags:G}},
    {{id:"event", label:L.event, color:CE, tags:E}},
    {{id:"dynamics", label:L.dynamics, color:CD, tags:D}}
  ];

  layers.forEach(function(ly) {{
    h += '<div style="margin-bottom:14px;">';
    h += '<div style="font-weight:700;color:'+ly.color+';margin-bottom:6px;font-size:0.85em;">'+ly.label+' ('+ly.tags.length+')</div>';
    h += '<div id="np-'+ly.id+'-chips" style="display:flex;flex-wrap:wrap;gap:5px;">';
    ly.tags.forEach(function(t) {{
      h += '<button data-slug="'+t.s+'" data-layer="'+ly.id+'" style="border:2px solid '+ly.color+';background:#fff;color:'+ly.color+';padding:3px 12px;border-radius:18px;font-size:0.8em;cursor:pointer;font-weight:500;transition:all 0.15s;">'+t.n+'</button>';
    }});
    h += '</div></div>';
  }});

  h += '<div style="margin:18px 0 0 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">';
  h += '<button id="np-btn-search" style="background:#1a1a2e;color:#fff;border:none;padding:9px 22px;border-radius:6px;font-size:0.9em;cursor:pointer;font-weight:600;">'+L.search+'</button>';
  h += '<button id="np-btn-reset" style="background:#ddd;color:#333;border:none;padding:9px 16px;border-radius:6px;font-size:0.9em;cursor:pointer;">'+L.reset+'</button>';
  // Year dropdown
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

  // Chip click handlers
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

  // Search
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

  // Tag table links: click → select that chip + auto-search
  function selectBySlug(slug, layer) {{
    sel[layer] = slug;
    var c = document.getElementById("np-"+layer+"-chips");
    if(!c) return;
    var co = CLR[layer];
    c.querySelectorAll("button").forEach(function(b) {{
      if(b.dataset.slug === slug) {{ b.style.background=co; b.style.color="#fff"; }}
      else {{ b.style.background="#fff"; b.style.color=co; }}
    }});
  }}

  document.querySelectorAll("[data-np-slug]").forEach(function(a) {{
    if (a.closest("#np-filter")) return; // skip chips themselves
    a.addEventListener("click", function(e) {{
      e.preventDefault();
      selectBySlug(a.dataset.npSlug, a.dataset.npLayer);
      doSearch();
      document.getElementById("np-filter").scrollIntoView({{behavior:"smooth"}});
    }});
  }});

}})();
</script>"""


def _build_css():
    return """<style>
.np-tax { max-width: 900px; margin: 0 auto; }
.np-tax h2 { padding-bottom: 8px; margin-top: 2.5em; font-size: 1.4em; }
.np-tax h2.genre { color: {G}; border-bottom: 3px solid {G}; }
.np-tax h2.event { color: {E}; border-bottom: 3px solid {E}; }
.np-tax h2.dynamics { color: {D}; border-bottom: 3px solid {D}; }
.np-tax table { width: 100%; border-collapse: collapse; margin: 16px 0 32px 0; }
.np-tax th.genre { background: {G}; color: #fff; padding: 10px 14px; text-align: left; font-size: 0.9em; }
.np-tax th.event { background: {E}; color: #fff; padding: 10px 14px; text-align: left; font-size: 0.9em; }
.np-tax th.dynamics { background: {D}; color: #fff; padding: 10px 14px; text-align: left; font-size: 0.9em; }
.np-tax th.guide { background: #1a1a2e; color: #fff; padding: 10px 14px; text-align: left; font-size: 0.9em; }
.np-tax td { padding: 10px 14px; border-bottom: 1px solid #e8e8e8; vertical-align: top; }
.np-tax tr:hover { background: #f5f5fa; }
.np-tax .intro { padding: 12px 16px; margin: 12px 0 20px 0; border-radius: 4px; font-size: 0.95em; }
.np-tax .intro.genre { background: #eef4ff; border-left: 4px solid {G}; }
.np-tax .intro.event { background: #eefbf3; border-left: 4px solid {E}; }
.np-tax .intro.dynamics { background: #fff0f5; border-left: 4px solid {D}; }
.np-tax .badge { display: inline-block; border-radius: 12px; padding: 2px 10px; font-size: 0.85em; color: #fff; margin-left: 8px; }
.np-tax .badge.genre { background: {G}; }
.np-tax .badge.event { background: {E}; }
.np-tax .badge.dynamics { background: {D}; }
</style>
""".replace("{G}", C_GENRE).replace("{E}", C_EVENT).replace("{D}", C_DYNAMICS)


def build_page_html(lang):
    is_ja = lang == "ja"
    other_lang = "en" if is_ja else "ja"
    other_label = "→ English Version" if is_ja else "→ 日本語版"
    guide_url = "/taxonomy-guide-ja/" if is_ja else "/taxonomy-guide-en/"
    guide_label = "→ なぜ3層に分けるのか？" if is_ja else "→ Why 3 Layers?"

    html = _build_css()
    # Tag tables only — filter UI is generated by JS in codeinjection_foot
    html += '<div class="np-tax">\n'

    # Genre
    html += f'<h2 class="genre">{"ジャンル（Genre）" if is_ja else "Genre"} <span class="badge genre">{len(TAX["genres"])}</span></h2>\n'
    html += f'<div class="intro genre">{"記事の主題領域。「何についての記事か」を示します。" if is_ja else "The subject domain. What is this about?"}</div>\n'
    html += f'<table><tr><th class="genre">{"タグ名" if is_ja else "Tag"}</th><th class="genre">{"説明" if is_ja else "Description"}</th></tr>\n'
    for g in TAX["genres"]:
        n = g["name_ja"] if is_ja else g["name_en"]
        d = g["description_ja"] if is_ja else g["description_en"]
        html += f'<tr><td>{_tag_link(g["slug"], n, "genre")}</td><td>{d}</td></tr>\n'
    html += '</table>\n'

    # Event
    html += f'<h2 class="event">{"イベント（Event）" if is_ja else "Event"} <span class="badge event">{len(TAX["events"])}</span></h2>\n'
    html += f'<div class="intro event">{"何が起きたか（トリガー）。記事のきっかけとなった出来事を示します。" if is_ja else "The trigger. What happened?"}</div>\n'
    html += f'<table><tr><th class="event">{"タグ名" if is_ja else "Tag"}</th><th class="event">{"説明" if is_ja else "Description"}</th></tr>\n'
    for e in TAX["events"]:
        n = e["name_ja"] if is_ja else e["name_en"]
        d = e["description_ja"] if is_ja else e["description_en"]
        html += f'<tr><td>{_tag_link(e["slug"], n, "event")}</td><td>{d}</td></tr>\n'
    html += '</table>\n'

    # Dynamics
    html += f'<h2 class="dynamics">{"力学 / NOW Pattern" if is_ja else "Dynamics / NOW Pattern"} <span class="badge dynamics">{len(TAX["dynamics"])}</span></h2>\n'
    html += f'<div class="intro dynamics">{"「なぜそうなるのか」を説明する構造パターン。" if is_ja else "The structural pattern. Why does this happen?"}</div>\n'
    html += f'<table><tr><th class="dynamics">{"パターン名" if is_ja else "Pattern"}</th><th class="dynamics">{"構造" if is_ja else "Structure"}</th></tr>\n'
    for d in TAX["dynamics"]:
        n = d["name_ja"] if is_ja else d["name_en"]
        desc = d["description_ja"] if is_ja else d["description_en"]
        html += f'<tr><td>{_tag_link(d["slug"], n, "dynamics")}</td><td>{desc}</td></tr>\n'
    html += '</table>\n'

    # Reading guide
    html += f'<h2 style="color:#1a1a2e;border-bottom:3px solid #1a1a2e;">{"読み方ガイド" if is_ja else "How to Read Tags"}</h2>\n'
    html += f'<table><tr><th class="guide">{"層" if is_ja else "Layer"}</th><th class="guide">{"色" if is_ja else "Color"}</th><th class="guide">{"問い" if is_ja else "Question"}</th></tr>\n'
    html += f'<tr><td><strong>{"ジャンル" if is_ja else "Genre"}</strong></td><td><span style="color:{C_GENRE};font-weight:700;">{"●青" if is_ja else "● Blue"}</span></td><td>{"何についての記事か？" if is_ja else "What is this about?"}</td></tr>\n'
    html += f'<tr><td><strong>{"イベント" if is_ja else "Event"}</strong></td><td><span style="color:{C_EVENT};font-weight:700;">{"●緑" if is_ja else "● Green"}</span></td><td>{"何が起きたか？" if is_ja else "What happened?"}</td></tr>\n'
    html += f'<tr><td><strong>{"力学" if is_ja else "Dynamics"}</strong></td><td><span style="color:{C_DYNAMICS};font-weight:700;">{"●ピンク" if is_ja else "● Pink"}</span></td><td>{"なぜそうなるのか？" if is_ja else "Why does it happen?"}</td></tr>\n'
    html += '</table>\n'

    # Footer
    html += '<div style="background:#1a1a2e;color:#fff;padding:20px 24px;border-radius:8px;margin:24px 0;text-align:center;">'
    html += f'<a href="{guide_url}" style="color:#c9a84c;font-weight:700;text-decoration:none;">{guide_label}</a>'
    html += ' &nbsp;|&nbsp; '
    html += f'<a href="/taxonomy-{other_lang}/" style="color:#c9a84c;font-weight:700;text-decoration:none;">{other_label}</a>'
    html += '</div>\n'

    html += '</div>\n'
    return html


def upsert_page(title, slug, html_content, js_code, meta_title, meta_description):
    r = requests.get(f"{GHOST_URL}/ghost/api/admin/pages/slug/{slug}/", headers=ghost_headers(), verify=False)
    if r.status_code == 200:
        page = r.json()["pages"][0]
        print(f"Deleting old '{slug}'...")
        requests.delete(f"{GHOST_URL}/ghost/api/admin/pages/{page['id']}/", headers=ghost_headers(), verify=False)

    url = f"{GHOST_URL}/ghost/api/admin/pages/?source=html"
    payload = {"pages": [{"title": title, "slug": slug, "html": html_content,
        "status": "published", "meta_title": meta_title, "meta_description": meta_description}]}
    r = requests.post(url, json=payload, headers=ghost_headers(), verify=False)
    if r.status_code != 201:
        print(f"ERROR creating {slug}: {r.status_code} {r.text[:300]}")
        return None

    page = r.json()["pages"][0]
    updated_at = page["updated_at"]
    print(f"Created: {GHOST_URL}/{page['slug']}/")

    # Inject JS via codeinjection_foot
    payload2 = {"pages": [{"codeinjection_foot": js_code, "updated_at": updated_at}]}
    r2 = requests.put(f"{GHOST_URL}/ghost/api/admin/pages/{page['id']}/",
        json=payload2, headers=ghost_headers(), verify=False)
    if r2.status_code == 200:
        print(f"JS injected ({len(js_code)} chars)")
    else:
        print(f"WARNING: JS injection failed: {r2.status_code} {r2.text[:200]}")
    return page


def main():
    print("=== Creating Taxonomy Pages (JS-generated filter + language separation) ===\n")

    for lang in ["ja", "en"]:
        is_ja = lang == "ja"
        slug = f"taxonomy-{lang}"
        title = "Nowpattern タクソノミー" if is_ja else "Nowpattern Taxonomy"
        meta_title = "タクソノミー | 3層フィルターで記事検索" if is_ja else "Taxonomy | 3-Layer Article Filter"
        meta_desc = "ジャンル×イベント×力学で記事を検索。日本語記事のみ表示。" if is_ja else "Search by Genre × Event × Dynamics. English articles only."

        page_html = build_page_html(lang)
        js = _build_filter_js(lang)
        print(f"{lang.upper()}: HTML={len(page_html)} JS={len(js)}")
        upsert_page(title, slug, page_html, js, meta_title, meta_desc)
        print()

    print(f"Done: {GHOST_URL}/taxonomy-ja/ | {GHOST_URL}/taxonomy-en/")


if __name__ == "__main__":
    main()
