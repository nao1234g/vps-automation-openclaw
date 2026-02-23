#!/usr/bin/env python3
"""
nowpattern_article_patcher.py
Ghost記事をv4.0フォーマットに一括アップグレードするスクリプト。

対象: BOTTOM LINE / パターン: / NOW PATTERN セクションが不足している記事

動作:
  1. Ghost APIから全記事取得
  2. 各記事のHTML解析（不足セクションを特定）
  3. Gemini APIで不足セクションのコンテンツを生成
  4. Ghost APIで記事HTML更新

使用方法:
  python3 nowpattern_article_patcher.py --dry-run           # 確認のみ（変更なし）
  python3 nowpattern_article_patcher.py --slug <slug>       # 1記事のみパッチ
  python3 nowpattern_article_patcher.py --all               # 全FAIL記事を一括パッチ
  python3 nowpattern_article_patcher.py --all --limit 5     # 最大5記事
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl
import hmac
import hashlib
import base64
from datetime import datetime, timezone

# ── 環境変数から設定読み込み ──────────────────────────────────────
GHOST_URL = os.environ.get("NOWPATTERN_GHOST_URL", "https://nowpattern.com")
GHOST_API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")

# Ghost Admin API JWT生成
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
    signature = hmac.new(
        bytes.fromhex(secret), sig_input, hashlib.sha256
    ).digest()
    sig = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"


def _ghost_request(method: str, path: str, data: dict | None = None) -> dict:
    """Ghost Admin API リクエスト（SSL検証なし + リダイレクト追従なし）"""
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
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(f"Ghost API {method} {path} → HTTP {e.code}: {body_text[:300]}")


def get_all_posts(page_limit: int = 200) -> list[dict]:
    """全Ghost記事を取得（HTMLフォーマット）"""
    posts = []
    page = 1
    while True:
        result = _ghost_request("GET", f"/posts/?formats=html&limit={page_limit}&page={page}&include=tags")
        batch = result.get("posts", [])
        posts.extend(batch)
        meta = result.get("meta", {}).get("pagination", {})
        if page >= meta.get("pages", 1):
            break
        page += 1
    return posts


# ── 不足セクション検出 ─────────────────────────────────────────────

def check_missing(html: str, language: str = "ja") -> list[str]:
    """記事HTMLに不足しているv4.0セクションを返す"""
    missing = []
    if not html:
        return ["MISSING_HTML"]

    # Bottom Line
    if "BOTTOM LINE" not in html:
        missing.append("MISSING_BOTTOM_LINE")

    # Pattern tag (NOW PATTERN box内の パターン: / Pattern:)
    if language == "ja":
        if "パターン:" not in html:
            missing.append("MISSING_PATTERN_TAG")
    else:
        if "The Pattern:" not in html and "Pattern:" not in html:
            missing.append("MISSING_PATTERN_TAG")

    # NOW PATTERN box itself
    if "NOW PATTERN" not in html:
        missing.append("MISSING_NOW_PATTERN")

    # Between the Lines
    if "np-between-lines" not in html:
        missing.append("MISSING_BETWEEN_LINES")

    # Open Loop
    if "np-open-loop" not in html:
        missing.append("MISSING_OPEN_LOOP")

    return missing


def detect_language(post: dict) -> str:
    """記事の言語を検出（タグから判定）"""
    tags = post.get("tags", [])
    for tag in tags:
        slug = tag.get("slug", "")
        if slug == "lang-en":
            return "en"
        if slug == "lang-ja":
            return "ja"
    # タイトルの文字種から推定
    title = post.get("title", "")
    ja_count = sum(1 for c in title if "\u3000" <= c <= "\u9fff" or "\u30a0" <= c <= "\u30ff")
    return "ja" if ja_count > 2 else "en"


# ── Gemini でコンテンツ生成 ────────────────────────────────────────

def _gemini_request(prompt: str, model: str = "gemini-2.0-flash") -> str:
    """Gemini API呼び出し（単純テキスト生成）"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        },
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        candidates = result.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"No candidates in response: {json.dumps(result)[:200]}")
        cand = candidates[0]
        finish = cand.get("finishReason", "")
        content = cand.get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise RuntimeError(f"Empty parts (finishReason={finish}): {json.dumps(cand)[:200]}")
        text = parts[0].get("text", "")
        if not text:
            raise RuntimeError(f"Empty text in parts[0]: {json.dumps(parts[0])[:200]}")
        return text
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Gemini API error {e.code}: {body[:300]}")


