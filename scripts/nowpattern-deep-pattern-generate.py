#!/usr/bin/env python3
"""
nowpattern-deep-pattern-generate.py — Deep Pattern記事自動生成パイプライン
═══════════════════════════════════════════════════════════════════

フロー:
  1. rss_article_queue.json から未投稿 + 分析済み記事を選択
  2. Claude Opus 4.6 (Max subscription, claude CLI -p) で構造化Deep Pattern分析
  3. nowpattern_article_builder.py で HTML生成
  4. nowpattern_publisher.py で Ghost投稿
  5. キューに ghost_url を記録

品質ゲート:
  - 必須5セクション: facts / big_picture / stakeholder_map / scenarios / dynamics
  - 最低語数: EN 5,000語 / JA 6,000文字
  - 不合格 → ドラフト保存（公開しない）

LLM: Claude Opus 4.6 via Claude Code CLI (Max subscription, 定額)
"""

import json
import os
import sys
import subprocess
import time
import re
from datetime import datetime
from pathlib import Path

# ===== パス =====
SCRIPTS_DIR = Path(__file__).parent
QUEUE_FILE = SCRIPTS_DIR / "rss_article_queue.json"
TAXONOMY_FILE = SCRIPTS_DIR / "nowpattern_taxonomy.json"
PROMPT_FILE = Path("/opt/shared/articles/NOWPATTERN_NEWS_ANALYST_PROMPT.md")
LOG_FILE = SCRIPTS_DIR / "deep-pattern-generate.log"
CRON_ENV = Path("/opt/cron-env.sh")

# ===== 設定 =====
MAX_PER_RUN = 1  # 1回のcronで最大1記事（レート制限回避）
GHOST_URL = "https://nowpattern.com"
MIN_WORDS_EN = 4000  # 英語最低語数（Deep Pattern品質）
MIN_CHARS_JA = 5000  # 日本語最低文字数

# JSON Schema for Claude structured output
DEEP_PATTERN_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Deep Pattern article title (compelling, 60-80 chars)"},
        "why_it_matters": {"type": "string", "description": "1-2 sentence hook explaining why this matters NOW"},
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["category", "content"]
            },
            "description": "Key facts extracted from the news (8-15 facts)"
        },
        "big_picture_history": {"type": "string", "description": "Historical context: why this is happening now (500+ words)"},
        "stakeholder_map": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "actor": {"type": "string"},
                    "public_position": {"type": "string"},
                    "private_interest": {"type": "string"},
                    "gains": {"type": "string"},
                    "loses": {"type": "string"}
                },
                "required": ["actor", "public_position", "private_interest", "gains", "loses"]
            },
            "description": "4-8 stakeholders with their stated vs real motivations"
        },
        "data_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "value": {"type": "string"}
                },
                "required": ["metric", "value"]
            },
            "description": "5-10 key data points with numbers"
        },
        "delta": {"type": "string", "description": "The key insight: what changed and why it matters"},
        "genre_tags": {"type": "string", "description": "Comma-separated genre tags from taxonomy"},
        "event_tags": {"type": "string", "description": "Comma-separated event tags from taxonomy"},
        "dynamics_tags": {"type": "string", "description": "Comma-separated dynamics/NOW Pattern tags from taxonomy"},
        "dynamics_summary": {"type": "string", "description": "1-2 sentence summary of the dominant structural pattern"},
        "dynamics_sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "icon": {"type": "string"},
                    "summary": {"type": "string", "description": "200+ word explanation of this dynamic"}
                },
                "required": ["name", "icon", "summary"]
            },
            "description": "1-3 dynamics sections with deep explanations"
        },
        "dynamics_intersection": {"type": "string", "description": "How the dynamics interact and reinforce each other (200+ words)"},
        "pattern_history": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "year": {"type": "string"},
                    "event": {"type": "string"},
                    "pattern": {"type": "string"},
                    "lesson": {"type": "string"}
                },
                "required": ["year", "event", "pattern", "lesson"]
            },
            "description": "3-5 historical precedents showing the same pattern"
        },
        "history_pattern_summary": {"type": "string", "description": "What the historical pattern tells us (150+ words)"},
        "scenarios": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "Base case / Bull case / Bear case"},
                    "probability": {"type": "string", "description": "e.g. 50%"},
                    "description": {"type": "string", "description": "200+ word scenario description"},
                    "signals": {"type": "string", "description": "What to watch for"}
                },
                "required": ["label", "probability", "description", "signals"]
            },
            "description": "Exactly 3 scenarios: Base case, Bull case, Bear case"
        },
        "triggers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "trigger": {"type": "string"},
                    "timeframe": {"type": "string"}
                },
                "required": ["trigger", "timeframe"]
            },
            "description": "3-5 specific triggers to watch"
        },
        "source_urls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"}
                },
                "required": ["title", "url"]
            }
        }
    },
    "required": [
        "title", "why_it_matters", "facts", "big_picture_history",
        "stakeholder_map", "data_points", "delta",
        "genre_tags", "event_tags", "dynamics_tags",
        "dynamics_summary", "dynamics_sections", "dynamics_intersection",
        "pattern_history", "history_pattern_summary",
        "scenarios", "triggers"
    ]
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_env():
    env = {}
    if CRON_ENV.exists():
        with open(CRON_ENV) as f:
            for line in f:
                line = line.strip()
                if line.startswith("export ") and "=" in line:
                    k, v = line[7:].split("=", 1)
                    env[k] = v.strip().strip("\"'")
    return env


