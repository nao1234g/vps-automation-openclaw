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
    # 1) open_loop_trigger is the best source
    trigger = pred.get("open_loop_trigger", "")
    if trigger:
        return trigger[:80]
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
        divergence = None
        if pm_match and base is not None:
            divergence = round(pm_match["probability"] - base, 1)

        dynamics_str = pred.get("dynamics_tags", "")
        url = pred.get("ghost_url", "")

        # Extract event summary for context
        event_summary = extract_event_summary(pred)

        row = {
            "title": title,
            "url": url,
            "base": base, "optimistic": opt, "pessimistic": pess,
            "base_content": base_content,
            "event_summary": event_summary,
            "polymarket": pm_match,
            "divergence": divergence,
            "status": pred.get("status", "open"),
            "outcome": pred.get("outcome"),
            "resolved_at": pred.get("resolved_at", ""),
            "brier": pred.get("brier_score"),
            "dynamics_str": dynamics_str,
            "source": "prediction_db",
        }
        rows.append(row)

        slug = url.split("/")[-2] if url else ""
        if slug:
            seen_slugs.add(slug)

    # Source 2: Ghost articles (fallback for articles not in prediction_db)
    for p in ghost_posts:
        if p["slug"] in seen_slugs:
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
    """Build a simple article row with event context."""
    L = LABELS[lang]
    base = r.get("base")
    title_short = r["title"][:50] + ("..." if len(r["title"]) > 50 else "")
    url = r.get("url", "#")

    # Event context — what is this probability about?
    event = r.get("event_summary") or r.get("base_content", "")
    event_short = event[:50] + ("..." if len(event) > 50 else "") if event else ""

    if base is not None:
        if event_short:
            scenario_text = f'<span style="font-size:0.85em;color:#555">{event_short}</span><br><strong>{base}%</strong>'
        else:
            scenario_text = f'<strong>{base}%</strong>'
    else:
        scenario_text = f'<span style="color:#666">{L["analyzing"]}</span>'

    return (
        f'<div style="display:flex;align-items:center;gap:12px;padding:10px 0;'
        f'border-bottom:1px solid #e0e0e0">'
        f'<a href="{url}" style="color:#b8860b;text-decoration:none;flex:1;'
        f'font-size:1em;overflow:hidden;text-overflow:ellipsis">{title_short}</a>'
        f'<span style="color:#333;font-size:0.95em;min-width:120px;text-align:right;line-height:1.4">{scenario_text}</span>'
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

    # ── Section 3: Tracking list ──
    tracking_html = ""
    if tracking:
        article_rows = [_build_article_row(r, lang) for r in tracking[:200]]
        overflow = ""
        if len(tracking) > 200:
            overflow = f'<div style="padding:10px;text-align:center;color:#888;font-size:0.9em">{L["overflow"].format(count=len(tracking)-200)}</div>'

        tracking_html = (
            f'<details style="margin-bottom:32px">'
            f'<summary style="cursor:pointer;color:#b8860b;font-size:1.1em;font-weight:600;'
            f'padding:12px 0;user-select:none">'
            f'{L["tracking_summary"].format(count=len(tracking))}</summary>'
            f'<div style="margin-top:10px;padding:12px 16px;background:#f9f9f6;border-radius:8px">'
            + "\n".join(article_rows) + overflow
            + '</div></details>'
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
        "/posts/?limit=all&include=tags&formats=html&fields=id,slug,title,url,html,published_at",
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