def strip_html_for_gemini(html: str) -> str:
    """HTMLタグを除去してGeminiに送るプレーンテキストを生成"""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:6000]  # トークン節約


def generate_v4_sections(post: dict, missing: list[str], language: str) -> dict:  # noqa: ARG001
    """Gemini APIで不足するv4.0セクションのコンテンツを生成"""
    title = post.get("title", "")
    html = post.get("html", "")
    plain_text = strip_html_for_gemini(html)

    if language == "ja":
        prompt = f"""あなたはgeopolitical/マクロ経済ニュースレター「Nowpattern」の編集AIです。
以下の記事コンテンツを分析して、不足しているセクションのコンテンツをJSON形式で生成してください。

タイトル: {title}

記事本文（抜粋）:
{plain_text}

以下のJSONフィールドを生成してください（全フィールド必須）:
{{
  "bottom_line": "記事の要点を1-2文で（読者がこれだけ読めばわかる内容）",
  "bottom_line_pattern": "この記事で分析している力学/パターンの名称（例: 権力の集中 × 制度の亀裂）",
  "bottom_line_scenario": "最も可能性が高い基本シナリオを1文で",
  "bottom_line_watch": "次に注目すべき具体的なイベントや日付",
  "between_the_lines": "報道が言っていないこと、表面の語り方と本当の利害の違いを1-2段落で",
  "pattern_tag_text": "NOWPATTERNセクション用のパターン名（force1 × force2 形式、日本語）",
  "open_loop_trigger": "次の転換点となるトリガーイベントと想定時期",
  "open_loop_series": "このパターンの次の分析テーマ（シリーズの続き）"
}}

注意:
- 記事の言語（日本語）に合わせてください
- bottom_line は読者がすぐ理解できる平易な文章で
- between_the_lines は「報道されていない利害関係者の本音」を鋭く指摘する内容で
- 推測ではなく記事内容に基づいて生成する"""

    else:  # English
        prompt = f"""You are an editorial AI for the geopolitical/macro newsletter "Nowpattern".
Analyze the following article content and generate the missing section content in JSON format.

Title: {title}

Article body (excerpt):
{plain_text}

Generate the following JSON fields (all fields required):
{{
  "bottom_line": "The key takeaway in 1-2 sentences (what readers need to know)",
  "bottom_line_pattern": "The name of the structural force/pattern analyzed in this article (e.g., Power consolidation × Institutional fracture)",
  "bottom_line_scenario": "The base case scenario in one sentence",
  "bottom_line_watch": "The specific next event or date to watch",
  "between_the_lines": "What the coverage isn't saying — the gap between official narrative and actual interests (1-2 paragraphs)",
  "pattern_tag_text": "Pattern label for NOW PATTERN section (force1 × force2 format)",
  "open_loop_trigger": "The next trigger event and approximate timing",
  "open_loop_series": "Next topic in this pattern series"
}}

Notes:
- Keep bottom_line simple and accessible
- between_the_lines should sharply identify the unstated interests of stakeholders
- Base output on article content, not speculation"""

    raw = _gemini_request(prompt)

    # JSONをパース（```json ... ``` ブロックを除去）
    raw = re.sub(r"^```json\s*", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw.strip(), flags=re.MULTILINE)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # フォールバック: キー抽出
        result = {}
        for key in ["bottom_line", "bottom_line_pattern", "bottom_line_scenario",
                    "bottom_line_watch", "between_the_lines", "pattern_tag_text",
                    "open_loop_trigger", "open_loop_series"]:
            match = re.search(rf'"{key}"\s*:\s*"([^"]*)"', raw)
            result[key] = match.group(1) if match else f"[{key} — 要手動補完]"
        return result


# ── HTML パッチ処理 ────────────────────────────────────────────────

