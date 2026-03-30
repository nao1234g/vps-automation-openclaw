#!/usr/bin/env python3
"""Enforce managed Ghost UI blocks for language switching and portal localization."""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys


DEFAULT_GHOST_DB = "/var/www/nowpattern/content/data/ghost.db"
LANGUAGE_SWITCHER_MARKER = "Language Switcher v3.3"
UI_GUARD_MARKER = "Global UI Guard v1.0"
DEFAULT_PORTAL_SIGNUP_TEXT = "Join Free"
DEFAULT_PORTAL_BUTTON_STYLE = "icon-and-text"
DEFAULT_PORTAL_BUTTON = "true"
DEFAULT_PORTAL_PLANS = '["free"]'

LANGUAGE_SWITCHER_BLOCK = r"""<!-- Language Switcher v3.3 -->
<style>
.np-lang-bar {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  background: rgba(15,23,42,0.96);
  border: 1px solid rgba(148,163,184,0.26);
  border-radius: 12px;
  box-shadow: 0 10px 24px rgba(15,23,42,0.18);
  padding: 4px;
  margin-right: 6px;
  flex-shrink: 0;
  min-height: 40px;
}
.np-lang-disabled {
  color: #cbd5e1 !important;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(148,163,184,0.18);
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.06em;
  padding: 6px 10px;
  border-radius: 10px;
  min-width: 44px;
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: default;
  opacity: 0.88;
  line-height: 1;
}
.np-lang-bar a,
.np-lang-bar a:visited,
.np-lang-bar span,
.np-lang-bar [data-np-lang] {
  color: #f8fafc !important;
  text-decoration: none;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.06em;
  padding: 6px 10px;
  border-radius: 10px;
  min-width: 44px;
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  line-height: 1;
}
.np-lang-bar a,
.np-lang-bar a:visited,
.np-lang-bar [data-np-lang]:not(.np-lang-active):not(.np-lang-disabled) {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(148,163,184,0.18);
}
.np-lang-bar .np-lang-active {
  background: #f2c94c !important;
  border: 1px solid #f6dd86 !important;
  color: #111827 !important;
}
.np-lang-bar a:hover,
.np-lang-bar a:visited:hover,
.np-lang-bar a:focus-visible {
  background: rgba(255,255,255,0.12) !important;
  border-color: #93c5fd !important;
  color: #ffffff !important;
  outline: none;
}
.np-lang-sep {
  color: #94a3b8;
  font-size: 13px;
  line-height: 1;
  padding: 0 2px;
}
@media (max-width: 640px) {
  .np-lang-bar {
    padding: 3px;
    margin-right: 4px;
    min-height: 38px;
  }
  .np-lang-bar a,
  .np-lang-bar span,
  .np-lang-sep,
  .np-lang-disabled {
    font-size: 13px;
    min-width: 42px;
    min-height: 30px;
    padding: 5px 9px;
  }
}
</style>
<script>
(function() {
  var origin = window.location.origin || "https://nowpattern.com";

  function normalizePath(href) {
    if (!href) return null;
    try {
      var pathname = new URL(href, origin).pathname || "/";
      if (pathname !== "/" && !pathname.endsWith("/") && pathname.indexOf(".", pathname.lastIndexOf("/") + 1) === -1) {
        pathname += "/";
      }
      return pathname;
    } catch (e) {
      return null;
    }
  }

  function safePath(pathname) {
    return normalizePath(pathname || "/") || "/";
  }

  var path = safePath(window.location.pathname || "/");

  var knownPairs = {
    "/": { ja: "/", en: "/en/" },
    "/en/": { ja: "/", en: "/en/" },
    "/page/2/": { ja: "/page/2/", en: "/en/page/2/" },
    "/en/page/2/": { ja: "/page/2/", en: "/en/page/2/" },
    "/about/": { ja: "/about/", en: "/en/about/" },
    "/en/about/": { ja: "/about/", en: "/en/about/" },
    "/predictions/": { ja: "/predictions/", en: "/en/predictions/" },
    "/en/predictions/": { ja: "/predictions/", en: "/en/predictions/" },
    "/en-predictions/": { ja: "/predictions/", en: "/en/predictions/" },
    "/taxonomy/": { ja: "/taxonomy/", en: "/en/taxonomy/" },
    "/en/taxonomy/": { ja: "/taxonomy/", en: "/en/taxonomy/" },
    "/taxonomy-guide/": { ja: "/taxonomy-guide/", en: "/en/taxonomy-guide/" },
    "/en/taxonomy-guide/": { ja: "/taxonomy-guide/", en: "/en/taxonomy-guide/" },
    "/leaderboard/": { ja: "/leaderboard/", en: "/en/leaderboard/" },
    "/en/leaderboard/": { ja: "/leaderboard/", en: "/en/leaderboard/" },
    "/my-predictions/": { ja: "/my-predictions/", en: "/en/my-predictions/" },
    "/en/my-predictions/": { ja: "/my-predictions/", en: "/en/my-predictions/" }
  };

  function deriveArticlePair(pathname) {
    var match;
    if ((match = pathname.match(/^\/page\/(\d+)\/$/))) {
      return { ja: pathname, en: "/en/page/" + match[1] + "/" };
    }
    if ((match = pathname.match(/^\/en\/page\/(\d+)\/$/))) {
      return { ja: "/page/" + match[1] + "/", en: pathname };
    }
    if (pathname.indexOf("/en/") === 0) {
      var enSlug = pathname.replace(/^\/en\//, "").replace(/\/$/, "");
      if (enSlug && enSlug.indexOf("/") === -1) {
        var canonicalEnSlug = enSlug.indexOf("en-") === 0 ? enSlug.slice(3) : enSlug;
        return { ja: "/" + canonicalEnSlug + "/", en: "/en/" + canonicalEnSlug + "/" };
      }
      return null;
    }
    var jaSlug = pathname.replace(/^\//, "").replace(/\/$/, "");
    if (jaSlug && jaSlug.indexOf("/") === -1) {
      return { ja: pathname, en: "/en/" + jaSlug + "/" };
    }
    return null;
  }

  function derivePair(pathname) {
    return knownPairs[pathname] || deriveArticlePair(pathname);
  }

  function canVerify(pathname) {
    return !!(pathname && pathname !== path);
  }

  function verifyPath(pathname) {
    if (!canVerify(pathname)) {
      return Promise.resolve(!!pathname);
    }
    return fetch(pathname, { method: "HEAD", cache: "no-store", credentials: "same-origin" })
      .then(function(response) { return response.ok; })
      .catch(function() { return false; });
  }

  var altJa = document.querySelector('link[rel="alternate"][hreflang="ja"]');
  var altEn = document.querySelector('link[rel="alternate"][hreflang="en"]');
  var pair = derivePair(path) || null;
  var jaPath = normalizePath(altJa && altJa.getAttribute("href")) || (pair && pair.ja) || null;
  var enPath = normalizePath(altEn && altEn.getAttribute("href")) || (pair && pair.en) || null;
  var isEnPage = path === "/en/" || path.indexOf("/en/") === 0;

  if (!jaPath && !enPath) return;

  function createLangNode(label, href, active, enabled) {
    var node = document.createElement(active || !enabled ? "span" : "a");
    node.textContent = label;
    node.setAttribute("data-np-lang", label.toLowerCase());
    node.setAttribute("title", label === "JA" ? "日本語" : "English");
    node.setAttribute("aria-label", label === "JA" ? "Switch to Japanese" : "Switch to English");
    if (active) {
      node.className = "np-lang-active";
      node.setAttribute("data-np-lang-active", "true");
      node.setAttribute("aria-current", "page");
      node.style.setProperty("color", "#111827", "important");
      node.style.setProperty("background", "#f2c94c", "important");
      node.style.setProperty("border", "1px solid #f6dd86", "important");
    } else if (!enabled) {
      node.className = "np-lang-disabled";
      node.setAttribute("data-np-lang-disabled", "true");
      node.style.setProperty("color", "#cbd5e1", "important");
      node.style.setProperty("background", "rgba(255,255,255,0.06)", "important");
      node.style.setProperty("border", "1px solid rgba(148,163,184,0.18)", "important");
    } else {
      node.setAttribute("href", href);
      node.style.setProperty("color", "#f8fafc", "important");
      node.style.setProperty("background", "rgba(255,255,255,0.04)", "important");
      node.style.setProperty("border", "1px solid rgba(148,163,184,0.18)", "important");
    }
    return node;
  }

  var bar = document.createElement("div");
  bar.className = "np-lang-bar";
  bar.id = "np-lang-bar";
  var jaNode = createLangNode("JA", jaPath, !isEnPage, !isEnPage || !canVerify(jaPath));
  var enNode = createLangNode("EN", enPath, isEnPage, isEnPage || !canVerify(enPath));
  bar.appendChild(jaNode);

  var sep = document.createElement("span");
  sep.className = "np-lang-sep";
  sep.textContent = "|";
  bar.appendChild(sep);

  bar.appendChild(enNode);

  function swapNode(currentNode, label, href, active, enabled) {
    var nextNode = createLangNode(label, href, active, enabled);
    currentNode.replaceWith(nextNode);
    return nextNode;
  }

  function mount() {
    if (document.getElementById("np-lang-bar")) return true;
    var brand = document.querySelector(".gh-navigation-brand")
      || document.querySelector(".gh-head-brand")
      || document.querySelector(".gh-header-actions");
    if (!brand) return false;

    var searchBtn = brand.querySelector(".gh-search");
    if (searchBtn) {
      brand.insertBefore(bar, searchBtn);
    } else {
      brand.appendChild(bar);
    }
    return true;
  }

  var attempts = 0;
  function ensureMounted() {
    if (mount()) return;
    attempts += 1;
    if (attempts < 20) {
      window.setTimeout(ensureMounted, 150);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureMounted);
  } else {
    ensureMounted();
  }

  if (canVerify(jaPath)) {
    verifyPath(jaPath).then(function(ok) {
      jaNode = swapNode(jaNode, "JA", jaPath, false, ok);
    });
  }
  if (canVerify(enPath)) {
    verifyPath(enPath).then(function(ok) {
      enNode = swapNode(enNode, "EN", enPath, false, ok);
    });
  }
})();
</script>"""

