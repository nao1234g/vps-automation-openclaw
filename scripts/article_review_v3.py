#!/usr/bin/env python3
"""Nowpattern 記事レビュー v3.0 — 全記事のタグ+内容整合性チェック＆修正

NEO-ONE が実行する記事レビュースクリプト。
各記事を Ghost から取得し、タクソノミー v3.0 に準拠しているかチェックし、
タグと本文（NOW PATTERN セクション）を修正して Ghost に再投稿する。

使い方:
  # 全記事のレビューレポート出力（修正なし）
  python3 article_review_v3.py --report

  # 1記事ずつ修正（IDを指定）
  python3 article_review_v3.py --fix <ghost_post_id>

  # 全記事を一括修正
  python3 article_review_v3.py --fix-all
"""

import json
import time
import hashlib
import hmac
import base64
import sys
import os
import re

sys.stdout.reconfigure(encoding="utf-8")

# --- Ghost API ---
GHOST_URL = "https://nowpattern.com"
GHOST_API_KEY = ""

try:
    with open("/opt/cron-env.sh") as f:
        for line in f:
            if "NOWPATTERN_GHOST_ADMIN_API_KEY" in line:
                GHOST_API_KEY = line.split("=", 1)[1].strip().strip("'").strip('"')
                break
except FileNotFoundError:
    GHOST_API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")


