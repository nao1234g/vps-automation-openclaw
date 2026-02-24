#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
polymarket_delta.py — Polymarket変動 × Nowpattern記事の自動照合

Polymarketのオッズ変動アラートと既存のNowpattern記事を照合し、
P2（差分提示型）記事の執筆提案をTelegramに送信する。

VPS cron:
  polymarket_monitor.py の直後に実行（アラートがある場合のみ通知）

使い方:
  python3 polymarket_delta.py              # レポートのみ
  python3 polymarket_delta.py --telegram   # Telegram送信
"""

from __future__ import annotations
import json
import os
import re
import sys
import datetime
import urllib.request
import urllib.error
import ssl

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Config ─────────────────────────────────────────────────────
DATA_DIR = "/opt/shared/polymarket"
CRON_ENV = "/opt/cron-env.sh"
GHOST_URL = "https://nowpattern.com"
MATCH_LOG = os.path.join(DATA_DIR, "delta_matches.json")

# Polymarket genre → Ghost genre slug mapping
POLY_TO_GHOST_GENRE = {
    "crypto": "crypto",
    "geopolitics": "geopolitics",
    "technology": "technology",
    "energy": "energy",
    "society": "society",
    "economic-policy": "economy",
    "financial-markets": "finance",
    "regulation": "governance",
    "security": "geopolitics",
    "corporate-strategy": "business",
    "science-health": "health",
    "climate": "environment",
    "space": "technology",
}

# Stopwords for title matching (minimal, no dependencies)
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "just", "about", "also", "and", "but", "or", "if",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "it", "its", "his", "her", "their", "our", "my", "your",
    "up", "out", "off", "over", "down", "s", "t", "re", "ve", "ll",
    # Japanese particles (for JA titles)
    "の", "は", "が", "を", "に", "で", "と", "も", "か", "へ", "や",
    "から", "まで", "より", "ため", "など", "って", "という", "する",
    "した", "して", "される", "された", "ある", "ない", "なる",
}


# ── Helper functions ───────────────────────────────────────────

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


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_keywords(text):
    """Extract meaningful keywords from title text."""
    text = text.lower()
    # Remove punctuation except hyphens
    text = re.sub(r"[^\w\s\-\u3000-\u9fff\uff00-\uffef]", " ", text)
    words = text.split()
    return {w for w in words if w not in STOPWORDS and len(w) > 1}


def ghost_jwt(api_key):
    """Generate Ghost Admin API JWT."""
    import hmac
    import hashlib
    import base64
    kid, secret = api_key.split(":")
    iat = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "kid": kid, "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"iat": iat, "exp": iat + 300, "aud": "/admin/"}).encode()
    ).rstrip(b"=").decode()
    sig_input = f"{header}.{payload}".encode()
    signature = hmac.new(bytes.fromhex(secret), sig_input, hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"


def ghost_get(path, api_key):
    """GET request to Ghost Admin API."""
    url = f"{GHOST_URL}/ghost/api/admin{path}"
    token = ghost_jwt(api_key)
    headers = {
        "Authorization": f"Ghost {token}",
        "Accept-Version": "v5.0",
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read())


def send_telegram(text, env):
    """Send message to owner's Telegram."""
    bot_token = env.get("NEO_BOT_TOKEN", env.get("TELEGRAM_BOT_TOKEN", ""))
    chat_id = env.get("TELEGRAM_CHAT_ID", env.get("NEO_CHAT_ID", ""))
    if not bot_token or not chat_id:
        print("WARN: Telegram credentials not found")
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


# ── Core matching ──────────────────────────────────────────────

