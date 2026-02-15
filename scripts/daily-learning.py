#!/usr/bin/env python3
"""
Hey Loop Intelligence System v3

4x daily intelligence gathering focused on BOTH infrastructure AND revenue.
Sends Telegram reports with article URLs, summaries, and monetization proposals.
Dynamically discovers new "information stars" — people making money with AI.

Data sources:
  1. Reddit (JSON API) — infrastructure + revenue subreddits
  2. Hacker News (Firebase API) — tech + business keywords
  3. GitHub (REST API) — dependency tracking + AI builder repos
  4. Gemini + Google Search grounding — deep research + dynamic discovery
  5. Grok/xAI (Chat API) — X/Twitter real-time intelligence

Schedule: 4x daily (every 6 hours)
  Run 0: 00:00 JST — Night scan (global markets, overnight news)
  Run 1: 06:00 JST — Morning briefing (main daily report)
  Run 2: 12:00 JST — Midday update (trending topics)
  Run 3: 18:00 JST — Evening review (summary + action items)

Usage:
  python3 daily-learning.py              # Auto-detect run based on JST hour
  python3 daily-learning.py --run 0      # Force specific run (0-3)
  python3 daily-learning.py --force      # Skip duplicate check
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# =============================================================================
# Config
# =============================================================================
LEARNING_DIR = "/opt/shared/learning"
WISDOM_FILE = "/opt/shared/AGENT_WISDOM.md"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

JST = timezone(timedelta(hours=9))

RUN_LABELS = {
    0: "Night Scan",
    1: "Morning Briefing",
    2: "Midday Update",
    3: "Evening Review",
}

# --- Subreddits (infrastructure + revenue) ---
INFRA_SUBREDDITS = [
    "selfhosted", "n8n", "docker", "PostgreSQL",
    "LocalLLaMA", "MachineLearning", "ClaudeAI",
    "Automate", "webdev", "netsec",
]

REVENUE_SUBREDDITS = [
    "AI_Agents", "SideProject", "EntrepreneurRideAlong",
    "passive_income", "newsletters", "SaaS",
    "indiehackers", "Entrepreneur", "startups",
    "juststart",
]

ALL_SUBREDDITS = INFRA_SUBREDDITS + REVENUE_SUBREDDITS

# --- GitHub repos (infrastructure + revenue/AI builders) ---
INFRA_GITHUB_REPOS = [
    "open-claw/open-claw",
    "n8n-io/n8n",
    "docker/compose",
    "langchain-ai/langchain",
    "anthropics/anthropic-sdk-python",
]

REVENUE_GITHUB_REPOS = [
    "joaomdmoura/crewAI",
    "langgenius/dify",
    "significant-gravitas/AutoGPT",
    "assafelovic/gpt-researcher",
    "Mintplex-Labs/anything-llm",
]

ALL_GITHUB_REPOS = INFRA_GITHUB_REPOS + REVENUE_GITHUB_REPOS

# --- Hacker News keywords (tech + business) ---
HN_KEYWORDS = [
    # Infrastructure
    "ai agent", "llm", "docker", "n8n", "postgres",
    "telegram bot", "self-hosted", "automation", "gemini",
    "claude", "grok", "vector database", "rag", "mcp", "open source",
    # Revenue / Business
    "newsletter", "content pipeline", "revenue", "startup",
    "saas", "monetize", "passive income", "indie hacker",
    "side project", "ai business", "pricing", "mrr",
    "subscription", "creator economy", "ai tool",
]

# --- Deep research topics (14 = ~3.5 day full rotation at 4x/day) ---
DEEP_TOPICS = [
    # Infrastructure (7)
    {
        "area": "AI Agent Architecture",
        "category": "infra",
        "search_query": (
            "multi-agent AI system architecture 2026 best practices coordination"
        ),
    },
    {
        "area": "Docker Security",
        "category": "infra",
        "search_query": (
            "Docker container security hardening 2026 non-root CVE"
        ),
    },
    {
        "area": "N8N Advanced Patterns",
        "category": "infra",
        "search_query": (
            "n8n workflow automation advanced patterns error handling 2026"
        ),
    },
    {
        "area": "LLM Cost Optimization",
        "category": "infra",
        "search_query": (
            "LLM API cost optimization prompt caching 2026 Gemini Claude"
        ),
    },
    {
        "area": "Content Automation Pipeline",
        "category": "infra",
        "search_query": (
            "AI newsletter automation pipeline Substack multilingual 2026"
        ),
    },
    {
        "area": "PostgreSQL Performance",
        "category": "infra",
        "search_query": (
            "PostgreSQL 16 17 performance tuning indexing 2026"
        ),
    },
    {
        "area": "Telegram Bot Best Practices",
        "category": "infra",
        "search_query": (
            "Telegram bot development python 2026 best practices webhook"
        ),
    },
    # Revenue (7)
    {
        "area": "AI Newsletter Revenue",
        "category": "revenue",
        "search_query": (
            "AI newsletter business revenue model 2026 Substack subscription "
            "earnings The Rundown Superhuman AI"
        ),
    },
    {
        "area": "AI Automation Agencies",
        "category": "revenue",
        "search_query": (
            "AI automation agency business model pricing clients 2026 "
            "revenue case study"
        ),
    },
    {
        "area": "AI SaaS Products",
        "category": "revenue",
        "search_query": (
            "AI SaaS product launch revenue MRR 2026 indie maker solo "
            "developer bootstrapped"
        ),
    },
    {
        "area": "Content Monetization Strategies",
        "category": "revenue",
        "search_query": (
            "AI content monetization multilingual newsletter sponsorship "
            "affiliate 2026 Asia"
        ),
    },
    {
        "area": "AI Builder Case Studies",
        "category": "revenue",
        "search_query": (
            "AI builder making money case study 2026 solo developer revenue "
            "journey transparent"
        ),
    },
    {
        "area": "Multilingual AI Content Business",
        "category": "revenue",
        "search_query": (
            "multilingual AI content creation translation business Asia "
            "Japan Korea 2026"
        ),
    },
    {
        "area": "AI Agent Marketplace",
        "category": "revenue",
        "search_query": (
            "AI agent marketplace selling bots automation service 2026 "
            "pricing gig economy"
        ),
    },
]

# --- Grok X/Twitter search queries (rotate per run) ---
GROK_SEARCH_QUERIES = [
    (
        "Search X/Twitter for posts from the last 48 hours about people "
        "sharing their AI automation agency revenue, clients, and business "
        "model. Find concrete numbers ($MRR, client count, pricing)."
    ),
    (
        "Search X/Twitter for posts from the last 48 hours about AI "
        "newsletter creators sharing subscriber growth, revenue, and "
        "monetization strategies. Find specific success stories."
    ),
    (
        "Search X/Twitter for posts from the last 48 hours about solo "
        "developers or indie hackers building AI tools/SaaS and sharing "
        "their revenue publicly. Find people with real traction."
    ),
    (
        "Search X/Twitter for posts from the last 48 hours about new AI "
        "models, API pricing changes, cost optimization techniques that "
        "could reduce our operational costs or improve our system."
    ),
]


# =============================================================================
# API Keys
# =============================================================================
def get_api_key():
    """Get Gemini API key from environment or .env file."""
    key = os.environ.get("GOOGLE_API_KEY")
    if key:
        return key

    env_paths = ["/opt/openclaw/.env", "/opt/shared/.env"]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GOOGLE_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def get_xai_api_key():
    """Get xAI API key from environment or .env files."""
    key = os.environ.get("XAI_API_KEY")
    if key:
        return key

    env_paths = [
        "/opt/openclaw/.env", "/opt/shared/.env", "/opt/.env",
        "/opt/claude-code-telegram/.env",
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("XAI_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def get_telegram_config():
    """Get Telegram bot token and owner chat ID from Neo's .env."""
    token = None
    chat_id = None
    env_path = "/opt/claude-code-telegram/.env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("ALLOWED_USERS="):
                    chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
    return token, chat_id


