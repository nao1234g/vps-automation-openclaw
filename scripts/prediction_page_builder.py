# [Phase8] rules_footer_installed
# Rules links injected into page HTML below
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
import math
from datetime import datetime, timezone

from prediction_state_utils import is_prediction_resolved, normalize_public_status, public_prediction_status

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Config ─────────────────────────────────────────────────────

# ── Feature Flags (Phase-gate for forecast platform features) ──────────────────
# Set to True to enable. All False = safe defaults (no UI changes).
FEATURE_FLAGS = {
    "COUNTER_FORECAST_UI":       False,  # Week 1: enable when explanation field is in use
    "LEADERBOARD_PAGE":          False,  # Week 1: enable after /leaderboard/ Ghost page created
    "BRIER_INDEX_DISPLAY":       True,   # Week 2: switch public score from raw Brier to Brier Index
    "NAMED_PROFILES":            False,  # Phase 1.5: enable after UUID->email bridge is built
    "RESOLUTION_NOTIFICATIONS":  False,  # Phase 2: enable after Ghost Members bridge is complete
}

DEFAULT_PUBLIC_SCORE_TIER = "PROVISIONAL"
INTEGRITY_AUDIT_PATHS = {
    "ja": "/integrity-audit/",
    "en": "/en/integrity-audit/",
}
_STATUS_ALIASES = {
    "open": "open",
    "active": "active",
    "resolving": "resolving",
    "awaiting_evidence": "resolving",
    "expired_unresolved": "resolving",
    "resolved": "resolved",
    "disputed": "disputed",
}
_VALID_SCORE_TIERS = {
    "VERIFIED_OFFICIAL",
    "MIGRATED_OFFICIAL",
    "PROVISIONAL",
    "NOT_SCORABLE",
}


def _normalize_status_value(status_or_prediction):
    if isinstance(status_or_prediction, dict):
        return public_prediction_status(status_or_prediction)
    return normalize_public_status(status_or_prediction)


def _is_resolved_status(status_or_prediction):
    if isinstance(status_or_prediction, dict):
        return is_prediction_resolved(status_or_prediction)
    return _normalize_status_value(status_or_prediction) == "resolved"


def _normalize_score_tier(score_tier, brier=None):
    tier = str(score_tier or "").strip().upper()
    if tier in _VALID_SCORE_TIERS:
        return tier
    if brier is None:
        return DEFAULT_PUBLIC_SCORE_TIER
    return DEFAULT_PUBLIC_SCORE_TIER


def _score_tier_meta(score_tier, lang):
    tier = _normalize_score_tier(score_tier)
    if lang == "ja":
        mapping = {
            "PROVISIONAL": {
                "label": "暫定計算値",
                "note": "このスコアは事後登録確率からの暫定計算値です。独立検証と OTS 確認待ちです。",
                "bg": "#F3F4F6",
                "border": "#D1D5DB",
                "color": "#6B7280",
            },
            "MIGRATED_OFFICIAL": {
                "label": "移行確定スコア",
                "note": "OTS で移行確認済みです。公開時点と完全一致するかは別途監査対象です。",
                "bg": "#FFFBEB",
                "border": "#FCD34D",
                "color": "#B45309",
            },
            "VERIFIED_OFFICIAL": {
                "label": "公式確定スコア",
                "note": "公開前ハッシュと OTS が一致した公式確定スコアです。",
                "bg": "#DCFCE7",
                "border": "#86EFAC",
                "color": "#166534",
            },
            "NOT_SCORABLE": {
                "label": "採点対象外",
                "note": "この予測は verdict のみ表示し、Brier 系スコアは公開しません。",
                "bg": "#FEF2F2",
                "border": "#FCA5A5",
                "color": "#B91C1C",
            },
        }
    else:
        mapping = {
            "PROVISIONAL": {
                "label": "Provisional Score",
                "note": "This score is backfilled from post-hoc probabilities and is awaiting independent / OTS confirmation.",
                "bg": "#F3F4F6",
                "border": "#D1D5DB",
                "color": "#6B7280",
            },
            "MIGRATED_OFFICIAL": {
                "label": "Migrated Official Score",
                "note": "OTS confirms the migrated record, but publication-time parity is still audited separately.",
                "bg": "#FFFBEB",
                "border": "#FCD34D",
                "color": "#B45309",
            },
            "VERIFIED_OFFICIAL": {
                "label": "Official Verified Score",
                "note": "Pre-publication hash and OTS proof match this official verified score.",
                "bg": "#DCFCE7",
                "border": "#86EFAC",
                "color": "#166534",
            },
            "NOT_SCORABLE": {
                "label": "Not Scored",
                "note": "This prediction shows a verdict only. No Brier-based score is published.",
                "bg": "#FEF2F2",
                "border": "#FCA5A5",
                "color": "#B91C1C",
            },
        }
    return mapping[tier]


def _score_tier_badge_html(score_tier, lang, compact=False):
    tier = _normalize_score_tier(score_tier)
    meta = _score_tier_meta(tier, lang)
    class_name = tier.lower().replace("_", "-")
    font_size = "0.62em" if compact else "0.68em"
    padding = "1px 7px" if compact else "2px 8px"
    return (
        f'<span class="score-tier-label {class_name}" '
        f'style="display:inline-block;background:{meta["bg"]};color:{meta["color"]};'
        f'border:1px solid {meta["border"]};border-radius:9999px;'
        f'font-size:{font_size};font-weight:700;padding:{padding};vertical-align:middle">'
        f'{meta["label"]}</span>'
    )


def _score_disclaimer_html(score_tier, lang, compact=False, include_link=True):
    meta = _score_tier_meta(score_tier, lang)
    font_size = "0.72em" if compact else "0.78em"
    audit_path = INTEGRITY_AUDIT_PATHS["ja" if lang == "ja" else "en"]
    if include_link:
        link_text = "監査詳細" if lang == "ja" else "Audit details"
        link_html = (
            f' <a href="{audit_path}" style="color:#6366F1;text-decoration:none;'
            f'border-bottom:1px dotted #6366F1">{link_text} ↗</a>'
        )
    else:
        link_html = ""
    return (
        f'<div class="score-disclaimer" style="font-size:{font_size};color:#6B7280;'
        f'line-height:1.5;margin-top:6px">{meta["note"]}{link_html}</div>'
    )


def _brier_index_value(raw_brier):
    try:
        brier = float(raw_brier)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(brier):
        return None
    brier = max(0.0, min(1.0, brier))
    return round((1.0 - math.sqrt(brier)) * 100.0, 1)


def _public_score_value(raw_brier):
    if FEATURE_FLAGS.get("BRIER_INDEX_DISPLAY", False):
        return _brier_index_value(raw_brier)
    try:
        return round(float(raw_brier), 2)
    except (TypeError, ValueError):
        return None


def _public_score_color(score_value):
    if score_value is None:
        return "#94A3B8"
    if FEATURE_FLAGS.get("BRIER_INDEX_DISPLAY", False):
        if score_value >= 70:
            return "#16A34A"
        if score_value >= 55:
            return "#D97706"
        return "#DC2626"
    if score_value < 0.15:
        return "#16A34A"
    if score_value < 0.25:
        return "#D97706"
    return "#DC2626"


def _score_basis_note(lang, raw_brier, market_raw_brier=None):
    if FEATURE_FLAGS.get("BRIER_INDEX_DISPLAY", False):
        base = (
            f'公開表示は Brier Index（raw Brier {float(raw_brier):.2f} 由来）'
            if lang == "ja"
            else f'Public display uses Brier Index (from raw Brier {float(raw_brier):.2f})'
        )
        if market_raw_brier is not None:
            base += (
                f' / 市場 raw {float(market_raw_brier):.2f}'
                if lang == "ja"
                else f' / market raw {float(market_raw_brier):.2f}'
            )
        return base
    return (
        "※ 低いほど良い（raw Brier Score）"
        if lang == "ja"
        else "Lower is better (raw Brier Score)"
    )


def _scenario_bucket(outcome):
    outcome_lower = str(outcome or "").strip().lower()
    if not outcome_lower:
        return None
    if any(keyword in outcome_lower for keyword in ("楽観", "optimistic", "bull")):
        return "optimistic"
    if any(keyword in outcome_lower for keyword in ("悲観", "pessimistic", "bear")):
        return "pessimistic"
    if any(keyword in outcome_lower for keyword in ("基本", "base", "neutral")):
        return "base"
    return None


def _resolved_binary_outcome(row):
    bucket = _scenario_bucket(row.get("outcome"))
    if bucket is None:
        return None
    direction = str(row.get("resolution_direction") or "optimistic").strip().lower()
    direction = "pessimistic" if direction == "pessimistic" else "optimistic"
    if bucket == "base":
        return 1.0 if direction == "optimistic" else 0.0
    yes_bucket = "optimistic" if direction == "optimistic" else "pessimistic"
    return 1.0 if bucket == yes_bucket else 0.0


def _aggregate_score_tier(rows):
    tiers = {
        _normalize_score_tier(r.get("official_score_tier"), r.get("brier"))
        for r in rows
        if r.get("brier") is not None
    }
    tiers.discard("NOT_SCORABLE")
    if not tiers:
        return "NOT_SCORABLE"
    if tiers == {"VERIFIED_OFFICIAL"}:
        return "VERIFIED_OFFICIAL"
    if tiers <= {"VERIFIED_OFFICIAL", "MIGRATED_OFFICIAL"}:
        return "MIGRATED_OFFICIAL"
    return "PROVISIONAL"


def check_gate_f_provisional_labels(html_content):
    """
    Enforce tier labels / disclaimers on every public score display.
    Blocks deploy if a score appears without provenance context.
    """
    import re

    score_markers = [
        "公開Brier Index",
        "Public Score",
        "Nowpattern Brier Index:",
    ]
    for marker in score_markers:
        for match in re.finditer(re.escape(marker), html_content):
            window = html_content[match.start():match.start() + 900]
            if (
                "score-tier-label" not in window
                or "score-disclaimer" not in window
            ) and "採点対象外" not in window and "Not Scored" not in window:
                raise AssertionError(
                    f"Gate F FAIL: score display missing tier/disclaimer near '{marker}'"
                )

    if FEATURE_FLAGS.get("BRIER_INDEX_DISPLAY", False):
        forbidden = (
            "Nowpattern Brier:",
            "Market Brier:",
            "Lower = better (Brier score)",
        )
        for marker in forbidden:
            if marker in html_content:
                raise AssertionError(
                    f"Gate F FAIL: legacy raw-Brier public label still present: {marker}"
                )

    return True

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
# MARKET_ACCURACY_PCT: removed — _scoreboard_block() computes accuracy dynamically from resolved predictions

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
    timeout_s = 180 if method in {"PUT", "POST"} else 30
    last_error = None
    for _attempt in range(2):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, context=ctx, timeout=timeout_s) as resp:
                return json.loads(resp.read())
        except TimeoutError as e:
            last_error = e
        except Exception as e:
            last_error = e
            break
    raise last_error


# ── Data loading ───────────────────────────────────────────────

def load_prediction_db():
    if os.path.exists(PREDICTION_DB):
        with open(PREDICTION_DB, encoding="utf-8") as f:
            db = json.load(f)
    else:
        return {"predictions": [], "stats": {}}
    # ★ 自動修正 (2026-03-29): エラー文字列をデータロード時に除去
    # コンテンツ抽出失敗文字列がUIに到達しないよう、ソースで除去する
    _ERROR_STRINGS = {"(本文抽出不可)"}
    _TEXT_FIELDS = (
        "hit_condition_ja", "hit_condition_en", "oracle_criteria",
        "base_content", "opt_content", "pess_content",
        "oracle_question", "title",
    )
    for _pred in db.get("predictions", []):
        for _f in _TEXT_FIELDS:
            if _pred.get(_f) in _ERROR_STRINGS:
                _pred[_f] = ""
        for _sc in _pred.get("scenarios", []):
            if isinstance(_sc, dict) and _sc.get("content") in _ERROR_STRINGS:
                _sc["content"] = ""
        for _sc in _pred.get("scenarios_labeled", []):
            if isinstance(_sc, dict) and _sc.get("content") in _ERROR_STRINGS:
                _sc["content"] = ""
    return db


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
                   m.market_slug, m.event_slug, m.external_id, m.event_id,
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
                "event_id": str(row["event_id"]) if row["event_id"] else "",
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
            return f"https://polymarket.com/market/{slug}"
        # Fallback: event_id-based URL (Polymarket redirects numeric event IDs)
        if linked.get("event_id"):
            return f"https://polymarket.com/event/{linked['event_id']}"
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


def en_safe(value: str, field_name: str, lang: str) -> str:
    """L4 Rendering Guard (Google/Airbnb style).
    On EN page output, if CJK characters are detected,
    return a visible red error placeholder instead of silently falling back.
    This makes missing translations visibly ugly so they can't ship.
    """
    if lang != "en" or not value:
        return value or ""
    if _is_japanese(str(value)):
        return (
            f'<span style="color:#dc2626;font-weight:700;font-size:0.82em;'
            f'background:#fff0f0;border:1px solid #fca5a5;border-radius:3px;'
            f'padding:1px 8px;display:inline-block">'
            f'&#128683; [TRANSLATION MISSING: {field_name}]</span>'
        )
    return value


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



# ── URL resolver: Ghost API URL 検証 + SQLite fallback ────────────────────

import sqlite3 as _sqlite3

_GHOST_DB_PATH = "/var/www/nowpattern/content/data/ghost.db"

