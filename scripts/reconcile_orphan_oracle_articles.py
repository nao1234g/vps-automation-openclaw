#!/usr/bin/env python3
"""Reconcile published orphan oracle articles with prediction_db or downgrade them to analysis-only.

This script does two safety-preserving things:
1. If an orphan `np-oracle` article exactly matches a prediction question, relink that prediction.
2. If no unique prediction match exists, strip the public oracle block so the article stops pretending
   to belong to the prediction graph.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = REPO_ROOT / "scripts" / "prediction_db.json"
DEFAULT_GHOST_DB = Path("/var/www/nowpattern/content/data/ghost.db")

QUESTION_PATTERNS = (
    re.compile(
        r"(?:予測質問|Prediction Question)\s*[:：]?\s*<strong>(.*?)</strong>",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"<strong>\s*(?:予測質問|Prediction Question)\s*</strong>\s*[:：]?\s*(.*?)(?:</p>|<br\s*/?>)",
        re.IGNORECASE | re.DOTALL,
    ),
)
TAG_RE = re.compile(r"<[^>]+>")
DIV_TOKEN_RE = re.compile(r"</?div\b", re.IGNORECASE)
ORACLE_OPEN_RE = re.compile(
    r"<div\b[^>]*(?:\bid=(['\"])np-oracle\1|\bclass=(['\"])[^>]*\bnp-oracle\b[^>]*\2)[^>]*>",
    re.IGNORECASE,
)
TRAILING_HR_RE = re.compile(r"\s*<hr[^>]*>\s*$", re.IGNORECASE)
LEADING_HR_RE = re.compile(r"^\s*<hr[^>]*>\s*", re.IGNORECASE)


def strip_tags(text: str) -> str:
    return TAG_RE.sub(" ", text or "")


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", strip_tags(text or "")).lower()
    value = re.sub(r"[^\w\u3040-\u30ff\u3400-\u9fff]+", "", value)
    return value


def infer_public_url(slug: str, tag_slugs: set[str]) -> str:
    if "lang-en" in tag_slugs and slug.startswith("en-"):
        return f"https://nowpattern.com/en/{slug[3:]}/"
    if "lang-en" in tag_slugs:
        return f"https://nowpattern.com/en/{slug}/"
    return f"https://nowpattern.com/{slug}/"


def infer_lang(slug: str, tag_slugs: set[str]) -> str:
    if "lang-en" in tag_slugs or slug.startswith("en-"):
        return "en"
    return "ja"


def extract_oracle_question(html: str) -> str:
    for pattern in QUESTION_PATTERNS:
        match = pattern.search(html or "")
        if match:
            return " ".join(strip_tags(match.group(1)).split()).strip()
    return ""


def find_oracle_block_bounds(html: str) -> tuple[int, int] | None:
    match = ORACLE_OPEN_RE.search(html or "")
    if not match:
        return None
    start = match.start()
    idx = match.end()
    depth = 1
    while depth > 0:
        token = DIV_TOKEN_RE.search(html, idx)
        if not token:
            return None
        if token.group(0).startswith("</"):
            depth -= 1
        else:
            depth += 1
        idx = token.end()
    return start, idx


def strip_oracle_block(html: str) -> str:
    bounds = find_oracle_block_bounds(html)
    if not bounds:
        return html
    start, end = bounds
    prefix = html[:start]
    suffix = html[end:]
    prefix = TRAILING_HR_RE.sub("", prefix)
    suffix = LEADING_HR_RE.sub("", suffix)
    return prefix.rstrip() + "\n\n" + suffix.lstrip()


def load_prediction_db(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_prediction_index(payload: dict) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for pred in payload.get("predictions", []):
        for key in ("resolution_question", "resolution_question_ja", "resolution_question_en"):
            normalized = normalize_text(str(pred.get(key) or ""))
            if not normalized:
                continue
            index.setdefault(normalized, []).append(pred)
    return index


def ensure_article_link(pred: dict, *, slug: str, url: str, lang: str) -> None:
    links = pred.setdefault("article_links", [])
    if not isinstance(links, list):
        pred["article_links"] = links = []
    for article in links:
        if not isinstance(article, dict):
            continue
        if article.get("slug") == slug or article.get("url") == url:
            article["slug"] = slug
            article["url"] = url
            article["lang"] = lang
            return
    links.append({"slug": slug, "url": url, "lang": lang})


def reconcile(
    *,
    prediction_db_path: Path,
    ghost_db_path: Path,
    strip_unmatched: bool,
    dry_run: bool,
) -> dict[str, object]:
    payload = load_prediction_db(prediction_db_path)
    index = build_prediction_index(payload)

    con = sqlite3.connect(str(ghost_db_path))
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT p.id, p.slug, p.title, p.html, p.status, p.published_at,
               GROUP_CONCAT(t.slug, ' ') AS tag_slugs
        FROM posts p
        LEFT JOIN posts_tags pt ON pt.post_id = p.id
        LEFT JOIN tags t ON t.id = pt.tag_id
        WHERE p.status='published' AND p.type='post' AND p.html LIKE '%np-oracle%'
        GROUP BY p.id, p.slug, p.title, p.html, p.status, p.published_at
        ORDER BY p.published_at DESC
        """
    ).fetchall()

    stats = {
        "published_oracle_posts_seen": len(rows),
        "matched_predictions": 0,
        "stripped_to_analysis_only": 0,
        "unresolved": 0,
        "updated_prediction_ids": [],
        "analysis_only_slugs": [],
        "unresolved_slugs": [],
    }

    for row in rows:
        slug = str(row["slug"] or "").strip()
        html = str(row["html"] or "")
        tag_slugs = set(str(row["tag_slugs"] or "").split())
        oracle_question = extract_oracle_question(html)
        if not oracle_question:
            if strip_unmatched:
                updated_html = strip_oracle_block(html)
                if updated_html != html:
                    if not dry_run:
                        con.execute("UPDATE posts SET html=? WHERE id=?", (updated_html, row["id"]))
                    stats["stripped_to_analysis_only"] += 1
                    stats["analysis_only_slugs"].append(slug)
                else:
                    stats["unresolved"] += 1
                    stats["unresolved_slugs"].append(slug)
            else:
                stats["unresolved"] += 1
                stats["unresolved_slugs"].append(slug)
            continue

        normalized_question = normalize_text(oracle_question)
        matches = index.get(normalized_question, [])
        if len(matches) == 1:
            pred = matches[0]
            public_url = infer_public_url(slug, tag_slugs)
            lang = infer_lang(slug, tag_slugs)
            pred["article_slug"] = slug
            pred["ghost_url"] = public_url
            ensure_article_link(pred, slug=slug, url=public_url, lang=lang)
            if lang == "ja" and row["title"]:
                pred["article_title"] = row["title"]
            if lang == "en" and row["title"]:
                pred["article_title_en"] = row["title"]
            stats["matched_predictions"] += 1
            stats["updated_prediction_ids"].append(pred.get("prediction_id"))
            continue

        if strip_unmatched:
            updated_html = strip_oracle_block(html)
            if updated_html != html:
                if not dry_run:
                    con.execute("UPDATE posts SET html=? WHERE id=?", (updated_html, row["id"]))
                stats["stripped_to_analysis_only"] += 1
                stats["analysis_only_slugs"].append(slug)
            else:
                stats["unresolved"] += 1
                stats["unresolved_slugs"].append(slug)
        else:
            stats["unresolved"] += 1
            stats["unresolved_slugs"].append(slug)

    if not dry_run:
        con.commit()
        prediction_db_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    con.close()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile orphan oracle articles with prediction_db or downgrade them to analysis-only."
    )
    parser.add_argument("--prediction-db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--ghost-db", default=str(DEFAULT_GHOST_DB))
    parser.add_argument("--strip-unmatched", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = reconcile(
        prediction_db_path=Path(args.prediction_db),
        ghost_db_path=Path(args.ghost_db),
        strip_unmatched=args.strip_unmatched,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
