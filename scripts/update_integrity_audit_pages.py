#!/usr/bin/env python3
"""Refresh public integrity-audit pages with stable, non-hardcoded copy."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import jwt
import requests
import urllib3

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
    token = jwt.encode(
        payload,
        bytes.fromhex(secret),
        algorithm="HS256",
        headers={"kid": key_id},
    )
    return token if isinstance(token, str) else token.decode("utf-8")


def ghost_get(token: str, endpoint: str) -> dict:
    response = requests.get(
        f"{GHOST_ADMIN_API}/{endpoint}",
        headers={"Authorization": f"Ghost {token}"},
        verify=False,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_page(token: str, slug: str) -> dict:
    payload = ghost_get(token, f"pages/slug/{slug}/?formats=html,lexical")
    pages = payload.get("pages") or []
    if not pages:
        raise RuntimeError(f"Ghost page not found for slug={slug}")
    return pages[0]


def update_page_html(token: str, page: dict, html: str) -> None:
    body = {
        "pages": [
            {
                "id": page["id"],
                "title": page["title"],
                "slug": page["slug"],
                "status": page.get("status", "published"),
                "updated_at": page["updated_at"],
                "html": html,
                "canonical_url": page.get("canonical_url") or "",
                "codeinjection_head": page.get("codeinjection_head") or "",
            }
        ]
    }
    response = requests.put(
        f"{GHOST_ADMIN_API}/pages/{page['id']}/?source=html",
        headers={
            "Authorization": f"Ghost {token}",
            "Content-Type": "application/json",
        },
        json=body,
        verify=False,
        timeout=30,
    )
    response.raise_for_status()


def common_style() -> str:
    return """
