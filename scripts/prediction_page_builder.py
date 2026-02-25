#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prediction_page_builder.py — Prediction Tracker公開ページ生成（日英対応）

既存の prediction_tracker.py (prediction_db.json) + Polymarket embed_data.json を
統合して、Ghost /predictions/ (JA) と /en/predictions/ (EN) ページを自動更新。

VPS cron (1日1回):
  python3 /opt/shared/scripts/prediction_page_builder.py

手動:
  python3 prediction_page_builder.py --report   # データ確認のみ
  python3 prediction_page_builder.py --update    # Ghost更新（日英両方）
  python3 prediction_page_builder.py --update --lang ja  # 日本語のみ
  python3 prediction_page_builder.py --update --lang en  # 英語のみ
"""

from __future__ import annotations
import json
import os
import re
import sqlite3
import sys
import hmac
import hashlib
import base64
import urllib.request
import ssl
from datetime import datetime, timezone

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Config ─────────────────────────────────────────────────────
CRON_ENV = "/opt/cron-env.sh"
GHOST_URL = "https://nowpattern.com"
PREDICTION_DB = "/opt/shared/scripts/prediction_db.json"
EMBED_DATA = "/opt/shared/polymarket/embed_data.json"
TRACKER_OUTPUT = "/opt/shared/polymarket/tracker_page_data.json"
PREDICTIONS_SLUG_JA = "predictions"
PREDICTIONS_SLUG_EN = "en-predictions"
MARKET_HISTORY_DB = "/opt/shared/market_history/market_history.db"
GEMINI_FLASH_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

POLY_TO_GHOST = {
    "crypto": "crypto", "geopolitics": "geopolitics",
    "technology": "technology", "energy": "energy",
    "society": "society", "economic-policy": "economy",
    "financial-markets": "finance", "regulation": "governance",
    "security": "geopolitics", "corporate-strategy": "business",
}

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

DYNAMICS_EN = {
    "p-platform": "Platform Dominance", "p-capture": "Regulatory Capture",
    "p-narrative": "Narrative Control", "p-overreach": "Power Overreach",
    "p-escalation": "Escalation Spiral", "p-alliance-strain": "Alliance Strain",
    "p-path-dependency": "Path Dependency", "p-backlash": "Backlash",
    "p-institutional-rot": "Institutional Decay", "p-collective-failure": "Coordination Failure",
    "p-moral-hazard": "Moral Hazard", "p-contagion": "Contagion",
    "p-shock-doctrine": "Shock Doctrine", "p-tech-leapfrog": "Tech Leapfrog",
    "p-winner-takes-all": "Winner Takes All", "p-legitimacy-void": "Legitimacy Void",
}

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "and", "but", "or", "it",
    "will", "would", "can", "has", "have", "not", "this", "that", "all",
    "の", "は", "が", "を", "に", "で", "と", "も", "する", "した",
}

# ── UI constants ───────────────────────────────────────────────
MARKET_ACCURACY_PCT = 68  # TODO: auto-fetch from Manifold aggregate

CATEGORY_LABELS = {
    "ja": [("all", "全て"), ("economy", "経済・貿易"), ("geopolitics", "地政学"),
           ("technology", "テクノロジー"), ("finance", "金融")],
    "en": [("all", "All"), ("economy", "Economy"), ("geopolitics", "Geopolitics"),
           ("technology", "Technology"), ("finance", "Finance")],
}

# ── I18N labels ───────────────────────────────────────────────

LABELS = {
    "ja": {
        "page_title": "予測トラッカー — Nowpatternの分析 vs 市場",
        "hero_heading": "Nowpatternの予測、当たってる？",
        "hero_text": (
            'Nowpatternは毎回の記事で「これは何%の確率で起きる」と予測しています。<br>'
            'このページでは、その予測を<strong style="color:#2563eb">世界中の人が実際にお金を賭けている確率</strong>と比較します。'
        ),
        "stat_predictions": "件の予測",
        "stat_tracking": "件を追跡中",
        "stat_resolved": "件の結果が出た",
        "last_updated": "最終更新",
        "featured_heading": "私たちの予測 vs 賭け市場",
        "featured_desc": (
            '<span style="color:#16a34a;font-weight:700">緑</span> = 私たちの予測 ／ '
            '<span style="color:#2563eb;font-weight:700">青</span> = 賭け市場（Polymarket）の確率。'
            'バーが長い方が「起きる」と見ている。'
        ),
        "resolved_heading": "結果が出た予測",
        "resolved_desc": "過去の予測と、実際にどうなったかの記録です。",
        "no_resolved": "まだ結果が確定した予測はありません。<br>予測の対象イベントが起きた（または起きなかった）時に、ここに結果が記録されます。",
        "tracking_summary": "追跡中の全予測を見る（{count}件）",
        "overflow": "...他 {count} 件",
        "footer_polymarket": "賭け市場のデータ: ",
        "footer_polymarket_desc": "（世界最大の予測市場。実際にお金を賭けて予測する仕組み）",
        "footer_auto": "このページは毎日自動で更新されます。",
        "bar_ours": "私たち",
        "bar_market": "市場",
        "market_q_label": "賭け市場の質問",
        "market_higher": "市場の方が「起きる」と見ている",
        "market_lower": "市場の方が「起きにくい」と見ている",
        "diff_small": "少し見方が違う",
        "diff_same": "ほぼ同じ見方",
        "analyzing": "分析中",
        "prediction_at": "予測時",
        "outcome_optimistic": ("良い方向に進んだ", "#16a34a", "&#9650;"),
        "outcome_base": ("予想通りの展開", "#3b82f6", "&#9644;"),
        "outcome_pessimistic": ("悪い方向に進んだ", "#dc2626", "&#9660;"),
        "outcome_default": ("結果確定", "#888", "?"),
        "accuracy_hit": "的中",
        "accuracy_ok": "まずまず",
        "accuracy_miss": "外れ",
        "what_probability": "が起きる確率",
        "en_link": '<a href="/en-predictions/" style="color:#b8860b;font-size:0.9em">English version →</a>',
        "other_lang_link": '<a href="/en-predictions/" style="color:#b8860b;font-size:0.9em">English version →</a>',
        "scoreboard_title": "🎯 予測精度スコアボード",
        "scoreboard_hit": "件的中",
        "scoreboard_miss": "件外れ",
        "scoreboard_brier": "Brier Score",
        "scoreboard_brier_good": "（上位10%水準）",
        "scoreboard_brier_ok": "（標準水準）",
        "scoreboard_brier_bad": "（改善余地あり）",
        "scoreboard_no_data": "まだ結果が出た予測がありません",
        "linked_market": "追跡市場",
        "expand_hint": "▼ 詳細を見る",
        "collapse_hint": "▲ 閉じる",
        "tracking_section_title": "追跡中の予測",
        "page_label": "予測トラッカー",
        "lang_toggle": (
            '<div style="display:flex;gap:6px">'
            '<span style="padding:3px 12px;border-radius:4px;background:#b8860b;color:#fff;'
            'font-size:0.85em;font-weight:700">JA</span>'
            '<a href="/en-predictions/" style="padding:3px 12px;border-radius:4px;'
            'background:#f0f0f0;color:#555;text-decoration:none;font-size:0.85em">EN</a>'
            '</div>'
        ),
    },
    "en": {
        "page_title": "Prediction Tracker — Nowpattern vs Market",
        "hero_heading": "Are Nowpattern's Predictions Accurate?",
        "hero_text": (
            'Every Nowpattern article includes probability forecasts for key events.<br>'
            'This page compares our predictions with <strong style="color:#2563eb">real-money betting odds</strong> from Polymarket.'
        ),
        "stat_predictions": "predictions",
        "stat_tracking": "tracking",
        "stat_resolved": "resolved",
        "last_updated": "Last updated",
        "featured_heading": "Our Predictions vs Betting Market",
        "featured_desc": (
            '<span style="color:#16a34a;font-weight:700">Green</span> = Our prediction / '
            '<span style="color:#2563eb;font-weight:700">Blue</span> = Polymarket betting odds. '
            'Longer bar = higher probability.'
        ),
        "resolved_heading": "Resolved Predictions",
        "resolved_desc": "Past predictions and what actually happened.",
        "no_resolved": "No predictions have been resolved yet.<br>Results will appear here once predicted events occur (or don't).",
        "tracking_summary": "View all tracked predictions ({count})",
        "overflow": "...and {count} more",
        "footer_polymarket": "Betting market data: ",
        "footer_polymarket_desc": " (world's largest prediction market — real money on the line)",
        "footer_auto": "This page is updated daily.",
        "bar_ours": "Ours",
        "bar_market": "Market",
        "market_q_label": "Market question",
        "market_higher": "Market sees it as more likely",
        "market_lower": "Market sees it as less likely",
        "diff_small": "Slightly different views",
        "diff_same": "Nearly the same view",
        "analyzing": "Analyzing",
        "prediction_at": "Predicted",
        "outcome_optimistic": ("Optimistic outcome", "#16a34a", "&#9650;"),
        "outcome_base": ("Base case outcome", "#3b82f6", "&#9644;"),
        "outcome_pessimistic": ("Pessimistic outcome", "#dc2626", "&#9660;"),
        "outcome_default": ("Resolved", "#888", "?"),
        "accuracy_hit": "Accurate",
        "accuracy_ok": "Close",
        "accuracy_miss": "Missed",
        "what_probability": "probability",
        "en_link": "",
        "other_lang_link": '<a href="/predictions/" style="color:#b8860b;font-size:0.9em">← 日本語版</a>',
        "scoreboard_title": "🎯 Prediction Accuracy",
        "scoreboard_hit": "accurate",
        "scoreboard_miss": "missed",
        "scoreboard_brier": "Brier Score",
        "scoreboard_brier_good": "(top 10% level)",
        "scoreboard_brier_ok": "(standard level)",
        "scoreboard_brier_bad": "(room for improvement)",
        "scoreboard_no_data": "No resolved predictions yet",
        "linked_market": "Tracking Market",
        "expand_hint": "▼ See details",
        "collapse_hint": "▲ Collapse",
        "tracking_section_title": "Tracked Predictions",
        "page_label": "Prediction Tracker",
        "lang_toggle": (
            '<div style="display:flex;gap:6px">'
            '<a href="/predictions/" style="padding:3px 12px;border-radius:4px;'
            'background:#f0f0f0;color:#555;text-decoration:none;font-size:0.85em">JA</a>'
            '<span style="padding:3px 12px;border-radius:4px;background:#b8860b;color:#fff;'
            'font-size:0.85em;font-weight:700">EN</span>'
            '</div>'
        ),
    },
}


# ── Ghost API ──────────────────────────────────────────────────

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


def ghost_jwt(api_key):
    kid, secret = api_key.split(":")
    iat = int(datetime.now(timezone.utc).timestamp())
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "kid": kid, "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"iat": iat, "exp": iat + 300, "aud": "/admin/"}).encode()
    ).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(
        hmac.new(bytes.fromhex(secret), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"


def ghost_request(method, path, api_key, data=None):
    url = f"{GHOST_URL}/ghost/api/admin{path}"
    headers = {
        "Authorization": f"Ghost {ghost_jwt(api_key)}",
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


# ── Data loading ───────────────────────────────────────────────

def load_prediction_db():
    if os.path.exists(PREDICTION_DB):
        with open(PREDICTION_DB, encoding="utf-8") as f:
            return json.load(f)
    return {"predictions": [], "stats": {}}


def load_embed_data():
    if os.path.exists(EMBED_DATA):
        with open(EMBED_DATA, encoding="utf-8") as f:
            return json.load(f)
    return []


def load_linked_markets():
    """
    market_history.db の nowpattern_links + probability_snapshots を読み込む。
    returns: {prediction_id: {"question": str, "yes_prob": float, "direction": str,
                               "market_source": str, "market_slug": str, "event_slug": str,
                               "external_id": str}}
    """
    if not os.path.exists(MARKET_HISTORY_DB):
        return {}
    try:
        db = sqlite3.connect(MARKET_HISTORY_DB)
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute("""
            SELECT nl.prediction_id, nl.resolution_direction,
                   nl.source as link_source, nl.external_market_id,
                   m.question, m.close_date, m.source as m_source,
                   m.market_slug, m.event_slug, m.external_id,
                   ps.yes_prob, ps.snapshot_date
            FROM nowpattern_links nl
            JOIN markets m ON nl.market_id = m.id
            LEFT JOIN (
                SELECT market_id, yes_prob, snapshot_date
                FROM probability_snapshots
                WHERE (market_id, snapshot_date) IN (
                    SELECT market_id, MAX(snapshot_date)
                    FROM probability_snapshots GROUP BY market_id
                )
            ) ps ON m.id = ps.market_id
        """)
        result = {}
        for row in cur.fetchall():
            result[row["prediction_id"]] = {
                "question": row["question"],
                "yes_prob": row["yes_prob"],
                "direction": row["resolution_direction"],
                "close_date": row["close_date"],
                "snapshot_date": row["snapshot_date"],
                "market_source": row["m_source"] or row["link_source"] or "",
                "market_slug": row["market_slug"] or "",
                "event_slug": row["event_slug"] or "",
                "external_id": row["external_id"] or row["external_market_id"] or "",
            }
        db.close()
        return result
    except Exception:
        return {}


def _get_market_url(linked):
    """linked_markets データから市場WebページのURLを構築する。"""
    if not linked:
        return None
    source = linked.get("market_source") or ""
    market_slug = linked.get("market_slug", "")
    event_slug = linked.get("event_slug", "")
    external_id = linked.get("external_id", "")

    if source == "polymarket":
        if event_slug:
            return f"https://polymarket.com/event/{event_slug}"
        if market_slug:
            slug = market_slug.replace("polymarket-", "")
            return f"https://polymarket.com/event/{slug}"
    elif source == "manifold":
        if market_slug:
            slug = market_slug.replace("manifold-", "")
            return f"https://manifold.markets/{slug}"
    elif source == "kalshi":
        if external_id:
            return f"https://kalshi.com/markets/{external_id}"
    elif source == "metaculus":
        if external_id:
            return f"https://www.metaculus.com/questions/{external_id}/"
    return None


def _translate_to_ja(text, api_key):
    """Translate English text to Japanese via Gemini Flash. Returns translated text or original on error."""
    if not api_key or not text:
        return text
    try:
        payload = json.dumps({
            "contents": [{"parts": [{"text": (
                "以下の英語を自然な日本語に翻訳してください。"
                "翻訳結果のみを出力してください:\n\n" + text
            )}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200},
        })
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = f"{GEMINI_FLASH_URL}?key={api_key}"
        req = urllib.request.Request(
            url, data=payload.encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"  Gemini translate error: {e}")
        return text


def ensure_ja_translations(pred_db, google_api_key):
    """
    Check all predictions for resolution_question_ja.
    If missing and google_api_key is available, translate via Gemini Flash and save back to DB.
    One-time operation per prediction — skipped if resolution_question_ja already exists.
    """
    changed = False
    for pred in pred_db.get("predictions", []):
        rq = pred.get("resolution_question", "")
        rq_ja = pred.get("resolution_question_ja", "")
        if rq and not rq_ja:
            if not google_api_key:
                print(f"  [translate] GOOGLE_API_KEY missing — skip: {rq[:50]}")
                continue
            translated = _translate_to_ja(rq, google_api_key)
            if translated and translated != rq:
                pred["resolution_question_ja"] = translated
                changed = True
                print(f"  [translate] {rq[:50]} → {translated[:50]}")
            else:
                print(f"  [translate] No change for: {rq[:50]}")
    if changed:
        with open(PREDICTION_DB, "w", encoding="utf-8") as f:
            json.dump(pred_db, f, ensure_ascii=False, indent=2)
        print(f"  [translate] Saved translations to {PREDICTION_DB}")
    return pred_db


def _is_japanese(text):
    """Check if text contains Japanese characters."""
    return any('\u3000' <= c <= '\u9fff' or '\uff00' <= c <= '\uffef' for c in text)


def _is_english(text):
    """Check if text is primarily English (Latin characters dominate)."""
    if not text:
        return False
    latin = sum(1 for c in text if 'A' <= c <= 'z')
    return latin > len(text) * 0.5 and not _is_japanese(text)


def extract_scenarios_from_html(html):
    """Extract scenarios from article HTML (fallback for articles not in prediction_db)."""
    scenarios = {}
    for label_re, key in [
        ("Base|基本", "base"), ("Optimistic|楽観", "optimistic"),
        ("Pessimistic|悲観", "pessimistic"),
    ]:
        m = re.search(rf"(?:{label_re})[^<]*?(\d+)(?:-\d+)?%", html, re.IGNORECASE)
        if m:
            scenarios[key] = int(m.group(1))
    return scenarios if scenarios else None


def extract_event_summary(pred):
    """Extract a short description of WHAT is being predicted.
    Uses scenario content, open_loop_trigger, or title keywords."""
    import ast
    # 1) open_loop_trigger is the best source
    trigger = pred.get("open_loop_trigger", "")
    if trigger:
        if isinstance(trigger, dict):
            return trigger.get("name", trigger.get("content", str(trigger)))[:80]
        if isinstance(trigger, str) and trigger.strip().startswith("{"):
            try:
                d = ast.literal_eval(trigger)
                if isinstance(d, dict):
                    return d.get("name", d.get("content", str(d)))[:80]
            except Exception:
                pass
        return str(trigger)[:80]
    # 2) triggers list
    triggers = pred.get("triggers", [])
    if triggers and triggers[0]:
        t = triggers[0]
        if isinstance(t, dict):
            name = t.get("name", "")
            date = t.get("date", "")
            return (name + (f"（{date}）" if date else ""))[:80]
        elif isinstance(t, list):
            return t[0][:80]
        else:
            return str(t)[:80]
    # 3) Base scenario content
    for s in pred.get("scenarios", []):
        label = s.get("label", "").lower()
        if "基本" in label or "base" in label:
            content = s.get("content", "")
            if content:
                return content[:80]
    return ""


def extract_keywords(text):
    text = text.lower()
    text = re.sub(r"[^\w\s\-\u3000-\u9fff]", " ", text)
    return {w for w in text.split() if w not in STOPWORDS and len(w) > 1}


# ── Polymarket matching ────────────────────────────────────────

def find_metaculus_match(title):
    """Search Manifold Markets API for a binary prediction market matching the article title.
    Returns dict with {question, probability, url} or None.

    NOTE: Uses Manifold Markets API (Metaculus API no longer exposes probability data).
    Strategy: extract proper nouns (capitalized entities) as primary search terms,
    fall back to longest content words. Accepts ~30-40% match rate as normal.
    API: https://api.manifold.markets/v0/search-markets
    """
    import urllib.request
    import urllib.parse
    import json as _json
    import ssl
    import re as _re

    # Extract proper nouns (capitalized words, 4+ chars) — most likely entities
    _SKIP_CAPS = {
        "The", "This", "That", "With", "From", "After", "Before", "Into",
        "When", "What", "Will", "Were", "Have", "Their", "There", "Been",
        "They", "These", "Those", "Would", "Could", "Should", "About",
        "Than", "Then", "More", "Most", "Such", "Even", "Over", "Also",
    }
    cap_words = [
        w for w in _re.findall(r"[A-Z][a-zA-Z]{3,}", title)
        if w not in _SKIP_CAPS
    ]

    # Build 2-3 search queries to try
    queries = []
    if len(cap_words) >= 2:
        queries.append(" ".join(cap_words[:2]))          # Top 2 entities
    if len(cap_words) >= 1:
        queries.append(cap_words[0])                     # Main entity alone
    # Fallback: 3 longest words
    long_words = sorted(
        [w for w in _re.findall(r"[a-zA-Z]{5,}", title)],
        key=len, reverse=True
    )[:3]
    if long_words:
        queries.append(" ".join(long_words[:2]))

    # Deduplicate queries
    seen = set()
    unique_queries = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)

    try:
        ctx = ssl.create_default_context()
        headers = {"User-Agent": "Nowpattern/1.0"}

        for query in unique_queries[:3]:
            enc = urllib.parse.quote(query)
            url = (
                f"https://api.manifold.markets/v0/search-markets"
                f"?term={enc}&filter=open&sort=score&limit=5"
            )
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                markets = _json.loads(resp.read())
            for m in markets:
                prob = m.get("probability")
                if prob is None:
                    continue
                if not (0.03 <= prob <= 0.97):
                    continue
                return {
                    "question": m.get("question", "")[:80],
                    "probability": round(prob * 100),
                    "url": m.get("url", f"https://manifold.markets/{m.get('id', '')}"),
                    "id": m.get("id", ""),
                }
        return None
    except Exception:
        return None


def find_polymarket_match(title, genres, embed_data):
    """Find best Polymarket match for an article."""
    article_kw = extract_keywords(title)
    article_genres = set(genres) if isinstance(genres, list) else set()
    best = None
    best_score = 0

    for m in embed_data:
        score = 0
        poly_genres = {POLY_TO_GHOST.get(g, g) for g in m.get("genres", [])}
        overlap = article_genres & poly_genres
        if overlap:
            score += len(overlap) * 3
        mkw = extract_keywords(m.get("title", "") + " " + m.get("question", ""))
        kw_hit = article_kw & mkw
        if len(kw_hit) >= 2:
            score += len(kw_hit)
        if score > best_score and (overlap and len(kw_hit) >= 2 or len(kw_hit) >= 4):
            best_score = score
            best = {
                "question": m.get("question", "")[:60],
                "probability": m.get("probability", 0),
                "outcomes": m.get("outcomes"),  # {"Yes": xx, "No": yy} 0-100%
                "volume_usd": m.get("volume_usd", 0),
            }
    return best


# ── Row builder (language-aware) ──────────────────────────────

def build_rows(pred_db, ghost_posts, embed_data, lang="ja"):
    """Build unified rows filtered by language."""
    rows = []
    seen_slugs = set()
    seen_titles = set()

    # Load market_history.db nowpattern_links (Pattern A data)
    linked_markets = load_linked_markets()

    # Source 1: prediction_db.json (authoritative)
    for pred in pred_db.get("predictions", []):
        title = pred.get("article_title", "")

        # Language filter
        if lang == "ja" and not _is_japanese(title):
            continue
        if lang == "en" and _is_japanese(title):
            continue

        scenarios = pred.get("scenarios", [])
        base = opt = pess = None
        base_content = opt_content = pess_content = ""
        for s in scenarios:
            label = s.get("label", "").lower()
            prob = s.get("probability", 0)
            if prob > 1:
                prob = prob / 100
            prob_pct = round(prob * 100)
            if "基本" in label or "base" in label:
                base = prob_pct
                base_content = s.get("content", "")
            elif "楽観" in label or "optimistic" in label:
                opt = prob_pct
                opt_content = s.get("content", "")
            elif "悲観" in label or "pessimistic" in label:
                pess = prob_pct
                pess_content = s.get("content", "")

        if base is None and opt is None and pess is None:
            continue

        genres = []
        genre_str = pred.get("genre_tags", "")
        if genre_str:
            genres = [g.strip().lower() for g in genre_str.split(",")]

        # prediction_dbエントリには自動マッチを使わない（不整合の原因）
        # 市場データはmarket_consensusフィールドで明示的に設定する
        pm_match = None  # find_polymarket_match disabled for prediction_db
        mc_match = None  # find_metaculus_match disabled for prediction_db
        divergence = None
        if pm_match and base is not None:
            divergence = round(pm_match["probability"] - base, 1)

        dynamics_str = pred.get("dynamics_tags", "")
        url = pred.get("ghost_url", "")

        # Extract event summary for context
        event_summary = extract_event_summary(pred)

        # Pattern A: nowpattern_links から market_history.db の追跡市場を取得
        prediction_id = pred.get("prediction_id", "")
        linked = linked_markets.get(prediction_id)
        linked_market_question = linked["question"] if linked else None
        linked_market_prob = linked["yes_prob"] if linked else None  # 0.0〜1.0

        # Trigger date from first trigger or linked market close_date
        trigger_date = ""
        triggers = pred.get("triggers", [])
        if triggers:
            t0 = triggers[0]
            if isinstance(t0, dict):
                trigger_date = (t0.get("date") or "")[:10]
        if not trigger_date and linked:
            trigger_date = (linked.get("close_date") or "")[:10]

        _validate_market_consensus(pred)
        row = {
            "title": title,
            "url": url,
            "base": base, "optimistic": opt, "pessimistic": pess,
            "base_content": base_content,
            "opt_content": opt_content,
            "pess_content": pess_content,
            "event_summary": event_summary,
            "polymarket": pm_match,
            "metaculus": mc_match,
            "divergence": divergence,
            "status": pred.get("status", "open"),
            "outcome": pred.get("outcome"),
            "resolved_at": pred.get("resolved_at", ""),
            "brier": pred.get("brier_score"),
            "dynamics_str": dynamics_str,
            "source": "prediction_db",
            "genres": genres,
            "trigger_date": trigger_date,
            "published_at": pred.get("published_at", ""),
            # Pattern A fields
            "prediction_id": prediction_id,
            "linked_market_question": linked_market_question,
            "linked_market_prob": linked_market_prob,
            "linked_market_url": _get_market_url(linked) if linked else None,
            "linked_market_source": linked.get("market_source", "") if linked else "",
            "resolution_question": pred.get("resolution_question", ""),
            "resolution_question_ja": pred.get("resolution_question_ja", ""),
            "resolution_direction": pred.get("resolution_direction", "optimistic"),
            "our_stance": pred.get("our_stance"),
            "our_pick": pred.get("our_pick"),
            "our_pick_prob": pred.get("our_pick_prob"),
            "question_type": pred.get("question_type", "binary"),
            "hit_condition_ja": pred.get("hit_condition_ja", ""),
            "hit_condition_en": pred.get("hit_condition_en", ""),
            "market_consensus": pred.get("market_consensus"),  # validated by _validate_market_consensus,
            "hit_miss": pred.get("hit_miss"),
            # Phase 2: Evidence chain + tamper detection
            "resolution_evidence": pred.get("resolution_evidence"),
            "integrity_hash": pred.get("integrity_hash"),
            "dispute_reason": pred.get("dispute_reason", ""),
            # Phase 3: Rebuttals
            "rebuttals": pred.get("rebuttals", []),
        }
        rows.append(row)

        slug = url.split("/")[-2] if url else ""
        if slug:
            seen_slugs.add(slug)
        seen_titles.add(title)

    # Source 2: Ghost articles (fallback for articles not in prediction_db)
    for p in ghost_posts:
        if p["slug"] in seen_slugs:
            continue
        if p.get("title", "") in seen_titles:
            continue

        tags = p.get("tags", [])
        is_ja = any(t["slug"] == "lang-ja" for t in tags)
        is_en = any(t["slug"] == "lang-en" for t in tags)
        title = p.get("title", "")
        title_has_ja = _is_japanese(title)

        # Language filter — strict: title language is the truth
        if lang == "ja":
            # JA page: title MUST contain Japanese characters
            if not title_has_ja:
                continue
        elif lang == "en":
            # EN page: title must NOT contain Japanese characters
            if title_has_ja:
                continue

        html = p.get("html", "") or ""
        scenarios = extract_scenarios_from_html(html)
        if not scenarios:
            continue

        genres = [t["slug"] for t in tags if t["slug"] in POLY_TO_GHOST.values()]
        dynamics = [t["slug"] for t in tags if t["slug"].startswith("p-")]

        # prediction_dbエントリには自動マッチを使わない（不整合の原因）
        # 市場データはmarket_consensusフィールドで明示的に設定する
        pm_match = find_polymarket_match(title, genres, embed_data)
        mc_match = find_metaculus_match(title)
        divergence = None
        if pm_match and scenarios.get("base"):
            divergence = round(pm_match["probability"] - scenarios["base"], 1)

        dyn_map = DYNAMICS_JA if lang == "ja" else DYNAMICS_EN
        dynamics_str = " × ".join(dyn_map.get(d, d) for d in dynamics[:2])

        row = {
            "title": title,
            "url": p.get("url", f"{GHOST_URL}/{p['slug']}/"),
            "base": scenarios.get("base"),
            "optimistic": scenarios.get("optimistic"),
            "pessimistic": scenarios.get("pessimistic"),
            "base_content": "",
            "opt_content": "",
            "pess_content": "",
            "event_summary": "",
            "polymarket": pm_match,
            "metaculus": mc_match,
            "divergence": divergence,
            "status": "open",
            "brier": None,
            "dynamics_str": dynamics_str,
            "source": "ghost_html",
            "genres": genres,
            "trigger_date": "",
            "published_at": p.get("published_at", ""),
            "prediction_id": "",
            "linked_market_question": None,
            "linked_market_prob": None,
        }
        rows.append(row)
        seen_slugs.add(p["slug"])

    return rows


# ── New HTML builder (Scrap & Build 2026-02-25) ────────────────

def _scoreboard_block(rows, lang):
    """BLOCK 1: Dark scoreboard grid (formal predictions only)."""
    # Only count formal prediction_db entries, not ghost_html articles
    formal = [r for r in rows if r.get("source") == "prediction_db"]
    resolved = [r for r in formal if r.get("status") == "resolved"]
    total = len(formal)
    # Use hit_miss field (authoritative). Fallback to brier < 0.25 for legacy rows without hit_miss.
    hits = sum(
        1 for r in resolved
        if r.get("hit_miss") in ("correct", "hit")
        or (r.get("hit_miss") is None and r.get("brier") is not None and r["brier"] < 0.25)
    )
    misses = sum(
        1 for r in resolved
        if r.get("hit_miss") in ("incorrect", "miss")
        or (r.get("hit_miss") is None and r.get("brier") is not None and r["brier"] >= 0.25)
    )
    hit_pct = round(hits / (hits + misses) * 100) if (hits + misses) > 0 else 0

    if lang == "ja":
        header_label = "Nowpatternの予測精度 — 2026年実績（自動更新）"
        total_label = "総予測数"
        hit_label = "✅ 的中"
        miss_label = "❌ 外れ"
        acc_label = "的中率"
        # Comparison bar removed — market accuracy reference not needed
    else:
        header_label = "Nowpattern Prediction Accuracy — 2026 Track Record (auto-updated)"
        total_label = "Total"
        hit_label = "✅ Accurate"
        miss_label = "❌ Missed"
        acc_label = "Accuracy"
        # Comparison bar removed — market accuracy reference not needed

    # 0件時のempty state
    if not resolved:
        empty_note = (
            "まだ解決済みの予測はありません。初解決をお楽しみに！"
            if lang == "ja"
            else "No resolved predictions yet. Stay tuned for the first result!"
        )
        return (
            '<div style="margin-bottom:24px;background:#fff;border-radius:12px;'
            'padding:24px 28px;box-shadow:0 2px 8px rgba(0,0,0,.08)">'
            f'<div style="font-size:0.75em;color:#888;letter-spacing:.08em;'
            f'text-transform:uppercase;margin-bottom:14px">{header_label}</div>'
            '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0;'
            'background:#111;border-radius:12px;padding:20px 24px;color:#fff;margin-bottom:14px">'
            '<div style="text-align:center;border-right:1px solid #333">'
            f'<div style="font-size:2.6em;font-weight:700;line-height:1">{total}</div>'
            f'<div style="font-size:0.78em;color:#888;margin-top:4px">{total_label}</div>'
            '</div>'
            '<div style="text-align:center;border-right:1px solid #333">'
            '<div style="font-size:2.6em;font-weight:700;color:#555;line-height:1">—</div>'
            f'<div style="font-size:0.78em;color:#888;margin-top:4px">{hit_label}</div>'
            '</div>'
            '<div style="text-align:center;border-right:1px solid #333">'
            '<div style="font-size:2.6em;font-weight:700;color:#555;line-height:1">—</div>'
            f'<div style="font-size:0.78em;color:#888;margin-top:4px">{miss_label}</div>'
            '</div>'
            '<div style="text-align:center">'
            '<div style="font-size:2.6em;font-weight:700;color:#555;line-height:1">—</div>'
            f'<div style="font-size:0.78em;color:#888;margin-top:4px">{acc_label}</div>'
            '</div>'
            '</div>'
            f'<div style="font-size:0.85em;color:#aaa;text-align:center;padding:4px 0">{empty_note}</div>'
            '</div>'
        )

    return (
        '<div style="margin-bottom:24px;background:#fff;border-radius:12px;'
        'padding:24px 28px;box-shadow:0 2px 8px rgba(0,0,0,.08)">'
        f'<div style="font-size:0.75em;color:#888;letter-spacing:.08em;'
        f'text-transform:uppercase;margin-bottom:14px">{header_label}</div>'
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0;'
        'background:#111;border-radius:12px;padding:20px 24px;color:#fff;margin-bottom:14px">'
        '<div style="text-align:center;border-right:1px solid #333">'
        f'<div style="font-size:2.6em;font-weight:700;line-height:1">{total}</div>'
        f'<div style="font-size:0.78em;color:#888;margin-top:4px">{total_label}</div>'
        '</div>'
        '<div style="text-align:center;border-right:1px solid #333">'
        f'<div style="font-size:2.6em;font-weight:700;color:#22c55e;line-height:1">{hits}</div>'
        f'<div style="font-size:0.78em;color:#888;margin-top:4px">{hit_label}</div>'
        '</div>'
        '<div style="text-align:center;border-right:1px solid #333">'
        f'<div style="font-size:2.6em;font-weight:700;color:#ef4444;line-height:1">{misses}</div>'
        f'<div style="font-size:0.78em;color:#888;margin-top:4px">{miss_label}</div>'
        '</div>'
        '<div style="text-align:center">'
        f'<div style="font-size:2.6em;font-weight:700;color:#fbbf24;line-height:1">{hit_pct}%</div>'
        f'<div style="font-size:0.78em;color:#888;margin-top:4px">{acc_label}</div>'
        '</div>'
        '</div>'
        '</div>'
    )


def _deadline_badge(trigger_date, lang, resolved=False):
    """Format deadline/resolution date as a small badge."""
    if not trigger_date:
        return ""
    try:
        parts = trigger_date.split("-")
        y, m = parts[0], int(parts[1])
        if lang == "ja":
            date_str = f"{y}年{m}月"
        else:
            import calendar
            date_str = f"{calendar.month_abbr[m]} {y}"
    except Exception:
        date_str = trigger_date
    if resolved:
        color, bg = "#16a34a", "#e8f5e9"
        prefix = ("📅 " + date_str + " 解決") if lang == "ja" else ("📅 Resolved " + date_str)
    else:
        color, bg = "#dc2626", "#fde8e8"
        prefix = ("📅 期限: " + date_str) if lang == "ja" else ("📅 Deadline: " + date_str)
    return (
        f'<span style="font-size:0.72em;color:{color};font-weight:600;'
        f'background:{bg};padding:1px 6px;border-radius:10px;white-space:nowrap">'
        f'{prefix}</span>'
    )


def _first_sentence(text, max_chars=100):
    """Extract first meaningful sentence (up to 。 or '. ')."""
    if not text:
        return ""
    ja_end = text.find("。")
    if 0 < ja_end <= max_chars:
        return text[:ja_end + 1]
    en_end = text.find(". ")
    if 0 < en_end <= max_chars:
        return text[:en_end + 1]
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rfind(" ")
    if cut > max_chars // 2:
        return text[:cut] + "…"
    return text[:max_chars] + "…"


def _scenario_chip(label, val, sub, bg, border, color):
    """Collapsed scenario chip (悲観/基本/楽観 with probability + sub-label)."""
    if val is None:
        return ""
    return (
        f'<div style="display:inline-flex;flex-direction:column;align-items:center;'
        f'padding:4px 10px;border-radius:6px;background:{bg};{border}min-width:52px">'
        f'<span style="font-size:0.68em;color:{color};font-weight:600">{label}</span>'
        f'<span style="font-size:0.95em;font-weight:700;color:{color}">{val}%</span>'
        f'</div>'
    )


def _scenario_box_exp(label, val, sub, bg, border, color):
    """Expanded scenario box — label and percentage only (text in accordion below)."""
    if val is None:
        return ""
    return (
        f'<div style="flex:1;background:{bg};border-radius:6px;padding:12px 6px;'
        f'text-align:center;{border}">'
        f'<div style="font-size:0.7em;color:{color};font-weight:600;margin-bottom:4px">{label}</div>'
        f'<div style="font-size:1.4em;font-weight:700;color:{color}">{val}%</div>'
        f'</div>'
    )


def _market_chip(market_prob, market_src):
    """Collapsed market chip — displays platform name and probability."""
    if market_prob is None:
        return ""
    return (
        f'<div style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;'
        f'background:#f0f4ff;border-radius:12px;margin-left:4px">'
        f'<span style="font-size:0.72em;color:#6366f1;font-weight:600">{market_src}</span>'
        f'<span style="font-size:0.85em;font-weight:700;color:#6366f1">{market_prob}%</span>'
        f'</div>'
    )


# Mapping from DB source identifiers (lowercase) to display names
_SOURCE_DISPLAY = {
    "polymarket": "Polymarket",
    "manifold": "Manifold",
    "kalshi": "Kalshi",
    "metaculus": "Metaculus",
}


def prob01_to_pct(prob_0_1):
    """Convert 0.0-1.0 probability (from DB) to 0.0-100.0 percentage (for UI display).

    Always use this when converting DB yes_prob/no_prob values.
    Never multiply manually (linked_prob * 100) — prevents scale mixing bugs.
    """
    return round(float(prob_0_1) * 100.0, 1)


def compute_stance_from_row(r):
    """
    Compute YES/NO/NEUTRAL stance from row data.
    Used by UI to display 'Nowpatternの立場: YES' in tracking cards.

    Design intent (SYSTEM_DESIGN.md §2-2):
      We never hedge — we state YES or NO based on our highest-probability scenario.
    """
    # Use pre-computed stance from DB if available
    if r.get("our_stance"):
        return r["our_stance"]

    # Otherwise compute on the fly from scenario probabilities
    opt = r.get("optimistic") or 0
    base = r.get("base") or 0
    pess = r.get("pessimistic") or 0
    direction = r.get("resolution_direction", "optimistic")

    # If base is highest, NEUTRAL
    if base >= opt and base >= pess:
        return "NEUTRAL"

    if direction == "optimistic":
        return "YES" if opt >= pess else "NO"
    else:
        return "YES" if pess >= opt else "NO"


def _get_market_prob(r):
    """Return (market_prob_int, market_src_str) from row data.

    Priority:
      1. linked_market_prob (from market_history.db via nowpattern_links)
         → uses r["linked_market_source"] to determine the actual platform
      2. polymarket embed → "Polymarket"
      3. metaculus embed  → "Metaculus"
      4. no data          → (None, "")
    """
    linked_prob = r.get("linked_market_prob")
    pm = r.get("polymarket") or {}
    mc = r.get("metaculus") or {}

    if linked_prob is not None:
        raw_src = (r.get("linked_market_source") or "").lower().strip()
        src = _SOURCE_DISPLAY.get(raw_src, raw_src.capitalize() if raw_src else "Manifold")
        return round(prob01_to_pct(linked_prob)), src

    if pm.get("probability") is not None:
        return int(pm["probability"]), "Polymarket"

    if mc.get("probability") is not None:
        return int(mc["probability"]), "Metaculus"

    return None, ""


def _ev_str(r):
    """Extract event summary as plain string."""
    event_summary = r.get("event_summary", "")
    if isinstance(event_summary, dict):
        name = event_summary.get("name", event_summary.get("content", ""))
        date = event_summary.get("date", "")
        return (name + (f"（{date}）" if date else ""))[:100]
    if event_summary:
        return str(event_summary)[:100]
    return r.get("title", "")[:60]



def _validate_market_consensus(pred):
    """ENFORCEMENT: Warn if market_consensus question doesn't match prediction topic.

    Root cause prevention: 2026-02-25 — Polymarket questions were blindly attached
    to predictions about completely different topics (e.g., Dough Finance lawsuit
    prediction had Clarity Act market attached, showing misleading YES/NO data).

    This function checks for obvious mismatches and prints a WARNING during build.
    The WARNING does not block build, but alerts the operator to review.
    """
    mc = pred.get("market_consensus")
    if not mc or not isinstance(mc, dict) or not mc.get("question"):
        return True  # No market_consensus, nothing to validate

    pid = pred.get("prediction_id", "?")
    mc_question = mc.get("question", "").lower()

    # Get prediction topic from multiple sources
    topic_sources = []
    olt = pred.get("open_loop_trigger", "")
    if isinstance(olt, dict):
        olt = olt.get("name", olt.get("content", ""))
    if olt:
        topic_sources.append(str(olt).lower())

    title = pred.get("title", "")
    if title:
        topic_sources.append(str(title).lower())

    triggers = pred.get("triggers", [])
    for t in triggers[:2]:
        if isinstance(t, dict):
            topic_sources.append(t.get("name", "").lower())
        elif t:
            topic_sources.append(str(t).lower())

    if not topic_sources:
        return True  # No topic info to compare against

    # Extract key terms from prediction topic
    combined_topic = " ".join(topic_sources)

    # Extract key terms from market question
    # Check if there's ANY meaningful overlap
    # Split into words, ignore common words
    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "will", "be", "to",
        "in", "of", "for", "by", "on", "at", "from", "with", "before",
        "after", "into", "through", "during", "until",
        "の", "が", "は", "を", "に", "で", "と", "か", "も", "する",
        "した", "して", "される", "された", "まで", "から", "より",
        "年", "月", "日", "中", "前", "後", "以降", "以内",
        "2025", "2026", "2027",
    }

    def extract_keywords(text):
        import re
        words = set(re.findall(r'[a-zA-Z]{3,}|[぀-鿿]{2,}', text.lower()))
        return words - STOP_WORDS

    topic_kw = extract_keywords(combined_topic)
    mc_kw = extract_keywords(mc_question)

    overlap = topic_kw & mc_kw
    if not overlap and topic_kw and mc_kw:
        print(f"  ⚠️  WARNING: {pid} market_consensus MISMATCH")
        print(f"       Topic keywords: {sorted(topic_kw)[:5]}")
        print(f"       MC keywords: {sorted(mc_kw)[:5]}")
        print(f"       Overlap: NONE — this market may be about a different topic!")
        return False

    return True


def _build_tracking_card(r, lang):
    """BLOCK 2: <details>/<summary> accordion card for open predictions."""
    pess = r.get("pessimistic")
    base = r.get("base")
    opt = r.get("optimistic")
    pess_content = r.get("pess_content", "")
    base_content = r.get("base_content", "")
    opt_content = r.get("opt_content", "")
    title = r.get("title", "")
    url = r.get("url", "#")
    trigger_date = r.get("trigger_date", "")
    genres = r.get("genres", [])
    published_at = r.get("published_at", "")

    market_prob, market_src = _get_market_prob(r)

    # market_consensusが設定済みの場合、古いembed market_probを抑制（整合性維持）
    _has_mc_early = (
        r.get("market_consensus")
        and isinstance(r.get("market_consensus"), dict)
        and r["market_consensus"].get("pick")
    )
    if _has_mc_early:
        market_prob = None
        market_src = ""

    if lang == "ja":
        pess_lbl, base_lbl, opt_lbl = "悲観", "基本", "楽観"
        tracking_prefix = "追跡中の問い:"
        read_label = "→ 記事を読む"
        ours_section_label = "私たちの予想"
        market_section_label = f"市場の予想（{market_src}）" if market_src else "市場の予想"
        prob_desc_suffix = "「確率」"
        crowd_desc = (
            "（予測コミュニティの集合知）"
            if market_src == "Metaculus"
            else "（お金を賭けた人たちの集合知）"
        )
        resolve_label = "解決予定:"
        base_detail_label = "基本シナリオ:"
        resolution_criteria_label = "🎯 判定基準"
        scenario_accordion_label = "▼ 各シナリオの背景を読む"
    else:
        pess_lbl, base_lbl, opt_lbl = "Bear", "Base", "Bull"
        tracking_prefix = "Tracking:"
        read_label = "→ Read article"
        ours_section_label = "Our Prediction"
        market_section_label = f"Market Probability ({market_src})" if market_src else "Market Probability"
        prob_desc_suffix = "probability"
        crowd_desc = (
            "(aggregated forecasts from the forecasting community)"
            if market_src == "Metaculus"
            else "(collective intelligence of real-money bettors)"
        )
        resolve_label = "Resolution:"
        base_detail_label = "Base scenario:"
        resolution_criteria_label = "🎯 Resolution Criteria"
        scenario_accordion_label = "▼ Read scenario background"

    # Published at label
    pub_date = published_at[:10] if published_at else ""
    if pub_date:
        if lang == "ja":
            pub_label = f"{pub_date} 記事公開時"
        else:
            pub_label = f"at publication ({pub_date})"
    else:
        pub_label = ours_section_label

    # genre data-attr for JS filter
    genre_str = ",".join(genres) if genres else "all"

    # Scenario chips (collapsed view)
    pess_chip = _scenario_chip(pess_lbl, pess, pess_content, "#fde8e8", "", "#dc2626")
    base_chip = _scenario_chip(base_lbl, base, base_content, "#fff8e1", "border:2px solid #b8860b;", "#b8860b")
    opt_chip = _scenario_chip(opt_lbl, opt, opt_content, "#e8f5e9", "", "#16a34a")
    mkt_chip = _market_chip(market_prob, market_src)

    # Deadline badge
    deadline_html = _deadline_badge(trigger_date, lang, resolved=False)

    # Compute Nowpattern's YES/NO stance (SYSTEM_DESIGN.md §2-2)
    stance = compute_stance_from_row(r)
    if lang == "ja":
        _stance_colors = {"YES": "#16a34a", "NO": "#dc2626", "NEUTRAL": "#6366f1"}
        _stance_labels = {"YES": "YES", "NO": "NO", "NEUTRAL": "保留中"}
        _stance_prefix = "立場:"
    else:
        _stance_colors = {"YES": "#16a34a", "NO": "#dc2626", "NEUTRAL": "#6366f1"}
        _stance_labels = {"YES": "YES", "NO": "NO", "NEUTRAL": "Neutral"}
        _stance_prefix = "Stance:"
    if stance:
        _sc = _stance_colors.get(stance, "#888")
        _sl = _stance_labels.get(stance, stance)
        stance_chip = (
            '<div style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;'
            'background:#111;border-radius:10px;color:#fff;font-size:0.7em;font-weight:700">'
            f'<span style="color:#aaa;font-weight:400">{_stance_prefix}</span>'
            f'<span style="color:{_sc}">&nbsp;{_sl}</span></div>'
        )
    else:
        stance_chip = ""

    # Resolution question visible in collapsed view — HERO element (SYSTEM_DESIGN.md §5)
    if lang == "ja":
        _rq_summary = (r.get("resolution_question_ja") or r.get("resolution_question") or "")
    else:
        _rq_summary = r.get("resolution_question", "")
    if _rq_summary:
        rq_summary_html = (
            '<div style="font-size:0.8em;color:#444;margin:5px 0 7px;line-height:1.4;'
            'padding:5px 10px;background:#fffbf0;border-left:3px solid #b8860b;border-radius:0 4px 4px 0">'
            '<span style="font-weight:700;color:#b8860b;margin-right:4px">🎯</span>'
            f'{_rq_summary}'
            '</div>'
        )
    else:
        rq_summary_html = ""

    # ── 市場 vs Nowpattern 対比ブロック ────────────────────────────────────
    _op = r.get("our_pick")  # "YES" | "NO" | None
    if not _op:
        _op_computed = compute_stance_from_row(r)
        _op = _op_computed if _op_computed != "NEUTRAL" else None
    _op_prob = r.get("our_pick_prob")
    _op_hit_cond = (
        r.get("hit_condition_ja") if lang == "ja"
        else r.get("hit_condition_en", r.get("hit_condition_ja", ""))
    )

    _OP_CLR  = {"YES": "#2563EB", "NO": "#DC2626"}
    _OP_BG   = {"YES": "#EFF6FF", "NO": "#FEF2F2"}
    _OP_BORD = {"YES": "#BFDBFE", "NO": "#FECACA"}
    _op_clr  = _OP_CLR.get(_op, "#6B7280")
    _op_bg   = _OP_BG.get(_op, "#F9FAFB")
    _op_bord = _OP_BORD.get(_op, "#E5E7EB")

    # 市場コンセンサスセクション
    _mc = r.get("market_consensus")
    # Fallback: Polymarket/Metaculusのembedデータを使用（market_consensusがnullの場合）
    if not (_mc and isinstance(_mc, dict) and _mc.get("pick")):
        _pm = r.get("polymarket") or {}
        _pm_outcomes = _pm.get("outcomes")
        _mc_data = r.get("metaculus") or {}
        _mc_prob = _mc_data.get("probability")
        if _pm_outcomes:
            _yes_pct = float(_pm_outcomes.get("Yes", _pm_outcomes.get("YES", 0)))
            _mc = {"source": "Polymarket", "pick": "YES" if _yes_pct >= 50 else "NO", "probability": round(_yes_pct, 1), "question": _pm.get("question", "")}
        elif _mc_prob is not None:
            _mc = {"source": "Metaculus", "pick": "YES" if float(_mc_prob) >= 50 else "NO", "probability": round(float(_mc_prob)), "question": _mc_data.get("question", "")}
    if _mc and isinstance(_mc, dict) and _mc.get("pick"):
        mc_source = _mc.get("source", "市場")
        mc_pick   = _mc.get("pick")
        mc_prob   = _mc.get("probability", 50)
        mc_clr    = "#2563EB" if mc_pick == "YES" else "#DC2626"
        mc_question = _mc.get("question_ja", "") if lang == "ja" else _mc.get("question", "")
        mc_question_html = ""
        if mc_question:
            mc_question_html = (
                f'<div style="font-size:0.72em;color:#475569;font-style:italic;'
                f'margin-bottom:5px;line-height:1.3">'
                f'&#10067; {mc_question}'
                f'</div>'
            )
        market_section_html = (
            f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
            f'border-radius:4px;padding:6px 10px;margin-bottom:6px">'
            f'{mc_question_html}'
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'font-size:0.74em;margin-bottom:4px">'
            f'<span style="color:#64748B">&#127963; {mc_source} コンセンサス</span>'
            f'<span style="font-weight:700;color:{mc_clr}">{mc_pick}&nbsp;{mc_prob}%</span>'
            f'</div>'
            f'<div style="background:#E2E8F0;border-radius:2px;height:3px">'
            f'<div style="background:{mc_clr};width:{mc_prob}%;height:3px;border-radius:2px"></div>'
            f'</div>'
            f'</div>'
        )
        is_contrarian = bool(_op and mc_pick != _op)
    else:
        market_section_html = ""
        is_contrarian = False

    contrarian_badge = (
        f'<span style="font-size:0.62em;background:#FEF3C7;color:#92400E;'
        f'border-radius:9999px;padding:1px 7px;margin-left:6px;vertical-align:middle">'
        f'&#9889; 逆張り</span>'
    ) if is_contrarian else ""

    # 判定基準 (Verdict形式) — pick_header 内に統合
    hit_cond_html = ""
    if _op_hit_cond:
        _hit_clr     = {"YES": "#1D4ED8", "NO": "#B91C1C"}.get(_op, "#6B7280")
        _verdict_lbl = "判定基準" if lang == "ja" else "Verdict"
        _verdict_win = "的中" if lang == "ja" else "Nowpattern wins"
        _cond_clean  = (
            _op_hit_cond
            .replace(" — Nowpatternの的中", "")
            .replace(" — Nowpattern wins", "")
            .strip()
        )
        verdict_inner = (
            f'<div style="font-size:0.75em;color:#555;padding:5px 0 2px 0;'
            f'border-top:1px dashed {_op_bord};margin-top:5px">'
            f'<span style="color:{_hit_clr};font-weight:700">&#10145; {_verdict_lbl}:</span>'
            f' {_cond_clean}'
            f' &#10132; <strong style="color:{_hit_clr}">{_verdict_win}</strong>'
            f'</div>'
        )
    else:
        verdict_inner = ""

    if _op:
        _op_label = "Nowpatternの結論" if lang == "ja" else "Nowpattern's Conclusion"
        _op_prob_html = (
            f'<span style="font-size:0.85em;font-weight:700;color:{_op_clr};opacity:0.85">'
            f'&nbsp;{_op_prob}%の確信</span>'
        ) if _op_prob else ""
        pick_header_html = (
            f'<div style="border-left:4px solid {_op_clr};background:{_op_bg};'
            f'border:1px solid {_op_bord};border-left-width:4px;'
            f'border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:7px">'
            f'{market_section_html}'
            f'<div style="font-size:0.68em;color:#888;margin-bottom:3px">{_op_label}</div>'
            f'<div style="display:flex;align-items:center;gap:6px">'
            f'<span style="font-size:1.55em;font-weight:900;color:{_op_clr};'
            f'line-height:1;letter-spacing:-0.02em">&#9679; {_op}</span>'
            f'{_op_prob_html}'
            f'{contrarian_badge}'
            f'</div>'
            f'{verdict_inner}'
            f'</div>'
        )
    elif market_section_html:
        # our_pickがなくても市場コンセンサスデータがあれば表示
        pick_header_html = (
            f'<div style="border-left:4px solid #94A3B8;background:#F8FAFC;'
            f'border:1px solid #E2E8F0;border-left-width:4px;'
            f'border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:7px">'
            f'{market_section_html}'
            f'</div>'
        )
    else:
        pick_header_html = ""

    # Expanded scenario boxes
    # Expanded scenario boxes
    exp_pess = _scenario_box_exp(pess_lbl, pess, pess_content, "#fde8e8", "", "#dc2626")
    exp_base = _scenario_box_exp(base_lbl, base, base_content, "#fff8e1", "border:2px solid #b8860b;", "#b8860b")
    exp_opt = _scenario_box_exp(opt_lbl, opt, opt_content, "#e8f5e9", "", "#16a34a")

    # Expanded market section
    # market_consensusが設定済みの場合、古いembedパネルを抑制（整合性維持）
    _has_mc = r.get("market_consensus") and isinstance(r.get("market_consensus"), dict) and r["market_consensus"].get("pick")
    pm = r.get("polymarket") or {} if not _has_mc else {}
    mc = r.get("metaculus") or {} if not _has_mc else {}
    mq = (pm.get("question") or mc.get("question") or r.get("linked_market_question") or "")[:80]
    market_url = r.get("linked_market_url")

    # PR2: YES/NO split bar — use outcomes from embed, fall back to computed values
    _bar_outcomes = pm.get("outcomes") or mc.get("outcomes")
    if _bar_outcomes is None and r.get("linked_market_prob") is not None:
        _y = round(prob01_to_pct(r["linked_market_prob"]), 1)
        _bar_outcomes = {"Yes": _y, "No": round(100.0 - _y, 1)}
    if _bar_outcomes is None and market_prob is not None:
        _bar_outcomes = {"Yes": float(market_prob), "No": round(100.0 - float(market_prob), 1)}
    if _bar_outcomes:
        _yes = float(_bar_outcomes.get("Yes", 0.0))
        _no = float(_bar_outcomes.get("No", round(100.0 - _yes, 1)))
        _is_close = (40.0 <= _yes <= 60.0)
        _close_lbl = "拮抗中" if lang == "ja" else "Neck&amp;Neck"
        _close_badge = (
            f'<span style="font-size:0.72em;background:#fef3c7;color:#b45309;'
            f'border-radius:4px;padding:1px 6px;font-weight:700;white-space:nowrap">'
            f'{_close_lbl}</span>'
        ) if _is_close else ""
        yes_no_bar = (
            f'<div style="margin:4px 0 2px;border-radius:3px;overflow:hidden;'
            f'display:flex;height:8px;background:#f0f0f0">'
            f'<div style="width:{_yes:.1f}%;background:#6366f1;flex-shrink:0"></div>'
            f'<div style="width:{_no:.1f}%;background:#e5e7eb;flex-shrink:0"></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'font-size:0.75em;color:#555;margin-bottom:6px">'
            f'<span>YES&nbsp;{_yes:.1f}%</span>'
            f'{_close_badge}'
            f'<span>NO&nbsp;{_no:.1f}%</span>'
            f'</div>'
        )
    else:
        yes_no_bar = ""

    if market_prob is not None:
        if lang == "ja":
            mq_desc = f'「{mq}」確率' if mq else "確率"
            view_market_label = "→ 市場を見る"
        else:
            mq_desc = f'"{mq}" probability' if mq else "probability"
            view_market_label = "→ View market"
        market_link_btn = (
            f'<div style="margin-top:12px">'
            f'<a href="{market_url}" target="_blank" rel="noopener" '
            f'style="display:inline-block;padding:6px 14px;border-radius:6px;'
            f'font-size:0.84em;font-weight:600;text-decoration:none;'
            f'background:#f0f4ff;color:#6366f1;border:1px solid #c7d2fe">'
            f'{view_market_label} ↗</a>'
            f'</div>'
        ) if market_url else ""
        market_expanded = (
            '<div style="background:#fff;border-radius:8px;padding:14px;border:1px solid #e0e0e0">'
            f'<div style="font-size:0.72em;font-weight:700;letter-spacing:.05em;'
            f'text-transform:uppercase;color:#999;margin-bottom:8px">{market_section_label}</div>'
            f'<div style="font-size:2em;font-weight:700;color:#6366f1;margin-bottom:2px">'
            f'{market_prob}%</div>'
            f'{yes_no_bar}'
            f'<div style="font-size:0.82em;color:#666;margin-bottom:4px">'
            f'{mq_desc}<br>{crowd_desc}</div>'
            + market_link_btn
            + '</div>'
        )
    else:
        no_data = "市場データなし" if lang == "ja" else "No market data"
        market_expanded = (
            '<div style="background:#f5f5f0;border-radius:8px;padding:14px;'
            'display:flex;align-items:center;justify-content:center;'
            f'color:#aaa;font-size:0.85em">{no_data}</div>'
        )

    # Resolve date in expanded
    if trigger_date:
        try:
            parts = trigger_date.split("-")
            y, m2 = parts[0], int(parts[1])
            if lang == "ja":
                resolve_date_str = f"{y}年{m2}月"
            else:
                import calendar
                resolve_date_str = f"{calendar.month_abbr[m2]} {y}"
        except Exception:
            resolve_date_str = trigger_date
    else:
        resolve_date_str = "—"

    # Use Japanese translation if available and lang==ja, else English
    if lang == "ja":
        resolution_question = (r.get("resolution_question_ja") or r.get("resolution_question") or "")
    else:
        resolution_question = r.get("resolution_question", "")
    scenario_rows = []
    for _lbl, _cnt, _clr in [
        (pess_lbl, pess_content, "#dc2626"),
        (base_lbl, base_content, "#b8860b"),
        (opt_lbl, opt_content, "#16a34a"),
    ]:
        if _cnt:
            scenario_rows.append(
                f'<div style="font-size:0.78em;color:#555;margin-bottom:6px;line-height:1.6">'
                f'<strong style="color:{_clr}">{_lbl}:</strong> {_cnt}</div>'
            )
    if scenario_rows:
        base_detail = (
            f'<details style="margin-top:8px">'
            f'<summary style="cursor:pointer;font-size:0.78em;color:#888;'
            f'user-select:none;list-style:none;padding:4px 0;outline:none">'
            f'{scenario_accordion_label}</summary>'
            f'<div style="padding:8px 0 0">'
            + "".join(scenario_rows)
            + '</div>'
            '</details>'
        )
    else:
        base_detail = ""
    rq_html = (
        f'<div style="background:#fffbf0;border-radius:6px;padding:8px 12px;'
        f'margin-bottom:10px;border-left:3px solid #b8860b;font-size:0.82em;'
        f'color:#555;line-height:1.5">'
        f'<span style="font-weight:700;color:#b8860b">{resolution_criteria_label}:</span> '
        f'{resolution_question}'
        f'</div>'
    ) if resolution_question else ""
    _mkt_nav_lbl = "→ 市場を見る ↗" if lang == "ja" else "→ View market ↗"

    ev = _ev_str(r)

    # Use resolution_question as tracking question (matches hit_condition)
    # Fall back to ev (event_summary) only if no resolution_question
    if lang == "ja":
        _tracking_q = (r.get("resolution_question_ja") or r.get("resolution_question") or ev)
    else:
        _tracking_q = (r.get("resolution_question") or ev)

    # Show event_summary as separate trigger line if different
    _ev_line = ""
    if ev and ev != _tracking_q and len(ev) > 5:
        _ev_pfx = "\u6ce8\u76ee\u30a4\u30d9\u30f3\u30c8:" if lang == "ja" else "Key Event:"
        _ev_line = (
            f'<div style="font-size:0.68em;color:#aaa;margin-bottom:4px">'
            f'{_ev_pfx}&nbsp;<span style="color:#888">{ev}</span>'
            f'</div>'
        )

    # Status badge
    _is_resolved = r.get("status") == "resolved"
    if _is_resolved:
        _hm = r.get("hit_miss", "")
        if _hm in ("correct", "hit"):
            _status_badge = (
                '<span style="display:inline-block;background:#dcfce7;color:#16a34a;'
                'font-size:0.72em;font-weight:700;padding:2px 10px;border-radius:12px;'
                'margin-bottom:6px">\u2705 ' + ("\u7684\u4e2d" if lang == "ja" else "Accurate") + '</span>'
            )
        elif _hm in ("incorrect", "miss"):
            _status_badge = (
                '<span style="display:inline-block;background:#fee2e2;color:#dc2626;'
                'font-size:0.72em;font-weight:700;padding:2px 10px;border-radius:12px;'
                'margin-bottom:6px">\u274c ' + ("\u5916\u308c" if lang == "ja" else "Missed") + '</span>'
            )
        else:
            _status_badge = (
                '<span style="display:inline-block;background:#fef3c7;color:#b45309;'
                'font-size:0.72em;font-weight:700;padding:2px 10px;border-radius:12px;'
                'margin-bottom:6px">\u26a0\ufe0f ' + ("\u4e8b\u5b9f\u78ba\u8a8d\u4e2d" if lang == "ja" else "Verifying") + '</span>'
            )
    else:
        _status_badge = (
            '<span style="display:inline-block;background:#e0f2fe;color:#0284c7;'
            'font-size:0.72em;font-weight:700;padding:2px 10px;border-radius:12px;'
            'margin-bottom:6px">\u23f3 ' + ("\u8ffd\u8de1\u4e2d" if lang == "ja" else "Tracking") + '</span>'
        )

    return (
        f'<details style="border-bottom:1px solid #eeebe4;padding:2px 0" data-genres="{genre_str}">'
        '<summary>'
        '<div style="display:flex;align-items:flex-start;gap:8px;padding:10px 4px;user-select:none">'
        '<div style="flex:1">'
        f'{_status_badge}'
        f'<div style="font-size:0.7em;color:#999;margin-bottom:6px">'
        f'{tracking_prefix}&nbsp;<span style="color:#333;font-weight:500">{_tracking_q}</span>'
        '</div>'
        f'{_ev_line}'
        f'{pick_header_html}'
        f'{hit_cond_html}'
        '<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px;flex-wrap:wrap">'
        f'<span style="color:#b8860b;font-weight:600;font-size:0.88em;line-height:1.4">{title}</span>'
        f'{deadline_html}'
        '</div>'
        '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">'
        f'{pess_chip}{base_chip}{opt_chip}{mkt_chip}'
        '</div>'
        '</div>'
        '<span class="chevron" style="color:#bbb;font-size:0.9em;margin-top:18px">▼</span>'
        '</div>'
        '</summary>'
        '<div style="padding:16px;background:#f9f9f6;border-radius:0 0 10px 10px;'
        'margin:0 4px 10px;border:1px solid #e8e4dc">'
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px">'
        '<div style="background:#fff;border-radius:8px;padding:14px;border:1px solid #e0e0e0">'
        f'<div style="font-size:0.72em;font-weight:700;letter-spacing:.05em;'
        f'text-transform:uppercase;color:#999;margin-bottom:8px">{pub_label}</div>'
        f'{rq_html}'
        '<div style="display:flex;gap:6px;margin-bottom:10px">'
        f'{exp_pess}{exp_base}{exp_opt}'
        '</div>'
        f'{base_detail}'
        '</div>'
        f'{market_expanded}'
        '</div>'
        '<div style="background:#fff8e1;border-radius:8px;padding:10px 14px;margin-bottom:10px">'
        '<div style="font-size:0.85em">'
        f'<span style="color:#888">{resolve_label}</span> '
        f'<strong style="color:#b8860b">{resolve_date_str}</strong>'
        '</div>'
        '</div>'
        '<div style="display:flex;gap:8px;flex-wrap:wrap">'
        f'<a href="{url}" style="display:inline-block;padding:6px 14px;border-radius:6px;'
        f'font-size:0.84em;font-weight:600;text-decoration:none;'
        f'background:#fff8e1;color:#b8860b;border:1px solid #e6c86a">{read_label}</a>'
        '</div>'
        '</div>'
        '</details>'
    )


def _build_resolved_card(r, lang):
    """BLOCK 3: <details>/<summary> accordion card for resolved predictions."""
    pess = r.get("pessimistic")
    base = r.get("base")
    opt = r.get("optimistic")
    pess_content = r.get("pess_content", "")
    base_content = r.get("base_content", "")
    opt_content = r.get("opt_content", "")
    title = r.get("title", "")
    url = r.get("url", "#")
    outcome = r.get("outcome", "")
    brier = r.get("brier")
    resolved_at = r.get("resolved_at", "")

    market_prob, market_src = _get_market_prob(r)

    if lang == "ja":
        pess_lbl, base_lbl, opt_lbl = "悲観", "基本", "楽観"
        resolved_prefix = "解決済みの問い:"
        read_label = "→ 記事を読む"
        ours_section = "私たちの予想（記事公開時）"
        market_section = f"市場の予想（{market_src}、解決直前）"
        actual_section = "実際の結果"
        accuracy_label = "Nowpattern精度スコア:"
        market_acc_label = "市場精度スコア:"
        brier_note = "※ スコアは低いほど良い（ブライアスコア）"

        outcome_map = {"楽観": "楽観", "基本": "基本", "悲観": "悲観"}
        hit_word = "的中"
        miss_word = "外れ"
        outcome_suffix_hit = "的中"
        outcome_suffix_miss = "が現実に"
    else:
        pess_lbl, base_lbl, opt_lbl = "Bear", "Base", "Bull"
        resolved_prefix = "Resolved:"
        read_label = "→ Read article"
        ours_section = "Our Prediction (at publication)"
        market_section = f"Market ({market_src}, pre-resolution)"
        actual_section = "Actual Result"
        accuracy_label = "Nowpattern Brier:"
        market_acc_label = "Market Brier:"
        brier_note = "※ Lower = better (Brier score)"

        outcome_map = {"楽観": "Optimistic", "基本": "Base", "悲観": "Pessimistic"}
        hit_word = "Accurate"
        miss_word = "Missed"
        outcome_suffix_hit = " Accurate"
        outcome_suffix_miss = " (Missed)"

    # hit_miss is authoritative; fall back to brier < 0.25 for legacy rows
    _hit_miss_val = r.get("hit_miss")
    if _hit_miss_val is not None:
        is_hit = _hit_miss_val in ("correct", "hit")
    else:
        is_hit = brier is not None and brier < 0.25

    # Phase 2: Disputed status overrides normal resolution display
    is_disputed = r.get("status") == "disputed"
    if is_disputed:
        disputed_lbl = "事実確認中" if lang == "ja" else "Under Review"
        result_badge = (
            '<div style="display:inline-block;border:3px solid #d97706;border-radius:6px;'
            'padding:3px 10px;color:#d97706;font-size:0.82em;font-weight:800;'
            'letter-spacing:.04em;transform:rotate(-2deg);white-space:nowrap;'
            'background:rgba(217,119,6,0.05)">'
            f'⚠️ {disputed_lbl}</div>'
        )
        result_color = "#d97706"
        result_bg = "#fffbeb"
        result_border = "border:2px solid #fcd34d"
        result_text = f"⚠️ {disputed_lbl}"
        collapsed_chip = (
            '<div style="display:inline-flex;gap:6px;align-items:center;padding:3px 10px;'
            'background:#fffbeb;border-radius:6px">'
            f'<span style="font-size:0.75em;color:#d97706;font-weight:700">{disputed_lbl}</span>'
            '</div>'
        )

    # Stamp-style result badge (rotated border box — more visual than pill)
    if is_hit and not is_disputed:
        result_badge = (
            f'<div style="display:inline-block;border:3px solid #16a34a;border-radius:6px;'
            f'padding:3px 10px;color:#16a34a;font-size:0.82em;font-weight:800;'
            f'letter-spacing:.04em;transform:rotate(-2deg);white-space:nowrap;'
            f'background:rgba(22,163,74,0.05)">'
            f'✅ {hit_word}</div>'
        )
        result_color = "#16a34a"
        result_bg = "#e8f5e9"
        result_border = "border:2px solid #16a34a"
    else:
        result_badge = (
            f'<div style="display:inline-block;border:3px solid #dc2626;border-radius:6px;'
            f'padding:3px 10px;color:#dc2626;font-size:0.82em;font-weight:800;'
            f'letter-spacing:.04em;transform:rotate(-2deg);white-space:nowrap;'
            f'background:rgba(220,38,38,0.05)">'
            f'❌ {miss_word}</div>'
        )
        result_color = "#dc2626"
        result_bg = "#fff0f0"
        result_border = "border:1px solid #fca5a5"

    outcome_en = outcome_map.get(outcome, outcome)
    result_text = "✅ " + outcome_en + outcome_suffix_hit if is_hit else "❌ " + outcome_en + outcome_suffix_miss

    # Collapsed outcome chips
    if is_hit:
        collapsed_chip = (
            f'<div style="display:inline-flex;gap:6px;align-items:center;padding:3px 10px;'
            f'background:#e8f5e9;border-radius:6px">'
            f'<span style="font-size:0.75em;color:#16a34a;font-weight:700">'
            f'{outcome_en}{outcome_suffix_hit}</span>'
            f'<span style="font-size:0.85em;font-weight:700;color:#16a34a">→✅</span>'
            f'</div>'
        )
    else:
        collapsed_chip = (
            f'<div style="display:inline-flex;gap:6px;align-items:center;padding:3px 10px;'
            f'background:#fde8e8;border-radius:6px">'
            f'<span style="font-size:0.75em;color:#dc2626;font-weight:700">'
            f'{outcome_en}{outcome_suffix_miss}</span>'
            f'<span style="font-size:0.85em;font-weight:700;color:#dc2626">→❌</span>'
            f'</div>'
        )

    # Market final chip
    if market_prob is not None:
        mf_text_color = "#16a34a" if is_hit else "#dc2626"
        if lang == "ja":
            mf_label = f"{market_src}最終値"
        else:
            mf_label = f"{market_src} final"
        mf_chip = (
            f'<div style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;'
            f'background:#f0f4ff;border-radius:12px">'
            f'<span style="font-size:0.72em;color:#6366f1;font-weight:600">{mf_label}</span>'
            f'<span style="font-size:0.85em;font-weight:700;color:{mf_text_color}">'
            f'{market_prob}%</span>'
            f'</div>'
        )
    else:
        mf_chip = ""

    auto_chip = ""

    # Date badge
    resolved_date = resolved_at[:10] if resolved_at else ""
    date_badge = _deadline_badge(resolved_date, lang, resolved=True) if resolved_date else ""

    ev = _ev_str(r)

    # Use resolution_question as the resolved question (matches hit_condition)
    if lang == "ja":
        _resolved_q = (r.get("resolution_question_ja") or r.get("resolution_question") or ev)
    else:
        _resolved_q = (r.get("resolution_question") or ev)

    # Show event_summary as separate line if different
    _ev_resolved_line = ""
    if ev and ev != _resolved_q and len(ev) > 5:
        _ev_rpfx = "注目イベント:" if lang == "ja" else "Key Event:"
        _ev_resolved_line = (
            f'<div style="font-size:0.68em;color:#aaa;margin-bottom:4px">'
            f'{_ev_rpfx}&nbsp;<span style="color:#888">{ev}</span>'
            f'</div>'
        )

    # Expanded 3-col scenario boxes (compact)
    def small_box(label, val, bg, border, color):
        if val is None:
            return ""
        return (
            f'<div style="flex:1;background:{bg};border-radius:6px;padding:6px;'
            f'text-align:center;{border}">'
            f'<div style="font-size:0.68em;color:{color};font-weight:600">{label}</div>'
            f'<div style="font-size:1.1em;font-weight:700;color:{color}">{val}%</div>'
            f'</div>'
        )

    exp_pess = small_box(pess_lbl, pess, "#fde8e8", "", "#dc2626")
    exp_base = small_box(base_lbl, base, "#fff8e1", "border:2px solid #b8860b;", "#b8860b")
    exp_opt = small_box(opt_lbl, opt, "#e8f5e9", "", "#16a34a")

    # Market column
    market_url_r = r.get("linked_market_url")
    # ── Phase 2: Evidence panel + integrity hash ──
    _evidence = r.get("resolution_evidence") or {}
    _key_text = _evidence.get("key_evidence_text", "")
    _confidence = _evidence.get("confidence", "")
    _ihash = r.get("integrity_hash", "")
    _rebuttals = r.get("rebuttals", [])
    _dispute_reason = r.get("dispute_reason", "")
    if lang == "ja":
        _ev_title = "📋 判定根拠"
        _ev_confidence_label = "確信度:"
        _hash_label = "改ざん検知コード:"
        _rebuttal_label = "反論"
        _rebuttal_unit = "件"
        _dispute_label = "異議理由:"
    else:
        _ev_title = "📋 Resolution Evidence"
        _ev_confidence_label = "Confidence:"
        _hash_label = "Integrity fingerprint:"
        _rebuttal_label = "Rebuttal"
        _rebuttal_unit = "s"
        _dispute_label = "Dispute reason:"
    if _key_text or _ihash:
        _hash_display = (
            f'<div style="font-size:0.68em;color:#aaa;margin-top:6px;font-family:monospace">'
            f'{_hash_label} <span style="color:#b8860b">{_ihash[-12:] if _ihash else "—"}</span>'
            + (f' <span style="color:#aaa">({_confidence})</span>' if _confidence else '')
            + '</div>'
        )
        _dispute_html = (
            f'<div style="font-size:0.75em;color:#d97706;margin-top:4px">⚠️ {_dispute_label} {_dispute_reason}</div>'
            if _dispute_reason else ""
        )
        _rebuttal_html = (
            f'<div style="font-size:0.75em;color:#6366f1;margin-top:4px">'
            f'💬 {len(_rebuttals)}{_rebuttal_unit}の{_rebuttal_label}</div>'
        ) if _rebuttals else ""
        _evidence_html = (
            '<details style="margin-top:10px">'
            f'<summary style="cursor:pointer;font-size:0.78em;color:#888;'
            f'user-select:none;list-style:none;padding:4px 0;outline:none">'
            f'▼ {_ev_title}</summary>'
            '<div style="padding:8px 10px;background:#fffbf0;border-radius:4px;'
            'border-left:3px solid #b8860b;margin-top:6px">'
            + (f'<div style="font-size:0.8em;color:#555;line-height:1.5">{_key_text}</div>' if _key_text else '')
            + _hash_display + _dispute_html + _rebuttal_html
            + '</div>'
            '</details>'
        )
    else:
        _evidence_html = ""
    if market_prob is not None:
        mf_res = ("→ 解決: YES" if is_hit else "→ 解決: NO") if lang == "ja" else ("→ Resolved: YES" if is_hit else "→ Resolved: NO")
        if lang == "ja":
            view_market_lbl_r = "→ 市場ページを見る"
        else:
            view_market_lbl_r = "→ View market page"
        mkt_link_html_r = (
            f'<a href="{market_url_r}" target="_blank" rel="noopener"'
            f' style="font-size:0.75em;color:#6366f1;font-weight:600;text-decoration:none;'
            f'display:inline-block;margin-top:6px">{view_market_lbl_r} ↗</a>'
        ) if market_url_r else ""
        market_col = (
            '<div style="background:#f0f4ff;border-radius:8px;padding:12px;border:1px solid #c7d2fe">'
            f'<div style="font-size:0.72em;font-weight:700;letter-spacing:.05em;'
            f'text-transform:uppercase;color:#999;margin-bottom:8px">{market_section}</div>'
            f'<div style="font-size:1.6em;font-weight:700;color:#6366f1">{market_prob}%</div>'
            f'<div style="font-size:0.75em;color:#6366f1;margin-top:6px">{mf_res}</div>'
            '</div>'
        )
    else:
        no_mkt = "市場データなし" if lang == "ja" else "No market data"
        market_col = (
            '<div style="background:#f5f5f0;border-radius:8px;padding:12px;'
            f'display:flex;align-items:center;justify-content:center;color:#aaa;font-size:0.85em">{no_mkt}</div>'
        )

    # Actual result column
    actual_desc = base_content or opt_content or pess_content or ""
    _mkt_nav_lbl_r = "→ 市場ページを見る ↗" if lang == "ja" else "→ View market page ↗"
    actual_col = (
        f'<div style="background:{result_bg};border-radius:8px;padding:12px;{result_border}">'
        f'<div style="font-size:0.72em;font-weight:700;letter-spacing:.05em;'
        f'text-transform:uppercase;color:{result_color};margin-bottom:8px">{actual_section}</div>'
        f'<div style="font-size:1.1em;font-weight:700;color:{result_color};margin-bottom:6px">'
        f'{result_text}</div>'
        + (
            f'<div style="font-size:0.8em;color:#333;line-height:1.5;'
            f'overflow:hidden;display:-webkit-box;-webkit-line-clamp:4;'
            f'-webkit-box-orient:vertical">{actual_desc}</div>'
            if actual_desc else ""
        )
        + f'</div>'
    )

    # Brier score row
    brier_html = ""
    if brier is not None:
        brier_color = "#16a34a" if brier < 0.15 else ("#f59e0b" if brier < 0.25 else "#dc2626")
        mkt_brier_html = ""
        if market_prob is not None:
            p = market_prob / 100
            mkt_brier = round(p * (1 - p) * 2, 2)
            mkt_brier_html = (
                f'<div><span style="color:#888">{market_acc_label}</span> '
                f'<strong style="color:#6366f1">{mkt_brier:.2f}</strong></div>'
            )
        brier_html = (
            '<div style="background:#f5f5f0;border-radius:8px;padding:10px 14px;'
            'margin-top:12px;display:flex;gap:20px;font-size:0.85em;flex-wrap:wrap">'
            f'<div><span style="color:#888">{accuracy_label}</span> '
            f'<strong style="color:{brier_color}">{brier:.2f}</strong></div>'
            + mkt_brier_html
            + f'<div style="font-size:0.78em;color:#aaa">{brier_note}</div>'
            '</div>'
        )

    return (
        '<details style="border-bottom:1px solid #eeebe4;padding:2px 0">'
        '<summary>'
        '<div style="display:flex;align-items:center;gap:8px;padding:10px 4px;user-select:none">'
        '<div style="flex:1">'
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
        '<div style="background:#111;color:#f5f5f0;padding:4px 10px;border-radius:4px;'
        f'font-size:0.77em;flex:1">'
        f'<span style="opacity:0.5">{resolved_prefix}</span>'
        f'<span style="font-weight:600;margin-left:4px">{_resolved_q}</span>'
        '</div>'
        f'{_ev_resolved_line}'
        f'{result_badge}'
        '</div>'
        '<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px;flex-wrap:wrap">'
        f'<span style="color:#b8860b;font-weight:600;font-size:0.92em">{title}</span>'
        f'{date_badge}'
        '</div>'
        '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">'
        f'{collapsed_chip}{mf_chip}{auto_chip}'
        '</div>'
        '</div>'
        '<span class="chevron" style="color:#bbb;font-size:0.9em">▼</span>'
        '</div>'
        '</summary>'
        '<div style="padding:16px;background:#f9f9f6;border-radius:0 0 10px 10px;'
        'margin:0 4px 10px;border:1px solid #e8e4dc">'
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">'
        '<div style="background:#fff;border-radius:8px;padding:12px;border:1px solid #e0e0e0">'
        f'<div style="font-size:0.72em;font-weight:700;letter-spacing:.05em;'
        f'text-transform:uppercase;color:#999;margin-bottom:8px">{ours_section}</div>'
        '<div style="display:flex;gap:4px">'
        f'{exp_pess}{exp_base}{exp_opt}'
        '</div>'
        '</div>'
        f'{market_col}'
        f'{actual_col}'
        '</div>'
        f'{brier_html}'
        f'{_evidence_html}'
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">'
        f'<a href="{url}" style="display:inline-block;padding:6px 14px;border-radius:6px;'
        f'font-size:0.84em;font-weight:600;text-decoration:none;'
        f'background:#fff8e1;color:#b8860b;border:1px solid #e6c86a">{read_label}</a>'
        + (
            f'<a href="{market_url_r}" target="_blank" rel="noopener" '
            f'style="display:inline-block;padding:6px 14px;border-radius:6px;'
            f'font-size:0.84em;font-weight:600;text-decoration:none;'
            f'background:#f0f4ff;color:#6366f1;border:1px solid #c7d2fe">{_mkt_nav_lbl_r}</a>'
            if market_url_r else ""
        )
        + '</div>'
        '</div>'
        '</details>'
    )



def build_page_html(rows, stats, lang="ja"):
    """Build predictions page HTML — 5 blocks: scoreboard + formal tracking + resolved + analysis + automation."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M JST")

    # B2: Split formal predictions vs Ghost article analysis
    formal_rows = [r for r in rows if r.get("source") == "prediction_db"]
    analysis_rows = [r for r in rows if r.get("source") != "prediction_db"]

    tracking = [r for r in formal_rows if r.get("status") != "resolved"]
    resolved = [r for r in formal_rows if r.get("status") == "resolved"]

    # ── BLOCK 1: Scoreboard (formal predictions only) ──
    block1 = _scoreboard_block(rows, lang)

    # ── BLOCK 2: Tracking (formal predictions only) ──
    if lang == "ja":
        tracking_title = (
            f'追跡中の予測 <span style="font-size:0.8em;color:#888;font-weight:400">'
            f'{len(tracking)}件</span>'
        )
        search_placeholder = "🔍  キーワードで絞り込み..."
        auto_updated = f"最終更新: {now}"
    else:
        tracking_title = (
            f'Tracked Predictions <span style="font-size:0.8em;color:#888;font-weight:400">'
            f'{len(tracking)}</span>'
        )
        search_placeholder = "🔍  Filter by keyword..."
        auto_updated = f"Last updated: {now}"

    # Category filter buttons
    cat_buttons = ""
    for cat_key, cat_name in CATEGORY_LABELS[lang]:
        if cat_key == "all":
            cat_buttons += (
                f'<button class="np-cat-btn" data-cat="all" '
                f'style="padding:5px 12px;border-radius:16px;border:2px solid #b8860b;'
                f'background:#b8860b;color:#fff;font-size:0.8em;cursor:pointer;font-weight:600">'
                f'{cat_name}</button>'
            )
        else:
            cat_buttons += (
                f'<button class="np-cat-btn" data-cat="{cat_key}" '
                f'style="padding:5px 12px;border-radius:16px;border:1px solid #ddd;'
                f'background:#fff;color:#555;font-size:0.8em;cursor:pointer">'
                f'{cat_name}</button>'
            )

    tracking_cards = "\n".join(_build_tracking_card(r, lang) for r in tracking)

    block2 = (
        '<div style="margin-bottom:24px;background:#fff;border-radius:12px;'
        'padding:24px 28px;box-shadow:0 2px 8px rgba(0,0,0,.08)">'
        f'<h2 style="color:#333;font-size:1.1em;border-left:4px solid #b8860b;'
        f'padding-left:10px;margin:0 0 16px 0">{tracking_title}</h2>'
        '<div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;align-items:center">'
        f'<input type="text" id="np-search" placeholder="{search_placeholder}" '
        f'style="flex:1;min-width:200px;padding:7px 12px;border:1px solid #ddd;'
        f'border-radius:6px;font-size:0.9em;outline:none">'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap">{cat_buttons}</div>'
        '</div>'
        f'<div id="np-tracking-list">{tracking_cards}</div>'
        '<div id="np-pagination" style="display:flex;justify-content:center;'
        'align-items:center;gap:6px;margin-top:16px;font-size:0.85em"></div>'
        f'<div style="font-size:0.78em;color:#aaa;margin-top:8px;text-align:right">'
        f'{auto_updated}</div>'
        '</div>'
    )

    # ── BLOCK 3: Resolved ──
    if lang == "ja":
        resolved_title = (
            f'解決済みの予測 <span style="font-size:0.8em;color:#888;font-weight:400">'
            f'{len(resolved)}件</span>'
        )
        resolved_desc = "📌 クリックで詳細展開"
        no_resolved_text = "まだ結果が確定した予測はありません。"
    else:
        resolved_title = (
            f'Resolved Predictions <span style="font-size:0.8em;color:#888;font-weight:400">'
            f'{len(resolved)}</span>'
        )
        resolved_desc = "📌 Click to expand details"
        no_resolved_text = "No resolved predictions yet."

    if resolved:
        resolved_cards = "\n".join(_build_resolved_card(r, lang) for r in resolved)
        block3 = (
            '<div style="margin-bottom:24px;background:#fff;border-radius:12px;'
            'padding:24px 28px;box-shadow:0 2px 8px rgba(0,0,0,.08)">'
            f'<h2 style="color:#333;font-size:1.1em;border-left:4px solid #b8860b;'
            f'padding-left:10px;margin:0 0 8px 0">{resolved_title}</h2>'
            f'<p style="font-size:0.82em;color:#888;margin:0 0 14px 0">{resolved_desc}</p>'
            f'{resolved_cards}'
            '</div>'
        )
    else:
        block3 = (
            '<div style="margin-bottom:24px;background:#fff;border-radius:12px;'
            'padding:24px 28px;box-shadow:0 2px 8px rgba(0,0,0,.08)">'
            f'<h2 style="color:#333;font-size:1.1em;border-left:4px solid #b8860b;'
            f'padding-left:10px;margin:0 0 8px 0">{resolved_title}</h2>'
            f'<p style="color:#888;font-size:0.9em">{no_resolved_text}</p>'
            '</div>'
        )

    # ── BLOCK 3.5: Related Analysis (Ghost articles) ──
    if analysis_rows:
        analysis_tracking = [r for r in analysis_rows if r.get("status") != "resolved"]
        analysis_resolved = [r for r in analysis_rows if r.get("status") == "resolved"]
        analysis_all = analysis_tracking + analysis_resolved
        if lang == "ja":
            analysis_title = (
                f'関連分析 <span style="font-size:0.8em;color:#888;font-weight:400">'
                f'{len(analysis_all)}件</span>'
            )
            analysis_desc = "Ghost記事から抽出したシナリオ分析。正式な予測とは別枠です。"
        else:
            analysis_title = (
                f'Related Analysis <span style="font-size:0.8em;color:#888;font-weight:400">'
                f'{len(analysis_all)}</span>'
            )
            analysis_desc = "Scenario analyses extracted from articles. Separate from formal predictions."
        analysis_cards = "\n".join(_build_tracking_card(r, lang) for r in analysis_all)
        block3_5 = (
            '<div style="margin-bottom:24px;background:#fff;border-radius:12px;'
            'padding:24px 28px;box-shadow:0 2px 8px rgba(0,0,0,.08)">'
            f'<h2 style="color:#333;font-size:1.1em;border-left:4px solid #94a3b8;'
            f'padding-left:10px;margin:0 0 8px 0">{analysis_title}</h2>'
            f'<p style="font-size:0.82em;color:#888;margin:0 0 14px 0">{analysis_desc}</p>'
            f'<div id="np-analysis-list">{analysis_cards}</div>'
            '</div>'
        )
    else:
        block3_5 = ""

    # ── BLOCK 4: Automation ──


    # ── Inline CSS + JS ──
    inline_code = """<style>
details > summary { list-style:none; cursor:pointer; }
details > summary::-webkit-details-marker { display:none; }
.chevron { transition:transform .2s; display:inline-block; }
details[open] .chevron { transform:rotate(180deg); }
.np-cat-btn:focus { outline:none; }
</style>
<script>
(function(){
  // Category filter
  var cats = document.querySelectorAll('.np-cat-btn');
  cats.forEach(function(btn){
    btn.addEventListener('click', function(){
      cats.forEach(function(b){
        b.style.background='#fff'; b.style.color='#555';
        b.style.border='1px solid #ddd'; b.style.fontWeight='400';
      });
      this.style.background='#b8860b'; this.style.color='#fff';
      this.style.border='2px solid #b8860b'; this.style.fontWeight='600';
      filterCards();
    });
  });
  // Keyword search
  var searchEl = document.getElementById('np-search');
  if(searchEl) searchEl.addEventListener('input', filterCards);
  function filterCards(){
    var activeCat = 'all';
    cats.forEach(function(b){
      if(b.style.background==='rgb(184, 134, 11)' || b.style.background==='#b8860b')
        activeCat = b.dataset.cat;
    });
    var kw = searchEl ? searchEl.value.toLowerCase() : '';
    var cards = document.querySelectorAll('#np-tracking-list details');
    cards.forEach(function(d){
      var genres = (d.dataset.genres || '').split(',');
      var matchCat = activeCat==='all' || genres.indexOf(activeCat)>=0;
      var matchKw = !kw || d.textContent.toLowerCase().indexOf(kw)>=0;
      d.style.display = (matchCat && matchKw) ? '' : 'none';
    });
  }
})();
</script>"""

    return (
        '<div class="np-tracker">'
        + inline_code
        + block1
        + block2
        + block3 + block3_5
        
        + '</div>'
    )


