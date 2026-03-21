#!/usr/bin/env python3
"""
Google Search Console Intelligence System for Nowpattern
=========================================================
日次自動実行: VPSのcronから毎朝08:00 JSTに起動
機能:
  1. Search Console API から過去28日分のデータ取得
  2. 国別・クエリ別・ページ別のパフォーマンス分析
  3. EN/JPコンテンツ戦略への推奨事項生成
  4. Telegramにデイリーレポート送信
  5. NEO向けのコンテンツ提案を pending_approvals.json に追加

認証: /opt/shared/gsc_service_account.json (Service Account推奨)
     または /opt/shared/gsc_token.json (OAuth2トークン)
"""

import json
import os
import sys
import time
import uuid
import urllib.request
from datetime import datetime, timedelta, timezone

# ============================================================
# 設定
# ============================================================
SITE_URL = "sc-domain:nowpattern.com"
SERVICE_ACCOUNT_FILE = "/opt/shared/gsc_service_account.json"
TOKEN_FILE = "/opt/shared/gsc_token.json"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
OUTPUT_FILE = "/opt/shared/data/gsc_insights.json"
APPROVALS_FILE = "/opt/shared/data/pending_approvals.json"
ENV_FILE = "/opt/cron-env.sh"

JST = timezone(timedelta(hours=9))
DAYS_BACK = 28


# ============================================================
# 環境変数読み込み
# ============================================================
def load_env():
    env = {}
    try:
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    k, _, v = line[7:].partition("=")
                    env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


ENV = load_env()
BOT_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = ENV.get("TELEGRAM_CHAT_ID", "")


# ============================================================
# Telegram
# ============================================================
def send_telegram(text, parse_mode="Markdown"):
    if not BOT_TOKEN or not CHAT_ID:
        print("[WARN] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            pass
    except Exception as e:
        print(f"[WARN] Telegram error: {e}")


# ============================================================
# Google Search Console 認証
# ============================================================
def get_gsc_service():
    """GSCサービスオブジェクトを返す"""
    try:
        from googleapiclient.discovery import build

        # Service Account 優先
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
            return build("searchconsole", "v1", credentials=creds)

        # OAuth2 フォールバック
        if os.path.exists(TOKEN_FILE):
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            with open(TOKEN_FILE) as f:
                data = json.load(f)
            creds = Credentials(
                token=data.get("token"),
                refresh_token=data.get("refresh_token"),
                token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=data.get("client_id"),
                client_secret=data.get("client_secret"),
                scopes=data.get("scopes", SCOPES)
            )
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # 更新したトークンを保存
                data["token"] = creds.token
                with open(TOKEN_FILE, "w") as f:
                    json.dump(data, f, indent=2)
            return build("searchconsole", "v1", credentials=creds)

    except Exception as e:
        raise RuntimeError(f"GSC認証失敗: {e}. gsc_auth_setup.py を実行してください。")

    raise RuntimeError("認証ファイルが見つかりません。gsc_auth_setup.py を実行してください。")


# ============================================================
# データ取得
# ============================================================
def fetch_search_analytics(service, dimensions, row_limit=5000):
    """Search Analytics データ取得"""
    end_date = (datetime.now(JST) - timedelta(days=3)).strftime("%Y-%m-%d")
    start_date = (datetime.now(JST) - timedelta(days=DAYS_BACK + 3)).strftime("%Y-%m-%d")

    try:
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": dimensions,
            "rowLimit": row_limit,
            "startRow": 0
        }
        response = service.searchanalytics().query(
            siteUrl=SITE_URL, body=body
        ).execute()
        return response.get("rows", [])
    except Exception as e:
        print(f"[ERROR] fetch_search_analytics({dimensions}): {e}")
        return []


