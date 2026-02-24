#!/usr/bin/env python3
"""
fix_missing_ghost_tags.py — 記事タグの3重重複を修復 + Ghostタグ割り当て

問題:
  1. 記事HTML内にタグバッジが3回重複表示（パッチスクリプトの副作用）
  2. 1つは壊れている（改行なし、1行連結）
  3. ホームページのカードにGhostタグが未割り当て

修復内容:
  1. 全てのタグバッジセクションを検出・除去
  2. 1つの正しいタグバッジHTMLを再挿入（inline style付き）
  3. Ghost記事タグを割り当て（ホームページのカード表示用）

VPS上で実行:
  python3 /opt/shared/scripts/fix_missing_ghost_tags.py --dry-run   # 確認のみ
  python3 /opt/shared/scripts/fix_missing_ghost_tags.py              # 実行
  python3 /opt/shared/scripts/fix_missing_ghost_tags.py --slug nasa-mars-ai-autonomous-driving  # 1記事のみ
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
import hmac
import hashlib
import base64
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timezone

# ── 設定 ─────────────────────────────────────────────────────────
CRON_ENV = "/opt/cron-env.sh"
GHOST_URL = os.environ.get("NOWPATTERN_GHOST_URL", "https://nowpattern.com")

def load_env():
    env = {}
    if not os.path.exists(CRON_ENV):
        return env
    with open(CRON_ENV) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                k, v = line[7:].split("=", 1)
                env[k] = v.strip().strip("\"'")
    return env

env = load_env()
GHOST_API_KEY = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")

# ── Ghost Admin API ──────────────────────────────────────────────

def _ghost_jwt(api_key: str) -> str:
    key_id, secret = api_key.split(":")
    iat = int(datetime.now(timezone.utc).timestamp())
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "kid": key_id, "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"iat": iat, "exp": iat + 300, "aud": "/admin/"}).encode()
    ).rstrip(b"=").decode()
    sig_input = f"{header}.{payload}".encode()
    signature = hmac.new(bytes.fromhex(secret), sig_input, hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"

def ghost_request(method: str, path: str, data: dict | None = None) -> dict:
    url = f"{GHOST_URL}/ghost/api/admin{path}"
    token = _ghost_jwt(GHOST_API_KEY)
    headers = {
        "Authorization": f"Ghost {token}",
        "Content-Type": "application/json",
        "Accept-Version": "v5.0",
    }
    body = json.dumps(data).encode() if data else None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read())

# ── タクソノミー ─────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TAXONOMY_PATH = os.path.join(SCRIPT_DIR, "nowpattern_taxonomy.json")

def load_taxonomy():
    """taxonomy.json読み込み。JA→EN, slug→EN, EN→slugのマッピングを返す"""
    paths = [TAXONOMY_PATH, "/opt/shared/scripts/nowpattern_taxonomy.json"]
    tax = None
    for p in paths:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                tax = json.load(f)
            break
    if not tax:
        print("WARNING: taxonomy.json not found")
        return {}, {}, {}

    ja_to_en = {}
    slug_to_en = {}
    en_to_slug = {}

    for layer in ["genres", "events", "dynamics"]:
        for item in tax.get(layer, []):
            ja = item.get("name_ja", "")
            en = item.get("name_en", "") or item.get("name", "")
            slug = item.get("slug", "")
            if ja and en:
                ja_to_en[ja] = en
                ja_to_en[en] = en  # EN→EN pass-through
            if slug and en:
                slug_to_en[slug] = en
                en_to_slug[en] = slug

    return ja_to_en, slug_to_en, en_to_slug

JA_TO_EN, SLUG_TO_EN, EN_TO_SLUG = load_taxonomy()

# ジャンルの英語名リスト（Ghost primary tag判定用）
GENRE_NAMES_EN = {
    "Technology", "Geopolitics & Security", "Economy & Trade",
    "Finance & Markets", "Business & Industry", "Crypto & Web3",
    "Energy", "Environment & Climate", "Governance & Law",
    "Society", "Culture, Entertainment & Sports",
    "Media & Information", "Health & Science",
}

# ── タグバッジ正規表現パターン ───────────────────────────────────

# パターン: タグバッジセクションを検出する全パターン
TAG_SECTION_PATTERNS = [
    # パターン1: <div> wrapper内のタグバッジ（正しい形式）
    # <div style="margin: 0 0 20px 0; padding-bottom: 12px; ..."> ... ジャンル ... </div>
    re.compile(
        r'<div[^>]*style="[^"]*margin:\s*0\s+0\s+20px\s+0[^"]*"[^>]*>'
        r'.*?(?:ジャンル|Genre|イベント|Event|力学|Dynamics).*?'
        r'</div>\s*(?:</div>)?',
        re.DOTALL
    ),
    # パターン2: <p>タグ内のボールドマークダウン変換結果
    # <p><strong>ジャンル:</strong> <a href="...">  #テクノロジー</a>...</p>
    re.compile(
        r'<p>\s*<strong>\s*(?:ジャンル|Genre)\s*[:：]\s*</strong>.*?</p>'
        r'(?:\s*<p>\s*<strong>\s*(?:イベント|Event)\s*[:：]\s*</strong>.*?</p>)?'
        r'(?:\s*<p>\s*<strong>\s*(?:力学|Dynamics).*?[:：]\s*</strong>.*?</p>)?',
        re.DOTALL
    ),
    # パターン3: 壊れた1行連結版（ジャンル...イベント...力学が改行なし）
    re.compile(
        r'<p>\s*<strong>\s*(?:ジャンル|Genre)\s*[:：]\s*</strong>\s*<a[^>]*>.*?'
        r'(?:イベント|Event)\s*[:：].*?'
        r'(?:力学|Dynamics).*?</p>',
        re.DOTALL
    ),
    # パターン4: <p>イベント: <a>... のみ（ジャンルなし）
    re.compile(
        r'<p>\s*(?:イベント|Event)\s*[:：]\s*<a[^>]*>.*?</p>'
        r'(?:\s*<p>\s*(?:力学|Dynamics)\s*(?:\(Nowpattern\))?\s*[:：]\s*<a[^>]*>.*?</p>)?',
        re.DOTALL
    ),
    # パターン5: plain text版（<a>なし）
    re.compile(
        r'<p>\s*(?:ジャンル|Genre)\s*[:：]\s*#[^<]+</p>'
        r'(?:\s*<p>\s*(?:イベント|Event)\s*[:：]\s*#[^<]+</p>)?'
        r'(?:\s*<p>\s*(?:力学|Dynamics).*?[:：]\s*#[^<]+</p>)?',
        re.DOTALL
    ),
    # パターン6: border-bottom separator + tag rows
    re.compile(
        r'<div[^>]*style="[^"]*border-bottom[^"]*"[^>]*>\s*'
        r'(?:<div[^>]*>.*?(?:ジャンル|Genre|イベント|Event|力学|Dynamics).*?</div>\s*)+'
        r'</div>',
        re.DOTALL
    ),
]


def extract_tags_from_html(html: str) -> dict:
    """HTMLからジャンル/イベント/力学タグを抽出"""
    result = {"genre": [], "event": [], "dynamics": []}
    if not html:
        return result

    # <a>タグからタグ名を抽出
    # <a href="/tag/xxx/">  #テクノロジー</a>
    tag_links = re.findall(r'<a[^>]*href="[^"]*?/tag/([^/"]+)/?[^"]*"[^>]*>\s*#?\s*([^<]+?)\s*</a>', html)

    seen = set()
    for slug, display_name in tag_links:
        display_name = display_name.strip().lstrip('#').strip()

        # slug から英語名を取得
        en_name = SLUG_TO_EN.get(slug, "")
        if not en_name:
            en_name = JA_TO_EN.get(display_name, "")
        if not en_name:
            continue
        if en_name in seen:
            continue
        seen.add(en_name)

        # カテゴリ判定
        if slug.startswith("genre-") or en_name in GENRE_NAMES_EN:
            result["genre"].append({"en": en_name, "ja": display_name, "slug": slug})
        elif slug.startswith("event-"):
            result["event"].append({"en": en_name, "ja": display_name, "slug": slug})
        elif slug.startswith("p-"):
            result["dynamics"].append({"en": en_name, "ja": display_name, "slug": slug})
        else:
            # slugにprefixがない場合、taxonomy逆引き
            if en_name in GENRE_NAMES_EN:
                result["genre"].append({"en": en_name, "ja": display_name, "slug": slug})
            else:
                # 不明なものはgenreにフォールバック
                result["genre"].append({"en": en_name, "ja": display_name, "slug": slug})

    # タグが <a> で見つからない場合、プレーンテキストから抽出
    if not any(result.values()):
        for pattern in [
            r'(?:ジャンル|Genre)\s*[:：]\s*#?\s*([^\n<]+)',
            r'(?:イベント|Event)\s*[:：]\s*#?\s*([^\n<]+)',
            r'(?:力学|Dynamics).*?[:：]\s*#?\s*([^\n<]+)',
        ]:
            matches = re.findall(pattern, html)
            for match in matches:
                for tag_text in re.split(r'[,、/]', match):
                    tag_text = tag_text.strip().lstrip('#').strip()
                    en = JA_TO_EN.get(tag_text, "")
                    if en:
                        slug = EN_TO_SLUG.get(en, tag_text.lower().replace(" ", "-"))
                        if en in GENRE_NAMES_EN:
                            result["genre"].append({"en": en, "ja": tag_text, "slug": slug})
                        else:
                            result["event"].append({"en": en, "ja": tag_text, "slug": slug})

    return result


def remove_all_tag_sections(html: str) -> str:
    """HTML内の全てのタグバッジセクションを除去"""
    cleaned = html
    for pattern in TAG_SECTION_PATTERNS:
        cleaned = pattern.sub('', cleaned)

    # 残った空の<div>や連続空行をクリーンアップ
    cleaned = re.sub(r'<div[^>]*>\s*</div>', '', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned


def build_clean_tag_html(tags: dict, language: str = "ja") -> str:
    """1つのクリーンなタグバッジHTMLを生成"""
    rows = []

    label_genre = "ジャンル：" if language == "ja" else "Genre:"
    label_event = "イベント：" if language == "ja" else "Event:"
    label_dynamics = "力学(Nowpattern)：" if language == "ja" else "Dynamics(Nowpattern):"

    if tags["genre"]:
        spans = "".join(
            f'<a href="/tag/{t["slug"]}/" style="color: #2563eb; font-weight: 600; margin-right: 8px; text-decoration: none;">#{t["ja"]}</a>'
            for t in tags["genre"]
        )
        rows.append(
            f'<div style="margin: 0 0 6px 0; font-size: 0.85em; line-height: 1.8;">'
            f'<span style="color: #888; font-size: 0.8em; margin-right: 6px;">{label_genre}</span>{spans}</div>'
        )

    if tags["event"]:
        spans = "".join(
            f'<a href="/tag/{t["slug"]}/" style="color: #16a34a; font-weight: 600; margin-right: 8px; text-decoration: none;">#{t["ja"]}</a>'
            for t in tags["event"]
        )
        rows.append(
            f'<div style="margin: 0 0 6px 0; font-size: 0.85em; line-height: 1.8;">'
            f'<span style="color: #888; font-size: 0.8em; margin-right: 6px;">{label_event}</span>{spans}</div>'
        )

    if tags["dynamics"]:
        spans = "".join(
            f'<a href="/tag/{t["slug"]}/" style="color: #FF1A75; font-weight: 600; margin-right: 8px; text-decoration: none;">#{t["ja"]}</a>'
            for t in tags["dynamics"]
        )
        rows.append(
            f'<div style="margin: 0 0 6px 0; font-size: 0.85em; line-height: 1.8;">'
            f'<span style="color: #888; font-size: 0.8em; margin-right: 6px;">{label_dynamics}</span>{spans}</div>'
        )

    if not rows:
        return ""

    inner = "\n".join(rows)
    return f'<div style="margin: 0 0 20px 0; padding-bottom: 12px; border-bottom: 1px solid #e0dcd4;">\n{inner}\n</div>'


def insert_tag_section(html: str, tag_html: str) -> str:
    """タグバッジHTMLを記事の適切な位置に挿入する。
    挿入位置: FAST READ / Delta セクションの直後、本文開始前"""

    if not tag_html:
        return html

    # 挿入ポイント: 📊 DELTA セクションの閉じタグ後、または ⚡ FAST READ 後
    # パターン: </div> の後で、次のセクション (<h2>, <h3>, 📝, なぜ重要か 等) の前
    insertion_patterns = [
        # DELTAボックスの後
        (r'(このトピック[^<]*分析[^<]*</p>\s*</div>)', r'\1\n' + tag_html),
        # FAST READ CTA ("続きを読む") の後
        (r'(→\s*続きを読む[^<]*</p>\s*</div>\s*</div>)', r'\1\n' + tag_html),
        # np-why-box (なぜ重要か) の前
        (r'(<div[^>]*class="np-why-box")', tag_html + r'\n\1'),
        # 📝 Summary の前
        (r'(<h[23][^>]*>\s*📝)', tag_html + r'\n\1'),
        # "なぜ重要か" の前
        (r'(<(?:h[23]|div)[^>]*>(?:\s*<[^>]+>)*\s*(?:なぜ重要か|Why (?:it|this) matters))', tag_html + r'\n\1'),
        # 最初の <h2> の前（フォールバック）
        (r'(<h2[^>]*>)', tag_html + r'\n\1'),
    ]

    for pattern, replacement in insertion_patterns:
        new_html, count = re.subn(pattern, replacement, html, count=1, flags=re.DOTALL)
        if count > 0:
            return new_html

    # どこにも挿入できなかった場合、記事冒頭に挿入
    return tag_html + "\n" + html


def detect_language(html: str) -> str:
    ja_markers = ["ジャンル", "イベント", "力学", "要約", "なぜ重要か"]
    en_markers = ["Genre", "Event", "Dynamics", "Summary", "Why it matters"]
    ja_count = sum(1 for m in ja_markers if m in (html or ""))
    en_count = sum(1 for m in en_markers if m in (html or ""))
    return "ja" if ja_count >= en_count else "en"


# ── メイン処理 ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ghost記事のタグ重複修復 + Ghostタグ割り当て")
    parser.add_argument("--dry-run", action="store_true", help="変更せずに確認のみ")
    parser.add_argument("--slug", type=str, help="特定のslugの記事のみ修復")
    parser.add_argument("--tags-only", action="store_true", help="Ghostタグ割り当てのみ（HTML修正なし）")
    args = parser.parse_args()

    if not GHOST_API_KEY:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not found")
        sys.exit(1)

    print("=== Nowpattern タグ修復スクリプト ===")
    print(f"Ghost URL: {GHOST_URL}")
    print(f"Taxonomy: {len(JA_TO_EN)} mappings loaded")
    print(f"Dry-run: {args.dry_run}")
    print()

    # Step 1: 全記事取得
    print("Step 1: Ghost記事を取得中...")
    if args.slug:
        result = ghost_request("GET", f"/posts/slug/{args.slug}/?formats=html&include=tags")
        posts = result.get("posts", [])
    else:
        result = ghost_request("GET", "/posts/?limit=all&formats=html&include=tags")
        posts = result.get("posts", [])
    print(f"  {len(posts)} 記事を取得")

    # Step 2: Ghost既存タグのID取得
    print("Step 2: Ghostタグ一覧を取得中...")
    tag_result = ghost_request("GET", "/tags/?limit=all")
    ghost_tags = {t["name"]: t["id"] for t in tag_result.get("tags", [])}
    print(f"  {len(ghost_tags)} タグがGhostに登録済み")

    # Step 3: 各記事を修復
    print(f"\nStep 3: 記事を修復中...")
    html_fixed = 0
    tags_fixed = 0
    skipped = 0

    for post in posts:
        html = post.get("html", "") or ""
        title = post["title"][:55]
        post_id = post["id"]
        slug = post.get("slug", "")
        existing_tag_names = [t["name"] for t in post.get("tags", [])]

        # タグ情報をHTMLから抽出
        tags = extract_tags_from_html(html)
        has_tags = any(tags.values())
        lang = detect_language(html)

        if not has_tags:
            print(f"\n  SKIP (タグ抽出不可): {title}")
            skipped += 1
            continue

        # --- HTML修復 ---
        html_changed = False
        if not args.tags_only:
            # 重複タグセクションの数を数える
            tag_occurrences = 0
            for pattern in TAG_SECTION_PATTERNS:
                tag_occurrences += len(pattern.findall(html))

            if tag_occurrences >= 2:
                # 重複あり → クリーンアップ
                cleaned_html = remove_all_tag_sections(html)
                clean_tag_html = build_clean_tag_html(tags, lang)
                fixed_html = insert_tag_section(cleaned_html, clean_tag_html)

                if fixed_html != html:
                    html_changed = True
                    print(f"\n  FIX HTML [{post_id[:8]}]: {title}")
                    print(f"    重複 {tag_occurrences} 箇所 → 1箇所に修復")
                    genre_str = ", ".join(t["ja"] for t in tags["genre"])
                    event_str = ", ".join(t["ja"] for t in tags["event"])
                    dyn_str = ", ".join(t["ja"] for t in tags["dynamics"])
                    print(f"    ジャンル: {genre_str}")
                    print(f"    イベント: {event_str}")
                    print(f"    力学: {dyn_str}")

        # --- Ghostタグ割り当て ---
        has_ghost_genre = any(t in existing_tag_names for t in GENRE_NAMES_EN)
        tags_to_add = []

        # 固定タグ
        for fixed in ["Nowpattern", "Deep Pattern"]:
            if fixed not in existing_tag_names:
                tags_to_add.append(fixed)
        lang_tag = "日本語" if lang == "ja" else "English"
        if lang_tag not in existing_tag_names:
            tags_to_add.append(lang_tag)

        # ジャンル/イベント/力学タグ
        for layer in ["genre", "event", "dynamics"]:
            for t in tags[layer]:
                if t["en"] not in existing_tag_names:
                    tags_to_add.append(t["en"])

        need_tag_fix = len(tags_to_add) > 0

        if need_tag_fix:
            print(f"\n  FIX TAGS [{post_id[:8]}]: {title}")
            print(f"    追加: {', '.join(tags_to_add[:6])}")

        if not html_changed and not need_tag_fix:
            skipped += 1
            continue

        if args.dry_run:
            if html_changed:
                html_fixed += 1
            if need_tag_fix:
                tags_fixed += 1
            continue

        # --- 実際のAPI更新 ---
        try:
            # 最新のupdated_atを取得
            fresh = ghost_request("GET", f"/posts/{post_id}/?formats=html&include=tags")
            fresh_post = fresh["posts"][0]
            updated_at = fresh_post["updated_at"]

            update_payload = {"updated_at": updated_at}

            # HTML修正
            if html_changed:
                update_payload["html"] = fixed_html

            # タグ修正（既存タグ保持 + 新規追加）
            if need_tag_fix:
                all_tags = list(existing_tag_names) + tags_to_add
                tag_objects = []
                for name in all_tags:
                    if name in ghost_tags:
                        tag_objects.append({"id": ghost_tags[name]})
                    else:
                        tag_objects.append({"name": name})
                update_payload["tags"] = tag_objects

            # Ghost 5.x: HTML更新時は ?source=html を追加
            path = f"/posts/{post_id}/"
            if html_changed:
                path += "?source=html"

            ghost_request("PUT", path, {"posts": [update_payload]})

            if html_changed:
                html_fixed += 1
                print(f"    ✅ HTML修復完了")
            if need_tag_fix:
                tags_fixed += 1
                print(f"    ✅ タグ割り当て完了")

        except Exception as e:
            print(f"    ❌ FAIL: {e}")

        time.sleep(0.5)

    # 結果サマリー
    print(f"\n{'='*50}")
    print(f"=== 結果 ===")
    print(f"HTML修復: {html_fixed} 記事")
    print(f"タグ割り当て: {tags_fixed} 記事")
    print(f"スキップ: {skipped} 記事")
    if args.dry_run:
        print("\n（dry-runモード。実際に変更するには --dry-run を外してください）")


if __name__ == "__main__":
    main()
