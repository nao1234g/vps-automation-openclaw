#!/usr/bin/env python3
"""Regression tests for article source audit behavior."""

from __future__ import annotations

from site_article_source_audit import ArticleAuditResult, extract_article_scope, extract_external_links, is_stale_article_result


def test_extract_article_scope_ignores_footer_links() -> None:
    html = """
    <html><body>
      <article class="gh-article">
        <p><a href="https://example.com/source-one">Source One</a></p>
      </article>
      <footer><a href="https://ghost.org/">Powered by Ghost</a></footer>
    </body></html>
    """
    scoped = extract_article_scope(html)
    links = extract_external_links("https://nowpattern.com/", scoped)
    assert links == ["https://example.com/source-one"], links


def test_stale_article_result_detects_dead_rotation_paths() -> None:
    result = ArticleAuditResult(
        slug="dead-path",
        url="https://nowpattern.com/dead-path/",
        ok=False,
        errors=["article_fetch_failed:HTTP Error 404: Not Found"],
    )
    assert is_stale_article_result(result) is True

    live_issue = ArticleAuditResult(
        slug="bad-source",
        url="https://nowpattern.com/live/",
        ok=False,
        errors=["broken_source:https://example.com -> HTTP Error 404: Not Found"],
    )
    assert is_stale_article_result(live_issue) is False


def run() -> None:
    test_extract_article_scope_ignores_footer_links()
    test_stale_article_result_detects_dead_rotation_paths()
    print("PASS: site_article_source_audit regression checks")


if __name__ == "__main__":
    run()