# ── Ghost page update ─────────────────────────────────────────

def update_ghost_page(api_key, slug, page_html, page_title):
    """Create or update a Ghost page by slug."""
    try:
        result = ghost_request("GET", f"/pages/slug/{slug}/?formats=lexical", api_key)
        page = result["pages"][0]
        lexical = json.dumps({
            "root": {
                "children": [{"type": "html", "version": 1, "html": page_html}],
                "direction": None, "format": "", "indent": 0, "type": "root", "version": 1
            }
        })
        fresh = ghost_request("GET", f"/pages/{page['id']}/", api_key)
        ghost_request("PUT", f"/pages/{page['id']}/", api_key, {
            "pages": [{"lexical": lexical, "mobiledoc": None, "updated_at": fresh["pages"][0]["updated_at"]}]
        })
        print(f"  Ghost page /{slug}/ updated OK")
    except Exception as e:
        print(f"  Creating new /{slug}/ page...")
        lexical = json.dumps({
            "root": {
                "children": [{"type": "html", "version": 1, "html": page_html}],
                "direction": None, "format": "", "indent": 0, "type": "root", "version": 1
            }
        })
        ghost_request("POST", "/pages/", api_key, {
            "pages": [{
                "title": page_title,
                "slug": slug,
                "lexical": lexical,
                "mobiledoc": None,
                "status": "published",
            }]
        })
        print(f"  Ghost page /{slug}/ created OK")