# ============================================================
# 分析
# ============================================================
def analyze_countries(rows):
    """国別パフォーマンス分析"""
    total_clicks = sum(r["clicks"] for r in rows)
    total_impressions = sum(r["impressions"] for r in rows)

    countries = []
    for r in sorted(rows, key=lambda x: x["clicks"], reverse=True)[:20]:
        country_code = r["keys"][0].upper()
        countries.append({
            "country": country_code,
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"] * 100, 2),
            "position": round(r["position"], 1),
            "clicks_pct": round(r["clicks"] / total_clicks * 100, 1) if total_clicks > 0 else 0
        })

    # JP vs 非JP分析
    jp_clicks = sum(r["clicks"] for r in rows if r["keys"][0].upper() == "JPN")
    non_jp_clicks = total_clicks - jp_clicks

    return {
        "total_clicks": int(total_clicks),
        "total_impressions": int(total_impressions),
        "jp_clicks": int(jp_clicks),
        "non_jp_clicks": int(non_jp_clicks),
        "jp_ratio": round(jp_clicks / total_clicks * 100, 1) if total_clicks > 0 else 0,
        "top_countries": countries[:10]
    }


def analyze_queries(rows):
    """クエリ分析 - コンテンツギャップ発見"""
    # クリック数上位
    top_by_clicks = sorted(rows, key=lambda x: x["clicks"], reverse=True)[:20]

    # CTR改善余地 (高インプレッション・低CTR)
    ctr_opportunities = [
        r for r in rows
        if r["impressions"] >= 50 and r["ctr"] < 0.05  # 50インプレ以上でCTR5%未満
    ]
    ctr_opportunities = sorted(ctr_opportunities, key=lambda x: x["impressions"], reverse=True)[:10]

    # 急成長クエリ (位置が良く伸びしろあり)
    rising_queries = [
        r for r in rows
        if r["position"] <= 10 and r["impressions"] >= 30
    ]
    rising_queries = sorted(rising_queries, key=lambda x: x["clicks"], reverse=True)[:10]

    def format_row(r):
        return {
            "query": r["keys"][0],
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"] * 100, 2),
            "position": round(r["position"], 1)
        }

    return {
        "top_by_clicks": [format_row(r) for r in top_by_clicks],
        "ctr_opportunities": [format_row(r) for r in ctr_opportunities],
        "rising_queries": [format_row(r) for r in rising_queries],
        "total_queries": len(rows)
    }


def analyze_pages(rows):
    """ページパフォーマンス分析"""
    top_pages = sorted(rows, key=lambda x: x["clicks"], reverse=True)[:20]

    # JA vs EN ページ分析
    ja_pages = [r for r in rows if "/en/" not in r["keys"][0]]
    en_pages = [r for r in rows if "/en/" in r["keys"][0]]

    ja_clicks = sum(r["clicks"] for r in ja_pages)
    en_clicks = sum(r["clicks"] for r in en_pages)
    total_clicks = ja_clicks + en_clicks

    def format_row(r):
        url = r["keys"][0].replace("https://nowpattern.com", "")
        return {
            "page": url,
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"] * 100, 2),
            "position": round(r["position"], 1)
        }

    return {
        "top_pages": [format_row(r) for r in top_pages],
        "ja_clicks": int(ja_clicks),
        "en_clicks": int(en_clicks),
        "en_ratio": round(en_clicks / total_clicks * 100, 1) if total_clicks > 0 else 0,
        "total_pages": len(rows)
    }


