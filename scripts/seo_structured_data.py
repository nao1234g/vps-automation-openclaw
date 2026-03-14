#!/usr/bin/env python3
"""
seo_structured_data.py — AI Overviews最適化: Ghost記事にJSON-LD構造化データを自動挿入

Google AI Overviewsに引用される確率を3倍にするための構造化データ戦略:
- Organization schema（サイト全体）
- AnalysisNewsArticle schema（個別記事）
- Dataset schema（/predictions/ページ）
- Author/Person schema（全記事）
- robots.txt AIボット許可設定

使い方:
  python3 seo_structured_data.py --inject-global     # Ghost Code Injectionに組織スキーマ挿入
  python3 seo_structured_data.py --inject-predictions # /predictions/にDatasetスキーマ挿入
  python3 seo_structured_data.py --generate-robots    # robots.txtのAIボット許可設定生成
  python3 seo_structured_data.py --generate-llms-txt  # llms.txt生成
  python3 seo_structured_data.py --report             # 現在の構造化データ状態レポート

cron: 不要（デプロイ時に1回実行、または記事構造変更時に実行）
"""

import json
import os
import sys
import hmac
import hashlib
import base64
import ssl
import urllib.request
from datetime import datetime, timezone

# ── Config ─────────────────────────────────────────────────────
CRON_ENV = "/opt/cron-env.sh"
GHOST_URL = "https://nowpattern.com"
PREDICTION_DB = "/opt/shared/scripts/prediction_db.json"

# ── Ghost API ヘルパー ──────────────────────────────────────────

def _load_env():
    """cron-env.sh から環境変数をロード"""
    env = {}
    if os.path.exists(CRON_ENV):
        with open(CRON_ENV) as f:
            for line in f:
                line = line.strip()
                if line.startswith("export ") and "=" in line:
                    kv = line[7:]
                    k, v = kv.split("=", 1)
                    env[k] = v.strip("\"'")
                elif "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k] = v.strip("\"'")
    return env


def _ghost_jwt(api_key: str) -> str:
    """Ghost Admin API JWT トークン生成"""
    key_id, secret_hex = api_key.split(":")
    secret = bytes.fromhex(secret_hex)
    iat = int(datetime.now(timezone.utc).timestamp())
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT", "kid": key_id}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"iat": iat, "exp": iat + 300, "aud": "/admin/"}).encode()
    ).rstrip(b"=").decode()
    sig_input = f"{header}.{payload}".encode()
    sig = base64.urlsafe_b64encode(
        hmac.new(secret, sig_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"


def _ghost_api(method, endpoint, api_key, data=None):
    """Ghost Admin API リクエスト"""
    token = _ghost_jwt(api_key)
    url = f"{GHOST_URL}/ghost/api/admin/{endpoint}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Ghost {token}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read())


# ── JSON-LD テンプレート ────────────────────────────────────────

def generate_organization_jsonld() -> str:
    """Organization + WebSite の JSON-LD（Ghost Header Code Injection用）"""
    schema = [
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Nowpattern",
            "url": "https://nowpattern.com",
            "logo": "https://nowpattern.com/content/images/nowpattern-logo.png",
            "description": "Prediction Oracle platform — pattern-driven news analysis with verified Brier Score track records. The only bilingual (JA/EN) prediction platform combining deep force-dynamics analysis with automated accuracy tracking.",
            "sameAs": [
                "https://x.com/nowpattern"
            ],
            "knowsAbout": [
                "Geopolitical analysis",
                "Prediction markets",
                "Brier Score forecasting",
                "Pattern dynamics analysis",
                "News analysis"
            ],
            "founder": {
                "@type": "Person",
                "name": "Naoto"
            }
        },
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Nowpattern",
            "url": "https://nowpattern.com",
            "description": "予測オラクルプラットフォーム — 力学分析 × 検証可能な予測 × Brier Scoreトラックレコード",
            "inLanguage": ["ja", "en"],
            "potentialAction": {
                "@type": "SearchAction",
                "target": "https://nowpattern.com/?s={search_term_string}",
                "query-input": "required name=search_term_string"
            }
        }
    ]
    return f'<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'


