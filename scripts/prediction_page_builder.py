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
    returns: {prediction_id: {"question": str, "yes_prob": float, "direction": str}}
    """
    if not os.path.exists(MARKET_HISTORY_DB):
        return {}
    try:
        db = sqlite3.connect(MARKET_HISTORY_DB)
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute("""
            SELECT nl.prediction_id, nl.resolution_direction,
                   m.question, m.close_date,
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
            }
        db.close()
        return result
    except Exception:
        return {}


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
        return triggers[0][0][:80] if isinstance(triggers[0], list) else str(triggers[0])[:80]
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
        base_content = ""
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
            elif "悲観" in label or "pessimistic" in label:
                pess = prob_pct

        if base is None and opt is None and pess is None:
            continue

        genres = []
        genre_str = pred.get("genre_tags", "")
        if genre_str:
            genres = [g.strip().lower() for g in genre_str.split(",")]

        pm_match = find_polymarket_match(title, genres, embed_data)
        mc_match = find_metaculus_match(title)
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

        row = {
            "title": title,
            "url": url,
            "base": base, "optimistic": opt, "pessimistic": pess,
            "base_content": base_content,
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
            # Pattern A fields
            "prediction_id": prediction_id,
            "linked_market_question": linked_market_question,
            "linked_market_prob": linked_market_prob,
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
            "event_summary": "",
            "polymarket": pm_match,
            "metaculus": mc_match,
            "divergence": divergence,
            "status": "open",
            "brier": None,
            "dynamics_str": dynamics_str,
            "source": "ghost_html",
        }
        rows.append(row)
        seen_slugs.add(p["slug"])

    return rows


# ── Page HTML builder ──────────────────────────────────────────

def _build_featured_card(r, lang="ja"):
    """Build a featured card with clear event description."""
    L = LABELS[lang]
    base = r.get("base")
    pm = r.get("polymarket", {})
    prob = pm.get("probability", 0) if pm else 0
    pm_q = pm.get("question", "") if pm else ""
    title_short = r["title"][:55] + ("..." if len(r["title"]) > 55 else "")
    url = r.get("url", "#")

    # Event context — WHAT is being predicted
    event = r.get("event_summary") or r.get("base_content", "")
    event_short = event[:100] + ("..." if len(event) > 100 else "") if event else ""
    event_html = ""
    if event_short:
        event_html = f'<div style="color:#555;font-size:0.95em;margin-bottom:8px;line-height:1.5">{event_short}</div>'

    # Plain-language comparison
    if base is not None and pm:
        diff = prob - base
        if abs(diff) >= 15:
            if diff > 0:
                verdict = f'<strong style="color:#FF1A75">{L["market_higher"]}</strong>'
            else:
                verdict = f'<strong style="color:#FF1A75">{L["market_lower"]}</strong>'
        elif abs(diff) >= 5:
            verdict = f'<strong style="color:#f59e0b">{L["diff_small"]}</strong>'
        else:
            verdict = f'<strong style="color:#16a34a">{L["diff_same"]}</strong>'

        if lang == "ja":
            story = (
                f'私たちの予測: <strong>{base}%</strong> ／ '
                f'賭け市場（実際にお金を賭けている人たち）: <strong>{prob:.0f}%</strong><br>'
                f'{verdict}'
            )
        else:
            story = (
                f'Our prediction: <strong>{base}%</strong> / '
                f'Betting market (real money): <strong>{prob:.0f}%</strong><br>'
                f'{verdict}'
            )
    elif base is not None:
        if lang == "ja":
            story = f'基本シナリオの確率: <strong>{base}%</strong>'
        else:
            story = f'Base scenario probability: <strong>{base}%</strong>'
    else:
        story = ''

    # Side-by-side bar
    bar_html = ''
    if base is not None and pm:
        bar_html = (
            '<div style="display:flex;gap:4px;margin:12px 0 8px 0;height:32px">'
            f'<div style="width:{max(base, 5)}%;background:linear-gradient(90deg,#16a34a,#22c55e);'
            f'border-radius:4px 0 0 4px;display:flex;align-items:center;justify-content:center;'
            f'min-width:55px">'
            f'<span style="color:#fff;font-size:0.8em;font-weight:700">{L["bar_ours"]} {base}%</span></div>'
            f'<div style="width:{max(prob, 5)}%;background:linear-gradient(90deg,#3b82f6,#60a5fa);'
            f'border-radius:0 4px 4px 0;display:flex;align-items:center;justify-content:center;'
            f'min-width:55px">'
            f'<span style="color:#fff;font-size:0.8em;font-weight:700">{L["bar_market"]} {prob:.0f}%</span></div>'
            '</div>'
        )

    pm_label = f'<div style="font-size:0.85em;color:#777;margin-top:8px">{L["market_q_label"]}: {pm_q}</div>' if pm_q else ''

    return (
        '<div style="background:#f5f5f0;'
        'border:2px solid #b8860b44;border-radius:10px;padding:20px 24px;margin-bottom:16px">'
        f'<a href="{url}" style="color:#b8860b;text-decoration:none;font-weight:700;'
        f'font-size:1.1em;display:block;margin-bottom:8px">{title_short}</a>'
        f'{event_html}'
        f'<p style="color:#333;font-size:1em;line-height:1.7;margin:0 0 6px 0">{story}</p>'
        f'{bar_html}{pm_label}'
        '</div>'
    )