# ============================================================
# コンテンツ戦略推奨
# ============================================================
def generate_recommendations(country_analysis, query_analysis, page_analysis):
    """データから具体的なコンテンツ戦略を生成"""
    recommendations = []

    jp_ratio = country_analysis["jp_ratio"]
    en_ratio = page_analysis["en_ratio"]
    top_countries = country_analysis["top_countries"]

    # 1. EN記事の優先度
    non_jp_top = [c for c in top_countries if c["country"] not in ("JPN", "")]
    non_jp_traffic = sum(c["clicks_pct"] for c in non_jp_top[:5])

    if non_jp_traffic > 30:
        recommendations.append({
            "type": "content_ratio",
            "priority": "high",
            "title": f"EN記事強化: 非日本トラフィックが{non_jp_traffic:.0f}%",
            "detail": f"JA:{jp_ratio}% vs EN:{100-jp_ratio}%. EN比率を増やす余地あり。"
                      f"主要な非JP国: {', '.join(c['country'] for c in non_jp_top[:3])}",
            "action": "EN記事の日割りを JP100:EN100 → JP80:EN120 に調整"
        })

    # 2. CTR改善余地
    if query_analysis["ctr_opportunities"]:
        top_opp = query_analysis["ctr_opportunities"][0]
        recommendations.append({
            "type": "ctr_improvement",
            "priority": "medium",
            "title": f"CTR改善余地: '{top_opp['query']}' ({top_opp['impressions']}インプレ/CTR{top_opp['ctr']}%)",
            "detail": "高インプレ・低CTRのクエリ = タイトル/メタディスクリプションを改善で大幅クリック増",
            "action": f"クエリ '{top_opp['query']}' に対応する記事のSEOタイトルを見直す"
        })

    # 3. トップクエリからトピック優先度
    if query_analysis["top_by_clicks"]:
        top_queries = [q["query"] for q in query_analysis["top_by_clicks"][:5]]
        recommendations.append({
            "type": "topic_priority",
            "priority": "high",
            "title": f"人気トピック: {', '.join(top_queries[:3])}",
            "detail": "これらのトピックに関連する記事・予測を増やす",
            "action": f"NEO-ONE/TWO への指示: 優先トピック = {top_queries}"
        })

    # 4. /predictions/ ページのパフォーマンス
    pred_pages = [p for p in page_analysis["top_pages"] if "predictions" in p["page"]]
    if pred_pages:
        pred = pred_pages[0]
        recommendations.append({
            "type": "predictions_page",
            "priority": "medium",
            "title": f"/predictions/: {pred['clicks']}クリック / {pred['impressions']}インプレ",
            "detail": f"予測ページのCTR: {pred['ctr']}%, 平均掲載順位: {pred['position']}",
            "action": "予測ページのメタタイトル改善 + 新鮮な予測追加でCTR向上"
        })

    return recommendations


# ============================================================
# pending_approvals.json への追記
# ============================================================
def add_to_pending_approvals(recommendations):
    """高優先度推奨をapproval キューに追加"""
    if not recommendations:
        return

    os.makedirs(os.path.dirname(APPROVALS_FILE), exist_ok=True)

    try:
        if os.path.exists(APPROVALS_FILE):
            with open(APPROVALS_FILE) as f:
                approvals = json.load(f)
        else:
            approvals = []
    except Exception:
        approvals = []

    added = 0
    for rec in recommendations:
        if rec["priority"] == "high":
            new_item = {
                "id": f"gsc-{uuid.uuid4().hex[:8]}",
                "ts": datetime.now(timezone.utc).isoformat(),
                "proposer": "gsc_intelligence",
                "title": f"[GSC] {rec['title'][:60]}",
                "description": rec["detail"][:200],
                "action": rec["action"],
                "expected_roi": "SEOトラフィック改善",
                "risk_level": "low",
                "reversible": True,
                "status": "pending",
                "type": rec["type"]
            }
            approvals.append(new_item)
            added += 1

    if added > 0:
        with open(APPROVALS_FILE, "w", encoding="utf-8") as f:
            json.dump(approvals, f, ensure_ascii=False, indent=2)
        print(f"[OK] {added}件のGSC推奨を pending_approvals.json に追加")