def _build_bottom_line_html(sections: dict, language: str) -> str:
    """Bottom Line div を生成"""
    bl = sections.get("bottom_line", "")
    pattern = sections.get("bottom_line_pattern", "")
    scenario = sections.get("bottom_line_scenario", "")
    watch = sections.get("bottom_line_watch", "")

    if language == "ja":
        bl_label = "BOTTOM LINE"
        pattern_label = "パターン:"
        scenario_label = "基本シナリオ:"
        watch_label = "注目:"
    else:
        bl_label = "BOTTOM LINE"
        pattern_label = "The Pattern:"
        scenario_label = "Base case:"
        watch_label = "Watch for:"

    style_box = 'class="np-bottom-line" style="background: linear-gradient(135deg, #121e30, #1a2940); border-radius: 8px; padding: 20px 24px; margin: 0 0 24px 0; border-left: 4px solid #c9a84c;"'
    style_h3 = 'style="color: #c9a84c; font-size: 0.85em; letter-spacing: 0.15em; text-transform: uppercase; margin: 0 0 12px 0;"'
    style_text = 'style="color: #ffffff; font-size: 1.05em; line-height: 1.6; margin: 0 0 8px 0;"'
    style_meta = 'style="color: #b0b0b0; font-size: 0.9em; margin: 4px 0 0 0;"'
    style_strong = 'style="color: #c9a84c;"'

    parts = [f'<div {style_box}>']
    parts.append(f'<h3 {style_h3}>{bl_label}</h3>')
    parts.append(f'<p {style_text}>{bl}</p>')
    if pattern:
        parts.append(f'<p {style_meta}><strong {style_strong}>{pattern_label}</strong> {pattern}</p>')
    if scenario:
        parts.append(f'<p {style_meta}><strong {style_strong}>{scenario_label}</strong> {scenario}</p>')
    if watch:
        parts.append(f'<p {style_meta}><strong {style_strong}>{watch_label}</strong> {watch}</p>')
    parts.append('</div>')
    return "\n".join(parts)


def _build_between_lines_html(sections: dict, language: str) -> str:
    """Between the Lines div を生成"""
    content = sections.get("between_the_lines", "")
    if not content:
        return ""
    if language == "ja":
        label = "行間を読む — 報道が言っていないこと"
    else:
        label = "Between the Lines"

    style_box = 'class="np-between-lines" style="background: #fff8e6; border: 1px solid #f0d060; border-radius: 6px; padding: 16px 20px; margin: 24px 0;"'
    style_h3 = 'style="color: #8a6d00; font-size: 0.95em; font-weight: 700; margin: 0 0 8px 0;"'
    style_text = 'style="color: #4a3d00; line-height: 1.7; margin: 0;"'

    return (
        f'<div {style_box}>'
        f'<h3 {style_h3}>{label}</h3>'
        f'<p {style_text}>{content}</p>'
        f'</div>'
    )


def _build_open_loop_html(sections: dict, language: str) -> str:
    """Open Loop div を生成"""
    trigger = sections.get("open_loop_trigger", "")
    series = sections.get("open_loop_series", "")
    if not trigger and not series:
        return ""

    if language == "ja":
        heading = "追跡ポイント"
        trigger_label = "次のトリガー:"
        series_label = "このパターンの続き:"
    else:
        heading = "What to Watch Next"
        trigger_label = "Next trigger:"
        series_label = "Next in this series:"

    style_box = 'class="np-open-loop" style="background: #f0f4f8; border-radius: 8px; padding: 16px 20px; margin: 24px 0; border-top: 3px solid #c9a84c;"'
    style_h3 = 'style="color: #121e30; font-size: 1em; margin: 0 0 8px 0;"'
    style_text = 'style="color: #333; line-height: 1.6; margin: 4px 0;"'

    parts = [f'<div {style_box}>']
    parts.append(f'<h3 {style_h3}>{heading}</h3>')
    if trigger:
        parts.append(f'<p {style_text}><strong>{trigger_label}</strong> {trigger}</p>')
    if series:
        parts.append(f'<p {style_text}><strong>{series_label}</strong> {series}</p>')
    parts.append('</div>')
    return "\n".join(parts)