# =============================================================================
# Source 1: Reddit
# =============================================================================
def fetch_reddit(subreddit, limit=10):
    """Fetch hot posts from a subreddit via JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "HeyLoopIntelligence/3.0 (daily research; non-commercial)"
            )
        },
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
                    "permalink": "https://reddit.com" + d.get("permalink", ""),
                    "selftext": (d.get("selftext") or "")[:500],
                    "created": d.get("created_utc", 0),
                    "subreddit": subreddit,
                })
            return posts
    except Exception as e:
        print(f"  Reddit r/{subreddit} error: {e}")
        return []


def collect_reddit_data(run_number):
    """Collect posts from rotating subset of both infra and revenue subs."""
    day = datetime.now(JST).timetuple().tm_yday

    # Each run picks different subreddits: 3 infra + 3 revenue
    infra_start = ((day * 4 + run_number) * 3) % len(INFRA_SUBREDDITS)
    rev_start = ((day * 4 + run_number) * 3) % len(REVENUE_SUBREDDITS)

    todays_infra = [
        INFRA_SUBREDDITS[(infra_start + i) % len(INFRA_SUBREDDITS)]
        for i in range(3)
    ]
    todays_revenue = [
        REVENUE_SUBREDDITS[(rev_start + i) % len(REVENUE_SUBREDDITS)]
        for i in range(3)
    ]

    all_subs = todays_infra + todays_revenue
    print(f"  Infra subs: {', '.join(todays_infra)}")
    print(f"  Revenue subs: {', '.join(todays_revenue)}")

    all_posts = {}
    for sub in all_subs:
        posts = fetch_reddit(sub, limit=8)
        if posts:
            posts.sort(key=lambda p: p["score"], reverse=True)
            all_posts[sub] = posts[:5]
            print(f"  r/{sub}: {len(posts)} posts fetched")
        time.sleep(1.5)  # Respect rate limit

    return all_posts


# =============================================================================
# Source 2: Hacker News
# =============================================================================
def fetch_hn_top_stories(limit=30):
    """Fetch top stories from Hacker News, filtered by relevance."""
    url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            story_ids = json.loads(resp.read().decode("utf-8"))[:limit]
    except Exception as e:
        print(f"  HN top stories error: {e}")
        return []

    relevant = []
    for sid in story_ids:
        try:
            item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
            with urllib.request.urlopen(item_url, timeout=10) as resp:
                item = json.loads(resp.read().decode("utf-8"))
                if not item:
                    continue
                title = (item.get("title") or "").lower()
                for kw in HN_KEYWORDS:
                    if kw in title:
                        relevant.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "score": item.get("score", 0),
                            "comments": item.get("descendants", 0),
                            "hn_url": (
                                f"https://news.ycombinator.com/item?id={sid}"
                            ),
                            "matched_keyword": kw,
                        })
                        break
        except Exception:
            continue
        time.sleep(0.1)

    relevant.sort(key=lambda x: x["score"], reverse=True)
    print(f"  HN: {len(relevant)} relevant stories from top {limit}")
    return relevant[:10]


# =============================================================================
# Source 3: GitHub Releases
# =============================================================================
def fetch_github_updates(run_number):
    """Check latest releases. Full check on run 1, quick check on others."""
    # Full repo check on morning run (1), subset on other runs
    if run_number == 1:
        repos = ALL_GITHUB_REPOS
    else:
        # Alternate between infra and revenue repos
        repos = (
            INFRA_GITHUB_REPOS if run_number % 2 == 0
            else REVENUE_GITHUB_REPOS
        )

    updates = []
    for repo in repos:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "HeyLoopIntelligence/3.0",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                updates.append({
                    "repo": repo,
                    "tag": data.get("tag_name", ""),
                    "name": data.get("name", ""),
                    "published": data.get("published_at", ""),
                    "body": (data.get("body") or "")[:800],
                    "url": data.get("html_url", ""),
                })
                print(f"  GitHub {repo}: {data.get('tag_name', 'no release')}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  GitHub {repo}: no releases")
            else:
                print(f"  GitHub {repo}: HTTP {e.code}")
        except Exception as e:
            print(f"  GitHub {repo}: {e}")
        time.sleep(0.5)

    return updates


# =============================================================================
# Source 4: Gemini + Google Search grounding + Dynamic Discovery
# =============================================================================
def query_gemini_with_search(api_key, search_topic, context_data):
    """Query Gemini with Google Search grounding for real-time analysis."""
    url = f"{GEMINI_API_URL}?key={api_key}"

    prompt = f"""You are a technology + business intelligence analyst for