def _build_article_row(r, lang="ja"):
    """Build a Pattern A expandable card: summary line + click-to-expand details."""
    L = LABELS[lang]
    bear = r.get("pessimistic")
    base = r.get("base")
    bull = r.get("optimistic")
    title = r.get("title", "")
    url = r.get("url", "#")
    base_content = r.get("base_content", "")
    dynamics_str = r.get("dynamics_str", "")
    linked_q = r.get("linked_market_question")
    linked_prob = r.get("linked_market_prob")  # float 0.0-1.0 or None

    # Labels per language
    if lang == "ja":
        bear_label = "悲観"
        base_label = "基本"
        bull_label = "楽観"
        analyzing = L.get("analyzing", "分析中")
    else:
        bear_label = "Bear"
        base_label = "Base"
        bull_label = "Bull"
        analyzing = L.get("analyzing", "Analyzing")

    # Build scenario chips (compact, inline)
    def chip(label, val, bg, color, border=""):
        if val is not None:
            border_style = f"border:{border};" if border else ""
            return (
                f'<span style="display:inline-flex;flex-direction:column;align-items:center;'
                f'min-width:52px;padding:4px 6px;border-radius:5px;'
                f'background:{bg};{border_style}">'
                f'<span style="font-size:0.68em;color:{color};font-weight:600;opacity:0.85">{label}</span>'
                f'<span style="font-size:1em;font-weight:700;color:{color}">{val}%</span>'
                f'</span>'
            )
        return (
            f'<span style="display:inline-flex;flex-direction:column;align-items:center;'
            f'min-width:52px;padding:4px 6px;border-radius:5px;background:#f5f5f5;">'
            f'<span style="font-size:0.68em;color:#999;font-weight:600">{label}</span>'
            f'<span style="font-size:0.85em;color:#bbb">—</span>'
            f'</span>'
        )

    has_scenarios = any(v is not None for v in [bear, base, bull])
    if has_scenarios:
        chips_html = (
            f'<span style="display:inline-flex;gap:4px;vertical-align:middle;margin-left:8px">'
            + chip(bear_label, bear, "#fde8e8", "#dc2626")
            + chip(base_label, base, "#fff8e1", "#b8860b", "1px solid #b8860b55")
            + chip(bull_label, bull, "#e8f5e9", "#16a34a")
            + f'</span>'
        )
    else:
        chips_html = (
            f'<span style="font-size:0.85em;color:#999;margin-left:8px">{analyzing}</span>'
        )

    # Market probability badge (from nowpattern_links / market_history.db)
    market_badge = ""
    if linked_prob is not None:
        pct = round(linked_prob * 100)
        market_badge = (
            f'<span style="margin-left:8px;padding:3px 8px;border-radius:12px;'
            f'background:#e8f0fe;color:#1a56db;font-size:0.78em;font-weight:700;'
            f'white-space:nowrap">{L["linked_market"]}: {pct}%</span>'
        )

    # ── Summary line (always visible) ──
    summary_line = (
        f'<div style="display:flex;align-items:flex-start;flex-wrap:wrap;gap:4px;">'
        f'<a href="{url}" style="color:#b8860b;text-decoration:none;font-weight:600;'
        f'font-size:0.97em;line-height:1.5;flex:1;min-width:200px">{title}</a>'
        f'<span style="display:inline-flex;align-items:center;flex-wrap:wrap;gap:4px">'
        + chips_html + market_badge +
        f'</span>'
        f'</div>'
    )

    # ── Expanded content ──
    expanded_parts = []

    if base_content:
        short = base_content[:120] + ("..." if len(base_content) > 120 else "")
        expanded_parts.append(
            f'<p style="margin:8px 0 4px 0;color:#444;font-size:0.9em;line-height:1.6">'
            f'{short}</p>'
        )

    if linked_q:
        expanded_parts.append(
            f'<div style="margin-top:8px;padding:6px 10px;background:#e8f0fe;'
            f'border-left:3px solid #1a56db;border-radius:3px;font-size:0.82em;color:#333">'
            f'<span style="font-weight:600;color:#1a56db">{L["linked_market"]}</span>: {linked_q}'
            + (f' <strong style="color:#1a56db">→ {round(linked_prob*100)}%</strong>' if linked_prob is not None else "")
            + f'</div>'
        )

    if dynamics_str:
        expanded_parts.append(
            f'<div style="margin-top:6px;font-size:0.8em;color:#777">'
            f'⚡ {dynamics_str}</div>'
        )

    expanded_html = "\n".join(expanded_parts) if expanded_parts else ""

    if expanded_html:
        return (
            f'<details style="margin-bottom:10px;border-bottom:1px solid #ebebeb;'
            f'padding-bottom:8px">'
            f'<summary style="cursor:pointer;list-style:none;user-select:none">'
            + summary_line +
            f'</summary>'
            f'<div style="padding:4px 0 4px 4px">'
            + expanded_html +
            f'</div>'
            f'</details>'
        )
    else:
        return (
            f'<div style="margin-bottom:10px;border-bottom:1px solid #ebebeb;'
            f'padding-bottom:8px">'
            + summary_line +
            f'</div>'
        )


