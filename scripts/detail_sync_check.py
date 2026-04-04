#!/usr/bin/env python3
"""
detail_sync_check.py — NORTH_STAR.md ↔ NORTH_STAR_DETAIL.md 同期チェッカー
==========================================================================
2ファイル間の§セクション番号とCHANGELOG日付の整合性を検証する。

使い方:
  python scripts/detail_sync_check.py          # チェック実行
  python scripts/detail_sync_check.py --fix    # 修正提案を表示
  python scripts/detail_sync_check.py --json   # JSON出力

チェック内容:
  1. §番号の対応: NORTH_STAR.md に§Nがあれば DETAIL にも§Nが必要
  2. CHANGELOG日付: 両ファイルの最新CHANGELOG日付が一致すること
  3. 孤立セクション: DETAIL にあるがNORTH_STARにない§番号を検出
"""
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import date

PROJECT_DIR = Path(__file__).parent.parent
NORTH_STAR = PROJECT_DIR / ".claude" / "rules" / "NORTH_STAR.md"
DETAIL = PROJECT_DIR / ".claude" / "reference" / "NORTH_STAR_DETAIL.md"


def extract_sections(text: str) -> set[str]:
    """テキストから§番号を抽出"""
    # ## §0, ## §12, ## 12. など複数パターンに対応
    sections = set()
    # パターン1: ## §N or ## §N 詳細:
    for m in re.finditer(r'##\s+§(\d+)', text):
        sections.add(m.group(1))
    # パターン2: ## N. (数字+ドット で始まるセクション)
    for m in re.finditer(r'^##\s+(\d+)\.\s', text, re.MULTILINE):
        sections.add(m.group(1))
    # パターン3: # Layer N の中の §N 参照
    for m in re.finditer(r'§(\d+)', text):
        sections.add(m.group(1))
    return sections


def extract_changelog_dates(text: str) -> list[str]:
    """CHANGELOGから日付を抽出（降順）"""
    dates = []
    in_changelog = False
    for line in text.splitlines():
        if "CHANGELOG" in line:
            in_changelog = True
            continue
        if in_changelog:
            m = re.match(r'\|\s*(20\d{2}-\d{2}-\d{2})\s*\|', line)
            if m:
                dates.append(m.group(1))
    return sorted(dates, reverse=True)


def extract_section_titles(text: str) -> dict[str, str]:
    """§番号とそのタイトルのマッピング"""
    titles = {}
    for m in re.finditer(r'^##\s+§(\d+)\s*(?:詳細[:：]?\s*)?(.+?)$', text, re.MULTILINE):
        titles[m.group(1)] = m.group(2).strip()
    return titles


