#!/usr/bin/env python3
"""Site-wide UI smoke audit for critical Nowpattern JA/EN pages."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import sys
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse


VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1100, "is_mobile": False},
    "mobile": {
        "width": 390,
        "height": 844,
        "is_mobile": True,
        "has_touch": True,
        "device_scale_factor": 2,
    },
}

CORE_PAGES = [
    {
        "slug": "home-ja",
        "path": "/",
        "expected_lang": "ja",
        "required_toggle": True,
        "content_selectors": ["main", ".post-feed", "article"],
    },
    {
        "slug": "home-en",
        "path": "/en/",
        "expected_lang": "en",
        "required_toggle": True,
        "content_selectors": ["main", ".post-feed", "article"],
    },
    {
        "slug": "about-ja",
        "path": "/about/",
        "expected_lang": "ja",
        "required_toggle": True,
        "content_selectors": ["main", "article"],
    },
    {
        "slug": "about-en",
        "path": "/en/about/",
        "expected_lang": "en",
        "required_toggle": True,
        "content_selectors": ["main", "article"],
    },
    {
        "slug": "taxonomy-ja",
        "path": "/taxonomy/",
        "expected_lang": "ja",
        "required_toggle": True,
        "content_selectors": ["main", "article"],
    },
    {
        "slug": "taxonomy-en",
        "path": "/en/taxonomy/",
        "expected_lang": "en",
        "required_toggle": True,
        "content_selectors": ["main", "article"],
    },
    {
        "slug": "predictions-ja",
        "path": "/predictions/",
        "expected_lang": "ja",
        "required_toggle": True,
        "content_selectors": ["#np-inplay-list", "#np-inplay-list details", "#np-awaiting-list", "#np-resolved-section"],
    },
    {
        "slug": "predictions-en",
        "path": "/en/predictions/",
        "expected_lang": "en",
        "required_toggle": True,
        "content_selectors": ["#np-inplay-list", "#np-inplay-list details", "#np-awaiting-list", "#np-resolved-section"],
    },
    {
        "slug": "integrity-audit-ja",
        "path": "/integrity-audit/",
        "expected_lang": "ja",
        "required_toggle": True,
        "content_selectors": ["main", "article", "h2"],
    },
    {
        "slug": "integrity-audit-en",
        "path": "/en/integrity-audit/",
        "expected_lang": "en",
        "required_toggle": True,
        "content_selectors": ["main", "article", "h2"],
    },
]

NEUTRAL_INTERNAL_PATHS = {
    "/",
    "/en/",
    "/about/",
    "/en/about/",
    "/taxonomy/",
    "/en/taxonomy/",
    "/taxonomy-ja/",
    "/taxonomy-en/",
    "/taxonomy-guide/",
    "/en/taxonomy-guide/",
    "/taxonomy-guide-ja/",
    "/taxonomy-guide-en/",
    "/predictions/",
    "/en/predictions/",
    "/leaderboard/",
    "/en/leaderboard/",
    "/my-predictions/",
    "/en/my-predictions/",
    "/integrity-audit/",
    "/en/integrity-audit/",
}
NEUTRAL_INTERNAL_PREFIXES = ("/tag/", "/author/", "/rss/", "/page/")


@dataclass
class PageResult:
    slug: str
    viewport: str
    url: str
    final_url: str = ""
    status: int = 0
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    content_hits: dict[str, int] = field(default_factory=dict)
    internal_link_sample: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


RGBA_RE = re.compile(r"rgba?\(([^)]+)\)")


def parse_css_rgba(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    match = RGBA_RE.search(value.strip())
    if not match:
        return None
    parts = [part.strip() for part in match.group(1).split(",")]
    if len(parts) < 3:
        return None
    try:
        r = float(parts[0])
        g = float(parts[1])
        b = float(parts[2])
        a = float(parts[3]) if len(parts) > 3 else 1.0
    except ValueError:
        return None
    return (r, g, b, a)


def _linearize_channel(channel: float) -> float:
    channel = channel / 255.0
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def contrast_ratio(fg: str | None, bg: str | None, fallback_bg: str | None = None) -> float | None:
    fg_rgba = parse_css_rgba(fg)
    bg_rgba = parse_css_rgba(bg)
    fallback_rgba = parse_css_rgba(fallback_bg)
    if not fg_rgba:
        return None
    if bg_rgba and bg_rgba[3] < 0.99 and fallback_rgba:
        bg_rgba = fallback_rgba
    if not bg_rgba:
        bg_rgba = fallback_rgba
    if not bg_rgba:
        return None

    def luminance(rgb: tuple[float, float, float, float]) -> float:
        r, g, b = rgb[:3]
        return (
            0.2126 * _linearize_channel(r)
            + 0.7152 * _linearize_channel(g)
            + 0.0722 * _linearize_channel(b)
        )

    fg_l = luminance(fg_rgba)
    bg_l = luminance(bg_rgba)
    lighter = max(fg_l, bg_l)
    darker = min(fg_l, bg_l)
    return (lighter + 0.05) / (darker + 0.05)


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def internal_path(url: str, base_url: str) -> str | None:
    parsed = urlparse(urljoin(base_url, url))
    base = urlparse(base_url)
    if parsed.netloc != base.netloc:
        return None
    return parsed.path or "/"


def has_meaningful_content(page, selectors: list[str], result: PageResult) -> bool:
    any_hit = False
    for selector in selectors:
        count = page.locator(selector).count()
        result.content_hits[selector] = count
        if count > 0:
            any_hit = True
    text_length = page.evaluate("document.body && document.body.innerText ? document.body.innerText.trim().length : 0")
    result.extra["body_text_length"] = text_length
    return any_hit and text_length >= 200


def broken_href_issues(page) -> list[str]:
    return page.evaluate(
        """() => {
          const bad = [];
          for (const anchor of document.querySelectorAll('a[href]')) {
            const href = anchor.getAttribute('href') || '';
            const text = (anchor.textContent || '').trim().slice(0, 60);
            if (!href) continue;
            if (/^\\+\\/?'?$/i.test(href.trim()) || href.includes('href= +')) {
              bad.push(`${text} -> ${href}`);
            }
          }
          return bad;
        }"""
    )


def detect_page_not_found(page) -> bool:
    title = page.title().lower()
    text = page.locator("body").inner_text(timeout=5000).lower()
    return ("404" in title or "page not found" in title) or (
        "404" in text and "page not found" in text
    )


def rotating_sample(items: list[str], limit: int, salt: str) -> list[str]:
    keyed = sorted(
        items,
        key=lambda item: hashlib.sha256(f"{salt}:{item}".encode("utf-8")).hexdigest(),
    )
    return keyed[:limit]


def sample_internal_links(page, base_url: str) -> list[str]:
    hrefs = page.evaluate(
        """() => Array.from(document.querySelectorAll('main a[href], article a[href], #np-inplay-list a[href], #np-awaiting-list a[href], #np-resolved-section a[href]'))
          .filter((anchor) => anchor.dataset.crossLangLink !== 'true')
          .map((anchor) => anchor.getAttribute('href') || anchor.href)
          .filter(Boolean)"""
    )
    samples: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        path = internal_path(href, base_url)
        if not path or path in seen:
            continue
        if path.startswith("/tag/") or path.startswith("/author/") or path.startswith("/rss/"):
            continue
        seen.add(path)
        samples.append(path)
    salt = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    return rotating_sample(samples, 10, salt)


def same_language_path_issues(paths: list[str], expected_lang: str) -> list[str]:
    issues: list[str] = []
    for path in paths:
        if path in NEUTRAL_INTERNAL_PATHS or path.startswith(NEUTRAL_INTERNAL_PREFIXES):
            continue
        if expected_lang == "en":
            if path != "/en/" and not path.startswith("/en/"):
                issues.append(path)
        else:
            if path.startswith("/en/"):
                issues.append(path)
    return issues


def check_internal_link_statuses(base_url: str, paths: list[str]) -> list[str]:
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    failures: list[str] = []
    for path in paths[:10]:
        url = urljoin(base_url, path)
        last_error = None
        saw_timeout = False
        for method, timeout_seconds in (("HEAD", 15), ("GET", 25)):
            try:
                request = urllib.request.Request(
                    url,
                    method=method,
                    headers={"User-Agent": "nowpattern-site-ui-smoke/1.0"},
                )
                with urllib.request.urlopen(request, context=ssl_ctx, timeout=timeout_seconds) as response:
                    if response.status < 400:
                        last_error = None
                        break
                    last_error = f"HTTP {response.status}"
            except Exception as exc:
                last_error = str(exc)
                if "timed out" in last_error.lower():
                    saw_timeout = True
        if last_error and saw_timeout:
            try:
                request = urllib.request.Request(
                    url,
                    method="GET",
                    headers={"User-Agent": "nowpattern-site-ui-smoke/1.0"},
                )
                with urllib.request.urlopen(request, context=ssl_ctx, timeout=90) as response:
                    if response.status < 400:
                        last_error = None
            except Exception as exc:
                last_error = str(exc)
        if last_error:
            failures.append(f"{path} -> {last_error}")
    return failures


def check_feed_card_statuses(base_url: str, paths: list[str]) -> list[str]:
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    failures: list[str] = []
    for path in paths[:8]:
        url = urljoin(base_url, path)
        try:
            request = urllib.request.Request(
                url,
                method="GET",
                headers={"User-Agent": "nowpattern-site-ui-smoke/1.0"},
            )
            with urllib.request.urlopen(request, context=ssl_ctx, timeout=20) as response:
                if response.status >= 400:
                    failures.append(f"{path} -> HTTP {response.status}")
        except Exception as exc:
            failures.append(f"{path} -> {exc}")
    return failures


def goto_with_retry(page, url: str, timeout_ms: int = 30000):
    last_error = None
    for current_timeout in (timeout_ms, 60000):
        try:
            return page.goto(url, wait_until="domcontentloaded", timeout=current_timeout)
        except Exception as exc:
            last_error = exc
            page.wait_for_timeout(1200)
    raise last_error


def navigation_timing(page) -> dict[str, int | None]:
    return page.evaluate(
        """() => {
          const nav = performance.getEntriesByType('navigation')[0];
          if (!nav) {
            return { dom_content_loaded_ms: null, load_ms: null, response_ms: null };
          }
          return {
            dom_content_loaded_ms: Math.round(nav.domContentLoadedEventEnd),
            load_ms: Math.round(nav.loadEventEnd || nav.duration || 0),
            response_ms: Math.round(nav.responseEnd || 0),
          };
        }"""
    )


def discover_feed_articles(page, base_url: str, limit: int = 4) -> list[str]:
    hrefs = page.evaluate(
        """() => Array.from(document.querySelectorAll('.post-feed a[href], .gh-card a[href], article a[href]'))
          .map((anchor) => anchor.href)
          .filter(Boolean)"""
    )
    paths: list[str] = []
    seen: set[str] = set()
    prioritized: list[str] = []
    fallback: list[str] = []
    for href in hrefs:
        path = internal_path(href, base_url)
        if not path:
            continue
        if path in {"/", "/en/"}:
            continue
        if path.startswith("/tag/") or path.startswith("/author/") or path.startswith("/rss/"):
            continue
        if path in seen:
            continue
        seen.add(path)
        if path.startswith("/en/en-"):
            prioritized.append(path)
        else:
            fallback.append(path)

    seed = datetime.now(timezone.utc).strftime("%Y%m%d")
    ordered = rotating_sample(prioritized, min(limit, len(prioritized)), seed)
    remaining = max(0, limit - len(ordered))
    if remaining > 0:
        ordered.extend(rotating_sample(fallback, remaining, seed))
    return ordered


def homepage_card_paths(page, base_url: str, limit: int = 8) -> list[str]:
    hrefs = page.evaluate(
        """() => Array.from(document.querySelectorAll('.gh-card-link[href], .post-feed .gh-card-link[href]'))
          .map((anchor) => anchor.getAttribute('href') || '')
          .filter(Boolean)"""
    )
    paths: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        path = internal_path(href, base_url)
        if not path or path in seen:
            continue
        seen.add(path)
        paths.append(path)
        if len(paths) >= limit:
            break
    return paths


def stale_en_internal_links(page, base_url: str) -> list[str]:
    hrefs = page.evaluate(
        """() => Array.from(document.querySelectorAll('a[href]'))
          .map((anchor) => anchor.getAttribute('href') || '')
          .filter(Boolean)"""
    )
    stale: list[str] = []
    for href in hrefs:
        path = internal_path(href, base_url)
        if not path:
            continue
        if path.startswith("/en/en-"):
            stale.append(path)
            if len(stale) >= 8:
                break
    return stale


def verify_lang_toggle(page, result: PageResult, expected_lang: str) -> None:
    expected_active = expected_lang.lower()
    try:
        page.wait_for_function(
            """(expectedLang) => {
              const active = document.querySelector(`[data-np-lang="${expectedLang}"][data-np-lang-active="true"]`);
              const otherLang = expectedLang === "ja" ? "en" : "ja";
              const other = document.querySelector(`[data-np-lang="${otherLang}"]`);
              return !!active && !!other;
            }""",
            arg=expected_active,
            timeout=5000,
        )
    except Exception:
        pass

    active_count = page.locator(f"[data-np-lang='{expected_active}'][data-np-lang-active='true']").count()
    if active_count == 0:
        result.fail(f"missing active language badge for {expected_active.upper()}")

    other_lang = "en" if expected_active == "ja" else "ja"
    other_anchor = page.locator(f"a[data-np-lang='{other_lang}']").first
    other_disabled = page.locator(
        f"span[data-np-lang='{other_lang}'][data-np-lang-disabled='true']"
    ).count()
    result.extra["lang_toggle_disabled_count"] = other_disabled

    if other_anchor.count() == 0:
        result.fail(f"missing clickable {other_lang.upper()} language toggle")
        return

    href = other_anchor.get_attribute("href")
    if not href:
        result.fail(f"{other_lang.upper()} language toggle missing href")
        return

    page.click(f"a[data-np-lang='{other_lang}']")
    page.wait_for_load_state("domcontentloaded")
    current_url = page.url
    result.extra["lang_toggle_target"] = current_url
    if "/404" in current_url or detect_page_not_found(page):
        result.fail(f"{other_lang.upper()} language toggle opened a 404 page: {current_url}")
        return
    if other_lang == "en" and "/en" not in urlparse(current_url).path:
        result.fail(f"EN language toggle stayed on non-EN path: {current_url}")
    if other_lang == "ja" and urlparse(current_url).path.startswith("/en/"):
        result.fail(f"JA language toggle stayed on EN path: {current_url}")


def prediction_tracker_summary(page) -> dict[str, int | None]:
    return page.evaluate(
        """() => {
          const parseCount = (selector) => {
            const el = document.querySelector(selector);
            if (!el) return null;
            const value = parseInt((el.textContent || '').replace(/[^0-9]/g, ''), 10);
            return Number.isFinite(value) ? value : null;
          };
          return {
            toolbar_all: parseCount('.np-view-btn[data-view="all"] span'),
            toolbar_inplay: parseCount('.np-view-btn[data-view="inplay"] span'),
            toolbar_awaiting: parseCount('.np-view-btn[data-view="awaiting"] span'),
            toolbar_resolved: parseCount('.np-view-btn[data-view="resolved"] span'),
            inplay_details: document.querySelectorAll('#np-inplay-list > details').length,
            awaiting_details: document.querySelectorAll('#np-awaiting-list > details').length,
            resolved_details: document.querySelectorAll('#np-resolved-section > details').length,
            cross_lang_links: document.querySelectorAll('#np-inplay-list [data-cross-lang-link="true"], #np-awaiting-list [data-cross-lang-link="true"], #np-resolved-section [data-cross-lang-link="true"]').length,
          };
        }"""
    )


def validate_integrity_audit_copy(page, result: PageResult, expected_lang: str) -> None:
    text = page.locator("body").inner_text(timeout=5000)
    if re.search(r"\b20\d{2}-\d{2}-\d{2}\b", text):
        result.fail("integrity audit page contains a fixed ISO date")
    if re.search(r"20\d{2}年\d{1,2}月", text):
        result.fail("integrity audit page contains a fixed Japanese date")
    if re.search(r"\d+件", text):
        result.fail("integrity audit page still exposes a fixed count in public copy")
    if re.search(r"\b\d{1,3}(,\d{3})+\b", text):
        result.fail("integrity audit page still exposes a comma-formatted fixed count")

    bad_headers = page.evaluate(
        """() => Array.from(document.querySelectorAll('th'))
          .map((el) => (el.textContent || '').trim())
          .filter((text) => text === '件数' || text === 'Count')"""
    )
    if bad_headers:
        result.fail(f"integrity audit page still renders count headers: {', '.join(bad_headers)}")

    tier_cards = page.locator(".np-tier-grid .np-tier-card").count()
    result.extra["integrity_tier_cards"] = tier_cards
    if tier_cards < 4:
        result.fail(f"integrity audit page missing tier cards: {tier_cards}")

    if expected_lang == "en" and "暫定計算値" in text:
        result.fail("unexpected Japanese tier copy on EN integrity page")


def validate_about_copy(page, result: PageResult, expected_lang: str) -> None:
    text = page.locator("body").inner_text(timeout=5000)
    head_html = page.locator("head").inner_html(timeout=5000)
    if expected_lang == "ja":
        if "予測オラクル・メディア" in text:
            result.fail("JA about page still uses old media label")
        if "開始年" in text:
            result.fail("JA about page still uses old metric label 開始年")
        if "検証可能な予測プラットフォーム" not in text:
            result.fail("JA about page missing canonical platform label")
        if "予測オラクル・メディア" in head_html:
            result.fail("JA about page head/meta still uses old media label")
    else:
        if "Prediction Oracle Media" in text:
            result.fail("EN about page still uses old media label")
        if "Verifiable Forecast Platform" not in text:
            result.fail("EN about page missing canonical platform label")
        if "0/2 correct" in text or "111 Total Forecasts" in text:
            result.fail("EN about page still exposes legacy fixed metrics")
        if "Prediction Oracle Media" in head_html:
            result.fail("EN about page head/meta still uses old media label")


def header_ui_snapshot(page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const texts = (selector) => Array.from(document.querySelectorAll(selector))
            .map((el) => (el.textContent || '').trim())
            .filter(Boolean);
          const nodeStyle = (selector) => {
            const el = document.querySelector(selector);
            if (!el) return null;
            const style = window.getComputedStyle(el);
            const parentStyle = el.parentElement ? window.getComputedStyle(el.parentElement) : null;
            const rect = el.getBoundingClientRect();
            return {
              text: (el.textContent || '').trim(),
              href: el.getAttribute('href') || '',
              color: style.color,
              background: style.backgroundColor,
              parent_background: parentStyle ? parentStyle.backgroundColor : '',
              font_size: style.fontSize,
              font_weight: style.fontWeight,
              width: rect.width,
              height: rect.height,
              opacity: style.opacity,
              active: el.getAttribute('data-np-lang-active') === 'true',
              disabled: el.getAttribute('data-np-lang-disabled') === 'true',
            };
          };
          return {
            html_lang: (document.documentElement.getAttribute('lang') || '').toLowerCase(),
            html_classes: document.documentElement.className || '',
            nav_texts: texts('.gh-navigation-menu a'),
            member_texts: texts('.gh-navigation-members a'),
            brand_href: document.querySelector('.gh-navigation-logo')?.getAttribute('href') || '',
            about_href: document.querySelector('.nav-about a')?.getAttribute('href') || '',
            lang_bar: nodeStyle('#np-lang-bar'),
            lang_ja: nodeStyle('#np-lang-bar [data-np-lang="ja"]'),
            lang_en: nodeStyle('#np-lang-bar [data-np-lang="en"]'),
          };
        }"""
    )