the "Hey Loop" project — an AI system that uses AI to generate returns
far exceeding token costs.

**Topic**: {search_topic['area']}
**Category**: {search_topic['category']}
**Search focus**: {search_topic['search_query']}

Raw data collected from Reddit and Hacker News:

{context_data}

Provide analysis in this format:

## Key Findings (from web search)
- Real news, releases, announcements from the past 7 days
- Include source URLs for EVERY claim
- For revenue topics: include specific dollar amounts, subscriber counts, growth rates

## Reddit & HN Highlights
- Most important discussions from the data above
- Include original post URLs
- Flag any revenue/business model discussions

## Revenue Signals
- Any information about people making money in this space
- Business models that are working RIGHT NOW
- Pricing data, revenue numbers, growth metrics
- Who is succeeding and how

## Actionable for Our System
- Specific things we should implement, change, or investigate
- For each action: estimated effort and potential revenue impact
- Be concrete: "Do X because Y, expected result Z"

## Newly Discovered Sources
- 2-3 NEW people, blogs, accounts, or newsletters relevant to this topic
  that are actively sharing valuable insights RIGHT NOW
- Include their URLs and what makes them worth following
- Prefer people who share revenue numbers publicly

## Warnings
- Breaking changes, deprecations, security issues
- Market shifts that could affect our strategy

