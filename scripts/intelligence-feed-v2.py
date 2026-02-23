#!/usr/bin/env python3
"""
Hey Loop Intelligence Feed v2.0
================================
設計図: docs/HEY_LOOP_V2_DESIGN.md

Layer 0: Python収集（RSS/Reddit/HN/GitHub/Grok — LLMなし）
Layer 1: Opus 4.6 全判断（claude --print + Read tool）
Layer 2: Telegram報告（200字以内）
Layer 3: state.json 閉ループ（前回文脈を次回に引き継ぐ）
Layer 4: 週次自己進化（AGENT_WISDOM.md 自動更新）

特別監視: Claude Code / OpenClaw — 変化があれば即アラート

「9割削減」技術:
  データをファイルに書く → claude --print で Opus が Read ツールで読む
  プロンプトは ~50トークン。毎回新鮮セッション（文脈蓄積なし）

Usage:
  python3 intelligence-feed-v2.py            # フル実行（collect + synth）
  python3 intelligence-feed-v2.py --collect  # Layer 0 のみ（LLMなし）
  python3 intelligence-feed-v2.py --synth    # Layer 1 のみ（Opus合成）
  python3 intelligence-feed-v2.py --evolve   # Layer 4（週次進化）
  python3 intelligence-feed-v2.py --dry-run  # Telegram送信なし（テスト）

VPS cron 設定:
  */30 * * * *  python3 /opt/shared/scripts/intelligence-feed-v2.py --collect
  0 */3 * * *   python3 /opt/shared/scripts/intelligence-feed-v2.py --synth
  0 23 * * 0    python3 /opt/shared/scripts/intelligence-feed-v2.py --evolve
"""

import argparse
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import urllib.request
import urllib.error

# =============================================================================
# Config
# =============================================================================

JST = timezone(timedelta(hours=9))

INTEL_DIR = "/opt/shared/intelligence"
RAW_DIR = f"{INTEL_DIR}/raw"
SYNTH_DIR = f"{INTEL_DIR}/synthesis"
WEEKLY_DIR = f"{INTEL_DIR}/weekly"
STATE_FILE = f"{INTEL_DIR}/state.json"
AGENT_WISDOM_FILE = "/opt/shared/AGENT_WISDOM.md"

# Claude バイナリ候補（VPS環境）
CLAUDE_BIN_CANDIDATES = [
    "/root/.nvm/versions/node/v22.14.0/bin/claude",
    "/opt/claude-code-telegram/node_modules/.bin/claude",
    "/usr/local/bin/claude",
    "/root/.local/bin/claude",
]

# =============================================================================
# RSS フィード（AI全般 + Claude/OpenClaw特別監視）
# =============================================================================
RSS_FEEDS = [
    # --- Claude Code / OpenClaw 最重要監視 ---
    {
        "name": "Anthropic Blog",
        "url": "https://www.anthropic.com/rss.xml",
        "category": "claude_watch",
        "priority": "critical",
    },
    # --- AI研究・モデル動向 ---
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog.rss",
        "category": "ai_research",
        "priority": "high",
    },
    {
        "name": "arXiv cs.AI",
        "url": "https://arxiv.org/rss/cs.AI",
        "category": "ai_research",
        "priority": "medium",
    },
    # --- AI業界ニュース ---
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "category": "ai_business",
        "priority": "high",
    },
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/tag/artificial-intelligence/feed/",
        "category": "ai_business",
        "priority": "medium",
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "category": "ai_news",
        "priority": "medium",
    },
    {
        "name": "MIT Technology Review AI",
        "url": "https://www.technologyreview.com/tag/artificial-intelligence/feed/",
        "category": "ai_research",
        "priority": "medium",
    },
    {
        "name": "Wired AI",
        "url": "https://www.wired.com/feed/tag/artificial-intelligence/latest/rss",
        "category": "ai_news",
        "priority": "low",
    },
]