def load_queue():
    if not QUEUE_FILE.exists():
        return []
    with open(QUEUE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_queue(data):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_taxonomy():
    with open(TAXONOMY_FILE, encoding="utf-8") as f:
        return json.load(f)


def select_candidates(queue):
    """未投稿 + 分析済みの記事を品質順に選択"""
    candidates = []
    for i, entry in enumerate(queue):
        # Skip already posted to Ghost
        if entry.get("ghost_url"):
            continue
        # Skip entries with no analysis
        analysis = entry.get("analysis_full", "")
        if len(analysis) < 100:
            continue
        candidates.append((i, entry, len(analysis)))

    # Sort by analysis length descending (longer = richer material)
    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates[:MAX_PER_RUN]


def build_claude_prompt(entry, taxonomy, lang):
    """Claude Opus 4.6に渡すプロンプトを構築"""
    analysis = entry.get("analysis_full", "")
    title = entry.get("title", "")
    url = entry.get("url", "")

    # Build taxonomy reference
    tax_genres = ", ".join(g["name_en"] if lang == "en" else g["name_ja"] for g in taxonomy["genres"])
    tax_events = ", ".join(e["name_en"] if lang == "en" else e["name_ja"] for e in taxonomy["events"])
    tax_dynamics = ", ".join(d["name_en"] if lang == "en" else d["name_ja"] for d in taxonomy["dynamics"])

    lang_instruction = "Write ALL content in English." if lang == "en" else "Write ALL content in Japanese (日本語で書くこと)."

    prompt = f"""You are the Nowpattern Deep Pattern article generator.

Generate a comprehensive Deep Pattern analysis from the following news article and preliminary analysis.

{lang_instruction}

## Source Article
Title: {title}
URL: {url}
Language: {lang}

## Preliminary Analysis (expand and deepen this)
{analysis[:25000]}

## Taxonomy Reference (use ONLY these tags)
Genres: {tax_genres}
Events: {tax_events}
Dynamics (NOW Patterns): {tax_dynamics}

## Quality Requirements
1. Title: Compelling, specific, 60-80 characters. Format: "[Subject] — [Structural Insight]"
2. Facts: 8-15 extracted facts with categories
3. Big Picture: 500+ words of historical context explaining WHY this is happening now
4. Stakeholder Map: 4-8 players with public position vs private interest
5. Data Points: 5-10 quantified metrics
6. Dynamics: Deep structural pattern analysis (200+ words per dynamic)
7. Pattern History: 3-5 historical precedents showing the same pattern repeating
8. Scenarios: Exactly 3 (Base/Bull/Bear) with probabilities totaling ~100%, each 200+ words
9. Triggers: 3-5 specific events to watch with timeframes

IMPORTANT:
- genre_tags, event_tags, dynamics_tags must use EXACTLY the names from the taxonomy above (comma-separated)
- Each dynamics_section must have an icon emoji and 200+ word summary
- scenarios must have labels: "Base case", "Bull case", "Bear case" (English) or "基本", "楽観", "悲観" (Japanese)
- Be specific with numbers, dates, names. No vague generalities.
- The total article should be 5,000+ words (EN) or 6,000+ characters (JA)"""

    return prompt


def call_claude_opus(prompt, schema):
    """Claude Code CLI (-p) でOpus 4.6を呼び出し、JSON構造化出力を取得"""
    schema_str = json.dumps(schema)

    cmd = [
        "claude", "-p",
        "--model", "opus",
        "--output-format", "json",
        "--json-schema", schema_str,
        "--permission-mode", "acceptEdits",
        "--no-session-persistence",
        prompt
    ]

    log(f"  Calling Claude Opus 4.6 (prompt: {len(prompt)} chars)...")
    start = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout (Deep Pattern generation is long)
            cwd="/opt"
        )
    except subprocess.TimeoutExpired:
        log("  ERROR: Claude CLI timed out (10 min)")
        return None

    elapsed = time.time() - start
    log(f"  Claude responded in {elapsed:.1f}s")

    if result.returncode != 0:
        log(f"  ERROR: claude exit code {result.returncode}")
        log(f"  stderr: {result.stderr[:500]}")
        # Check for rate limit
        try:
            err_json = json.loads(result.stdout)
            if err_json.get("is_error") and "limit" in err_json.get("result", "").lower():
                log(f"  RATE LIMITED: {err_json['result']}")
                return "RATE_LIMITED"
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    # Parse JSON output
    try:
        output = json.loads(result.stdout)
        # claude --output-format json wraps in {"type":"result","result":...}
        if isinstance(output, dict):
            # Check for rate limit or error in successful response
            if output.get("is_error"):
                err_msg = output.get("result", "")
                if "limit" in err_msg.lower():
                    log(f"  RATE LIMITED: {err_msg}")
                    return "RATE_LIMITED"
                log(f"  ERROR from Claude: {err_msg}")
                return None
            if "result" in output:
                inner = output["result"]
                # The result may be a JSON string that needs parsing
                if isinstance(inner, str):
                    return json.loads(inner)
                return inner
        return output
    except json.JSONDecodeError as e:
        log(f"  ERROR: JSON parse failed: {e}")
        log(f"  stdout preview: {result.stdout[:500]}")
        return None


