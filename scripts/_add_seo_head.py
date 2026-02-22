#!/usr/bin/env python3
"""Add hreflang + NewsArticle structured data to Ghost site header code injection."""
import sqlite3
import subprocess

DB = "/var/www/nowpattern/content/data/ghost.db"

# Read current head injection
conn = sqlite3.connect(DB)
cur = conn.execute("SELECT value FROM settings WHERE key='codeinjection_head'")
row = cur.fetchone()
current = row[0] if row else ""
conn.close()

print(f"Current head injection: {len(current)} chars")

# New SEO code to append
SEO_CODE = """
<!-- hreflang + NewsArticle SEO v1.0 -->
<script>
(function(){
  var loc = window.location;
  var path = loc.pathname;
  var base = "https://nowpattern.com";

  // Determine current language from URL
  var isEN = path.startsWith("/en/");
  var lang = isEN ? "en" : "ja";

  // Add hreflang for current page
  var link = document.createElement("link");
  link.rel = "alternate";
  link.hreflang = lang;
  link.href = loc.href;
  document.head.appendChild(link);

  // Add x-default (always points to JA version)
  var xd = document.createElement("link");
  xd.rel = "alternate";
  xd.hreflang = "x-default";
  xd.href = isEN ? base + path.replace("/en/", "/") : loc.href;
  document.head.appendChild(xd);

  // NewsArticle structured data (for article pages only)
  var article = document.querySelector("article.gh-article");
  if (article) {
    var titleEl = document.querySelector("h1.gh-article-title");
    var excerptEl = document.querySelector("p.gh-article-excerpt");
    var dateEl = document.querySelector("time[datetime]");
    var imgEl = document.querySelector("img.gh-article-image, figure.gh-article-image img");

    var schema = {
      "@context": "https://schema.org",
      "@type": "NewsArticle",
      "headline": titleEl ? titleEl.textContent.trim() : document.title,
      "description": excerptEl ? excerptEl.textContent.trim() : "",
      "datePublished": dateEl ? dateEl.getAttribute("datetime") : "",
      "dateModified": dateEl ? dateEl.getAttribute("datetime") : "",
      "author": {"@type": "Organization", "name": "Nowpattern"},
      "publisher": {
        "@type": "Organization",
        "name": "Nowpattern",
        "url": "https://nowpattern.com",
        "logo": {"@type": "ImageObject", "url": base + "/favicon.png"}
      },
      "mainEntityOfPage": {"@type": "WebPage", "@id": loc.href},
      "inLanguage": lang
    };

    if (imgEl && imgEl.src) {
      schema.image = imgEl.src;
    }

    var script = document.createElement("script");
    script.type = "application/ld+json";
    script.textContent = JSON.stringify(schema);
    document.head.appendChild(script);
  }
})();
</script>
"""

# Check if already added
if "hreflang + NewsArticle SEO" in current:
    print("Already added, skipping")
else:
    new_value = current + SEO_CODE
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE settings SET value=? WHERE key='codeinjection_head'", (new_value,))
    conn.commit()
    conn.close()
    print(f"Updated head injection: {len(new_value)} chars")

    # Restart Ghost
    subprocess.run(["systemctl", "restart", "ghost-nowpattern"], check=True)
    print("Ghost restarted")
