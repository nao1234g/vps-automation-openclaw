#!/usr/bin/env python3
"""
Nowpattern 記事品質バリデーター v3.0
Ghost CMS内の全記事をv5.3フォーマット + genre URL構造で検証する。

v3.0 changes:
  - TAG_BADGE (np-tag-badge) 必須チェック追加
  - SUMMARY (np-summary) 必須チェック追加
  - ジャンルスラグをプレフィックスなしに修正 (geopolitics, economy, etc.)
  - URL構造チェック修正

Usage:
  python3 article_validator.py                # 全記事を検証
  python3 article_validator.py --slug <slug>  # 特定記事のみ
  python3 article_validator.py --json         # JSON出力
  python3 article_validator.py --warnings     # 警告も表示
"""

import json
import re
import sys
import time
import argparse
import requests
import urllib3
import jwt

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GHOST_URL = "https://nowpattern.com"
ADMIN_API_KEY = None

# ── v5.3 セクション定義 ──
# 必須セクション（これがないと不合格）
REQUIRED_SECTIONS = {
    "ja": {
        "FAST READ": ["FAST READ", "⚡ FAST READ"],
        "NOW PATTERN": ["NOW PATTERN"],
    },
    "en": {
        "FAST READ": ["FAST READ", "⚡ FAST READ"],
        "NOW PATTERN": ["NOW PATTERN"],
    },
}

# v5.3必須: TAG_BADGE と SUMMARY（HTMLクラスで検出）
REQUIRED_HTML_CLASSES = {
    "np-tag-badge": "TAG_BADGE（タグバッジ）",
    "np-summary": "SUMMARY（要約）",
}

# 推奨セクション（なくても合格だが警告）
RECOMMENDED_SECTIONS = {
    "ja": {
        "Between the Lines": ["行間を読む", "行間"],
        "What's Next": ["今後のシナリオ", "今後の展望", "シナリオ分析"],
        "OPEN LOOP": ["追跡ポイント", "注目すべきトリガー", "OPEN LOOP"],
        "What happened": ["何が起きたか", "観測事実"],
        "Big Picture": ["全体像", "歴史的文脈"],
        "Pattern History": ["パターンの歴史", "パターン史"],
    },
    "en": {
        "Between the Lines": ["Between the Lines"],
        "What's Next": ["What's Next", "What&#x27;s Next"],
        "OPEN LOOP": ["OPEN LOOP", "What to Watch Next"],
        "What happened": ["What happened"],
        "Big Picture": ["The Big Picture", "Big Picture"],
        "Pattern History": ["Pattern History"],
    },
}

# 禁止パターン（これがあったら不合格）
FORBIDDEN_PATTERNS = {
    "BOTTOM LINE": r"(?i)<h[23][^>]*>\s*BOTTOM\s+LINE\s*</h[23]>",
    "Speed Log見出し": r"(?i)speed\s+log",
    "観測ログ番号": r"観測ログ\s*#?\d+",
    "np-bottom-line CSS": r"np-bottom-line",
    "フッターTags行": r"Tags:\s*#",
}

# タグ検証
VALID_GENRES_JA = [
    "地政学・安全保障", "経済・貿易", "金融・市場", "ビジネス・産業",
    "テクノロジー", "暗号資産", "エネルギー", "環境・気候",
    "ガバナンス・法", "社会", "文化・エンタメ・スポーツ", "メディア・情報", "健康・科学",
]
VALID_GENRES_EN = [
    "Geopolitics & Security", "Economy & Trade", "Finance & Markets",
    "Business & Industry", "Technology", "Crypto & Web3", "Energy",
    "Environment & Climate", "Governance & Law", "Society",
    "Culture, Entertainment & Sports", "Media & Information", "Health & Science",
]

SYSTEM_TAGS = ["nowpattern", "deep-pattern", "lang-ja", "lang-en"]

# ── ジャンルタグ + URL構造 ──
VALID_GENRE_SLUGS = [
    "geopolitics", "finance", "economy", "technology",
    "crypto", "energy", "environment", "governance",
    "business", "culture", "health", "media", "society",
]
GENRE_PRIORITY_ORDER = list(VALID_GENRE_SLUGS)


