#!/usr/bin/env python3
"""
hreflang_stale_fix.py — nowpattern.com EN/JA stale hreflang 一括修正

問題:
  - 189件のスラッグ修復済みEN記事が古いピンインURLをhreflangで参照
  - 92件のJA記事が対応EN記事の古いURLをhreflangで参照
  - 9件のEN記事がguan-ce-roguという存在しないスラッグを参照
  - 1件のEN記事がen-en-ダブルプレフィックス

修正方法:
  slug_repair_report.json の {old_slug -> new_slug} マッピングを使い
  codeinjection_head 内の古いURLを新しいURLに置換する

Usage:
  python3 hreflang_stale_fix.py --dry-run    # 変更なし（確認のみ）
  python3 hreflang_stale_fix.py --apply      # 適用

所要時間: 約30秒
"""

import sqlite3
import json
import re
import sys
import os
from datetime import datetime

DB_PATH = "/var/www/nowpattern/content/data/ghost.db"
REPAIR_REPORT_PATH = "/opt/shared/reports/slug_repair_report.json"
BACKUP_PATH = f"/opt/shared/backups/hreflang_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
REPORT_PATH = "/opt/shared/reports/hreflang_stale_fix_report.json"
BASE_URL = "https://nowpattern.com"


def load_repair_mapping():
    """slug_repair_report.json から old_slug -> new_slug マッピングを構築"""
    with open(REPAIR_REPORT_PATH) as f:
        data = json.load(f)
    mapping = {}
    for item in data.get("repairs", []):
        old_slug = item["old_slug"]
        new_slug = item["new_slug"]
        mapping[old_slug] = new_slug
    print(f"Loaded {len(mapping)} slug repairs from {REPAIR_REPORT_PATH}")
    return mapping


def fix_codeinjection_head(ci, slug_mapping):
    """
    codeinjection_head の古いhreflang URLを新しいURLに修正する。

    パターンA: /en/en-[old-pinyin]/ → /en/[english]/
    パターンB: /en/guan-ce-rogu-.../ → hreflangタグを削除
    パターンC: /en/en-en-[pinyin]/ → /en/en-[pinyin]/ (または修復済みならさらに修正)

    Returns: (new_ci, changes_made, change_description)
    """
    if not ci:
        return ci, 0, []

    original = ci
    changes = []

    # --- パターンA + C: 古いスラッグURLを新しいスラッグURLに置換 ---
    # __GHOST_URL__/en/[old-slug]/ または https://nowpattern.com/en/[old-slug]/
    url_pattern = re.compile(
        r'(href="(?:__GHOST_URL__|https://nowpattern\.com)/en/)([^/"]+)(/[^"]*")',
    )

    def replace_url(m):
        prefix = m.group(1)
        extracted_slug = m.group(2)
        suffix = m.group(3)

        # ダブルプレフィックス en-en-xxx の場合
        if extracted_slug.startswith("en-en-"):
            inner = extracted_slug[4:]  # en-xxx の形
            new_slug = slug_mapping.get(inner, inner)
            changes.append(f"double-prefix: {extracted_slug} → {new_slug}")
            return f'{prefix}{new_slug}{suffix}'

        # 修復マッピングに存在する場合
        if extracted_slug in slug_mapping:
            new_slug = slug_mapping[extracted_slug]
            changes.append(f"stale: {extracted_slug} → {new_slug}")
            return f'{prefix}{new_slug}{suffix}'

        # それ以外はそのまま
        return m.group(0)

    ci = url_pattern.sub(replace_url, ci)

    # --- パターンB: guan-ce-rogu スラッグを参照するhreflangタグを削除 ---
    guan_ce_pattern = re.compile(
        r'<link[^>]+href="[^"]*guan-ce-rogu[^"]*"[^>]*>\s*\n?',
    )
    guan_matches = guan_ce_pattern.findall(ci)
    if guan_matches:
        for m in guan_matches:
            changes.append(f"removed broken guan-ce-rogu ref: {m.strip()[:60]}...")
        ci = guan_ce_pattern.sub("", ci)

    return ci, len(changes), changes


