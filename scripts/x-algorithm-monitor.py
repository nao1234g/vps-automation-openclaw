#!/usr/bin/env python3
"""
X Algorithm Monitor — Xアルゴリズム自動監視 + 投稿戦術の自動調整

毎朝 09:00 JST に自動実行（cron）。3つの仕事:
  1. 自分(@nowpattern)の投稿パフォーマンスをGrokで追跡
  2. 同ジャンルのバズ投稿パターンを収集
  3. Xアルゴリズム変更情報をRSSで監視

結果:
  - /opt/shared/x-analytics/YYYY-MM-DD.json に保存
  - /opt/shared/x-analytics/tactics.json に最新戦術を保存（x-auto-post.pyが参照）
  - Telegramでオーナーに朝のX戦術レポートを送信

Usage:
  python3 x-algorithm-monitor.py            # フル実行
  python3 x-algorithm-monitor.py --dry-run  # Telegram送信なし
  python3 x-algorithm-monitor.py --collect  # 収集のみ（分析・通知なし）

VPS cron:
  0 9 * * *  python3 /opt/shared/scripts/x-algorithm-monitor.py
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

# =============================================================================
# Config
# =============================================================================

JST = timezone(timedelta(hours=9))

ANALYTICS_DIR = "/opt/shared/x-analytics"
TACTICS_FILE = f"{ANALYTICS_DIR}/tactics.json"
HISTORY_DIR = f"{ANALYTICS_DIR}/history"

GROK_API_URL = "https://openrouter.ai/api/v1/chat/completions"
GROK_MODEL = "x-ai/grok-3"
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# Xアルゴリズム情報源（RSS）
ALGO_RSS_FEEDS = [
    {
        "name": "Sprout Social",
        "url": "https://sproutsocial.com/insights/feed/",
        "keywords": ["twitter algorithm", "x algorithm", "twitter tips",
                     "social media algorithm"],
    },
    {
        "name": "Social Media Examiner",
        "url": "https://www.socialmediaexaminer.com/feed/",
        "keywords": ["twitter", "x algorithm", "twitter strategy",
                     "x strategy", "twitter engagement"],
    },
    {
        "name": "Buffer Blog",
        "url": "https://buffer.com/resources/feed/",
        "keywords": ["twitter", "x algorithm", "social media tips",
                     "twitter growth"],
    },
    {
        "name": "Hootsuite Blog",
        "url": "https://blog.hootsuite.com/feed/",
        "keywords": ["twitter algorithm", "x algorithm", "twitter tips",
                     "twitter strategy"],
    },
]

# 監視対象の競合・同ジャンルアカウント（ニュース分析系）
BENCHMARK_ACCOUNTS = [
    "therundownai",     # The Rundown AI — AIニュース最大手
    "rowancheung",      # Rowan Cheung — AIツールレビュー
    "emollick",         # Ethan Mollick — AI×ビジネス実証
    "karpathy",         # Andrej Karpathy — 技術解説最高峰
    "benedictevans",    # Benedict Evans — テック構造分析
    "ianbremmer",       # Ian Bremmer — 地政学
    "adam_tooze",       # Adam Tooze — 経済歴史
    "levelsio",         # Pieter Levels — インディーハッカー
]


# =============================================================================
# ユーティリティ
# =============================================================================

def now_jst() -> datetime:
    return datetime.now(JST)


def log(msg: str):
    ts = now_jst().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def ensure_dirs():
    for d in [ANALYTICS_DIR, HISTORY_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)


def get_api_keys() -> dict:
    """APIキーを環境変数と.envから取得。"""
    keys = {
        "openrouter": os.environ.get("OPENROUTER_API_KEY"),
        "telegram_token": os.environ.get("TELEGRAM_BOT_TOKEN"),
        "telegram_chat": os.environ.get("ALLOWED_USERS"),
    }
    env_paths = [
        "/opt/cron-env.sh",
        "/opt/claude-code-telegram/.env",
        "/opt/shared/.env",
        "/opt/openclaw/.env",
    ]
    for path in env_paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("export "):
                        line = line[7:]
                    if "=" not in line or line.startswith("#"):
                        continue
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == "OPENROUTER_API_KEY" and not keys["openrouter"]:
                        keys["openrouter"] = v
                    elif k == "TELEGRAM_BOT_TOKEN" and not keys["telegram_token"]:
                        keys["telegram_token"] = v
                    elif k == "ALLOWED_USERS" and not keys["telegram_chat"]:
                        keys["telegram_chat"] = v
        except Exception:
            pass
    return keys


# =============================================================================
# 1. 自分の投稿パフォーマンス追跡（Grok検索）
# =============================================================================

def check_own_performance(api_key: str) -> dict | None:
    """@nowpatternの過去24時間の投稿パフォーマンスをGrokで確認。"""
    log("1/3: @nowpattern 投稿パフォーマンス確認中...")

    payload = {
        "model": GROK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an X/Twitter analytics expert. "
                    "Search for recent posts from @nowpattern. "
                    "Analyze engagement patterns. Report in JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Search X for all posts from @nowpattern in the last 48 hours.\n\n"
                    "For each post found, report:\n"
                    "- post_text (first 100 chars)\n"
                    "- likes, retweets, replies, views (if visible)\n"
                    "- post_url\n"
                    "- format_type: one of [quote_repost, original, thread, reply, image]\n\n"
                    "Then provide analysis:\n"
                    "- best_performing_post: which got most engagement and why\n"
                    "- worst_performing_post: which got least engagement\n"
                    "- avg_engagement_rate: rough estimate\n"
                    "- posting_time_analysis: which posting times got better results\n"
                    "- content_pattern: what topics/styles performed best\n\n"
                    "If no posts found, say so.\n\n"
                    "Return as JSON with keys: posts (array), analysis (object)."
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 2000,
    }

    result = _call_grok(api_key, payload)
    if result:
        log(f"  パフォーマンスデータ取得: {len(result)}文字")
    return {"raw": result} if result else None


# =============================================================================
# 2. バズ投稿パターン分析（Grok検索）
# =============================================================================

def check_viral_patterns(api_key: str) -> dict | None:
    """同ジャンルのバズ投稿パターンを収集。"""
    log("2/3: バズ投稿パターン収集中...")

    accounts_str = " OR ".join([f"from:{a}" for a in BENCHMARK_ACCOUNTS[:5]])

    payload = {
        "model": GROK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an X/Twitter trend analyst. "
                    "Find viral posts in the news analysis / AI / geopolitics niche. "
                    "Focus on WHAT made them go viral. Report in JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Search X for the most engaging posts in the last 48 hours from "
                    "news analysis, AI commentary, and geopolitics accounts.\n\n"
                    f"Priority accounts: {', '.join('@' + a for a in BENCHMARK_ACCOUNTS)}\n\n"
                    "Find the top 10 highest-engagement posts and analyze:\n"
                    "- post_text (first 120 chars)\n"
                    "- author (@username)\n"
                    "- likes, retweets, replies (approx)\n"
                    "- viral_reason: WHY it went viral (hook type, emotion, timing, format)\n"
                    "- format: text_only / image / video / thread / quote_repost / poll\n"
                    "- hook_type: curiosity_gap / contrarian / data_shock / breaking / personal_story\n"
                    "- had_external_link: true/false\n\n"
                    "Then provide pattern_summary:\n"
                    "- top_3_viral_patterns: what patterns are working RIGHT NOW\n"
                    "- best_format: which format got most engagement\n"
                    "- best_hook_type: which hook type worked best\n"
                    "- optimal_time_window: when were viral posts posted (JST)\n"
                    "- link_impact: did external links help or hurt engagement\n\n"
                    "Return as JSON with keys: viral_posts (array), pattern_summary (object)."
                ),
            },
        ],
        "temperature": 0.3,
        "max_tokens": 2500,
    }

    result = _call_grok(api_key, payload)
    if result:
        log(f"  バズパターンデータ取得: {len(result)}文字")
    return {"raw": result} if result else None


# =============================================================================
# 3. Xアルゴリズム変更チェック（RSS）
# =============================================================================

def check_algorithm_changes() -> list[dict]:
    """RSS フィードからXアルゴリズム関連記事を検出。"""
    log("3/3: Xアルゴリズム変更チェック中...")

    found = []
    for feed_info in ALGO_RSS_FEEDS:
        try:
            req = urllib.request.Request(
                feed_info["url"],
                headers={"User-Agent": "NowpatternXMonitor/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", errors="replace")

            root = ET.fromstring(raw)
            items = root.findall(".//item")
            if not items:
                atom_ns = "http://www.w3.org/2005/Atom"
                items = root.findall(f".//{{{atom_ns}}}entry")

            for item in items[:20]:
                title = item.findtext("title") or ""
                desc = item.findtext("description") or ""
                link = item.findtext("link") or ""
                pub_date = item.findtext("pubDate") or ""

                # キーワードマッチ
                text = (title + " " + desc).lower()
                matched_kw = [
                    kw for kw in feed_info["keywords"]
                    if kw.lower() in text
                ]

                if matched_kw:
                    found.append({
                        "source": feed_info["name"],
                        "title": title.strip(),
                        "url": link.strip(),
                        "date": pub_date.strip(),
                        "matched_keywords": matched_kw,
                    })

            log(f"  {feed_info['name']}: {len(items)}件チェック")
        except Exception as e:
            log(f"  {feed_info['name']}: エラー ({e})")
        time.sleep(0.5)

    # 重複除去（タイトルベース）
    seen = set()
    unique = []
    for item in found:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)

    log(f"  アルゴリズム関連記事: {len(unique)}件検出")
    return unique


# =============================================================================
# 戦術生成
# =============================================================================

def generate_tactics(
    own_perf: dict | None,
    viral_patterns: dict | None,
    algo_changes: list[dict],
    prev_tactics: dict | None,
) -> dict:
    """収集データから今日の投稿戦術を生成。"""
    log("戦術レポート生成中...")

    today = now_jst().strftime("%Y-%m-%d")

    tactics = {
        "generated_at": now_jst().isoformat(),
        "date": today,
        # デフォルト戦術（2026年Xアルゴリズム準拠）
        "base_rules": {
            "reply_weight": "150x likes — 会話を生む投稿を最優先",
            "text_vs_video": "テキスト+画像がビデオより30%伸びる",
            "external_links": "本文にリンクを入れない。リプライに置く",
            "tone": "ポジティブ/建設的（Grokが監視、攻撃的=抑制）",
            "first_hour": "投稿後1時間のエンゲージメントが最重要",
            "best_times_jst": "9:00-12:00, 18:00-21:00（平日）",
            "premium": "X Premium必須（無料アカウントはリーチ激減）",
        },
        # 今日の推奨
        "today": {
            "recommended_format": "quote_repost + image",
            "recommended_hook": "curiosity_gap (P1)",
            "avoid": [],
            "special_notes": [],
        },
        # データソース
        "data": {
            "own_performance": own_perf,
            "viral_patterns": viral_patterns,
            "algorithm_changes": algo_changes[:5],
        },
    }

    # アルゴリズム変更があれば特別注記
    if algo_changes:
        tactics["today"]["special_notes"].append(
            f"アルゴリズム関連記事 {len(algo_changes)}件検出 — 要確認"
        )
        tactics["today"]["algo_alert"] = True

    # 前回の戦術との差分
    if prev_tactics:
        prev_date = prev_tactics.get("date", "")
        tactics["today"]["previous_date"] = prev_date

    return tactics


# =============================================================================
# Telegram通知
# =============================================================================

def build_telegram_report(tactics: dict) -> str:
    """Telegram向けの朝レポートを生成。"""
    lines = []
    today = tactics["date"]
    lines.append(f"[X Monitor] {today} 朝のX戦術レポート")
    lines.append("")

    # アルゴリズム変更アラート
    algo_changes = tactics["data"].get("algorithm_changes", [])
    if algo_changes:
        lines.append(f"!! アルゴリズム関連記事 {len(algo_changes)}件 !!")
        for ac in algo_changes[:3]:
            lines.append(f"  - {ac['title'][:60]}")
            lines.append(f"    {ac['url']}")
        lines.append("")

    # 今日の戦術
    today_data = tactics["today"]
    lines.append("-- 今日の戦術 --")
    lines.append(f"フォーマット: {today_data['recommended_format']}")
    lines.append(f"フック: {today_data['recommended_hook']}")
    if today_data.get("special_notes"):
        for note in today_data["special_notes"]:
            lines.append(f"  * {note}")
    lines.append("")

    # ベースルール（毎回リマインド）
    lines.append("-- 常時ルール --")
    rules = tactics["base_rules"]
    lines.append(f"- リプライ = いいねの{rules['reply_weight']}")
    lines.append(f"- {rules['external_links']}")
    lines.append(f"- {rules['tone']}")
    lines.append(f"- ベスト時間: {rules['best_times_jst']}")

    # 自分のパフォーマンス要約
    own = tactics["data"].get("own_performance")
    if own and own.get("raw"):
        lines.append("")
        lines.append("-- @nowpattern 48h --")
        # Grokの生テキストから最初の300文字
        raw_text = own["raw"][:300]
        lines.append(raw_text)

    # バズパターン要約
    viral = tactics["data"].get("viral_patterns")
    if viral and viral.get("raw"):
        lines.append("")
        lines.append("-- バズパターン --")
        raw_text = viral["raw"][:300]
        lines.append(raw_text)

    return "\n".join(lines)


def send_telegram(token: str, chat_id: str, text: str, dry_run: bool = False):
    """Telegramにメッセージ送信。4000文字超は分割。"""
    if dry_run:
        log("[dry-run] Telegram送信内容:")
        print(text[:500])
        print("..." if len(text) > 500 else "")
        return True

    # markdownストリップ（Telegram strict parserで400エラー回避）
    clean = text.replace("**", "").replace("*", "").replace("_", "")

    chunks = []
    current = ""
    for line in clean.split("\n"):
        if len(current) + len(line) + 1 > 4000:
            if current:
                chunks.append(current)
            current = line
        else:
            current += ("\n" if current else "") + line
    if current:
        chunks.append(current)

    success = True
    for i, chunk in enumerate(chunks):
        url = TELEGRAM_API_URL.format(token=token)
        payload = {"chat_id": chat_id, "text": chunk}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("ok"):
                    log(f"  Telegram {i+1}/{len(chunks)} 送信OK")
                else:
                    log(f"  Telegram エラー: {result}")
                    success = False
        except Exception as e:
            log(f"  Telegram 送信失敗: {e}")
            success = False
        if i < len(chunks) - 1:
            time.sleep(1)

    return success


# =============================================================================
# Grok API共通呼び出し
# =============================================================================

def _call_grok(api_key: str, payload: dict) -> str | None:
    """Grok APIをOpenRouter経由で呼び出し、レスポンステキストを返す。"""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROK_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No details"
        log(f"  Grok APIエラー {e.code}: {error_body[:300]}")
        return None
    except Exception as e:
        log(f"  Grok APIエラー: {e}")
        return None


# =============================================================================
# メイン
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="X Algorithm Monitor")
    parser.add_argument("--dry-run", action="store_true",
                        help="Telegram送信しない")
    parser.add_argument("--collect", action="store_true",
                        help="収集のみ（分析・通知なし）")
    args = parser.parse_args()

    log("=== X Algorithm Monitor 開始 ===")
    ensure_dirs()
    keys = get_api_keys()

    today = now_jst().strftime("%Y-%m-%d")
    daily_file = f"{HISTORY_DIR}/{today}.json"

    # 既に今日実行済みか確認
    if os.path.exists(daily_file) and not args.dry_run:
        log(f"今日({today})は実行済み。--dry-run で再実行可能。")
        return

    # --- 収集 ---

    # 1. 自分のパフォーマンス（Grok via OpenRouter）
    own_perf = None
    if keys.get("openrouter"):
        own_perf = check_own_performance(keys["openrouter"])
        time.sleep(2)
    else:
        log("  OPENROUTER_API_KEY なし — パフォーマンスチェックをスキップ")

    # 2. バズパターン（Grok via OpenRouter）
    viral_patterns = None
    if keys.get("openrouter"):
        viral_patterns = check_viral_patterns(keys["openrouter"])
        time.sleep(2)
    else:
        log("  OPENROUTER_API_KEY なし — バズパターンをスキップ")

    # 3. アルゴリズム変更チェック（RSS、無料）
    algo_changes = check_algorithm_changes()

    if args.collect:
        # 収集のみモード
        raw_data = {
            "collected_at": now_jst().isoformat(),
            "own_performance": own_perf,
            "viral_patterns": viral_patterns,
            "algorithm_changes": algo_changes,
        }
        with open(daily_file, "w") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
        log(f"収集データ保存: {daily_file}")
        return

    # --- 分析・戦術生成 ---

    # 前回の戦術を読み込み
    prev_tactics = None
    if os.path.exists(TACTICS_FILE):
        try:
            with open(TACTICS_FILE) as f:
                prev_tactics = json.load(f)
        except Exception:
            pass

    tactics = generate_tactics(own_perf, viral_patterns, algo_changes,
                               prev_tactics)

    # 保存
    with open(TACTICS_FILE, "w") as f:
        json.dump(tactics, f, ensure_ascii=False, indent=2)
    log(f"戦術ファイル更新: {TACTICS_FILE}")

    with open(daily_file, "w") as f:
        json.dump(tactics, f, ensure_ascii=False, indent=2)
    log(f"日次データ保存: {daily_file}")

    # --- Telegram通知 ---
    report = build_telegram_report(tactics)

    if keys.get("telegram_token") and keys.get("telegram_chat"):
        send_telegram(
            keys["telegram_token"],
            keys["telegram_chat"],
            report,
            dry_run=args.dry_run,
        )
    else:
        log("Telegram設定なし — レポートを標準出力に表示")
        print(report)

    log("=== X Algorithm Monitor 完了 ===")


if __name__ == "__main__":
    main()