def portal_trigger_label(page, expected_label: str | None = None) -> str | None:
    label = page.frame_locator('iframe[data-testid="portal-trigger-frame"]').locator(
        ".gh-portal-triggerbtn-label"
    ).first
    for _ in range(10):
        try:
            if label.count() == 0:
                page.wait_for_timeout(500)
                continue
            text = label.inner_text(timeout=2000).strip()
            if text and (not expected_label or text == expected_label):
                return text
            if text:
                observed = text
            else:
                observed = None
        except Exception:
            observed = None
        page.wait_for_timeout(500)
    return observed if "observed" in locals() else None


def validate_language_specific_ui(page, result: PageResult, expected_lang: str) -> None:
    snapshot = header_ui_snapshot(page)
    result.extra["header_ui"] = snapshot

    html_lang = str(snapshot.get("html_lang") or "").lower()
    if html_lang != expected_lang:
        result.fail(f"html lang mismatch: expected {expected_lang}, got {html_lang or 'missing'}")

    brand_path = urlparse(urljoin(page.url, str(snapshot.get("brand_href") or ""))).path or "/"
    about_path = urlparse(urljoin(page.url, str(snapshot.get("about_href") or ""))).path or "/"
    nav_member_text = " | ".join(list(snapshot.get("nav_texts") or []) + list(snapshot.get("member_texts") or []))

    expected_portal_label = "Join Free" if expected_lang == "en" else "\u7121\u6599\u3067\u53c2\u52a0"
    portal_label = portal_trigger_label(page, expected_portal_label)
    result.extra["portal_trigger_label"] = portal_label

    lang_bar = snapshot.get("lang_bar")
    lang_ja = snapshot.get("lang_ja")
    lang_en = snapshot.get("lang_en")
    if not lang_bar or not lang_ja or not lang_en:
        result.fail("language switcher missing managed JA/EN controls")
    else:
        min_width = 40 if result.viewport == "mobile" else 42
        min_height = 30 if result.viewport == "mobile" else 32
        min_font = 13 if result.viewport == "mobile" else 14
        for label, node in {"JA": lang_ja, "EN": lang_en}.items():
            width = float(node.get("width") or 0)
            height = float(node.get("height") or 0)
            font_size = float(str(node.get("font_size") or "0").replace("px", "") or 0)
            ratio = contrast_ratio(
                str(node.get("color") or ""),
                str(node.get("background") or ""),
                str(node.get("parent_background") or ""),
            )
            if width < min_width or height < min_height:
                result.fail(
                    f"{label} toggle hit area too small: {width:.1f}x{height:.1f}px"
                )
            if font_size < min_font:
                result.fail(f"{label} toggle font too small: {font_size:.1f}px")
            if ratio is None or ratio < 4.5:
                result.fail(f"{label} toggle contrast too low: {ratio if ratio is not None else 'n/a'}")

    if expected_lang == "en":
        for bad_text in [
            "\u4e88\u6e2c\u30c8\u30e9\u30c3\u30ab\u30fc",
            "\u529b\u5b66\u3067\u63a2\u3059",
            "\u4e88\u6e2c\u30d7\u30e9\u30c3\u30c8\u30d5\u30a9\u30fc\u30e0\u306b\u53c2\u52a0\uff08\u7121\u6599\uff09",
            "\u7121\u6599\u3067\u53c2\u52a0",
            "\u8cfc\u8aad\u3059\u308b",
            "\u30ed\u30b0\u30a4\u30f3",
        ]:
            if bad_text in nav_member_text or (portal_label and bad_text in portal_label):
                result.fail(f"unexpected Japanese UI text on EN page: {bad_text}")
                break
        if brand_path != "/en/":
            result.fail(f"EN brand link points to wrong path: {brand_path}")
        if about_path != "/en/about/":
            result.fail(f"EN about link points to wrong path: {about_path}")
        if portal_label and portal_label != "Join Free":
            result.fail(f"EN portal trigger label mismatch: {portal_label}")
    else:
        if brand_path != "/":
            result.fail(f"JA brand link points to wrong path: {brand_path}")
        if about_path != "/about/":
            result.fail(f"JA about link points to wrong path: {about_path}")
        if portal_label and portal_label != "\u7121\u6599\u3067\u53c2\u52a0":
            result.fail(f"JA portal trigger label mismatch: {portal_label}")