Keep it factual. Every claim needs a source URL. No speculation."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.3},
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            parts = result["candidates"][0]["content"]["parts"]
            text_parts = [p["text"] for p in parts if "text" in p]
            return "\n".join(text_parts)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No details"
        print(f"  Gemini Search API error {e.code}: {error_body[:300]}")
        return None
    except Exception as e:
        print(f"  Gemini Search error: {e}")
        return None


# =============================================================================
# Source 5: Grok/xAI — X/Twitter real-time search
# =============================================================================
def search_x_via_grok(xai_key, run_number):
    """Use Grok API to search X/Twitter for real-time intelligence."""
    query = GROK_SEARCH_QUERIES[run_number % len(GROK_SEARCH_QUERIES)]

    payload = {
        "model": "grok-3",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an X/Twitter intelligence analyst. Search for "
                    "recent posts and threads. Always include the @username, "
                    "post content summary, engagement metrics if visible, "
                    "and the post URL. Focus on posts with real numbers "
                    "(revenue, subscribers, growth rates)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{query}\n\n"
                    "Return the top 5 most relevant and recent posts/threads. "
                    "Format each as:\n"
                    "- @username: [summary] (likes/retweets if visible)\n"
                    "  URL: [post URL]\n"
                    "  Revenue signal: [any concrete numbers mentioned]\n"
                ),
            },
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROK_API_URL,
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
            content = result["choices"][0]["message"]["content"]
            print(f"  Grok X search: {len(content)} chars")
            return content
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No details"
        print(f"  Grok API error {e.code}: {error_body[:300]}")
        return None
    except Exception as e:
        print(f"  Grok X search error: {e}")
        return None


# =============================================================================
# Report Formatting
# =============================================================================
def format_raw_data(reddit_data, hn_data, github_data, x_data):
    """Format raw collected data into readable context for Gemini."""
    sections = []

    if reddit_data:
        sections.append("### Reddit Posts")
        for sub, posts in reddit_data.items():
            is_revenue = sub in REVENUE_SUBREDDITS
            tag = "[REVENUE]" if is_revenue else "[INFRA]"
            for p in posts:
                sections.append(
                    f"- {tag} r/{sub}: \"{p['title']}\" "
                    f"(score:{p['score']}, comments:{p['comments']})"
                )
                sections.append(f"  URL: {p['permalink']}")
                if p["selftext"]:
                    sections.append(f"  Summary: {p['selftext'][:200]}")

    if hn_data:
        sections.append("\n### Hacker News Top Stories")
        for s in hn_data:
            sections.append(
                f"- \"{s['title']}\" (score:{s['score']}, "
                f"comments:{s['comments']}) [{s['matched_keyword']}]"
            )
            sections.append(f"  Article: {s['url']}")
            sections.append(f"  Discussion: {s['hn_url']}")

    if github_data:
        sections.append("\n### GitHub Releases")
        for g in github_data:
            if g["tag"]:
                sections.append(
                    f"- {g['repo']} -> {g['tag']} ({g['published'][:10]})"
                )
                sections.append(f"  URL: {g['url']}")
                if g["body"]:
                    sections.append(f"  Notes: {g['body'][:300]}")

    if x_data:
        sections.append("\n### X/Twitter Intelligence (via Grok)")
        sections.append(x_data)

    return "\n".join(sections) if sections else "(No raw data collected)"


