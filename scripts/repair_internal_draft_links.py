#!/usr/bin/env python3
"""Audit and repair published internal links that point at dead or draft Ghost slugs."""

from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_GHOST_DB = Path("/var/www/nowpattern/content/data/ghost.db")
FIELDS_TO_SCAN = ("html", "codeinjection_head", "codeinjection_foot")
INTERNAL_URL_RE = re.compile(
    r"(?P<prefix>https?://nowpattern\.com|__GHOST_URL__)(?P<lang>/en)?(?:/(?P<legacy_prefix>genre-[a-z0-9-]+))?/(?P<slug>[a-z0-9-]+)/",
    re.IGNORECASE,
)
NUMERIC_SUFFIX_RE = re.compile(r"^(?P<base>.+?)-(?P<num>\d+)$")
ANCHOR_TEMPLATE = re.compile(
    r'<a\b(?P<pre>[^>]*?)href=["\'](?P<url>{url})["\'](?P<post>[^>]*)>(?P<label>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
IGNORED_ROUTE_PATHS = {
    "/tag/",
    "/author/",
    "/members/",
    "/rss/",
    "/webmentions/",
}


@dataclass
class RepairIssue:
    source_id: str
    source_slug: str
    source_type: str
    field: str
    target_slug: str
    replacement_slug: str | None
    original_url: str
    replacement_url: str | None
    target_reason: str
    anchor_label: str | None = None


def canonical_url_to_key(canonical_url: str | None) -> tuple[str, str] | None:
    if not canonical_url:
        return None
    parsed = urlparse(canonical_url)
    if parsed.netloc and parsed.netloc != "nowpattern.com":
        return None
    path = parsed.path or ""
    match = re.match(r"^(?P<lang>/en)?/(?P<slug>[a-z0-9-]+)/?$", path)
    if not match:
        return None
    return (match.group("lang") or "", match.group("slug"))


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", html.unescape(str(value)))
    text = text.lstrip(" \t\r\n→➡➜➝»&-–—:;,.")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_ignored_internal_route(original_url: str) -> bool:
    parsed = urlparse(original_url.replace("__GHOST_URL__", "https://nowpattern.com"))
    path = parsed.path or "/"
    if path in IGNORED_ROUTE_PATHS:
        return True
    if any(path.startswith(prefix) for prefix in ("/tag/", "/author/")):
        return True
    if path.startswith("/genre-"):
        segments = [segment for segment in path.split("/") if segment]
        return len(segments) <= 1
    return False


def fallback_url_for_slug(slug: str, lang_prefix: str) -> str:
    if lang_prefix == "/en":
        clean_slug = slug[3:] if slug.startswith("en-") else slug
        return f"https://nowpattern.com/en/{clean_slug}/"
    return f"https://nowpattern.com/{slug}/"


def normalize_internal_url(url: str) -> str:
    """Treat Ghost template placeholders as equivalent to the public origin."""
    return url.replace("__GHOST_URL__", "https://nowpattern.com").rstrip("/") + "/"


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def strip_numeric_suffix(slug: str) -> str:
    current = slug
    while True:
        match = NUMERIC_SUFFIX_RE.match(current)
        if not match:
            return current
        current = match.group("base")


def build_route_map(
    cur: sqlite3.Cursor,
) -> tuple[dict[tuple[str, str], str], dict[str, str], set[str], dict[str, list[tuple[str, str]]]]:
    columns = {str(row[1]) for row in cur.execute("PRAGMA table_info(posts)").fetchall()}
    has_canonical = "canonical_url" in columns
    route_map: dict[tuple[str, str], str] = {}
    published_slug_to_url: dict[str, str] = {}
    published_slugs: set[str] = set()
    title_to_routes: dict[str, list[tuple[str, str]]] = {}
    has_posts_tags = bool(cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_tags'"
    ).fetchone())
    has_tags = bool(cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tags'"
    ).fetchone())
    if has_posts_tags and has_tags:
        tag_sql = (
            "COALESCE(("
            "SELECT GROUP_CONCAT(t.slug, '|') "
            "FROM posts_tags pt "
            "JOIN tags t ON t.id = pt.tag_id "
            "WHERE pt.post_id = posts.id"
            "), '')"
        )
    else:
        tag_sql = "''"

    select_sql = (
        f"SELECT slug, title, {tag_sql} AS tag_slugs, canonical_url "
        f"FROM posts WHERE status = 'published'"
        if has_canonical
        else f"SELECT slug, title, {tag_sql} AS tag_slugs, NULL as canonical_url "
        f"FROM posts WHERE status = 'published'"
    )
    for slug, title, tag_blob, canonical_url in cur.execute(select_sql):
        if not slug:
            continue
        slug = str(slug)
        published_slugs.add(slug)
        tag_slugs = {part.strip().lower() for part in str(tag_blob or "").split("|") if part.strip()}
        lang_prefix = "/en" if (slug.startswith("en-") or "lang-en" in tag_slugs) else ""
        canonical_key = canonical_url_to_key(str(canonical_url) if canonical_url else None)
        if canonical_key:
            route_map[canonical_key] = str(canonical_url)
            published_slug_to_url[slug] = str(canonical_url)
        else:
            fallback = fallback_url_for_slug(slug, lang_prefix)
            published_slug_to_url[slug] = fallback
            key_slug = slug[3:] if slug.startswith("en-") else slug
            route_map.setdefault((lang_prefix, key_slug), fallback)
            route_map.setdefault(("", slug), fallback)
        normalized_title = normalize_title(title)
        if normalized_title:
            title_to_routes.setdefault(normalized_title, []).append((slug, published_slug_to_url[slug]))
    return route_map, published_slug_to_url, published_slugs, title_to_routes