def load_api_key():
    global ADMIN_API_KEY
    try:
        with open("/opt/cron-env.sh", "r") as f:
            for line in f:
                m = re.search(r'NOWPATTERN_GHOST_ADMIN_API_KEY="?([^"\s]+)"?', line)
                if m:
                    ADMIN_API_KEY = m.group(1)
                    return
    except FileNotFoundError:
        pass
    import os
    ADMIN_API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY")
    if not ADMIN_API_KEY:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not found")
        sys.exit(1)


def ghost_jwt():
    kid, sec = ADMIN_API_KEY.split(":")
    iat = int(time.time())
    return jwt.encode(
        {"iat": iat, "exp": iat + 300, "aud": "/admin/"},
        bytes.fromhex(sec), algorithm="HS256",
        headers={"alg": "HS256", "typ": "JWT", "kid": kid},
    )


def ghost_headers():
    return {"Authorization": f"Ghost {ghost_jwt()}", "Content-Type": "application/json"}


def get_all_posts(slug=None):
    posts = []
    page = 1
    while True:
        url = f"{GHOST_URL}/ghost/api/admin/posts/?formats=html&include=tags&limit=50&page={page}"
        if slug:
            url = f"{GHOST_URL}/ghost/api/admin/posts/slug/{slug}/?formats=html&include=tags"
            resp = requests.get(url, headers=ghost_headers(), verify=False, timeout=30)
            return resp.json().get("posts", [])
        resp = requests.get(url, headers=ghost_headers(), verify=False, timeout=30)
        batch = resp.json().get("posts", [])
        if not batch:
            break
        posts.extend(batch)
        meta = resp.json().get("meta", {}).get("pagination", {})
        if page >= meta.get("pages", 1):
            break
        page += 1
    return posts


def has_section(html, names):
    for n in names:
        if n.lower() in html.lower():
            return True
    return False


def validate_post(post):
    """1記事を検証。結果をdictで返す。"""
    title = post.get("title", "")
    slug = post.get("slug", "")
    html = post.get("html", "") or ""
    status = post.get("status", "")
    tags = post.get("tags", [])
    tag_slugs = [t.get("slug", "") for t in tags]
    tag_names = [t.get("name", "") for t in tags]

    # 言語判定
    lang = "ja" if "lang-ja" in tag_slugs else "en" if "lang-en" in tag_slugs else None

    errors = []  # 不合格
    warnings = []  # 警告
    info = []  # 情報

    # 0. 下書きはスキップ
    if status != "published":
        info.append(f"下書き（status={status}）— スキップ")
        return {"title": title, "slug": slug, "lang": lang, "status": status,
                "grade": "SKIP", "errors": errors, "warnings": warnings, "info": info}

    # 1. 言語タグチェック
    if not lang:
        errors.append("言語タグなし（lang-ja / lang-en どちらもない）")

    # 2. システムタグチェック
    if "nowpattern" not in tag_slugs:
        warnings.append("'nowpattern' タグなし")
    if "deep-pattern" not in tag_slugs:
        warnings.append("'deep-pattern' タグなし")

    # 2b. ジャンルタグチェック（v4.0: 1〜2個必須）
    genre_tags_found = [s for s in tag_slugs if s in VALID_GENRE_SLUGS]
    if len(genre_tags_found) == 0:
        errors.append("ジャンルタグなし（genre-* タグが1個も付いていない）")
    elif len(genre_tags_found) > 2:
        errors.append(f"ジャンルタグ過多: {len(genre_tags_found)}個（最大2個）: {genre_tags_found}")

    # 2c. URL構造チェック（/{genre}/{slug}/ or /en/{genre}/{slug}/）
    post_url = post.get("url", "")
    if post_url and lang and genre_tags_found:
        primary_genre_slug = genre_tags_found[0]  # primary_tag = first tag
        if lang == "en":
            expected_prefix = f"/en/{primary_genre_slug}/"
        else:
            expected_prefix = f"/{primary_genre_slug}/"
        url_path = post_url.replace(GHOST_URL, "")
        if not url_path.startswith(expected_prefix):
            warnings.append(f"URL構造不一致: 期待={expected_prefix}... 実際={url_path}")

    # 3. 禁止パターンチェック
    for name, pattern in FORBIDDEN_PATTERNS.items():
        if re.search(pattern, html):
            errors.append(f"禁止パターン検出: {name}")

    # 4. 必須セクションチェック
    if lang:
        for section_name, search_terms in REQUIRED_SECTIONS[lang].items():
            if not has_section(html, search_terms):
                errors.append(f"必須セクション欠落: {section_name}")

    # 4b. v5.3必須: TAG_BADGE + SUMMARY（HTMLクラスで検出）
    for css_class, label in REQUIRED_HTML_CLASSES.items():
        if css_class not in html:
            errors.append(f"v5.3必須要素欠落: {label} (class=\"{css_class}\")")

    # 5. 推奨セクションチェック
    if lang:
        for section_name, search_terms in RECOMMENDED_SECTIONS[lang].items():
            if not has_section(html, search_terms):
                warnings.append(f"推奨セクション欠落: {section_name}")

    # 6. シナリオチェック（3シナリオ必須）
    scenario_patterns_ja = [r"楽観", r"基本", r"悲観"]
    scenario_patterns_en = [r"(?i)bull\s*case|optimistic", r"(?i)base\s*case", r"(?i)bear\s*case|pessimistic"]
    scenario_patterns = scenario_patterns_ja if lang == "ja" else scenario_patterns_en
    scenario_count = sum(1 for p in scenario_patterns if re.search(p, html))
    if scenario_count < 3:
        warnings.append(f"シナリオ {scenario_count}/3 検出（基本/楽観/悲観 必須）")

    # 7. タイトル形式チェック
    if re.search(r"観測ログ|#\d{4}|Speed Log|Deep Pattern", title):
        errors.append(f"タイトルに禁止ワード: {title[:50]}")
    if len(title) > 80:
        warnings.append(f"タイトルが長い: {len(title)}文字（目安60文字以内）")

    # 8. 本文長チェック
    text_only = re.sub(r'<[^>]+>', '', html)
    word_count = len(text_only)
    if word_count < 2000:
        warnings.append(f"本文が短い: {word_count}文字（目安6000-7000語）")

    # グレード判定
    if errors:
        grade = "FAIL"
    elif warnings:
        grade = "WARN"
    else:
        grade = "PASS"

    return {
        "title": title, "slug": slug, "lang": lang or "??",
        "status": status, "grade": grade,
        "errors": errors, "warnings": warnings, "info": info,
        "word_count": word_count,
        "url": post.get("url", ""),
        "genre_tags": genre_tags_found,
    }