# ── Main ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Prediction Page Builder (JA+EN)")
    parser.add_argument("--report", action="store_true", help="Report only")
    parser.add_argument("--update", action="store_true", help="Update Ghost page")
    parser.add_argument("--lang", choices=["ja", "en", "both"], default="both",
                        help="Language to update (default: both)")
    args = parser.parse_args()

    env = load_env()
    api_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not api_key:
        print("ERROR: API key not found")
        sys.exit(1)
    google_api_key = env.get("GOOGLE_API_KEY", "")

    # Load data sources
    pred_db = load_prediction_db()
    embed_data = load_embed_data()
    print(f"Prediction DB: {len(pred_db.get('predictions', []))} entries")

    # Ensure all predictions have Japanese resolution_question (one-time translation)
    pred_db = ensure_ja_translations(pred_db, google_api_key)
    print(f"Polymarket: {len(embed_data)} markets")

    # Fetch articles from Ghost
    ghost_result = ghost_request("GET",
        "/posts/?limit=all&filter=status:published&include=tags&formats=html&fields=id,slug,title,url,html,published_at",
        api_key)
    ghost_posts = ghost_result.get("posts", [])
    print(f"Ghost articles: {len(ghost_posts)}")

    langs = ["ja", "en"] if args.lang == "both" else [args.lang]

    for lang in langs:
        print(f"\n{'='*40}")
        print(f"Building {lang.upper()} page...")
        print(f"{'='*40}")

        rows = build_rows(pred_db, ghost_posts, embed_data, lang)

        print(f"  Total rows: {len(rows)}")
        print(f"    From prediction_db: {sum(1 for r in rows if r['source'] == 'prediction_db')}")
        print(f"    From Ghost HTML: {sum(1 for r in rows if r['source'] == 'ghost_html')}")
        print(f"    With Polymarket match: {sum(1 for r in rows if r.get('polymarket'))}")

        for r in rows:
            pm_str = f"PM={r['polymarket']['probability']:.0f}%" if r.get("polymarket") else "—"
            div_str = f"Δ={r['divergence']:+.0f}%" if r.get("divergence") is not None else ""
            print(f"    B={r.get('base','?')}% {pm_str} {div_str} | {r['title'][:50]}")

        # Build HTML
        page_html = build_page_html(rows, pred_db.get("stats", {}), lang)

        if lang == "ja":
            slug = PREDICTIONS_SLUG_JA
            title = "予測トラッカー — Nowpatternの分析 vs 市場"
        else:
            slug = PREDICTIONS_SLUG_EN
            title = "Prediction Tracker — Nowpattern vs Market"

        if args.report:
            print(f"  [report mode] Would update /{slug}/")
            continue

        if args.update or not args.report:
            update_ghost_page(api_key, slug, page_html, title)

    # Save output data (combined)
    all_rows_ja = build_rows(pred_db, ghost_posts, embed_data, "ja")
    output_data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M JST"),
        "rows": all_rows_ja,
        "stats": pred_db.get("stats", {}),
    }
    with open(TRACKER_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {TRACKER_OUTPUT}")


if __name__ == "__main__":
    main()