def audit_prediction_tracker_parity(context, base_url: str, viewport_name: str) -> PageResult:
    result = PageResult(
        slug="predictions-parity",
        viewport=viewport_name,
        url=urljoin(base_url, "/predictions/"),
        final_url=urljoin(base_url, "/en/predictions/"),
    )

    ja_page = context.new_page()
    en_page = context.new_page()
    try:
        ja_resp = goto_with_retry(ja_page, urljoin(base_url, "/predictions/"))
        en_resp = goto_with_retry(en_page, urljoin(base_url, "/en/predictions/"))
        result.status = min((ja_resp.status if ja_resp else 0), (en_resp.status if en_resp else 0))
        ja_page.wait_for_timeout(1500)
        en_page.wait_for_timeout(1500)

        ja_summary = prediction_tracker_summary(ja_page)
        en_summary = prediction_tracker_summary(en_page)
        result.extra["ja_summary"] = ja_summary
        result.extra["en_summary"] = en_summary

        ja_total = ja_summary.get("toolbar_all") or (
            (ja_summary.get("inplay_details") or 0)
            + (ja_summary.get("awaiting_details") or 0)
            + (ja_summary.get("resolved_details") or 0)
        )
        en_total = en_summary.get("toolbar_all") or (
            (en_summary.get("inplay_details") or 0)
            + (en_summary.get("awaiting_details") or 0)
            + (en_summary.get("resolved_details") or 0)
        )
        if not ja_total or not en_total:
            result.fail(f"prediction totals missing: ja={ja_total} en={en_total}")

        if int(ja_summary.get("cross_lang_links") or 0) != 0:
            result.fail(f"JA tracker exposes cross-language links: {ja_summary.get('cross_lang_links')}")

        if int(en_summary.get("cross_lang_links") or 0) != 0:
            result.fail(f"EN tracker exposes cross-language links: {en_summary.get('cross_lang_links')}")

        ja_live_total = (
            (ja_summary.get("inplay_details") or 0)
            + (ja_summary.get("awaiting_details") or 0)
            + (ja_summary.get("resolved_details") or 0)
        )
        en_live_total = (
            (en_summary.get("inplay_details") or 0)
            + (en_summary.get("awaiting_details") or 0)
            + (en_summary.get("resolved_details") or 0)
        )

        if ja_live_total <= 0:
            result.fail(
                "JA tracker has no visible cards: "
                f"inplay={ja_summary.get('inplay_details')} awaiting={ja_summary.get('awaiting_details')} resolved={ja_summary.get('resolved_details')}"
            )

        if en_live_total <= 0:
            result.fail(
                "EN tracker has no visible cards: "
                f"inplay={en_summary.get('inplay_details')} awaiting={en_summary.get('awaiting_details')} resolved={en_summary.get('resolved_details')}"
            )
    finally:
        ja_page.close()
        en_page.close()

    return result


