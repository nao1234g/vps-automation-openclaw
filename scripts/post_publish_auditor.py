#!/usr/bin/env python3
"""
post_publish_auditor.py — 公開後スタブ記事検出ガーディアン（Layer 2 Enforcement）

役割:
  1. Ghost DB から過去30分以内に公開された記事を取得
  2. 各記事の HTML を article_validator.py 相当でチェック
     - np-signal クラスが存在するか
     - np-between-lines クラスが存在するか
     - HTML が 8000 文字以上あるか
  3. スタブ検出 → 即 Telegram アラート
  4. 全結果をログに記録

cron（5分ごと）:
  */5 * * * * . /opt/cron-env.sh && python3 /opt/shared/scripts/post_publish_auditor.py >> /opt/shared/logs/post_publish_auditor.log 2>&1

注意: Ghost DB への直接アクセス + Ghost Content API 両方を使用
"""

import json
import os
import re
import sqlite3
import ssl
import sys
import time
import urllib.request
from datetime import datetime

from article_truth_guard import evaluate_article_truth

# ─── 設定 ───────────────────────────────────────────────
GHOST_DB = "/var/www/nowpattern/content/data/ghost.db"
GHOST_URL = "https://nowpattern.com"
CONTENT_API_KEY = "8a5c72b01df5c092d60d865330"
CRON_ENV = "/opt/cron-env.sh"
LOG_PATH = "/opt/shared/logs/post_publish_auditor.log"
STATE_PATH = "/opt/shared/state/post_publish_auditor_last.json"
CHECK_WINDOW_MINUTES = 30   # 過去N分以内の記事をチェック
MIN_HTML_LENGTH = 8000      # 完全記事の最低文字数
REQUIRED_CLASSES = ["np-signal", "np-between-lines"]

# 特殊ページ（記事フォーマット不要）スキップリスト
SKIP_SLUGS = {
    "about", "en-about",
    "predictions", "en-predictions",
    "taxonomy-ja", "en-taxonomy",
    "taxonomy-guide-ja", "en-taxonomy-guide",
    "members",
}

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


# ─── Telegram ────────────────────────────────────────────
def _load_env():
    env = {}
    try:
        for line in open(CRON_ENV):
            if line.startswith("export "):
                k, _, v = line[7:].strip().partition("=")
                env[k] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