# =============================================================================
# Report Saving
# =============================================================================
def save_report(run_number, topic, raw_data_text, analysis, reddit_data,
                hn_data, github_data, x_data, date_str):
    """Save the intelligence report with run number."""
    os.makedirs(LEARNING_DIR, exist_ok=True)

    area_slug = topic["area"].lower().replace(" ", "-").replace("&", "and")
    filename = f"{date_str}_run{run_number}_{area_slug}.md"
    filepath = os.path.join(LEARNING_DIR, filename)

    run_label = RUN_LABELS.get(run_number, f"Run {run_number}")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Hey Loop Intelligence: {topic['area']}\n")
        f.write(f"**Date**: {date_str} | **Run**: #{run_number} ({run_label})\n")
        f.write(f"**Category**: {topic['category'].upper()}\n")
        f.write(
            f"**Sources**: Reddit, Hacker News, GitHub, Gemini+Google Search"
        )
        if x_data:
            f.write(", Grok+X/Twitter")
        f.write(f"\n**Search focus**: {topic['search_query']}\n\n")
        f.write("---\n\n")

        # Analysis
        f.write("## Analysis (Gemini + Google Search grounding)\n\n")
        if analysis:
            f.write(analysis)
        else:
            f.write("*Gemini analysis failed. Review raw data below.*\n")

        f.write("\n\n---\n\n")

        # X/Twitter data
        if x_data:
            f.write("## X/Twitter Intelligence (Grok)\n\n")
            f.write(x_data)
            f.write("\n\n---\n\n")

        # Raw data
        f.write("## Raw Data Collected\n\n")
        f.write(raw_data_text)

        f.write("\n\n---\n\n")

        # Stats
        reddit_count = sum(
            len(v) for v in reddit_data.values()
        ) if reddit_data else 0
        f.write("## Collection Stats\n")
        f.write(f"- Reddit posts: {reddit_count}\n")
        f.write(f"- HN stories: {len(hn_data)}\n")
        f.write(f"- GitHub repos: {len(github_data)}\n")
        f.write(f"- Gemini web search: {'Yes' if analysis else 'Failed'}\n")
        f.write(f"- X/Twitter (Grok): {'Yes' if x_data else 'N/A'}\n")

    print(f"Saved: {filepath}")
    return filepath


def update_dashboard(run_number, topic, date_str, filepath, stats):
    """Update the learning dashboard."""
    dashboard_path = os.path.join(LEARNING_DIR, "DASHBOARD.md")

    entries = []
    if os.path.exists(dashboard_path):
        with open(dashboard_path, "r", encoding="utf-8") as f:
            content = f.read()
            for line in content.split("\n"):
                if line.startswith("| 2"):
                    entries.append(line)

    new_entry = (
        f"| {date_str} #{run_number} | {topic['area']} "
        f"[{topic['category']}] | "
        f"R:{stats['reddit']} HN:{stats['hn']} GH:{stats['github']} "
        f"X:{'Y' if stats.get('x') else 'N'} | "
        f"Pending | {os.path.basename(filepath)} |"
    )
    entries.insert(0, new_entry)
    entries = entries[:60]  # Keep 60 entries (15 days at 4x/day)

    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write("# Hey Loop Intelligence Dashboard\n\n")
        f.write("> 4x daily intelligence | Infrastructure + Revenue\n\n")
        f.write("| Date/Run | Topic [Category] | Sources | Status | File |\n")
        f.write("|----------|------------------|---------|--------|------|\n")
        for entry in entries:
            f.write(entry + "\n")
        f.write(f"\n\n*Last updated: {date_str} run #{run_number}*\n")

    print(f"Dashboard updated: {dashboard_path}")