def extract_anchor_label(content: str, original_url: str) -> str | None:
    anchor_re = re.compile(ANCHOR_TEMPLATE.pattern.format(url=re.escape(original_url)), re.IGNORECASE | re.DOTALL)
    match = anchor_re.search(content)
    if not match:
        return None
    return normalize_title(match.group("label"))


def choose_replacement_from_title(
    anchor_label: str | None,
    title_to_routes: dict[str, list[tuple[str, str]]],
) -> tuple[str | None, str | None]:
    normalized = normalize_title(anchor_label)
    if not normalized:
        return None, None

    exact = title_to_routes.get(normalized, [])
    if len(exact) == 1:
        slug, url = exact[0]
        return slug, url

    prefix_matches: list[tuple[str, str]] = []
    normalized_lower = normalized.lower()
    for title_key, routes in title_to_routes.items():
        title_lower = title_key.lower()
        if title_lower.startswith(normalized_lower) or normalized_lower.startswith(title_lower):
            prefix_matches.extend(routes)

    deduped: dict[str, str] = {}
    for slug, url in prefix_matches:
        deduped.setdefault(slug, url)
    if len(deduped) == 1:
        slug, url = next(iter(deduped.items()))
        return slug, url
    return None, None


def choose_replacement_url(
    target_slug: str,
    lang_prefix: str,
    route_map: dict[tuple[str, str], str],
    published_slug_to_url: dict[str, str],
    published_slugs: set[str],
) -> tuple[str | None, str | None]:
    candidate_keys: list[tuple[str, str]] = []

    def add_key(key: tuple[str, str]) -> None:
        if key not in candidate_keys:
            candidate_keys.append(key)

    add_key((lang_prefix, target_slug))
    add_key((lang_prefix, strip_numeric_suffix(target_slug)))

    if target_slug.startswith("en-"):
        clean = target_slug[3:]
        add_key(("/en", clean))
        add_key(("/en", strip_numeric_suffix(clean)))
        add_key(("", target_slug))
        add_key(("", strip_numeric_suffix(target_slug)))
    elif lang_prefix == "/en":
        add_key(("", f"en-{target_slug}"))
        add_key(("", f"en-{strip_numeric_suffix(target_slug)}"))
        add_key(("", target_slug))
        add_key(("", strip_numeric_suffix(target_slug)))

    for key in candidate_keys:
        url = route_map.get(key)
        if url:
            replacement_slug = key[1]
            return replacement_slug, url

    base = strip_numeric_suffix(target_slug)
    key_variants = [(lang_prefix, target_slug), (lang_prefix, base)]
    if target_slug.startswith("en-"):
        clean = target_slug[3:]
        key_variants.extend([("/en", clean), ("/en", strip_numeric_suffix(clean)), ("", target_slug), ("", base)])
    elif lang_prefix == "/en":
        key_variants.extend([("", f"en-{target_slug}"), ("", f"en-{base}"), ("", target_slug), ("", base)])

    candidate_urls: list[tuple[str, str]] = []
    for prefix, slug_key in key_variants:
        for (route_prefix, route_slug), url in route_map.items():
            if route_prefix != prefix:
                continue
            if route_slug.startswith(f"{slug_key}-"):
                candidate_urls.append((route_slug, url))
        for pub_slug, url in published_slug_to_url.items():
            if prefix == "" and pub_slug.startswith(f"{slug_key}-"):
                candidate_urls.append((pub_slug, url))

    deduped: dict[str, str] = {}
    for slug_key, url in candidate_urls:
        deduped.setdefault(slug_key, url)
    if len(deduped) == 1:
        slug_key, url = next(iter(deduped.items()))
        return slug_key, url
    if deduped:
        shortest = min(deduped, key=len)
        if sum(1 for slug_key in deduped if len(slug_key) == len(shortest)) == 1:
            return shortest, deduped[shortest]
    return None, None