def _send_tg(msg, tok, cid):
    data = json.dumps({"chat_id": cid, "text": msg, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{tok}/sendMessage",
        data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[TG] Error: {e}")


# ─── Ghost DB から最近公開された記事を取得 ─────────────────
def _get_recent_posts_from_db():
    """SQLite直接アクセスで過去30分以内に公開された記事を取得"""
    posts = []
    try:
        con = sqlite3.connect(f"file:{GHOST_DB}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # Ghost の published_at は ミリ秒 UNIX タイムスタンプ
        cutoff_ms = int((time.time() - CHECK_WINDOW_MINUTES * 60) * 1000)
        cur.execute(
            "SELECT id, slug, title, html, published_at, status "
            "FROM posts "
            "WHERE status = 'published' AND published_at >= ? "
            "ORDER BY published_at DESC LIMIT 50",
            (cutoff_ms,)
        )
        for row in cur.fetchall():
            posts.append(dict(row))
        con.close()
    except Exception as ex:
        print(f"[DB] Error: {ex}")
    return posts


# ─── Ghost Content API からフォールバック取得 ─────────────
def _get_recent_posts_from_api():
    """Content API 経由で過去30分の記事を取得（DB読めない場合のフォールバック）"""
    posts = []
    api = (
        f"{GHOST_URL}/ghost/api/content/posts/"
        f"?key={CONTENT_API_KEY}"
        f"&limit=20"
        f"&fields=id,slug,title,html,published_at"
        f"&filter=status:published"
        f"&order=published_at+desc"
    )
    try:
        req = urllib.request.Request(api, headers={"User-Agent": "PostPublishAuditor/1.0"})
        with urllib.request.urlopen(req, timeout=20, context=ssl_ctx) as r:
            data = json.loads(r.read())
        cutoff = time.time() - CHECK_WINDOW_MINUTES * 60
        for p in data.get("posts", []):
            pub_str = p.get("published_at", "")
            if pub_str:
                try:
                    pub_str_clean = pub_str.replace("Z", "+00:00")
                    pub_ts = datetime.fromisoformat(pub_str_clean).timestamp()
                    if pub_ts >= cutoff:
                        posts.append(p)
                except Exception:
                    pass
    except Exception as ex:
        print(f"[API] Error: {ex}")
    return posts


# ─── 記事のスタブ検査 ─────────────────────────────────────
def _audit_post(post):
    """記事の HTML を検査。問題があれば (True, [エラーリスト]) を返す"""
    html = post.get("html") or ""
    slug = post.get("slug", "")
    issues = []

    # 特殊ページはスキップ
    if slug in SKIP_SLUGS:
        return False, []

    # 1. HTML 長チェック
    if len(html) < MIN_HTML_LENGTH:
        issues.append(
            f"HTML短すぎ（{len(html)}文字 < {MIN_HTML_LENGTH}文字）スタブ記事の疑い"
        )

    # 2. 必須クラスチェック
    for cls in REQUIRED_CLASSES:
        pattern = f'class="[^"]*{re.escape(cls)}[^"]*"'
        if not re.search(pattern, html):
            issues.append(f"`{cls}` クラスが存在しない（本文セクション未完成）")

    truth_errors, _ = evaluate_article_truth(
        title=post.get("title", ""),
        html=html,
        site_url=GHOST_URL,
        require_external_sources=True,
    )
    if truth_errors:
        issues.append("source/truth guard: " + ", ".join(truth_errors))

    return len(issues) > 0, issues


# ─── 状態管理（アラート重複を防ぐ） ─────────────────────────
def _load_alerted():
    """既にアラート済みのスラッグセットを返す"""
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return set(json.load(f).get("alerted_slugs", []))
    except Exception:
        return set()


def _save_alerted(slugs):
    """アラート済みスラッグを保存"""
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "alerted_slugs": list(slugs),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M JST")
            }, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        print(f"[STATE] Save error: {ex}")


# ─── メイン ─────────────────────────────────────────────
def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M JST")
    env = _load_env()
    tok = env.get("TELEGRAM_BOT_TOKEN", "")
    cid = env.get("TELEGRAM_CHAT_ID", "")

    # 記事取得
    posts = _get_recent_posts_from_db()
    source = "DB"
    if not posts:
        posts = _get_recent_posts_from_api()
        source = "API"

    if not posts:
        print(f"[{ts}] チェック対象なし（過去{CHECK_WINDOW_MINUTES}分に公開なし）")
        return 0

    print(f"[{ts}] 対象: {len(posts)}件 (source={source})")

    # アラート済みスラッグを読み込み
    alerted = _load_alerted()

    stub_reports = []
    ok_count = 0

    for post in posts:
        slug = post.get("slug", "?")
        title = post.get("title", "?")

        # 既にアラート済みならスキップ
        if slug in alerted:
            continue

        has_issue, issues = _audit_post(post)
        if has_issue:
            stub_reports.append({
                "slug": slug,
                "title": title,
                "issues": issues,
            })
            alerted.add(slug)
        else:
            ok_count += 1

    # ログ出力
    for r in stub_reports:
        print(f"  STUB: {r['slug']}")
        for iss in r["issues"]:
            print(f"     - {iss}")
    if ok_count:
        print(f"  OK: {ok_count}件")

    # アラート送信
    if stub_reports and tok and cid:
        lines = []
        for r in stub_reports:
            lines.append(f"*{r['title']}*")
            lines.append(f"   slug: `{r['slug']}`")
            for iss in r["issues"]:
                lines.append(f"   - {iss}")
        msg = (
            f"[Post-Publish Auditor] スタブ記事を検出 | {ts}\n\n"
            + "\n".join(lines)
            + f"\n\n→ 今すぐ記事を完成させてください（FAST READのみ公開禁止）\n"
            f"→ {GHOST_URL}/ghost/"
        )
        _send_tg(msg, tok, cid)
        print(f"  Telegram: {len(stub_reports)}件アラート送信")

    # 状態保存
    _save_alerted(alerted)

    # ログファイルに記録
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as lf:
        lf.write(
            f"{ts} | checked={len(posts)} stubs={len(stub_reports)} ok={ok_count}"
            f" alerted={len(stub_reports) > 0}\n"
        )

    return 1 if stub_reports else 0


if __name__ == "__main__":
    sys.exit(main())
