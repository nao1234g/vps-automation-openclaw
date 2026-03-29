#!/usr/bin/env python3
"""Site-wide UI smoke audit for critical Nowpattern JA/EN pages."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.request
from dataclasses import asdict, dataclass, field
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
        "content_selectors": ["#np-tracking-list", "#np-tracking-list details"],
    },
    {
        "slug": "predictions-en",
        "path": "/en/predictions/",
        "expected_lang": "en",
        "required_toggle": True,
        "content_selectors": ["#np-tracking-list", "#np-tracking-list details"],
    },
]


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


def sample_internal_links(page, base_url: str) -> list[str]:
    hrefs = page.evaluate(
        """() => Array.from(document.querySelectorAll('main a[href], article a[href], #np-tracking-list a[href]'))
          .map((anchor) => anchor.href)
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
        if len(samples) >= 6:
            break
    return samples


def same_language_path_issues(paths: list[str], expected_lang: str) -> list[str]:
    issues: list[str] = []
    for path in paths:
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
    for path in paths[:4]:
        url = urljoin(base_url, path)
        try:
            request = urllib.request.Request(
                url,
                method="HEAD",
                headers={"User-Agent": "nowpattern-site-ui-smoke/1.0"},
            )
            with urllib.request.urlopen(request, context=ssl_ctx, timeout=15) as response:
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


def discover_feed_articles(page, base_url: str, limit: int = 2) -> list[str]:
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

    for group in (prioritized, fallback):
        for path in group:
            paths.append(path)
            if len(paths) >= limit:
                return paths
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
            toolbar_tracking: parseCount('.np-view-btn[data-view="tracking"] span'),
            toolbar_resolved: parseCount('.np-view-btn[data-view="resolved"] span'),
            tracking_details: document.querySelectorAll('#np-tracking-list details').length,
            resolved_details: document.querySelectorAll('#np-resolved-section details').length,
          };
        }"""
    )


def header_ui_snapshot(page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const texts = (selector) => Array.from(document.querySelectorAll(selector))
            .map((el) => (el.textContent || '').trim())
            .filter(Boolean);
          return {
            html_lang: (document.documentElement.getAttribute('lang') || '').toLowerCase(),
            html_classes: document.documentElement.className || '',
            nav_texts: texts('.gh-navigation-menu a'),
            member_texts: texts('.gh-navigation-members a'),
            brand_href: document.querySelector('.gh-navigation-logo')?.getAttribute('href') || '',
            about_href: document.querySelector('.nav-about a')?.getAttribute('href') || '',
          };
        }"""
    )


def portal_trigger_label(page) -> str | None:
    try:
        label = page.frame_locator('iframe[data-testid="portal-trigger-frame"]').locator(
            ".gh-portal-triggerbtn-label"
        ).first
        if label.count() == 0:
            return None
        text = label.inner_text(timeout=4000).strip()
        return text or None
    except Exception:
        return None


def validate_language_specific_ui(page, result: PageResult, expected_lang: str) -> None:
    snapshot = header_ui_snapshot(page)
    result.extra["header_ui"] = snapshot

    html_lang = str(snapshot.get("html_lang") or "").lower()
    if html_lang != expected_lang:
        result.fail(f"html lang mismatch: expected {expected_lang}, got {html_lang or 'missing'}")

    brand_path = urlparse(urljoin(page.url, str(snapshot.get("brand_href") or ""))).path or "/"
    about_path = urlparse(urljoin(page.url, str(snapshot.get("about_href") or ""))).path or "/"
    nav_member_text = " | ".join(list(snapshot.get("nav_texts") or []) + list(snapshot.get("member_texts") or []))

    portal_label = portal_trigger_label(page)
    result.extra["portal_trigger_label"] = portal_label

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

        ja_total = ja_summary.get("toolbar_all") or ((ja_summary.get("tracking_details") or 0) + (ja_summary.get("resolved_details") or 0))
        en_total = en_summary.get("toolbar_all") or ((en_summary.get("tracking_details") or 0) + (en_summary.get("resolved_details") or 0))
        if ja_total != en_total:
            result.fail(f"prediction totals differ between JA and EN: ja={ja_total} en={en_total}")

        if (ja_summary.get("tracking_details") or 0) != (en_summary.get("tracking_details") or 0):
            result.fail(
                f"tracking card counts differ between JA and EN: ja={ja_summary.get('tracking_details')} en={en_summary.get('tracking_details')}"
            )

        if (ja_summary.get("resolved_details") or 0) != (en_summary.get("resolved_details") or 0):
            result.fail(
                f"resolved card counts differ between JA and EN: ja={ja_summary.get('resolved_details')} en={en_summary.get('resolved_details')}"
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

    nav_timing = navigation_timing(page)
    result.extra["navigation_timing"] = nav_timing
    dom_ms = nav_timing.get("dom_content_loaded_ms")
    load_ms = nav_timing.get("load_ms")
    if isinstance(dom_ms, int) and dom_ms > 8000:
        result.warnings.append(f"slow domContentLoaded {dom_ms}ms")
    if isinstance(load_ms, int) and load_ms > 12000:
        result.warnings.append(f"slow load {load_ms}ms")

    validate_language_specific_ui(page, result, spec["expected_lang"])
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