UI_GUARD_BLOCK = r"""<!-- Global UI Guard v1.0 -->
<style>
.np-ui-managed .nav-en {
  display: none !important;
}
.np-ui-managed iframe.gh-portal-triggerbtn-iframe {
  max-width: calc(100vw - 16px) !important;
}
</style>
<script>
(function() {
  var path = window.location.pathname || "/";
  var isEnPage = path === "/en/" || path.indexOf("/en/") === 0;
  var labels = isEnPage ? {
    join: "Join Free",
    signIn: "Sign in",
    predictions: "Predictions",
    dynamics: "Explore Dynamics",
    about: "About",
    homeHref: "/en/",
    aboutHref: "/en/about/",
    predictionsHref: "/en/predictions/",
    dynamicsHref: "/en/tag/lang-en/"
  } : {
    join: "\u7121\u6599\u3067\u53c2\u52a0",
    signIn: "\u30ed\u30b0\u30a4\u30f3",
    predictions: "\u4e88\u6e2c\u30c8\u30e9\u30c3\u30ab\u30fc",
    dynamics: "\u529b\u5b66\u3067\u63a2\u3059",
    about: "About",
    homeHref: "/",
    aboutHref: "/about/",
    predictionsHref: "/predictions/",
    dynamicsHref: "/taxonomy/"
  };

  function normalizeLanguageState() {
    var root = document.documentElement;
    if (!root) return;
    root.lang = isEnPage ? "en" : "ja";
    root.classList.remove(isEnPage ? "np-ja" : "np-en");
    root.classList.add(isEnPage ? "np-en" : "np-ja", "np-ui-managed");
    if (document.body) {
      document.body.classList.remove(isEnPage ? "np-ja" : "np-en");
      document.body.classList.add(isEnPage ? "np-en" : "np-ja", "np-ui-managed");
    }
  }

  function setAnchor(selector, text, href) {
    var anchor = document.querySelector(selector);
    if (!anchor) return;
    if (typeof text === "string" && anchor.textContent.trim() !== text) {
      anchor.textContent = text;
    }
    if (href) {
      anchor.setAttribute("href", href);
    }
  }

  function fixHeader() {
    normalizeLanguageState();
    setAnchor(".gh-navigation-logo", "Nowpattern", labels.homeHref);
    setAnchor(".nav-yu-ce-toratuka a", labels.predictions, labels.predictionsHref);
    setAnchor(".nav-li-xue-detan-su a", labels.dynamics, labels.dynamicsHref);
    setAnchor(".nav-about a", labels.about, labels.aboutHref);
    var redundantLang = document.querySelector(".nav-en");
    if (redundantLang) {
      redundantLang.style.display = "none";
    }
    setAnchor('.gh-navigation-members [data-portal="signin"]', labels.signIn, "#/portal/signin");
    setAnchor('.gh-navigation-members [data-portal="signup"]', labels.join, "#/portal/signup");
  }

  function localizePortalTrigger() {
    var iframe = document.querySelector('iframe[data-testid="portal-trigger-frame"]');
    if (!iframe) return false;
    try {
      var doc = iframe.contentDocument || (iframe.contentWindow && iframe.contentWindow.document);
      if (!doc || !doc.body) return false;
      var label = doc.querySelector(".gh-portal-triggerbtn-label");
      if (label && label.textContent.trim() !== labels.join) {
        label.textContent = labels.join;
      }
      var container = doc.querySelector(".gh-portal-triggerbtn-container");
      if (container) {
        container.setAttribute("aria-label", labels.join);
      }
      var width = Math.max(176, Math.min(window.innerWidth - 16, isEnPage ? 232 : 212));
      iframe.style.width = width + "px";
      iframe.style.maxWidth = "calc(100vw - 16px)";
      return !!label;
    } catch (error) {
      return false;
    }
  }

  function normalizeHrefPath(href) {
    try {
      var url = new URL(href, origin);
      if (url.origin !== origin) return null;
      var pathname = url.pathname || "/";
      if (pathname !== "/" && !pathname.endsWith("/") && pathname.indexOf(".", pathname.lastIndexOf("/") + 1) === -1) {
        pathname += "/";
      }
      return pathname;
    } catch (error) {
      return null;
    }
  }

  function isUtilityPath(pathname) {
    if (!pathname) return true;
    if (
      pathname === "/" ||
      pathname === "/en/" ||
      pathname === "/about/" ||
      pathname === "/en/about/" ||
      pathname === "/taxonomy/" ||
      pathname === "/en/taxonomy/" ||
      pathname === "/taxonomy-guide/" ||
      pathname === "/en/taxonomy-guide/" ||
      pathname === "/taxonomy-guide-ja/" ||
      pathname === "/taxonomy-guide-en/" ||
      pathname === "/predictions/" ||
      pathname === "/en/predictions/" ||
      pathname === "/leaderboard/" ||
      pathname === "/en/leaderboard/" ||
      pathname === "/my-predictions/" ||
      pathname === "/en/my-predictions/" ||
      pathname === "/integrity-audit/" ||
      pathname === "/en/integrity-audit/"
    ) {
      return true;
    }
    return pathname.indexOf("/tag/") === 0 || pathname.indexOf("/author/") === 0 || pathname.indexOf("/rss/") === 0;
  }

  function rewriteSameLanguageCardPath(pathname) {
    if (!pathname || isUtilityPath(pathname)) return null;
    if (pathname.indexOf("/en/") === 0) {
      return isEnPage ? pathname : "/" + pathname.replace(/^\/en\//, "");
    }
    if (!isEnPage) return pathname;
    var slug = pathname.replace(/^\/+|\/+$/g, "");
    if (!slug || slug.indexOf("/") !== -1) return null;
    return "/en/" + slug + "/";
  }

  function rewriteStaleInternalLinks() {
    var anchors = document.querySelectorAll('a[href]');
    anchors.forEach(function(anchor) {
      var rawHref = anchor.getAttribute('href');
      if (!rawHref) return;
      var normalized = rawHref.trim();
      if (!normalized) return;

      if (normalized === "/en-predictions/") {
        anchor.setAttribute("href", "/en/predictions/");
        return;
      }

      if (normalized.indexOf("https://nowpattern.com/en/en-") === 0) {
        anchor.setAttribute("href", normalized.replace("https://nowpattern.com/en/en-", "https://nowpattern.com/en/"));
        return;
      }

      if (normalized.indexOf("/en/en-") === 0) {
        anchor.setAttribute("href", normalized.replace("/en/en-", "/en/"));
        return;
      }

      if (!anchor.closest(".gh-card, .post-feed")) return;
      if (anchor.dataset.npLang || anchor.closest(".np-lang-bar")) return;
      var path = normalizeHrefPath(normalized);
      var rewrittenPath = rewriteSameLanguageCardPath(path);
      if (rewrittenPath && rewrittenPath !== path) {
        anchor.setAttribute("href", rewrittenPath);
      }
    });
  }

  var scheduled = false;
  function scheduleSync() {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(function() {
      scheduled = false;
      fixHeader();
      rewriteStaleInternalLinks();
      localizePortalTrigger();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scheduleSync);
  } else {
    scheduleSync();
  }
  window.addEventListener("load", scheduleSync);

  var attempts = 0;
  var timer = window.setInterval(function() {
    scheduleSync();
    attempts += 1;
    if (attempts >= 40) {
      window.clearInterval(timer);
    }
  }, 500);

  var observer = new MutationObserver(function() {
    scheduleSync();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
</script>"""