def run_page_audit(page, base_url: str, spec: dict[str, Any], viewport_name: str, screenshot_dir: Path | None) -> PageResult:
    result = PageResult(
        slug=spec["slug"],
        viewport=viewport_name,
        url=urljoin(base_url, spec["path"]),
    )

    response = goto_with_retry(page, result.url)
    result.final_url = page.url
    result.status = response.status if response else 0
    if result.status >= 400 or result.status == 0:
        result.fail(f"HTTP {result.status} for {result.url}")
        return result

    page.wait_for_timeout(1200)
    if spec.get("required_toggle"):
        try:
            page.wait_for_function(
                "() => !!document.querySelector('#np-lang-bar, [data-np-lang]')",
                timeout=5000,
            )
        except Exception:
            pass
    if detect_page_not_found(page):
        result.fail(f"404 template rendered at {page.url}")

    if not has_meaningful_content(page, spec["content_selectors"], result):
        result.fail("main content missing or too short")

    bad_hrefs = broken_href_issues(page)
    if bad_hrefs:
        preview = ", ".join(bad_hrefs[:3])
        result.fail(f"broken href markup found: {preview}")

    overflow = page.evaluate(
        """() => ({
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
          overflow: document.documentElement.scrollWidth - window.innerWidth
        })"""
    )
    result.extra["overflow"] = overflow
    if overflow["overflow"] > 4:
        result.fail(
            f"horizontal overflow detected ({overflow['scrollWidth']} > {overflow['innerWidth']})"
        )

    result.internal_link_sample = sample_internal_links(page, base_url)
    if not result.internal_link_sample:
        result.warnings.append("no internal content links sampled")
    else:
        link_failures = check_internal_link_statuses(base_url, result.internal_link_sample)
        if link_failures:
            result.fail(f"broken sampled internal links: {', '.join(link_failures[:3])}")
        wrong_lang_paths = same_language_path_issues(result.internal_link_sample, spec["expected_lang"])
        if wrong_lang_paths:
            result.fail(f"same-language landing mismatch: {', '.join(wrong_lang_paths[:3])}")

    if spec["slug"].startswith("home-"):
        card_paths = homepage_card_paths(page, base_url)
        result.extra["homepage_card_paths"] = card_paths
        preview_paths = [path for path in card_paths if path.startswith("/p/")]
        if preview_paths:
            result.warnings.append(f"preview-style homepage links present: {', '.join(preview_paths[:3])}")
        card_failures = check_feed_card_statuses(base_url, card_paths)
        if card_failures:
            result.fail(f"broken homepage card links: {', '.join(card_failures[:3])}")

    nav_timing = navigation_timing(page)
    result.extra["navigation_timing"] = nav_timing
    dom_ms = nav_timing.get("dom_content_loaded_ms")
    load_ms = nav_timing.get("load_ms")
    if isinstance(dom_ms, int) and dom_ms > 8000:
        result.warnings.append(f"slow domContentLoaded {dom_ms}ms")
    if isinstance(load_ms, int) and load_ms > 12000:
        result.warnings.append(f"slow load {load_ms}ms")

    validate_language_specific_ui(page, result, spec["expected_lang"])
    if spec["slug"].startswith("about-"):
        validate_about_copy(page, result, spec["expected_lang"])
    if spec["slug"].startswith("integrity-audit-"):
        validate_integrity_audit_copy(page, result, spec["expected_lang"])
    if spec["expected_lang"] == "en":
        stale_links = stale_en_internal_links(page, base_url)
        if stale_links:
            result.fail(f"stale EN article links still present: {', '.join(stale_links[:3])}")

    if screenshot_dir is not None:
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / f"{spec['slug']}-{viewport_name}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        result.screenshots.append(str(screenshot_path))

    if spec.get("required_toggle"):
        verify_lang_toggle(page, result, spec["expected_lang"])

    return result


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Run site-wide desktop/mobile UI smoke audit.")
    parser.add_argument("--base-url", default="https://nowpattern.com", help="Base site URL")
    parser.add_argument("--json-out", help="Optional JSON report path")
    parser.add_argument("--screenshot-dir", help="Optional screenshot output directory")
    parser.add_argument(
        "--skip-articles",
        action="store_true",
        help="Skip dynamic JA/EN article sampling",
    )
    args = parser.parse_args()

    screenshot_dir = Path(args.screenshot_dir) if args.screenshot_dir else None
    report: dict[str, Any] = {"base_url": args.base_url.rstrip("/"), "results": [], "summary": {}}
    failed = False

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright is not installed.")
        return 1

    base_url = args.base_url.rstrip("/") + "/"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        for viewport_name, viewport in VIEWPORTS.items():
            context = browser.new_context(
                viewport={"width": viewport["width"], "height": viewport["height"]},
                is_mobile=viewport.get("is_mobile", False),
                has_touch=viewport.get("has_touch", False),
                device_scale_factor=viewport.get("device_scale_factor", 1),
                ignore_https_errors=True,
            )

            page_specs = list(CORE_PAGES)
            if not args.skip_articles:
                for seed_slug, seed_path, expected_lang in [
                    ("article-seed-ja", "/", "ja"),
                    ("article-seed-en", "/en/", "en"),
                ]:
                    seed_page = context.new_page()
                    goto_with_retry(seed_page, urljoin(base_url, seed_path))
                    seed_page.wait_for_timeout(1000)
                    article_paths = discover_feed_articles(
                        seed_page,
                        base_url,
                        limit=1 if expected_lang == "ja" else 2,
                    )
                    seed_page.close()
                    for index, article_path in enumerate(article_paths, start=1):
                        suffix = "" if expected_lang == "ja" else f"-{index}"
                        page_specs.append(
                            {
                                "slug": f"sample-{expected_lang}-article{suffix}",
                                "path": article_path,
                                "expected_lang": expected_lang,
                                "required_toggle": False,
                                "content_selectors": ["main", "article"],
                            }
                        )

            for spec in page_specs:
                page = context.new_page()
                result = run_page_audit(page, base_url, spec, viewport_name, screenshot_dir)
                report["results"].append(asdict(result))
                if not result.ok:
                    failed = True
                page.close()

            parity_result = audit_prediction_tracker_parity(context, base_url, viewport_name)
            report["results"].append(asdict(parity_result))
            if not parity_result.ok:
                failed = True

            context.close()
        browser.close()

    total = len(report["results"])
    failed_results = [item for item in report["results"] if not item["ok"]]
    report["summary"] = {
        "total": total,
        "passed": total - len(failed_results),
        "failed": len(failed_results),
    }

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False))
    if failed_results:
        for item in failed_results:
            print(f"FAIL {item['slug']} [{item['viewport']}]: {' | '.join(item['errors'])}")
        return 1

    print("PASS: site UI smoke audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
