#!/usr/bin/env python3
"""
update_predictions_page.py — /predictions/ ページ自動更新

prediction_db.json の内容を読み込み、Ghost の /predictions/ ページを
Brier Score・予測一覧・精度統計のHTMLテーブルで自動更新する。

使い方:
  python3 update_predictions_page.py             # 通常実行
  python3 update_predictions_page.py --dry-run    # HTML確認のみ

cron: prediction_verifier.py の直後に実行
  5 6 * * * source /opt/cron-env.sh && python3 /opt/shared/scripts/update_predictions_page.py >> /opt/shared/reports/predictions_page.log 2>&1
"""

import json
import os
import sys
import hashlib
import hmac
import time
import argparse
from datetime import datetime, timezone

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PREDICTION_DB = "/opt/shared/scripts/prediction_db.json"
GHOST_URL = os.environ.get("GHOST_URL", "https://nowpattern.com")
GHOST_ADMIN_API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
PREDICTIONS_SLUG = "predictions"


def make_ghost_jwt(admin_api_key):
    """Ghost Admin API用JWT生成"""
    key_id, secret_hex = admin_api_key.split(":")
    secret = bytes.fromhex(secret_hex)
    iat = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iat": iat, "exp": iat + 300, "aud": "/admin/"}

    import base64
    def b64url(data):
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    h = b64url(json.dumps(header, separators=(",", ":")).encode())
    p = b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig_input = f"{h}.{p}".encode()
    sig = hmac.new(secret, sig_input, hashlib.sha256).digest()
    return f"{h}.{p}.{b64url(sig)}"


def load_prediction_db():
    if os.path.exists(PREDICTION_DB):
        with open(PREDICTION_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"predictions": [], "stats": {}}


def brier_rating(score):
    """Brier Scoreから評価ラベルを返す"""
    if score is None:
        return "—"
    if score < 0.10:
        return "🏆 Exceptional"
    if score < 0.15:
        return "🏆 Superforecaster"
    if score < 0.20:
        return "⭐ Excellent"
    if score < 0.25:
        return "✅ Above Average"
    return "📊 Average"