# =============================================================================
# Reddit サブレディット
# =============================================================================
SUBREDDITS = [
    # Claude Code / OpenClaw 特別監視
    {"name": "ClaudeAI", "category": "claude_watch", "limit": 15},
    # AIエージェントツール
    {"name": "LocalLLaMA", "category": "ai_tools", "limit": 10},
    {"name": "AI_Agents", "category": "ai_tools", "limit": 10},
    {"name": "artificial", "category": "ai_news", "limit": 8},
    {"name": "MachineLearning", "category": "ai_research", "limit": 8},
    {"name": "Singularity", "category": "ai_news", "limit": 5},
    # 収益シグナル
    {"name": "SideProject", "category": "revenue", "limit": 10},
    {"name": "SaaS", "category": "revenue", "limit": 8},
    {"name": "indiehackers", "category": "revenue", "limit": 8},
    {"name": "Entrepreneur", "category": "revenue", "limit": 8},
    {"name": "EntrepreneurRideAlong", "category": "revenue", "limit": 8},
    # インフラ
    {"name": "n8n", "category": "infra", "limit": 5},
    {"name": "selfhosted", "category": "infra", "limit": 5},
    {"name": "docker", "category": "infra", "limit": 5},
]

# =============================================================================
# GitHub リポジトリ監視
# =============================================================================
GITHUB_REPOS = [
    # --- Claude Code / OpenClaw 最重要 ---
    {
        "repo": "anthropics/anthropic-sdk-python",
        "category": "claude_watch",
        "priority": "critical",
    },
    {
        "repo": "open-claw/open-claw",
        "category": "claude_watch",
        "priority": "critical",
    },
    # --- AIエージェントツール競合追跡 ---
    {
        "repo": "continuedev/continue",
        "category": "ai_tools_competitor",
        "priority": "high",
    },
    {
        "repo": "BerriAI/litellm",
        "category": "ai_tools",
        "priority": "high",
    },
    {
        "repo": "langgenius/dify",
        "category": "ai_tools",
        "priority": "medium",
    },
    {
        "repo": "microsoft/autogen",
        "category": "ai_tools",
        "priority": "medium",
    },
    {
        "repo": "joaomdmoura/crewAI",
        "category": "ai_tools",
        "priority": "medium",
    },
    {
        "repo": "n8n-io/n8n",
        "category": "infra",
        "priority": "high",
    },
    {
        "repo": "Mintplex-Labs/anything-llm",
        "category": "ai_tools",
        "priority": "low",
    },
    {
        "repo": "assafelovic/gpt-researcher",
        "category": "ai_tools",
        "priority": "low",
    },
]

# =============================================================================
# HN キーワード
# =============================================================================
HN_KEYWORDS = [
    # Claude Code / OpenClaw 最重要
    "claude code", "claude", "anthropic", "open-claw", "openclaw",
    # AIエージェントツール全般
    "ai agent", "llm", "gpt", "gemini", "grok", "mistral", "cursor",
    "copilot", "devin", "continue", "codeium", "model", "ai tool",
    # ビジネス・収益
    "revenue", "mrr", "saas", "newsletter", "indie hacker", "startup",
    "automation", "side project", "monetize",
    # インフラ
    "n8n", "self-hosted", "docker", "openai", "deepmind", "meta ai",
]

