#!/usr/bin/env python3
"""Refresh public About pages from canonical product copy and release snapshot."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import jwt
import requests
import urllib3

from canonical_public_lexicon import (
    get_about_copy,
    get_brand_copy,
    get_public_metric_bundle,
    get_tracker_copy,
    load_release_snapshot,
)

urllib3.disable_warnings()

GHOST_ADMIN_API = "https://nowpattern.com/ghost/api/admin"
CRON_ENV_FILE = "/opt/cron-env.sh"


def load_cron_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not os.path.exists(CRON_ENV_FILE):
        return env
    with open(CRON_ENV_FILE, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("export "):
                continue
            key, _, value = line[7:].strip().partition("=")
            env[key] = value.strip().strip('"').strip("'")
    return env


def get_ghost_token() -> str:
    env = load_cron_env()
    key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY") or os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not key:
        raise ValueError("NOWPATTERN_GHOST_ADMIN_API_KEY not found in cron-env.sh or environment")
    key_id, secret = key.split(":")
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {"iat": now, "exp": now + 300, "aud": "/admin/"}
    token = jwt.encode(payload, bytes.fromhex(secret), algorithm="HS256", headers={"kid": key_id})
    return token if isinstance(token, str) else token.decode("utf-8")


def ghost_get(token: str, endpoint: str) -> dict:
    response = requests.get(
        f"{GHOST_ADMIN_API}/{endpoint}",
        headers={"Authorization": f"Ghost {token}"},
        verify=False,
        timeout=90,
    )
    response.raise_for_status()
    return response.json()


def fetch_page(token: str, slug: str) -> dict:
    payload = ghost_get(token, f"pages/slug/{slug}/?formats=html,lexical")
    pages = payload.get("pages") or []
    if not pages:
        raise RuntimeError(f"Ghost page not found for slug={slug}")
    return pages[0]


def update_page(token: str, page: dict, *, title: str, html: str, meta_title: str, meta_description: str) -> None:
    body = {
        "pages": [
            {
                "id": page["id"],
                "title": title,
                "slug": page["slug"],
                "status": page.get("status", "published"),
                "updated_at": page["updated_at"],
                "html": html,
                "custom_excerpt": meta_description,
                "meta_title": meta_title,
                "meta_description": meta_description,
                "og_title": meta_title,
                "og_description": meta_description,
                "twitter_title": meta_title,
                "twitter_description": meta_description,
                "canonical_url": page.get("canonical_url") or "",
                "codeinjection_head": page.get("codeinjection_head") or "",
            }
        ]
    }
    response = requests.put(
        f"{GHOST_ADMIN_API}/pages/{page['id']}/?source=html",
        headers={"Authorization": f"Ghost {token}", "Content-Type": "application/json"},
        json=body,
        verify=False,
        timeout=90,
    )
    response.raise_for_status()


def common_style() -> str:
    return """