def fetch_ghost_articles(api_key):
    """Fetch all Ghost articles with tags."""
    result = ghost_get("/posts/?limit=all&include=tags&fields=id,slug,title,url,published_at", api_key)
    posts = result.get("posts", [])
    articles = []
    for p in posts:
        tags = p.get("tags", [])
        genres = []
        events = []
        dynamics = []
        is_ja = False
        for t in tags:
            s = t["slug"]
            if s in ("nowpattern", "deep-pattern"):
                continue
            if s.startswith("lang-"):
                if s == "lang-ja":
                    is_ja = True
                continue
            if s.startswith("event-"):
                events.append(s)
            elif s.startswith("p-"):
                dynamics.append(s)
            elif s in POLY_TO_GHOST_GENRE.values():
                genres.append(s)

        articles.append({
            "id": p["id"],
            "slug": p["slug"],
            "title": p["title"],
            "url": p.get("url", f"{GHOST_URL}/{p['slug']}/"),
            "published_at": p.get("published_at", ""),
            "genres": genres,
            "events": events,
            "dynamics": dynamics,
            "is_ja": is_ja,
            "keywords": extract_keywords(p["title"]),
        })
    return articles


def match_alert_to_articles(alert, snapshot_event, articles):
    """Match a Polymarket alert to existing Nowpattern articles.

    Returns list of (article, score, reasons) tuples sorted by score desc.
    """
    # Get Polymarket event genres → Ghost genre slugs
    poly_genres = set()
    event_genres = snapshot_event.get("genres", []) if snapshot_event else []
    for g in event_genres:
        slug = g.get("slug", "")
        ghost_slug = POLY_TO_GHOST_GENRE.get(slug, slug)
        poly_genres.add(ghost_slug)

    # Keywords from Polymarket event title + market question
    event_title = snapshot_event.get("title", "") if snapshot_event else ""
    market_question = alert.get("market_question", alert.get("question", ""))
    poly_keywords = extract_keywords(event_title) | extract_keywords(market_question)

    matches = []
    for article in articles:
        score = 0
        reasons = []

        # Genre overlap (weighted heavily)
        genre_overlap = poly_genres & set(article["genres"])
        if genre_overlap:
            score += len(genre_overlap) * 3
            reasons.append(f"genre: {', '.join(genre_overlap)}")

        # Keyword overlap
        kw_overlap = poly_keywords & article["keywords"]
        if len(kw_overlap) >= 2:
            score += len(kw_overlap)
            reasons.append(f"keywords({len(kw_overlap)}): {', '.join(list(kw_overlap)[:5])}")

        # Minimum threshold: genre match + 2 keywords, OR 4+ keywords
        if (genre_overlap and len(kw_overlap) >= 2) or len(kw_overlap) >= 4:
            matches.append((article, score, reasons))

    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:3]  # top 3 matches


# ── Report generation ──────────────────────────────────────────

def generate_delta_report(alerts, snapshot, articles):
    """Generate delta report matching alerts to articles."""
    if not alerts:
        return [], "No alerts to process."

    all_matches = []
    report_lines = []
    report_lines.append(f"=== Polymarket Delta Report ===")
    report_lines.append(f"Alerts: {len(alerts)}")
    report_lines.append(f"Articles: {len(articles)}")
    report_lines.append("")

    events_data = snapshot if isinstance(snapshot, dict) else {}

    for alert in alerts:
        event_id = str(alert.get("event_id", ""))
        event_data = events_data.get(event_id, {})
        event_title = event_data.get("title", alert.get("event_title", "?"))
        market_q = alert.get("market_question", alert.get("question", "?"))
        prev = alert.get("prev_prob", 0)
        curr = alert.get("curr_prob", 0)
        delta = alert.get("delta", curr - prev)
        direction = "+" if delta > 0 else ""

        report_lines.append(f"[Alert] {event_title}")
        report_lines.append(f"  Market: {market_q}")
        report_lines.append(f"  Change: {prev*100:.1f}% → {curr*100:.1f}% ({direction}{delta*100:.1f}%)")

        matches = match_alert_to_articles(alert, event_data, articles)
        if matches:
            for article, score, reasons in matches:
                lang = "JA" if article["is_ja"] else "EN"
                report_lines.append(f"  → MATCH [{lang}] {article['title'][:60]}")
                report_lines.append(f"    Score: {score}, Reasons: {'; '.join(reasons)}")
                report_lines.append(f"    URL: {article['url']}")
                all_matches.append({
                    "alert": alert,
                    "event_title": event_title,
                    "market_question": market_q,
                    "prev_prob": prev,
                    "curr_prob": curr,
                    "delta": delta,
                    "article_slug": article["slug"],
                    "article_title": article["title"],
                    "article_url": article["url"],
                    "article_dynamics": article["dynamics"],
                    "score": score,
                    "is_ja": article["is_ja"],
                })
        else:
            report_lines.append("  → No matching article found")
        report_lines.append("")

    return all_matches, "\n".join(report_lines)