def patch_html(html: str, sections: dict, missing: list[str], language: str) -> str:
    """記事HTMLに不足セクションを注入する"""
    patched = html

    # 1. Bottom Line を先頭に挿入
    if "MISSING_BOTTOM_LINE" in missing:
        bl_html = _build_bottom_line_html(sections, language)
        # 既存の <!-- v5.0 --> コメントより前、または最初のdivより前に挿入
        # まず既存のbottom_lineコメントを探す
        comment_match = re.search(r"<!--\s*v[45]\.0[^>]*Bottom Line[^>]*-->", patched, re.IGNORECASE)
        if comment_match:
            pos = comment_match.start()
            patched = patched[:pos] + bl_html + "\n" + patched[pos:]
        else:
            # タグバッジのdivまたは最初の要素の前に挿入
            badge_match = re.search(r"<div[^>]*style=['\"][^'\"]*border-bottom[^'\"]*['\"]", patched)
            if badge_match:
                pos = badge_match.start()
                patched = patched[:pos] + bl_html + "\n" + patched[pos:]
            else:
                # フォールバック: 先頭に挿入
                patched = bl_html + "\n" + patched

    # 2. パターンタグを NOW PATTERN box 内に挿入
    if "MISSING_PATTERN_TAG" in missing and "MISSING_NOW_PATTERN" not in missing:
        pattern_text = sections.get("pattern_tag_text", "")
        if pattern_text:
            style_tag = 'class="np-pattern-tag" style="color: #c9a84c; font-size: 1.1em; font-weight: bold; margin: 0 0 16px 0;"'
            # NOW PATTERN の h2 タグの直後に挿入
            pattern_tag_html = f'<p {style_tag}>\n    {pattern_text}\n  </p>'
            # 英語の場合は "NOW PATTERN" ラベル固定
            now_pattern_h2 = re.search(
                r"(<h2[^>]*>NOW PATTERN</h2>)", patched, re.IGNORECASE
            )
            if now_pattern_h2:
                insert_after = now_pattern_h2.end()
                patched = patched[:insert_after] + "\n  " + pattern_tag_html + patched[insert_after:]

    # 3. NOW PATTERN セクション全体を追加（完全に欠落している場合）
    if "MISSING_NOW_PATTERN" in missing:
        pattern_text = sections.get("pattern_tag_text", "")
        now_label = "NOW PATTERN"

        np_html = f'''
<hr style="border: none; border-top: 1px solid #e0dcd4; margin: 24px 0;">

<!-- NOW PATTERN (v4.0 patch) -->
<div class="np-pattern-box" style="background: #121e30; border-radius: 8px; padding: 24px 28px; margin: 24px 0;">
  <h2 style="font-size: 1.3em; color: #c9a84c; margin: 0 0 12px 0; letter-spacing: 0.1em;">{now_label}</h2>
  <p class="np-pattern-tag" style="color: #c9a84c; font-size: 1.1em; font-weight: bold; margin: 0 0 16px 0;">
    {pattern_text}
  </p>
  <div style="color: #ffffff; line-height: 1.7;">
    <p>{sections.get("bottom_line", "")}</p>
  </div>
</div>'''
        # What's Next / シナリオセクションの前、またはfooter divの前に挿入
        footer_match = re.search(r'<div[^>]*class="np-footer"', patched)
        if footer_match:
            patched = patched[:footer_match.start()] + np_html + "\n" + patched[footer_match.start():]
        else:
            patched = patched + np_html

    # 4. Between the Lines を注入（なければ最後のhrの前）
    if "MISSING_BETWEEN_LINES" in missing:
        btl_html = _build_between_lines_html(sections, language)
        if btl_html:
            # NOW PATTERN ボックスの直前（Big Picture後）に挿入
            np_match = re.search(r'<!--\s*Section 4\s*|<div[^>]*class="np-pattern-box"', patched)
            if np_match:
                patched = patched[:np_match.start()] + btl_html + "\n" + patched[np_match.start():]
            else:
                # フォールバック: footer直前
                footer_match = re.search(r'<div[^>]*class="np-footer"', patched)
                if footer_match:
                    patched = patched[:footer_match.start()] + btl_html + "\n" + patched[footer_match.start():]

    # 5. Open Loop を注入（What's Next の後、footerの前）
    if "MISSING_OPEN_LOOP" in missing:
        ol_html = _build_open_loop_html(sections, language)
        if ol_html:
            footer_match = re.search(r'<div[^>]*class="np-footer"', patched)
            if footer_match:
                patched = patched[:footer_match.start()] + ol_html + "\n" + patched[footer_match.start():]
            else:
                patched = patched + "\n" + ol_html

    return patched


def update_ghost_post(post_id: str, new_html: str, updated_at: str) -> dict:
    """Ghost APIで記事HTMLを更新（?source=html）"""
    path = f"/posts/{post_id}/?source=html"
    data = {
        "posts": [{
            "html": new_html,
            "updated_at": updated_at,
        }]
    }
    return _ghost_request("PUT", path, data)


