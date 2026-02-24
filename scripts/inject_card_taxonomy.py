#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_card_taxonomy.py — ホームページカードに3層タクソノミーバッジを表示

Ghost codeinjection_head にCSS、codeinjection_foot にJSを注入。
各カードの tag-* CSSクラスからジャンル/イベント/力学を読み取り表示する。

VPS上で実行:
  python3 /opt/shared/scripts/inject_card_taxonomy.py
  systemctl restart ghost-nowpattern
"""

import sys
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import os
import re
import sqlite3

DEFAULT_GHOST_DB = "/var/www/nowpattern/content/data/ghost.db"

# ── CSS ────────────────────────────────────────────────────────
CARD_TAXONOMY_CSS = """
/* Card Taxonomy Badge v1.0 */
.np-card-taxonomy {
  margin-top: 8px;
  font-size: 0.72em;
  line-height: 1.7;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
}
.np-ct-genre, .np-ct-event, .np-ct-dynamics {
  font-weight: 600;
  white-space: nowrap;
}
.np-ct-genre { color: #c9a84c; }
.np-ct-event { color: #16a34a; }
.np-ct-dynamics { color: #FF1A75; }
"""

# ── JS ─────────────────────────────────────────────────────────
CARD_TAXONOMY_JS = r"""
/* Card Taxonomy Badge v1.0 */
(function(){
  var GJA={
    'technology':'\u30c6\u30af\u30ce\u30ed\u30b8\u30fc','geopolitics':'\u5730\u653f\u5b66\u30fb\u5b89\u5168\u4fdd\u969c',
    'economy':'\u7d4c\u6e08\u30fb\u8cbf\u6613','finance':'\u91d1\u878d\u30fb\u5e02\u5834',
    'business':'\u30d3\u30b8\u30cd\u30b9\u30fb\u7523\u696d','crypto':'\u6697\u53f7\u8cc7\u7523',
    'energy':'\u30a8\u30cd\u30eb\u30ae\u30fc','environment':'\u74b0\u5883\u30fb\u6c17\u5019',
    'governance':'\u30ac\u30d0\u30ca\u30f3\u30b9\u30fb\u6cd5','society':'\u793e\u4f1a',
    'culture':'\u6587\u5316\u30fb\u30a8\u30f3\u30bf\u30e1\u30fb\u30b9\u30dd\u30fc\u30c4',
    'media':'\u30e1\u30c7\u30a3\u30a2\u30fb\u60c5\u5831','health':'\u5065\u5eb7\u30fb\u79d1\u5b66'
  };
  var GEN={
    'technology':'Technology','geopolitics':'Geopolitics & Security',
    'economy':'Economy & Trade','finance':'Finance & Markets',
    'business':'Business & Industry','crypto':'Crypto & Web3',
    'energy':'Energy','environment':'Environment & Climate',
    'governance':'Governance & Law','society':'Society',
    'culture':'Culture, Entertainment & Sports','media':'Media & Information',
    'health':'Health & Science'
  };
  var EJA={
    'event-military':'\u8ecd\u4e8b\u885d\u7a81','event-sanctions':'\u5236\u88c1\u30fb\u7d4c\u6e08\u6226\u4e89',
    'event-trade':'\u8cbf\u6613\u30fb\u95a2\u7a0e','event-regulation':'\u898f\u5236\u30fb\u6cd5\u6539\u6b63',
    'event-election':'\u9078\u6319\u30fb\u653f\u6a29\u4ea4\u4ee3','event-market':'\u5e02\u5834\u30b7\u30e7\u30c3\u30af',
    'event-tech':'\u6280\u8853\u9032\u5c55','event-alliance':'\u6761\u7d04\u30fb\u540c\u76df\u5909\u52d5',
    'event-resource':'\u8cc7\u6e90\u30fb\u30a8\u30cd\u30eb\u30ae\u30fc\u5371\u6a5f',
    'event-judicial':'\u53f8\u6cd5\u30fb\u88c1\u5224','event-disaster':'\u707d\u5bb3\u30fb\u4e8b\u6545',
    'event-health':'\u5065\u5eb7\u5371\u6a5f\u30fb\u611f\u67d3\u75c7',
    'event-cyber':'\u30b5\u30a4\u30d0\u30fc\u653b\u6483','event-social':'\u793e\u4f1a\u4e0d\u5b89\u30fb\u6297\u8b70',
    'event-structural':'\u69cb\u9020\u30b7\u30d5\u30c8','event-deal':'\u4e8b\u696d\u518d\u7de8\u30fb\u53d6\u5f15',
    'event-competition':'\u7af6\u4e89\u30fb\u30b7\u30a7\u30a2\u4e89\u3044',
    'event-trust':'\u30b9\u30ad\u30e3\u30f3\u30c0\u30eb\u30fb\u4fe1\u983c\u5371\u6a5f',
    'event-social-shift':'\u793e\u4f1a\u5909\u52d5\u30fb\u4e16\u8ad6'
  };
  var EEN={
    'event-military':'Military Conflict','event-sanctions':'Sanctions & Economic Warfare',
    'event-trade':'Trade & Tariffs','event-regulation':'Regulation & Law Change',
    'event-election':'Election & Political Shift','event-market':'Market Shock',
    'event-tech':'Tech Breakthrough','event-alliance':'Treaty & Alliance Change',
    'event-resource':'Resource & Energy Crisis','event-judicial':'Judicial Action',
    'event-disaster':'Disaster & Accident','event-health':'Health Emergency',
    'event-cyber':'Cyber & Information Attack','event-social':'Social Unrest & Protest',
    'event-structural':'Structural Shift','event-deal':'Deal & Restructuring',
    'event-competition':'Competition & Rivalry','event-trust':'Scandal & Trust Crisis',
    'event-social-shift':'Social Change & Opinion'
  };
  var DJA={
    'p-platform':'\u30d7\u30e9\u30c3\u30c8\u30d5\u30a9\u30fc\u30e0\u652f\u914d',
    'p-capture':'\u898f\u5236\u306e\u6355\u7372','p-narrative':'\u7269\u8a9e\u306e\u8987\u6a29',
    'p-overreach':'\u6a29\u529b\u306e\u904e\u4f38\u5c55',
    'p-escalation':'\u5bfe\u7acb\u306e\u87ba\u65cb','p-alliance-strain':'\u540c\u76df\u306e\u4e80\u88c2',
    'p-path-dependency':'\u7d4c\u8def\u4f9d\u5b58','p-backlash':'\u63fa\u308a\u623b\u3057',
    'p-institutional-rot':'\u5236\u5ea6\u306e\u52a3\u5316',
    'p-collective-failure':'\u5354\u8abf\u306e\u5931\u6557',
    'p-moral-hazard':'\u30e2\u30e9\u30eb\u30cf\u30b6\u30fc\u30c9',
    'p-contagion':'\u4f1d\u67d3\u306e\u9023\u9396',
    'p-shock-doctrine':'\u5371\u6a5f\u4fbf\u4e57',
    'p-tech-leapfrog':'\u5f8c\u767a\u9006\u8ee2',
    'p-winner-takes-all':'\u52dd\u8005\u7dcf\u53d6\u308a',
    'p-legitimacy-void':'\u6b63\u7d71\u6027\u306e\u7a7a\u767d'
  };
  var DEN={
    'p-platform':'Platform Power','p-capture':'Regulatory Capture',
    'p-narrative':'Narrative War','p-overreach':'Imperial Overreach',
    'p-escalation':'Escalation Spiral','p-alliance-strain':'Alliance Strain',
    'p-path-dependency':'Path Dependency','p-backlash':'Backlash Pendulum',
    'p-institutional-rot':'Institutional Decay','p-collective-failure':'Coordination Failure',
    'p-moral-hazard':'Moral Hazard','p-contagion':'Contagion Cascade',
    'p-shock-doctrine':'Shock Doctrine','p-tech-leapfrog':'Tech Leapfrog',
    'p-winner-takes-all':'Winner Takes All','p-legitimacy-void':'Legitimacy Void'
  };

  function run(){
    var cards=document.querySelectorAll('article.gh-card');
    if(!cards.length) return;
    var isEN=location.pathname.indexOf('/en/')===0;

    cards.forEach(function(card){
      if(card.querySelector('.np-card-taxonomy')) return;
      var cls=card.className.split(/\s+/);
      var g=[],e=[],d=[];
      cls.forEach(function(c){
        if(c.indexOf('tag-')!==0) return;
        var s=c.substring(4);
        if(GJA[s]) g.push(s);
        else if(EJA[s]) e.push(s);
        else if(DJA[s]) d.push(s);
      });
      if(!g.length && !e.length && !d.length) return;

      var h='';
      if(g.length){
        var labels=g.map(function(s){return '#'+(isEN?GEN[s]:GJA[s]);});
        h+='<span class="np-ct-genre">'+labels.join(' ')+'</span>';
      }
      if(e.length){
        var labels=e.map(function(s){return '#'+(isEN?EEN[s]:EJA[s]);});
        h+='<span class="np-ct-event">'+labels.join(' ')+'</span>';
      }
      if(d.length){
        var labels=d.map(function(s){return '#'+(isEN?DEN[s]:DJA[s]);});
        h+='<span class="np-ct-dynamics">'+labels.join(' ')+'</span>';
      }

      var badge=document.createElement('div');
      badge.className='np-card-taxonomy';
      badge.innerHTML=h;

      var footer=card.querySelector('.gh-card-meta');
      if(footer && footer.parentNode){
        footer.parentNode.insertBefore(badge,footer.nextSibling);
      }
    });
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',run);
  } else {
    run();
  }
})();
"""

# ── Markers ────────────────────────────────────────────────────
CSS_MARKER = "/* Card Taxonomy Badge"
JS_MARKER = "/* Card Taxonomy Badge"


def inject():
    db_path = os.environ.get("GHOST_DB_PATH", DEFAULT_GHOST_DB)
    if not os.path.exists(db_path):
        print(f"ERROR: Ghost DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # ── CSS → codeinjection_head ──
    cur.execute("SELECT value FROM settings WHERE key = 'codeinjection_head'")
    row = cur.fetchone()
    head = (row[0] or "") if row else ""

    css_block = f"<style>\n{CARD_TAXONOMY_CSS.strip()}\n</style>"

    if CSS_MARKER in head:
        pattern = r"<style>\s*/\* Card Taxonomy Badge.*?</style>"
        head = re.sub(pattern, css_block, head, flags=re.DOTALL)
        print("CSS: Replaced existing Card Taxonomy CSS")
    else:
        head = head.rstrip() + "\n" + css_block
        print("CSS: Added Card Taxonomy CSS")

    cur.execute("UPDATE settings SET value = ? WHERE key = 'codeinjection_head'", (head,))

    # ── JS → codeinjection_foot ──
    cur.execute("SELECT value FROM settings WHERE key = 'codeinjection_foot'")
    row = cur.fetchone()
    foot = (row[0] or "") if row else ""

    js_block = f"<script>\n{CARD_TAXONOMY_JS.strip()}\n</script>"

    if JS_MARKER in foot:
        pattern = r"<script>\s*/\* Card Taxonomy Badge.*?</script>"
        foot = re.sub(pattern, js_block, foot, flags=re.DOTALL)
        print("JS: Replaced existing Card Taxonomy JS")
    else:
        foot = foot.rstrip() + "\n" + js_block
        print("JS: Added Card Taxonomy JS")

    cur.execute("UPDATE settings SET value = ? WHERE key = 'codeinjection_foot'", (foot,))

    conn.commit()
    conn.close()

    print(f"\nOK: Card Taxonomy Badge injected")
    print(f"  codeinjection_head: {len(head)} chars")
    print(f"  codeinjection_foot: {len(foot)} chars")
    print("NOTE: Run 'systemctl restart ghost-nowpattern' to apply")


if __name__ == "__main__":
    inject()
