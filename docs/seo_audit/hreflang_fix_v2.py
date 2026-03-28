#!/usr/bin/env python3
"""
hreflang_fix_v2.py — nowpattern.com EN posts への hreflang="ja" 補完 (バグ修正版)

v1 (hreflang_fix.py) からの変更点:
  [BUG FIX] 修復済みEN記事のマッチング失敗を修正
    - v1: JA hreflang内の古いURL（/en/en-[pinyin]/）を使ってEN記事をルックアップ → 修復後のスラッグと不一致 → 全てunmatched
    - v2: slug_repair_report.json で古いスラッグ → 新スラッグに解決してからマッチング

Usage:
  python3 hreflang_fix_v2.py --dry-run    # Analysis only
  python3 hreflang_fix_v2.py --apply      # Apply fixes

Deploy:
  scp hreflang_fix_v2.py root@163.44.124.123:/tmp/
  ssh root@163.44.124.123 "python3 /tmp/hreflang_fix_v2.py --dry-run"
  ssh root@163.44.124.123 "python3 /tmp/hreflang_fix_v2.py --apply"
"""

import sqlite3
import re
import json
import sys
import os
from datetime import datetime

DB_PATH = "/var/www/nowpattern/content/data/ghost.db"
REPAIR_REPORT_PATH = "/opt/shared/reports/slug_repair_report.json"
REPORT_PATH = "/opt/shared/reports/hreflang_fix_v2_report.json"
BASE_URL = "https://nowpattern.com"


def load_repair_mapping():
    """slug_repair_report.json から {old_slug: new_slug} マッピングを構築"""
    try:
        with open(REPAIR_REPORT_PATH) as f:
            data = json.load(f)
        mapping = {r["old_slug"]: r["new_slug"] for r in data.get("repairs", [])}
        print(f"Loaded {len(mapping)} slug repairs from repair_report")
        return mapping
    except FileNotFoundError:
        print(f"WARNING: {REPAIR_REPORT_PATH} not found. Repaired article matching disabled.")
        return {}


def resolve_en_slug_from_url(raw_url, old_to_new):
    """
    JA hreflang内の旧EN URL → 現在のENスラッグに解決する

    入力例:
      "__GHOST_URL__/en/en-denmaku-zong-xuan-ju-.../" → "the-shock-of-the-danish-..."
      "/en/en-chugoku-seifuno-ai-..."                 → "china-governments-ai-..."

    Returns: (resolved_slug_str, resolved_url_str)
    """
    # プレースホルダーとドメイン除去
    url = raw_url.replace("__GHOST_URL__", "").replace(BASE_URL, "")
    if not url.startswith("/"):
        url = "/" + url
    url = url.rstrip("/") + "/"

    m = re.match(r"/en/(.+)/", url)
    if not m:
        return None, url

    extracted_slug = m.group(1)
    # 修復マッピングで解決（なければ元のスラッグ）
    resolved_slug = old_to_new.get(extracted_slug, extracted_slug)
    return resolved_slug, f"/en/{resolved_slug}/"