def check_sync() -> dict:
    """同期チェックを実行"""
    results = {
        "status": "PASS",
        "checks": [],
        "errors": [],
        "warnings": [],
    }

    # ファイル存在チェック
    if not NORTH_STAR.exists():
        results["status"] = "FAIL"
        results["errors"].append(f"NORTH_STAR.md not found: {NORTH_STAR}")
        return results
    if not DETAIL.exists():
        results["status"] = "FAIL"
        results["errors"].append(f"NORTH_STAR_DETAIL.md not found: {DETAIL}")
        return results

    ns_text = NORTH_STAR.read_text(encoding="utf-8")
    dt_text = DETAIL.read_text(encoding="utf-8")

    # ── Check 1: §番号の対応 ──────────────────────────────────────
    ns_sections = extract_sections(ns_text)
    dt_sections = extract_sections(dt_text)

    # NORTH_STAR にあって DETAIL にないセクション
    # ※ NORTH_STAR は参照として§を多用するので、DETAIL のヘッダーとして
    #    定義されているものだけをチェック対象にする
    dt_header_sections = set()
    for m in re.finditer(r'^##\s+§(\d+)', dt_text, re.MULTILINE):
        dt_header_sections.add(m.group(1))

    ns_header_sections = set()
    for m in re.finditer(r'^##\s+(\d+)\.\s', ns_text, re.MULTILINE):
        ns_header_sections.add(m.group(1))
    # Also check ## §N format in NORTH_STAR
    for m in re.finditer(r'^##\s+§(\d+)', ns_text, re.MULTILINE):
        ns_header_sections.add(m.group(1))

    # NORTH_STAR のメインセクション(0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,18)
    # のうち DETAIL にヘッダーがないものを検出
    missing_in_detail = ns_header_sections - dt_header_sections
    orphan_in_detail = dt_header_sections - ns_header_sections

    if missing_in_detail:
        results["status"] = "WARN"
        msg = f"NORTH_STARにあるがDETAILにない§: {sorted(missing_in_detail, key=int)}"
        results["warnings"].append(msg)
        results["checks"].append({"name": "section_coverage", "status": "WARN", "detail": msg})
    else:
        results["checks"].append({"name": "section_coverage", "status": "PASS", "detail": "全§セクション対応済み"})

    if orphan_in_detail:
        results["warnings"].append(f"DETAILにあるがNORTH_STARにない§: {sorted(orphan_in_detail, key=int)}")

    # ── Check 2: CHANGELOG日付の同期 ─────────────────────────────
    ns_dates = extract_changelog_dates(ns_text)
    dt_dates = extract_changelog_dates(dt_text)

    if not ns_dates:
        results["warnings"].append("NORTH_STAR.md にCHANGELOGエントリなし")
    elif not dt_dates:
        results["warnings"].append("DETAIL にCHANGELOGエントリなし")
    else:
        ns_latest = ns_dates[0]
        dt_latest = dt_dates[0] if dt_dates else "none"

        if ns_latest == dt_latest:
            results["checks"].append({
                "name": "changelog_sync",
                "status": "PASS",
                "detail": f"最新日付一致: {ns_latest}"
            })
        else:
            results["status"] = "WARN"
            msg = f"CHANGELOG日付不一致: NORTH_STAR={ns_latest}, DETAIL={dt_latest}"
            results["warnings"].append(msg)
            results["checks"].append({"name": "changelog_sync", "status": "WARN", "detail": msg})

    # ── Check 3: DETAIL のセクション行数（極端に短いセクションを検出）──
    dt_lines = dt_text.splitlines()
    section_lengths = {}
    current_section = None
    current_start = 0

    for i, line in enumerate(dt_lines):
        m = re.match(r'^##\s+§(\d+)', line)
        if m:
            if current_section is not None:
                section_lengths[current_section] = i - current_start
            current_section = m.group(1)
            current_start = i
    if current_section is not None:
        section_lengths[current_section] = len(dt_lines) - current_start

    short_sections = {k: v for k, v in section_lengths.items() if v < 10}
    if short_sections:
        results["warnings"].append(
            f"DETAIL内の極短セクション(10行未満): {', '.join(f'§{k}({v}行)' for k, v in short_sections.items())}"
        )

    # ── Check 4: 今日の日付チェック（編集後にCHANGELOG更新忘れ）──
    today = date.today().isoformat()
    # 最近の変更があるかだけ情報提供
    if ns_dates and ns_dates[0] != today:
        results["checks"].append({
            "name": "freshness",
            "status": "INFO",
            "detail": f"NORTH_STAR最終更新: {ns_dates[0]} (今日: {today})"
        })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="NORTH_STAR.md ↔ DETAIL 同期チェッカー"
    )
    parser.add_argument("--json", action="store_true", help="JSON出力")
    parser.add_argument("--fix", action="store_true", help="修正提案を表示")
    args = parser.parse_args()

    results = check_sync()

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    # 通常出力
    status_icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(results["status"], "?")
    print(f"\n{'='*60}")
    print(f"  NORTH_STAR ↔ DETAIL 同期チェック: {status_icon} {results['status']}")
    print(f"{'='*60}\n")

    for check in results["checks"]:
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "INFO": "ℹ️"}.get(check["status"], "?")
        print(f"  {icon} {check['name']}: {check['detail']}")

    if results["errors"]:
        print(f"\n  ❌ Errors:")
        for e in results["errors"]:
            print(f"     {e}")

    if results["warnings"]:
        print(f"\n  ⚠️  Warnings:")
        for w in results["warnings"]:
            print(f"     {w}")

    if args.fix and results["warnings"]:
        print(f"\n  🔧 修正提案:")
        for w in results["warnings"]:
            if "NORTH_STARにあるがDETAILにない" in w:
                print(f"     → DETAIL に該当§のセクションヘッダーと詳細を追加する")
            elif "CHANGELOG日付不一致" in w:
                print(f"     → 両ファイルのCHANGELOGに同じ日付のエントリを追加する")
            elif "極短セクション" in w:
                print(f"     → 該当セクションに詳細情報を追記する（DETAIL = 情報量が増えるべき）")

    print()

    # 終了コード
    if results["status"] == "FAIL":
        sys.exit(1)
    elif results["status"] == "WARN":
        sys.exit(0)  # 警告は0で終了（CI向け）
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