def quality_check(data, lang):
    """品質ゲート: 必須セクション + 最低語数チェック"""
    issues = []

    # Required sections
    for key in ["facts", "big_picture_history", "stakeholder_map", "scenarios", "dynamics_sections"]:
        val = data.get(key)
        if not val:
            issues.append(f"Missing: {key}")
        elif isinstance(val, list) and len(val) == 0:
            issues.append(f"Empty: {key}")

    # Facts count
    facts = data.get("facts", [])
    if len(facts) < 5:
        issues.append(f"Too few facts: {len(facts)} (need 5+)")

    # Scenarios count
    scenarios = data.get("scenarios", [])
    if len(scenarios) != 3:
        issues.append(f"Need exactly 3 scenarios, got {len(scenarios)}")

    # Word count check
    total_text = " ".join([
        data.get("why_it_matters", ""),
        data.get("big_picture_history", ""),
        data.get("delta", ""),
        data.get("dynamics_summary", ""),
        data.get("dynamics_intersection", ""),
        data.get("history_pattern_summary", ""),
    ])
    for s in data.get("stakeholder_map", []):
        total_text += " " + " ".join(s.values())
    for s in data.get("dynamics_sections", []):
        total_text += " " + s.get("summary", "")
    for s in data.get("scenarios", []):
        total_text += " " + s.get("description", "")

    if lang == "en":
        word_count = len(total_text.split())
        if word_count < MIN_WORDS_EN:
            issues.append(f"Too short: {word_count} words (need {MIN_WORDS_EN}+)")
    else:
        char_count = len(total_text.replace(" ", ""))
        if char_count < MIN_CHARS_JA:
            issues.append(f"Too short: {char_count} chars (need {MIN_CHARS_JA}+)")

    return issues