# ── Dynamics name mapping ──────────────────────────────────────

DYNAMICS_JA = {
    "p-platform": "プラットフォーム支配", "p-capture": "規制の捕獲",
    "p-narrative": "物語の覇権", "p-overreach": "権力の過伸展",
    "p-escalation": "対立の螺旋", "p-alliance-strain": "同盟の亀裂",
    "p-path-dependency": "経路依存", "p-backlash": "揺り戻し",
    "p-institutional-rot": "制度の劣化", "p-collective-failure": "協調の失敗",
    "p-moral-hazard": "モラルハザード", "p-contagion": "伝染の連鎖",
    "p-shock-doctrine": "危機便乗", "p-tech-leapfrog": "後発逆転",
    "p-winner-takes-all": "勝者総取り", "p-legitimacy-void": "正統性の空白",
}


def format_telegram_message(matches):
    """Format delta matches as Telegram HTML message."""
    if not matches:
        return None

    lines = ["<b>📊 Polymarket Delta Alert</b>", ""]

    seen_articles = set()
    for m in matches:
        slug = m["article_slug"]
        if slug in seen_articles:
            continue
        seen_articles.add(slug)

        delta = m["delta"]
        arrow = "📈" if delta > 0 else "📉"
        direction = "+" if delta > 0 else ""
        dynamics_ja = [DYNAMICS_JA.get(d, d) for d in m["article_dynamics"]]

        lines.append(f"{arrow} <b>{m['market_question'][:80]}</b>")
        lines.append(f"  {m['prev_prob']*100:.0f}% → {m['curr_prob']*100:.0f}% ({direction}{delta*100:.1f}%)")
        lines.append("")
        lines.append(f"📝 関連記事: <a href=\"{m['article_url']}\">{m['article_title'][:60]}</a>")
        if dynamics_ja:
            lines.append(f"  力学: {' × '.join(dynamics_ja)}")
        lines.append("")
        lines.append("💡 <b>P2（差分提示型）記事の提案:</b>")
        lines.append(f"  Polymarketの確率が{direction}{abs(delta)*100:.0f}%変動。")
        lines.append(f"  前回記事のシナリオ確率を更新するDeep Pattern記事を検討。")
        lines.append("─" * 30)
        lines.append("")

    lines.append(f"<i>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} JST</i>")
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Polymarket Delta → Article Trigger")
    parser.add_argument("--telegram", action="store_true", help="Send to Telegram")
    args = parser.parse_args()

    env = load_env()
    api_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not api_key:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not found")
        sys.exit(1)

    # Load data
    alerts = load_json(os.path.join(DATA_DIR, "alerts.json")) or []
    snapshot = load_json(os.path.join(DATA_DIR, "latest_snapshot.json")) or {}

    if not alerts:
        print("No alerts. Nothing to do.")
        return

    print(f"Loaded {len(alerts)} alerts")

    # Fetch Ghost articles
    articles = fetch_ghost_articles(api_key)
    print(f"Fetched {len(articles)} Ghost articles")

    # Match
    matches, report = generate_delta_report(alerts, snapshot, articles)
    print(report)

    # Save matches
    if matches:
        with open(MATCH_LOG, "w", encoding="utf-8") as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        print(f"\nSaved {len(matches)} matches to {MATCH_LOG}")

    # Telegram
    if args.telegram and matches:
        msg = format_telegram_message(matches)
        if msg:
            ok = send_telegram(msg, env)
            print(f"Telegram: {'OK' if ok else 'FAILED'}")
    elif args.telegram and not matches:
        print("No matches → no Telegram notification")


if __name__ == "__main__":
    main()
