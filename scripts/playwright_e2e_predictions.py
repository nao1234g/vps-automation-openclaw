#!/usr/bin/env python3
"""Prediction tracker E2E checks for Nowpattern JA/EN pages."""

from __future__ import annotations

import argparse
import ssl
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path


PREDICTIONS_URL_JA = "https://nowpattern.com/predictions/"
PREDICTIONS_URL_EN = "https://nowpattern.com/en/predictions/"
SCREENSHOT_DIR = "/opt/shared/reports/e2e-screenshots"
TIMEOUT = 20000
CARDS_PER_PAGE = 50


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


def tracker_card_counts(page) -> tuple[int, int, int]:
    total, visible = page.evaluate(
        """() => {
          const cards = Array.from(document.querySelectorAll('#np-tracking-list details'));
          const visible = cards.filter((card) => {
            const style = window.getComputedStyle(card);
            return style.display !== 'none' && style.visibility !== 'hidden';
          }).length;
          return [cards.length, visible];
        }"""
    )
    return total, visible, max(0, total - visible)


def tracker_category_counts(page) -> dict[str, int]:
    return page.evaluate(
        """() => {
          const counts = {};
          for (const card of document.querySelectorAll('#np-tracking-list details')) {
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


def run_tests(lang: str = "ja", take_screenshot: bool = False) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed.")
        print("Run: pip3 install playwright && playwright install chromium")
        return False

    base_url = PREDICTIONS_URL_JA if lang == "ja" else PREDICTIONS_URL_EN
    fail_details: list[str] = []
    pass_count = 0
    fail_count = 0

    print("\n" + "=" * 60)
    print(f"  Nowpattern Prediction Tracker E2E ({lang.upper()})")
    print(f"  URL: {base_url}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M JST')}")
    print("=" * 60 + "\n")

    Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )
        page = ctx.new_page()
        page.set_default_timeout(TIMEOUT)

        print("Test 0: page load")
        try:
            resp = goto_with_retry(page, base_url, wait_until="domcontentloaded")
            status = resp.status if resp else 0
            if status < 400:
                print(f"  PASS: HTTP {status}")
                pass_count += 1
            else:
                print(f"  FAIL: HTTP {status}")
                fail_count += 1
                fail_details.append(f"page load HTTP {status}")
                browser.close()
                return False
        except Exception as exc:
            print(f"  FAIL: {exc}")
            fail_count += 1
            fail_details.append(f"page load {exc}")
            browser.close()
            return False

        if take_screenshot:
            ss_path = f"{SCREENSHOT_DIR}/{lang}-01-initial.png"
            page.screenshot(path=ss_path, full_page=False)
            print(f"  Screenshot: {ss_path}")

        print("\nTest 1: tracking cards visible")
        try:
            page.wait_for_selector("#np-tracking-list details", timeout=TIMEOUT)
            card_count = page.locator("#np-tracking-list details").count()
            if card_count > 0:
                print(f"  PASS: {card_count} cards rendered")
                pass_count += 1
            else:
                print("  FAIL: 0 cards rendered")
                fail_count += 1
                fail_details.append("tracking cards: 0 rendered")
        except Exception as exc:
            print(f"  FAIL: {exc}")
            fail_count += 1
            fail_details.append(f"tracking cards: {exc}")

        print("\nTest 2: impossible keyword hides all cards")
        try:
            search_box = page.locator("#np-search")
            search_box.wait_for(state="visible", timeout=TIMEOUT)

            initial_total, initial_visible, _ = tracker_card_counts(page)
            print(f"  Initial cards: total={initial_total}, visible={initial_visible}")
            if initial_total == 0:
                print("  FAIL: no cards available before search")
                fail_count += 1
                fail_details.append("search filter: initial card count is 0")
            else:
                search_box.fill("zzzxxx_nonexistent_9999")
                time.sleep(0.8)
                total_after, visible_after, hidden_after = tracker_card_counts(page)
                if visible_after == 0 and hidden_after == initial_total:
                    print(f"  PASS: impossible query hides all cards ({initial_total} -> 0 visible)")
                    pass_count += 1
                else:
                    print(f"  FAIL: total={total_after}, visible={visible_after}, hidden={hidden_after}")
                    fail_count += 1
                    fail_details.append(
                        f"search filter: expected 0 visible after impossible query, got visible={visible_after} hidden={hidden_after} total={total_after}"
                    )

                search_box.fill("")
                time.sleep(0.3)
        except Exception as exc:
            print(f"  FAIL: {exc}")
            fail_count += 1
            fail_details.append(f"search filter: {exc}")

        print("\nTest 3: category filter returns a real subset")
        try:
            cat_buttons = page.locator(".np-cat-btn")
            btn_count = cat_buttons.count()
            print(f"  Category buttons: {btn_count}")

            if btn_count < 2:
                print(f"  FAIL: category buttons missing ({btn_count})")
                fail_count += 1
                fail_details.append(f"category filter: too few buttons ({btn_count})")
            else:
                initial_total, _, _ = tracker_card_counts(page)
                category_counts = tracker_category_counts(page)
                clicked = False

                for i in range(btn_count):
                    btn = cat_buttons.nth(i)
                    cat_val = btn.get_attribute("data-cat")
                    expected_matches = int(category_counts.get(cat_val or "", 0))
                    if not cat_val or cat_val == "all":
                        continue
                    if expected_matches <= 0 or expected_matches >= initial_total:
                        continue

                    btn.click()
                    time.sleep(0.6)
                    active_bg = btn.evaluate("el => el.style.background")
                    total_after, visible_after, hidden_after = tracker_card_counts(page)
                    expected_visible = min(expected_matches, CARDS_PER_PAGE)
                    print(
                        f"  category '{cat_val}': visible={visible_after}, hidden={hidden_after}, "
                        f"expected_matches={expected_matches}, expected_visible<={expected_visible}"
                    )
                    print(f"  Active style: {active_bg}")

                    if visible_after <= 0:
                        print(f"  FAIL: category '{cat_val}' returned 0 visible cards")
                        fail_count += 1
                        fail_details.append(f"category filter: {cat_val} visible=0 expected={expected_matches}")
                    elif visible_after > expected_visible:
                        print(f"  FAIL: category '{cat_val}' visible count too high")
                        fail_count += 1
                        fail_details.append(
                            f"category filter: {cat_val} visible={visible_after} expected_visible={expected_visible}"
                        )
                    elif hidden_after <= 0:
                        print(f"  FAIL: category '{cat_val}' hid 0 cards")
                        fail_count += 1
                        fail_details.append(f"category filter: {cat_val} hid 0 cards")
                    else:
                        print(f"  PASS: category '{cat_val}' filtered to a real subset")
                        pass_count += 1

                    cat_buttons.first.click()
                    time.sleep(0.3)
                    clicked = True
                    break

                if not clicked:
                    print(f"  FAIL: no filterable category found (counts={category_counts})")
                    fail_count += 1
                    fail_details.append(f"category filter: no filterable category found {category_counts}")
        except Exception as exc:
            print(f"  FAIL: {exc}")
            fail_count += 1
            fail_details.append(f"category filter: {exc}")

        print("\nTest 4: sampled internal links resolve")
        try:
            article_links = page.locator("a[href*='nowpattern.com']")
            link_count = article_links.count()
            print(f"  Internal links: {link_count}")

            if link_count == 0:
                print("  SKIP: no same-domain links found in tracker")
            else:
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

                failed_links = []
                max_check = min(link_count, 10)

                for i in range(max_check):
                    href = article_links.nth(i).get_attribute("href")
                    if not href or href.startswith("#"):
                        continue
                    ok, detail = check_internal_url(href, ssl_ctx)
                    if ok:
                        print(f"  OK {detail}: ...{href[-50:]}")
                    else:
                        print(f"  FAIL: {href} -> {detail}")
                        failed_links.append((href, detail))

                if failed_links:
                    print(f"  FAIL: {len(failed_links)} links failed")
                    fail_count += 1
                    fail_details.append(f"internal links: {len(failed_links)} failed")
                else:
                    print(f"  PASS: {max_check} sampled links resolved")
                    pass_count += 1
        except Exception as exc:
            print(f"  FAIL: {exc}")
            fail_count += 1
            fail_details.append(f"internal links: {exc}")

        if take_screenshot:
            ss_path = f"{SCREENSHOT_DIR}/{lang}-02-final.png"
            page.screenshot(path=ss_path, full_page=True)
            print(f"\n  Full screenshot: {ss_path}")

        print("")
        print("Test 5: market/no-market contradictions absent")
        try:
            import re as _re

            cards = page.locator("#np-tracking-list > details").all()
            contradictions = []
            no_market_label = "市場データなし"
            for card in cards:
                html = card.inner_html()
                has_no_market = ("Nowpattern独自分析" in html) or (no_market_label in html)
                has_market_prob = any(token in html for token in ["Polymarket", "Metaculus", "Manifold"])
                if has_no_market and has_market_prob:
                    match = _re.search(r"data-pred=.?(NP-[0-9]{4}-[0-9]{4})", html)
                    contradictions.append(match.group(1) if match else "unknown")

            if contradictions:
                print(f"  FAIL: contradictions found in {len(contradictions)} cards: {contradictions}")
                fail_count += 1
                fail_details.append(f"market contradiction: {len(contradictions)} cards")
            else:
                print(f"  PASS: no contradictions ({len(cards)} cards checked)")
                pass_count += 1
        except Exception as exc:
            print(f"  FAIL: {exc}")
            fail_count += 1
            fail_details.append(f"market contradiction: {exc}")

        browser.close()

    total = pass_count + fail_count
    print("\n" + "=" * 60)
    print(f"  E2E Summary ({lang.upper()}): {pass_count}/{total} PASS")
    if fail_count == 0:
        print("  ALL PASS")
    else:
        print(f"  FAILURES: {fail_count}")
        for msg in fail_details:
            print(f"     - {msg}")
    print("=" * 60 + "\n")

    return fail_count == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Nowpattern prediction tracker E2E")
    parser.add_argument("--lang", choices=["ja", "en", "both"], default="ja")
    parser.add_argument("--screenshot", action="store_true")
    args = parser.parse_args()

    all_pass = True
    langs = ["ja", "en"] if args.lang == "both" else [args.lang]
    for lang in langs:
        if not run_tests(lang=lang, take_screenshot=args.screenshot):
            all_pass = False

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