def replace_managed_block(head_html: str, block_name: str, replacement: str) -> tuple[str, bool]:
    pattern = re.compile(
        rf"<!-- {re.escape(block_name)} v[0-9.]+ -->.*?</script>\s*",
        flags=re.DOTALL,
    )
    if pattern.search(head_html):
        return pattern.sub(lambda _match: replacement + "\n", head_html, count=1), True
    return (head_html.rstrip() + "\n\n" + replacement + "\n"), False


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix the broken global Ghost language switcher.")
    parser.add_argument("--db", default=os.environ.get("GHOST_DB_PATH", DEFAULT_GHOST_DB), help="Path to ghost.db")
    parser.add_argument("--dry-run", action="store_true", help="Print whether a replacement would occur without writing")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    db_path = args.db
    if not os.path.exists(db_path):
        print(f"ERROR: ghost.db not found: {db_path}")
        return 1

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT value FROM settings WHERE key = 'codeinjection_head'")
    row = cur.fetchone()
    if not row:
        print("ERROR: settings.codeinjection_head not found")
        con.close()
        return 1

    current = row[0] or ""
    updated, replaced_lang = replace_managed_block(current, "Language Switcher", LANGUAGE_SWITCHER_BLOCK)
    updated, replaced_ui = replace_managed_block(updated, "Global UI Guard", UI_GUARD_BLOCK)
    if 'href= + jaPath +' in updated or 'href= + enPath +' in updated:
        print("ERROR: malformed language switcher markup still present after replacement")
        con.close()
        return 1

    portal_updates: list[tuple[str, str]] = []
    for key, expected in [
        ("portal_button_signup_text", DEFAULT_PORTAL_SIGNUP_TEXT),
        ("portal_button_style", DEFAULT_PORTAL_BUTTON_STYLE),
        ("portal_button", DEFAULT_PORTAL_BUTTON),
        ("portal_plans", DEFAULT_PORTAL_PLANS),
    ]:
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        current_value = (cur.fetchone() or [None])[0]
        if current_value != expected:
            portal_updates.append((key, expected))

    if args.dry_run:
        print(f"DRY RUN: would sync managed UI blocks in {db_path}")
        print(f"Current head chars: {len(current)}")
        print(f"Updated head chars: {len(updated)}")
        for key, expected in portal_updates:
            print(f"Would update {key}: {expected}")
        con.close()
        return 0

    if updated != current:
        cur.execute("UPDATE settings SET value = ? WHERE key = 'codeinjection_head'", (updated,))
    for key, expected in portal_updates:
        cur.execute("UPDATE settings SET value = ? WHERE key = ?", (expected, key))
    con.commit()
    con.close()
    print(f"OK: synced managed Ghost UI blocks in {db_path}")
    print(f"Head chars: {len(current)} -> {len(updated)}")
    print(f"Language switcher block: {'replaced' if replaced_lang else 'appended'}")
    print(f"UI guard block: {'replaced' if replaced_ui else 'appended'}")
    if portal_updates:
        for key, expected in portal_updates:
            print(f"Updated {key} -> {expected}")
    else:
        print("Portal settings already aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