def _build_resolved_card(r, lang="ja"):
    """Build a card for resolved predictions."""
    L = LABELS[lang]
    title_short = r["title"][:55] + ("..." if len(r["title"]) > 55 else "")
    url = r.get("url", "#")
    base = r.get("base")
    outcome = r.get("outcome")  # "楽観" / "基本" / "悲観"
    brier = r.get("brier")
    resolved_at = r.get("resolved_at", "")

    outcome_map = {
        "楽観": L["outcome_optimistic"],
        "基本": L["outcome_base"],
        "悲観": L["outcome_pessimistic"],
    }
    label, color, icon = outcome_map.get(outcome, L["outcome_default"])
    result_text = f'<span style="color:{color};font-weight:700">{label}</span>'

    accuracy_text = ''
    if brier is not None:
        if brier < 0.15:
            accuracy_text = f'<span style="color:#16a34a;font-size:0.8em"> {L["accuracy_hit"]}</span>'
        elif brier < 0.25:
            accuracy_text = f'<span style="color:#f59e0b;font-size:0.8em"> {L["accuracy_ok"]}</span>'
        else:
            accuracy_text = f'<span style="color:#dc2626;font-size:0.8em"> {L["accuracy_miss"]}</span>'

    base_text = f'{L["prediction_at"]}: {base}%' if base is not None else ''
    date_text = resolved_at[:10] if resolved_at else ''

    return (
        '<div style="background:#f5f5f0;border-radius:8px;padding:16px 20px;margin-bottom:10px;'
        'display:flex;align-items:center;gap:14px">'
        f'<span style="font-size:1.4em;color:{color};min-width:28px">{icon}</span>'
        f'<div style="flex:1">'
        f'<a href="{url}" style="color:#b8860b;text-decoration:none;font-weight:600;font-size:1em">'
        f'{title_short}</a>'
        f'<div style="color:#666;font-size:0.9em;margin-top:3px">{base_text}'
        f'{" | " + date_text if date_text else ""}</div>'
        f'</div>'
        f'<div style="text-align:right">{result_text}{accuracy_text}</div>'
        '</div>'
    )