# ── メイン処理 ────────────────────────────────────────────────────

def process_post(post: dict, dry_run: bool = False, verbose: bool = True) -> dict:
    """1記事をv4.0フォーマットにパッチ"""
    title = post.get("title", "")[:60]
    slug = post.get("slug", "")
    html = post.get("html", "") or ""
    language = detect_language(post)

    missing = check_missing(html, language)

    if not missing:
        if verbose:
            print(f"  [SKIP] {title} — already v4.0")
        return {"status": "skip", "slug": slug}

    if verbose:
        print(f"  [PATCH] {title}")
        print(f"         lang={language}, missing={missing}")

    if dry_run:
        return {"status": "dry_run", "slug": slug, "missing": missing, "language": language}

    # Gemini でコンテンツ生成
    try:
        sections = generate_v4_sections(post, missing, language)
        if verbose:
            print(f"         Gemini OK: bottom_line={sections.get('bottom_line', '')[:50]}...")
    except Exception as e:
        print(f"  [ERROR] Gemini failed for {slug}: {e}")
        return {"status": "error", "slug": slug, "error": str(e)}

    # HTMLパッチ
    new_html = patch_html(html, sections, missing, language)

    # Ghost API更新
    try:
        update_ghost_post(post["id"], new_html, post["updated_at"])
        if verbose:
            print(f"         Ghost updated OK")
        return {"status": "ok", "slug": slug, "missing_fixed": missing}
    except Exception as e:
        print(f"  [ERROR] Ghost update failed for {slug}: {e}")
        return {"status": "error", "slug": slug, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Nowpattern Ghost記事v4.0フォーマット一括パッチ")
    parser.add_argument("--dry-run", action="store_true", help="変更せず確認のみ")
    parser.add_argument("--slug", help="特定記事のslugのみ処理")
    parser.add_argument("--all", action="store_true", help="全FAIL記事を処理")
    parser.add_argument("--limit", type=int, default=0, help="最大処理件数（0=無制限）")
    parser.add_argument("--delay", type=float, default=3.0, help="記事間の待機秒数（レート制限）")
    args = parser.parse_args()

    if not GHOST_API_KEY:
        print("[ERROR] NOWPATTERN_GHOST_ADMIN_API_KEY が設定されていません")
        print("使用方法: source /opt/cron-env.sh && python3 nowpattern_article_patcher.py --all")
        sys.exit(1)

    if not args.all and not args.slug:
        parser.print_help()
        sys.exit(0)

    # API設定確認
    if not args.dry_run and not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY が設定されていません")
        sys.exit(1)

    print(f"Ghost URL: {GHOST_URL}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Fetching posts...")

    posts = get_all_posts()
    print(f"Total posts: {len(posts)}")

    if args.slug:
        posts = [p for p in posts if p.get("slug") == args.slug]
        if not posts:
            print(f"[ERROR] slug '{args.slug}' not found")
            sys.exit(1)

    # FAIL記事のみ絞り込み
    fail_posts = []
    for p in posts:
        html = p.get("html", "") or ""
        lang = detect_language(p)
        missing = check_missing(html, lang)
        if missing:
            fail_posts.append((p, missing, lang))

    print(f"\nFAIL articles: {len(fail_posts)} / {len(posts)}")
    print("─" * 60)

    if args.limit > 0:
        fail_posts = fail_posts[:args.limit]
        print(f"Limiting to {args.limit} articles")

    results = {"ok": 0, "skip": 0, "error": 0, "dry_run": 0}

    for i, (post, missing, lang) in enumerate(fail_posts, 1):
        title = post.get("title", "")[:55]
        print(f"\n[{i}/{len(fail_posts)}] {title}")
        print(f"  missing: {', '.join(missing)}")

        result = process_post(post, dry_run=args.dry_run)
        results[result["status"]] = results.get(result["status"], 0) + 1

        # レート制限対策
        if i < len(fail_posts) and not args.dry_run:
            time.sleep(args.delay)

    print("\n" + "=" * 60)
    print("SUMMARY:")
    for k, v in results.items():
        print(f"  {k}: {v}")

    if args.dry_run:
        print("\n→ DRY RUN完了。変更は行われていません。")
        print("  本番実行: python3 nowpattern_article_patcher.py --all")
    else:
        print("\n→ パッチ完了。nowpattern_visual_verify.py --all で確認してください。")


if __name__ == "__main__":
    main()
