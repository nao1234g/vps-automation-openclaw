#!/usr/bin/env python3
"""Prediction tracker E2E checks for Nowpattern JA/EN pages."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin


PREDICTIONS_URLS = {
    "ja": "https://nowpattern.com/predictions/",
    "en": "https://nowpattern.com/en/predictions/",
}
TRACKING_SELECTOR = "#np-inplay-list details, #np-awaiting-list details"
SCREENSHOT_DIR = "/opt/shared/reports/e2e-screenshots"
TIMEOUT = 20000
DEVICE_CONFIGS = {
    "desktop": {
        "viewport": {"width": 1280, "height": 900},
        "context": {"ignore_https_errors": True},
        "cards_per_page": 36,
    },
    "mobile": {
        "viewport": {"width": 390, "height": 844},
        "context": {
            "ignore_https_errors": True,
            "is_mobile": True,
            "has_touch": True,
            "device_scale_factor": 3,
        },
        "cards_per_page": 18,
    },
}


def goto_with_retry(page, url: str, wait_until: str = "domcontentloaded"):
    last_error = None
    for timeout_ms in (30000, 60000):
        try:
            return page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        except Exception as exc:
            last_error = exc
            page.wait_for_timeout(1200)
    raise last_error


def check_internal_url(href: str, ssl_ctx: ssl.SSLContext) -> tuple[bool, str]:
    """Use HEAD first, then GET fallback so transient HEAD timeouts do not fail deploys."""
    last_error = "unknown error"
    for method, timeout in (("HEAD", 10), ("GET", 20)):
        try:
            req = urllib.request.Request(
                href,
                method=method,
                headers={"User-Agent": "nowpattern-e2e/1.0"},
            )
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=timeout) as response:
                if response.status < 400:
                    return True, f"{method} {response.status}"
                last_error = f"{method} {response.status}"
        except Exception as exc:
            last_error = f"{method} {exc}"
    return False, last_error


def card_counts(page, selector: str) -> tuple[int, int, int]:
    total, visible = page.evaluate(
        """(sel) => {
          const cards = Array.from(document.querySelectorAll(sel));
          const visible = cards.filter((card) => {
            const style = window.getComputedStyle(card);
            return style.display !== 'none' && style.visibility !== 'hidden';
          }).length;
          return [cards.length, visible];
        }""",
        selector,
    )
    return total, visible, max(0, total - visible)


def tracker_category_counts(page) -> dict[str, int]:
    return page.evaluate(
        """() => {
          const counts = {};
          for (const card of document.querySelectorAll('#np-inplay-list details, #np-awaiting-list details')) {
            const genres = (card.dataset.genres || '')
              .split(',')
              .map((item) => item.trim())
              .filter(Boolean);
            for (const genre of genres) {
              counts[genre] = (counts[genre] || 0) + 1;
            }
          }
          return counts;
        }"""
    ) or {}


def record_result(name: str, ok: bool, detail: str, fail_details: list[str]) -> tuple[int, int]:
    if ok:
        print(f"  PASS: {detail}")
        return 1, 0
    print(f"  FAIL: {detail}")
    fail_details.append(f"{name}: {detail}")
    return 0, 1


def run_tests(lang: str, device: str, take_screenshot: bool = False) -> dict[str, object]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed.")
        print("Run: pip3 install playwright && playwright install chromium")
        return {
            "lang": lang,
            "device": device,
            "ok": False,
            "pass_count": 0,
            "fail_count": 1,
            "fail_details": ["playwright_not_installed"],
        }

    base_url = PREDICTIONS_URLS[lang]
    device_config = DEVICE_CONFIGS[device]
    fail_details: list[str] = []
    pass_count = 0
    fail_count = 0

    print("\n" + "=" * 64)
    print(f"  Nowpattern Prediction Tracker E2E ({lang.upper()} / {device.upper()})")
    print(f"  URL: {base_url}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M JST')}")
    print("=" * 64 + "\n")

    Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context_kwargs = dict(device_config["context"])
        context_kwargs["viewport"] = device_config["viewport"]
        ctx = browser.new_context(**context_kwargs)
        page = ctx.new_page()
        page.set_default_timeout(TIMEOUT)

        print("Test 0: page load")
        try:
            resp = goto_with_retry(page, base_url, wait_until="domcontentloaded")
            status = resp.status if resp else 0
            inc_pass, inc_fail = record_result("page load", status < 400, f"HTTP {status}", fail_details)
            pass_count += inc_pass
            fail_count += inc_fail
            if status >= 400:
                browser.close()
                return {
                    "lang": lang,
                    "device": device,
                    "ok": False,
                    "pass_count": pass_count,
                    "fail_count": fail_count + 1,
                    "fail_details": fail_details + [str(status)],
                }
        except Exception as exc:
            record_result("page load", False, str(exc), fail_details)
            browser.close()
            return {
                "lang": lang,
                "device": device,
                "ok": False,
                "pass_count": pass_count,
                "fail_count": fail_count + 1,
                "fail_details": fail_details + [str(exc)],
            }

        if take_screenshot:
            ss_path = f"{SCREENSHOT_DIR}/{lang}-{device}-01-initial.png"
            page.screenshot(path=ss_path, full_page=False)
            print(f"  Screenshot: {ss_path}")

        print("\nTest 1: tracking cards and controls visible")
        try:
            page.wait_for_function(
                "() => document.querySelectorAll('#np-inplay-list details, #np-awaiting-list details').length > 0",
                timeout=TIMEOUT,
            )
            total, visible, _ = card_counts(page, TRACKING_SELECTOR)
            search_visible = page.locator("#np-search").is_visible()
            controls_visible = (
                page.locator("[data-view='all']").is_visible()
                and page.locator("[data-view='inplay']").is_visible()
                and page.locator("[data-view='awaiting']").is_visible()
                and page.locator("[data-view='resolved']").is_visible()
            )
            ok = total > 0 and visible > 0 and search_visible and controls_visible
            detail = f"tracking_total={total}, visible={visible}, search={search_visible}, view_controls={controls_visible}"
            inc_pass, inc_fail = record_result("tracking visible", ok, detail, fail_details)
            pass_count += inc_pass
            fail_count += inc_fail
        except Exception as exc:
            inc_pass, inc_fail = record_result("tracking visible", False, str(exc), fail_details)
            pass_count += inc_pass
            fail_count += inc_fail

        print("\nTest 2: impossible keyword hides all cards")
        try:
            search_box = page.locator("#np-search")
            search_box.wait_for(state="visible", timeout=TIMEOUT)
            initial_total, initial_visible, _ = card_counts(page, TRACKING_SELECTOR)
            search_box.fill("zzzxxx_nonexistent_9999")
            page.wait_for_timeout(800)
            total_after, visible_after, hidden_after = card_counts(page, TRACKING_SELECTOR)
            ok = initial_total > 0 and visible_after == 0 and hidden_after == initial_total
            detail = f"initial_total={initial_total}, initial_visible={initial_visible}, after_visible={visible_after}, hidden={hidden_after}, total_after={total_after}"
            inc_pass, inc_fail = record_result("search filter", ok, detail, fail_details)
            pass_count += inc_pass
            fail_count += inc_fail
            search_box.fill("")
            page.wait_for_timeout(300)
        except Exception as exc:
            inc_pass, inc_fail = record_result("search filter", False, str(exc), fail_details)
            pass_count += inc_pass
            fail_count += inc_fail

        print("\nTest 3: category filter returns a real subset")
        try:
            initial_total, _, _ = card_counts(page, TRACKING_SELECTOR)
            category_counts = tracker_category_counts(page)
            buttons = page.locator(".np-cat-btn")
            clicked = False
            detail = f"counts={category_counts}"
            for index in range(buttons.count()):
                btn = buttons.nth(index)
                category = btn.get_attribute("data-cat")
                expected_matches = int(category_counts.get(category or "", 0))
                if not category or category == "all":
                    continue
                if expected_matches <= 0 or expected_matches >= initial_total:
                    continue

                btn.click()
                page.wait_for_timeout(700)
                _, visible_after, hidden_after = card_counts(page, TRACKING_SELECTOR)
                expected_visible = min(expected_matches, int(device_config["cards_per_page"]))
                ok = 0 < visible_after <= expected_visible and hidden_after > 0
                detail = (
                    f"category={category}, expected_matches={expected_matches}, "
                    f"visible={visible_after}, hidden={hidden_after}, expected_visible<={expected_visible}"
                )
                inc_pass, inc_fail = record_result("category filter", ok, detail, fail_details)
                pass_count += inc_pass
                fail_count += inc_fail
                page.locator(".np-cat-btn[data-cat='all']").click()
                page.wait_for_timeout(300)
                clicked = True
                break
            if not clicked:
                non_all_categories = [key for key in category_counts.keys() if key and key != "all"]
                if buttons.count() <= 1 or not non_all_categories:
                    detail = f"no non-all categories exposed: counts={category_counts}"
                    inc_pass, inc_fail = record_result("category filter", True, detail, fail_details)
                else:
                    inc_pass, inc_fail = record_result("category filter", False, detail, fail_details)
                pass_count += inc_pass
                fail_count += inc_fail
        except Exception as exc:
            inc_pass, inc_fail = record_result("category filter", False, str(exc), fail_details)
            pass_count += inc_pass
            fail_count += inc_fail

        print("\nTest 4: no horizontal overflow on current viewport")
        try:
            overflow = page.evaluate(
                """() => ({
                    scrollWidth: document.documentElement.scrollWidth,
                    innerWidth: window.innerWidth
                })"""
            )
            ok = int(overflow["scrollWidth"]) <= int(overflow["innerWidth"]) + 4
            detail = f"scrollWidth={overflow['scrollWidth']}, innerWidth={overflow['innerWidth']}"
            inc_pass, inc_fail = record_result("horizontal overflow", ok, detail, fail_details)
            pass_count += inc_pass
            fail_count += inc_fail
        except Exception as exc:
            inc_pass, inc_fail = record_result("horizontal overflow", False, str(exc), fail_details)
            pass_count += inc_pass
            fail_count += inc_fail

        print("\nTest 5: in-play / awaiting / resolved view toggle works")
        try:
            resolved_button = page.locator("[data-view='resolved']")
            awaiting_button = page.locator("[data-view='awaiting']")
            inplay_button = page.locator("[data-view='inplay']")
            all_button = page.locator("[data-view='all']")
            resolved_button.click()
            page.wait_for_timeout(500)
            tracking_section_hidden = page.locator("#np-tracking-section").evaluate(
                "el => window.getComputedStyle(el).display === 'none'"
            )
            resolved_total, resolved_visible, _ = card_counts(page, "#np-resolved-section details")
            step1_ok = tracking_section_hidden and resolved_total > 0 and resolved_visible > 0

            awaiting_button.click()
            page.wait_for_timeout(500)
            awaiting_section_visible = page.locator("#np-awaiting-group").evaluate(
                "el => window.getComputedStyle(el).display !== 'none'"
            )
            awaiting_total, awaiting_visible, _ = card_counts(page, "#np-awaiting-list details")
            inplay_section_hidden = page.locator("#np-inplay-group").evaluate(
                "el => window.getComputedStyle(el).display === 'none'"
            )
            resolved_section_hidden = page.locator("#np-resolved-section").evaluate(
                "el => window.getComputedStyle(el).display === 'none'"
            )
            step2_ok = awaiting_section_visible and awaiting_total > 0 and awaiting_visible > 0 and inplay_section_hidden and resolved_section_hidden

            inplay_button.click()
            page.wait_for_timeout(500)
            inplay_total, inplay_visible, _ = card_counts(page, "#np-inplay-list details")
            expected_inplay = int(page.locator("[data-view='inplay'] span").inner_text().strip() or "0")
            awaiting_section_hidden = page.locator("#np-awaiting-group").evaluate(
                "el => window.getComputedStyle(el).display === 'none'"
            )
            resolved_section_hidden_again = page.locator("#np-resolved-section").evaluate(
                "el => window.getComputedStyle(el).display === 'none'"
            )
            step3_ok = awaiting_section_hidden and resolved_section_hidden_again and (
                (expected_inplay == 0 and inplay_total == 0 and inplay_visible == 0)
                or (expected_inplay > 0 and inplay_total > 0 and inplay_visible > 0)
            )

            all_button.click()
            page.wait_for_timeout(500)
            step4_ok = (
                page.locator("#np-tracking-section").evaluate("el => window.getComputedStyle(el).display !== 'none'")
                and page.locator("#np-resolved-section").evaluate("el => window.getComputedStyle(el).display !== 'none'")
            )

            ok = step1_ok and step2_ok and step3_ok and step4_ok
            detail = (
                f"resolved_total={resolved_total}, resolved_visible={resolved_visible}, "
                f"awaiting_total={awaiting_total}, awaiting_visible={awaiting_visible}, "
                f"inplay_total={inplay_total}, inplay_visible={inplay_visible}, expected_inplay={expected_inplay}"
            )
            inc_pass, inc_fail = record_result("view toggle", ok, detail, fail_details)
            pass_count += inc_pass
            fail_count += inc_fail
        except Exception as exc:
            inc_pass, inc_fail = record_result("view toggle", False, str(exc), fail_details)
            pass_count += inc_pass
            fail_count += inc_fail

        print("\nTest 6: tracker article links do not loop back to tracker")
        try:
            offending = page.evaluate(
                """() => {
                    const current = window.location.pathname;
                    return Array.from(document.querySelectorAll('#np-inplay-list details a[href], #np-awaiting-list details a[href], #np-resolved-section details a[href]'))
                      .filter((anchor) => anchor.dataset.crossLangLink !== 'true')
                      .map((anchor) => {
                        const href = anchor.getAttribute('href') || '';
                        const text = (anchor.textContent || '').trim();
                        let path = '';
                        try {
                          path = new URL(href, window.location.origin).pathname + (new URL(href, window.location.origin).hash || '');
                        } catch (e) {
                          path = href;
                        }
                        return { href, path, text };
                      })
                      .filter((item) =>
                        item.path.startsWith('/predictions/#np-') ||
                        item.path.startsWith('/en/predictions/#np-') ||
                        item.text.includes('View in tracker') ||
                        item.text.includes('トラッカーで見る')
                      );
                }"""
            )
            ok = not offending
            detail = f"offending={len(offending)}"
            if offending:
                detail += f", sample={offending[:3]}"
            inc_pass, inc_fail = record_result("article link integrity", ok, detail, fail_details)
            pass_count += inc_pass
            fail_count += inc_fail
        except Exception as exc:
            inc_pass, inc_fail = record_result("article link integrity", False, str(exc), fail_details)
            pass_count += inc_pass
            fail_count += inc_fail

        print("\nTest 6b: tracker cards keep same-language article integrity")
        try:
            link_audit = page.evaluate(
                """() => {
                    const isEnPage = window.location.pathname === '/en/predictions/' || window.location.pathname.startsWith('/en/');
                    const current = window.location.pathname;
                    const cards = Array.from(document.querySelectorAll('#np-inplay-list > details, #np-awaiting-list > details, #np-resolved-section > details'));
                    const offending = [];
                    const missing = [];

                    const toPath = (href) => {
                      try {
                        const url = new URL(href, window.location.origin);
                        return url.pathname + (url.hash || '');
                      } catch (e) {
                        return href || '';
                      }
                    };

                    for (const card of cards) {
                      const title = (card.querySelector('summary')?.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 140);
                      const anchors = Array.from(card.querySelectorAll('a[href]')).map((anchor) => {
                        const href = anchor.getAttribute('href') || '';
                        const path = toPath(href);
                        return {
                          href,
                          path,
                          text: (anchor.textContent || '').trim(),
                          cross: anchor.dataset.crossLangLink === 'true',
                        };
                      });

                      const sameLangAnchors = anchors.filter((item) => {
                        if (item.cross) return false;
                        if (item.path.startsWith('/predictions/#np-') || item.path.startsWith('/en/predictions/#np-')) return false;
                        if (isEnPage) return item.path.startsWith('/en/') && item.path !== current;
                        return item.path.startsWith('/') && !item.path.startsWith('/en/') && item.path !== current;
                      });

                      const badAnchors = anchors.filter((item) =>
                        item.cross ||
                        item.path.startsWith('/predictions/#np-') ||
                        item.path.startsWith('/en/predictions/#np-') ||
                        item.text.includes('View in tracker') ||
                        item.text.includes('トラッカーで見る')
                      );

                      if (badAnchors.length) {
                        offending.push({ title, anchors: badAnchors.slice(0, 3) });
                      }
                      if (!sameLangAnchors.length) {
                        missing.push({ title, anchors: anchors.slice(0, 3) });
                      }
                    }

                    return { cards: cards.length, offending, missing };
                }"""
            )
            ok = not link_audit["offending"] and not link_audit["missing"] and int(link_audit["cards"]) > 0
            detail = (
                f"cards={link_audit['cards']}, offending={len(link_audit['offending'])}, "
                f"missing_same_lang={len(link_audit['missing'])}"
            )
            if link_audit["offending"]:
                detail += f", offending_sample={link_audit['offending'][:2]}"
            if link_audit["missing"]:
                detail += f", missing_sample={link_audit['missing'][:2]}"
            inc_pass, inc_fail = record_result("same-language article integrity", ok, detail, fail_details)
            pass_count += inc_pass
            fail_count += inc_fail
        except Exception as exc:
            inc_pass, inc_fail = record_result("same-language article integrity", False, str(exc), fail_details)
            pass_count += inc_pass
            fail_count += inc_fail

        print("\nTest 7: sampled internal links resolve")
        try:
            link_samples = page.evaluate(
                """() => Array.from(document.querySelectorAll('a[href]'))
                  .filter((anchor) => anchor.dataset.crossLangLink !== 'true')
                  .map((anchor) => anchor.getAttribute('href') || '')
                  .filter((href) => href.startsWith('/') || href.includes('nowpattern.com'))"""
            )
            if not link_samples:
                inc_pass, inc_fail = record_result("internal links", False, "0 same-domain links found", fail_details)
                pass_count += inc_pass
                fail_count += inc_fail
            else:
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
                failed_links: list[str] = []
                checked = 0
                for href in link_samples[:8]:
                    if not href or href.startswith("#"):
                        continue
                    if href.startswith("/"):
                        href = urljoin(base_url, href)
                    ok, detail = check_internal_url(href, ssl_ctx)
                    checked += 1
                    if ok:
                        print(f"  OK {detail}: ...{href[-60:]}")
                    else:
                        print(f"  FAIL: {href} -> {detail}")
                        failed_links.append(f"{href} -> {detail}")
                ok = checked > 0 and not failed_links
                detail = f"checked={checked}, failed={len(failed_links)}"
                inc_pass, inc_fail = record_result("internal links", ok, detail, fail_details)
                pass_count += inc_pass
                fail_count += inc_fail
        except Exception as exc:
            inc_pass, inc_fail = record_result("internal links", False, str(exc), fail_details)
            pass_count += inc_pass
            fail_count += inc_fail

        if take_screenshot:
            ss_path = f"{SCREENSHOT_DIR}/{lang}-{device}-02-final.png"
            page.screenshot(path=ss_path, full_page=True)
            print(f"\n  Full screenshot: {ss_path}")

        browser.close()

    total = pass_count + fail_count
    print("\n" + "=" * 64)
    print(f"  E2E Summary ({lang.upper()} / {device.upper()}): {pass_count}/{total} PASS")
    if fail_count == 0:
        print("  ALL PASS")
    else:
        print(f"  FAILURES: {fail_count}")
        for msg in fail_details:
            print(f"     - {msg}")
    print("=" * 64 + "\n")
    return {
        "lang": lang,
        "device": device,
        "ok": fail_count == 0,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "fail_details": fail_details,
        "total": total,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Nowpattern prediction tracker E2E")
    parser.add_argument("--lang", choices=["ja", "en", "both"], default="ja")
    parser.add_argument("--device", choices=["desktop", "mobile", "both"], default="both")
    parser.add_argument("--screenshot", action="store_true")
    parser.add_argument("--json-out")
    args = parser.parse_args()

    langs = ["ja", "en"] if args.lang == "both" else [args.lang]
    devices = ["desktop", "mobile"] if args.device == "both" else [args.device]
    all_pass = True
    results: list[dict[str, object]] = []
    for lang in langs:
        for device in devices:
            result = run_tests(lang=lang, device=device, take_screenshot=args.screenshot)
            results.append(result)
            if not bool(result["ok"]):
                all_pass = False

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generated_at_epoch": int(datetime.now(timezone.utc).timestamp()),
            "results": results,
            "summary": {
                "total_runs": len(results),
                "failed_runs": sum(1 for item in results if not bool(item["ok"])),
                "passed_runs": sum(1 for item in results if bool(item["ok"])),
            },
            "ok": all_pass,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    raise SystemExit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
