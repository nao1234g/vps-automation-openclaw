#!/usr/bin/env python3
"""
Phase 7: 読者向けJA/EN公開ルールページ作成
- 3テーマ × 2言語 = 6 Ghost pages
- routes.yaml への追加
- Caddyfile へのEN redirects追加
- Ghost / Caddy 自動リロード

Pages:
  JA: /forecast-rules/   /scoring-guide/   /integrity-audit/
  EN: /en/forecast-rules/ /en/scoring-guide/ /en/integrity-audit/
"""
import json
import jwt
import time
import os
import sys
import re
import requests
import subprocess
import urllib3
from datetime import datetime, timezone

urllib3.disable_warnings()

GHOST_ADMIN_API = "https://nowpattern.com/ghost/api/admin"
CRON_ENV_FILE   = "/opt/cron-env.sh"
ROUTES_YAML     = "/var/www/nowpattern/content/settings/routes.yaml"
CADDYFILE       = "/etc/caddy/Caddyfile"

def load_cron_env() -> dict:
    env = {}
    try:
        for line in open(CRON_ENV_FILE):
            if line.startswith("export "):
                k, _, v = line[7:].strip().partition("=")
                env[k] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env

# ── Ghost Admin API Helper ────────────────────────────────────────────────────

def get_ghost_token() -> str:
    env = load_cron_env()
    key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not key:
        raise ValueError("NOWPATTERN_GHOST_ADMIN_API_KEY not found in cron-env.sh")
    key_id, secret = key.split(":")
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {"iat": now, "exp": now + 300, "aud": "/admin/"}
    token = jwt.encode(payload, bytes.fromhex(secret), algorithm="HS256",
                       headers={"kid": key_id})
    return token if isinstance(token, str) else token.decode("utf-8")

def ghost_get(endpoint: str) -> dict:
    token = get_ghost_token()
    r = requests.get(f"{GHOST_ADMIN_API}/{endpoint}",
                     headers={"Authorization": f"Ghost {token}"},
                     verify=False, timeout=30)
    return r.json()

def ghost_create_page(token: str, slug: str, title: str, html: str,
                      tags: list, canonical_url: str = "", codeinjection_head: str = "") -> dict:
    data = {
        "pages": [{
            "title": title,
            "slug": slug,
            "status": "published",
            "html": html,
            "tags": [{"name": t} for t in tags],
        }]
    }
    if canonical_url:
        data["pages"][0]["canonical_url"] = canonical_url
    if codeinjection_head:
        data["pages"][0]["codeinjection_head"] = codeinjection_head

    r = requests.post(f"{GHOST_ADMIN_API}/pages/?source=html",
                      headers={"Authorization": f"Ghost {token}",
                               "Content-Type": "application/json"},
                      json=data, verify=False, timeout=30)
    return r.json()

def ghost_page_exists(slug: str) -> bool:
    resp = ghost_get(f"pages/slug/{slug}/")
    return "pages" in resp and len(resp["pages"]) > 0

def ghost_delete_page_by_slug(token: str, slug: str):
    resp = ghost_get(f"pages/slug/{slug}/")
    if "pages" not in resp or len(resp["pages"]) == 0:
        return False
    page_id = resp["pages"][0]["id"]
    r = requests.delete(f"{GHOST_ADMIN_API}/pages/{page_id}/",
                        headers={"Authorization": f"Ghost {token}"},
                        verify=False, timeout=30)
    return r.status_code == 204


# ── Page Content ─────────────────────────────────────────────────────────────