def main():
    dry_run = "--dry-run" in sys.argv
    apply_mode = "--apply" in sys.argv

    if not dry_run and not apply_mode:
        print("Usage: python3 hreflang_fix_v2.py --dry-run | --apply")
        sys.exit(1)

    # === 修復マッピング読み込み ===
    old_to_new = load_repair_mapping()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 全公開記事取得
    rows = c.execute("""
        SELECT p.id, p.slug, p.title, p.codeinjection_head, p.type,
               GROUP_CONCAT(t.slug, ',') as tags
        FROM posts p
        LEFT JOIN posts_tags pt ON p.id = pt.post_id
        LEFT JOIN tags t ON pt.tag_id = t.id
        WHERE p.status = 'published' AND p.type = 'post'
        GROUP BY p.id
    """).fetchall()

    ja_posts = {}
    en_posts = {}
    for row in rows:
        tags = row["tags"] or ""
        info = {
            "id": row["id"],
            "ci": row["codeinjection_head"] or "",
            "title": row["title"] or "",
            "slug": row["slug"]
        }
        if "lang-en" in tags:
            en_posts[row["slug"]] = info
        elif "lang-ja" in tags:
            ja_posts[row["slug"]] = info

    print(f"JA posts: {len(ja_posts)}, EN posts: {len(en_posts)}")

    # === Step 2: JA posts から EN URL を抽出（旧URL → 新スラッグに解決）===
    ja_to_en_slug = {}  # ja_slug -> resolved current EN slug
    ja_to_en_url = {}   # ja_slug -> resolved current EN URL

    for ja_slug, info in ja_posts.items():
        ci = info["ci"]
        m = re.search(r'hreflang="en"[^>]*href="([^"]*)"', ci)
        if not m:
            m = re.search(r'href="([^"]*)"[^>]*hreflang="en"', ci)
        if m:
            raw_url = m.group(1)
            resolved_slug, resolved_url = resolve_en_slug_from_url(raw_url, old_to_new)
            if resolved_slug:
                ja_to_en_slug[ja_slug] = resolved_slug
                ja_to_en_url[ja_slug] = resolved_url

    print(f"JA posts with EN hreflang (resolved): {len(ja_to_en_slug)}")

    # === Step 3: 逆引きマップ（解決済みEN URL → JA slug）===
    en_url_to_ja = {url: ja_slug for ja_slug, url in ja_to_en_url.items()}

    # === Step 4: EN posts とのマッチング ===
    matched_pairs = []
    unmatched_en = []
    already_has_ja = []

    for en_slug, info in en_posts.items():
        en_url = f"/en/{en_slug}/"
        ci = info["ci"]

        if 'hreflang="ja"' in ci:
            already_has_ja.append(en_slug)
            continue

        if en_url in en_url_to_ja:
            ja_slug = en_url_to_ja[en_url]
            ja_url = f"{BASE_URL}/{ja_slug}/"
            matched_pairs.append((en_slug, ja_slug, ja_url))
        else:
            unmatched_en.append(en_slug)

    # === Step 5: Broken JA->EN チェック ===
    broken_ja_en = []
    for ja_slug, en_slug in ja_to_en_slug.items():
        if en_slug not in en_posts:
            broken_ja_en.append({
                "ja_slug": ja_slug,
                "resolved_en_slug": en_slug,
                "resolved_en_url": ja_to_en_url[ja_slug],
            })

    print(f"\nResults:")
    print(f"  EN posts already have hreflang='ja': {len(already_has_ja)}")
    print(f"  Matched EN-JA pairs (will add hreflang='ja'): {len(matched_pairs)}")
    print(f"  Unmatched EN posts (no JA counterpart): {len(unmatched_en)}")
    print(f"  Broken JA->EN (EN slug doesn't exist in posts): {len(broken_ja_en)}")

    if broken_ja_en[:3]:
        print(f"  Sample broken:")
        for b in broken_ja_en[:3]:
            print(f"    JA:{b['ja_slug']} -> EN:{b['resolved_en_slug']} (not in Ghost)")

    # === Step 6: Apply ===
    fixed_count = 0
    fix_details = []

    if apply_mode and matched_pairs:
        print(f"\nApplying {len(matched_pairs)} hreflang='ja' additions...")
        for en_slug, ja_slug, ja_url in matched_pairs:
            info = en_posts[en_slug]
            old_ci = info["ci"]

            ja_hreflang = f'<link rel="alternate" hreflang="ja" href="{ja_url}">'

            # hreflang="en" の前に挿入（JA→EN→x-default の順になるように）
            if 'hreflang="en"' in old_ci:
                new_ci = old_ci.replace(
                    '<link rel="alternate" hreflang="en"',
                    ja_hreflang + '\n<link rel="alternate" hreflang="en"',
                    1
                )
            elif old_ci.strip():
                new_ci = ja_hreflang + "\n" + old_ci
            else:
                new_ci = ja_hreflang

            c.execute(
                "UPDATE posts SET codeinjection_head = ?, updated_at = ? WHERE id = ?",
                (new_ci, datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"), info["id"])
            )
            fixed_count += 1
            fix_details.append({"en_slug": en_slug, "ja_slug": ja_slug, "ja_url": ja_url})

            if fixed_count <= 5:
                print(f"  [{fixed_count}] EN:{en_slug} → added ja href='{ja_url}'")

        conn.commit()
        print(f"\nCommitted {fixed_count} fixes to Ghost DB.")
        print(">>> Next step: systemctl restart ghost-nowpattern")

    elif dry_run:
        print(f"\n[DRY RUN] Would add hreflang='ja' to {len(matched_pairs)} EN posts:")
        for en_slug, ja_slug, ja_url in matched_pairs[:10]:
            print(f"  EN:{en_slug} → ja href='{ja_url}'")
        if len(matched_pairs) > 10:
            print(f"  ... and {len(matched_pairs) - 10} more")

    # === Step 7: Report ===
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": "dry-run" if dry_run else "applied",
        "repair_mapping_loaded": len(old_to_new),
        "summary": {
            "ja_posts_total": len(ja_posts),
            "en_posts_total": len(en_posts),
            "ja_with_en_hreflang_resolved": len(ja_to_en_slug),
            "en_already_has_ja": len(already_has_ja),
            "en_matched_pairs": len(matched_pairs),
            "en_unmatched": len(unmatched_en),
            "broken_ja_en_after_resolution": len(broken_ja_en),
            "fixes_applied": fixed_count
        },
        "matched_pairs": [
            {"en_slug": e, "ja_slug": j, "ja_url": u}
            for e, j, u in matched_pairs
        ],
        "broken_ja_en": broken_ja_en[:50],
        "unmatched_en_sample": unmatched_en[:20],
    }

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report saved: {REPORT_PATH}")

    conn.close()
    return report


if __name__ == "__main__":
    main()