def generate_html(db):
    """prediction_db.json からHTMLを生成"""
    preds = db.get("predictions", [])
    stats = db.get("stats", {})

    total = stats.get("total", len(preds))
    resolved = stats.get("resolved", 0)
    open_count = stats.get("open", total - resolved)
    avg_brier = stats.get("avg_brier_score")

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # --- Header ---
    html = f"""<div class="np-predictions-page">

<div class="np-predictions-header" style="background:#0a0a23;color:#fff;padding:30px;border-radius:12px;margin-bottom:30px;">
  <h2 style="color:#00d4ff;margin:0 0 10px 0;">📊 Nowpattern Prediction Track Record</h2>
  <p style="color:#ccc;margin:0;">Last updated: {now_str}</p>
</div>

<div class="np-stats-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-bottom:30px;">
  <div style="background:#1a1a3e;padding:20px;border-radius:8px;text-align:center;">
    <div style="font-size:2em;color:#00d4ff;font-weight:bold;">{total}</div>
    <div style="color:#aaa;">Total Predictions</div>
  </div>
  <div style="background:#1a1a3e;padding:20px;border-radius:8px;text-align:center;">
    <div style="font-size:2em;color:#4CAF50;font-weight:bold;">{resolved}</div>
    <div style="color:#aaa;">Verified</div>
  </div>
  <div style="background:#1a1a3e;padding:20px;border-radius:8px;text-align:center;">
    <div style="font-size:2em;color:#FF9800;font-weight:bold;">{open_count}</div>
    <div style="color:#aaa;">Open</div>
  </div>
  <div style="background:#1a1a3e;padding:20px;border-radius:8px;text-align:center;">
    <div style="font-size:2em;color:#E040FB;font-weight:bold;">{f'{avg_brier:.3f}' if avg_brier is not None else '—'}</div>
    <div style="color:#aaa;">Avg Brier Score</div>
    <div style="color:#888;font-size:0.8em;">{brier_rating(avg_brier)}</div>
  </div>
</div>

<div style="background:#111;padding:15px;border-radius:8px;margin-bottom:30px;border-left:4px solid #00d4ff;">
  <p style="margin:0;color:#ccc;">
    <strong style="color:#00d4ff;">Brier Score</strong>: 0 = perfect prediction, 0.25 = no skill.
    Superforecasters average 0.15. Lower is better.
  </p>
</div>
"""

    # --- Resolved Predictions ---
    resolved_preds = [p for p in preds if p.get("status") == "resolved"]
    if resolved_preds:
        html += """
<h3 style="color:#4CAF50;">✅ Verified Predictions</h3>
<table style="width:100%;border-collapse:collapse;margin-bottom:30px;">
<thead>
<tr style="background:#1a1a3e;color:#fff;">
  <th style="padding:10px;text-align:left;">ID</th>
  <th style="padding:10px;text-align:left;">Article</th>
  <th style="padding:10px;text-align:center;">Outcome</th>
  <th style="padding:10px;text-align:center;">Brier</th>
  <th style="padding:10px;text-align:center;">Rating</th>
</tr>
</thead>
<tbody>
"""
        for p in sorted(resolved_preds, key=lambda x: x.get("resolved_at", ""), reverse=True):
            pid = p.get("prediction_id", "")
            title = p.get("article_title", "")[:60]
            outcome = p.get("outcome", "—")
            brier = p.get("brier_score")
            brier_str = f"{brier:.3f}" if brier is not None else "—"
            rating = brier_rating(brier)
            ghost_url = p.get("ghost_url", "")
            title_link = f'<a href="{ghost_url}" style="color:#00d4ff;">{title}</a>' if ghost_url else title

            html += f"""<tr style="border-bottom:1px solid #333;">
  <td style="padding:8px;color:#888;font-family:monospace;">{pid}</td>
  <td style="padding:8px;">{title_link}</td>
  <td style="padding:8px;text-align:center;">{outcome}</td>
  <td style="padding:8px;text-align:center;font-weight:bold;">{brier_str}</td>
  <td style="padding:8px;text-align:center;">{rating}</td>
</tr>
"""
        html += "</tbody></table>\n"

    # --- Open Predictions ---
    open_preds = [p for p in preds if p.get("status") == "open"]
    if open_preds:
        html += """
<h3 style="color:#FF9800;">⏳ Open Predictions (Awaiting Verification)</h3>
<table style="width:100%;border-collapse:collapse;margin-bottom:30px;">
<thead>
<tr style="background:#1a1a3e;color:#fff;">
  <th style="padding:10px;text-align:left;">ID</th>
  <th style="padding:10px;text-align:left;">Article</th>
  <th style="padding:10px;text-align:left;">Scenarios</th>
  <th style="padding:10px;text-align:left;">Next Trigger</th>
</tr>
</thead>
<tbody>
"""
        for p in open_preds:
            pid = p.get("prediction_id", "")
            title = p.get("article_title", "")[:50]
            ghost_url = p.get("ghost_url", "")
            title_link = f'<a href="{ghost_url}" style="color:#00d4ff;">{title}</a>' if ghost_url else title

            # Scenarios
            scenarios = p.get("scenarios", [])
            scenario_html = ""
            for s in scenarios:
                label = s.get("label", "")
                prob = s.get("probability", 0)
                prob_pct = f"{prob*100:.0f}%" if prob <= 1 else f"{prob:.0f}%"
                scenario_html += f"<div>{label}: {prob_pct}</div>"

            # Next trigger
            trigger_text = p.get("open_loop_trigger", "")
            if not trigger_text:
                triggers = p.get("triggers", [])
                if triggers:
                    t = triggers[0]
                    trigger_text = f"{t.get('name', '')} ({t.get('date', '')})"

            if len(trigger_text) > 60:
                trigger_text = trigger_text[:57] + "..."

            html += f"""<tr style="border-bottom:1px solid #333;">
  <td style="padding:8px;color:#888;font-family:monospace;">{pid}</td>
  <td style="padding:8px;">{title_link}</td>
  <td style="padding:8px;font-size:0.85em;">{scenario_html}</td>
  <td style="padding:8px;font-size:0.85em;color:#FF9800;">{trigger_text}</td>
</tr>
"""
        html += "</tbody></table>\n"

    # --- Methodology ---
    html += """
<div style="background:#111;padding:20px;border-radius:8px;margin-top:30px;">
  <h3 style="color:#00d4ff;margin-top:0;">📐 Methodology</h3>
  <ul style="color:#ccc;">
    <li><strong>Framework</strong>: 16 structural dynamics × 13 genre categories (Nowpattern Taxonomy v3.0)</li>
    <li><strong>Scoring</strong>: Brier Score — measures calibration of probabilistic forecasts</li>
    <li><strong>Verification</strong>: AI-assisted (Gemini 2.5 Pro + Google Search) with manual review</li>
    <li><strong>Immutability</strong>: All predictions are timestamped on Ghost CMS at publication time</li>
    <li><strong>Transparency</strong>: Every prediction links to its original analysis article</li>
  </ul>
</div>

</div><!-- .np-predictions-page -->
"""
    return html