PAGES = [
    # ── 予測ルール (JA) ────────────────────────────────────────────────────
    {
        "slug": "forecast-rules",
        "route": "/forecast-rules/",
        "title": "予測ルール — Nowpatternの予測はこう作られる",
        "lang": "ja",
        "canonical": "",
        "hreflang": '<link rel="alternate" hreflang="ja" href="https://nowpattern.com/forecast-rules/">\n<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/forecast-rules/">\n<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/forecast-rules/">',
        "tags": ["nowpattern", "lang-ja"],
        "html": """\
<h2>予測とは何か</h2>
<p>Nowpatternの予測（オラクル宣言）は、記事が公開される時点で<strong>未来の特定の出来事について検証可能な確率を宣言する</strong>ものです。</p>
<p>予測は「感想」や「見通し」ではありません。事後的に正しかったかどうかを数値で検証できる形式でのみ記録されます。</p>

<h2>予測の3要素</h2>
<ul>
  <li><strong>判定質問</strong> — YES/NOで判定できる具体的な質問（例：「2026年末までにビットコインは10万ドルを超えるか？」）</li>
  <li><strong>確率</strong> — 0〜100%でNowpatternが割り当てた信頼度（例：65%）</li>
  <li><strong>的中条件</strong> — 「YESとみなす具体的な基準」を明記（例：「CMCの終値が$100,000以上で30日間継続」）</li>
</ul>

<h2>オラクル宣言のルール</h2>
<ol>
  <li><strong>事前記録</strong> — 予測は結果判明前に登録する。事後修正は禁止。</li>
  <li><strong>検証可能性</strong> — 判定質問は誰もが独立して検証できる基準に基づく。</li>
  <li><strong>全件公開</strong> — 的中・外れを問わず全ての予測を公開する。都合の良い予測だけを見せることは絶対にしない。</li>
  <li><strong>タイムスタンプ</strong> — 全予測はOTS（OpenTimestamps）でビットコインブロックチェーンに刻印する。</li>
</ol>

<h2>予測のステータス</h2>
<table>
  <thead><tr><th>ステータス</th><th>意味</th></tr></thead>
  <tbody>
    <tr><td>OPEN（追跡中）</td><td>まだ判定日が来ていない予測</td></tr>
    <tr><td>AWAITING EVIDENCE（証拠収集中）</td><td>判定日を過ぎ、結果の確認中</td></tr>
    <tr><td>RESOLVED（解決済み）</td><td>HIT（的中）またはMISS（外れ）が確定</td></tr>
    <tr><td>EXPIRED（期限切れ）</td><td>判定基準を満たす証拠が得られなかった</td></tr>
  </tbody>
</table>

<p>→ スコアリングの詳細は <a href="/scoring-guide/">スコアリングガイド</a> をご覧ください。</p>
<p>→ 記録の改ざん防止については <a href="/integrity-audit/">整合性・監査ページ</a> をご覧ください。</p>
""",
    },

    # ── Forecast Rules (EN) ───────────────────────────────────────────────
    {
        "slug": "en-forecast-rules",
        "route": "/en/forecast-rules/",
        "title": "Forecast Rules — How Nowpattern Makes Predictions",
        "lang": "en",
        "canonical": "https://nowpattern.com/en/forecast-rules/",
        "hreflang": '<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/forecast-rules/">\n<link rel="alternate" hreflang="ja" href="https://nowpattern.com/forecast-rules/">\n<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/forecast-rules/">',
        "tags": ["nowpattern", "lang-en"],
        "html": """\
<h2>What Is a Prediction?</h2>
<p>A Nowpattern prediction (Oracle Statement) is a <strong>verifiable probability claim about a future event</strong>, recorded before the outcome is known.</p>
<p>These are not opinions or outlooks. Every prediction is recorded in a form that can be objectively verified after the fact.</p>

<h2>The Three Elements of a Prediction</h2>
<ul>
  <li><strong>Resolution Question</strong> — A specific YES/NO question (e.g., "Will Bitcoin exceed $100,000 by end of 2026?")</li>
  <li><strong>Probability</strong> — A confidence level from 0–100% assigned by Nowpattern (e.g., 65%)</li>
  <li><strong>Hit Condition</strong> — The exact criteria for a YES verdict (e.g., "CMC closing price ≥$100,000 sustained for 30 days")</li>
</ul>

<h2>Oracle Statement Rules</h2>
<ol>
  <li><strong>Pre-registration</strong> — Predictions are recorded before the outcome is known. Retroactive changes are prohibited.</li>
  <li><strong>Verifiability</strong> — Resolution criteria must be independently verifiable by anyone.</li>
  <li><strong>Full disclosure</strong> — All predictions are published, both hits and misses. We never cherry-pick results.</li>
  <li><strong>Timestamping</strong> — All predictions are anchored via OTS (OpenTimestamps) on the Bitcoin blockchain.</li>
</ol>

<h2>Prediction Status</h2>
<table>
  <thead><tr><th>Status</th><th>Meaning</th></tr></thead>
  <tbody>
    <tr><td>OPEN (Tracking)</td><td>Resolution date has not yet arrived</td></tr>
    <tr><td>AWAITING EVIDENCE</td><td>Resolution date passed; verifying outcome</td></tr>
    <tr><td>RESOLVED</td><td>Verdict confirmed: HIT or MISS</td></tr>
    <tr><td>EXPIRED</td><td>No qualifying evidence found within the grace period</td></tr>
  </tbody>
</table>

<p>→ See <a href="/en/scoring-guide/">Scoring Guide</a> for how accuracy is measured.</p>
<p>→ See <a href="/en/integrity-audit/">Integrity &amp; Audit</a> for tamper-proof records.</p>
""",
    },

    # ── スコアリングガイド (JA) ────────────────────────────────────────────
    {
        "slug": "scoring-guide",
        "route": "/scoring-guide/",
        "title": "スコアリングガイド — ブライアースコアと予測精度の測り方",
        "lang": "ja",
        "canonical": "",
        "hreflang": '<link rel="alternate" hreflang="ja" href="https://nowpattern.com/scoring-guide/">\n<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/scoring-guide/">\n<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/scoring-guide/">',
        "tags": ["nowpattern", "lang-ja"],
        "html": """\
<h2>HIT（的中）とMISS（外れ）</h2>
<p>予測が解決すると、的中条件に基づき自動的に判定されます。</p>
<ul>
  <li><strong>HIT</strong> — 的中条件が満たされた（YESが証明された）</li>
  <li><strong>MISS</strong> — 的中条件が満たされなかった（NOが証明された、または期限切れ）</li>
</ul>

<h2>ブライアースコア（Brier Score）とは</h2>
<p>単純な的中率（正解率%）では「70%の確率でYES」と「99%の確率でYES」が同じヒットとして扱われてしまいます。</p>
<p>ブライアースコアは<strong>確率の精度（キャリブレーション）</strong>を測ります。</p>

<h3>計算式</h3>
<p><code>BS = (予測確率 - 実際の結果)²</code></p>
<p>ここで「実際の結果」はHIT=1、MISS=0です。</p>

<h3>スコアの解釈</h3>
<table>
  <thead><tr><th>Brier Score</th><th>評価</th></tr></thead>
  <tbody>
    <tr><td>0.00</td><td>完璧（起こったことに100%、起きなかったことに0%を割り当てた）</td></tr>
    <tr><td>0.00 – 0.10</td><td>EXCELLENT（非常に優秀）</td></tr>
    <tr><td>0.10 – 0.20</td><td>GOOD（良好）</td></tr>
    <tr><td>0.20 – 0.30</td><td>FAIR（平均的）</td></tr>
    <tr><td>0.25</td><td>ベースライン（常に50%と予測した場合）</td></tr>
    <tr><td>0.30以上</td><td>POOR（改善が必要）</td></tr>
  </tbody>
</table>

<h3>具体例</h3>
<ul>
  <li>予測確率70%、結果HIT → BS = (0.70 - 1)² = 0.09（良好）</li>
  <li>予測確率70%、結果MISS → BS = (0.70 - 0)² = 0.49（過信）</li>
  <li>予測確率50%、結果HIT → BS = (0.50 - 1)² = 0.25（ベースライン）</li>
</ul>

<h2>なぜブライアースコアが重要か</h2>
<p>単純な正解率では「強気な予測者」と「慎重な予測者」を公平に比較できません。ブライアースコアは<strong>確率の過信（overconfidence）</strong>を罰します。</p>
<p>Nowpatternの目標はBrier Score平均 <strong>0.20以下</strong>（GOOD水準）です。現在の平均スコアは <a href="/predictions/">予測ページ</a> でリアルタイムに確認できます。</p>
""",
    },

    # ── Scoring Guide (EN) ────────────────────────────────────────────────
    {
        "slug": "en-scoring-guide",
        "route": "/en/scoring-guide/",
        "title": "Scoring Guide — Brier Score and Prediction Accuracy",
        "lang": "en",
        "canonical": "https://nowpattern.com/en/scoring-guide/",
        "hreflang": '<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/scoring-guide/">\n<link rel="alternate" hreflang="ja" href="https://nowpattern.com/scoring-guide/">\n<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/scoring-guide/">',
        "tags": ["nowpattern", "lang-en"],
        "html": """\
<h2>HIT and MISS</h2>
<p>When a prediction resolves, it is automatically judged against the hit condition.</p>
<ul>
  <li><strong>HIT</strong> — The hit condition was met (YES confirmed)</li>
  <li><strong>MISS</strong> — The hit condition was not met (NO confirmed, or expired)</li>
</ul>

<h2>What Is the Brier Score?</h2>
<p>A simple accuracy rate (% correct) treats "70% confidence YES" and "99% confidence YES" as the same hit. That's not useful.</p>
<p>The Brier Score measures <strong>probability calibration</strong> — how well your confidence levels match reality.</p>

<h3>Formula</h3>
<p><code>BS = (forecast probability − actual outcome)²</code></p>
<p>Where actual outcome = 1 for HIT, 0 for MISS.</p>

<h3>Interpreting the Score</h3>
<table>
  <thead><tr><th>Brier Score</th><th>Rating</th></tr></thead>
  <tbody>
    <tr><td>0.00</td><td>Perfect (100% on hits, 0% on misses)</td></tr>
    <tr><td>0.00 – 0.10</td><td>EXCELLENT</td></tr>
    <tr><td>0.10 – 0.20</td><td>GOOD</td></tr>
    <tr><td>0.20 – 0.30</td><td>FAIR</td></tr>
    <tr><td>0.25</td><td>Baseline (always predicting 50%)</td></tr>
    <tr><td>0.30+</td><td>POOR — needs improvement</td></tr>
  </tbody>
</table>

<h3>Examples</h3>
<ul>
  <li>Forecast 70%, result HIT → BS = (0.70 − 1)² = 0.09 (good)</li>
  <li>Forecast 70%, result MISS → BS = (0.70 − 0)² = 0.49 (overconfident)</li>
  <li>Forecast 50%, result HIT → BS = (0.50 − 1)² = 0.25 (baseline)</li>
</ul>

<h2>Why Brier Score Matters</h2>
<p>Simple accuracy rates cannot distinguish between a bold predictor and a careful one. Brier Score <strong>penalizes overconfidence</strong>.</p>
<p>Nowpattern's target is an average Brier Score below <strong>0.20</strong> (GOOD level). The live average is shown on the <a href="/en/predictions/">Predictions page</a>.</p>
""",
    },

    # ── 整合性・監査 (JA) ────────────────────────────────────────────────
    {
        "slug": "integrity-audit",
        "route": "/integrity-audit/",
        "title": "整合性・監査 — 予測記録はなぜ改ざんできないのか",
        "lang": "ja",
        "canonical": "",
        "hreflang": '<link rel="alternate" hreflang="ja" href="https://nowpattern.com/integrity-audit/">\n<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/integrity-audit/">\n<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/integrity-audit/">',
        "tags": ["nowpattern", "lang-ja"],
        "html": """\
<h2>予測の誠実性とは</h2>
<p>予測プラットフォームへの信頼は「記録が改ざんされていない」という確証から生まれます。Nowpatternは技術的に改ざんを検知・防止する仕組みを持っています。</p>

<h2>3層の改ざん防止システム</h2>

<h3>1. 予測マニフェスト（SHA-256ハッシュ）</h3>
<p>全1,115件の予測は、登録時に <strong>コアフィールド（予測内容・確率・的中条件）のSHA-256ハッシュ</strong> を計算し、<code>prediction_manifest.json</code> に記録されます。</p>
<p>毎日自動的に現在のデータベースとマニフェストを照合し、ハッシュが一致しない予測を即座に検知・通知します。</p>

<h3>2. イベント台帳（Append-Only Ledger）</h3>
<p>全ての予測操作（登録・更新・解決）は <code>prediction_ledger.jsonl</code> にNDJSON形式で追記されます。</p>
<p>このファイルは<strong>追記専用（append-only）</strong>です。既存の行を変更・削除することは構造的に禁止されています。</p>
<pre><code>{"ts":"2026-03-01T10:00:00Z","event":"REGISTERED","prediction_id":"NP-2026-0001","hash":"769672ae...","actor":"system"}
{"ts":"2026-03-15T14:30:00Z","event":"RESOLVED","prediction_id":"NP-2026-0001","verdict":"HIT","actor":"auto_verifier"}</code></pre>

<h3>3. OTSタイムスタンプ（ビットコインブロックチェーン）</h3>
<p>予測データベースのハッシュは定期的に <strong>OpenTimestamps (OTS)</strong> によってビットコインブロックチェーンに刻印されます。</p>
<p>ビットコインのブロックチェーンは書き換え不可能なため、「この時点でこのデータが存在した」という事実が永続的に証明されます。</p>

<h2>自動整合性チェック</h2>
<p>毎日午前3時（JST）に整合性チェックが自動実行され、問題が検知された場合は即座に通知されます。</p>

<p>→ 予測の見方は <a href="/forecast-rules/">予測ルール</a> をご覧ください。</p>
<p>→ スコアリングの詳細は <a href="/scoring-guide/">スコアリングガイド</a> をご覧ください。</p>
""",
    },

    # ── Integrity & Audit (EN) ────────────────────────────────────────────
    {
        "slug": "en-integrity-audit",
        "route": "/en/integrity-audit/",
        "title": "Integrity & Audit — Why Prediction Records Cannot Be Altered",
        "lang": "en",
        "canonical": "https://nowpattern.com/en/integrity-audit/",
        "hreflang": '<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/integrity-audit/">\n<link rel="alternate" hreflang="ja" href="https://nowpattern.com/integrity-audit/">\n<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/integrity-audit/">',
        "tags": ["nowpattern", "lang-en"],
        "html": """\
<h2>What Is Prediction Integrity?</h2>
<p>Trust in a prediction platform comes from certainty that records have not been altered. Nowpattern uses a three-layer technical system to detect and prevent tampering.</p>

<h2>Three-Layer Tamper-Prevention System</h2>

<h3>1. Prediction Manifest (SHA-256 Hashes)</h3>
<p>All 1,115 predictions have their <strong>core fields (content, probability, hit condition) hashed with SHA-256</strong> and stored in <code>prediction_manifest.json</code> at registration time.</p>
<p>An automated daily process compares the live database against the manifest. Any hash mismatch triggers an immediate alert.</p>

<h3>2. Event Ledger (Append-Only)</h3>
<p>Every prediction operation (registration, update, resolution) is appended to <code>prediction_ledger.jsonl</code> in NDJSON format.</p>
<p>This file is <strong>append-only by design</strong>. Modifying or deleting existing lines is structurally prohibited.</p>
<pre><code>{"ts":"2026-03-01T10:00:00Z","event":"REGISTERED","prediction_id":"NP-2026-0001","hash":"769672ae...","actor":"system"}
{"ts":"2026-03-15T14:30:00Z","event":"RESOLVED","prediction_id":"NP-2026-0001","verdict":"HIT","actor":"auto_verifier"}</code></pre>

<h3>3. OTS Timestamps (Bitcoin Blockchain)</h3>
<p>Hashes of the prediction database are periodically anchored on the <strong>Bitcoin blockchain via OpenTimestamps (OTS)</strong>.</p>
<p>Because the Bitcoin blockchain is immutable, this creates a permanent proof that "this data existed at this exact time."</p>

<h2>Automated Integrity Checks</h2>
<p>An integrity check runs automatically every day at 03:00 JST. Any tampering detected triggers an immediate notification.</p>

<p>→ See <a href="/en/forecast-rules/">Forecast Rules</a> to understand how predictions are made.</p>
<p>→ See <a href="/en/scoring-guide/">Scoring Guide</a> for how accuracy is measured.</p>
""",
    },
]

