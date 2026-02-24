#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_live_panel.py — 記事内 Polymarket ライブパネル注入

個別記事ページ（post-template）で、その記事のタグと Polymarket embed_data を
自動照合し、関連マーケットの現在オッズを表示するパネルを挿入。

VPS cron (polymarket_monitor.py の後に実行):
  python3 /opt/shared/scripts/inject_live_panel.py
  systemctl restart ghost-nowpattern

手動:
  python3 inject_live_panel.py           # 注入
  python3 inject_live_panel.py --dry-run # プレビュー
"""

import sys
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import os
import re
import json
import sqlite3

DEFAULT_GHOST_DB = "/var/www/nowpattern/content/data/ghost.db"
EMBED_DATA = "/opt/shared/polymarket/embed_data.json"

# ── Load Polymarket data ──────────────────────────────────────

def load_embed_data():
    if not os.path.exists(EMBED_DATA):
        print(f"WARN: {EMBED_DATA} not found, using empty data")
        return []
    with open(EMBED_DATA, encoding="utf-8") as f:
        data = json.load(f)
    # Keep top 30 by volume to limit JS payload size
    if isinstance(data, list):
        data.sort(key=lambda x: x.get("volume_usd", 0), reverse=True)
        return data[:30]
    return []


# ── Build CSS ─────────────────────────────────────────────────

LIVE_PANEL_CSS = """
/* Polymarket Live Panel v1.0 */
.np-live-panel {
  background: linear-gradient(135deg, #0d1b2a, #1b2838);
  border: 1px solid #c9a84c33;
  border-radius: 8px;
  padding: 16px 20px;
  margin: 20px 0;
  font-size: 0.88em;
}
.np-live-panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #c9a84c;
  font-weight: 700;
  font-size: 0.95em;
}
.np-live-panel-header .np-lp-dot {
  width: 8px; height: 8px;
  background: #16a34a;
  border-radius: 50%;
  animation: np-pulse 2s infinite;
}
@keyframes np-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.np-live-panel-q {
  color: #e0dcd4;
  margin-bottom: 10px;
  font-style: italic;
}
.np-live-panel-bar {
  display: flex;
  height: 28px;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}
