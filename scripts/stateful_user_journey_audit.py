#!/usr/bin/env python3
"""Exercise stateful public user journeys in a single browser context."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


TIMEOUT = 20000
TRACKER_URLS = {
    "ja": "https://nowpattern.com/predictions/",
    "en": "https://nowpattern.com/en/predictions/",
}


def goto_with_retry(page, url: str):
    last_error = None
    for timeout_ms in (30000, 60000):
        try:
            return page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception as exc:  # pragma: no cover - exercised in live audit
            last_error = exc
            page.wait_for_timeout(1000)
    raise last_error


def _journey_result(name: str, ok: bool, detail: str) -> dict[str, object]:
    return {"name": name, "ok": ok, "detail": detail}


def _first_same_lang_article_href(page, lang: str) -> str | None:
    return page.evaluate(
        """(lang) => {
          const currentIsEn = lang === 'en';
          const cards = Array.from(document.querySelectorAll('#np-inplay-list > details, #np-awaiting-list > details, #np-resolved-section > details'));
          const normalize = (href) => {
            try {
              const url = new URL(href, window.location.origin);
              return url.pathname + (url.hash || '');
            } catch (e) {
              return href || '';
            }
          };
          const isVisible = (node) => {
            const style = window.getComputedStyle(node);
            return style.display !== 'none' && style.visibility !== 'hidden';
          };
          for (let cardIndex = 0; cardIndex < cards.length; cardIndex += 1) {
            if (!isVisible(cards[cardIndex])) continue;
            const anchors = Array.from(cards[cardIndex].querySelectorAll('a[href]'));
            for (let anchorIndex = 0; anchorIndex < anchors.length; anchorIndex += 1) {
              const anchor = anchors[anchorIndex];
              if (!isVisible(anchor)) continue;
              if (anchor.dataset.crossLangLink === 'true') continue;
              const path = normalize(anchor.getAttribute('href') || '');
              if (!path || path.startsWith('/predictions/#') || path.startsWith('/en/predictions/#')) continue;
              if (currentIsEn) {
                if (!path.startsWith('/en/') || path === '/en/predictions/') continue;
              } else {
                if (path.startsWith('/en/') || path === '/predictions/') continue;
              }
              return anchor.href || null;
            }
          }
          return null;
        }""",
        lang,
    )


def run_audit(base_url: str) -> dict[str, object]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generated_at_epoch": int(datetime.now(timezone.utc).timestamp()),
            "base_url": base_url.rstrip("/"),
            "total": 1,
            "failed": 1,
            "results": [_journey_result("playwright_import", False, "playwright_not_installed")],
        }

    results: list[dict[str, object]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(ignore_https_errors=True, viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(TIMEOUT)

        try:
            for lang in ("ja", "en"):
                tracker_url = TRACKER_URLS[lang].replace("https://nowpattern.com", base_url.rstrip("/"))
                resp = goto_with_retry(page, tracker_url)
                results.append(_journey_result(f"{lang}_tracker_load", bool(resp and resp.status < 400), f"status={resp.status if resp else 0}"))

                page.wait_for_function(
                    "() => document.querySelectorAll('#np-inplay-list details, #np-awaiting-list details, #np-resolved-section details').length > 0",
                    timeout=TIMEOUT,
                )
                search_box = page.locator("#np-search")
                search_box.fill("zzz_stateful_probe_999")
                page.wait_for_timeout(400)
                hidden_count = page.evaluate(
                    """() => Array.from(document.querySelectorAll('#np-inplay-list details, #np-awaiting-list details, #np-resolved-section details'))
                        .filter((card) => window.getComputedStyle(card).display === 'none').length"""
                )
                search_box.fill("")
                page.wait_for_timeout(250)
                results.append(_journey_result(f"{lang}_search_state", hidden_count > 0, f"hidden_after_filter={hidden_count}"))

                href = _first_same_lang_article_href(page, lang)
                if not href:
                    results.append(_journey_result(f"{lang}_same_lang_article_link", False, "no_same_language_article_link_found"))
                    continue

                goto_with_retry(page, href)
                current_path = page.evaluate("() => window.location.pathname")
                path_ok = current_path not in ("/predictions/", "/en/predictions/") and (current_path.startswith("/en/") if lang == "en" else not current_path.startswith("/en/"))
                results.append(_journey_result(f"{lang}_article_open", path_ok, f"href={href} path={current_path}"))

                page.go_back(wait_until="domcontentloaded", timeout=TIMEOUT)
                returned_path = page.evaluate("() => window.location.pathname")
                results.append(_journey_result(f"{lang}_return_to_tracker", returned_path == ("/en/predictions/" if lang == "en" else "/predictions/"), f"path={returned_path}"))
        finally:
            browser.close()

    failed = sum(1 for item in results if not item["ok"])
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_epoch": int(datetime.now(timezone.utc).timestamp()),
        "base_url": base_url.rstrip("/"),
        "total": len(results),
        "failed": failed,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run stateful anonymous user journeys against public tracker/article flows.")
    parser.add_argument("--base-url", default="https://nowpattern.com")
    parser.add_argument("--json-out")
    args = parser.parse_args()

    report = run_audit(args.base_url)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
