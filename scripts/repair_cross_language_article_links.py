#!/usr/bin/env python3
"""Repair silent cross-language internal article links in published Ghost HTML."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_GHOST_DB = Path("/var/www/nowpattern/content/data/ghost.db")
FIELDS_TO_SCAN = ("html",)
ANCHOR_RE = re.compile(
    r'<a\b(?P<pre>[^>]*?)href=["\'](?P<url>(?:https?://(?:www\.)?nowpattern\.com|__GHOST_URL__)[^"\']+)["\'](?P<post>[^>]*)>(?P<label>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
ARTICLE_ROUTE_RE = re.compile(r"^(?P<lang>/en)?/(?P<slug>[a-z0-9-]+)/?$", re.IGNORECASE)


@dataclass
class CrossLangIssue:
    source_id: str
    source_slug: str
    source_lang: str
    field: str
    original_url: str
    target_slug: str
    target_lang: str | None
    replacement_url: str | None
    action: str
    reason: str
    anchor_label: str


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def canonical_public_url(slug: str, lang: str) -> str:
    clean_slug = slug[3:] if slug.startswith("en-") else slug
    if lang == "en":
        return f"https://nowpattern.com/en/{clean_slug}/"
    return f"https://nowpattern.com/{slug}/"


def parse_internal_article_url(url: str) -> tuple[str | None, str | None]:
    parsed = urlparse(url.replace("__GHOST_URL__", "https://nowpattern.com"))
    if parsed.netloc and parsed.netloc != "nowpattern.com":
        return None, None
    match = ARTICLE_ROUTE_RE.match(parsed.path or "")
    if not match:
        return None, None
    return ("en" if match.group("lang") else "ja"), match.group("slug")


def normalize_label(label: str) -> str:
    text = re.sub(r"<[^>]+>", " ", label or "")
    return re.sub(r"\s+", " ", text).strip()


def strip_cross_lang_attr(attrs: str) -> str:
    return re.sub(r"\sdata-cross-lang-link=(['\"]).*?\1", "", attrs, flags=re.IGNORECASE)


def add_cross_lang_attr(attrs: str) -> str:
    if re.search(r"\bdata-cross-lang-link=", attrs, flags=re.IGNORECASE):
        return attrs
    return attrs + ' data-cross-lang-link="true"'


def append_lang_marker(label: str, target_lang: str | None) -> str:
    marker = " (EN)" if target_lang == "en" else " (日本語)" if target_lang == "ja" else ""
    if not marker:
        return label
    if marker.lower() in label.lower():
        return label
    return f"{label}{marker}"


def post_rows(cur: sqlite3.Cursor) -> list[tuple[str, str, str, str, str]]:
    return list(
        cur.execute(
            """
            SELECT
              p.id,
              p.slug,
              COALESCE(GROUP_CONCAT(t.slug, '|'), ''),
              COALESCE(p.html, ''),
              p.status
            FROM posts p
            LEFT JOIN posts_tags pt ON pt.post_id = p.id
            LEFT JOIN tags t ON t.id = pt.tag_id
            WHERE p.type = 'post'
            GROUP BY p.id, p.slug, p.html, p.status
            ORDER BY p.published_at DESC, p.created_at DESC
            """
        )
    )


def build_post_maps(cur: sqlite3.Cursor) -> tuple[dict[str, dict[str, str]], dict[str, str], dict[str, str]]:
    meta_by_slug: dict[str, dict[str, str]] = {}
    ja_by_clean_slug: dict[str, str] = {}
    en_by_clean_slug: dict[str, str] = {}
    for _, slug, tag_blob, _, status in post_rows(cur):
        if status != "published" or not slug:
            continue
        tag_slugs = {part.strip().lower() for part in str(tag_blob or "").split("|") if part.strip()}
        lang = "en" if "lang-en" in tag_slugs or str(slug).startswith("en-") else "ja"
        canonical = canonical_public_url(str(slug), lang)
        meta_by_slug[str(slug)] = {"lang": lang, "canonical_url": canonical}
        clean_slug = str(slug)[3:] if str(slug).startswith("en-") else str(slug)
        if lang == "en":
            en_by_clean_slug.setdefault(clean_slug, canonical)
        else:
            ja_by_clean_slug.setdefault(clean_slug, canonical)
    return meta_by_slug, ja_by_clean_slug, en_by_clean_slug


def resolve_target_language(
    target_slug: str,
    target_prefix_lang: str,
    meta_by_slug: dict[str, dict[str, str]],
    ja_by_clean_slug: dict[str, str],
    en_by_clean_slug: dict[str, str],
) -> tuple[str | None, str | None]:
    if target_prefix_lang == "en":
        clean_slug = target_slug[3:] if target_slug.startswith("en-") else target_slug
        canonical = en_by_clean_slug.get(clean_slug)
        if canonical:
            return "en", canonical
        canonical = en_by_clean_slug.get(target_slug)
        if canonical:
            return "en", canonical
        canonical = ja_by_clean_slug.get(target_slug)
        if canonical:
            return "ja", canonical
        return None, None

    meta = meta_by_slug.get(target_slug)
    if meta:
        return meta["lang"], meta["canonical_url"]
    canonical = en_by_clean_slug.get(target_slug)
    if canonical:
        return "en", canonical
    canonical = ja_by_clean_slug.get(target_slug)
    if canonical:
        return "ja", canonical
    return None, None


def desired_same_language_url(
    source_lang: str,
    target_slug: str,
    ja_by_clean_slug: dict[str, str],
    en_by_clean_slug: dict[str, str],
) -> str | None:
    clean_slug = target_slug[3:] if target_slug.startswith("en-") else target_slug
    if source_lang == "en":
        return en_by_clean_slug.get(clean_slug)
    return ja_by_clean_slug.get(clean_slug)


def discover_issues(cur: sqlite3.Cursor) -> list[CrossLangIssue]:
    meta_by_slug, ja_by_clean_slug, en_by_clean_slug = build_post_maps(cur)
    issues: list[CrossLangIssue] = []
    for source_id, source_slug, tag_blob, html, status in post_rows(cur):
        if status != "published" or not html or not source_slug:
            continue
        source_tags = {part.strip().lower() for part in str(tag_blob or "").split("|") if part.strip()}
        source_lang = "en" if "lang-en" in source_tags or str(source_slug).startswith("en-") else "ja"
        seen: set[tuple[str, str]] = set()
        for match in ANCHOR_RE.finditer(str(html)):
            original_url = match.group("url")
            attr_blob = f'{match.group("pre")} {match.group("post")}'
            if re.search(r"\bdata-cross-lang-link=", attr_blob, flags=re.IGNORECASE):
                continue
            target_prefix_lang, target_slug = parse_internal_article_url(original_url)
            if not target_slug:
                continue
            issue_key = ("html", original_url)
            if issue_key in seen:
                continue
            seen.add(issue_key)
            target_lang, target_canonical = resolve_target_language(
                target_slug,
                target_prefix_lang or "ja",
                meta_by_slug,
                ja_by_clean_slug,
                en_by_clean_slug,
            )
            desired_url = desired_same_language_url(source_lang, target_slug, ja_by_clean_slug, en_by_clean_slug)
            anchor_label = normalize_label(match.group("label"))
            normalized_original = original_url.rstrip("/") + "/"
            if desired_url:
                desired_url = desired_url.rstrip("/") + "/"
                if desired_url != normalized_original:
                    issues.append(
                        CrossLangIssue(
                            source_id=str(source_id),
                            source_slug=str(source_slug),
                            source_lang=source_lang,
                            field="html",
                            original_url=original_url,
                            target_slug=target_slug,
                            target_lang=target_lang,
                            replacement_url=desired_url,
                            action="replace_same_language",
                            reason="same_language_canonical",
                            anchor_label=anchor_label,
                        )
                    )
                continue
            if target_lang and target_lang != source_lang:
                replacement = (target_canonical or original_url).rstrip("/") + "/"
                issues.append(
                    CrossLangIssue(
                        source_id=str(source_id),
                        source_slug=str(source_slug),
                        source_lang=source_lang,
                        field="html",
                        original_url=original_url,
                        target_slug=target_slug,
                        target_lang=target_lang,
                        replacement_url=replacement,
                        action="annotate_cross_language",
                        reason="no_same_language_sibling",
                        anchor_label=anchor_label,
                    )
                )
                continue
            if target_canonical:
                replacement = target_canonical.rstrip("/") + "/"
                if replacement != normalized_original:
                    issues.append(
                        CrossLangIssue(
                            source_id=str(source_id),
                            source_slug=str(source_slug),
                            source_lang=source_lang,
                            field="html",
                            original_url=original_url,
                            target_slug=target_slug,
                            target_lang=target_lang,
                            replacement_url=replacement,
                            action="canonicalize_target",
                            reason="target_canonical_drift",
                            anchor_label=anchor_label,
                        )
                    )
        # end anchors
    return issues


def apply_issues(cur: sqlite3.Cursor, issues: list[CrossLangIssue]) -> int:
    grouped: dict[str, dict[str, CrossLangIssue]] = {}
    for issue in issues:
        grouped.setdefault(issue.source_id, {})[issue.original_url] = issue

    repaired = 0
    for source_id, issue_map in grouped.items():
        row = cur.execute("SELECT html FROM posts WHERE id = ?", (source_id,)).fetchone()
        if not row or row[0] is None:
            continue
        content = str(row[0])
        original = content

        def repl(match: re.Match[str]) -> str:
            issue = issue_map.get(match.group("url"))
            if not issue:
                return match.group(0)
            attrs = strip_cross_lang_attr(f'{match.group("pre")}href="{match.group("url")}"{match.group("post")}')
            if issue.replacement_url:
                attrs = attrs.replace(match.group("url"), issue.replacement_url, 1)
            label = match.group("label")
            if issue.action == "annotate_cross_language":
                attrs = add_cross_lang_attr(attrs)
                label = append_lang_marker(label, issue.target_lang)
            return f"<a{attrs}>{label}</a>"

        content = ANCHOR_RE.sub(repl, content)
        if content != original:
            cur.execute("UPDATE posts SET html = ? WHERE id = ?", (content, source_id))
            repaired += 1
    return repaired


def main() -> int:
    ensure_stdout_utf8()
    parser = argparse.ArgumentParser(description="Repair silent cross-language internal article links in published Ghost HTML.")
    parser.add_argument("--db", default=str(DEFAULT_GHOST_DB), help="Path to ghost.db")
    parser.add_argument("--audit-only", action="store_true", help="Report issues without writing changes")
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
        repaired = apply_issues(cur, before)
        if repaired:
            con.commit()
    after = discover_issues(cur)
    con.close()

    report = {
        "db": str(db_path),
        "issues_before": len(before),
        "repaired_posts": repaired,
        "issues_after": len(after),
        "cross_language_after": sum(1 for item in after if item.action == "annotate_cross_language"),
        "same_language_replacements_after": sum(1 for item in after if item.action == "replace_same_language"),
        "samples_before": [asdict(item) for item in before[:20]],
        "samples_after": [asdict(item) for item in after[:20]],
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
    return 0 if len(after) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