def generate_article(entry_index, entry, taxonomy, env):
    """1記事のDeep Pattern生成 → HTML → Ghost投稿"""
    title = entry.get("title", "Unknown")
    lang = entry.get("lang", "ja")
    url = entry.get("url", "")

    log(f"=== Generating Deep Pattern: {title[:60]} (lang={lang}) ===")

    # Step 1: Build prompt and call Claude
    prompt = build_claude_prompt(entry, taxonomy, lang)
    data = call_claude_opus(prompt, DEEP_PATTERN_SCHEMA)

    if data == "RATE_LIMITED":
        log("  RATE LIMITED: Stopping all generation for this run")
        return "RATE_LIMITED"

    if not data:
        log("  FAILED: No response from Claude")
        return False

    # Step 2: Quality check
    issues = quality_check(data, lang)
    status = "published" if not issues else "draft"
    if issues:
        log(f"  QUALITY ISSUES (posting as draft): {issues}")

    # Step 3: Build HTML using article builder
    sys.path.insert(0, str(SCRIPTS_DIR))
    from nowpattern_article_builder import build_deep_pattern_html
    from nowpattern_publisher import publish_deep_pattern, generate_article_id

    # Convert data to builder parameters
    facts_tuples = [(f["category"], f["content"]) for f in data.get("facts", [])]
    stakeholder_tuples = [
        (s["actor"], s["public_position"], s["private_interest"], s["gains"], s["loses"])
        for s in data.get("stakeholder_map", [])
    ]
    data_tuples = [(d["metric"], d["value"]) for d in data.get("data_points", [])]
    scenario_tuples = [
        (s["label"], s["probability"], s["description"], s["signals"])
        for s in data.get("scenarios", [])
    ]
    trigger_tuples = [(t["trigger"], t["timeframe"]) for t in data.get("triggers", [])]
    source_tuples = [(s["title"], s["url"]) for s in data.get("source_urls", [])]

    # Add original source URL
    if url and not any(u == url for _, u in source_tuples):
        source_tuples.insert(0, (title[:50], url))

    html = build_deep_pattern_html(
        title=data.get("title", title),
        why_it_matters=data.get("why_it_matters", ""),
        facts=facts_tuples,
        big_picture_history=data.get("big_picture_history", ""),
        stakeholder_map=stakeholder_tuples,
        data_points=data_tuples,
        delta=data.get("delta", ""),
        dynamics_tags=data.get("dynamics_tags", ""),
        dynamics_summary=data.get("dynamics_summary", ""),
        dynamics_sections=data.get("dynamics_sections", []),
        dynamics_intersection=data.get("dynamics_intersection", ""),
        pattern_history=data.get("pattern_history", []),
        history_pattern_summary=data.get("history_pattern_summary", ""),
        scenarios=scenario_tuples,
        triggers=trigger_tuples,
        genre_tags=data.get("genre_tags", ""),
        event_tags=data.get("event_tags", ""),
        source_urls=source_tuples,
        related_articles=[],
        diagram_html="",
        language=lang,
    )

    log(f"  HTML generated: {len(html)} chars")

    # Step 4: Publish to Ghost
    admin_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not admin_key:
        log("  ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not set")
        return False

    article_id = generate_article_id("deep_pattern")
    genre_list = [t.strip() for t in data.get("genre_tags", "").split(",") if t.strip()]
    event_list = [t.strip() for t in data.get("event_tags", "").split(",") if t.strip()]
    dynamics_list = [t.strip() for t in data.get("dynamics_tags", "").split(",") if t.strip()]

    result = publish_deep_pattern(
        article_id=article_id,
        title=data.get("title", title),
        html=html,
        genre_tags=genre_list,
        event_tags=event_list,
        dynamics_tags=dynamics_list,
        source_urls=[url] if url else [],
        ghost_url=GHOST_URL,
        admin_api_key=admin_key,
        status=status,
        language=lang,
    )

    ghost_url_result = result.get("url", "")
    log(f"  Published: {ghost_url_result} (status={status})")

    return ghost_url_result


def main():
    log("=" * 60)
    log("Deep Pattern Generator started")

    env = load_env()
    queue = load_queue()
    taxonomy = load_taxonomy()

    candidates = select_candidates(queue)
    if not candidates:
        log("No candidates found. Exiting.")
        return

    log(f"Found {len(candidates)} candidates")

    generated = 0
    for idx, entry, analysis_len in candidates:
        log(f"\n--- Candidate {idx}: {entry.get('title', '?')[:50]} ({analysis_len} chars) ---")

        result = generate_article(idx, entry, taxonomy, env)

        if result == "RATE_LIMITED":
            log("Rate limited. Stopping this run. Will retry next cron cycle.")
            break

        if result and isinstance(result, str) and result.startswith("http"):
            # Update queue
            queue[idx]["ghost_url"] = result
            queue[idx]["ghost_posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_queue(queue)
            generated += 1
            log(f"  Queue updated: ghost_url={result}")

    log(f"\nDone. Generated {generated}/{len(candidates)} articles.")


if __name__ == "__main__":
    main()