.np-lp-yes {
  background: #16a34a;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85em;
  min-width: 32px;
}
.np-lp-no {
  background: #dc2626;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85em;
  min-width: 32px;
}
.np-live-panel-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.78em;
  color: #888;
}
.np-live-panel-meta a {
  color: #c9a84c;
  text-decoration: none;
}
.np-live-panel-meta a:hover {
  text-decoration: underline;
}
.np-live-panel-divergence {
  margin-top: 10px;
  padding: 8px 12px;
  background: #ffffff08;
  border-radius: 4px;
  font-size: 0.85em;
  color: #e0dcd4;
}
.np-div-label { color: #888; }
.np-div-value { font-weight: 700; }
.np-div-high { color: #FF1A75; }
.np-div-mid { color: #f59e0b; }
.np-div-low { color: #16a34a; }
"""


# ── Build JS ──────────────────────────────────────────────────

def build_js(embed_data):
    """Build JS with embedded Polymarket data."""
    # Compact the data for JS
    markets_js = json.dumps([{
        "q": m.get("question", "")[:80],
        "p": round(m.get("probability", 0), 1),
        "o": m.get("outcomes", {}),
        "g": m.get("genres", []),
        "t": m.get("title", "")[:60],
        "v": round(m.get("volume_usd", 0)),
        "u": m.get("updated", ""),
        "es": m.get("event_slug", ""),
        "ms": m.get("market_slug", ""),
    } for m in embed_data], ensure_ascii=False)

    # Genre mapping for matching
    genre_map_js = json.dumps({
        "crypto": "crypto", "geopolitics": "geopolitics",
        "technology": "technology", "energy": "energy",
        "society": "society", "economic-policy": "economy",
        "financial-markets": "finance", "regulation": "governance",
        "security": "geopolitics", "corporate-strategy": "business",
    })

    # Stopwords for keyword extraction
    sw_js = json.dumps(list({
        "the", "a", "an", "is", "are", "was", "were", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "and", "but", "or", "it",
        "will", "would", "can", "this", "that", "not", "has", "have", "all",
    }))

    return f"""/* Polymarket Live Panel v1.0 */
(function(){{
  if(!document.body.classList.contains('post-template')) return;

  var M={markets_js};
  var GM={genre_map_js};
  var SW=new Set({sw_js});

  function kw(text){{
    return text.toLowerCase().replace(/[^\\w\\s\\-\\u3000-\\u9fff]/g,' ')
      .split(/\\s+/).filter(function(w){{ return w.length>1 && !SW.has(w); }});
  }}

  // Get article tags from body classes
  var cls=document.body.className.split(/\\s+/);
  var genres=[], events=[], dynamics=[];
  cls.forEach(function(c){{
    if(c.indexOf('tag-')!==0) return;
    var s=c.substring(4);
    if(s==='nowpattern'||s==='deep-pattern'||s.indexOf('lang-')===0) return;
    if(s.indexOf('event-')===0) events.push(s);
    else if(s.indexOf('p-')===0) dynamics.push(s);
    else genres.push(s);
  }});

  if(!genres.length && !events.length) return;

  // Get article title keywords
  var titleEl=document.querySelector('.gh-article-title, .article-title, h1');
  var titleText=titleEl ? titleEl.textContent : document.title;
  var artKw=kw(titleText);

  // Find best match
  var best=null, bestScore=0;
  M.forEach(function(m){{
    var score=0;
    var polyGenres=m.g.map(function(g){{ return GM[g]||g; }});
    genres.forEach(function(g){{
      if(polyGenres.indexOf(g)>=0) score+=3;
    }});
    var mKw=kw(m.t+' '+m.q);
    var hits=0;
    artKw.forEach(function(w){{
      if(mKw.indexOf(w)>=0) hits++;
    }});
    if(hits>=2) score+=hits;
    if(score>bestScore && ((genres.some(function(g){{return polyGenres.indexOf(g)>=0;}}) && hits>=2) || hits>=4)){{
      bestScore=score;
      best=m;
    }}
  }});

  if(!best) return;

  // Extract base scenario from article HTML
  var baseProb=null;
  var html=document.querySelector('.gh-content, .post-content');
  if(html){{
    var text=html.textContent;
    var m1=text.match(/(?:基本|Base)[^\\d]*?(\\d+)(?:-\\d+)?%/i);
    if(m1) baseProb=parseInt(m1[1]);
  }}

  // Build panel HTML
  var yesP=best.p;
  var noP=best.o&&best.o.No ? best.o.No : (100-yesP);
  var vol=best.v>=1e6 ? '$'+(best.v/1e6).toFixed(1)+'M' : '$'+(best.v/1e3).toFixed(0)+'K';

  var h='<div class="np-live-panel-header">';
  h+='<span class="np-lp-dot"></span> Polymarket Live';
  h+='</div>';
  h+='<div class="np-live-panel-q">'+best.q+'</div>';
  h+='<div class="np-live-panel-bar">';
  h+='<div class="np-lp-yes" style="width:'+Math.max(yesP,5)+'%">Yes '+yesP.toFixed(0)+'%</div>';
  h+='<div class="np-lp-no" style="width:'+Math.max(noP,5)+'%">No '+noP.toFixed(0)+'%</div>';
  h+='</div>';
  var pmUrl='https://polymarket.com';
  if(best.es) pmUrl='https://polymarket.com/event/'+best.es;
  h+='<div class="np-live-panel-meta">';
  h+='<span>Vol: '+vol+'</span>';
  h+='<span>'+best.u+'</span>';
  h+='<a href="'+pmUrl+'" target="_blank" rel="noopener">Polymarket で見る &rarr;</a>';
  h+='</div>';

  if(baseProb!==null){{
    var div=yesP-baseProb;
    var sign=div>0?'+':'';
    var cls2=Math.abs(div)>=15?'np-div-high':(Math.abs(div)>=8?'np-div-mid':'np-div-low');
    h+='<div class="np-live-panel-divergence">';
    h+='<span class="np-div-label">Nowpattern基本シナリオ: '+baseProb+'% | Polymarket: '+yesP.toFixed(0)+'% | </span>';
    h+='<span class="np-div-value '+cls2+'">乖離: '+sign+div.toFixed(0)+'%</span>';
    h+='</div>';
  }}

  var panel=document.createElement('div');
  panel.className='np-live-panel';
  panel.innerHTML=h;

  // Insert after np-fast-read or at top of content
  var fastRead=document.querySelector('.np-fast-read');
  if(fastRead && fastRead.parentNode){{
    fastRead.parentNode.insertBefore(panel, fastRead.nextSibling);
  }} else {{
    var content=document.querySelector('.gh-content, .post-content');
    if(content && content.firstChild){{
      content.insertBefore(panel, content.children[1]||content.firstChild);
    }}
  }}
}})();"""


# ── Inject into Ghost DB ──────────────────────────────────────

CSS_MARKER = "/* Polymarket Live Panel"
JS_MARKER = "/* Polymarket Live Panel"


def inject(dry_run=False):
    embed_data = load_embed_data()
    print(f"Loaded {len(embed_data)} Polymarket markets")

    css_block = f"<style>\n{LIVE_PANEL_CSS.strip()}\n</style>"
    js_code = build_js(embed_data)
    js_block = f"<script>\n{js_code}\n</script>"

    if dry_run:
        print("\n=== CSS ===")
        print(css_block[:500] + "...")
        print(f"\n=== JS ({len(js_code)} chars) ===")
        print(js_block[:1000] + "...")
        print(f"\nTotal: CSS={len(css_block)} JS={len(js_block)} chars")
        return

    db_path = os.environ.get("GHOST_DB_PATH", DEFAULT_GHOST_DB)
    if not os.path.exists(db_path):
        print(f"ERROR: Ghost DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # CSS → codeinjection_head
    cur.execute("SELECT value FROM settings WHERE key = 'codeinjection_head'")
    row = cur.fetchone()
    head = (row[0] or "") if row else ""

    if CSS_MARKER in head:
        pattern = r"<style>\s*/\* Polymarket Live Panel.*?</style>"
        head = re.sub(pattern, lambda m: css_block, head, flags=re.DOTALL)
        print("CSS: Replaced existing Live Panel CSS")
    else:
        head = head.rstrip() + "\n" + css_block
        print("CSS: Added Live Panel CSS")

    cur.execute("UPDATE settings SET value = ? WHERE key = 'codeinjection_head'", (head,))

    # JS → codeinjection_foot
    cur.execute("SELECT value FROM settings WHERE key = 'codeinjection_foot'")
    row = cur.fetchone()
    foot = (row[0] or "") if row else ""

    if JS_MARKER in foot:
        pattern = r"<script>\s*/\* Polymarket Live Panel.*?</script>"
        foot = re.sub(pattern, lambda m: js_block, foot, flags=re.DOTALL)
        print("JS: Replaced existing Live Panel JS")
    else:
        foot = foot.rstrip() + "\n" + js_block
        print("JS: Added Live Panel JS")

    cur.execute("UPDATE settings SET value = ? WHERE key = 'codeinjection_foot'", (foot,))

    conn.commit()
    conn.close()

    print(f"\nOK: Polymarket Live Panel injected")
    print(f"  Markets embedded: {len(embed_data)}")
    print(f"  CSS: {len(css_block)} chars")
    print(f"  JS: {len(js_block)} chars")
    print("NOTE: Run 'systemctl restart ghost-nowpattern' to apply")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Inject Polymarket Live Panel")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    inject(dry_run=args.dry_run)