def generate_predictions_dataset_jsonld() -> str:
    """/predictions/ ページ用の Dataset JSON-LD"""
    # prediction_db.json の統計を読む
    stats = {"total": 0, "resolved": 0, "avg_brier_score": None}
    if os.path.exists(PREDICTION_DB):
        with open(PREDICTION_DB, "r", encoding="utf-8") as f:
            data = json.load(f)
            stats = data.get("stats", stats)

    description = (
        f"Nowpattern Prediction Tracker — {stats['total']} geopolitical and technology predictions "
        f"with {stats['resolved']} resolved and verified using Brier Scores. "
    )
    if stats.get("avg_brier_score"):
        description += f"Current average Brier Score: {stats['avg_brier_score']}. "
    description += "Updated daily. Predictions cover economics, geopolitics, technology, crypto, and energy."

    schema = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Nowpattern Prediction Tracker",
        "description": description,
        "url": "https://nowpattern.com/predictions/",
        "temporalCoverage": "2026/..",
        "license": "https://creativecommons.org/licenses/by-nc/4.0/",
        "creator": {
            "@type": "Organization",
            "name": "Nowpattern",
            "url": "https://nowpattern.com"
        },
        "distribution": {
            "@type": "DataDownload",
            "encodingFormat": "text/html",
            "contentUrl": "https://nowpattern.com/predictions/"
        },
        "variableMeasured": [
            {
                "@type": "PropertyValue",
                "name": "Brier Score",
                "description": "Prediction accuracy metric (0 = perfect, 0.25 = random)"
            },
            {
                "@type": "PropertyValue",
                "name": "Total Predictions",
                "value": str(stats["total"])
            },
            {
                "@type": "PropertyValue",
                "name": "Resolved Predictions",
                "value": str(stats["resolved"])
            }
        ]
    }
    return f'<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'


def generate_article_jsonld_template() -> str:
    """記事用のAnalysisNewsArticle JSON-LDテンプレート（Ghost Post Code Injection用）"""
    template = {
        "@context": "https://schema.org",
        "@type": "AnalysisNewsArticle",
        "author": {
            "@type": "Organization",
            "name": "Nowpattern",
            "url": "https://nowpattern.com"
        },
        "publisher": {
            "@type": "Organization",
            "name": "Nowpattern",
            "url": "https://nowpattern.com",
            "logo": {
                "@type": "ImageObject",
                "url": "https://nowpattern.com/content/images/nowpattern-logo.png"
            }
        },
        "isAccessibleForFree": True,
        "inLanguage": "ja"
    }
    return json.dumps(template, ensure_ascii=False, indent=2)


# ── robots.txt / llms.txt ─────────────────────────────────────

def generate_robots_txt() -> str:
    """AIボットを明示的に許可するrobots.txt追記"""
    return """# === AI Bot Permissions (Nowpattern SEO) ===
# Allow AI crawlers to index content for citation in AI Overviews
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Bingbot
Allow: /

User-agent: BingPreview
Allow: /

# Standard crawlers
User-agent: *
Allow: /
Disallow: /ghost/
Disallow: /p/

Sitemap: https://nowpattern.com/sitemap.xml
"""


def generate_llms_txt() -> str:
    """llms.txt — AIエージェント向けサイト概要"""
    # prediction_db.json の統計
    stats = {"total": 0, "resolved": 0, "avg_brier_score": None}
    if os.path.exists(PREDICTION_DB):
        with open(PREDICTION_DB, "r", encoding="utf-8") as f:
            data = json.load(f)
            stats = data.get("stats", stats)

    brier_line = ""
    if stats.get("avg_brier_score"):
        brier_line = f"Average Brier Score: {stats['avg_brier_score']} (lower is better, 0 = perfect)\n"

    return f"""# Nowpattern

> Prediction Oracle platform — pattern-driven news analysis with verified Brier Score track records.

Nowpattern is the only bilingual (Japanese/English) prediction platform that combines deep force-dynamics analysis with every prediction tracked, auto-verified, and scored. We analyze geopolitics, economics, technology, crypto, and energy using a unique 3-layer taxonomy (Genre / Event / Dynamics) to identify recurring power patterns.

Track Record:
- Total predictions: {stats['total']}
- Resolved predictions: {stats['resolved']}
{brier_line}
## Key Pages

- [Prediction Tracker (JA)](https://nowpattern.com/predictions/): All predictions with live Brier Scores
- [Prediction Tracker (EN)](https://nowpattern.com/en/predictions/): English version
- [Taxonomy Guide (JA)](https://nowpattern.com/taxonomy/): 3-layer analysis framework
- [Taxonomy Guide (EN)](https://nowpattern.com/en/taxonomy/): English version

## Analysis Framework

Each article uses the Deep Pattern format with 13 sections:
1. FAST READ — 1-minute summary
2. BOTTOM LINE — Core insight in 3 seconds
3. DELTA — Change since last analysis
4. Tag badges — Genre/Event/Dynamics classification
5. Why it matters
6. What happened — Verified facts
7. The Big Picture — Historical context
8. Between the Lines — What media won't say
9. NOW PATTERN — Force dynamics analysis (unique methodology)
10. Pattern History — Historical parallels
11. What's Next — 3 scenarios with probabilities
12. OPEN LOOP — Next trigger event
13. ORACLE STATEMENT — Prediction tracking box with Brier Score

## Optional

- [About](https://nowpattern.com/about/): Platform mission and methodology
"""