# ── Routes YAML additions ─────────────────────────────────────────────────────

ROUTES_TO_ADD = """  /forecast-rules/:
    data: page.forecast-rules
    template: page
  /scoring-guide/:
    data: page.scoring-guide
    template: page
  /integrity-audit/:
    data: page.integrity-audit
    template: page
  /en/forecast-rules/:
    data: page.en-forecast-rules
    template: page
  /en/scoring-guide/:
    data: page.en-scoring-guide
    template: page
  /en/integrity-audit/:
    data: page.en-integrity-audit
    template: page
"""

# ── Caddy redirects ───────────────────────────────────────────────────────────

CADDY_REDIRECTS = """
\t# Phase 7: Public rules pages (EN redirects)
\thandle /en/forecast-rules {
\t\tredir /en/forecast-rules /en/forecast-rules/ permanent
\t}
\thandle /en/scoring-guide {
\t\tredir /en/scoring-guide /en/scoring-guide/ permanent
\t}
\thandle /en/integrity-audit {
\t\tredir /en/integrity-audit /en/integrity-audit/ permanent
\t}
"""

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # 1. Ghost pages
    token = get_ghost_token()
    print("=== Creating Ghost Pages ===")
    for page in PAGES:
        slug = page["slug"]
        if ghost_page_exists(slug):
            print(f"  EXISTS: {slug} — deleting and recreating...")
            ghost_delete_page_by_slug(token, slug)
            token = get_ghost_token()  # refresh

        result = ghost_create_page(
            token,
            slug=slug,
            title=page["title"],
            html=page["html"],
            tags=page["tags"],
            canonical_url=page.get("canonical", ""),
            codeinjection_head=page.get("hreflang", ""),
        )
        token = get_ghost_token()

        if "pages" in result:
            pid = result["pages"][0]["id"]
            url = result["pages"][0].get("url", "")
            print(f"  ✅ {slug} → {url} (id: {pid})")
        elif "errors" in result:
            print(f"  ❌ {slug}: {result['errors']}")
        else:
            print(f"  ? {slug}: {result}")

    # 2. Update routes.yaml
    print("\n=== Updating routes.yaml ===")
    with open(ROUTES_YAML, "r") as f:
        routes_content = f.read()

    # Check if already added
    if "/forecast-rules/:" in routes_content:
        print("  routes.yaml already updated — skipping")
    else:
        # Insert after "routes:\n"
        new_content = routes_content.replace(
            "routes:\n",
            "routes:\n" + ROUTES_TO_ADD,
            1
        )
        with open(ROUTES_YAML, "w") as f:
            f.write(new_content)
        print("  Added 6 routes to routes.yaml")

    # 3. Update Caddyfile
    print("\n=== Updating Caddyfile ===")
    with open(CADDYFILE, "r") as f:
        caddy_content = f.read()

    if "/en/forecast-rules" in caddy_content:
        print("  Caddyfile already updated — skipping")
    else:
        # Insert before the EN tag pages block
        insert_before = "\t# EN tag pages"
        if insert_before in caddy_content:
            new_caddy = caddy_content.replace(
                insert_before,
                CADDY_REDIRECTS + "\n" + insert_before,
                1
            )
            with open(CADDYFILE, "w") as f:
                f.write(new_caddy)
            print("  Added EN redirects to Caddyfile")
        else:
            print("  WARNING: Could not find insert point in Caddyfile")

    # 4. Update the "not path" exclusion in Caddyfile
    with open(CADDYFILE, "r") as f:
        caddy_content = f.read()

    old_not_path = "not path /en/about* /en/predictions* /en/tag/* /en/taxonomy* /en/tournament* /en/members* /en/my-predictions*"
    new_not_path = "not path /en/about* /en/predictions* /en/tag/* /en/taxonomy* /en/tournament* /en/members* /en/my-predictions* /en/forecast-rules* /en/scoring-guide* /en/integrity-audit*"

    if old_not_path in caddy_content and new_not_path not in caddy_content:
        caddy_content = caddy_content.replace(old_not_path, new_not_path)
        with open(CADDYFILE, "w") as f:
            f.write(caddy_content)
        print("  Updated 'not path' exclusions in Caddyfile")

    # 5. Reload Ghost and Caddy
    print("\n=== Reloading Services ===")
    r1 = subprocess.run(["systemctl", "restart", "ghost-nowpattern.service"],
                        capture_output=True, text=True)
    print(f"  Ghost restart: {'✅' if r1.returncode == 0 else '❌'} {r1.stderr.strip()[:100]}")
    time.sleep(5)

    r2 = subprocess.run(["caddy", "reload", "--config", CADDYFILE],
                        capture_output=True, text=True)
    print(f"  Caddy reload:  {'✅' if r2.returncode == 0 else '❌'} {r2.stderr.strip()[:100]}")

    # 6. Verify pages are accessible
    print("\n=== Verifying URLs ===")
    time.sleep(3)
    for page in PAGES:
        url = f"https://nowpattern.com{page['route']}"
        try:
            r = requests.get(url, verify=False, timeout=10, allow_redirects=True)
            status = "✅" if r.status_code == 200 else f"❌ {r.status_code}"
            print(f"  {status} {url}")
        except Exception as e:
            print(f"  ❌ {url}: {e}")

    print("\nPhase 7 complete.")


if __name__ == "__main__":
    main()