# Grok X検索クエリ（4本ローテーション）
GROK_QUERIES = [
    (
        "Search X/Twitter for the last 48h: Claude Code power users sharing tips, "
        "tricks, CLAUDE.md setups, and workflows. Also find comparisons between "
        "Claude Code vs Cursor vs Copilot vs Devin. Include usernames and URLs."
    ),
    (
        "Search X/Twitter for the last 48h: people sharing their AI automation "
        "revenue, MRR, client results. Indie hackers building AI SaaS or newsletters "
        "with concrete numbers. Include @username, revenue figures, and post URLs."
    ),
    (
        "Search X/Twitter for the last 48h: new AI tools, agent frameworks, or "
        "services that just launched. Anything that could be better than current "
        "tools (OpenClaw, n8n, LiteLLM etc). Include product names and URLs."
    ),
    (
        "Search X/Twitter for the last 48h: AI model pricing changes, free tier "
        "updates, API cost reductions from Anthropic, OpenAI, Google, xAI. "
        "Include specific numbers and effective dates."
    ),
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
    for d in [INTEL_DIR, RAW_DIR, SYNTH_DIR, WEEKLY_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)


def find_claude_bin() -> str | None:
    """Claude CLIバイナリを探す。"""
    import shutil
    # PATH から探す
    found = shutil.which("claude")
    if found:
        return found
    # 候補パスから探す
    for path in CLAUDE_BIN_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def get_api_keys() -> dict:
    """各種APIキーを環境変数と.envファイルから取得。"""
    keys = {
        "google": os.environ.get("GOOGLE_API_KEY"),
        "xai": os.environ.get("XAI_API_KEY"),
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
                    # export KEY=VALUE または KEY=VALUE 形式に対応
                    if line.startswith("export "):
                        line = line[7:]
                    if "=" not in line or line.startswith("#"):
                        continue
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == "GOOGLE_API_KEY" and not keys["google"]:
                        keys["google"] = v
                    elif k == "XAI_API_KEY" and not keys["xai"]:
                        keys["xai"] = v
                    elif k == "TELEGRAM_BOT_TOKEN" and not keys["telegram_token"]:
                        keys["telegram_token"] = v
                    elif k == "ALLOWED_USERS" and not keys["telegram_chat"]:
                        keys["telegram_chat"] = v
        except Exception:
            pass
    return keys


def load_state() -> dict:
    """前回の状態を読み込む（なければ空の状態を返す）。"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_synthesis": None,
        "acted_on": [],
        "skipped": [],
        "top_claude_code_version": None,
        "top_openclaw_version": None,
        "known_best_ai_agent_tool": "open-claw",
        "article_pipeline": [],
        "next_context": "初回実行。過去の文脈なし。",
        "weekly_insights": [],
    }


def save_state(state: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        log(f"  state.json 保存: {STATE_FILE}")
    except Exception as e:
        log(f"  state.json 保存エラー: {e}")


# =============================================================================
# Layer 0: 収集関数
# =============================================================================

def fetch_rss(feed: dict) -> list[dict]:
    """RSS フィードを取得してアイテムリストを返す。"""
    url = feed["url"]
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "HeyLoopIntelligence/2.0 (AI monitoring)"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        root = ET.fromstring(raw)
        # RSS 2.0
        ns = {}
        items = root.findall(".//item")
        # Atom フォールバック
        if not items:
            atom_ns = "http://www.w3.org/2005/Atom"
            items = root.findall(f".//{{{atom_ns}}}entry")

        results = []
        for item in items[:10]:
            title = (
                item.findtext("title") or
                item.findtext(f"{{{atom_ns}}}title") if not item.findtext("title") else item.findtext("title")
            )
            link = (
                item.findtext("link") or
                (item.find("link").get("href") if item.find("link") is not None else "")
            )
            pub = item.findtext("pubDate") or item.findtext("published") or ""
            desc = (item.findtext("description") or item.findtext("summary") or "")[:400]
            if title:
                results.append({
                    "title": (title or "").strip(),
                    "url": (link or "").strip(),
                    "published": pub.strip(),
                    "summary": desc.strip(),
                    "source": feed["name"],
                    "category": feed["category"],
                    "priority": feed["priority"],
                })
        log(f"  RSS [{feed['name']}]: {len(results)} 件")
        return results
    except Exception as e:
        log(f"  RSS [{feed['name']}] エラー: {e}")
        return []


def fetch_reddit(sub: dict) -> list[dict]:
    """Reddit サブレディットのホット投稿を取得。"""
    url = f"https://www.reddit.com/r/{sub['name']}/hot.json?limit={sub['limit']}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "HeyLoopIntelligence/2.0 (non-commercial research)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        posts = []
        for child in data.get("data", {}).get("children", []):
            d = child["data"]
            if d.get("stickied"):
                continue
            posts.append({
                "title": d.get("title", ""),
                "score": d.get("score", 0),
                "comments": d.get("num_comments", 0),
                "url": d.get("url", ""),
                "reddit_url": "https://reddit.com" + d.get("permalink", ""),
                "selftext": (d.get("selftext") or "")[:300],
                "subreddit": sub["name"],
                "category": sub["category"],
            })
        # スコア順にソート
        posts.sort(key=lambda p: p["score"], reverse=True)
        log(f"  Reddit r/{sub['name']}: {len(posts)} 件")
        return posts
    except Exception as e:
        log(f"  Reddit r/{sub['name']} エラー: {e}")
        return []


def fetch_hn(limit: int = 50) -> list[dict]:
    """Hacker News のトップストーリーからキーワードフィルタして返す。"""
    try:
        with urllib.request.urlopen(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15
        ) as resp:
            ids = json.loads(resp.read().decode("utf-8"))[:limit]
    except Exception as e:
        log(f"  HN トップ取得エラー: {e}")
        return []

    results = []
    for sid in ids:
        try:
            with urllib.request.urlopen(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10
            ) as resp:
                item = json.loads(resp.read().decode("utf-8"))
            if not item:
                continue
            title_lower = (item.get("title") or "").lower()
            matched = next((kw for kw in HN_KEYWORDS if kw in title_lower), None)
            if matched:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "score": item.get("score", 0),
                    "comments": item.get("descendants", 0),
                    "hn_url": f"https://news.ycombinator.com/item?id={sid}",
                    "matched_keyword": matched,
                })
        except Exception:
            pass
        time.sleep(0.05)

    results.sort(key=lambda x: x["score"], reverse=True)
    log(f"  HN: {len(results)} 件（top {limit} から）")
    return results[:15]


def fetch_github(repos: list[dict]) -> list[dict]:
    """GitHub リポジトリの最新リリース情報を取得。"""
    results = []
    for repo_info in repos:
        repo = repo_info["repo"]
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "HeyLoopIntelligence/2.0",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results.append({
                "repo": repo,
                "tag": data.get("tag_name", ""),
                "name": data.get("name", ""),
                "published": data.get("published_at", ""),
                "body": (data.get("body") or "")[:600],
                "url": data.get("html_url", ""),
                "category": repo_info["category"],
                "priority": repo_info["priority"],
            })
            log(f"  GitHub {repo}: {data.get('tag_name', 'no release')}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                log(f"  GitHub {repo}: リリースなし")
            else:
                log(f"  GitHub {repo}: HTTP {e.code}")
        except Exception as e:
            log(f"  GitHub {repo}: {e}")
        time.sleep(0.3)
    return results


def fetch_grok_x(xai_key: str, run_index: int) -> str | None:
    """Grok API で X/Twitter を検索（6時間ごとの呼び出し想定）。"""
    query = GROK_QUERIES[run_index % len(GROK_QUERIES)]
    payload = {
        "model": "grok-3",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an X/Twitter intelligence analyst. "
                    "Search for recent posts. Include @username, summary, "
                    "engagement if visible, and post URL. "
                    "Focus on concrete numbers and new tools."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{query}\n\n"
                    "Return top 5 most relevant posts. Format each as:\n"
                    "- @username: [summary]\n  URL: [url]\n  Signal: [key number or finding]"
                ),
            },
        ],
        "temperature": 0.3,
        "max_tokens": 1500,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {xai_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        text = result["choices"][0]["message"]["content"]
        log(f"  Grok X検索: 成功（{len(text)}字）")
        return text
    except Exception as e:
        log(f"  Grok X検索 エラー: {e}")
        return None


# =============================================================================
# Layer 0: メイン収集
# =============================================================================

def collect(keys: dict, grok_enabled: bool = False) -> dict:
    """全ソースからデータを収集してJSONに保存。"""
    log("=== Layer 0: データ収集開始 ===")
    ts = now_jst()

    raw_data = {
        "collected_at": ts.isoformat(),
        "rss": [],
        "reddit": [],
        "hn": [],
        "github": [],
        "grok_x": None,
    }

    # RSS
    log("RSS フィード収集中...")
    for feed in RSS_FEEDS:
        items = fetch_rss(feed)
        raw_data["rss"].extend(items)
        time.sleep(0.5)

    # Reddit（30分ごと収集ではサブセットのみ）
    log("Reddit 収集中...")
    hour = ts.hour
    # 奇数時間はAIツール系、偶数時間は収益系を優先
    subs_to_collect = SUBREDDITS if grok_enabled else SUBREDDITS[:8]
    for sub in subs_to_collect:
        posts = fetch_reddit(sub)
        raw_data["reddit"].extend(posts)
        time.sleep(1.0)

    # Hacker News
    log("HN 収集中...")
    raw_data["hn"] = fetch_hn(limit=50)

    # GitHub（3時間ごと = synth と同タイミング想定）
    log("GitHub 収集中...")
    raw_data["github"] = fetch_github(GITHUB_REPOS)

    # Grok X（6時間ごと、フラグがある時のみ）
    if grok_enabled and keys.get("xai"):
        log("Grok X 検索中...")
        run_idx = (hour // 6) % len(GROK_QUERIES)
        raw_data["grok_x"] = fetch_grok_x(keys["xai"], run_idx)
    else:
        log("  Grok X: スキップ（--synth 時のみ実行）")

    # ファイル保存
    filename = ts.strftime("%Y-%m-%d_%H%M") + ".json"
    filepath = os.path.join(RAW_DIR, filename)
    # latest.json も常に上書き（Opus が読む）
    latest_path = os.path.join(RAW_DIR, "latest.json")

    with open(filepath, "w") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)
    with open(latest_path, "w") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    total = (
        len(raw_data["rss"]) + len(raw_data["reddit"]) +
        len(raw_data["hn"]) + len(raw_data["github"])
    )
    log(f"収集完了: {total} 件 → {filepath}")
    return raw_data


# =============================================================================
# Layer 1: Opus 4.6 合成（claude --print）
# =============================================================================

def build_opus_prompt(state: dict) -> str:
    """Opus に渡すプロンプトを生成（短く、ファイル参照方式）。"""
    state_summary = json.dumps(
        {
            "last_synthesis": state.get("last_synthesis"),
            "top_claude_code_version": state.get("top_claude_code_version"),
            "top_openclaw_version": state.get("top_openclaw_version"),
            "known_best_ai_agent_tool": state.get("known_best_ai_agent_tool"),
            "next_context": state.get("next_context"),
            "article_pipeline": state.get("article_pipeline", [])[:3],
        },
        ensure_ascii=False,
    )

    return f"""あなたはHey Loop v2.0のインテリジェンスアナリストです。

## 前回の状態（閉ループ文脈）
{state_summary}

## タスク
以下のファイルを Read ツールで読んでください:
- 収集データ: {RAW_DIR}/latest.json

## 特別監視項目（最重要）
- Claude Code: バージョン変化・新機能・Breaking Change を必ず確認
- OpenClaw: バージョン変化・セキュリティ修正 を必ず確認
- 「OpenClawより優れたAIエージェントツール」の出現を検知

## 出力形式（JSONのみ。説明文は一切不要）
{{
  "top_insight": "最重要の発見1件（日本語、1文）",
  "action_for_naoto": "Naotoが今すぐ取れる最高価値アクション（日本語、1文、具体的に）",
  "claude_code_alert": "Claude Code/Anthropicの変化（なければnull）",
  "openclaw_alert": "OpenClawの変化（なければnull）",
  "better_tool_found": "OpenClawより優れたツールの発見（なければnull）",
  "ai_developments": ["AI業界の重要動向（最大3件）"],
  "revenue_signals": ["収益シグナル（@username + 数字 + URL、最大3件）"],
  "article_ideas": ["Nowpattern記事候補（力学・テーマ・角度、最大2件）"],
  "infrastructure_alerts": ["インフラ更新・脆弱性（必要な場合のみ、最大2件）"],
  "new_claude_code_version": "検出したClaude Codeバージョン（不明ならnull）",
  "new_openclaw_version": "検出したOpenClawバージョン（不明ならnull）",
  "next_context": "次回分析のための要点（日本語、2-3文）"
}}"""


def run_opus_synthesis(state: dict, dry_run: bool = False) -> dict | None:
    """claude --print でOpus 4.6に合成させる。"""
    claude_bin = find_claude_bin()
    if not claude_bin:
        log("  ❌ claude CLI が見つかりません。パスを確認してください。")
        log(f"  確認候補: {CLAUDE_BIN_CANDIDATES}")
        return None

    log(f"  Claude CLI: {claude_bin}")

    # 収集データが存在するか確認
    latest_path = os.path.join(RAW_DIR, "latest.json")
    if not os.path.exists(latest_path):
        log(f"  ❌ 収集データなし: {latest_path}")
        log("  先に --collect を実行してください")
        return None

    prompt = build_opus_prompt(state)
    prompt_file = f"/tmp/hey_loop_opus_prompt_{now_jst().strftime('%H%M%S')}.txt"

    if dry_run:
        log("  [dry-run] Opus プロンプト:")
        print(prompt[:500] + "...")
        return {"dry_run": True, "prompt_preview": prompt[:200]}

    # プロンプトをファイルに書いて stdin から渡す（長いプロンプト対策）
    with open(prompt_file, "w") as f:
        f.write(prompt)

    log(f"  Opus 4.6 呼び出し中...")
    try:
        result = subprocess.run(
            [
                claude_bin,
                "--print",
                prompt,
                "--allowedTools", "Read",
                "--output-format", "text",
            ],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=INTEL_DIR,  # CLAUDE.md があればここから読む
        )
    except subprocess.TimeoutExpired:
        log("  ❌ Opus タイムアウト（180秒）")
        return None
    except Exception as e:
        log(f"  ❌ Opus 実行エラー: {e}")
        return None
    finally:
        # 一時ファイル削除
        if os.path.exists(prompt_file):
            os.remove(prompt_file)

    if result.returncode != 0:
        log(f"  ❌ Opus 終了コード {result.returncode}")
        log(f"  stderr: {result.stderr[:300]}")
        # トークン期限切れの可能性
        if "oauth" in result.stderr.lower() or "token" in result.stderr.lower():
            log("  ⚠️ OAuthトークンが期限切れの可能性。ローカルPCで claude setup-token を実行してVPSにSCPしてください。")
        return None

    output = result.stdout.strip()
    log(f"  Opus 出力: {len(output)} 字")

    # JSON 抽出（```json ... ``` ブロックがある場合も対処）
    if "```json" in output:
        start = output.find("```json") + 7
        end = output.find("```", start)
        output = output[start:end].strip()
    elif "```" in output:
        start = output.find("```") + 3
        end = output.find("```", start)
        output = output[start:end].strip()

    try:
        parsed = json.loads(output)
        log("  ✅ Opus JSON パース成功")
        return parsed
    except json.JSONDecodeError as e:
        log(f"  ⚠️ JSON パース失敗: {e}")
        log(f"  生出力（先頭500字）: {output[:500]}")
        # パース失敗でも生テキストを返す
        return {"raw_text": output, "parse_error": str(e)}


# =============================================================================
# Layer 1: 合成メイン
# =============================================================================

def synth(keys: dict, dry_run: bool = False) -> dict | None:
    """Layer 1: 収集 → Opus合成 → 結果保存。"""
    log("=== Layer 1: Opus 4.6 合成開始 ===")

    # Grok X検索を合成時に実行（6時間ごとのタイミング）
    collect(keys, grok_enabled=True)

    state = load_state()
    synthesis = run_opus_synthesis(state, dry_run=dry_run)
    if not synthesis or synthesis.get("dry_run"):
        return synthesis

    # 合成結果を保存
    ts = now_jst()
    synth_file = os.path.join(SYNTH_DIR, ts.strftime("%Y-%m-%d_%H") + ".json")
    with open(synth_file, "w") as f:
        json.dump(synthesis, f, ensure_ascii=False, indent=2)
    log(f"  合成結果保存: {synth_file}")

    # state.json 更新（閉ループ）
    state["last_synthesis"] = ts.isoformat()
    state["next_context"] = synthesis.get("next_context", state.get("next_context"))
    if synthesis.get("new_claude_code_version"):
        state["top_claude_code_version"] = synthesis["new_claude_code_version"]
    if synthesis.get("new_openclaw_version"):
        state["top_openclaw_version"] = synthesis["new_openclaw_version"]
    if synthesis.get("better_tool_found"):
        state["known_best_ai_agent_tool"] = synthesis["better_tool_found"]
    # 記事パイプライン追加
    for idea in synthesis.get("article_ideas", []):
        if idea not in state.get("article_pipeline", []):
            state.setdefault("article_pipeline", []).append(idea)
    # 最大10件まで
    state["article_pipeline"] = state.get("article_pipeline", [])[-10:]

    save_state(state)
    return synthesis


# =============================================================================
# Layer 2: Telegram 報告
# =============================================================================

def format_telegram_report(synthesis: dict) -> str:
    """Opus合成結果を Telegram メッセージにフォーマット（200字以内を目標）。"""
    ts = now_jst().strftime("%m/%d %H:%M JST")
    lines = [f"🤖 Hey Loop v2.0 — {ts}"]
    lines.append("")

    # 最重要アラート（Claude Code/OpenClaw変化）
    alerts = []
    if synthesis.get("claude_code_alert"):
        alerts.append(f"⚡ Claude Code: {synthesis['claude_code_alert']}")
    if synthesis.get("openclaw_alert"):
        alerts.append(f"⚡ OpenClaw: {synthesis['openclaw_alert']}")
    if synthesis.get("better_tool_found"):
        alerts.append(f"🚨 新ツール発見: {synthesis['better_tool_found']}")

    if alerts:
        lines.append("【緊急アラート】")
        lines.extend(alerts)
        lines.append("")

    # トップ発見
    if synthesis.get("top_insight"):
        lines.append(f"🔥 {synthesis['top_insight']}")
        lines.append("")

    # Naotoへのアクション
    if synthesis.get("action_for_naoto"):
        lines.append(f"→ 今すぐ: {synthesis['action_for_naoto']}")
        lines.append("")

    # AI動向
    devs = synthesis.get("ai_developments", [])
    if devs:
        lines.append("📊 AI動向:")
        for d in devs[:2]:
            lines.append(f"  • {d}")
        lines.append("")

    # 収益シグナル
    rev = synthesis.get("revenue_signals", [])
    if rev:
        lines.append("💰 収益シグナル:")
        for r in rev[:2]:
            lines.append(f"  • {r}")
        lines.append("")

    # 記事候補
    ideas = synthesis.get("article_ideas", [])
    if ideas:
        lines.append(f"📰 記事候補: {ideas[0]}")

    # パースエラー時
    if "raw_text" in synthesis:
        lines = [f"🤖 Hey Loop v2.0 — {ts}", ""]
        lines.append("⚠️ JSON パース失敗 — 生テキスト:")
        lines.append(synthesis["raw_text"][:500])

    return "\n".join(lines)


def send_telegram(token: str, chat_id: str, text: str, dry_run: bool = False):
    """Telegram にメッセージ送信。"""
    if dry_run:
        log("[dry-run] Telegram 送信内容:")
        print(text)
        print(f"（{len(text)} 字）")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
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
            log("  ✅ Telegram 送信成功")
        else:
            log(f"  ❌ Telegram エラー: {result}")
    except Exception as e:
        log(f"  ❌ Telegram 送信失敗: {e}")


# =============================================================================
# Layer 4: 週次自己進化
# =============================================================================

def evolve(keys: dict, dry_run: bool = False):
    """週次: 過去7日分の synthesis を Opus が分析 → AGENT_WISDOM.md 更新。"""
    log("=== Layer 4: 週次自己進化 ===")

    claude_bin = find_claude_bin()
    if not claude_bin:
        log("  ❌ claude CLI なし")
        return

    # 過去7日分の synthesis ファイルを収集
    synth_files = sorted(Path(SYNTH_DIR).glob("*.json"))[-28:]  # 最大28ファイル
    if not synth_files:
        log("  synthesis ファイルがありません")
        return

    # ファイルリストをプロンプトに含める
    file_list = "\n".join([f"  - {f}" for f in synth_files])
    state = load_state()

    prompt = f"""あなたはHey Loop v2.0の自己進化エンジンです。

## タスク
過去7日間の分析結果を振り返り、システムを改善してください。

## 読むべきファイル（Read ツールで読んでください）
{file_list}

## 現在の状態
{json.dumps(state, ensure_ascii=False, indent=2)[:1000]}

## 現在の AGENT_WISDOM.md
{AGENT_WISDOM_FILE}

## 出力（JSONのみ）
{{
  "what_worked": ["効果があった情報・アクション（最大5件）"],
  "what_didnt_work": ["役に立たなかった情報タイプ（最大3件）"],
  "wisdom_to_add": ["AGENT_WISDOM.md に追加すべき教訓（最大3件）"],
  "topics_to_drop": ["監視をやめるべきトピック・ソース"],
  "topics_to_add": ["新たに監視すべきトピック・ソース"],
  "weekly_summary": "1週間のサマリー（Naotoへ、日本語3文）",
  "system_improvement": "スクリプト・設計への改善提案（あれば）",
  "flash_card_updates": [
    {{
      "key": "更新が必要な項目名（例: X_API_PRICING）",
      "old": "現在FLASH_CARDS.mdに書かれている内容（変化なければnull）",
      "new": "新しい正確な事実（変化なければnull）",
      "reason": "なぜ変更が必要か"
    }}
  ]
}}"""

    if dry_run:
        log("[dry-run] 週次進化プロンプト（先頭300字）:")
        print(prompt[:300])
        return

    log("Opus 週次分析中...")
    try:
        result = subprocess.run(
            [claude_bin, "--print", prompt, "--allowedTools", "Read", "--output-format", "text"],
            capture_output=True, text=True, timeout=300, cwd=INTEL_DIR,
        )
    except subprocess.TimeoutExpired:
        log("  ❌ 週次分析タイムアウト")
        return
    except Exception as e:
        log(f"  ❌ 週次分析エラー: {e}")
        return

    if result.returncode != 0:
        log(f"  ❌ 終了コード {result.returncode}")
        return

    output = result.stdout.strip()
    # JSON 抽出
    if "```json" in output:
        start = output.find("```json") + 7
        end = output.find("```", start)
        output = output[start:end].strip()

    try:
        weekly = json.loads(output)
    except Exception:
        log("  ⚠️ 週次JSON パース失敗")
        weekly = {"raw_text": output}

    # weekly 結果を保存
    ts = now_jst()
    weekly_file = os.path.join(WEEKLY_DIR, ts.strftime("%Y-%m-%d_weekly") + ".json")
    with open(weekly_file, "w") as f:
        json.dump(weekly, f, ensure_ascii=False, indent=2)
    log(f"  週次結果保存: {weekly_file}")

    # state に週次インサイトを記録
    state["weekly_insights"] = state.get("weekly_insights", [])
    state["weekly_insights"].append({
        "date": ts.isoformat(),
        "summary": weekly.get("weekly_summary", ""),
    })
    state["weekly_insights"] = state["weekly_insights"][-4:]  # 直近4週分のみ
    save_state(state)

    # Telegram に週次サマリーを送信
    summary = weekly.get("weekly_summary", "週次分析完了")
    token = keys.get("telegram_token")
    chat_id = keys.get("telegram_chat")
    if token and chat_id:
        msg = f"📈 Hey Loop 週次レポート\n\n{summary}"
        if weekly.get("wisdom_to_add"):
            msg += "\n\n💡 新しい教訓:\n"
            for w in weekly["wisdom_to_add"]:
                msg += f"  • {w}\n"
        # ★ FLASH_CARDS更新提案（重要：これがあれば必ずClaudeに適用させる）
        flash_updates = [u for u in weekly.get("flash_card_updates", []) if u.get("new")]
        if flash_updates:
            msg += "\n\n⚡ FLASH_CARDS.md 更新が必要:\n"
            for u in flash_updates:
                msg += f"  [{u['key']}] {u.get('old', '?')} → {u['new']}\n  理由: {u.get('reason', '')}\n"
            msg += "\n→ Claude Codeに「FLASH_CARDSを更新して」と指示してください"
        send_telegram(token, chat_id, msg)

    log("  ✅ 週次進化完了")


# =============================================================================
# メインエントリポイント
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Hey Loop Intelligence Feed v2.0")
    parser.add_argument("--collect", action="store_true", help="Layer 0: 収集のみ")
    parser.add_argument("--synth", action="store_true", help="Layer 1: Opus合成のみ（収集も実行）")
    parser.add_argument("--evolve", action="store_true", help="Layer 4: 週次自己進化")
    parser.add_argument("--dry-run", action="store_true", help="Telegram送信なし（テスト）")
    parser.add_argument("--no-grok", action="store_true", help="Grok X検索をスキップ")
    args = parser.parse_args()

    ensure_dirs()
    keys = get_api_keys()

    # デフォルト（引数なし）= フル実行
    if not any([args.collect, args.synth, args.evolve]):
        args.synth = True  # フル実行 = synth（内部で collect も呼ぶ）

    if args.collect:
        collect(keys, grok_enabled=not args.no_grok)
        return

    if args.synth:
        synthesis = synth(keys, dry_run=args.dry_run)
        if synthesis and not synthesis.get("dry_run"):
            msg = format_telegram_report(synthesis)
            token = keys.get("telegram_token")
            chat_id = keys.get("telegram_chat")
            if token and chat_id:
                send_telegram(token, chat_id, msg, dry_run=args.dry_run)
            elif not args.dry_run:
                log("  ⚠️ Telegram 設定なし（TELEGRAM_BOT_TOKEN / ALLOWED_USERS）")
                print("\n=== Telegram 報告内容（未送信） ===")
                print(msg)
        return

    if args.evolve:
        evolve(keys, dry_run=args.dry_run)
        return


if __name__ == "__main__":
    main()