def discover_issues(cur: sqlite3.Cursor) -> list[RepairIssue]:
    route_map, published_slug_to_url, published_slugs, title_to_routes = build_route_map(cur)
    draft_slugs = {
        str(row[0])
        for row in cur.execute("SELECT slug FROM posts WHERE status = 'draft'")
        if row[0]
    }
    issues: list[RepairIssue] = []
    rows = cur.execute(
        """
        SELECT id, slug, type, html, codeinjection_head, codeinjection_foot
        FROM posts
        WHERE status = 'published'
        ORDER BY published_at DESC, created_at DESC
        """
    ).fetchall()
    for row in rows:
        source_id = str(row[0])
        source_slug = str(row[1])
        source_type = str(row[2])
        field_values = dict(zip(FIELDS_TO_SCAN, row[3:6], strict=True))
        for field_name, value in field_values.items():
            if not value:
                continue
            seen: set[tuple[str, str]] = set()
            for match in INTERNAL_URL_RE.finditer(str(value)):
                target_slug = match.group("slug")
                original_url = match.group(0)
                if is_ignored_internal_route(original_url):
                    continue
                key = (field_name, target_slug)
                if key in seen:
                    continue
                seen.add(key)
                lang_prefix = match.group("lang") or ""
                anchor_label = extract_anchor_label(str(value), original_url) if field_name == "html" else None
                replacement_slug, replacement_url = choose_replacement_url(
                    target_slug,
                    lang_prefix,
                    route_map,
                    published_slug_to_url,
                    published_slugs,
                )
                normalized_original = normalize_internal_url(original_url)
                normalized_replacement = normalize_internal_url(replacement_url) if replacement_url else None
                if target_slug in draft_slugs:
                    reason = "draft_slug"
                elif target_slug in published_slugs:
                    if replacement_url is None or normalized_replacement == normalized_original:
                        continue
                    reason = "canonical_drift"
                else:
                    reason = "missing_slug"
                    replacement_slug, replacement_url = choose_replacement_from_title(anchor_label, title_to_routes)
                    if replacement_url is None:
                        replacement_slug, replacement_url = choose_replacement_url(
                            target_slug,
                            lang_prefix,
                            route_map,
                            published_slug_to_url,
                            published_slugs,
                        )
                    normalized_replacement = normalize_internal_url(replacement_url) if replacement_url else None
                if replacement_url and normalized_replacement == normalized_original:
                    continue
                issues.append(
                    RepairIssue(
                        source_id=source_id,
                        source_slug=source_slug,
                        source_type=source_type,
                        field=field_name,
                        target_slug=target_slug,
                        replacement_slug=replacement_slug,
                        original_url=original_url,
                        replacement_url=replacement_url,
                        target_reason=reason,
                        anchor_label=anchor_label,
                    )
                )
    return issues


def apply_repairs(cur: sqlite3.Cursor, issues: list[RepairIssue]) -> int:
    grouped: dict[tuple[str, str], list[RepairIssue]] = {}
    for issue in issues:
        grouped.setdefault((issue.source_id, issue.field), []).append(issue)

    repaired = 0
    for (source_id, field_name), field_issues in grouped.items():
        row = cur.execute(f"SELECT {field_name} FROM posts WHERE id = ?", (source_id,)).fetchone()
        if not row or row[0] is None:
            continue
        content = str(row[0])
        original = content
        for issue in field_issues:
            if issue.replacement_url:
                content = content.replace(issue.original_url, issue.replacement_url)
                continue
            if field_name == "html":
                anchor_re = re.compile(ANCHOR_TEMPLATE.pattern.format(url=re.escape(issue.original_url)), re.IGNORECASE | re.DOTALL)
                content = anchor_re.sub(lambda m: f"<span data-removed-draft-link=\"true\">{m.group('label')}</span>", content)
            else:
                content = content.replace(issue.original_url, "")
        if content != original:
            cur.execute(f"UPDATE posts SET {field_name} = ? WHERE id = ?", (content, source_id))
            repaired += 1
    return repaired


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Repair published internal links that point at draft or dead slugs.")
    parser.add_argument("--db", default=str(DEFAULT_GHOST_DB), help="Path to ghost.db")
    parser.add_argument("--audit-only", action="store_true", help="Only report issues and exit non-zero if any remain")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise FileNotFoundError(f"ghost db not found: {db_path}")

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    before = discover_issues(cur)
    repaired = 0
    if not args.audit_only:
        repaired = apply_repairs(cur, before)
        if repaired:
            con.commit()
    after = discover_issues(cur)
    con.close()

    unresolved = [issue for issue in after if issue.replacement_slug is None]
    report = {
        "db": str(db_path),
        "issues_before": len(before),
        "repaired_fields": repaired,
        "issues_after": len(after),
        "unresolved_after": len(unresolved),
        "samples_before": [asdict(issue) for issue in before[:20]],
        "samples_after": [asdict(issue) for issue in after[:20]],
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if len(after) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