def main():
    dry_run = "--dry-run" in sys.argv
    apply_mode = "--apply" in sys.argv

    if not dry_run and not apply_mode:
        print("Usage: python3 hreflang_stale_fix.py --dry-run | --apply")
        sys.exit(1)

    # マッピング読み込み
    slug_mapping = load_repair_mapping()

    # DB接続
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 全公開記事の codeinjection_head を取得
    rows = c.execute("""
        SELECT p.id, p.slug, p.title, p.codeinjection_head,
               GROUP_CONCAT(t.slug, ',') as tags
        FROM posts p
        LEFT JOIN posts_tags pt ON p.id = pt.post_id
        LEFT JOIN tags t ON pt.tag_id = t.id
        WHERE p.status = 'published' AND p.type = 'post'
          AND p.codeinjection_head IS NOT NULL
          AND p.codeinjection_head != ''
        GROUP BY p.id
    """).fetchall()

    print(f"\nTotal posts with non-null codeinjection_head: {len(rows)}")

    # バックアップ用データ
    backup = []
    # 修正詳細
    fixes = []
    # 統計
    stats = {
        "total_examined": len(rows),
        "en_fixed": 0,
        "ja_fixed": 0,
        "guan_ce_rogu_removed": 0,
        "double_prefix_fixed": 0,
        "no_change": 0,
    }

    for row in rows:
        post_id = row["id"]
        slug = row["slug"]
        old_ci = row["codeinjection_head"]
        tags = row["tags"] or ""

        lang = "en" if "lang-en" in tags else ("ja" if "lang-ja" in tags else "other")

        new_ci, change_count, change_list = fix_codeinjection_head(old_ci, slug_mapping)

        if change_count > 0:
            backup.append({
                "id": post_id,
                "slug": slug,
                "lang": lang,
                "old_ci": old_ci,
            })

            fix_detail = {
                "id": post_id,
                "slug": slug,
                "lang": lang,
                "changes": change_list,
            }
            fixes.append(fix_detail)

            # 統計更新
            for ch in change_list:
                if "guan-ce-rogu" in ch:
                    stats["guan_ce_rogu_removed"] += 1
                elif "double-prefix" in ch:
                    stats["double_prefix_fixed"] += 1
                elif lang == "en":
                    stats["en_fixed"] += 1
                elif lang == "ja":
                    stats["ja_fixed"] += 1

            if dry_run:
                print(f"  [DRY] {lang}: {slug}")
                for ch in change_list[:2]:
                    print(f"        {ch}")
                if len(change_list) > 2:
                    print(f"        ... ({len(change_list) - 2} more)")
            else:
                # 実際に更新
                c.execute(
                    "UPDATE posts SET codeinjection_head = ?, updated_at = ? WHERE id = ?",
                    (new_ci, datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"), post_id)
                )
        else:
            stats["no_change"] += 1

    # 結果表示
    total_fixed = len(fixes)
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Results:")
    print(f"  Total examined: {stats['total_examined']}")
    print(f"  EN posts fixed: {stats['en_fixed']}")
    print(f"  JA posts fixed: {stats['ja_fixed']}")
    print(f"  guan-ce-rogu removed: {stats['guan_ce_rogu_removed']}")
    print(f"  double-prefix fixed: {stats['double_prefix_fixed']}")
    print(f"  No change needed: {stats['no_change']}")
    print(f"  Total would fix: {total_fixed}")

    if apply_mode and total_fixed > 0:
        # バックアップ保存
        os.makedirs(os.path.dirname(BACKUP_PATH), exist_ok=True)
        with open(BACKUP_PATH, "w") as f:
            json.dump(backup, f, indent=2, ensure_ascii=False)
        print(f"\nBackup saved: {BACKUP_PATH}")

        conn.commit()
        print(f"Committed {total_fixed} fixes to Ghost DB.")
        print("\n>>> Next step: systemctl restart ghost-nowpattern")

    # レポート保存
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": "dry-run" if dry_run else "applied",
        "stats": stats,
        "total_fixed": total_fixed,
        "fixes": fixes[:100],  # 最大100件
        "backup_path": BACKUP_PATH if apply_mode else None,
    }
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report saved: {REPORT_PATH}")

    conn.close()


if __name__ == "__main__":
    main()