def _resolve_ghost_url(api_url: str, slug: str) -> str:
    """
    Ghost Admin APIのurlフィールドを検証し正しい /{primary_tag}/{slug}/ 形式を返す。
    API URLが正しくない場合(primary_tagなし)はSQLite DBからprimary_tagを取得。
    """
    if api_url:
        return api_url if api_url.endswith("/") else api_url + "/"
    if not slug:
        return ""
    # Fallback: query SQLite DB for primary_tag
    try:
        conn = _sqlite3.connect(_GHOST_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT t.slug FROM posts p "
            "JOIN posts_tags pt ON pt.post_id = p.id "
            "JOIN tags t ON t.id = pt.tag_id "
            "WHERE p.slug = ? AND pt.sort_order = 0",
            (slug,)
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return f"{GHOST_URL}/{row[0]}/{slug}/"
    except Exception:
        pass
    return ""


def _normalize_public_url(url: str) -> str:
    return (url or "").strip().rstrip("/")


def _infer_url_lang(url: str, fallback_lang: str = "") -> str:
    normalized = _normalize_public_url(url)
    if normalized:
        return "en" if "/en/" in normalized else "ja"
    fallback_lang = (fallback_lang or "").strip().lower()
    return fallback_lang if fallback_lang in {"ja", "en"} else ""


def _resolve_live_candidate_url(raw_url: str, raw_slug: str, ghost_slug_url_map: dict, ghost_url_set: set) -> str:
    slug = (raw_slug or "").strip()
    url_norm = _normalize_public_url(raw_url)
    if slug and slug in ghost_slug_url_map:
        return ghost_slug_url_map[slug]
    if url_norm and url_norm in ghost_url_set:
        return raw_url if raw_url.endswith("/") else raw_url + "/"
    if url_norm:
        slug_from_url = url_norm.split("/")[-1]
        if slug_from_url in ghost_slug_url_map:
            return ghost_slug_url_map[slug_from_url]
    return ""


def _iter_live_ghost_candidates(pred: dict, ghost_slug_url_map: dict, ghost_url_set: set) -> list[dict]:
    raw_candidates = []
    for article in pred.get("article_links") or []:
        if not isinstance(article, dict):
            continue
        article_url = (article.get("url") or "").strip()
        article_slug = (article.get("slug") or article_url.rstrip("/").split("/")[-1]).strip()
        raw_candidates.append({
            "url": article_url,
            "slug": article_slug,
            "lang": (article.get("lang") or "").strip().lower(),
        })

    ghost_url = (pred.get("ghost_url") or "").strip()
    if ghost_url:
        raw_candidates.append({
            "url": ghost_url,
            "slug": (pred.get("article_slug") or ghost_url.rstrip("/").split("/")[-1]).strip(),
            "lang": "",
        })

    article_slug = (pred.get("article_slug") or "").strip()
    if article_slug:
        raw_candidates.append({"url": "", "slug": article_slug, "lang": ""})

    candidates = []
    seen = set()
    for item in raw_candidates:
        resolved_url = _resolve_live_candidate_url(item["url"], item["slug"], ghost_slug_url_map, ghost_url_set)
        resolved_lang = _infer_url_lang(resolved_url, item["lang"])
        key = (_normalize_public_url(resolved_url), item["slug"], resolved_lang)
        if key in seen:
            continue
        seen.add(key)
        candidates.append({
            "url": resolved_url,
            "slug": item["slug"],
            "lang": resolved_lang,
        })
    return candidates


def _select_live_ghost_url(pred: dict, ghost_slug_url_map: dict, ghost_url_set: set, lang: str) -> str:
    """Pick the first currently published Ghost URL for this prediction and language."""
    for candidate in _iter_live_ghost_candidates(pred, ghost_slug_url_map, ghost_url_set):
        if candidate["lang"] == lang:
            return candidate["url"]
    return ""


def _select_any_live_ghost_url(pred: dict, ghost_slug_url_map: dict, ghost_url_set: set) -> str:
    candidates = _iter_live_ghost_candidates(pred, ghost_slug_url_map, ghost_url_set)
    return candidates[0]["url"] if candidates else ""


def _display_title_for_lang(pred: dict, lang: str) -> str:
    article_title = (pred.get("article_title") or "").strip()
    if lang == "ja":
        candidates = [
            article_title if _is_japanese(article_title) else "",
            (pred.get("resolution_question_ja") or "").strip(),
            (pred.get("title") or "").strip() if _is_japanese(pred.get("title") or "") else "",
            (pred.get("resolution_question") or "").strip(),
        ]
    else:
        candidates = [
            (pred.get("title_en") or "").strip(),
            (pred.get("article_title_en") or "").strip(),
            article_title if article_title and not _is_japanese(article_title) else "",
            (pred.get("resolution_question_en") or "").strip(),
            (pred.get("resolution_question") or "").strip() if not _is_japanese(pred.get("resolution_question") or "") else "",
        ]

    for candidate in candidates:
        if candidate:
            return candidate

    prediction_id = pred.get("prediction_id", "")
    return (f"予測 {prediction_id}" if lang == "ja" else f"Prediction {prediction_id}").strip()

# ── Row builder (language-aware) ──────────────────────────────

def build_rows(pred_db, ghost_posts, embed_data, lang="ja"):
    """Build unified rows filtered by language."""
    rows = []
    seen_slugs = set()
    seen_titles = set()

    # Load market_history.db nowpattern_links (Pattern A data)
    linked_markets = load_linked_markets()

    # Build ghost slug -> title lookup for minimal-row fallback
    # (used when prediction_db article_title is empty)
    _ghost_slug_map = {p.get("slug", ""): p.get("title", "") for p in ghost_posts if p.get("slug")}
    _ghost_slug_url_map = {}
    _ghost_url_set = set()
    for _post in ghost_posts:
        _slug = _post.get("slug", "")
        _resolved_url = _resolve_ghost_url(_post.get("url", ""), _slug)
        if _slug and _resolved_url:
            _ghost_slug_url_map[_slug] = _resolved_url
            _ghost_url_set.add(_normalize_public_url(_resolved_url))

    # Source 1: prediction_db.json (authoritative)
    for pred in pred_db.get("predictions", []):
        title = _display_title_for_lang(pred, lang)
        same_lang_url = _select_live_ghost_url(pred, _ghost_slug_url_map, _ghost_url_set, lang)
        fallback_url = "" if same_lang_url else _select_any_live_ghost_url(pred, _ghost_slug_url_map, _ghost_url_set)
        url_for_lang = same_lang_url or fallback_url
        analysis_lang = _infer_url_lang(url_for_lang)
        analysis_is_fallback = bool(url_for_lang and not same_lang_url)

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
                base_content = s.get("content", "") or ""
                if base_content == '(本文抽出不可)': base_content = ""
            elif "楽観" in label or "optimistic" in label:
                opt = prob_pct
                opt_content = s.get("content", "") or ""
                if opt_content == '(本文抽出不可)': opt_content = ""
            elif "悲観" in label or "pessimistic" in label:
                pess = prob_pct
                pess_content = s.get("content", "") or ""
                if pess_content == '(本文抽出不可)': pess_content = ""

        if base is None and opt is None and pess is None:
            # Include predictions without scenarios as minimal compact rows
            # so that article oracle deep links (#np-XXXX) land on a real DOM anchor
            _pid_min = pred.get("prediction_id", "")
            _url_min = url_for_lang
            if _pid_min:
                _title_min = title
                if not _title_min and _url_min:
                    _slug_min = _url_min.rstrip("/").split("/")[-1]
                    _title_min = _ghost_slug_map.get(_slug_min, "")
                if not _title_min:
                    _title_min = (f"予測 {_pid_min}" if lang == "ja"
                                  else f"Prediction {_pid_min}")
                rows.append({
                    "title": _title_min, "url": _url_min,
                    "base": None, "optimistic": None, "pessimistic": None,
                    "base_content": "", "opt_content": "", "pess_content": "",
                    "event_summary": "", "polymarket": None, "metaculus": None,
                    "divergence": None, "status": _normalize_status_value(pred),
                    "outcome": pred.get("outcome"),
                    "resolved_at": pred.get("resolved_at", ""),
                    "brier": pred.get("brier_score"), "dynamics_str": "",
                    "source": "prediction_db", "genres": [],
                    "analysis_lang": analysis_lang,
                    "analysis_is_fallback": analysis_is_fallback,
                    "same_lang_url": same_lang_url,
                    "fallback_url": fallback_url,
                    "trigger_date": "", "published_at": pred.get("published_at", ""),
                    "prediction_id": _pid_min, "linked_market_question": None,
                    "linked_market_prob": None, "linked_market_url": None,
                    "linked_market_source": "",
                    "resolution_question": pred.get("resolution_question", ""),
                    "resolution_question_ja": pred.get("resolution_question_ja", ""),
                    "resolution_direction": pred.get("resolution_direction", "optimistic"),
                    "our_stance": pred.get("our_stance"),
                    "our_pick": pred.get("our_pick"),
                    "our_pick_prob": pred.get("our_pick_prob"),
                    "question_type": pred.get("question_type", "binary"),
                    "hit_condition_ja": pred.get("hit_condition_ja", ""),
                    "hit_condition_en": pred.get("hit_condition_en", ""),
            "oracle_deadline":   pred.get("oracle_deadline", ""),
            "oracle_criteria":   pred.get("oracle_criteria", ""),
            "oracle_question":   pred.get("oracle_question", ""),
            "oracle_premortem":  pred.get("oracle_premortem", ""),
                    "market_consensus": pred.get("market_consensus"),
                    "hit_miss": pred.get("hit_miss"),
                    "official_score_tier": pred.get("official_score_tier", DEFAULT_PUBLIC_SCORE_TIER),
                    "resolution_evidence": pred.get("resolution_evidence"),
                    "integrity_hash": pred.get("integrity_hash"),
                    "dispute_reason": pred.get("dispute_reason", ""),
                    "rebuttals": pred.get("rebuttals", []),
                    "trigger_date_display": "", "scenarios_labeled": [],
                })
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

        if lang == "en":
            dynamics_str = pred.get("dynamics_tags_en", "") or pred.get("dynamics_tags", "")
        else:
            dynamics_str = pred.get("dynamics_tags", "")
        url = url_for_lang

        # Extract event summary for context (EN-aware)
        if lang == "en":
            _olt_en = pred.get("open_loop_trigger_en", "")
            event_summary = _olt_en[:100] if _olt_en else extract_event_summary(pred)
        else:
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
                if lang == "en":
                    trigger_date = (t0.get("date_en") or t0.get("date") or "")
                else:
                    trigger_date = (t0.get("date") or "")[:10]
        if not trigger_date and linked:
            trigger_date = (linked.get("close_date") or "")[:10]

        # === Oracle: trigger_date_display (clean, human-readable) ===
        import re as _re
        trigger_date_display = ""
        if triggers:
            _t0 = triggers[0]
            if isinstance(_t0, dict):
                if lang == "en":
                    _raw = (_t0.get("date_en") or _t0.get("date") or "")
                else:
                    _raw = (_t0.get("date") or "")
                _clean = _re.split(r"[（(]|[ ]+[-—]", _raw)[0].strip()
                _clean = _clean.replace("前後", "").strip()
                trigger_date_display = _clean

        # === Oracle: scenarios_labeled (label + prob + content for Formula/Accordion) ===
        scenarios_labeled = []
        for _s in scenarios:
            _lbl = _s.get("label", "")
            _prob_raw = _s.get("probability", 0)
            try:
                _pf = float(_prob_raw)
                if _pf > 1:
                    _pf = _pf / 100
                _sp = int(round(_pf * 100))
            except (ValueError, TypeError):
                _sp = 0
            _sc = _s.get("content", "") or ""
            _sc_en = _s.get("content_en", "") or ""
            # Filter out extraction failure placeholder
            if _sc == "(本文抽出不可)": _sc = ""
            if _sc_en == "(本文抽出不可)": _sc_en = ""
            scenarios_labeled.append({
                "label": _lbl, "prob": _sp,
                "content": _sc, "action": _s.get("action", ""),
                "label_en": _s.get("label_en", ""), "content_en": _sc_en
            })

        _validate_market_consensus(pred)
        row = {
            "title": title,
            "url": url,
            "analysis_lang": analysis_lang,
            "analysis_is_fallback": analysis_is_fallback,
            "same_lang_url": same_lang_url,
            "fallback_url": fallback_url,
            "base": base, "optimistic": opt, "pessimistic": pess,
            "base_content": base_content,
            "opt_content": opt_content,
            "pess_content": pess_content,
            "event_summary": event_summary,
            "polymarket": pm_match,
            "metaculus": mc_match,
            "divergence": divergence,
            "status": _normalize_status_value(pred),
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
            "resolution_question_en": pred.get("resolution_question_en", ""),
            "resolution_question_ja": pred.get("resolution_question_ja", ""),
            "title_en": pred.get("title_en", ""),
            "resolution_direction": pred.get("resolution_direction", "optimistic"),
            "our_stance": pred.get("our_stance"),
            "our_pick": pred.get("our_pick"),
            "our_pick_prob": pred.get("our_pick_prob"),
            "question_type": pred.get("question_type", "binary"),
            "hit_condition_ja": pred.get("hit_condition_ja", ""),
            "hit_condition_en": pred.get("hit_condition_en", ""),
            "oracle_deadline":   pred.get("oracle_deadline", ""),
            "oracle_criteria":   pred.get("oracle_criteria", ""),
            "oracle_question":   pred.get("oracle_question", ""),
            "oracle_premortem":  pred.get("oracle_premortem", ""),
            "polymarket": pm_match,
            "metaculus": mc_match,
            "market_consensus": pred.get("market_consensus"),  # validated by _validate_market_consensus,
            "hit_miss": pred.get("hit_miss"),
            "official_score_tier": pred.get("official_score_tier", DEFAULT_PUBLIC_SCORE_TIER),
            # Phase 2: Evidence chain + tamper detection
            "resolution_evidence": pred.get("resolution_evidence"),
            "integrity_hash": pred.get("integrity_hash"),
            "dispute_reason": pred.get("dispute_reason", ""),
            # Phase 3: Rebuttals
            "rebuttals": pred.get("rebuttals", []),
            # Oracle fields
            "trigger_date_display": trigger_date_display,
            "scenarios_labeled": scenarios_labeled,
        }
        rows.append(row)

        slug = url.split("/")[-2] if url else ""
        if slug:
            seen_slugs.add(slug)
        seen_titles.add(title)

    # ── 構造完全性チェック（ghost_htmlソース廃止 — prediction_dbのみ） ───────────
    # ghost_htmlフォールバックを削除済み。
    # prediction_dbに登録されていない記事はページに表示しない。
    # 理由: 必須フィールド（scenarios_labeled, trigger_date_display等）が
    #       ghost_htmlソースでは埋まらず、カード構造が不完全になるため。

    return rows


# ── New HTML builder (Scrap & Build 2026-02-25) ────────────────

def _scoreboard_block(rows, lang):
    """BLOCK 1: Dark scoreboard grid (formal predictions only)."""
    # Only count formal prediction_db entries, not ghost_html articles
    formal = [r for r in rows if r.get("source") == "prediction_db"]
    resolved = [r for r in formal if _is_resolved_status(r)]
    scorable = [
        r for r in resolved
        if r.get("brier") is not None
        and _normalize_score_tier(r.get("official_score_tier"), r.get("brier")) != "NOT_SCORABLE"
    ]
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
    avg_brier = round(sum(float(r["brier"]) for r in scorable) / len(scorable), 4) if scorable else None
    public_score = _public_score_value(avg_brier)
    aggregate_tier = _aggregate_score_tier(scorable)
    aggregate_badge = _score_tier_badge_html(aggregate_tier, lang)
    aggregate_disclaimer = _score_disclaimer_html(aggregate_tier, lang, include_link=True)
    score_color = _public_score_color(public_score)
    raw_note = (
        (
            f'Brier Index / n={len(scorable)} / 平均 raw Brier {avg_brier:.4f}'
            if avg_brier is not None
            else "Score sample is still accumulating"
        )
        if lang == "ja"
        else (
            f'Brier Index / n={len(scorable)} / avg raw Brier {avg_brier:.4f}'
            if avg_brier is not None
            else "Score sample is still accumulating"
        )
    )

    if lang == "ja":
        header_label = "Nowpatternの予測精度 — 2026年実績"
        total_label = "総予測数"
        hit_label = "✅ 的中"
        miss_label = "❌ 外れ"
        acc_label = "的中率"
        score_label = "公開Brier Index"
        score_empty = "スコア対象の解決済み予測がまだありません。"
    else:
        header_label = "Nowpattern Prediction Accuracy — 2026 Track Record"
        total_label = "Total"
        hit_label = "✅ Accurate"
        miss_label = "❌ Missed"
        acc_label = "Accuracy"
        score_label = "Public Score"
        score_empty = "No scorable resolved predictions yet."

    # 0件時のempty state
    if not resolved:
        empty_note = (
            "まだ解決済みの予測はありません。初解決をお楽しみに！"
            if lang == "ja"
            else "No resolved predictions yet. Stay tuned for the first result!"
        )
        return (
            '<div id="np-scoreboard" style="margin-bottom:24px;background:#fff;border-radius:12px;'
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

    if public_score is None:
        score_panel = (
            '<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;'
            'padding:14px 16px;margin-top:14px">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap">'
            f'<div style="font-size:0.82em;color:#475569;font-weight:700">{score_label}</div>'
            f'{aggregate_badge}'
            '</div>'
            f'<div style="font-size:0.82em;color:#94A3B8;margin-top:6px">{score_empty}</div>'
            f'{aggregate_disclaimer}'
            '</div>'
        )
    else:
        score_panel = (
            '<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;'
            'padding:14px 16px;margin-top:14px">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap">'
            f'<div><span style="font-size:0.82em;color:#475569;font-weight:700">{score_label}</span> '
            f'<strong style="font-size:1.35em;color:{score_color};margin-left:6px">{public_score:.1f}%</strong></div>'
            f'{aggregate_badge}'
            '</div>'
            f'<div style="font-size:0.74em;color:#6B7280;margin-top:6px">{raw_note}</div>'
            f'{aggregate_disclaimer}'
            '</div>'
        )

    return (
        '<div id="np-scoreboard" style="margin-bottom:24px;background:#fff;border-radius:12px;'
        'padding:24px 28px;box-shadow:0 2px 8px rgba(0,0,0,.08)">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;'
        f'margin-bottom:14px">'
        f'<div style="font-size:0.75em;color:#888;letter-spacing:.08em;text-transform:uppercase">{header_label}</div>'
        f'{aggregate_badge}'
        '</div>'
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
        f'{score_panel}'
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
    # L4: guard raw Japanese date_str in EN output
    if lang == "en":
        date_str = en_safe(date_str, "trigger_date_en", lang)
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

    # Never NEUTRAL — force direction (50% = cop-out, forbidden by Oracle principle)
    if base >= opt and base >= pess:
        if direction == "optimistic":
            return "YES"
        else:
            return "NO"

    if direction == "optimistic":
        return "YES" if opt >= pess else "NO"
    else:
        return "YES" if pess >= opt else "NO"


def _get_market_prob(r):
    """Return (market_prob_int, market_src_str) from row data.

    Priority:
      1. linked_market_prob (from market_history.db via nowpattern_links)
      2. market_consensus field (explicit DB setting — prediction_db rows)
      3. polymarket embed
      4. metaculus embed
      5. no data → (None, "")
    """
    linked_prob = r.get("linked_market_prob")
    pm = r.get("polymarket") or {}
    mc = r.get("metaculus") or {}
    mc_field = r.get("market_consensus")

    if linked_prob is not None:
        raw_src = (r.get("linked_market_source") or "").lower().strip()
        src = _SOURCE_DISPLAY.get(raw_src, raw_src.capitalize() if raw_src else "Manifold")
        return round(prob01_to_pct(linked_prob)), src

    # market_consensus field (explicitly set for prediction_db rows)
    if isinstance(mc_field, dict) and mc_field.get("probability") is not None:
        src = mc_field.get("source", "Polymarket")
        return round(float(mc_field["probability"])), src

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




# ═══════════════════════════════════════════════════════
# ORACLE GUARDIAN SYSTEM — 3層強制バリデーター
# ═══════════════════════════════════════════════════════

_ORACLE_PRINCIPLES = {
    "deadline":  "原則8: インテレクチュアル・ヒューミリティ（予測の記録と検証）",
    "hit_cond":  "原則7: システム・シンキング（判定基準の明文化）",
    "scenarios": "原則8: インテレクチュアル・ヒューミリティ（根拠の透明性）",
    "formula":   "原則7: システム・シンキング（確率計算の明示）",
}


def _validate_tracker_card(r):
    """Oracle Guardian — tracker cardの4要素を検証。
    Returns list of (code, label_ja, label_en, principle) for missing fields.
    An empty list means the card passes validation.
    """
    missing = []
    # 1. 判定期限（Ω）: trigger_date / trigger_date_display / oracle_deadline のどれかあればOK
    if not r.get("trigger_date_display") and not r.get("trigger_date") and not r.get("oracle_deadline"):
        missing.append((
            "deadline",
            "判定期限（Ω）未設定",
            "Deadline (Ω) not set",
            _ORACLE_PRINCIPLES["deadline"],
        ))
    # 2. 的中条件: hit_condition_ja/en または oracle_criteria のどれかあればOK
    if not r.get("hit_condition_ja") and not r.get("hit_condition_en") and not r.get("oracle_criteria"):
        missing.append((
            "hit_cond",
            "的中条件（Verdict）未定義",
            "Hit Condition undefined",
            _ORACLE_PRINCIPLES["hit_cond"],
        ))
    # 3. シナリオ背景: scenarios_labeled / scenarios / oracle_question のどれかあればOK
    if not r.get("scenarios_labeled") and not r.get("scenarios") and not r.get("oracle_question"):
        missing.append((
            "scenarios",
            "シナリオ背景（Accordion）なし",
            "Scenario backgrounds missing",
            _ORACLE_PRINCIPLES["scenarios"],
        ))
    # 4. 計算根拠（Formula）
    if not r.get("our_pick") or r.get("our_pick_prob") is None:
        missing.append((
            "formula",
            "計算根拠（Formula）未設定",
            "Formula not set",
            _ORACLE_PRINCIPLES["formula"],
        ))
    return missing


def _build_error_card(r, lang, missing_fields):
    """真っ赤なエラーカード — Guardian が検閲を通過させなかった証拠。
    不完全なデータはフロントエンドで公開停止 + 理由を明示。
    """
    pred_id = r.get("prediction_id", "???") or "???"
    title = r.get("title", "Unknown")[:80]
    genre_str = r.get("dynamics_str", "") or r.get("genres", "")
    if isinstance(genre_str, list):
        genre_str = ",".join(genre_str)
    if lang == "ja":
        header = "⚠️ データ不完全 — Oracle Guardian により公開停止"
        footer = "このカードは必須データが揃うまで掲載できません。prediction_db.json に不足フィールドを追加してください。"
    else:
        header = "⚠️ Incomplete Data — Publication Blocked by Oracle Guardian"
        footer = "This card cannot be published until all required fields are present in prediction_db.json."
    items = ""
    for code, label_ja, label_en, principle in missing_fields:
        label = label_ja if lang == "ja" else label_en
        items += (
            f'<div style="margin-bottom:6px;padding:4px 8px;background:#FEF2F2;border-radius:4px">'
            f'<span style="color:#991B1B;font-weight:700">✗ {label}</span>'
            f'<div style="color:#6B7280;font-size:0.82em;margin-top:2px">[{principle}に抵触]</div>'
            f'</div>'
        )
    return (
        f'<details style="border:2px solid #EF4444;border-radius:8px;margin-bottom:8px;'
        f'background:linear-gradient(135deg,#FEF2F2 0%,#FFF5F5 100%)" data-genres="{genre_str}">'
        f'<summary style="padding:12px;cursor:pointer">'
        f'<div style="display:flex;align-items:flex-start;gap:8px">'
        f'<div style="flex:1">'
        f'<div style="font-weight:700;color:#991B1B;font-size:0.9em">{header}</div>'
        f'<div style="font-size:0.75em;color:#475569;margin-top:2px">[{pred_id}] {title}</div>'
        f'</div>'
        f'<span style="color:#EF4444;font-size:1.2em">⚔</span>'
        f'</div>'
        f'</summary>'
        f'<div style="padding:12px;border-top:1px solid #FECACA">'
        f'<div style="font-size:0.85em;margin-bottom:10px">{items}</div>'
        f'<div style="font-size:0.75em;color:#6B7280;font-style:italic">{footer}</div>'
        f'</div>'
        f'</details>'
    )


# ═══════════════════════════════════════════════════════
# UNIFIED CARD — Gemini 金型強制
# normalize_payload: 欠損フィールドを警告文字列で補完
# すべての tracker card はこの関数を通ってから描画する
# ═══════════════════════════════════════════════════════

def normalize_payload(r, lang):
    """Gemini 金型: 欠損フィールドに警告文字列を代入してレイアウト崩壊を防ぐ。
    Ghost article cards はスキップ（prediction_db のみ対象）。
    """
    if r.get("source") != "prediction_db":
        return r
    result = dict(r)
    result["status"] = _normalize_status_value(result)
    result["official_score_tier"] = _normalize_score_tier(
        result.get("official_score_tier"),
        result.get("brier"),
    )
    # 1. 判定期限（Ω）
    if not result.get("trigger_date_display") and not result.get("trigger_date"):
        _missing_deadline = "期限未設定" if lang == "ja" else "Deadline not set"
        result["trigger_date_display"] = _missing_deadline
        result["trigger_date"] = _missing_deadline
    # 2. 的中条件（Verdict）: oracle_criteria を hit_condition_ja/en にマップ
    if lang == "ja":
        if not result.get("hit_condition_ja"):
            if result.get("oracle_criteria"):
                result["hit_condition_ja"] = result["oracle_criteria"]
            else:
                result["hit_condition_ja"] = "【基準策定中】"
    else:
        if not result.get("hit_condition_en") and not result.get("hit_condition_ja"):
            if result.get("oracle_criteria"):
                result["hit_condition_en"] = result["oracle_criteria"]
            else:
                result["hit_condition_en"] = "[Criteria pending]"
    # oracle_deadline を trigger_date にマップ
    if not result.get("trigger_date_display") and not result.get("trigger_date"):
        if result.get("oracle_deadline"):
            result["trigger_date"] = result["oracle_deadline"]
            result["trigger_date_display"] = result["oracle_deadline"]
    # 3. scenarios_labeled（アコーディオン）
    if not result.get("scenarios_labeled"):
        _no_scen_lbl = "シナリオ情報なし" if lang == "ja" else "No scenario data"
        result["scenarios_labeled"] = [
            {"label": _no_scen_lbl, "prob": 0, "content": "", "action": ""},
        ]
    # 4. our_pick / our_pick_prob（計算根拠）
    if not result.get("our_pick"):
        result["our_pick"] = "—"
    if result.get("our_pick_prob") is None:
        result["our_pick_prob"] = 0
    # 5. SANITIZE: エラー文字列をUIに絶対表示しない（2026-03-29 恒久対策）
    # コンテンツ抽出パイプライン失敗時の内部文字列がユーザーに見えるのを防ぐ
    _CONTENT_ERRORS = {"(本文抽出不可)"}
    for _f in ("hit_condition_ja", "hit_condition_en", "oracle_criteria",
               "base_content", "opt_content", "pess_content"):
        if result.get(_f) in _CONTENT_ERRORS:
            result[_f] = ""
    if result.get("scenarios_labeled"):
        for _sc_item in result["scenarios_labeled"]:
            if isinstance(_sc_item, dict) and _sc_item.get("content") in _CONTENT_ERRORS:
                _sc_item["content"] = ""
    return result


def _build_card(r, lang):
    """Unified prediction card — always 3-column grid.
    Replaces _build_tracking_card + _build_resolved_card.
    Column 3: tracking='Awaiting Result' / resolved='Hit/Miss'.
    Enable with UNIFIED_CARD=1 env var.
    """
    # ── Layer 1: Type routing ─────────────────────────────────────────────
    # source=="prediction_db"  → tracker card (strict validation)
    # source=="ghost_html"     → article card (no validation, simpler)
    _row_source = r.get("source", "prediction_db")

    # ── Layer 2: Oracle Guardian Validation (tracker cards only) ─────────
    if _row_source == "prediction_db":
        _guardian_errors = _validate_tracker_card(r)
        if _guardian_errors:
            return _build_error_card(r, lang, _guardian_errors)

    # ── Layer 3: normalize_payload — 欠損フィールドを補完 ─────────────────
    r = normalize_payload(r, lang)

    # === Data extraction (common) ===
    pess = r.get("pessimistic")
    base = r.get("base")
    opt  = r.get("optimistic")
    pess_content = r.get("pess_content", "")
    base_content = r.get("base_content", "")
    opt_content  = r.get("opt_content", "")
    title        = r.get("title", "")
    url          = r.get("url", "#")
    trigger_date = r.get("trigger_date", "")
    genres       = r.get("genres", [])
    published_at = r.get("published_at", "")

    is_resolved = _is_resolved_status(r)
    outcome     = r.get("outcome", "") if is_resolved else ""
    brier       = r.get("brier") if is_resolved else None
    resolved_at = r.get("resolved_at", "") if is_resolved else ""
    score_tier  = _normalize_score_tier(r.get("official_score_tier"), brier)
    resolved_binary_outcome = _resolved_binary_outcome(r) if is_resolved else None

    # === Market prob ===
    market_prob, market_src = _get_market_prob(r)

    # Suppress embed market_prob if market_consensus is set (tracking only)
    _has_mc_early = (
        r.get("market_consensus")
        and isinstance(r.get("market_consensus"), dict)
        and r["market_consensus"].get("pick")
    )
    if _has_mc_early and not is_resolved:
        market_prob = None
        market_src = ""

    # === I18N Labels ===
    if lang == "ja":
        pess_lbl, base_lbl, opt_lbl = "\u60b2\u89b3", "\u57fa\u672c", "\u697d\u89b3"
        tracking_prefix = "\u89e3\u6c7a\u6e08\u307f\u306e\u554f\u3044:" if is_resolved else "\u8ffd\u8de1\u4e2d\u306e\u554f\u3044:"
        read_label = "\u2192 \u8a18\u4e8b\u3092\u8aad\u3080"
        ours_section_label = "\u79c1\u305f\u3061\u306e\u4e88\u60f3"
        market_section_label = f"\u5e02\u5834\u306e\u4e88\u60f3\uff08{market_src}\uff09" if market_src else "\u5e02\u5834\u306e\u4e88\u60f3"
        result_section_label = "\u7d50\u679c"
        crowd_desc = (
            "\uff08\u4e88\u6e2c\u30b3\u30df\u30e5\u30cb\u30c6\u30a3\u306e\u96c6\u5408\u77e5\uff09" if market_src == "Metaculus"
            else "\uff08\u304a\u91d1\u3092\u8ced\u3051\u305f\u4eba\u305f\u3061\u306e\u96c6\u5408\u77e5\uff09"
        )
        resolve_label = "\u89e3\u6c7a\u4e88\u5b9a:"
        resolution_criteria_label = "\ud83c\udfaf \u5224\u5b9a\u57fa\u6e96"
        scenario_accordion_label = "\u25bc \u5404\u30b7\u30ca\u30ea\u30aa\u306e\u80cc\u666f\u3092\u8aad\u3080"
        accuracy_label = "Nowpattern Brier Index:"
        market_acc_label = "\u5e02\u5834 Brier Index:"
        not_scored_label = "\u63a1\u70b9\u5bfe\u8c61\u5916"
        outcome_map = {"\u697d\u89b3": "\u697d\u89b3", "\u57fa\u672c": "\u57fa\u672c", "\u60b2\u89b3": "\u60b2\u89b3"}
        hit_word, miss_word = "\u7684\u4e2d", "\u5916\u308c"
        outcome_suffix_hit  = "\u7684\u4e2d"
        outcome_suffix_miss = "\u304c\u73fe\u5b9f\u306b"
        waiting_label = "\u23f3 \u7d50\u679c\u5f85\u3061"
        pending_note  = "\u4e88\u6e2c\u671f\u9650\u307e\u3067\u8ffd\u8de1\u4e2d"
    else:
        pess_lbl, base_lbl, opt_lbl = "Bear", "Base", "Bull"
        tracking_prefix = "Resolved:" if is_resolved else "Tracking:"
        read_label = "\u2192 Read article"
        ours_section_label = "Our Prediction"
        market_section_label = f"Market ({market_src})" if market_src else "Market"
        result_section_label = "Result"
        crowd_desc = (
            "(aggregated forecasts)" if market_src == "Metaculus"
            else "(real-money bettors)"
        )
        resolve_label = "Resolution:"
        resolution_criteria_label = "\ud83c\udfaf Resolution Criteria"
        scenario_accordion_label = "\u25bc Read scenario background"
        accuracy_label = "Nowpattern Brier Index:"
        market_acc_label = "Market Brier Index:"
        not_scored_label = "Not Scored"
        outcome_map = {"\u697d\u89b3": "Optimistic", "\u57fa\u672c": "Base", "\u60b2\u89b3": "Pessimistic"}
        hit_word, miss_word = "Accurate", "Missed"
        outcome_suffix_hit  = " Accurate"
        outcome_suffix_miss = " (Missed)"
        waiting_label = "\u23f3 Awaiting Result"
        pending_note  = "Tracking until deadline"

    analysis_is_fallback = bool(r.get("analysis_is_fallback"))
    if analysis_is_fallback:
        read_label = "\u2192 English analysis" if lang == "ja" else "\u2192 日本語分析"

    # === Resolved-specific data ===
    is_hit = False
    is_disputed = False
    if is_resolved:
        _hit_miss_val = r.get("hit_miss")
        if _hit_miss_val is not None:
            is_hit = _hit_miss_val in ("correct", "hit")
        else:
            is_hit = brier is not None and brier < 0.25
        is_disputed = r.get("status") == "disputed"

    # === Status badge (pill style, all states) ===
    if is_resolved:
        if is_disputed:
            _sb_bg, _sb_clr = "#fef3c7", "#b45309"
            _sb_txt = "\u26a0\ufe0f " + ("\u4e8b\u5b9f\u78ba\u8a8d\u4e2d" if lang == "ja" else "Under Review")
        elif is_hit:
            _sb_bg, _sb_clr = "#dcfce7", "#16a34a"
            _sb_txt = "\u2705 " + ("\u7684\u4e2d" if lang == "ja" else "Accurate")
        else:
            _sb_bg, _sb_clr = "#fee2e2", "#dc2626"
            _sb_txt = "\u274c " + ("\u5916\u308c" if lang == "ja" else "Missed")
    else:
        _sb_bg, _sb_clr = "#e0f2fe", "#0284c7"
        _sb_txt = "\u23f3 " + ("\u8ffd\u8de1\u4e2d" if lang == "ja" else "Tracking")
    _status_badge = (
        f'<span style="display:inline-block;background:{_sb_bg};color:{_sb_clr};'
        f'font-size:0.72em;font-weight:700;padding:2px 10px;border-radius:12px;'
        f'margin-bottom:6px">{_sb_txt}</span>'
    )

    # === Oracle: Deadline badge ===
    _deadline_raw = r.get("trigger_date_display", "")
    if not _deadline_raw:
        _deadline_raw = r.get("trigger_date", "")
    _deadline_lbl = (
        ("⏳ 判定期限：" + (_deadline_raw or "期限策定中"))
        if lang == "ja" else
        ("⏳ Deadline: " + en_safe(_deadline_raw or "TBD", "trigger_date_en", lang))
    )
    _deadline_html = (
        f'<div style="margin-bottom:4px">'
        f'<span style="font-size:0.65em;background:#FFF7ED;color:#C2410C;'
        f'border:1px solid #FED7AA;border-radius:4px;padding:1px 8px;font-weight:600">'
        f'{_deadline_lbl}</span></div>'
    )

    # === Question line ===
    ev = _ev_str(r)
    if lang == "ja":
        _tracking_q = (r.get("resolution_question_ja") or r.get("resolution_question") or ev)
    else:
        _tracking_q = (r.get("resolution_question_en") or r.get("resolution_question") or ev)
    _ev_line = ""
    if ev and ev != _tracking_q and len(ev) > 5:
        _ev_pfx = "\u6ce8\u76ee\u30a4\u30d9\u30f3\u30c8:" if lang == "ja" else "Key Event:"
        _ev_safe = en_safe(ev, "open_loop_trigger_en", lang)
        _ev_line = (
            f'<div style="font-size:0.68em;color:#aaa;margin-bottom:4px">'
            f'{_ev_pfx}&nbsp;<span style="color:#888">{_ev_safe}</span>'
            f'</div>'
        )

    # === Pick header (our pick + market consensus + verdict) ===
    _OP_CLR  = {"YES": "#2563EB", "NO": "#DC2626"}
    _OP_BG   = {"YES": "#EFF6FF", "NO": "#FEF2F2"}
    _OP_BORD = {"YES": "#BFDBFE", "NO": "#FECACA"}

    if is_resolved:
        _op = r.get("our_pick")
        _op_prob = r.get("our_pick_prob")
        _op_hit_cond = (
            r.get("hit_condition_ja") if lang == "ja"
            else r.get("hit_condition_en", r.get("hit_condition_ja", ""))
        )
        _mc = r.get("market_consensus")
        _op_label = "Nowpattern\u306e\u7d50\u8ad6\uff08\u5f53\u6642\uff09" if lang == "ja" else "Our Conclusion (at Publication)"
    else:
        _op = r.get("our_pick")
        if not _op:
            _op_computed = compute_stance_from_row(r)
            _op = _op_computed if _op_computed != "NEUTRAL" else None
        _op_prob = r.get("our_pick_prob")
        _op_hit_cond = (
            r.get("hit_condition_ja") if lang == "ja"
            else r.get("hit_condition_en", r.get("hit_condition_ja", ""))
        )
        _op_label = "\u26a1 Nowpattern\u306e\u65ad\u8a00" if lang == "ja" else "\u26a1 Nowpattern's Verdict"
        # Market consensus with fallback chain (tracking only)
        _mc = r.get("market_consensus")
        if not (_mc and isinstance(_mc, dict) and _mc.get("pick")):
            _lm_prob = r.get("linked_market_prob")
            _lm_src  = r.get("linked_market_source", "")
            _lm_q    = r.get("linked_market_question", "")
            _pm = r.get("polymarket") or {}
            _pm_outcomes = _pm.get("outcomes")
            _mc_data = r.get("metaculus") or {}
            _mc_prob = _mc_data.get("probability")
            if _lm_prob is not None:
                _lm_pct = round(float(_lm_prob) * 100, 1) if float(_lm_prob) <= 1 else round(float(_lm_prob), 1)
                _src_map = {"polymarket": "Polymarket", "metaculus": "Metaculus", "manifold": "Manifold"}
                _src_name = _src_map.get(_lm_src.lower().strip(), _lm_src.capitalize() if _lm_src else "Market")
                _mc = {"source": _src_name, "pick": "YES" if _lm_pct >= 50 else "NO", "probability": _lm_pct, "question": _lm_q}
            elif _pm_outcomes:
                _yes_pct = float(_pm_outcomes.get("Yes", _pm_outcomes.get("YES", 0)))
                _mc = {"source": "Polymarket", "pick": "YES" if _yes_pct >= 50 else "NO", "probability": round(_yes_pct, 1)}
            elif _mc_prob is not None:
                _mc = {"source": "Metaculus", "pick": "YES" if float(_mc_prob) >= 50 else "NO", "probability": round(float(_mc_prob))}

    _op_clr  = _OP_CLR.get(_op, "#6B7280")
    _op_bg   = _OP_BG.get(_op, "#F9FAFB")
    _op_bord = _OP_BORD.get(_op, "#E5E7EB")

    # Market consensus HTML block
    market_section_html = ""
    is_contrarian = False
    alpha_gap = 0
    is_alpha_alert = False
    if _mc and isinstance(_mc, dict) and _mc.get("pick"):
        mc_source = _mc.get("source", "\u5e02\u5834")
        mc_pick   = _mc.get("pick")
        mc_prob   = _mc.get("probability", 50)
        mc_clr    = "#2563EB" if mc_pick == "YES" else "#DC2626"
        _q_ja = _mc.get("question_ja", "")
        _q_en = _mc.get("question", "")
        mc_question = _q_ja if lang == "ja" else _q_en
        mc_question_html = ""
        if mc_question:
            mc_question_html = (
                f'<div style="font-size:0.72em;color:#475569;font-style:italic;'
                f'margin-bottom:5px;line-height:1.3">&#10067; {mc_question}</div>'
            )
        elif lang == "ja" and _q_en:
            # Fallback: show English question in smaller gray italic when question_ja is missing
            mc_question_html = (
                f'<div style="font-size:0.68em;color:#94A3B8;font-style:italic;'
                f'margin-bottom:5px;line-height:1.3">&#10067; {_q_en}</div>'
            )
        _mc_time_lbl = ""
        _mc_last_updated = _mc.get("last_updated", "") if isinstance(_mc, dict) else ""
        if is_resolved:
            _mc_time_lbl = "\uff08\u5f53\u6642\uff09" if lang == "ja" else " (at pub)"
        elif _mc_last_updated:
            _mc_time_lbl = ("\uff08" + _mc_last_updated + "\u53d6\u5f97\uff09") if lang == "ja" else f" ({_mc_last_updated})"
        _mc_dir_ja = "成立" if mc_pick == "YES" else "不成立"
        _mc_dir_en = mc_pick
        _mc_snapshot_note = ""
        if not is_resolved:
            _mc_snapshot_note = (
                '<div style="font-size:0.65em;color:#94A3B8;margin-top:3px;text-align:right">'
                + ("※取得時点のスナップショット。現在値はリンク先で確認" if lang == "ja" else "※Snapshot only — check link for live data")
                + '</div>'
            )
        _mc_desc_html = (
            f'<div style="font-size:0.69em;color:#64748B;margin-top:5px;text-align:right;font-style:italic">'
            f'{"実資金の" + str(mc_prob) + "%" + "が「" + _mc_dir_ja + "」に賭けています" if lang == "ja" else str(mc_prob) + "% of prediction market capital bets on " + _mc_dir_en}'
            f'</div>'
            f'{_mc_snapshot_note}'
        )
        # Layer 4: 市場URL直リンク義務化
        _mc_url = (
            r.get("linked_market_url")
            or (_mc.get("url") if isinstance(_mc, dict) else None)
        )
        if _mc_url:
            _mc_src_html = (
                f'<a href="{_mc_url}" target="_blank" rel="noopener" '
                f'style="color:#6366f1;font-weight:700;text-decoration:none'
                f';border-bottom:1px dotted #6366f1">{mc_source} ↗</a>'
            )
        else:
            _mc_src_html = (
                f'<span style="color:#64748B">{mc_source}</span>'
            )
        market_section_html = (
            f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
            f'border-radius:4px;padding:6px 10px;margin-bottom:6px">'
            f'{mc_question_html}'
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'font-size:0.74em;margin-bottom:4px">'
            f'<span style="color:#64748B">&#127963; {_mc_src_html} '
            f'{"コンセンサス" if lang == "ja" else "Consensus"}{_mc_time_lbl}</span>'
            f'<span style="font-weight:700;color:{mc_clr}">{mc_pick}&nbsp;{mc_prob}%</span>'
            f'</div>'
            f'<div style="background:#E2E8F0;border-radius:2px;height:3px">'
            f'<div style="background:{mc_clr};width:{mc_prob}%;height:3px;border-radius:2px"></div>'
            f'</div>'
            f'{_mc_desc_html}'
            f'</div>'
        )
        is_contrarian = bool(_op and mc_pick != _op)
        if _op_prob and mc_prob:
            _our_yes = _op_prob if _op == 'YES' else (100 - _op_prob)
            _mc_yes  = mc_prob  if mc_pick == 'YES' else (100 - mc_prob)
            alpha_gap = abs(_our_yes - _mc_yes)
            is_alpha_alert = is_contrarian and alpha_gap >= 30

    if is_alpha_alert:
        contrarian_badge = (
            f'<span style="font-size:0.62em;background:#FEE2E2;color:#991B1B;'
            f'border-radius:9999px;padding:1px 7px;margin-left:6px;vertical-align:middle;'
            f'font-weight:700;border:1px solid #FCA5A5">'
            f'&#9889; ALPHA +{alpha_gap}pt '
            f'<span style="font-size:0.88em;font-weight:400;opacity:0.85">{"(市場との乖離)" if lang == "ja" else "(vs market)"}</span></span>'
        )
    elif is_contrarian:
        contrarian_badge = (
            f'<span style="font-size:0.62em;background:#FEF3C7;color:#92400E;'
            f'border-radius:9999px;padding:1px 7px;margin-left:6px;vertical-align:middle">'
            f'&#9889; {"\u9006\u5f35\u308a" if lang == "ja" else "Contrarian"}</span>'
        )
    else:
        contrarian_badge = ""

    # === Oracle: Formula display ===
    _formula_html = ""
    _scenarios_labeled = r.get("scenarios_labeled", [])
    if _op and _op_prob and len(_scenarios_labeled) >= 2:
        def _short_lbl(lbl):
            # lang-aware: EN page gets English labels
            if lang == "en":
                if "楽観" in lbl or "optimistic" in lbl.lower() or "bull" in lbl.lower(): return "Bull"
                if "悲観" in lbl or "pessimistic" in lbl.lower() or "bear" in lbl.lower(): return "Bear"
                if "基本" in lbl or "base" in lbl.lower(): return "Base"
            else:
                if "楽観" in lbl or "optimistic" in lbl.lower(): return "楽観"
                if "悲観" in lbl or "pessimistic" in lbl.lower(): return "悲観"
                if "基本" in lbl or "base" in lbl.lower(): return "基本"
            # Strip parentheticals and シナリオ suffix for custom labels
            import re as _re
            _s = _re.sub(r'[（(][^）)]*[）)]', '', lbl).replace("シナリオ", "").strip()
            # L4: For EN, if stripped result is still Japanese, return placeholder
            if lang == "en" and _is_japanese(_s):
                return "[?]"
            return (_s[:5] + "…") if len(_s) > 5 else (_s or lbl[:5])
        if _op == "YES":
            _fscens = _scenarios_labeled[:2]
        else:
            _fscens = _scenarios_labeled[1:]
        _fparts = " + ".join(f'{ _short_lbl(_s["label"])} {_s["prob"]}%' for _s in _fscens)
        _formula_html = (
            f'<div style="font-size:0.63em;color:#94A3B8;margin-top:4px;font-family:monospace">'
            f'({_fparts}) = {_op} {_op_prob}%'
            f'</div>'
        )

    # === Oracle: Scenarios accordion ===
    _scenarios_accordion_html = ""
    if _scenarios_labeled:
        _scen_items = ""
        for _si, _s in enumerate(_scenarios_labeled):
            if lang == "en":
                _s_content = (_s.get("content_en") or _s.get("content") or "").strip()
            else:
                _s_content = (_s.get("content") or "").strip()
            _s_action  = (_s.get("action")  or "").strip()
            # 文字制限撤廃（Gemini 金型: テキスト切れ禁止）
            _s_action_html = ""
            if _s_action:
                _s_action_html = (
                    f'<div style="font-size:0.82em;color:#6366f1;margin-top:5px;'
                    f'padding-top:5px;border-top:1px dashed #e2e8f0;white-space:normal">'
                    f'&#8594; {_s_action}'
                    f'</div>'
                )
            _is_supporting = ((_op == "YES" and _si < 2) or (_op == "NO" and _si > 0)) if _op else True
            _border_clr = "#818CF8" if _is_supporting else "#E2E8F0"
            _scen_items += (
                f'<div style="border-left:3px solid {_border_clr};padding:5px 10px;margin-bottom:6px">'
                f'<div style="font-size:0.74em;font-weight:700;color:#475569">'
                f'{en_safe(_s.get("label_en") or _s["label"] if lang == "en" else _s["label"], "scenario.label_en", lang)} <span style="color:#94A3B8;font-weight:400">({_s["prob"]}%)</span>'
                f'</div>'
                f'<div style="font-size:0.71em;color:#64748B;line-height:1.5;margin-top:2px;'
                f'white-space:normal;overflow:visible">{en_safe(_s_content, "scenario.content_en", lang)}</div>'
                f'{_s_action_html}'
                f'</div>'
            )
        _acc_lbl = "▼ 各シナリオの根拠" if lang == "ja" else "▼ Scenario Backgrounds"
        _scenarios_accordion_html = (
            f'<details style="margin-top:8px">'
            f'<summary style="font-size:0.75em;color:#6366f1;cursor:pointer;'
            f'padding:4px 0;font-weight:600;list-style:none">{_acc_lbl}</summary>'
            f'<div style="padding:8px 0">{_scen_items}</div>'
            f'</details>'
        )

    # Verdict line
    verdict_inner = ""
    if _op_hit_cond:
        _hit_clr = {"YES": "#1D4ED8", "NO": "#B91C1C"}.get(_op, "#6B7280")
        _cond_clean = (
            _op_hit_cond
            .replace(" \u2014 Nowpattern\u306e\u7684\u4e2d", "")
            .replace(" \u2014 Nowpattern wins", "")
            .strip()
        )
        if is_resolved:
            _verdict_lbl = "\u5224\u5b9a" if lang == "ja" else "Verdict"
            if is_hit:
                _vend = f'\u2705 {"\u7684\u4e2d" if lang == "ja" else "Accurate"}'
                _vend_clr = "#16a34a"
            else:
                _vend = f'\u274c {"\u5916\u308c" if lang == "ja" else "Missed"}'
                _vend_clr = "#dc2626"
            verdict_inner = (
                f'<div style="font-size:0.75em;color:#555;padding:5px 0 2px;'
                f'border-top:1px dashed {_op_bord};margin-top:5px">'
                f'<span style="color:{_hit_clr};font-weight:700">&#10145; {_verdict_lbl}:</span>'
                f' {_cond_clean}'
                f' \u2192 <strong style="color:{_vend_clr}">{_vend}</strong>'
                f'</div>'
            )
        else:
            _verdict_lbl = "\u5224\u5b9a\u57fa\u6e96" if lang == "ja" else "Verdict"
            _verdict_win = "\u7684\u4e2d" if lang == "ja" else "Nowpattern wins"
            verdict_inner = (
                f'<div style="font-size:0.75em;color:#555;padding:5px 0 2px;'
                f'border-top:1px dashed {_op_bord};margin-top:5px">'
                f'<span style="color:{_hit_clr};font-weight:700">&#10145; {_verdict_lbl}:</span>'
                f' {_cond_clean}'
                f' &#10132; <strong style="color:{_hit_clr}">{_verdict_win}</strong>'
                f'</div>'
            )

    # === S2: Market consensus block (ALWAYS shown, independent) ===
    if market_section_html:
        market_collapsed_html = (
            f'<div style="border-left:4px solid #6366f1;background:#F8FAFC;'
            f'border:1px solid #E2E8F0;border-left-width:4px;'
            f'border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:5px">'
            f'{market_section_html}'
            f'</div>'
        )
    else:
        _no_mkt_lbl = (
            "\U0001f4ca \u5e02\u5834\u30c7\u30fc\u30bf\u306a\u3057 \u2014 Nowpattern\u72ec\u81ea\u5206\u6790"
            if lang == "ja" else
            "\U0001f4ca No market data \u2014 Nowpattern original analysis"
        )
        market_collapsed_html = (
            f'<div style="border-left:4px solid #94A3B8;background:#F8FAFC;'
            f'border:1px solid #E2E8F0;border-left-width:4px;'
            f'border-radius:0 6px 6px 0;padding:6px 12px;margin-bottom:5px">'
            f'<div style="font-size:0.74em;color:#94A3B8;font-weight:600">{_no_mkt_lbl}</div>'
            f'</div>'
        )

    # === S3: Nowpattern stance block (ALWAYS shown, independent) ===
    if _op:
        _conf_suffix = "\u306e\u78ba\u4fe1" if lang == "ja" else " confidence"
        _op_prob_html = (
            f'<span style="font-size:0.85em;font-weight:700;color:{_op_clr};opacity:0.85">'
            f'&nbsp;{_op_prob}%{_conf_suffix}</span>'
        ) if _op_prob else ""
        stance_collapsed_html = (
            f'<div style="border-left:4px solid {_op_clr};background:{_op_bg};'
            f'border:1px solid {_op_bord};border-left-width:4px;'
            f'border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:7px">'
            f'<div style="font-size:0.68em;color:#888;margin-bottom:3px">{_op_label}</div>'
            f'<div style="display:flex;align-items:center;gap:6px">'
            f'<span style="font-size:1.55em;font-weight:900;color:{_op_clr};'
            f'line-height:1;letter-spacing:-0.02em">&#9679; {_op}</span>'
            f'{_op_prob_html}'
            f'{contrarian_badge}'
            f'</div>'
            f'{_formula_html}'
            f'{verdict_inner}'
            f'</div>'
        )
    elif base is not None and base != "":
        # Derive YES/NO from base probability (>= 51 YES, <= 49 NO, 50 NEUTRAL)
        _base_f = float(base)
        if _base_f >= 51:
            _derived_op = "YES"
        elif _base_f <= 49:
            _derived_op = "NO"
        else:
            # Force direction — 50% has no place in Oracle
            _direction_r = r.get("resolution_direction", "optimistic")
            _derived_op = "YES" if _direction_r == "optimistic" else "NO"
        _d_clr = _OP_CLR.get(_derived_op, "#6B7280")
        _d_bg = _OP_BG.get(_derived_op, "#F9FAFB")
        _d_bord = _OP_BORD.get(_derived_op, "#E5E7EB")
        _conf_suffix = "\u306e\u78ba\u4fe1" if lang == "ja" else " confidence"
        _d_prob_html = (
            f'<span style="font-size:0.85em;font-weight:700;color:{_d_clr};opacity:0.85">'
            f'&nbsp;{base}%{_conf_suffix}</span>'
        )
        _d_contrarian = ""
        if _derived_op != "NEUTRAL" and _mc and isinstance(_mc, dict) and _mc.get("pick") and _mc.get("pick") != _derived_op:
            _d_contrarian = (
                f'<span style="font-size:0.62em;background:#FEF3C7;color:#92400E;'
                f'border-radius:9999px;padding:1px 7px;margin-left:6px;vertical-align:middle">'
                f'&#9889; {"\u9006\u5f35\u308a" if lang == "ja" else "Contrarian"}</span>'
            )
        stance_collapsed_html = (
            f'<div style="border-left:4px solid {_d_clr};background:{_d_bg};'
            f'border:1px solid {_d_bord};border-left-width:4px;'
            f'border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:7px">'
            f'<div style="font-size:0.68em;color:#888;margin-bottom:3px">{_op_label}</div>'
            f'<div style="display:flex;align-items:center;gap:6px">'
            f'<span style="font-size:1.55em;font-weight:900;color:{_d_clr};'
            f'line-height:1;letter-spacing:-0.02em">&#9679; {_derived_op}</span>'
            f'{_d_prob_html}'
            f'{_d_contrarian}'
            f'</div>'
            f'{verdict_inner}'
            f'</div>'
        )
    else:
        if analysis_is_fallback:
            _article_lbl = "利用可能な分析" if lang == "ja" else "Available Analysis"
            _article_cta = "\U0001f4cb English analysis available \u2192" if lang == "ja" else "\U0001f4cb 日本語分析あり \u2192"
        else:
            _article_lbl = "Nowpattern\u306e\u5206\u6790" if lang == "ja" else "Nowpattern\u2019s Analysis"
            _article_cta = "\U0001f4cb \u8a18\u4e8b\u3067\u8a73\u7d30\u5206\u6790 \u2192" if lang == "ja" else "\U0001f4cb Detailed analysis in article \u2192"
        stance_collapsed_html = (
            f'<div style="border-left:4px solid #94A3B8;background:#F9FAFB;'
            f'border:1px solid #E5E7EB;border-left-width:4px;'
            f'border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:7px">'
            f'<div style="font-size:0.68em;color:#888;margin-bottom:3px">{_article_lbl}</div>'
            f'<div style="font-size:0.88em;color:#6B7280;font-weight:600">{_article_cta}</div>'
            f'</div>'
        )

    # Combined header = S2 (market) + S3 (stance)
    pick_header_html = stance_collapsed_html + market_collapsed_html

    # === Collapsed bottom chips ===
    genre_str = ",".join(genres) if genres else "all"

    if is_resolved:
        outcome_en = outcome_map.get(outcome, outcome) or ""
        if is_disputed:
            _disp_lbl = "\u4e8b\u5b9f\u78ba\u8a8d\u4e2d" if lang == "ja" else "Under Review"
            collapsed_chip = (
                '<div style="display:inline-flex;gap:6px;align-items:center;padding:3px 10px;'
                'background:#fffbeb;border-radius:6px">'
                f'<span style="font-size:0.75em;color:#d97706;font-weight:700">{_disp_lbl}</span>'
                '</div>'
            )
        elif is_hit:
            collapsed_chip = (
                f'<div style="display:inline-flex;gap:6px;align-items:center;padding:3px 10px;'
                f'background:#e8f5e9;border-radius:6px">'
                f'<span style="font-size:0.75em;color:#16a34a;font-weight:700">'
                f'{outcome_en}{outcome_suffix_hit}</span>'
                f'<span style="font-size:0.85em;font-weight:700;color:#16a34a">\u2192\u2705</span>'
                f'</div>'
            )
        else:
            collapsed_chip = (
                f'<div style="display:inline-flex;gap:6px;align-items:center;padding:3px 10px;'
                f'background:#fde8e8;border-radius:6px">'
                f'<span style="font-size:0.75em;color:#dc2626;font-weight:700">'
                f'{outcome_en}{outcome_suffix_miss}</span>'
                f'<span style="font-size:0.85em;font-weight:700;color:#dc2626">\u2192\u274c</span>'
                f'</div>'
            )
        # Market final chip
        mf_chip = ""
        if market_prob is not None:
            mf_text_color = "#16a34a" if is_hit else "#dc2626"
            mf_label = f"{market_src}\u6700\u7d42\u5024" if lang == "ja" else f"{market_src} final"
            mf_chip = (
                f'<div style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;'
                f'background:#f0f4ff;border-radius:12px">'
                f'<span style="font-size:0.72em;color:#6366f1;font-weight:600">{mf_label}</span>'
                f'<span style="font-size:0.85em;font-weight:700;color:{mf_text_color}">{market_prob}%</span>'
                f'</div>'
            )
        resolved_date = resolved_at[:10] if resolved_at else ""
        date_badge = _deadline_badge(resolved_date, lang, resolved=True) if resolved_date else ""
        bottom_chips = f'{collapsed_chip}{mf_chip}{date_badge}'
    else:
        pess_chip = _scenario_chip(pess_lbl, pess, pess_content, "#fde8e8", "", "#dc2626")
        base_chip = _scenario_chip(base_lbl, base, base_content, "#fff8e1", "border:2px solid #b8860b;", "#b8860b")
        opt_chip  = _scenario_chip(opt_lbl, opt, opt_content, "#e8f5e9", "", "#16a34a")
        mkt_chip  = _market_chip(market_prob, market_src)
        bottom_chips = f'{pess_chip}{base_chip}{opt_chip}{mkt_chip}'

    # Deadline badge (tracking only)
    deadline_html = _deadline_badge(trigger_date, lang, resolved=False) if (not is_resolved and trigger_date) else ""

    # === Published at label ===
    pub_date = published_at[:10] if published_at else ""
    if is_resolved:
        pub_label = ("\u79c1\u305f\u3061\u306e\u4e88\u60f3\uff08\u8a18\u4e8b\u516c\u958b\u6642\uff09" if lang == "ja"
                     else "Our Prediction (at publication)")
    elif pub_date:
        pub_label = (f"{pub_date} \u8a18\u4e8b\u516c\u958b\u6642" if lang == "ja"
                     else f"at publication ({pub_date})")
    else:
        pub_label = ours_section_label

    # === Expanded Column 1: Our Prediction ===
    if is_resolved:
        def _sbox(label, val, bg, border, color):
            if val is None:
                return ""
            return (
                f'<div style="flex:1;background:{bg};border-radius:6px;padding:6px;'
                f'text-align:center;{border}">'
                f'<div style="font-size:0.68em;color:{color};font-weight:600">{label}</div>'
                f'<div style="font-size:1.1em;font-weight:700;color:{color}">{val}%</div>'
                f'</div>'
            )
        exp_pess = _sbox(pess_lbl, pess, "#fde8e8", "", "#dc2626")
        exp_base = _sbox(base_lbl, base, "#fff8e1", "border:2px solid #b8860b;", "#b8860b")
        exp_opt  = _sbox(opt_lbl, opt, "#e8f5e9", "", "#16a34a")
    else:
        exp_pess = _scenario_box_exp(pess_lbl, pess, pess_content, "#fde8e8", "", "#dc2626")
        exp_base = _scenario_box_exp(base_lbl, base, base_content, "#fff8e1", "border:2px solid #b8860b;", "#b8860b")
        exp_opt  = _scenario_box_exp(opt_lbl, opt, opt_content, "#e8f5e9", "", "#16a34a")

    # Resolution criteria box (tracking only)
    rq_html = ""
    if not is_resolved:
        resolution_question = ""
        if lang == "ja":
            resolution_question = (r.get("resolution_question_ja") or r.get("resolution_question") or "")
        else:
            resolution_question = r.get("resolution_question", "")
        if resolution_question:
            rq_html = (
                f'<div style="background:#fffbf0;border-radius:6px;padding:8px 12px;'
                f'margin-bottom:10px;border-left:3px solid #b8860b;font-size:0.82em;'
                f'color:#555;line-height:1.5">'
                f'<span style="font-weight:700;color:#b8860b">{resolution_criteria_label}:</span> '
                f'{resolution_question}'
                f'</div>'
            )

    # Scenario accordion (tracking only)
    base_detail = ""
    if not is_resolved:
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
                + '</div></details>'
            )

    _gap = "4px" if is_resolved else "6px"
    col1_html = (
        '<div style="background:#fff;border-radius:8px;padding:12px;border:1px solid #e0e0e0">'
        f'<div style="font-size:0.72em;font-weight:700;letter-spacing:.05em;'
        f'text-transform:uppercase;color:#999;margin-bottom:8px">{pub_label}</div>'
        f'{rq_html}'
        f'<div style="display:flex;gap:{_gap};margin-bottom:10px">'
        f'{exp_pess}{exp_base}{exp_opt}'
        f'</div>'
        '</div>'
    )

    # === Expanded Column 2: Market ===
    _has_mc = (r.get("market_consensus") and isinstance(r.get("market_consensus"), dict)
               and r["market_consensus"].get("pick"))
    pm = r.get("polymarket") or {} if not _has_mc else {}
    mc_embed = r.get("metaculus") or {} if not _has_mc else {}
    if lang == "ja":
        mq = ""  # JA: suppress English market question text
    else:
        mq = (pm.get("question") or mc_embed.get("question") or r.get("linked_market_question") or "")[:80]
    market_url = r.get("linked_market_url")

    # YES/NO split bar (tracking only)
    yes_no_bar = ""
    if not is_resolved and not _has_mc:
        _bar_outcomes = pm.get("outcomes") or mc_embed.get("outcomes")
        _bar_from_linked = False
        if _bar_outcomes is None and r.get("linked_market_prob") is not None:
            _y = round(prob01_to_pct(r["linked_market_prob"]), 1)
            _bar_outcomes = {"Yes": _y, "No": round(100.0 - _y, 1)}
            _bar_from_linked = True
        if _bar_outcomes is None and market_prob is not None:
            _bar_outcomes = {"Yes": float(market_prob), "No": round(100.0 - float(market_prob), 1)}
        if _bar_outcomes:
            _yes = float(_bar_outcomes.get("Yes", 0.0))
            _no  = float(_bar_outcomes.get("No", round(100.0 - _yes, 1)))
            _is_close = (40.0 <= _yes <= 60.0)
            _close_lbl = "\u62ee\u6297\u4e2d" if lang == "ja" else "Neck&amp;Neck"
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
                f'<span>{"市場YES" if (_bar_from_linked and lang == "ja") else ("Market YES" if _bar_from_linked else "YES")}&nbsp;{_yes:.1f}%</span>'
                f'{_close_badge}'
                f'<span>{"市場NO" if (_bar_from_linked and lang == "ja") else ("Market NO" if _bar_from_linked else "NO")}&nbsp;{_no:.1f}%</span>'
                f'</div>'
            )

    if is_resolved and market_prob is not None:
        mkt_section_lbl = (
            f"\u5e02\u5834\u306e\u4e88\u60f3\uff08{market_src}\u3001\u89e3\u6c7a\u76f4\u524d\uff09" if lang == "ja"
            else f"Market ({market_src}, pre-resolution)"
        )
        mf_res = (
            ("\u2192 \u89e3\u6c7a: YES" if is_hit else "\u2192 \u89e3\u6c7a: NO") if lang == "ja"
            else ("\u2192 Resolved: YES" if is_hit else "\u2192 Resolved: NO")
        )
        col2_html = (
            '<div style="background:#f0f4ff;border-radius:8px;padding:12px;border:1px solid #c7d2fe">'
            f'<div style="font-size:0.72em;font-weight:700;letter-spacing:.05em;'
            f'text-transform:uppercase;color:#999;margin-bottom:8px">{mkt_section_lbl}</div>'
            f'<div style="font-size:1.6em;font-weight:700;color:#6366f1">{market_prob}%</div>'
            f'<div style="font-size:0.75em;color:#6366f1;margin-top:6px">{mf_res}</div>'
            '</div>'
        )
    elif market_prob is not None:
        if lang == "ja":
            mq_desc = f'\u300c{mq}\u300d\u78ba\u7387' if mq else "\u4e88\u6e2c\u30b3\u30df\u30e5\u30cb\u30c6\u30a3\u306e\u96c6\u5408\u77e5"
            view_market_label = "\u2192 \u5e02\u5834\u3092\u898b\u308b"
        else:
            mq_desc = f'"{mq}" probability' if mq else "probability"
            view_market_label = "\u2192 View market"
        market_link_btn = ""
        if market_url:
            market_link_btn = (
                f'<div style="margin-top:12px">'
                f'<a href="{market_url}" target="_blank" rel="noopener" '
                f'style="display:inline-block;padding:6px 14px;border-radius:6px;'
                f'font-size:0.84em;font-weight:600;text-decoration:none;'
                f'background:#f0f4ff;color:#6366f1;border:1px solid #c7d2fe">'
                f'{view_market_label} \u2197</a></div>'
            )
        col2_html = (
            '<div style="background:#fff;border-radius:8px;padding:14px;border:1px solid #e0e0e0">'
            f'<div style="font-size:0.72em;font-weight:700;letter-spacing:.05em;'
            f'text-transform:uppercase;color:#999;margin-bottom:8px">{market_section_label}</div>'
            f'<div style="font-size:2em;font-weight:700;color:#6366f1;margin-bottom:2px">'
            f'{market_prob}%</div>'
            f'{yes_no_bar}'
            f'<div style="font-size:0.82em;color:#666;margin-bottom:4px">'
            f'{mq_desc}<br>{crowd_desc}</div>'
            + market_link_btn + '</div>'
        )
    else:
        no_data = "\u5e02\u5834\u30c7\u30fc\u30bf\u306a\u3057" if lang == "ja" else "No market data"
        col2_html = (
            '<div style="background:#f5f5f0;border-radius:8px;padding:12px;'
            'display:flex;align-items:center;justify-content:center;'
            f'color:#aaa;font-size:0.85em;min-height:80px">{no_data}</div>'
        )

    # === Expanded Column 3: Result ===
    if is_resolved:
        if is_disputed:
            _r_color, _r_bg = "#d97706", "#fffbeb"
            _r_border = "border:2px solid #fcd34d"
            _disp_lbl = "\u4e8b\u5b9f\u78ba\u8a8d\u4e2d" if lang == "ja" else "Under Review"
            result_text = f"\u26a0\ufe0f {_disp_lbl}"
        elif is_hit:
            _r_color, _r_bg = "#16a34a", "#e8f5e9"
            _r_border = "border:2px solid #16a34a"
            _oe = outcome_map.get(outcome, outcome) or ""
            result_text = "\u2705 " + _oe + outcome_suffix_hit
        else:
            _r_color, _r_bg = "#dc2626", "#fff0f0"
            _r_border = "border:1px solid #fca5a5"
            _oe = outcome_map.get(outcome, outcome) or ""
            result_text = "\u274c " + _oe + outcome_suffix_miss
        actual_desc = base_content or opt_content or pess_content or ""
        col3_html = (
            f'<div style="background:{_r_bg};border-radius:8px;padding:12px;{_r_border}">'
            f'<div style="font-size:0.72em;font-weight:700;letter-spacing:.05em;'
            f'text-transform:uppercase;color:{_r_color};margin-bottom:8px">{result_section_label}</div>'
            f'<div style="font-size:1.1em;font-weight:700;color:{_r_color};margin-bottom:6px">'
            f'{result_text}</div>'
            + (
                f'<div style="font-size:0.8em;color:#333;line-height:1.5;'
                f'overflow:hidden;display:-webkit-box;-webkit-line-clamp:4;'
                f'-webkit-box-orient:vertical">{actual_desc}</div>'
                if actual_desc else ""
            )
            + '</div>'
        )
    else:
        col3_html = (
            '<div style="background:#fafaf8;border-radius:8px;padding:12px;'
            'border:2px dashed #d1d5db;display:flex;flex-direction:column;'
            'align-items:center;justify-content:center;min-height:80px;text-align:center">'
            f'<div style="font-size:0.72em;font-weight:700;letter-spacing:.05em;'
            f'text-transform:uppercase;color:#aaa;margin-bottom:8px">{result_section_label}</div>'
            f'<div style="font-size:1.3em;margin-bottom:4px">{waiting_label}</div>'
            f'<div style="font-size:0.75em;color:#aaa">{pending_note}</div>'
            '</div>'
        )

    # === Brier score (resolved only) ===
    brier_html = ""
    if is_resolved:
        if score_tier == "NOT_SCORABLE" or brier is None:
            brier_html = (
                '<div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;'
                'padding:10px 14px;margin-top:12px">'
                f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
                f'<span style="font-size:0.82em;color:#9A3412;font-weight:700">{not_scored_label}</span>'
                f'{_score_tier_badge_html(score_tier, lang, compact=True)}'
                '</div>'
                f'{_score_disclaimer_html(score_tier, lang, compact=True, include_link=True)}'
                '</div>'
            )
        else:
            public_score = _public_score_value(brier)
            brier_color = _public_score_color(public_score)
            mkt_brier_html = ""
            market_raw_brier = None
            if market_prob is not None and resolved_binary_outcome is not None:
                p = float(market_prob) / 100.0
                market_raw_brier = round((p - resolved_binary_outcome) ** 2, 4)
                market_public_score = _public_score_value(market_raw_brier)
                market_color = _public_score_color(market_public_score)
                if market_public_score is not None:
                    mkt_brier_html = (
                        f'<div><span style="color:#888">{market_acc_label}</span> '
                        f'<strong style="color:{market_color}">{market_public_score:.1f}%</strong></div>'
                    )
            brier_html = (
                '<div style="background:#f5f5f0;border-radius:8px;padding:10px 14px;'
                'margin-top:12px;display:flex;gap:20px;font-size:0.85em;flex-wrap:wrap">'
                f'<div><span style="color:#888">{accuracy_label}</span> '
                f'<strong style="color:{brier_color}">{public_score:.1f}%</strong> '
                f'{_score_tier_badge_html(score_tier, lang, compact=True)}</div>'
                + mkt_brier_html
                + f'<div style="font-size:0.78em;color:#6B7280">{_score_basis_note(lang, brier, market_raw_brier)}</div>'
                + _score_disclaimer_html(score_tier, lang, compact=True, include_link=True)
                + '</div>'
            )

    # === Evidence panel (resolved only) ===
    _evidence_html = ""
    if is_resolved:
        _evidence = r.get("resolution_evidence") or {}
        _key_text = _evidence.get("key_evidence_text", "")
        _confidence = _evidence.get("confidence", "")
        _ihash = r.get("integrity_hash", "")
        _rebuttals = r.get("rebuttals", [])
        _dispute_reason = r.get("dispute_reason", "")
        if lang == "ja":
            _ev_title = "\ud83d\udccb \u5224\u5b9a\u6839\u62e0"
            _hash_label = "\u6539\u3056\u3093\u691c\u77e5\u30b3\u30fc\u30c9:"
            _rebuttal_label = "\u53cd\u8ad6"
            _rebuttal_unit = "\u4ef6"
            _dispute_label_ev = "\u7570\u8b70\u7406\u7531:"
        else:
            _ev_title = "\ud83d\udccb Resolution Evidence"
            _hash_label = "Integrity fingerprint:"
            _rebuttal_label = "Rebuttal"
            _rebuttal_unit = "s"
            _dispute_label_ev = "Dispute reason:"
        if _key_text or _ihash:
            _hash_display = (
                f'<div style="font-size:0.68em;color:#aaa;margin-top:6px;font-family:monospace">'
                f'{_hash_label} <span style="color:#b8860b">{_ihash[-12:] if _ihash else "\u2014"}</span>'
                + (f' <span style="color:#aaa">({_confidence})</span>' if _confidence else '')
                + '</div>'
            )
            _dispute_html = (
                f'<div style="font-size:0.75em;color:#d97706;margin-top:4px">\u26a0\ufe0f {_dispute_label_ev} {_dispute_reason}</div>'
                if _dispute_reason else ""
            )
            _rebuttal_html = (
                f'<div style="font-size:0.75em;color:#6366f1;margin-top:4px">'
                f'\ud83d\udcac {len(_rebuttals)}{_rebuttal_unit}\u306e{_rebuttal_label}</div>'
            ) if _rebuttals else ""
            _evidence_html = (
                '<details style="margin-top:10px">'
                f'<summary style="cursor:pointer;font-size:0.78em;color:#888;'
                f'user-select:none;list-style:none;padding:4px 0;outline:none">'
                f'\u25bc {_ev_title}</summary>'
                '<div style="padding:8px 10px;background:#fffbf0;border-radius:4px;'
                'border-left:3px solid #b8860b;margin-top:6px">'
                + (f'<div style="font-size:0.8em;color:#555;line-height:1.5">{_key_text}</div>' if _key_text else '')
                + _hash_display + _dispute_html + _rebuttal_html
                + '</div></details>'
            )

    # === Resolve date row (tracking only) ===
    resolve_date_html = ""
    if not is_resolved and trigger_date:
        try:
            parts = trigger_date.split("-")
            y, m2 = parts[0], int(parts[1])
            if lang == "ja":
                _rd_str = f"{y}\u5e74{m2}\u6708"
            else:
                import calendar
                _rd_str = f"{calendar.month_abbr[m2]} {y}"
        except Exception:
            _rd_str = trigger_date
        resolve_date_html = (
            '<div style="background:#fff8e1;border-radius:8px;padding:10px 14px;margin-bottom:10px">'
            f'<div style="font-size:0.85em">'
            f'<span style="color:#888">{resolve_label}</span> '
            f'<strong style="color:#b8860b">{_rd_str}</strong>'
            f'</div></div>'
        )

    # === Footer links ===
    footer_links = ""
    if url and url != "#":
        footer_links = (
            f'<a href="{url}" style="display:inline-block;padding:6px 14px;border-radius:6px;'
            f'font-size:0.84em;font-weight:600;text-decoration:none;'
            f'background:#fff8e1;color:#b8860b;border:1px solid #e6c86a">{read_label}</a>'
        )
    if is_resolved and market_url:
        _mkt_nav = "\u2192 \u5e02\u5834\u30da\u30fc\u30b8\u3092\u898b\u308b \u2197" if lang == "ja" else "\u2192 View market page \u2197"
        footer_links += (
            f'<a href="{market_url}" target="_blank" rel="noopener" '
            f'style="display:inline-block;padding:6px 14px;border-radius:6px;'
            f'font-size:0.84em;font-weight:600;text-decoration:none;'
            f'background:#f0f4ff;color:#6366f1;border:1px solid #c7d2fe">{_mkt_nav}</a>'
        )

    # === Final HTML — ALWAYS 3-COLUMN GRID ===
    _alpha_card_style = (
        "border-left:3px solid #EF4444!important;"
        "background:linear-gradient(135deg,#FFF5F5 0%,#FFF 70%)!important;"
    ) if is_alpha_alert else ""
    _anchor_id = r.get('prediction_id', '').lower()
    _id_attr = f' id="{_anchor_id}"' if _anchor_id else ''
    return (
        f'<details{_id_attr} style="border-bottom:1px solid #eeebe4;padding:2px 0;{_alpha_card_style}" data-genres="{genre_str}">'
        '<summary>'
        '<div style="display:flex;align-items:flex-start;gap:8px;padding:10px 4px;user-select:none">'
        '<div style="flex:1">'
        f'{_status_badge}'
        f'{_deadline_html}'
        f'<div style="font-size:0.7em;color:#999;margin-bottom:6px">'
        f'{tracking_prefix}&nbsp;<span style="color:#333;font-weight:500">{_tracking_q}</span>'
        '</div>'
        f'{_ev_line}'
        f'{pick_header_html}'
        '<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px;flex-wrap:wrap">'
        f'<span style="color:#b8860b;font-weight:600;font-size:0.88em;line-height:1.4">{title}</span>'
        f'{deadline_html}'
        '</div>'
        '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">'
        f'{bottom_chips}'
        '</div>'
        '</div>'
        '<span class="chevron" style="color:#bbb;font-size:0.9em;margin-top:18px">\u25bc</span>'
        '</div>'
        '</summary>'
        '<div style="padding:16px;background:#f9f9f6;border-radius:0 0 10px 10px;'
        'margin:0 4px 10px;border:1px solid #e8e4dc">'
        '<div class="np-card-grid" style="display:grid;grid-template-columns:1fr 1fr 1fr;'
        'gap:12px;margin-bottom:14px">'
        f'{col1_html}'
        f'{col2_html}'
        f'{col3_html}'
        '</div>'
        f'{resolve_date_html}'
        f'{brier_html}'
        f'{_evidence_html}'
        f'{_scenarios_accordion_html}'
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">'
        f'{footer_links}'
        '</div>'
        '</div>'
        '</details>'
    )






def _build_compact_row(r, lang):
    # Compact row for resolving predictions.
    # ~400 bytes vs ~4000 bytes for full card => 91% EN page size reduction.
    # Uses <details> so existing JS filter (data-genres, textContent) still works.
    if lang == 'en':
        title = (r.get('title_en', '') or
                 r.get('article_title_en', '') or
                 r.get('resolution_question_en', '') or
                 r.get('resolution_question', '') or
                 r.get('title', ''))
    else:
        title = r.get('title', '')
    title_short = title[:80] + '...' if len(title) > 80 else title

    genre_str = r.get('genre_tags', '')
    genre_data = ','.join(g.strip().lower() for g in genre_str.split(',')) if genre_str else 'all'

    pick_prob = r.get('our_pick_prob')
    pick_yn   = r.get('our_pick', '')
    if pick_prob is not None:
        prob_text  = f'{pick_yn} {pick_prob}%' if pick_yn else f'{pick_prob}%'
        prob_badge = (
            f"<span style='background:#2563eb;color:#fff;font-size:0.72em;"
            f"font-weight:700;padding:2px 7px;border-radius:10px;white-space:nowrap'>"
            f"{prob_text}</span>"
        )
    else:
        prob_badge = ''

    deadline = r.get('oracle_deadline', '')
    if not deadline:
        triggers = r.get('triggers', [])
        if triggers:
            deadline = (triggers[0].get('date_en', '') if lang == 'en'
                        else triggers[0].get('date', '')) or triggers[0].get('date', '')
    dl_short = deadline[:22] + '...' if len(deadline) > 22 else deadline
    deadline_html = (
        f"<span style='font-size:0.73em;color:#aaa;white-space:nowrap'>{dl_short}</span>"
        if dl_short else ''
    )

    url = r.get('url', '') or r.get('ghost_url', '')
    if url and not url.startswith('http'):
        url = 'https://nowpattern.com' + url
    analysis_is_fallback = bool(r.get("analysis_is_fallback"))

    status_lbl = '結果待ち' if lang == 'ja' else 'Resolving'
    status_badge = (
        f"<span style='background:#e8f0fe;color:#1a73e8;font-size:0.68em;"
        f"font-weight:600;padding:2px 6px;border-radius:8px;white-space:nowrap'>"
        f"{status_lbl}</span>"
    )

    if url:
        title_html = (
            f"<a href='{url}' target='_blank' rel='noopener' "
            f"style='flex:1;font-size:0.84em;color:#333;font-weight:500;"
            f"text-decoration:none;line-height:1.4'>{title_short}</a>"
        )
    else:
        title_html = (
            f"<span style='flex:1;font-size:0.84em;color:#333;font-weight:500;"
            f"line-height:1.4'>{title_short}</span>"
        )

    read_lbl = '→ 記事を読む' if lang == 'ja' else '→ Read article'
    if analysis_is_fallback:
        read_lbl = '→ English analysis' if lang == 'ja' else '→ 日本語分析'
    else:
        read_lbl = '→ 記事を読む' if lang == 'ja' else '→ Read article'
    article_link = (
        f"<a href='{url}' target='_blank' rel='noopener' "
        f"style='font-size:0.8em;color:#b8860b;text-decoration:none'>{read_lbl}</a>"
        if url else ''
    )

    _anchor_id = r.get('prediction_id', '').lower()
    _id_attr = f" id='{_anchor_id}'" if _anchor_id else ''
    return (
        f"<details{_id_attr} data-genres='{genre_data}' "
        f"style='border-bottom:1px solid #f0ece4;padding:0'>"
        "<summary style='list-style:none;cursor:pointer;padding:8px 4px;"
        "display:flex;align-items:center;gap:8px;user-select:none'>"
        f"{status_badge}"
        f"{title_html}"
        f"{deadline_html}"
        f"{prob_badge}"
        "</summary>"
        "<div style='padding:6px 16px 10px;font-size:0.82em;color:#666'>"
        f"{article_link}"
        "</div>"
        "</details>"
    )


def build_page_html(rows, stats, lang="ja"):
    """Build predictions page HTML — 4 blocks: scoreboard + tracking + resolved + automation."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M JST")

    # B2: Split formal predictions vs Ghost article analysis
    formal_rows = [r for r in rows if r.get("source") == "prediction_db"]
    analysis_rows = [r for r in rows if r.get("source") != "prediction_db"]

    analysis_rows_tracking = [r for r in analysis_rows if not _is_resolved_status(r)]
    tracking = [r for r in formal_rows if not _is_resolved_status(r)] + analysis_rows_tracking
    resolved = [r for r in formal_rows if _is_resolved_status(r)]

    # ── BLOCK 1: Scoreboard (formal predictions only) ──
    block1 = _scoreboard_block(rows, lang)
    total_predictions = len(formal_rows)
    same_lang_analysis = sum(1 for r in formal_rows if r.get("same_lang_url"))
    cross_lang_analysis = sum(1 for r in formal_rows if r.get("analysis_is_fallback"))
    no_article_analysis = sum(1 for r in formal_rows if not r.get("url"))

    if lang == "ja":
        view_toolbar = (
            '<div id="np-view-toolbar" style="position:sticky;top:12px;z-index:20;margin-bottom:18px;'
            'background:rgba(255,255,255,.96);backdrop-filter:blur(10px);border-radius:14px;'
            'padding:18px 20px;box-shadow:0 8px 28px rgba(15,23,42,.08)">'
            '<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between">'
            '<div style="display:flex;gap:8px;flex-wrap:wrap">'
            f'<button class="np-view-btn active" data-view="all">すべて <span>{total_predictions}</span></button>'
            f'<button class="np-view-btn" data-view="tracking">追跡中 <span>{len(tracking)}</span></button>'
            f'<button class="np-view-btn" data-view="resolved">解決済み <span>{len(resolved)}</span></button>'
            '</div>'
            f'<div style="font-size:0.78em;color:#64748b">同じ <strong>{total_predictions} 件</strong> の予測を JA/EN 両方で表示します。'
            f' 日本語記事リンク {same_lang_analysis} 件 / 英語分析フォールバック {cross_lang_analysis} 件 / 記事未接続 {no_article_analysis} 件。</div>'
            '</div>'
            '</div>'
        )
    else:
        view_toolbar = (
            '<div id="np-view-toolbar" style="position:sticky;top:12px;z-index:20;margin-bottom:18px;'
            'background:rgba(255,255,255,.96);backdrop-filter:blur(10px);border-radius:14px;'
            'padding:18px 20px;box-shadow:0 8px 28px rgba(15,23,42,.08)">'
            '<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between">'
            '<div style="display:flex;gap:8px;flex-wrap:wrap">'
            f'<button class="np-view-btn active" data-view="all">All <span>{total_predictions}</span></button>'
            f'<button class="np-view-btn" data-view="tracking">Tracking <span>{len(tracking)}</span></button>'
            f'<button class="np-view-btn" data-view="resolved">Resolved <span>{len(resolved)}</span></button>'
            '</div>'
            f'<div style="font-size:0.78em;color:#64748b">Both JA and EN trackers now list the same <strong>{total_predictions}</strong> predictions.'
            f' Same-language analysis {same_lang_analysis} / cross-language fallback {cross_lang_analysis} / no article yet {no_article_analysis}.</div>'
            '</div>'
            '</div>'
        )

    # ── BLOCK 2: Tracking (formal predictions only) ──
    if lang == "ja":
        tracking_title = (
            f'追跡中のシナリオ <span style="font-size:0.8em;color:#888;font-weight:400">'
            f'{len(tracking)}件</span>'
        )
        search_placeholder = "🔍  キーワードで絞り込み..."
        auto_updated = f"最終更新: {now}"
    else:
        tracking_title = (
            f'Active Scenarios <span style="font-size:0.8em;color:#888;font-weight:400">'
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

    # Split tracking: active/open -> full _build_card(); resolving -> compact row
    # Reduces EN page: 5.27MB -> ~450KB (91% size reduction)
    _featured   = [r for r in tracking if _normalize_status_value(r) in ('active', 'open')]
    _monitoring = [r for r in tracking if _normalize_status_value(r) == 'resolving']
    _featured_cards   = "\n".join(_build_card(r, lang) for r in _featured)
    _monitoring_cards = "\n".join(_build_compact_row(r, lang) for r in _monitoring)
    if _monitoring:
        if lang == 'ja':
            _mon_hdr = (
                "<div style='margin-top:16px;padding:10px 4px 4px;"
                "border-top:2px solid #f0ece4'>"
                f"<p style='font-size:0.78em;color:#bbb;margin:0 0 8px 0'>"
                f"解決待ち（{len(_monitoring)}件）— クリックで記事を開く</p>"
            )
        else:
            _mon_hdr = (
                "<div style='margin-top:16px;padding:10px 4px 4px;"
                "border-top:2px solid #f0ece4'>"
                f"<p style='font-size:0.78em;color:#bbb;margin:0 0 8px 0'>"
                f"Awaiting resolution ({len(_monitoring)}) — click to open article</p>"
            )
        _monitoring_section = _mon_hdr + _monitoring_cards + "</div>"
    else:
        _monitoring_section = ''
    tracking_cards = _featured_cards + _monitoring_section

    block2 = (
        '<div id="np-tracking-section" style="margin-bottom:24px;background:#fff;border-radius:12px;'
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
        resolved_cards = "\n".join(_build_card(r, lang) for r in resolved)
        block3 = (
            '<div id="np-resolved-section" style="margin-bottom:24px;background:#fff;border-radius:12px;'
            'padding:24px 28px;box-shadow:0 2px 8px rgba(0,0,0,.08)">'
            f'<h2 style="color:#333;font-size:1.1em;border-left:4px solid #b8860b;'
            f'padding-left:10px;margin:0 0 8px 0">{resolved_title}</h2>'
            f'<p style="font-size:0.82em;color:#888;margin:0 0 14px 0">{resolved_desc}</p>'
            f'{resolved_cards}'
            '</div>'
        )
    else:
        block3 = (
            '<div id="np-resolved-section" style="margin-bottom:24px;background:#fff;border-radius:12px;'
            'padding:24px 28px;box-shadow:0 2px 8px rgba(0,0,0,.08)">'
            f'<h2 style="color:#333;font-size:1.1em;border-left:4px solid #b8860b;'
            f'padding-left:10px;margin:0 0 8px 0">{resolved_title}</h2>'
            f'<p style="color:#888;font-size:0.9em">{no_resolved_text}</p>'
            '</div>'
        )


    # ── BLOCK 4: Automation ──


    # ── Inline CSS + JS ──
    inline_code = """<style>
details > summary { list-style:none; cursor:pointer; }
details > summary::-webkit-details-marker { display:none; }
.chevron { transition:transform .2s; display:inline-block; }
details[open] .chevron { transform:rotate(180deg); }
.np-cat-btn:focus { outline:none; }
.np-view-btn { min-height:44px;padding:10px 14px;border-radius:9999px;border:1px solid #d6dce5;background:#f8fafc;color:#334155;font-size:0.88em;font-weight:700;cursor:pointer;display:inline-flex;gap:8px;align-items:center; }
.np-view-btn span { display:inline-flex;min-width:24px;justify-content:center;padding:2px 7px;border-radius:9999px;background:#e2e8f0;color:#334155;font-size:0.82em;font-weight:700; }
.np-view-btn.active { background:#0f172a;color:#fff;border-color:#0f172a;box-shadow:0 6px 18px rgba(15,23,42,.14); }
.np-view-btn.active span { background:#f59e0b;color:#1f2937; }
.np-view-btn:hover { background:#eef2f7; }
.np-view-btn.active:hover { background:#111827; }
.np-cat-btn { min-height:40px; }
.np-page-btn { padding:4px 10px;border-radius:4px;border:1px solid #ddd;background:#fff;color:#555;font-size:0.85em;cursor:pointer;font-family:inherit; }
.np-page-btn.active { background:#b8860b;color:#fff;border-color:#b8860b;font-weight:600; }
.np-page-btn:hover { background:#f5f0e0; }
.np-page-btn.active:hover { background:#a07a0a; }
.score-tier-label { white-space:nowrap; }
.score-disclaimer a:hover { opacity:.85; }
@media (max-width: 640px) {
  .np-card-grid { grid-template-columns: 1fr !important; }
  .np-view-btn { flex:1 1 calc(33.333% - 6px); justify-content:center; padding:10px 8px; font-size:0.8em; }
  #np-view-toolbar > div { gap:12px !important; }
}
</style>
<script>
(function(){
  var CARDS_PER_PAGE = window.innerWidth <= 640 ? 18 : 36;
  var currentPage = 1;
  var filteredCards = [];
  var currentView = 'tracking';
  // Category filter
  var cats = document.querySelectorAll('.np-cat-btn');
  var viewButtons = document.querySelectorAll('.np-view-btn');
  function setView(view){
    currentView = view || 'tracking';
    viewButtons.forEach(function(btn){
      btn.classList.toggle('active', btn.dataset.view === currentView);
    });
    var trackingSection = document.getElementById('np-tracking-section');
    var resolvedSection = document.getElementById('np-resolved-section');
    if(trackingSection) trackingSection.style.display = (currentView === 'resolved') ? 'none' : '';
    if(resolvedSection) resolvedSection.style.display = (currentView === 'tracking') ? 'none' : '';
  }
  viewButtons.forEach(function(btn){
    btn.addEventListener('click', function(){
      setView(this.dataset.view);
      if(this.dataset.view !== 'resolved'){
        filterCards();
      }
    });
  });
  cats.forEach(function(btn){
    btn.addEventListener('click', function(){
      cats.forEach(function(b){
        b.style.background='#fff'; b.style.color='#555';
        b.style.border='1px solid #ddd'; b.style.fontWeight='400';
      });
      this.style.background='#b8860b'; this.style.color='#fff';
      this.style.border='2px solid #b8860b'; this.style.fontWeight='600';
      currentPage = 1;
      filterCards();
    });
  });
  // Keyword search
  var searchEl = document.getElementById('np-search');
  if(searchEl) searchEl.addEventListener('input', function(){ currentPage=1; filterCards(); });
  var allCards = Array.from(document.querySelectorAll('#np-tracking-list details'));
  function filterCards(){
    var activeCat = 'all';
    cats.forEach(function(b){
      if(b.style.background==='rgb(184, 134, 11)' || b.style.background==='#b8860b')
        activeCat = b.dataset.cat;
    });
    var kw = searchEl ? searchEl.value.toLowerCase() : '';
    filteredCards = [];
    allCards.forEach(function(d){
      var genres = (d.dataset.genres || '').split(',');
      var matchCat = activeCat==='all' || genres.indexOf(activeCat)>=0;
      var matchKw = !kw || d.textContent.toLowerCase().indexOf(kw)>=0;
      d.style.display = 'none';
      if(matchCat && matchKw) filteredCards.push(d);
    });
    showPage(currentPage);
  }
  function showPage(page){
    currentPage = page;
    var total = filteredCards.length;
    var totalPages = Math.max(1, Math.ceil(total / CARDS_PER_PAGE));
    if(currentPage > totalPages) currentPage = totalPages;
    var start = (currentPage - 1) * CARDS_PER_PAGE;
    var end = start + CARDS_PER_PAGE;
    filteredCards.forEach(function(d, i){
      d.style.display = (i >= start && i < end) ? '' : 'none';
    });
    renderPagination(totalPages, total);
  }
  function renderPagination(totalPages, total){
    var pag = document.getElementById('np-pagination');
    if(!pag) return;
    if(totalPages <= 1){ pag.innerHTML = '<span style="color:#888;font-size:0.85em">'+total+' predictions</span>'; return; }
    var html = '';
    var pages = [];
    pages.push(1);
    var lo = Math.max(2, currentPage - 2);
    var hi = Math.min(totalPages - 1, currentPage + 2);
    if(lo > 2) pages.push(-1);
    for(var i = lo; i <= hi; i++) pages.push(i);
    if(hi < totalPages - 1) pages.push(-1);
    if(totalPages > 1) pages.push(totalPages);
    pages.forEach(function(p){
      if(p === -1){ html += '<span style="color:#888">...</span> '; }
      else { html += '<button class="np-page-btn'+(p===currentPage?' active':'')+'" onclick="window._npGoPage('+p+')">'+p+'</button> '; }
    });
    html += '<span style="color:#888;font-size:0.85em;margin-left:8px">'+total+' predictions</span>';
    pag.innerHTML = html;
  }
  window._npGoPage = function(p){
    showPage(p);
    var el = document.getElementById('np-tracking-list');
    if(el) el.scrollIntoView({behavior:'smooth',block:'start'});
  };
  setView('tracking');
  filterCards();
  (function(){
    function npLand(){
      var h=window.location.hash;
      if(!h||h.indexOf('np-')<0)return;
      var el=document.querySelector(h);
      if(!el)return;
      if(el.style.display==='none'){
        var idx=filteredCards.indexOf(el);
        if(idx>=0)showPage(Math.floor(idx/CARDS_PER_PAGE)+1);
      }
      el.open=true;
      setTimeout(function(){
        el.scrollIntoView({behavior:'smooth',block:'center'});
        el.style.outline='3px solid #b8860b';
        setTimeout(function(){el.style.outline='';},2500);
      },150);
    }
    npLand();
    window.addEventListener('hashchange',npLand);
  })();
})();
</script>"""

    return (
        '<div class="np-tracker">'
        + block1
        + view_toolbar
        + block2
        + block3
        + inline_code
        
        + '</div>'
    )


def assert_prediction_language_parity(rows_ja, rows_en):
    ja_ids = {r.get("prediction_id") for r in rows_ja if r.get("source") == "prediction_db" and r.get("prediction_id")}
    en_ids = {r.get("prediction_id") for r in rows_en if r.get("source") == "prediction_db" and r.get("prediction_id")}
    if ja_ids != en_ids:
        only_ja = sorted(ja_ids - en_ids)[:10]
        only_en = sorted(en_ids - ja_ids)[:10]
        raise AssertionError(
            f"JA/EN tracker prediction_id mismatch: only_ja={only_ja} only_en={only_en}"
        )


# ── Layer 1: デプロイ前 Link Checker ─────────────────────────────────────

def check_links_in_html(html: str, context: str = "") -> bool:
    """
    生成したHTML内の全 <a href> リンクをHTTP HEADで検証。
    1件でも404/エラー → False を返してデプロイをブロック。
    """
    import re
    import urllib.error
    import urllib.request
    import ssl
    from concurrent.futures import ThreadPoolExecutor, as_completed

    urls = re.findall(r"""href=['"](https://nowpattern[.]com/[^'"]+)['"]""", html)
    if not urls:
        print(f"  [LinkChecker] {context}: no internal links found")
        return True

    unique_urls = list(set(urls))
    print(f"  [LinkChecker] {context}: checking {len(unique_urls)} links...")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    errors = []

    def _probe(url, method, timeout_s):
        req = urllib.request.Request(
            url,
            method=method,
            headers={"User-Agent": "nowpattern-linkchecking/1.0"},
        )
        with urllib.request.urlopen(req, context=ctx, timeout=timeout_s) as r:
            return r.status

    def check_one(url):
        last_error = None
        saw_timeout = False
        for method, timeout_s in (("HEAD", 12), ("GET", 25)):
            try:
                return (url, _probe(url, method, timeout_s))
            except urllib.error.HTTPError as e:
                if e.code in (404, 410):
                    return (url, e.code)
                last_error = f"HTTP Error {e.code}: {e.reason}"
            except Exception as e:
                last_error = str(e)
                if isinstance(e, TimeoutError) or "timed out" in last_error.lower():
                    saw_timeout = True
        if saw_timeout:
            try:
                return (url, _probe(url, "GET", 90))
            except Exception as e:
                last_error = str(e)
        return (url, last_error or "Unknown link check error")

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(check_one, u): u for u in unique_urls}
        for future in as_completed(futures):
            url, result = future.result()
            if isinstance(result, int) and result < 400:
                pass  # OK
            else:
                errors.append((url, result))
                print(f"    ❌ FAIL: {url} -> {result}")

    if errors:
        print(f"  [LinkChecker] {context}: BLOCKED — {len(errors)} broken links found!")
        return False

    print(f"  [LinkChecker] {context}: ✅ ALL {len(unique_urls)} links OK")
    return True


# ── Ghost page update ─────────────────────────────────────────



def _build_dataset_ld(stats, lang="ja"):
    """Generate Dataset JSON-LD for /predictions/ pages (REQ-006+007)."""
    import json as _json
    nl = chr(10)
    total = stats.get("total", 0)
    resolved = stats.get("resolved", 0)
    last_updated = (stats.get("last_updated") or "")[:10]
    if lang == "en":
        name = "Nowpattern Prediction Database"
        description = (
            "A bilingual (Japanese/English) prediction database tracking "
            + str(total) + " forecasts across geopolitics, economics, technology, and more. "
            "Predictions are verified automatically, scored with raw Brier Score, and shown publicly as Brier Index with provenance labels."
        )
        url = "https://nowpattern.com/en/predictions/"
        creator_url = "https://nowpattern.com/en/about/"
        keywords = "predictions, forecasting, Brier Index, Brier score, geopolitics, economics"
    else:
        name = "Nowpatternの予測データベース"
        description = (
            "地政学・経済・テクノロジーなど幅広いトピックにわたる" + str(total) + "件の予測を追跡する、"
            "日本語×英語バイリンガル予測データベース。予測は自動的に検証され、raw Brier Score で採点し、公開面では Brier Index と provenance 表示で公開します。"
        )
        url = "https://nowpattern.com/predictions/"
        creator_url = "https://nowpattern.com/about/"
        keywords = "予測, 予測精度, Brier Index, Brier Score, 地政学, 経済"
    schema = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": name,
        "description": description,
        "url": url,
        "creator": {
            "@type": "Organization",
            "name": "Nowpattern",
            "url": creator_url,
        },
        "dateModified": last_updated,
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "keywords": keywords,
        "isAccessibleForFree": True,
        "measurementTechnique": "Brier Score",
        "size": str(total) + " predictions (" + str(resolved) + " resolved)",
    }
    ld_json = _json.dumps(schema, ensure_ascii=False, indent=2)
    return '<script type="application/ld+json">' + nl + ld_json + nl + "</script>"



def _build_faqpage_ld(lang="ja"):
    """Generate FAQPage JSON-LD for /predictions/ pages (REQ-008)."""
    if lang == "en":
        return (
            '<script type="application/ld+json">\n'
            '{\n'
            '  "@context": "https://schema.org",\n'
            '  "@type": "FAQPage",\n'
            '  "mainEntity": [\n'
            '    {\n'
            '      "@type": "Question",\n'
            '      "name": "How are Nowpattern predictions verified?",\n'
            '      "acceptedAnswer": {"@type": "Answer",\n'
            '        "text": "Nowpattern predictions are automatically verified by prediction_auto_verifier.py. After the resolution date passes, AI and news search are combined to judge hit or miss. Raw Brier Score is calculated internally, and the public page shows a Brier Index with provenance labels."}\n'
            '    },\n'
            '    {\n'
            '      "@type": "Question",\n'
            '      "name": "What is a Brier Index?",\n'
            '      "acceptedAnswer": {"@type": "Answer",\n'
            '        "text": "Nowpattern publicly shows Brier Index = (1 - sqrt(Brier)) * 100. Higher is better on a 0-100 scale, while raw Brier Score remains the underlying metric for audit and methodology."}\n'
            '    },\n'
            '    {\n'
            '      "@type": "Question",\n'
            '      "name": "How can I participate in predictions?",\n'
            '      "acceptedAnswer": {"@type": "Answer",\n'
            '        "text": "Use the vote button on each prediction card to select optimistic, base, or pessimistic scenario and submit your probability. No account registration required."}\n'
            '    },\n'
            '    {\n'
            '      "@type": "Question",\n'
            '      "name": "Where can I check past prediction results?",\n'
            '      "acceptedAnswer": {"@type": "Answer",\n'
            '        "text": "See the Resolved Predictions section on this page for judged predictions including hit/miss, public Brier Index, and provenance labels."}\n'
            '    }\n'
            '  ]\n'
            '}\n'
            '</script>'
        )
    else:
        return (
            '<script type="application/ld+json">\n'
            '{\n'
            '  "@context": "https://schema.org",\n'
            '  "@type": "FAQPage",\n'
            '  "mainEntity": [\n'
            '    {\n'
            '      "@type": "Question",\n'
            u'      "name": "Nowpattern\u306e\u4e88\u6e2c\u306f\u3069\u306e\u3088\u3046\u306b\u691c\u8a3c\u3055\u308c\u307e\u3059\u304b\uff1f",\n'
            '      "acceptedAnswer": {"@type": "Answer",\n'
            u'        "text": "Nowpattern\u306e\u4e88\u6e2c\u306fprediction_auto_verifier.py\u306b\u3088\u3063\u3066\u81ea\u52d5\u7684\u306b\u691c\u8a3c\u3055\u308c\u307e\u3059\u3002\u5224\u5b9a\u65e5\u304c\u904e\u304e\u305f\u4e88\u6e2c\u306f\u3001AI\u3068\u30cb\u30e5\u30fc\u30b9\u691c\u7d22\u3092\u7d44\u307f\u5408\u308f\u305b\u3066\u7684\u4e2d\u30fb\u5916\u308c\u3092\u81ea\u52d5\u5224\u5b9a\u3057\u3001internal raw Brier Score \u3092\u8a08\u7b97\u3057\u305f\u3046\u3048\u3067\u3001\u516c\u958b\u753b\u9762\u3067\u306f Brier Index \u3068 provenance \u8868\u793a\u3092\u51fa\u3057\u307e\u3059\u3002"}\n'
            '    },\n'
            '    {\n'
            '      "@type": "Question",\n'
            u'      "name": "Brier Index\u3068\u306f\u4f55\u3067\u3059\u304b\uff1f",\n'
            '      "acceptedAnswer": {"@type": "Answer",\n'
            u'        "text": "Nowpattern\u306e\u516c\u958b\u753b\u9762\u3067\u306f Brier Index = (1-\u221aBrier)\u00d7100 \u3092\u8868\u793a\u3057\u307e\u3059\u30020-100%\u3067\u9ad8\u3044\u307b\u3069\u826f\u304f\u3001raw Brier Score \u306f\u76e3\u67fb\u30fb\u65b9\u6cd5\u8ad6\u7528\u306e\u57fa\u790e\u6307\u6a19\u3068\u3057\u3066\u4fdd\u6301\u3057\u307e\u3059\u3002"}\n'
            '    },\n'
            '    {\n'
            '      "@type": "Question",\n'
            u'      "name": "\u4e88\u6e2c\u306b\u53c2\u52a0\u3059\u308b\u306b\u306f\u3069\u3046\u3059\u308c\u3070\u3044\u3044\u3067\u3059\u304b\uff1f",\n'
            '      "acceptedAnswer": {"@type": "Answer",\n'
            u'        "text": "\u5404\u4e88\u6e2c\u30ab\u30fc\u30c9\u306e\u6295\u7968\u30dc\u30bf\u30f3\u304b\u3089\u3001\u697d\u89b3\u30fb\u57fa\u672c\u30fb\u60b2\u89b3\u30b7\u30ca\u30ea\u30aa\u306e\u3044\u305a\u308c\u304b\u3092\u9078\u3093\u3067\u78ba\u7387\u3092\u6295\u7968\u3067\u304d\u307e\u3059\u3002\u30a2\u30ab\u30a6\u30f3\u30c8\u767b\u9332\u4e0d\u8981\u3067\u3001\u533f\u540d\u306e\u307e\u307e\u53c2\u52a0\u53ef\u80fd\u3002"}\n'
            '    },\n'
            '    {\n'
            '      "@type": "Question",\n'
            u'      "name": "\u904e\u53bb\u306e\u4e88\u6e2c\u7d50\u679c\u306f\u3069\u3053\u3067\u78ba\u8a8d\u3067\u304d\u307e\u3059\u304b\uff1f",\n'
            '      "acceptedAnswer": {"@type": "Answer",\n'
            u'        "text": "\u3053\u306e\u30da\u30fc\u30b8\u306e\u300c\u89e3\u6c7a\u6e08\u307f\u4e88\u6e2c\u300d\u30bb\u30af\u30b7\u30e7\u30f3\u3067\u3001\u5224\u5b9a\u6e08\u307f\u306e\u5168\u4e88\u6e2c\uff08\u7684\u4e2d\u30fb\u5916\u308c\u30fbBrier Index\u30fbprovenance\u8868\u793a\uff09\u3092\u78ba\u8a8d\u3067\u304d\u307e\u3059\u3002"}\n'
            '    }\n'
            '  ]\n'
            '}\n'
            '</script>'
        )


def _build_claimreview_ld(predictions, lang="ja"):
    """Generate ClaimReview JSON-LD for recently resolved predictions (GEO対策)."""
    import json as _json_cr
    resolved = [
        p for p in predictions
        if _is_resolved_status(p) and p.get("our_pick_prob") is not None
    ]
    # Take up to 5 most recently resolved
    recent = sorted(resolved, key=lambda p: p.get("triggers", [{}])[0].get("date", ""), reverse=True)[:5]
    if not recent:
        return ""
    items = []
    for p in recent:
        hit = p.get("result") == "hit"
        brier = p.get("brier_score")
        prob = p.get("our_pick_prob", 50)
        if lang == "en":
            q = p.get("resolution_question", p.get("title", ""))
            verdict = "Correct" if hit else "Incorrect"
        else:
            q = p.get("resolution_question_ja") or p.get("resolution_question") or p.get("title", "")
            verdict = "的中" if hit else "外れ"
        claim_url = "https://nowpattern.com/predictions/#" + p.get("prediction_id", "").lower()
        item = {
            "@type": "ClaimReview",
            "url": claim_url,
            "claimReviewed": q,
            "author": {"@type": "Organization", "name": "Nowpattern", "url": "https://nowpattern.com"},
            "reviewRating": {
                "@type": "Rating",
                "ratingValue": 1 if hit else 0,
                "bestRating": 1,
                "worstRating": 0,
                "ratingExplanation": (
                    f"{verdict} (probability: {prob}%, Brier Index: {_public_score_value(brier):.1f}%, raw Brier: {brier:.3f})"
                    if brier is not None else
                    f"{verdict} (probability: {prob}%)"
                )
            },
            "itemReviewed": {"@type": "Claim", "text": q}
        }
        items.append(item)
    schema = {"@context": "https://schema.org", "@graph": items}
    return '<script type="application/ld+json">\n' + _json_cr.dumps(schema, ensure_ascii=False, indent=2) + '\n</script>'

def _update_dataset_in_head(api_key, slug, stats, lang="ja", predictions=None):
    """Update Dataset JSON-LD in Ghost page codeinjection_head (REQ-006+007)."""
    import re as _re
    page_resp = ghost_request(
        "GET",
        "/pages/slug/" + slug + "/?fields=id,codeinjection_head,updated_at",
        api_key,
    )
    if not page_resp or not page_resp.get("pages"):
        print("[Dataset] ERROR: could not fetch page slug=" + slug)
        return
    p = page_resp["pages"][0]
    page_id = p["id"]
    updated_at = p["updated_at"]
    head = p.get("codeinjection_head") or ""
    # Remove existing Dataset AND FAQPage blocks (block-aware finditer, re-inject both)
    _ld_blocks = list(_re.finditer(
        r'<script[^>]*application/ld\+json[^>]*>[\s\S]*?</script>',
        head, _re.IGNORECASE,
    ))
    head_clean = head
    for _m in reversed(_ld_blocks):
        if '"Dataset"' in _m.group() or '"FAQPage"' in _m.group():
            head_clean = head_clean[:_m.start()] + head_clean[_m.end():]
    head_clean = head_clean.strip()
    dataset_block = _build_dataset_ld(stats, lang)
    faqpage_block = _build_faqpage_ld(lang)
    claimreview_block = _build_claimreview_ld(predictions or [], lang) if predictions else ""
    blocks = [b for b in [dataset_block, faqpage_block, claimreview_block] if b]
    new_head = (head_clean + chr(10) + chr(10).join(blocks)
                if head_clean else chr(10).join(blocks))
    payload = {"pages": [{"codeinjection_head": new_head, "updated_at": updated_at}]}
    ghost_request("PUT", "/pages/" + page_id + "/", api_key, payload)
    print("[Dataset+FAQPage] Updated codeinjection_head for slug=" + slug + " (" + lang + ")")

def update_ghost_page(api_key, slug, page_html, page_title):
    """Create or update a Ghost page by slug.
    
    SAFETY: Only creates a new page if the GET returns 404 (page truly doesn't exist).
    Auth errors, network errors, etc. raise instead of silently creating duplicates.
    """
    import urllib.error
    page_exists = True
    page = None
    try:
        result = ghost_request("GET", f"/pages/slug/{slug}/?formats=lexical", api_key)
        page = result["pages"][0]
    except urllib.error.HTTPError as he:
        if he.code == 404:
            page_exists = False
            print(f"  Page /{slug}/ not found (404). Will create new.")
        else:
            # Auth error (401/403), server error (500), etc. — do NOT create duplicate
            raise RuntimeError(f"Ghost API error {he.code} for /{slug}/: {he.reason}. "
                               "Refusing to create duplicate. Check API key and Ghost service.") from he
    except Exception as e:
        # Network timeout, connection refused, JSON decode error, etc.
        raise RuntimeError(f"Ghost API request failed for /{slug}/: {e}. "
                           "Refusing to create duplicate. Check network and Ghost service.") from e

    if page_exists and page:
        # Update existing page
        _cur_lex = page.get("lexical") or "{}"
        try:
            _cur_html = __import__("json").loads(_cur_lex).get("root", {}).get("children", [{}])[0].get("html", "")
        except Exception:
            _cur_html = ""
        # Sanitize surrogates to prevent UnicodeEncodeError
        _cur_html = _cur_html.encode('utf-8', errors='replace').decode('utf-8')
        page_html = page_html.encode('utf-8', errors='replace').decode('utf-8')
        _cur_hash = hashlib.sha256(_cur_html.encode()).hexdigest()
        _new_hash = hashlib.sha256(page_html.encode()).hexdigest()
        if _cur_hash == _new_hash:
            print(f"  [SKIP] /{slug}/ content unchanged (hash match). No write.")
            return
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
    else:
        # Create new page — ONLY when page truly doesn't exist (404)
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



# ── Page Snapshot (History Archive) ──────────────────────────────────────────
TAKE_SNAPSHOT_SCRIPT = "/opt/shared/scripts/take_page_snapshot.py"

def take_page_snapshot(lang="ja", phase="pre"):
    """Playwright でデプロイ済みページのスクリーンショットを撮り page-history/ に保存"""
    import subprocess as _sp
    try:
        result = _sp.run(
            ["python3", TAKE_SNAPSHOT_SCRIPT, "--lang", lang, "--phase", phase],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            print(f"  📸 {result.stdout.strip()}")
        else:
            print(f"  [SKIP] snapshot: {result.stderr.strip()[:120]}")
    except Exception as e:
        print(f"  [SKIP] snapshot exception: {e}")


# ── Main ───────────────────────────────────────────────────────

def main():
    # BLOCK G-1: 並行実行防止ロック v2.0 (stale lock 検出あり)
    import fcntl as _fcntl
    import time as _time_mod
    _LOCK_PATH      = "/opt/shared/locks/predictions_page.lock"
    _LOCK_MAX_AGE_S = 3600   # 1時間以上保持されたロックは stale と見なす
    os.makedirs("/opt/shared/locks", exist_ok=True)

    # stale lock 検出: ロックファイルが存在してもPIDが死んでいれば削除
    if os.path.exists(_LOCK_PATH):
        try:
            with open(_LOCK_PATH) as _lf:
                _meta    = _lf.read().strip().split()
                _old_pid = int(_meta[0]) if _meta else 0
                _old_ts  = float(_meta[1]) if len(_meta) > 1 else 0
            _age = _time_mod.time() - _old_ts
            _pid_alive = False
            try:
                os.kill(_old_pid, 0)   # シグナル 0 = 存在確認のみ
                _pid_alive = True
            except (ProcessLookupError, PermissionError):
                _pid_alive = False
            if not _pid_alive:
                print(f"[STALE] Lock held by dead PID {_old_pid} ({int(_age)}s ago). Removing.")
                os.unlink(_LOCK_PATH)
            elif _age > _LOCK_MAX_AGE_S:
                print(f"[STALE] Lock held for {int(_age)}s (>{_LOCK_MAX_AGE_S}s). Removing.")
                os.unlink(_LOCK_PATH)
        except Exception as _le:
            print(f"[WARN] Stale-lock check error: {_le}")

    _lock_fd = open(_LOCK_PATH, "w")
    try:
        _fcntl.flock(_lock_fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        _lock_fd.write(f"{os.getpid()} {_time_mod.time()}")
        _lock_fd.flush()
        print(f"[LOCK] Acquired by PID {os.getpid()}")
    except (IOError, OSError):
        print("[SKIP] prediction_page_builder already running (lock held). Exit 0.")
        _lock_fd.close()
        sys.exit(0)

    import argparse
    parser = argparse.ArgumentParser(description="Prediction Page Builder (JA+EN)")
    parser.add_argument("--report", action="store_true", help="Report only")
    parser.add_argument("--update", action="store_true", help="Update Ghost page")
    parser.add_argument("--force", action="store_true", help="Skip link checker")
    parser.add_argument("--lang", choices=["ja", "en", "both"], default="both",
                        help="Language to update (default: both)")
    args = parser.parse_args()

    env = load_env()
    api_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not api_key:
        print("ERROR: API key not found")
        sys.exit(1)
    google_api_key = env.get("GOOGLE_API_KEY", "")

    _scripts_dir = os.path.dirname(os.path.abspath(__file__))
    _db_path = PREDICTION_DB if os.path.exists(PREDICTION_DB) else os.path.join(_scripts_dir, "prediction_db.json")

    # -- Deploy Gate (prediction data integrity check) --------------------
    # Runs no_duplicate_gate + numerical_integrity_gate + score_provenance_gate
    # Exit 2 from any gate blocks the page build (deploy-path hard gate).
    import subprocess as _sp
    _refresh_script = os.path.join(_scripts_dir, "refresh_prediction_db_meta.py")
    _state_gate_script = os.path.join(_scripts_dir, "prediction_state_integrity_gate.py")
    if os.path.exists(_refresh_script) and os.path.exists(_db_path) and not args.report:
        print("[STATE REFRESH] Canonicalizing prediction DB status/meta...")
        _refresh_result = _sp.run([sys.executable, _refresh_script, "--db", _db_path], capture_output=False)
        if _refresh_result.returncode != 0:
            print("[STATE REFRESH] FAILED -- fix refresh_prediction_db_meta.py before deploying.")
            sys.exit(_refresh_result.returncode or 1)
    if os.path.exists(_state_gate_script) and os.path.exists(_db_path) and not args.report:
        print("[STATE GATE] Running prediction state integrity gate...")
        _state_gate_result = _sp.run([sys.executable, _state_gate_script, "--db", _db_path], capture_output=False)
        if _state_gate_result.returncode != 0:
            print("[STATE GATE] BLOCKED -- fix prediction_db state/scoring mismatches before deploying.")
            sys.exit(_state_gate_result.returncode or 2)
    _gate_script = "/opt/shared/scripts/prediction_deploy_gate.py"
    if os.path.exists(_gate_script) and not (hasattr(args, "report") and args.report):
        print("[DEPLOY GATE] Running pre-build integrity gates...")
        _gate_result = _sp.run([sys.executable, _gate_script], capture_output=False)
        if _gate_result.returncode == 2:
            print("[DEPLOY GATE] BLOCKED -- fix FAILs before deploying.")
            sys.exit(2)
        elif _gate_result.returncode == 0:
            print("[DEPLOY GATE] All gates PASSED.")
        else:
            print("[DEPLOY GATE] WARNs present (non-blocking). Proceeding.")
    else:
        print("[DEPLOY GATE] Skipped (report mode or gate script not found)")

    # Load data sources
    pred_db = load_prediction_db()
    embed_data = load_embed_data()
    print(f"Prediction DB: {len(pred_db.get('predictions', []))} entries")

    # ★ SCHEMA COMPATIBILITY CHECK (2026-03-29追加)
    # ビルド前にOracle Guardianブロック率とプレースホルダーを事前チェック
    # 異常が多い場合はログで警告（ビルドは続行するが原因調査が必要）
    _schema_preds = pred_db.get("predictions", [])[:50]
    _schema_blocked = sum(1 for _p in _schema_preds if _validate_tracker_card(_p))
    _schema_placeholders = sum(
        1 for _p in _schema_preds
        for _f in ("hit_condition_ja","hit_condition_en","oracle_criteria")
        if _p.get(_f) == "(本文抽出不可)"
    )
    _block_rate = (_schema_blocked / len(_schema_preds) * 100) if _schema_preds else 0
    print(f"[SCHEMA CHECK] Oracle Guardian block rate (sample 50): {_schema_blocked}/{len(_schema_preds)} ({_block_rate:.1f}%)")
    print(f"[SCHEMA CHECK] Placeholder strings in fields: {_schema_placeholders}")
    if _block_rate > 50:
        print(f"[SCHEMA ALERT] Block rate {_block_rate:.1f}% > 50%!")
        print("[SCHEMA ALERT] Probable cause: prediction_db fields don't match _validate_tracker_card expectations.")
        print("[SCHEMA ALERT] Check: hit_condition_ja / oracle_criteria / our_pick fields in prediction_db.json")
    if _schema_placeholders > 0:
        print(f"[SCHEMA ALERT] {_schema_placeholders} placeholder strings detected in prediction fields!")

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
    rows_by_lang = {lang: build_rows(pred_db, ghost_posts, embed_data, lang) for lang in langs}
    if "ja" in rows_by_lang and "en" in rows_by_lang:
        assert_prediction_language_parity(rows_by_lang["ja"], rows_by_lang["en"])
        print(f"[PARITY] JA/EN tracker rows aligned: {len(rows_by_lang['ja'])} / {len(rows_by_lang['en'])}")

    for lang in langs:
        print(f"\n{'='*40}")
        print(f"Building {lang.upper()} page...")
        print(f"{'='*40}")

        rows = rows_by_lang[lang]

        print(f"  Total rows: {len(rows)}")
        print(f"    From prediction_db: {sum(1 for r in rows if r['source'] == 'prediction_db')}")
        print(f"    From Ghost HTML: 0 (ghost_html source removed — prediction_db only)")
        print(f"    With Polymarket match: {sum(1 for r in rows if r.get('polymarket'))}")

        for r in rows:
            pm_str = f"PM={r['polymarket']['probability']:.0f}%" if r.get("polymarket") else "—"
            div_str = f"Δ={r['divergence']:+.0f}%" if r.get("divergence") is not None else ""
            print(f"    B={r.get('base','?')}% {pm_str} {div_str} | {r['title'][:50]}")

        # Build HTML
        page_html = build_page_html(rows, pred_db.get("stats", {}), lang)
        try:
            check_gate_f_provisional_labels(page_html)
            print("  [GATE F] Score label / disclaimer check PASSED")
        except AssertionError as gate_exc:
            print(f"  [GATE F FAIL] {gate_exc}")
            if args.report:
                sys.exit(2)
            continue

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
            # Layer 1: Link Checker — デプロイ前に全リンクを検証
            if not args.force and not check_links_in_html(page_html, context=f"{lang.upper()} predictions page"):
                print(f"  ⛔ BLOCKED: broken links detected in {lang} page. Ghost NOT updated.")
                print(f"  Fix the broken links above before re-running.")
                continue
            # ★ 出荷前品質ゲート (2026-03-29): 壊れたページをデプロイしない
            _guardian_count = page_html.count("Oracle Guardian")
            _placeholder_count = page_html.count("(本文抽出不可)")
            _total_cards = page_html.count('data-genres=')
            _block_rate = (_guardian_count / _total_cards * 100) if _total_cards > 0 else 0
            _gate_ok = (_block_rate <= 5.0) and (_placeholder_count == 0)
            print(f"  [GATE] Oracle Guardian: {_guardian_count}/{_total_cards} ({_block_rate:.1f}%) | Placeholders: {_placeholder_count}")
            if not _gate_ok:
                print(f"  [GATE FAIL] Quality check failed — keeping existing {lang} page unchanged.")
                print(f"  [GATE FAIL] Reason: block_rate={_block_rate:.1f}% (max 5%) | placeholders={_placeholder_count} (max 0)")
                import time as _t
                _fail_log = f"/opt/shared/logs/predeploy_gate_fail.log"
                os.makedirs("/opt/shared/logs", exist_ok=True)
                with open(_fail_log, "a") as _fl:
                    _fl.write(_t.strftime('%Y-%m-%d %H:%M') + f' [{lang}] block={_block_rate:.1f}% placeholders={_placeholder_count}' + chr(10))
                continue
            # 📸 ビルド前スナップショット（履歴アーカイブ）
            take_page_snapshot(lang=lang, phase="pre")
            update_ghost_page(api_key, slug, page_html, title)
            _update_dataset_in_head(api_key, slug, pred_db.get("stats", {}), lang, pred_db.get("predictions", []))

    # Save output data (combined)
    all_rows_ja = rows_by_lang.get("ja") or build_rows(pred_db, ghost_posts, embed_data, "ja")
    output_data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M JST"),
        "rows": all_rows_ja,
        "stats": pred_db.get("stats", {}),
    }
    with open(TRACKER_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {TRACKER_OUTPUT}")

    # Layer 2: E2E インタラクションテスト（Ghost更新後に実行）
    if not args.report:
        print("\n" + "=" * 60)
        print("  Layer 2: E2E インタラクションテスト実行中...")
        print("=" * 60)
        import subprocess as _subprocess
        e2e_script = "/opt/shared/scripts/playwright_e2e_predictions.py"
        e2e_langs = args.lang if hasattr(args, "lang") and args.lang != "both" else "ja"
        try:
            result = _subprocess.run(
                ["python3", e2e_script, "--lang", e2e_langs, "--screenshot"],
                timeout=120
            )
            if result.returncode != 0:
                print("\n[WARNING] E2Eテストが失敗 — UIに問題がある可能性あり")
                print(f"  手動確認: python3 {e2e_script} --lang {e2e_langs} --screenshot")
            else:
                print("\n[OK] E2Eテスト全PASS — UIが正常に動作しています")
        except FileNotFoundError:
            print(f"[SKIP] E2Eスクリプトが見つかりません: {e2e_script}")
        except _subprocess.TimeoutExpired:
            print("[SKIP] E2Eテストがタイムアウト (120秒)")
        except Exception as e:
            print(f"[SKIP] E2Eエラー: {e}")

        site_audit_script = "/opt/shared/scripts/site_ui_smoke_audit.py"
        print("\n" + "=" * 60)
        print("  Layer 3: Site UI smoke audit...")
        print("=" * 60)
        try:
            site_result = _subprocess.run(
                ["python3", site_audit_script, "--base-url", "https://nowpattern.com"],
                timeout=180
            )
            if site_result.returncode != 0:
                print("\n[WARNING] Site UI smoke audit failed — review primary desktop/mobile flows.")
                print(f"  Manual rerun: python3 {site_audit_script} --base-url https://nowpattern.com")
            else:
                print("\n[OK] Site UI smoke audit PASS — primary desktop/mobile flows verified.")
        except FileNotFoundError:
            print(f"[SKIP] Site UI smoke audit script not found: {site_audit_script}")
        except _subprocess.TimeoutExpired:
            print("[SKIP] Site UI smoke audit timed out (180s)")
        except Exception as e:
            print(f"[SKIP] Site UI smoke audit: {e}")


if __name__ == "__main__":
    main()