# ── Ghost Code Injection ──────────────────────────────────────

def inject_global_schema(dry_run=False):
    """Ghost Settings の codeinjection_head に Organization JSON-LD を挿入"""
    env = _load_env()
    api_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not api_key:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY が設定されていません")
        return False

    jsonld = generate_organization_jsonld()
    print("=== Organization + WebSite JSON-LD ===")
    print(jsonld[:500])
    print("...")

    if dry_run:
        print("\n[DRY RUN] Ghost Code Injection への挿入をスキップ")
        return True

    # Ghost Settings API で codeinjection_head を取得
    try:
        settings = _ghost_api("GET", "settings/", api_key)
        current_head = ""
        for s in settings.get("settings", []):
            if s.get("key") == "codeinjection_head":
                current_head = s.get("value", "") or ""
                break

        # 既に挿入済みかチェック
        if "Nowpattern" in current_head and "schema.org" in current_head:
            print("✅ Organization JSON-LD は既に挿入済みです")
            return True

        # 挿入
        new_head = current_head + "\n\n<!-- Nowpattern SEO: Organization + WebSite Schema -->\n" + jsonld
        _ghost_api("PUT", "settings/", api_key, {
            "settings": [{"key": "codeinjection_head", "value": new_head}]
        })
        print("✅ Ghost Code Injection に Organization JSON-LD を挿入しました")
        return True
    except Exception as e:
        print(f"ERROR: Ghost API エラー — {e}")
        print("NOTE: Ghost Settings API 501の場合、SQLite直接更新が必要です")
        print(f"\n代替手順: Ghost管理画面 → Settings → Code injection → Header に以下を貼り付け:")
        print(jsonld)
        return False


# ── メイン ──────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Nowpattern SEO構造化データ管理")
    parser.add_argument("--inject-global", action="store_true",
                        help="Ghost Code Injection に Organization JSON-LD を挿入")
    parser.add_argument("--inject-predictions", action="store_true",
                        help="/predictions/ に Dataset JSON-LD を生成")
    parser.add_argument("--generate-robots", action="store_true",
                        help="robots.txt の AIボット許可設定を生成")
    parser.add_argument("--generate-llms-txt", action="store_true",
                        help="llms.txt を生成")
    parser.add_argument("--report", action="store_true",
                        help="現在の構造化データ状態レポート")
    parser.add_argument("--dry-run", action="store_true",
                        help="変更を適用せずに確認のみ")
    args = parser.parse_args()

    if args.inject_global:
        inject_global_schema(dry_run=args.dry_run)
    elif args.inject_predictions:
        print("=== Dataset JSON-LD (/predictions/) ===")
        print(generate_predictions_dataset_jsonld())
        print("\nこれを prediction_page_builder.py の HTML 出力に組み込んでください")
    elif args.generate_robots:
        print(generate_robots_txt())
        print("\n上記を /var/www/nowpattern/robots.txt に保存してください")
        print("または Caddy の respond ディレクティブで配信:")
        print('  handle /robots.txt { respond "..." }')
    elif args.generate_llms_txt:
        print(generate_llms_txt())
        print("\n上記を /var/www/nowpattern/llms.txt に保存してください")
    elif args.report:
        print("=== SEO構造化データ レポート ===\n")
        print("1. Organization JSON-LD:")
        print(generate_organization_jsonld()[:200] + "...\n")
        print("2. Dataset JSON-LD (/predictions/):")
        print(generate_predictions_dataset_jsonld()[:200] + "...\n")
        print("3. Article テンプレート:")
        print(generate_article_jsonld_template()[:200] + "...\n")
        print("4. robots.txt AIボット許可: 生成可能 (--generate-robots)")
        print("5. llms.txt: 生成可能 (--generate-llms-txt)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