# ============================================================
# Telegram レポート生成
# ============================================================
def build_telegram_report(country_analysis, query_analysis, page_analysis, recommendations):
    """Telegram用のレポートテキストを生成"""
    now_str = datetime.now(JST).strftime("%Y-%m-%d")

    # 国別トップ5
    country_lines = []
    for c in country_analysis["top_countries"][:5]:
        bar = "█" * int(c["clicks_pct"] / 5) + "░" * (20 - int(c["clicks_pct"] / 5))
        country_lines.append(f"  `{c['country']:3s}` {bar[:10]} {c['clicks_pct']}% ({c['clicks']}クリック)")

    # トップクエリ5
    query_lines = []
    for q in query_analysis["top_by_clicks"][:5]:
        query_lines.append(f"  • `{q['query'][:40]}` — {q['clicks']}クリック (CTR {q['ctr']}%)")

    # トップページ5
    page_lines = []
    for p in page_analysis["top_pages"][:5]:
        page_lines.append(f"  • `{p['page'][:40]}` — {p['clicks']}クリック")

    # 推奨アクション
    rec_lines = []
    for r in recommendations[:3]:
        priority_emoji = "🔴" if r["priority"] == "high" else "🟡"
        rec_lines.append(f"  {priority_emoji} {r['title']}")

    report = f"""📊 *Search Console インテリジェンス* — {now_str}

🌍 *国別トラフィック* (過去{DAYS_BACK}日)
  総クリック: *{country_analysis['total_clicks']:,}* / 総インプレ: {country_analysis['total_impressions']:,}
  JA: *{country_analysis['jp_ratio']}%* | 非JA: {100 - country_analysis['jp_ratio']}%
{chr(10).join(country_lines)}

🔍 *トップクエリ*
{chr(10).join(query_lines)}

📄 *トップページ*
{chr(10).join(page_lines)}

⚡ *CTR改善余地* (高インプレ・低CTR)
{chr(10).join(f"  • `{q['query'][:35]}`: {q['impressions']}インプレ/CTR {q['ctr']}%" for q in query_analysis['ctr_opportunities'][:3]) or "  なし"}

🎯 *推奨アクション*
{chr(10).join(rec_lines) or "  特になし"}

EN記事比率: *{page_analysis['en_ratio']}%* / JA記事比率: {100 - page_analysis['en_ratio']}%
→ nowpattern.com/en/ への流入: {page_analysis['en_clicks']:,}クリック"""

    return report


# ============================================================
# メイン
# ============================================================
def main():
    print(f"[GSC] Starting at {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}")

    # GSC接続
    try:
        service = get_gsc_service()
        print("[OK] GSC 接続成功")
    except RuntimeError as e:
        msg = f"[GSC ERROR] {e}"
        print(msg)
        send_telegram(f"❌ GSC Intelligence 起動失敗\n{e}")
        sys.exit(1)

    # データ取得
    print("[GSC] 国別データ取得中...")
    country_rows = fetch_search_analytics(service, ["country"])

    print("[GSC] クエリデータ取得中...")
    query_rows = fetch_search_analytics(service, ["query"])

    print("[GSC] ページデータ取得中...")
    page_rows = fetch_search_analytics(service, ["page"])

    if not country_rows and not query_rows and not page_rows:
        msg = "[GSC] データが取得できませんでした (サイトへのアクセス権限を確認)"
        print(msg)
        send_telegram(f"⚠️ GSC: データ取得失敗\n{msg}")
        sys.exit(1)

    # 分析
    print("[GSC] 分析中...")
    country_analysis = analyze_countries(country_rows) if country_rows else {
        "total_clicks": 0, "total_impressions": 0,
        "jp_clicks": 0, "non_jp_clicks": 0, "jp_ratio": 0, "top_countries": []
    }
    query_analysis = analyze_queries(query_rows) if query_rows else {
        "top_by_clicks": [], "ctr_opportunities": [], "rising_queries": [], "total_queries": 0
    }
    page_analysis = analyze_pages(page_rows) if page_rows else {
        "top_pages": [], "ja_clicks": 0, "en_clicks": 0, "en_ratio": 0, "total_pages": 0
    }

    # 推奨事項生成
    recommendations = generate_recommendations(country_analysis, query_analysis, page_analysis)

    # 結果保存
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    insights = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days_analyzed": DAYS_BACK,
        "country": country_analysis,
        "queries": query_analysis,
        "pages": page_analysis,
        "recommendations": recommendations
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(insights, f, ensure_ascii=False, indent=2)
    print(f"[OK] インサイトを {OUTPUT_FILE} に保存")

    # pending_approvals に高優先度推奨を追加
    add_to_pending_approvals(recommendations)

    # Telegram レポート送信
    report = build_telegram_report(country_analysis, query_analysis, page_analysis, recommendations)
    send_telegram(report)
    print("[OK] Telegram レポート送信完了")

    # サマリー表示
    print(f"\n=== GSC サマリー ({DAYS_BACK}日) ===")
    print(f"総クリック: {country_analysis['total_clicks']:,}")
    print(f"総インプレ: {country_analysis['total_impressions']:,}")
    print(f"JP比率: {country_analysis['jp_ratio']}%")
    print(f"上位クエリ: {[q['query'] for q in query_analysis['top_by_clicks'][:3]]}")
    print(f"推奨件数: {len(recommendations)}")


if __name__ == "__main__":
    main()
