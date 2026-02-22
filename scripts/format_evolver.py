#!/usr/bin/env python3
"""
format_evolver.py — Nowpattern Format Evolver

月1回実行: 世界トップのニュースレターをスキャンし、
Nowpatternの記事フォーマットを自動で最新の世界水準に更新する。

使い方:
  python3 format_evolver.py                    # 通常実行
  python3 format_evolver.py --dry-run          # 分析のみ（指示書更新なし）

cron: 0 3 1 * * source /opt/cron-env.sh && python3 /opt/shared/scripts/format_evolver.py

フロー:
  1. 世界のトップ10ニュースレターの最新記事をRSS/WebでN件取得
  2. Gemini 2.5 Proが構造・トーン・テクニックを分析
  3. Nowpatternへの改善提案をリスト化
  4. 改善提案をレポートとして保存
  5. Telegram通知（オーナーが確認→採用判断）

※ 指示書の自動更新は危険なため、レポート生成+Telegram通知にとどめる。
   オーナーが承認した改善案のみを手動で反映する。
"""

import json
import os
import sys
import argparse
import subprocess
from datetime import datetime, timezone

REPORT_DIR = "/opt/shared/reports"
SCRIPTS_DIR = "/opt/shared/scripts"
TELEGRAM_SCRIPT = "/opt/shared/scripts/send-telegram-message.py"

# スキャン対象（RSS URL or Web URL）
TOP_NEWSLETTERS = [
    {"name": "Stratechery", "url": "https://stratechery.com/feed/", "type": "rss"},
    {"name": "Axios", "url": "https://www.axios.com/feeds/feed.rss", "type": "rss"},
    {"name": "Morning Brew", "url": "https://www.morningbrew.com/daily/rss", "type": "rss"},
    {"name": "Ben Evans", "url": "https://www.ben-evans.com/feed", "type": "rss"},
    {"name": "Doomberg", "url": "https://doomberg.substack.com/feed", "type": "rss"},
    {"name": "Kyla Scanlon", "url": "https://kylascanlon.substack.com/feed", "type": "rss"},
    {"name": "The Hustle", "url": "https://thehustle.co/feed/", "type": "rss"},
]

# 分析プロンプト
ANALYSIS_PROMPT = """あなたはニュースレター・コンテンツ戦略の世界的専門家です。

以下の世界トップクラスのニュースレター記事を分析し、Nowpattern.comの記事フォーマットを改善するための具体的な提案を作成してください。

【Nowpatternの現在のフォーマット（v4.0）】
1. BOTTOM LINE（TL;DR: 1文の核心 + パターン名 + 基本シナリオ + 注目ポイント）
2. タグバッジ（ジャンル/イベント/力学）
3. Why it matters（2-3文）
4. What happened（事実要約、300語）
5. The Big Picture（歴史的文脈 + 利害関係者 + データ）
6. Between the Lines（報道が言っていないこと）
7. NOW PATTERN（力学分析、ダークボックス）
8. Pattern History（歴史的並行事例）
9. What's Next（3シナリオ+確率+示唆）
10. Open Loop（次のトリガー + 追跡テーマ）

【分析してほしいニュースレター記事】
{articles}

【回答フォーマット】
以下のJSON形式で回答してください:
{{
  "analysis_date": "YYYY-MM-DD",
  "newsletters_analyzed": ["名前1", "名前2", ...],
  "observations": [
    {{
      "newsletter": "ニュースレター名",
      "technique": "発見したテクニック名",
      "description": "何をやっているか（具体的に）",
      "example": "記事からの具体例",
      "applicability": "Nowpatternにどう適用できるか",
      "impact": "high/medium/low",
      "effort": "high/medium/low"
    }}
  ],
  "top_3_recommendations": [
    {{
      "title": "改善提案タイトル",
      "description": "具体的な改善内容",
      "rationale": "なぜこの改善が効果的か",
      "implementation": "どうやって実装するか"
    }}
  ],
  "format_health_score": 85,
  "summary": "全体まとめ（3-4文）"
}}
"""


def fetch_rss_articles(url, max_items=3):
    """RSSフィードから最新N件の記事を取得"""
    try:
        import feedparser
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:max_items]:
            articles.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", "")[:1000],
                "published": entry.get("published", ""),
            })
        return articles
    except Exception as e:
        print(f"  RSS取得失敗({url[:50]}): {e}")
        return []