<style>
.np-integrity-intro{margin:0 0 1.25rem;color:#334155;line-height:1.8}
.np-integrity-note{margin:0 0 1.25rem;color:#475569;line-height:1.8}
.np-tier-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin:24px 0 28px}
.np-tier-card{border:1px solid #e2e8f0;border-radius:20px;padding:18px 18px 16px;background:#fff;box-shadow:0 10px 30px rgba(15,23,42,.04)}
.np-tier-card h3{margin:0 0 6px;font-size:1.2rem;line-height:1.35}
.np-tier-card .np-tier-sub{display:block;font-size:.95rem;font-weight:700}
.np-tier-card dl{margin:14px 0 0}
.np-tier-card dt{font-size:.8rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#64748b;margin:0 0 4px}
.np-tier-card dd{margin:0 0 12px;color:#0f172a;line-height:1.65}
.np-tier-card dd:last-child{margin-bottom:0}
.np-tier-provisional h3{color:#64748b}
.np-tier-migrated h3{color:#d97706}
.np-tier-verified h3{color:#15803d}
.np-tier-excluded h3{color:#dc2626}
@media (max-width: 640px){
  .np-tier-grid{grid-template-columns:1fr}
  .np-tier-card{padding:16px}
}
</style>
""".strip()


def build_ja_html() -> str:
    return f"""\
<h2>予測記録の整合性とは</h2>
<p>このページは、予測スコアの<strong>証拠レベル</strong>と<strong>改ざん耐性</strong>の考え方を説明するためのページです。各予測がどの証拠条件を満たしているかで、表示ティアが決まります。</p>
<p>公開画面のラベルは、記録状態・検証状態・暗号学的証跡に応じて自動で切り替わります。重要なのは、各予測がどこまで検証可能かです。</p>

<!--kg-card-begin: html-->
{common_style()}
<div class="np-tier-grid">
  <section class="np-tier-card np-tier-provisional">
    <h3>PROVISIONAL<span class="np-tier-sub">暫定計算値</span></h3>
    <dl>
      <dt>意味</dt>
      <dd>公開中の標準表示です。スコアは計算できますが、完全な証跡がまだ揃っていない段階を示します。</dd>
      <dt>適用条件</dt>
      <dd>確率記録や検証証跡がまだ移行途中、または確認待ちの予測。</dd>
      <dt>公開表示</dt>
      <dd>予測ページやスコア表示では provisional ラベルで案内します。</dd>
    </dl>
  </section>

  <section class="np-tier-card np-tier-migrated">
    <h3>MIGRATED_OFFICIAL<span class="np-tier-sub">移行確定スコア</span></h3>
    <dl>
      <dt>意味</dt>
      <dd>既存予測に対して、後追いで整合性証跡を補強し、検証可能性を高めた段階です。</dd>
      <dt>適用条件</dt>
      <dd>レジャー記録と OTS 確認が揃い、移行済みスコアとして扱えること。</dd>
      <dt>公開表示</dt>
      <dd>必要条件を満たした予測だけが自動でこのティアに昇格します。</dd>
    </dl>
  </section>

  <section class="np-tier-card np-tier-verified">
    <h3>VERIFIED_OFFICIAL<span class="np-tier-sub">公式確定スコア</span></h3>
    <dl>
      <dt>意味</dt>
      <dd>公開前ハッシュと後続の検証証跡が一貫して追える、もっとも強い証拠レベルです。</dd>
      <dt>適用条件</dt>
      <dd>公開前に SHA-256 で固定され、その後の OTS 確認まで end-to-end で追跡できること。</dd>
      <dt>公開表示</dt>
      <dd>条件を満たした予測のみが verified として表示されます。</dd>
    </dl>
  </section>

  <section class="np-tier-card np-tier-excluded">
    <h3>NOT_SCORABLE<span class="np-tier-sub">採点対象外</span></h3>
    <dl>
      <dt>意味</dt>
      <dd>解決条件を満たす客観証拠が得られず、採点対象から外すケースです。</dd>
      <dt>適用条件</dt>
      <dd>後から見ても一貫した resolution が不可能と判断されること。</dd>
      <dt>公開表示</dt>
      <dd>Brier 集計には含めず、採点対象外として扱います。</dd>
    </dl>
  </section>
</div>
<!--kg-card-end: html-->

<h2>なぜ現在は「暫定」表示が中心なのか</h2>
<p>公開済みの予測には、証跡が十分に揃っているものと、まだ確認途中のものが混在します。そのため、必要条件が揃うまでは provisional と表示します。</p>
<p>逆に言えば、条件が満たされたものだけが MIGRATED_OFFICIAL や VERIFIED_OFFICIAL に昇格します。ここで見るべきなのは、各予測の証拠条件です。</p>

<p><a href="/predictions/">予測トラッカー</a> | <a href="/scoring-guide/">スコアリングガイド</a></p>
"""


def build_en_html() -> str:
    return f"""\
<h2>What This Page Explains</h2>
<p>This page explains the <strong>evidence tiers</strong> behind Nowpattern scores and the <strong>tamper-resistance model</strong> behind prediction records.</p>
<p>Public labels change automatically as record state, verification state, and cryptographic evidence change. What matters here is which proof conditions each prediction satisfies.</p>

<!--kg-card-begin: html-->
{common_style()}
<div class="np-tier-grid">
  <section class="np-tier-card np-tier-provisional">
    <h3>PROVISIONAL</h3>
    <dl>
      <dt>Meaning</dt>
      <dd>The default public label. A score can be computed, but the strongest evidence chain is not yet complete.</dd>
      <dt>When It Applies</dt>
      <dd>Predictions whose probability record or verification trail is still being migrated or confirmed.</dd>
      <dt>Public Display</dt>
      <dd>Shown as provisional on score displays until stronger proof conditions are met.</dd>
    </dl>
  </section>

  <section class="np-tier-card np-tier-migrated">
    <h3>MIGRATED_OFFICIAL</h3>
    <dl>
      <dt>Meaning</dt>
      <dd>A legacy prediction whose evidence trail has been strengthened after the original publication flow.</dd>
      <dt>When It Applies</dt>
      <dd>Ledger continuity and OTS confirmation are both available for migrated evidence.</dd>
      <dt>Public Display</dt>
      <dd>Only predictions that satisfy the migration requirements are upgraded automatically.</dd>
    </dl>
  </section>

  <section class="np-tier-card np-tier-verified">
    <h3>VERIFIED_OFFICIAL</h3>
    <dl>
      <dt>Meaning</dt>
      <dd>The strongest evidence tier, where pre-publication hashing and later verification remain traceable end to end.</dd>
      <dt>When It Applies</dt>
      <dd>The prediction is locked with SHA-256 before publication and later confirmed through the OTS path.</dd>
      <dt>Public Display</dt>
      <dd>Only predictions that satisfy the full proof chain are shown as verified.</dd>
    </dl>
  </section>

  <section class="np-tier-card np-tier-excluded">
    <h3>NOT_SCORABLE</h3>
    <dl>
      <dt>Meaning</dt>
      <dd>The question cannot be scored consistently with objective evidence.</dd>
      <dt>When It Applies</dt>
      <dd>A stable resolution cannot be established even after review.</dd>
      <dt>Public Display</dt>
      <dd>Excluded from Brier aggregation and shown as non-scorable.</dd>
    </dl>
  </section>
</div>
<!--kg-card-end: html-->

<h2>Why Provisional Labels Still Exist</h2>
<p>The public corpus contains a mix of predictions with stronger proof chains and predictions that are still moving through verification. That is why provisional remains the safe default until the required evidence is complete.</p>
<p>When the required conditions are met, individual predictions upgrade to MIGRATED_OFFICIAL or VERIFIED_OFFICIAL automatically. The key question is which proof conditions each prediction satisfies.</p>

<p><a href="/en/predictions/">Prediction Tracker</a> | <a href="/en/scoring-guide/">Scoring Guide</a></p>
"""


def main() -> int:
    token = get_ghost_token()
    pages = {
        "integrity-audit": build_ja_html(),
        "en-integrity-audit": build_en_html(),
    }
    for slug, html in pages.items():
        page = fetch_page(token, slug)
        update_page_html(token, page, html)
        print(f"UPDATED {slug}")
        token = get_ghost_token()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