def update_ghost_page(html, dry_run=False):
    """Ghost の /predictions/ ページを更新"""
    if not GHOST_ADMIN_API_KEY:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not set")
        return False

    jwt = make_ghost_jwt(GHOST_ADMIN_API_KEY)
    headers = {"Authorization": f"Ghost {jwt}"}

    # Step 1: 既存ページを取得
    url = f"{GHOST_URL}/ghost/api/admin/pages/slug/{PREDICTIONS_SLUG}/"
    resp = requests.get(url, headers=headers, verify=False, timeout=30)

    if resp.status_code != 200:
        print(f"ERROR: Could not fetch /predictions/ page: HTTP {resp.status_code}")
        print(f"  Response: {resp.text[:200]}")
        return False

    page_data = resp.json().get("pages", [{}])[0]
    page_id = page_data.get("id", "")
    updated_at = page_data.get("updated_at", "")

    if not page_id:
        print("ERROR: /predictions/ page not found")
        return False

    if dry_run:
        print(f"[DRY-RUN] Would update page {page_id} ({PREDICTIONS_SLUG})")
        print(f"  HTML length: {len(html):,} chars")
        return True

    # Step 2: ページ更新（?source=html でHTML→lexical自動変換）
    put_url = f"{GHOST_URL}/ghost/api/admin/pages/{page_id}/?source=html"
    payload = {
        "pages": [{
            "html": html,
            "updated_at": updated_at,
        }]
    }

    put_resp = requests.put(put_url, headers=headers, json=payload, verify=False, timeout=30)

    if put_resp.status_code == 200:
        print(f"✅ /predictions/ page updated successfully")
        return True
    else:
        print(f"ERROR: Failed to update page: HTTP {put_resp.status_code}")
        print(f"  Response: {put_resp.text[:300]}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Update /predictions/ page from prediction_db.json")
    parser.add_argument("--dry-run", action="store_true", help="Generate HTML without updating Ghost")
    args = parser.parse_args()

    db = load_prediction_db()
    preds = db.get("predictions", [])

    if not preds:
        print("No predictions in database. Skipping page update.")
        return

    print(f"📊 Generating predictions page: {len(preds)} predictions")
    html = generate_html(db)

    if args.dry_run:
        print(f"\n--- Generated HTML ({len(html):,} chars) ---")
        print(html[:500])
        print("...")
        return

    success = update_ghost_page(html, dry_run=args.dry_run)
    if success:
        print(f"Done. {len(preds)} predictions rendered on /predictions/")


if __name__ == "__main__":
    main()