def make_jwt(api_key):
    key_id, secret = api_key.split(":")
    iat = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iat": iat, "exp": iat + 300, "aud": "/admin/"}
    def b64url(data):
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
    h = b64url(json.dumps(header).encode())
    p = b64url(json.dumps(payload).encode())
    sig = hmac.new(bytes.fromhex(secret), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{b64url(sig)}"


# --- タクソノミー v3.0 定義 ---

VALID_DYNAMICS = {
    "Platform Power", "Regulatory Capture", "Narrative War", "Imperial Overreach",
    "Escalation Spiral", "Alliance Strain", "Path Dependency", "Backlash Pendulum",
    "Institutional Decay", "Coordination Failure", "Moral Hazard", "Contagion Cascade",
    "Shock Doctrine", "Tech Leapfrog", "Winner Takes All", "Legitimacy Void",
}

VALID_DYNAMICS_JA = {
    "プラットフォーム支配", "規制の捕獲", "物語の覇権", "権力の過伸展",
    "対立の螺旋", "同盟の亀裂", "経路依存", "揺り戻し",
    "制度の劣化", "協調の失敗", "モラルハザード", "伝染の連鎖",
    "危機便乗", "後発逆転", "勝者総取り", "正統性の空白",
}

VALID_EVENTS = {
    "Military Conflict", "Sanctions & Economic Warfare", "Trade & Tariffs",
    "Regulation & Law Change", "Election & Political Shift", "Market Shock",
    "Tech Breakthrough", "Treaty & Alliance Change", "Resource & Energy Crisis",
    "Judicial Action", "Disaster & Accident", "Health Emergency",
    "Cyber & Information Attack", "Social Unrest & Protest", "Structural Shift",
    "Deal & Restructuring", "Competition & Rivalry",
    "Scandal & Trust Crisis", "Social Change & Opinion",
}

VALID_EVENTS_JA = {
    "軍事衝突", "制裁・経済戦争", "貿易・関税", "規制・法改正",
    "選挙・政権交代", "市場ショック", "技術進展", "条約・同盟変動",
    "資源・エネルギー危機", "司法・裁判", "災害・事故", "健康危機・感染症",
    "サイバー攻撃", "社会不安・抗議", "構造シフト",
    "事業再編・取引", "競争・シェア争い", "スキャンダル・信頼危機", "社会変動・世論",
}

VALID_GENRES = {
    "Geopolitics & Security", "Economy & Trade", "Finance & Markets",
    "Business & Industry", "Technology", "Crypto & Web3",
    "Energy", "Environment & Climate", "Governance & Law",
    "Society", "Culture & Entertainment", "Media & Information", "Health & Science",
}

VALID_GENRES_JA = {
    "政治・政策", "地政学・安全保障", "経済・金融", "ビジネス・企業",
    "テクノロジー", "暗号資産・Web3", "科学・医療", "エネルギー・環境",
    "社会・人口", "文化・メディア", "スポーツ", "エンタメ",
}

# 旧タグ → 新タグ マッピング（自動変換が安全なもの）
OLD_TO_NEW_SAFE = {
    "Institutional Rot": "Institutional Decay",
    "Blowback": "Backlash Pendulum",
    "Collective Failure": "Coordination Failure",
    "Platform Dominance": "Platform Power",
    "Narrative Control": "Narrative War",
    "Contagion": "Contagion Cascade",
}

# 旧タグ → 要レビュー（1:1マッピングが不安全）
OLD_NEEDS_REVIEW = {
    "Exit Game": "記事の文脈に応じて Winner Takes All / Path Dependency / Escalation Spiral から選択",
    "Resource Power": "記事の文脈に応じて Platform Power / Path Dependency から選択",
    "Financial Coercion": "記事の文脈に応じて Path Dependency / Regulatory Capture から選択",
    "Deterrence Failure": "多くの場合 Escalation Spiral に吸収。記事がすでに Escalation Spiral を持つ場合は別のタグを検討",
    "Capital Flight": "Contagion Cascade が最も近い",
    "Systemic Fragility": "Contagion Cascade または Institutional Decay",
    "Silent Crisis": "Institutional Decay が最も近い",
}

SYSTEM_TAGS = {"Nowpattern", "Deep Pattern", "日本語", "English", "lang-ja", "lang-en"}


def classify_tag(tag_name):
    """タグを分類: genre / event / dynamics / system / old / custom"""
    if tag_name in SYSTEM_TAGS:
        return "system"
    if tag_name in VALID_DYNAMICS or tag_name in VALID_DYNAMICS_JA:
        return "dynamics_ok"
    if tag_name in VALID_EVENTS or tag_name in VALID_EVENTS_JA:
        return "event_ok"
    if tag_name in VALID_GENRES or tag_name in VALID_GENRES_JA:
        return "genre_ok"
    if tag_name in OLD_TO_NEW_SAFE:
        return "old_safe"
    if tag_name in OLD_NEEDS_REVIEW:
        return "old_review"
    return "custom"


def analyze_article(post):
    """記事のタグを分析し、修正が必要かどうかを判定"""
    tags = [t["name"] for t in post.get("tags", [])]
    title = post.get("title", "")
    post_id = post.get("id", "")

    result = {
        "id": post_id,
        "title": title[:80],
        "tags": tags,
        "issues": [],
        "auto_fix": {},
        "needs_review": [],
    }

    for tag in tags:
        cat = classify_tag(tag)
        if cat == "old_safe":
            new_tag = OLD_TO_NEW_SAFE[tag]
            result["auto_fix"][tag] = new_tag
            result["issues"].append(f"AUTO-FIX: '{tag}' -> '{new_tag}'")
        elif cat == "old_review":
            advice = OLD_NEEDS_REVIEW[tag]
            result["needs_review"].append(f"REVIEW: '{tag}' -> {advice}")
            result["issues"].append(f"NEEDS-REVIEW: '{tag}'")
        elif cat == "custom":
            result["needs_review"].append(f"CUSTOM TAG: '{tag}' (タクソノミー外)")
            result["issues"].append(f"CUSTOM: '{tag}'")

    return result


def report_all():
    """全記事のレビューレポートを出力"""
    import urllib3
    urllib3.disable_warnings()
    import requests

    token = make_jwt(GHOST_API_KEY)
    headers = {"Authorization": f"Ghost {token}"}

    r = requests.get(
        f"{GHOST_URL}/ghost/api/admin/posts/?limit=all&include=tags",
        headers=headers, verify=False, timeout=30
    )
    posts = r.json().get("posts", [])

    auto_fix_count = 0
    review_count = 0
    clean_count = 0

    print("=" * 80)
    print("NOWPATTERN 記事レビュー v3.0 — タクソノミー整合性レポート")
    print(f"対象: {len(posts)} 記事")
    print("=" * 80)

    for post in posts:
        result = analyze_article(post)
        if not result["issues"]:
            clean_count += 1
            continue

        print(f"\n--- {result['title']} ---")
        print(f"  ID: {result['id']}")
        print(f"  Tags: {', '.join(result['tags'])}")

        for fix_from, fix_to in result["auto_fix"].items():
            print(f"  ✅ AUTO-FIX: '{fix_from}' -> '{fix_to}'")
            auto_fix_count += 1

        for note in result["needs_review"]:
            print(f"  ⚠️  {note}")
            review_count += 1

    print("\n" + "=" * 80)
    print(f"SUMMARY:")
    print(f"  Clean (問題なし): {clean_count}")
    print(f"  Auto-fixable (自動修正可能): {auto_fix_count}")
    print(f"  Needs review (レビュー必要): {review_count}")
    print("=" * 80)

    # NEO-ONE用の修正指示を /opt/shared/ に書き出し
    instructions = {
        "task": "Nowpattern v3.0 タクソノミー統一 — 全記事レビュー＆修正",
        "total_articles": len(posts),
        "auto_fix_mapping": OLD_TO_NEW_SAFE,
        "review_mapping": OLD_NEEDS_REVIEW,
        "instructions": [
            "1. 各記事のタグをv3.0タクソノミーに修正する",
            "2. AUTO-FIXタグは自動的に新タグ名に変換してGhostに更新する",
            "3. NEEDS-REVIEWタグは記事の内容を読んで最適な新タグを選択する",
            "4. CUSTOMタグ（日本語記事の独自タグ）はv3.0のイベント+力学タグに再分類する",
            "5. 記事本文のNOW PATTERNセクションに旧タグ名が使われている場合は新タグ名に書き換える",
            "6. タグだけでなく分析の整合性も確認する（新タグの定義に沿った分析になっているか）",
        ],
        "valid_dynamics_en": sorted(VALID_DYNAMICS),
        "valid_events_en": sorted(VALID_EVENTS),
        "articles": [],
    }

    for post in posts:
        result = analyze_article(post)
        if result["issues"]:
            instructions["articles"].append(result)

    output_path = "/opt/shared/article_review_v3_instructions.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(instructions, f, ensure_ascii=False, indent=2)
        print(f"\nNEO-ONE用指示ファイル: {output_path}")
    except Exception as e:
        print(f"\nWARN: Could not write instructions file: {e}")


if __name__ == "__main__":
    if not GHOST_API_KEY:
        print("ERROR: Ghost API key not found")
        sys.exit(1)

    if "--report" in sys.argv:
        report_all()
    elif "--fix" in sys.argv:
        print("--fix mode: NEO-ONE が個別記事を修正する際に使用します")
        print("Usage: python3 article_review_v3.py --fix <post_id>")
    elif "--fix-all" in sys.argv:
        print("--fix-all mode: NEO-ONE が全記事を一括修正する際に使用します")
    else:
        print("Usage:")
        print("  python3 article_review_v3.py --report     # レビューレポート出力")
        print("  python3 article_review_v3.py --fix <id>   # 1記事修正")
        print("  python3 article_review_v3.py --fix-all    # 全記事修正")