def build_page_html(rows, stats, lang="ja"):
    """Build predictions page HTML — supports ja and en."""
    L = LABELS[lang]
    now = datetime.now().strftime("%Y-%m-%d %H:%M JST")

    total = len(rows)
    featured = [r for r in rows if r.get("polymarket")]
    resolved = [r for r in rows if r.get("status") == "resolved"]
    tracking = [r for r in rows if r.get("status") != "resolved"]

    # ── Hero ──
    hero = (
        '<div style="margin-bottom:28px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<h2 style="color:#b8860b;margin:0 0 12px 0;font-size:1.5em">'
        f'{L["hero_heading"]}</h2>'
        f'{L["other_lang_link"]}'
        f'</div>'
        f'<p style="color:#333;font-size:1.05em;line-height:1.8;margin:0">'
        f'{L["hero_text"]}'
        '</p></div>'
    )

    # ── Stats ──
    stats_html = (
        f'<div style="display:flex;gap:24px;flex-wrap:wrap;margin-bottom:28px;'
        f'padding:14px 20px;background:#f5f5f0;border-radius:8px;font-size:1em;color:#555">'
        f'<div><strong style="color:#b8860b;font-size:1.3em">{total}</strong> {L["stat_predictions"]}</div>'
        f'<div><strong style="color:#16a34a;font-size:1.3em">{len(tracking)}</strong> {L["stat_tracking"]}</div>'
        f'<div><strong style="font-size:1.3em">{len(resolved)}</strong> {L["stat_resolved"]}</div>'
        f'<div style="margin-left:auto;font-size:0.9em;color:#888">{L["last_updated"]}: {now}</div>'
        f'</div>'
    )

    # ── Brier Scoreboard ──
    scored_rows = [r for r in resolved if r.get("brier") is not None]
    hits = sum(1 for r in scored_rows if r.get("brier", 1) < 0.25)
    misses = len(scored_rows) - hits
    avg_brier = (sum(r["brier"] for r in scored_rows) / len(scored_rows)) if scored_rows else None

    if scored_rows:
        if avg_brier < 0.15:
            brier_quality = L["scoreboard_brier_good"]
            brier_color = "#16a34a"
        elif avg_brier < 0.25:
            brier_quality = L["scoreboard_brier_ok"]
            brier_color = "#f59e0b"
        else:
            brier_quality = L["scoreboard_brier_bad"]
            brier_color = "#dc2626"
        scoreboard_html = (
            f'<div style="margin-bottom:28px;padding:16px 20px;'
            f'background:linear-gradient(135deg,#fffbeb,#fef3c7);'
            f'border:1px solid #b8860b44;border-radius:10px">'
            f'<div style="font-weight:700;color:#b8860b;font-size:1.05em;margin-bottom:10px">'
            f'{L["scoreboard_title"]}</div>'
            f'<div style="display:flex;gap:20px;flex-wrap:wrap;align-items:center">'
            f'<div style="font-size:1.5em;font-weight:800;color:#16a34a">{hits}</div>'
            f'<div style="font-size:0.9em;color:#555">{L["scoreboard_hit"]}</div>'
            f'<div style="font-size:0.95em;color:#aaa">／</div>'
            f'<div style="font-size:1.5em;font-weight:800;color:#dc2626">{misses}</div>'
            f'<div style="font-size:0.9em;color:#555">{L["scoreboard_miss"]}</div>'
            f'<div style="margin-left:auto;text-align:right">'
            f'<div style="font-size:0.8em;color:#888">{L["scoreboard_brier"]}</div>'
            f'<div style="font-size:1.3em;font-weight:700;color:{brier_color}">'
            f'{avg_brier:.2f}'
            f'<span style="font-size:0.7em;font-weight:400;margin-left:4px">{brier_quality}</span>'
            f'</div></div>'
            f'</div></div>'
        )
    else:
        scoreboard_html = (
            f'<div style="margin-bottom:28px;padding:14px 20px;'
            f'background:#f9f9f6;border:1px dashed #ccc;border-radius:10px;'
            f'text-align:center;color:#888;font-size:0.9em">'
            f'{L["scoreboard_no_data"]}'
            f'</div>'
        )

    # ── Section 1: Featured ──
    featured.sort(key=lambda r: abs(r.get("divergence") or 0), reverse=True)
    featured_html = ""
    if featured:
        cards = [_build_featured_card(r, lang) for r in featured[:10]]
        featured_html = (
            '<div style="margin-bottom:32px">'
            f'<h3 style="color:#222;font-size:1.2em;margin:0 0 8px 0">'
            f'{L["featured_heading"]}</h3>'
            f'<p style="color:#555;font-size:0.95em;margin:0 0 16px 0">'
            f'{L["featured_desc"]}</p>'
            + "\n".join(cards)
            + '</div>'
        )

    # ── Section 2: Resolved ──
    resolved_html = ""
    if resolved:
        res_cards = [_build_resolved_card(r, lang) for r in resolved[:50]]
        resolved_html = (
            '<div style="margin-bottom:32px">'
            f'<h3 style="color:#222;font-size:1.2em;margin:0 0 8px 0">'
            f'{L["resolved_heading"]}</h3>'
            f'<p style="color:#555;font-size:0.95em;margin:0 0 16px 0">'
            f'{L["resolved_desc"]}</p>'
            + "\n".join(res_cards)
            + '</div>'
        )
    else:
        resolved_html = (
            '<div style="margin-bottom:32px;padding:24px;background:#f9f9f6;'
            'border-radius:8px;text-align:center">'
            f'<p style="color:#666;font-size:1em;margin:0">'
            f'{L["no_resolved"]}</p>'
            '</div>'
        )

    # ── Section 3: Tracking list (individual expandable cards) ──
    tracking_html = ""
    if tracking:
        article_rows = [_build_article_row(r, lang) for r in tracking[:200]]
        overflow = ""
        if len(tracking) > 200:
            overflow = f'<div style="padding:10px;text-align:center;color:#888;font-size:0.9em">{L["overflow"].format(count=len(tracking)-200)}</div>'

        tracking_html = (
            f'<div style="margin-bottom:32px">'
            f'<h3 style="color:#222;font-size:1.2em;margin:0 0 12px 0">'
            f'{L["tracking_section_title"]} ({len(tracking)})</h3>'
            f'<div style="padding:12px 16px;background:#f9f9f6;border-radius:8px">'
            + "\n".join(article_rows) + overflow
            + '</div></div>'
        )

    # ── Footer ──
    footer = (
        '<div style="margin-top:24px;padding:14px 18px;border-top:1px solid #e0e0e0;'
        'font-size:0.9em;color:#888;line-height:1.7">'
        f'<p style="margin:0">{L["footer_polymarket"]}'
        f'<a href="https://polymarket.com" style="color:#b8860b">Polymarket</a>'
        f'{L["footer_polymarket_desc"]}</p>'
        f'<p style="margin:4px 0 0 0">{L["footer_auto"]}</p>'
        '</div>'
    )

    return f"""<div class="np-tracker">
{hero}
{stats_html}
{scoreboard_html}
{featured_html}
{resolved_html}
{tracking_html}
{footer}
</div>"""


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

    # Load data sources
    pred_db = load_prediction_db()
    embed_data = load_embed_data()
    print(f"Prediction DB: {len(pred_db.get('predictions', []))} entries")
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
