#!/usr/bin/env python3
"""SEO Monitor v2.0 — Detect → Auto-fix → Verify → Telegram
cron: 30 8 * * * /usr/bin/python3 /opt/shared/scripts/seo_monitor.py
"""

import json
import os
import re
import sqlite3
import subprocess
import time
import urllib.request
from datetime import datetime

# === CONFIG ===
GHOST_DB = "/var/www/nowpattern/content/data/ghost.db"
CADDYFILE = "/etc/caddy/Caddyfile"
REDIRECTS_FILE = "/etc/caddy/nowpattern-redirects.txt"
ROBOTS_FILE = "/var/www/nowpattern-static/robots.txt"
STATE_FILE = "/opt/shared/state/seo_monitor_state.json"
SITE_URL = "https://nowpattern.com"

INTERNAL_TAG_PREFIXES = ["/tag/p-", "/tag/event-", "/tag/lang-"]
INTERNAL_TAG_EXACT = ["/tag/deep-pattern/", "/tag/nowpattern/"]

ROBOTS_EXPECTED = (
    "User-agent: *\n"
    "Sitemap: https://nowpattern.com/sitemap.xml\n"
    "Disallow: /ghost/\n"
    "Disallow: /email/\n"
    "Disallow: /members/api/comments/counts/\n"
    "Disallow: /r/\n"
    "Disallow: /webmentions/receive/\n"
)

DUP_PAGE_PATTERN = re.compile(
    r"/(predictions|taxonomy|en-predictions|taxonomy-guide)-(\d+)/"
)

# cron-env.sh から読み込み
def load_env():
    env = {}
    try:
        with open("/opt/cron-env.sh") as f:
            for line in f:
                if line.startswith("export "):
                    k, _, v = line[7:].strip().partition("=")
                    env[k] = v.strip().strip('"').strip("'")
    except Exception as e:
        print(f"[WARN] cron-env.sh 読み込み失敗: {e}")
    return env


ENV = load_env()
BOT_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = ENV.get("TELEGRAM_CHAT_ID", "")


