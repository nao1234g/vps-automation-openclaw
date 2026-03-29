#!/usr/bin/env python3
"""
Phase 4: 記事↔予測 双方向リンク backfill
- ghost_url から article_slug を抽出 (1105件)
- article_links[] 配列を追加 [{url, slug, title, title_en, lang}]
- Ghost API で article_title / article_title_en の補完（batch）
  ※ Ghost API アクセス不要で ghost_url + 既存 article_title から構築可能

逆方向（記事→予測）:
- Ghost Admin API で記事を検索し codeinjection_head に prediction_ids を追記
- → Phase 4b として別スクリプトに分離（今回は Forward のみ）
"""
import json
import re
import shutil
from datetime import datetime

DB_PATH = "/opt/shared/scripts/prediction_db.json"

def extract_slug_from_url(url: str) -> str:
    """https://nowpattern.com/some-slug/ → some-slug"""
    if not url:
        return ""
    # Remove trailing slash
    url = url.rstrip("/")
    # Get last path component
    parts = url.split("/")
    slug = parts[-1] if parts else ""
    # Exclude non-article paths
    skip = {"", "en", "predictions", "about", "taxonomy", "taxonomy-guide"}
    if slug in skip:
        return ""
    return slug

def main():
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    bak = f"{DB_PATH}.bak-phase4-{ts}"
    shutil.copy2(DB_PATH, bak)
    print(f"Backup: {bak}")

    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    preds = db["predictions"]
    print(f"Total: {len(preds)}")

    stats = {
        "article_slug_added": 0,
        "article_slug_already": 0,
        "article_links_added": 0,
        "article_links_updated": 0,
        "no_ghost_url": 0,
    }

    for p in preds:
        ghost_url = p.get("ghost_url", "")
        if not ghost_url:
            stats["no_ghost_url"] += 1
            continue

        # 1. article_slug を ghost_url から抽出
        slug = extract_slug_from_url(ghost_url)
        if slug:
            if not p.get("article_slug"):
                p["article_slug"] = slug
                stats["article_slug_added"] += 1
            else:
                stats["article_slug_already"] += 1

        # 2. article_links[] を追加/更新
        existing_links = p.get("article_links", [])
        if not existing_links:
            link_entry = {
                "url": ghost_url,
                "slug": slug,
                "title_ja": p.get("article_title", ""),
                "title_en": p.get("article_title_en", ""),
                "lang": "ja",  # 親記事は JA
            }
            p["article_links"] = [link_entry]
            stats["article_links_added"] += 1
        else:
            # 既存のリンクがあれば slug / title を補完
            updated = False
            for link in existing_links:
                if not link.get("slug") and ghost_url and link.get("url") == ghost_url:
                    link["slug"] = slug
                    updated = True
            if updated:
                stats["article_links_updated"] += 1

    # 保存
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print("Done!")
    print(f"  article_slug added:      {stats['article_slug_added']}")
    print(f"  article_slug existing:   {stats['article_slug_already']}")
    print(f"  article_links added:     {stats['article_links_added']}")
    print(f"  article_links updated:   {stats['article_links_updated']}")
    print(f"  no ghost_url:            {stats['no_ghost_url']}")

    # 事後確認
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db2 = json.load(f)
    p2 = db2["predictions"]
    has_slug = sum(1 for p in p2 if p.get("article_slug"))
    has_links = sum(1 for p in p2 if p.get("article_links"))
    print(f"\nPost-run:")
    print(f"  article_slug:  {has_slug}/{len(p2)}")
    print(f"  article_links: {has_links}/{len(p2)}")

if __name__ == "__main__":
    main()