def main():
    parser = argparse.ArgumentParser(description="Nowpattern記事品質バリデーター")
    parser.add_argument("--slug", help="特定記事のslugのみ検証")
    parser.add_argument("--json", action="store_true", help="JSON出力")
    parser.add_argument("--warnings", action="store_true", help="警告も表示（デフォルトはエラーのみ）")
    parser.add_argument("--all", action="store_true", help="全記事の詳細を表示")
    args = parser.parse_args()

    load_api_key()
    posts = get_all_posts(slug=args.slug)

    results = []
    for post in posts:
        result = validate_post(post)
        results.append(result)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    # サマリー出力
    total = len([r for r in results if r["grade"] != "SKIP"])
    passed = len([r for r in results if r["grade"] == "PASS"])
    warned = len([r for r in results if r["grade"] == "WARN"])
    failed = len([r for r in results if r["grade"] == "FAIL"])

    print("=" * 70)
    print(f"Nowpattern 記事品質レポート — v5.3 フォーマット準拠チェック")
    print(f"検証対象: {total} 記事 | ✅ PASS: {passed} | ⚠️ WARN: {warned} | ❌ FAIL: {failed}")
    print("=" * 70)

    # FAIL記事を表示
    for r in results:
        if r["grade"] == "FAIL":
            print(f"\n❌ [{r['lang'].upper()}] {r['title'][:60]}")
            for e in r["errors"]:
                print(f"   ERROR: {e}")
            if args.warnings or args.all:
                for w in r["warnings"]:
                    print(f"   WARN:  {w}")

    # WARN記事を表示（--warnings or --all）
    if args.warnings or args.all:
        for r in results:
            if r["grade"] == "WARN":
                print(f"\n⚠️  [{r['lang'].upper()}] {r['title'][:60]}")
                for w in r["warnings"]:
                    print(f"   WARN:  {w}")

    # PASS記事を表示（--all のみ）
    if args.all:
        for r in results:
            if r["grade"] == "PASS":
                print(f"\n✅ [{r['lang'].upper()}] {r['title'][:60]}")

    print(f"\n{'=' * 70}")
    if failed == 0:
        print("✅ 全記事がv5.3フォーマットに準拠しています。")
    else:
        print(f"❌ {failed}記事に修正が必要です。")
    print("=" * 70)


if __name__ == "__main__":
    main()