def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("[WARN] Telegram設定なし")
        return
    data = json.dumps({
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"[ERROR] Telegram送信失敗: {e}")


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# === CHECKS ===

def check_sitemap_pages():
    """サイトマップに数字サフィックスページがないか確認"""
    issues = []
    try:
        req = urllib.request.Request(
            f"{SITE_URL}/sitemap-pages.xml",
            headers={"User-Agent": "SEOMonitor/2.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read().decode("utf-8")
        urls = re.findall(r"<loc>([^<]+)</loc>", content)
        for url in urls:
            path = url.replace(SITE_URL, "")
            if DUP_PAGE_PATTERN.search(path):
                issues.append({
                    "type": "dup_page_in_sitemap",
                    "url": url,
                    "path": path,
                    "fixable": True
                })
    except Exception as e:
        issues.append({"type": "sitemap_fetch_error", "error": str(e), "fixable": False})
    return issues


def check_internal_tag_noindex():
    """内部タグページにX-Robots-Tag: noindexがあるか確認（存在するタグのみ）"""
    issues = []
    # 実際に存在するタグを使ってチェック（404はスキップ）
    test_tags = ["/tag/event-alliance/", "/tag/lang-ja/", "/tag/lang-en/"]
    for tag in test_tags:
        try:
            req = urllib.request.Request(
                f"{SITE_URL}{tag}",
                headers={"User-Agent": "SEOMonitor/2.0"}
            )
            req.get_method = lambda: "HEAD"
            with urllib.request.urlopen(req, timeout=10) as r:
                header = r.headers.get("X-Robots-Tag", "")
                status = r.status
            if status == 200 and "noindex" not in header.lower():
                issues.append({
                    "type": "missing_noindex",
                    "path": tag,
                    "got_header": header,
                    "fixable": True
                })
            # 404: タグページなし → 問題なし（スキップ）
        except urllib.error.HTTPError as e:
            if e.code == 404:
                pass  # ページなし = インデックスされる心配なし
            else:
                issues.append({
                    "type": "tag_check_error",
                    "path": tag,
                    "error": f"HTTP {e.code}",
                    "fixable": False
                })
        except Exception as e:
            issues.append({
                "type": "tag_check_error",
                "path": tag,
                "error": str(e),
                "fixable": False
            })
    return issues


def check_robots_txt():
    """robots.txtが正しい内容か確認"""
    issues = []
    try:
        with open(ROBOTS_FILE) as f:
            content = f.read()
        # /tag/ のDisallowが含まれていたらNG
        if re.search(r"Disallow:\s*/tag/", content):
            issues.append({
                "type": "robots_tag_disallow",
                "detail": "/tag/ Disallowがあるとnoindexが機能しない",
                "fixable": True
            })
        # Sitemapが含まれているか
        if "Sitemap:" not in content:
            issues.append({
                "type": "robots_no_sitemap",
                "detail": "SitemapディレクティブがないとGSCが警告",
                "fixable": True
            })
    except Exception as e:
        issues.append({"type": "robots_read_error", "error": str(e), "fixable": False})
    return issues


def check_posts_count(state):
    """記事数が急減していないか確認"""
    issues = []
    try:
        conn = sqlite3.connect(GHOST_DB)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM posts WHERE type='post' AND status='published'"
        )
        count = cur.fetchone()[0]
        conn.close()
        prev = state.get("posts_count", count)
        if prev - count > 5:
            issues.append({
                "type": "posts_count_drop",
                "previous": prev,
                "current": count,
                "drop": prev - count,
                "fixable": False  # 自動復元不可（手動確認必要）
            })
        state["posts_count"] = count
    except Exception as e:
        issues.append({"type": "db_read_error", "error": str(e), "fixable": False})
    return issues


# === AUTO-FIXES ===

def fix_dup_page(slug):
    """重複ページを修正: Ghost DB canonical_url + Caddy redirect"""
    base_slug = DUP_PAGE_PATTERN.sub(
        lambda m: f"/{m.group(1)}/", f"/{slug}/"
    ).strip("/")
    base_slug = re.sub(r"-\d+$", "", slug)

    # Step 1: Ghost DB に canonical_url を設定
    try:
        conn = sqlite3.connect(GHOST_DB)
        cur = conn.cursor()
        canonical = f"{SITE_URL}/{base_slug}/"
        cur.execute(
            "UPDATE posts SET canonical_url=? WHERE slug=? AND type='page'",
            (canonical, slug)
        )
        conn.commit()
        conn.close()
        print(f"  [FIX] Ghost DB canonical_url set: {slug} → {canonical}")
    except Exception as e:
        print(f"  [ERROR] Ghost DB fix失敗 ({slug}): {e}")
        return False

    # Step 2: Caddy redirectsに追加（重複チェック）
    try:
        with open(REDIRECTS_FILE) as f:
            existing = f.read()
        redirect_line = f"redir /{slug}/ /{base_slug}/ permanent\n"
        if redirect_line not in existing:
            with open(REDIRECTS_FILE, "a") as f:
                f.write(redirect_line)
            print(f"  [FIX] Caddy redirect追加: /{slug}/ → /{base_slug}/")
    except Exception as e:
        print(f"  [WARN] Caddy redirect追加失敗: {e}")

    # Step 3: Caddy reload
    try:
        subprocess.run(["caddy", "reload", "--config", CADDYFILE], check=True, timeout=10)
        print("  [FIX] Caddy reload OK")
    except Exception as e:
        print(f"  [WARN] Caddy reload失敗: {e}")

    return True


def fix_tag_noindex():
    """内部タグのnoindexをCaddyfileで確認・修復"""
    try:
        with open(CADDYFILE) as f:
            content = f.read()
        if "@internal_tags" not in content:
            # Guardが存在しない場合は追加
            guard = (
                "\n\t# Guard 1: Internal taxonomy tags noindex (auto-added by seo_monitor)\n"
                "\t@internal_tags path /tag/p-* /tag/event-* /tag/lang-* "
                "/tag/deep-pattern/ /tag/nowpattern/\n"
                "\theader @internal_tags X-Robots-Tag \"noindex, follow\"\n"
            )
            # nowpattern.com ブロック内に挿入
            content = content.replace(
                "nowpattern.com {",
                "nowpattern.com {" + guard
            )
            with open(CADDYFILE, "w") as f:
                f.write(content)
            subprocess.run(["caddy", "reload", "--config", CADDYFILE], check=True, timeout=10)
            print("  [FIX] Caddyfile @internal_tags guard追加 + reload")
            return True
        else:
            # Guardはあるがnoindexが返っていない → reload試みる
            subprocess.run(["caddy", "reload", "--config", CADDYFILE], check=True, timeout=10)
            print("  [FIX] Caddy reload実行（@internal_tags guard既存）")
            return True
    except Exception as e:
        print(f"  [ERROR] fix_tag_noindex失敗: {e}")
        return False


def fix_robots_txt():
    """robots.txtを正規内容に上書き"""
    try:
        os.makedirs(os.path.dirname(ROBOTS_FILE), exist_ok=True)
        with open(ROBOTS_FILE, "w") as f:
            f.write(ROBOTS_EXPECTED)
        print("  [FIX] robots.txt 正規内容に上書き")
        return True
    except Exception as e:
        print(f"  [ERROR] fix_robots_txt失敗: {e}")
        return False


# === MAIN ===

def main():
    print(f"[SEO Monitor v2] {datetime.now().strftime('%Y-%m-%d %H:%M JST')}")
    state = load_state()

    # --- Phase 1: 全チェック ---
    print("\n[Phase 1] チェック開始...")
    all_issues = []
    all_issues.extend(check_sitemap_pages())
    all_issues.extend(check_internal_tag_noindex())
    all_issues.extend(check_robots_txt())
    all_issues.extend(check_posts_count(state))

    if not all_issues:
        print("[OK] 全チェックOK。問題なし。")
        save_state(state)
        # 毎日サイレント成功（毎回通知は邪魔なので週1のみ）
        dow = datetime.now().weekday()  # 0=月曜
        if dow == 0:  # 月曜日のみサマリー送信
            send_telegram(
                "✅ *[SEO Monitor] 週次チェック: 問題なし*\n"
                f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"記事数: {state.get('posts_count', '?')}件"
            )
        return

    print(f"\n[Phase 2] {len(all_issues)}件の問題を検出。自動修正を試みます...")

    fixed = []
    failed = []
    manual_required = []

    for issue in all_issues:
        itype = issue["type"]
        print(f"  問題: {itype}")

        if not issue.get("fixable"):
            manual_required.append(issue)
            continue

        # 自動修正
        if itype == "dup_page_in_sitemap":
            path = issue["path"]
            m = DUP_PAGE_PATTERN.search(path)
            if m:
                slug = path.strip("/")
                ok = fix_dup_page(slug)
                (fixed if ok else failed).append(issue)

        elif itype == "missing_noindex":
            ok = fix_tag_noindex()
            (fixed if ok else failed).append(issue)

        elif itype in ("robots_tag_disallow", "robots_no_sitemap"):
            ok = fix_robots_txt()
            (fixed if ok else failed).append(issue)

        else:
            manual_required.append(issue)

    # --- Phase 3: 修正後に再チェック ---
    if fixed:
        print("\n[Phase 3] 修正後の再チェック（3秒待機）...")
        time.sleep(3)
        recheck = []
        recheck.extend(check_sitemap_pages())
        recheck.extend(check_internal_tag_noindex())
        recheck.extend(check_robots_txt())
        confirmed_fixed = [i for i in fixed if i["type"] not in [r["type"] for r in recheck]]
        still_broken = [i for i in fixed if i["type"] in [r["type"] for r in recheck]]
        failed.extend(still_broken)
    else:
        confirmed_fixed = []

    save_state(state)

    # --- Phase 4: Telegram通知 ---
    lines = [f"🔧 *[SEO Monitor v2] 自動修正レポート*"]
    lines.append(f"実行: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"検出: {len(all_issues)}件 | 修正OK: {len(confirmed_fixed)}件 | 失敗: {len(failed)}件 | 手動必要: {len(manual_required)}件")
    lines.append("")

    if confirmed_fixed:
        lines.append("✅ *自動修正済み:*")
        for i in confirmed_fixed:
            if i["type"] == "dup_page_in_sitemap":
                lines.append(f"  - 重複ページ除去: {i.get('path', '?')}")
            elif i["type"] == "missing_noindex":
                lines.append(f"  - noindex修復: {i.get('path', '?')}")
            elif i["type"] in ("robots_tag_disallow", "robots_no_sitemap"):
                lines.append(f"  - robots.txt修復")

    if failed:
        lines.append("\n❌ *修正失敗（要確認）:*")
        for i in failed:
            lines.append(f"  - {i['type']}: {i.get('detail', i.get('path', '?'))}")

    if manual_required:
        lines.append("\n⚠️ *手動対応必要:*")
        for i in manual_required:
            if i["type"] == "posts_count_drop":
                lines.append(
                    f"  - 記事数急減: {i['previous']}→{i['current']}件 ({i['drop']}件減)"
                )
            else:
                lines.append(f"  - {i['type']}: {i.get('error', i.get('detail', '?'))}")

    send_telegram("\n".join(lines))
    print("\n[完了] Telegram通知送信済み")


if __name__ == "__main__":
    main()