<style>
.np-about-intro{margin:0 0 1.1rem;color:#334155;line-height:1.85}
.np-about-sub{display:inline-block;padding:4px 10px;border-radius:999px;background:#f1f5f9;color:#475569;font-size:.82rem;font-weight:700;letter-spacing:.02em}
.np-about-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:24px 0 28px}
.np-about-card{border:1px solid #e2e8f0;border-radius:20px;padding:18px 18px 16px;background:#fff;box-shadow:0 10px 30px rgba(15,23,42,.04)}
.np-about-card .np-label{display:block;font-size:.82rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#64748b}
.np-about-card .np-value{display:block;font-size:2rem;line-height:1.1;font-weight:800;color:#0f172a;margin-top:8px}
.np-about-card .np-note{display:block;font-size:.88rem;line-height:1.65;color:#475569;margin-top:10px}
.np-state-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin:18px 0 28px}
.np-state-card{border:1px solid #e2e8f0;border-radius:18px;padding:16px;background:#fff}
.np-state-badge{display:inline-block;padding:4px 10px;border-radius:999px;background:#0f172a;color:#fff;font-size:.82rem;font-weight:700}
.np-state-note{margin:10px 0 0;color:#475569;line-height:1.7}
.np-about-links{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}
.np-about-links a{display:inline-flex;align-items:center;gap:8px;padding:10px 14px;border-radius:999px;background:#fff7e6;border:1px solid #f6d58a;color:#8a6408;text-decoration:none;font-weight:700}
@media (max-width: 640px){
  .np-about-grid,.np-state-grid{grid-template-columns:1fr}
  .np-about-card,.np-state-card{padding:16px}
}
</style>
""".strip()


def metric_card(label: str, value: str, note: str) -> str:
    return (
        '<section class="np-about-card">'
        f'<span class="np-label">{label}</span>'
        f'<span class="np-value">{value}</span>'
        f'<span class="np-note">{note}</span>'
        '</section>'
    )


def state_card(label: str, note: str) -> str:
    return (
        '<section class="np-state-card">'
        f'<span class="np-state-badge">{label}</span>'
        f'<p class="np-state-note">{note}</p>'
        '</section>'
    )


def build_about_html(lang: str) -> str:
    about = get_about_copy(lang)
    brand = get_brand_copy(lang)
    tracker = get_tracker_copy(lang)
    metrics = get_public_metric_bundle(lang, load_release_snapshot())

    if lang == "ja":
        state_notes = [
            (tracker["view_in_play"], "イベントがまだ進行中で、確率つきの予測を継続して追っている状態です。"),
            (tracker["view_awaiting"], "イベントは発生済みですが、証拠確認と判定記録の最終反映を待っている状態です。"),
            (tracker["view_resolved"], "判定が確定し、結果とスコアを公開できる状態です。"),
        ]
    else:
        state_notes = [
            (tracker["view_in_play"], "The event is still unfolding and the forecast remains live."),
            (tracker["view_awaiting"], "The event has happened, but the evidence check and resolution record are still being finalized."),
            (tracker["view_resolved"], "The forecast has a finalized outcome and can be scored publicly."),
        ]

    metric_cards = "".join(
        [
            metric_card(about["metric_registered"], f"{metrics['registered_forecasts']:,}", about["card_registered_note"]),
            metric_card(about["metric_public_cards"], f"{metrics['public_tracker_cards']:,}", about["card_public_note"]),
            metric_card(about["metric_resolved_cards"], f"{metrics['resolved_public_cards']:,}", about["card_resolved_note"]),
            metric_card(about["metric_operating_since"], str(metrics["operating_since"]), about["card_operating_note"]),
        ]
    )
    state_cards = "".join(state_card(label, note) for label, note in state_notes)
    footer_links = "".join(f'<a href="{href}">{label}</a>' for label, href in about["footer_links"])
    points = "".join(f"<li>{point}</li>" for point in about["section_how_points"])

    return f"""\
{common_style()}
<p><span class="np-about-sub">{brand["oracle_subtitle"]}</span></p>
<h2>{about["hero_title"]}</h2>
<p class="np-about-intro">{about["hero_intro"]}</p>
<p class="np-about-intro">{about["hero_body"]}</p>

<!--kg-card-begin: html-->
<div class="np-about-grid">
  {metric_cards}
</div>
<!--kg-card-end: html-->

<h3>{about["section_how_title"]}</h3>
<ul>
  {points}
</ul>

<div class="np-state-grid">
  {state_cards}
</div>

<div class="np-about-links">
  {footer_links}
</div>
"""


def main() -> int:
    token = get_ghost_token()
    pages = {
        "about": "ja",
        "en-about": "en",
    }
    for slug, lang in pages.items():
        page = fetch_page(token, slug)
        brand = get_brand_copy(lang)
        html = build_about_html(lang)
        update_page(
            token,
            page,
            title=brand["about_title"],
            html=html,
            meta_title=brand["about_meta_title"],
            meta_description=brand["about_meta_description"],
        )
        print(f"updated:{slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