# =============================================================================
# Telegram: Enhanced proposals with URLs + monetization ideas
# =============================================================================
def generate_proposals(api_key, run_number, topic, analysis, github_data,
                       x_data, stats):
    """Generate owner-facing Telegram report in Japanese with monetization."""
    url = f"{GEMINI_API_URL}?key={api_key}"

    run_label = RUN_LABELS.get(run_number, f"Run {run_number}")

    github_summary = ""
    for g in github_data:
        if g.get("tag"):
            github_summary += f"- {g['repo']}: {g['tag']}\n"

    x_summary = ""
    if x_data:
        x_summary = f"\n## X/Twitter情報:\n{x_data[:2000]}\n"

    prompt = f"""あなたはHey Loopプロジェクトの経済アナリスト兼テクノロジーアドバイザーです。
以下のインテリジェンスレポートから、オーナー（非エンジニア）への報告メッセージを作成してください。

## レポート情報
- Run: #{run_number} ({run_label})
- トピック: {topic['area']} [{topic['category']}]
- 収集: Reddit {stats['reddit']}件, HN {stats['hn']}件, GitHub {stats['github']}件

## 分析結果（抜粋）:
{(analysis or '分析失敗')[:3000]}

## 依存関係リリース:
{github_summary}
{x_summary}

## 報告フォーマット（必ずこの順番で書く）:

[注目ニュース] (最大3つ、URL必須)
1. タイトル
   URL: 記事のURL
   要約: 1行で何が重要か
   収益化: この情報をどうお金に変えられるか

[インフラ更新] (あれば)
- 依存関係のアップデート、セキュリティ警告

[新発見の情報源] (最大2つ)
- 新しく見つけた人物/ブログ/アカウント + URL + なぜフォローすべきか

[提案アクション] (最大3つ)
1. 何をすべきか → なぜ → 推定効果
   承認なら「やって」と返信

## ルール:
1. 全体700文字以内
2. 専門用語は（）で説明
3. URLは必ず含める（URLがない情報は省略）
4. 収益に関する話は最優先で記載
5. 「情報を見てどう稼ぐか」の視点を必ず入れる
6. 提案がない場合は「今回はアクション不要」と書く
7. オーナーが読んで5分で判断できるレベルに落とす"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.3},
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"  Proposal generation error: {e}")
        return None


def send_telegram(token, chat_id, message):
    """Send message(s) to owner via Telegram. Splits if > 4000 chars."""
    # Strip markdown (Telegram strict parser causes 400 errors)
    clean = message.replace("**", "").replace("*", "").replace("_", "")

    # Split into chunks at line boundaries
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
                    print(
                        f"  Telegram message {i + 1}/{len(chunks)} sent"
                    )
                else:
                    print(f"  Telegram error: {result}")
                    success = False
        except Exception as e:
            print(f"  Telegram send error: {e}")
            success = False
        if i < len(chunks) - 1:
            time.sleep(1)  # Avoid rate limiting between chunks

    return success


# =============================================================================
# Run Number Detection
# =============================================================================
def detect_run_number():
    """Auto-detect run number from current JST hour."""
    jst_hour = datetime.now(JST).hour
    return jst_hour // 6  # 0-5=0, 6-11=1, 12-17=2, 18-23=3


def parse_args():
    """Parse command-line arguments."""
    run_number = None
    force = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--run" and i + 1 < len(args):
            run_number = int(args[i + 1])
            i += 2
        elif args[i] == "--force":
            force = True
            i += 1
        else:
            i += 1

    if run_number is None:
        run_number = detect_run_number()

    return run_number, force


# =============================================================================
# Main
# =============================================================================
def main():
    run_number, force = parse_args()
    date_str = datetime.now(JST).strftime("%Y-%m-%d")
    jst_time = datetime.now(JST).strftime("%H:%M")
    run_label = RUN_LABELS.get(run_number, f"Run {run_number}")

    print(f"=== Hey Loop Intelligence v3 ===")
    print(f"Date: {date_str} | Time: {jst_time} JST")
    print(f"Run: #{run_number} ({run_label})")
    print()

    # Get API keys
    api_key = get_api_key()
    if not api_key:
        print("ERROR: No GOOGLE_API_KEY found.")
        sys.exit(1)

    xai_key = get_xai_api_key()
    if xai_key:
        print("xAI API key: found (X/Twitter search enabled)")
    else:
        print("xAI API key: not found (X/Twitter search disabled)")

    # Pick today's deep-research topic
    day = datetime.now(JST).timetuple().tm_yday
    topic_index = (day * 4 + run_number) % len(DEEP_TOPICS)
    topic = DEEP_TOPICS[topic_index]
    print(f"Topic: {topic['area']} [{topic['category']}]")

    # Duplicate check
    if not force:
        area_slug = (
            topic["area"].lower().replace(" ", "-").replace("&", "and")
        )
        expected = os.path.join(
            LEARNING_DIR, f"{date_str}_run{run_number}_{area_slug}.md"
        )
        if os.path.exists(expected):
            print(f"Already ran. File: {expected}")
            print("Use --force to re-run.")
            return

    # Phase 1: Collect from all sources
    print("\n--- Phase 1: Collecting real-world data ---")

    print("\n[Reddit]")
    reddit_data = collect_reddit_data(run_number)

    print("\n[Hacker News]")
    hn_data = fetch_hn_top_stories(limit=50)

    print("\n[GitHub]")
    github_data = fetch_github_updates(run_number)

    # Phase 2: X/Twitter via Grok (morning run only to conserve $5 credit)
    x_data = None
    if xai_key and run_number == 1:
        print("\n[X/Twitter via Grok]")
        x_data = search_x_via_grok(xai_key, run_number)
    elif xai_key:
        print("\n[X/Twitter] Skipped (Grok runs on morning briefing only)")
    else:
        print("\n[X/Twitter] Skipped (no xAI API key)")

    # Phase 3: Format raw data for Gemini
    raw_data_text = format_raw_data(reddit_data, hn_data, github_data, x_data)

    # Phase 4: Gemini analysis with Google Search grounding
    print("\n--- Phase 2: Gemini analysis with web search ---")
    analysis = query_gemini_with_search(api_key, topic, raw_data_text)

    if analysis:
        print(f"  Analysis received: {len(analysis)} chars")
    else:
        print("  WARNING: Gemini analysis failed, saving raw data only")

    # Phase 5: Save report
    print("\n--- Phase 3: Saving report ---")
    stats = {
        "reddit": sum(
            len(v) for v in reddit_data.values()
        ) if reddit_data else 0,
        "hn": len(hn_data),
        "github": len(github_data),
        "x": bool(x_data),
    }
    filepath = save_report(
        run_number, topic, raw_data_text, analysis,
        reddit_data, hn_data, github_data, x_data, date_str,
    )
    update_dashboard(run_number, topic, date_str, filepath, stats)

    # Phase 6: Telegram report with URLs + monetization proposals
    print("\n--- Phase 4: Sending Telegram report ---")
    tg_token, tg_chat_id = get_telegram_config()
    if tg_token and tg_chat_id:
        proposals = generate_proposals(
            api_key, run_number, topic, analysis, github_data, x_data, stats,
        )
        if proposals:
            header = (
                f"[Hey Loop #{run_number}] {run_label}\n"
                f"{date_str} {jst_time} JST\n"
                f"Topic: {topic['area']} [{topic['category']}]\n"
                f"---\n\n"
            )
            message = header + proposals
            send_telegram(tg_token, tg_chat_id, message)
        else:
            print("  WARNING: Could not generate proposals")
    else:
        print("  WARNING: Telegram config not found")

    # Summary
    print(f"\n=== Done ===")
    print(f"Report: {filepath}")
    print(
        f"Sources: Reddit({stats['reddit']}) + HN({stats['hn']}) + "
        f"GitHub({stats['github']}) + Gemini Search"
        + (f" + Grok/X" if x_data else "")
    )


if __name__ == "__main__":
    main()