def scrape_article_text(url, timeout=15):
    """記事URLから本文を取得"""
    try:
        from curl_cffi import requests as cffi_requests
        from bs4 import BeautifulSoup

        resp = cffi_requests.get(url, impersonate="chrome", timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return ""

        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        article = soup.find("article")
        text = (article or soup).get_text(separator="\n", strip=True)
        return text[:3000] if len(text) > 3000 else text
    except Exception as e:
        print(f"  スクレイプ失敗({url[:50]}): {e}")
        return ""


def analyze_with_gemini(articles_text):
    """Gemini 2.5 Proで記事を分析"""
    api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY / GOOGLE_API_KEY が設定されていません")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-pro-preview-05-06")

        prompt = ANALYSIS_PROMPT.replace("{articles}", articles_text)
        response = model.generate_content(prompt)

        # JSONを抽出
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text)
    except Exception as e:
        print(f"  Gemini分析失敗: {e}")
        return None


def send_telegram_notification(report):
    """Telegram通知"""
    summary = report.get("summary", "分析完了")
    recs = report.get("top_3_recommendations", [])

    message = f"📊 Format Evolver 月次レポート\n\n"
    message += f"分析対象: {', '.join(report.get('newsletters_analyzed', []))}\n"
    message += f"フォーマット健全度: {report.get('format_health_score', '?')}/100\n\n"
    message += f"📝 サマリー:\n{summary}\n\n"

    if recs:
        message += "🏆 Top 3 改善提案:\n"
        for i, r in enumerate(recs, 1):
            message += f"{i}. {r.get('title', '')}\n   → {r.get('description', '')[:100]}\n\n"

    message += f"詳細: /opt/shared/reports/ を確認"

    try:
        if os.path.exists(TELEGRAM_SCRIPT):
            subprocess.run(
                ["python3", TELEGRAM_SCRIPT, message],
                capture_output=True, text=True, timeout=15
            )
    except Exception:
        pass

    return message


def run_evolver(dry_run=False):
    """メイン処理"""
    print("🔄 Nowpattern Format Evolver 起動")
    print(f"   分析対象: {len(TOP_NEWSLETTERS)} ニュースレター")

    # Step 1: 記事収集
    print("\nStep 1: 記事収集中...")
    all_articles = []
    for nl in TOP_NEWSLETTERS:
        print(f"  📰 {nl['name']}...")
        if nl["type"] == "rss":
            articles = fetch_rss_articles(nl["url"], max_items=2)
            for a in articles:
                a["newsletter"] = nl["name"]
                # 本文もスクレイプ（ベストエフォート）
                if a.get("link"):
                    a["full_text"] = scrape_article_text(a["link"])
            all_articles.extend(articles)

    print(f"  → {len(all_articles)} 記事を収集")

    if not all_articles:
        print("記事が取得できませんでした。")
        return

    # Step 2: 分析用テキスト構築
    articles_text = ""
    for a in all_articles:
        articles_text += f"\n=== {a.get('newsletter', '')} ===\n"
        articles_text += f"Title: {a.get('title', '')}\n"
        articles_text += f"Summary: {a.get('summary', '')[:500]}\n"
        if a.get("full_text"):
            articles_text += f"Body (excerpt): {a['full_text'][:1500]}\n"
        articles_text += "\n"

    if dry_run:
        print(f"\n[DRY-RUN] 分析テキスト: {len(articles_text)} 文字")
        print(f"[DRY-RUN] Gemini分析はスキップ")
        return

    # Step 3: Gemini分析
    print("\nStep 2: Gemini分析中...")
    report = analyze_with_gemini(articles_text)

    if not report:
        print("分析に失敗しました。")
        return

    # Step 4: レポート保存
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = os.path.join(REPORT_DIR, f"{date_str}_format-evolver-report.json")
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nStep 3: レポート保存: {report_path}")

    # Step 5: Telegram通知
    print("Step 4: Telegram通知...")
    msg = send_telegram_notification(report)
    print(msg[:200])

    # 結果サマリー
    print(f"\n=== Format Evolver 完了 ===")
    print(f"フォーマット健全度: {report.get('format_health_score', '?')}/100")
    observations = report.get("observations", [])
    high_impact = [o for o in observations if o.get("impact") == "high"]
    print(f"発見: {len(observations)} 件（高インパクト: {len(high_impact)} 件）")
    print(f"改善提案: {len(report.get('top_3_recommendations', []))} 件")


def main():
    parser = argparse.ArgumentParser(description="Nowpattern Format Evolver — 月次世界スキャン")
    parser.add_argument("--dry-run", action="store_true", help="記事収集のみ（分析・更新なし）")
    args = parser.parse_args()

    run_evolver(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
