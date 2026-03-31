#!/usr/bin/env python3
"""
Breaking News Watcher v1.0
速報RSSを5分ごとにチェックし、新着10分以内の高スコア記事に対して
Flash記事を自動生成 → Ghost公開 → X引用リポストを行う。

フロー:
  RSS取得 → 新着10分チェック → スコア評価(>=7) → ソースツイート検索
  → Flash記事生成(claude -p) → Ghost公開 → prediction_db追記
  → Xにquote-repost → リプライでGhost記事URL投稿

実行: cron */5 * * * *
ログ: /opt/shared/scripts/breaking-news.log
状態: /opt/shared/state/breaking_seen.json (24h保持)
"""

import json
import os
import sys
import time
import subprocess
import hashlib
import hmac
import base64
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from email.utils import parsedate_to_datetime

from article_factcheck_postprocess import fact_check_and_revise_generated_article
from mission_contract import assert_mission_handshake
from release_governor import evaluate_governed_release
from article_truth_guard import evaluate_article_truth

MISSION_HANDSHAKE = assert_mission_handshake(
    "breaking-news-watcher",
    "watch and generate breaking news only inside the shared founder mission contract",
)
# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path("/opt/shared/scripts")
STATE_DIR = Path("/opt/shared/state")
STATE_FILE = STATE_DIR / "breaking_seen.json"
LOG_FILE = SCRIPTS_DIR / "breaking-news.log"

GHOST_URL = "https://nowpattern.com"
FRESHNESS_MINUTES = 10      # 公開後この分以内の記事のみ処理
MAX_PER_RUN = 2             # 1回の実行で最大処理件数
MIN_SCORE = 6               # この閾値以上のみFlash生成
CLAUDE_TIMEOUT = 240        # Flash生成タイムアウト(秒)
SEEN_EXPIRY_HOURS = 24      # 既処理URLの保持時間

X_MAX_CHARS = 4000          # X Premiumは25000文字まで可能だが実用的な長さに

RSS_FEEDS = [
    # JA feeds
    {"url": "https://www3.nhk.or.jp/rss/news/cat4.xml",        "lang": "ja", "media": "NHK",          "base_cat": "政治"},
    {"url": "https://www3.nhk.or.jp/rss/news/cat6.xml",        "lang": "ja", "media": "NHK",          "base_cat": "経済"},
    {"url": "https://www3.nhk.or.jp/rss/news/cat0.xml",        "lang": "ja", "media": "NHK",          "base_cat": "国際"},
    {"url": "https://news.yahoo.co.jp/rss/topics/business.xml","lang": "ja", "media": "Yahoo",         "base_cat": "経済"},
    {"url": "https://news.yahoo.co.jp/rss/topics/world.xml",   "lang": "ja", "media": "Yahoo",         "base_cat": "国際"},
    {"url": "https://news.yahoo.co.jp/rss/topics/it.xml",      "lang": "ja", "media": "Yahoo",         "base_cat": "AI"},
    {"url": "https://coinpost.jp/?feed=rss2",                  "lang": "ja", "media": "CoinPost",      "base_cat": "暗号資産"},
    {"url": "https://jp.cointelegraph.com/rss",                "lang": "ja", "media": "CoinTelegraph", "base_cat": "暗号資産"},
    # EN feeds
    {"url": "https://www.aljazeera.com/xml/rss/all.xml",       "lang": "en", "media": "AlJazeera",    "base_cat": "国際"},
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml",     "lang": "en", "media": "BBC",           "base_cat": "国際"},
    {"url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",     "lang": "en", "media": "WSJ",           "base_cat": "国際"},
    {"url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "lang": "en", "media": "CoinDesk",      "base_cat": "暗号資産"},
    {"url": "https://cointelegraph.com/rss",                   "lang": "en", "media": "CoinTelegraph", "base_cat": "暗号資産"},
    {"url": "https://www.technologyreview.com/feed/",          "lang": "en", "media": "MIT Tech",      "base_cat": "AI"},
    {"url": "https://thehill.com/feed/",                       "lang": "en", "media": "TheHill",       "base_cat": "政治"},
    {"url": "https://thediplomat.com/feed/",                   "lang": "en", "media": "The Diplomat",  "base_cat": "地政学"},
]

# ニュースソースドメイン → X(Twitter)ハンドル の対応表
DOMAIN_TO_HANDLE = {
    "nhk.or.jp":          "nhk_news",
    "nhk.jp":             "nhk_news",
    "yahoo.co.jp":        "YahooNewsTopics",
    "coinpost.jp":        "CoinPost_JP",
    "jp.cointelegraph.com": "JpCointelegraph",
    "cointelegraph.com":  "Cointelegraph",
    "aljazeera.com":      "AJEnglish",
    "bbc.co.uk":          "BBCBreaking",
    "bbc.com":            "BBC",
    "wsj.com":            "WSJ",
    "coindesk.com":       "CoinDesk",
    "technologyreview.com": "techreview",
    "thehill.com":        "thehill",
    "thediplomat.com":    "the_diplomat",
    "foreignpolicy.com":  "ForeignPolicy",
    "reuters.com":        "Reuters",
    "apnews.com":         "AP",
    "bloomberg.com":      "Bloomberg",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def load_env() -> dict:
    env = {}
    try:
        for line in open("/opt/cron-env.sh"):
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception as e:
        log(f"WARNING: cron-env.sh read failed: {e}")
    return env


# ---------------------------------------------------------------------------
# State (deduplication)
# ---------------------------------------------------------------------------

def load_seen() -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_seen(seen: dict):
    # Expire entries older than SEEN_EXPIRY_HOURS
    cutoff = (datetime.utcnow() - timedelta(hours=SEEN_EXPIRY_HOURS)).isoformat()
    seen = {k: v for k, v in seen.items() if v > cutoff}
    STATE_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_seen(seen: dict, url: str):
    seen[url] = datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# RSS Fetch
# ---------------------------------------------------------------------------

def fetch_rss(feed_url: str, timeout: int = 15) -> list[dict]:
    """RSSを取得してアイテムリストを返す"""
    try:
        req = urllib.request.Request(
            feed_url,
            headers={"User-Agent": "Mozilla/5.0 Nowpattern-Bot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log(f"  RSS fetch failed {feed_url}: {e}")
        return []

    items = []
    # Simple regex-based RSS/Atom parser (avoids lxml dependency)
    item_blocks = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)
    if not item_blocks:
        item_blocks = re.findall(r"<entry>(.*?)</entry>", content, re.DOTALL)

    for block in item_blocks:
        title = _extract_tag(block, "title")
        link = _extract_tag(block, "link") or _extract_attr(block, "link", "href")
        pub_date = _extract_tag(block, "pubDate") or _extract_tag(block, "published") or _extract_tag(block, "updated")
        description = _extract_tag(block, "description") or _extract_tag(block, "summary") or ""
        description = re.sub(r"<[^>]+>", "", description)[:500]
        if title and link:
            items.append({
                "title": title.strip(),
                "link": link.strip(),
                "pub_date": pub_date.strip() if pub_date else "",
                "description": description.strip(),
            })
    return items


def _extract_tag(text: str, tag: str) -> str:
    m = re.search(rf"<{tag}[^>]*>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</{tag}>", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_attr(text: str, tag: str, attr: str) -> str:
    m = re.search(rf'<{tag}[^>]*\s{attr}="([^"]+)"', text)
    return m.group(1) if m else ""


def is_fresh(pub_date_str: str) -> bool:
    """記事が FRESHNESS_MINUTES 以内に公開されたかチェック"""
    if not pub_date_str:
        return False
    try:
        dt = parsedate_to_datetime(pub_date_str)
        now = datetime.now(timezone.utc)
        age = (now - dt).total_seconds() / 60
        return 0 <= age <= FRESHNESS_MINUTES
    except Exception:
        pass
    # Try ISO format
    try:
        dt = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age = (now - dt).total_seconds() / 60
        return 0 <= age <= FRESHNESS_MINUTES
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

HIGH_VALUE_KEYWORDS = [
    # 経済・金融
    "利上げ", "利下げ", "金利", "GDP", "インフレ", "デフレ", "株価", "円安", "円高",
    "interest rate", "rate hike", "rate cut", "inflation", "gdp", "recession",
    # 地政学
    "戦争", "紛争", "制裁", "外交", "首脳会談", "条約",
    "war", "conflict", "sanction", "summit", "treaty", "invasion",
    # 暗号資産
    "ビットコイン", "イーサリアム", "SEC", "ETF", "規制", "取引所",
    "bitcoin", "ethereum", "crypto", "blockchain", "exchange", "regulation",
    # AI・テック
    "AI", "人工知能", "ChatGPT", "GPT", "モデル", "規制", "半導体",
    "artificial intelligence", "chip", "semiconductor", "model", "release",
    # 企業・市場
    "買収", "合併", "倒産", "IPO", "決算", "利益", "損失",
    "acquisition", "merger", "bankruptcy", "ipo", "earnings", "profit",
    # 地政学・政治リーダー
    "攻撃", "危機", "衝突", "警告", "封鎖", "侵攻", "爆発", "決断",
    "大統領", "首相", "外相", "閣僚", "緊急会議", "辞任",
    "attack", "crisis", "clash", "warning", "blockade", "explosion",
    # 相場急変
    "急減", "急増", "過去最高", "過去最低", "最安値", "最高値",
    "record high", "record low", "all-time high", "collapse",

    # 緊急性
    "速報", "緊急", "突発", "急落", "急騰", "暴落",
    "breaking", "urgent", "crash", "surge", "plunge", "soar",
]


def score_article(title: str, description: str, base_cat: str) -> int:
    """記事の重要度スコア(0-10)を算出"""
    text = (title + " " + description).lower()
    score = 4  # base score

    # Keyword bonus
    keyword_hits = sum(1 for kw in HIGH_VALUE_KEYWORDS if kw.lower() in text)
    score += min(keyword_hits, 4)

    # Category bonus
    if base_cat in ("暗号資産", "AI"):
        score += 1
    if base_cat in ("経済", "国際"):
        score += 0

    # Urgency keywords
    if any(kw in text for kw in ["速報", "緊急", "breaking", "urgent", "alert"]):
        score += 2

    return min(score, 10)


# ---------------------------------------------------------------------------
# X API: Tweet Search
# ---------------------------------------------------------------------------

def find_source_tweet(article_url: str, media: str, bearer_token: str) -> str | None:
    """記事URLに関連するツイートを検索してURLを返す"""
    if not bearer_token:
        return None

    # ドメイン → ハンドル変換
    domain = urllib.parse.urlparse(article_url).netloc.replace("www.", "")
    handle = DOMAIN_TO_HANDLE.get(domain, "")

    # 検索クエリ: メディアのハンドルからの最新ツイートを検索
    if handle:
        query = f"from:{handle} -is:retweet"
    else:
        # ハンドル不明ならURLドメインで検索
        query = f"url:{domain} -is:retweet lang:ja OR lang:en"

    params = urllib.parse.urlencode({
        "query": query,
        "max_results": 5,
        "tweet.fields": "created_at,author_id",
        "sort_order": "recency",
    })

    try:
        req = urllib.request.Request(
            f"https://api.twitter.com/2/tweets/search/recent?{params}",
            headers={"Authorization": f"Bearer {bearer_token}"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            tweets = data.get("data", [])
            if tweets:
                tweet_id = tweets[0]["id"]
                return f"https://x.com/i/web/status/{tweet_id}"
    except Exception as e:
        log(f"  Tweet search failed: {e}")

    return None


# ---------------------------------------------------------------------------
# Ghost JWT
# ---------------------------------------------------------------------------

def ghost_jwt(admin_api_key: str) -> str:
    key_id, secret = admin_api_key.split(":")
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT", "kid": key_id}).encode()).rstrip(b"=")
    now = int(time.time())
    payload = base64.urlsafe_b64encode(json.dumps({"iat": now, "exp": now + 300, "aud": "/admin/"}).encode()).rstrip(b"=")
    sig_input = header + b"." + payload
    sig = base64.urlsafe_b64encode(
        hmac.new(bytes.fromhex(secret), sig_input, "sha256").digest()
    ).rstrip(b"=")
    return (sig_input + b"." + sig).decode()


# ---------------------------------------------------------------------------
# Flash Article Generation
# ---------------------------------------------------------------------------

FLASH_PROMPT = """あなたはNowpatternの速報アナリストです。
以下のニュース記事について、Flash Analysisを生成してください。

ニュース:
タイトル: {title}
ソース: {media}
概要: {description}
URL: {url}

以下のJSON形式で出力してください（コードブロック不要、JSONのみ）:
{{
  "title": "日本語の記事タイトル（50文字以内）",
  "fast_read": "1分要約（200字以内）。何が起きたか・なぜ重要か・次に何が起きるかを3文で",
  "signal": "シグナル分析（400字以内）。事実・歴史的背景・なぜ今重要かを分析",
  "between_lines": "行間を読む（300字以内）。報道が言っていない本質・インサイダー視点",
  "scenarios": {{
    "optimistic": {{"label": "楽観", "prob": 30, "description": "100字以内"}},
    "base": {{"label": "基本", "prob": 50, "description": "100字以内"}},
    "pessimistic": {{"label": "悲観", "prob": 20, "description": "100字以内"}}
  }},
  "oracle_question": "判定可能な予測質問（例: 〇〇は2026年Q2までに〜するか？）",
  "oracle_pick": "YES",
  "oracle_pick_prob": 65,
  "oracle_deadline": "2026-06-30",
  "x_post_text": "X投稿文（500字以内）。速報感・インサイト・#Nowpattern #ニュース分析 必須。記事URLは含めない",
  "genre_tags": "geopolitics",
  "event_tags": "structural-shift",
  "dynamics_tags": "platform-power"
}}

タグは必ず以下のリストから選択:
genre: geopolitics, technology, economy-trade, social-change, security-conflict, environment-energy, finance-markets, media-information, health-bio, culture-sports, science-space, law-justice, crypto-web3
event: structural-shift, leadership-change, policy-decision, market-move, social-unrest, judicial-action, tech-breakthrough, conflict-escalation, economic-crisis, corporate-move, election-politics, treaty-diplomacy, natural-disaster, scientific-discovery, institutional-change, media-event, regulatory-action, financial-event, cultural-moment
dynamics: platform-power, regulatory-capture, network-effects, information-asymmetry, first-mover, disruption, consolidation, polarization, systemic-risk, narrative-control, liquidity-crisis, arms-race-dynamics, demographic-shift, trust-erosion, innovation-diffusion, power-vacuum"""


def generate_flash_article(title: str, media: str, description: str, url: str, lang: str) -> dict | None:
    """claude -p でFlash記事JSONを生成"""
    prompt = FLASH_PROMPT.format(
        title=title,
        media=media,
        description=description[:800],
        url=url,
    )

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT,
            env={**os.environ, "HOME": "/root"},
        )
        output = result.stdout.strip()
        if not output:
            log(f"  Flash gen: empty output. stderr={result.stderr[:200]}")
            return None

        # JSON抽出
        json_match = re.search(r"\{.*\}", output, re.DOTALL)
        if not json_match:
            log(f"  Flash gen: no JSON found in output")
            return None

        data = json.loads(json_match.group(0))
        return data

    except subprocess.TimeoutExpired:
        log(f"  Flash gen: timeout ({CLAUDE_TIMEOUT}s)")
        return None
    except json.JSONDecodeError as e:
        log(f"  Flash gen: JSON parse error: {e}")
        return None
    except Exception as e:
        log(f"  Flash gen: error: {e}")
        return None


# ---------------------------------------------------------------------------
# Build Flash HTML
# ---------------------------------------------------------------------------

def build_flash_html(data: dict, source_url: str, media: str) -> str:
    """Flash記事のHTMLを構築"""
    scenarios = data.get("scenarios", {})
    opt = scenarios.get("optimistic", {})
    base = scenarios.get("base", {})
    pes = scenarios.get("pessimistic", {})

    html = f"""<div class="np-flash-article">

<div id="np-fast-read" class="np-fast-read">
<h2>⚡ FAST READ</h2>
<p>{data.get('fast_read', '')}</p>
<p><small>ソース: <a href="{source_url}" target="_blank">{media}</a> | Flash Analysis</small></p>
</div>

<hr>

<div id="np-signal">
<h2>📡 シグナル — 何が起きたか</h2>
<p>{data.get('signal', '')}</p>
</div>

<hr>

<div id="np-between-lines">
<h2>🔍 行間を読む — 報道が言っていないこと</h2>
<p>{data.get('between_lines', '')}</p>
</div>

<hr>

<h2>🔮 次のシナリオ</h2>
<div style="display:flex;gap:12px;flex-wrap:wrap;">
  <div style="flex:1;min-width:180px;padding:12px;background:#f0fdf4;border-radius:8px;">
    <strong>楽観 {opt.get('prob',0)}%</strong><br>{opt.get('description','')}
  </div>
  <div style="flex:1;min-width:180px;padding:12px;background:#eff6ff;border-radius:8px;">
    <strong>基本 {base.get('prob',0)}%</strong><br>{base.get('description','')}
  </div>
  <div style="flex:1;min-width:180px;padding:12px;background:#fef2f2;border-radius:8px;">
    <strong>悲観 {pes.get('prob',0)}%</strong><br>{pes.get('description','')}
  </div>
</div>

</div>"""

    # Oracle section if exists
    oracle_q = data.get("oracle_question", "")
    if oracle_q:
        html += f"""

<hr>

<div id="np-oracle">
<h2>🎯 オラクル宣言</h2>
<div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;">
<p><strong>判定質問:</strong> {oracle_q}</p>
<p><strong>Nowpatternの予測:</strong> {data.get('oracle_pick','YES')} — {data.get('oracle_pick_prob',60)}%確率</p>
<p><strong>判定日:</strong> {data.get('oracle_deadline','')}</p>
<p>↳ <a href="/predictions/">予測一覧</a></p>
</div>
</div>"""

    return html


# ---------------------------------------------------------------------------
# Ghost Publish
# ---------------------------------------------------------------------------

def publish_to_ghost(
    title: str,
    html: str,
    genre_tags: list[str],
    event_tags: list[str],
    dynamics_tags: list[str],
    source_url: str,
    admin_api_key: str,
    lang: str = "ja",
    status: str = "published",
) -> dict:
    """Ghost Admin APIに記事を公開する"""
    try:
        # Import publisher (reuse existing logic)
        sys.path.insert(0, str(SCRIPTS_DIR))
        from nowpattern_publisher import publish_deep_pattern
    except ImportError as e:
        log(f"  ERROR: Cannot import nowpattern_publisher: {e}")
        return {}

    article_id = f"flash-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    try:
        result = publish_deep_pattern(
            article_id=article_id,
            title=title,
            html=html,
            genre_tags=genre_tags[:2],
            event_tags=event_tags[:2],
            dynamics_tags=dynamics_tags[:3],
            source_urls=[source_url],
            ghost_url=GHOST_URL,
            admin_api_key=admin_api_key,
            status=status,
            title_en=title if lang == "en" else "",
        )
        return result
    except Exception as e:
        log(f"  Ghost publish error: {e}")
        return {}


# ---------------------------------------------------------------------------
# X Posting (Quote-Repost + Reply)
# ---------------------------------------------------------------------------

def post_to_x_v2(text: str, quote_tweet_url: str, env: dict) -> dict:
    """X API v2でツイートを投稿（quote tweet対応）"""
    api_key = env.get("TWITTER_API_KEY", "")
    api_secret = env.get("TWITTER_API_SECRET", "")
    access_token = env.get("TWITTER_ACCESS_TOKEN", "")
    access_secret = env.get("TWITTER_ACCESS_SECRET", "")

    if not all([api_key, api_secret, access_token, access_secret]):
        log("  SKIP X: credentials not set")
        return {}

    try:
        from requests_oauthlib import OAuth1
        import requests as req
    except ImportError:
        log("  ERROR X: requests_oauthlib not installed")
        return {}

    auth = OAuth1(api_key, api_secret, access_token, access_secret)
    payload = {"text": text[:X_MAX_CHARS]}
    if quote_tweet_url:
        payload["quote_tweet_id"] = _extract_tweet_id(quote_tweet_url)

    resp = req.post(
        "https://api.twitter.com/2/tweets",
        auth=auth,
        json=payload,
        timeout=30,
    )
    if resp.status_code in (200, 201):
        tweet_id = resp.json().get("data", {}).get("id", "")
        tweet_url = f"https://x.com/i/web/status/{tweet_id}"
        log(f"  OK X tweet: {tweet_url}")
        return {"tweet_id": tweet_id, "url": tweet_url}
    else:
        log(f"  ERROR X {resp.status_code}: {resp.text[:300]}")
        return {}


def post_reply_to_x(reply_text: str, in_reply_to_id: str, env: dict) -> dict:
    """先のツイートにリプライでGhost記事URLを投稿"""
    api_key = env.get("TWITTER_API_KEY", "")
    api_secret = env.get("TWITTER_API_SECRET", "")
    access_token = env.get("TWITTER_ACCESS_TOKEN", "")
    access_secret = env.get("TWITTER_ACCESS_SECRET", "")

    if not all([api_key, api_secret, access_token, access_secret]) or not in_reply_to_id:
        return {}

    try:
        from requests_oauthlib import OAuth1
        import requests as req
    except ImportError:
        return {}

    auth = OAuth1(api_key, api_secret, access_token, access_secret)
    payload = {
        "text": reply_text[:X_MAX_CHARS],
        "reply": {"in_reply_to_tweet_id": in_reply_to_id}
    }

    resp = req.post(
        "https://api.twitter.com/2/tweets",
        auth=auth,
        json=payload,
        timeout=30,
    )
    if resp.status_code in (200, 201):
        tweet_id = resp.json().get("data", {}).get("id", "")
        log(f"  OK X reply: https://x.com/i/web/status/{tweet_id}")
        return {"tweet_id": tweet_id}
    else:
        log(f"  ERROR X reply {resp.status_code}: {resp.text[:200]}")
        return {}


def _extract_tweet_id(tweet_url: str) -> str:
    m = re.search(r"/status/(\d+)", tweet_url)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Telegram Notification
# ---------------------------------------------------------------------------

def notify_telegram(msg: str, bot_token: str, chat_id: str):
    if not bot_token or not chat_id:
        return
    try:
        data = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        log(f"  Telegram notify failed: {e}")


# ---------------------------------------------------------------------------
# prediction_db update
# ---------------------------------------------------------------------------

def update_prediction_db(data: dict, ghost_article_url: str, lang: str):
    """prediction_db.jsonにFlash予測を追記"""
    oracle_q = data.get("oracle_question", "")
    if not oracle_q or not ghost_article_url:
        return

    db_path = SCRIPTS_DIR / "prediction_db.json"
    try:
        db = json.loads(db_path.read_text(encoding="utf-8")) if db_path.exists() else {"predictions": [], "stats": {}}
        preds = db.get("predictions", []) if isinstance(db, dict) else db

        existing_qs = [p.get("oracle_question", "") for p in preds if isinstance(p, dict)]
        if oracle_q in existing_qs:
            log("  prediction_db: oracle_question already exists, skipped")
            return

        existing_ids = [p.get("prediction_id", "") for p in preds if isinstance(p, dict)]
        nums = [int(pid.split("-")[-1]) for pid in existing_ids
                if pid.startswith("NP-2026-") and pid.split("-")[-1].isdigit()]
        next_num = max(nums) + 1 if nums else 1
        new_pid = f"NP-2026-{next_num:04d}"

        raw_prob = int(data.get("oracle_pick_prob", 60) or 60)
        def extremize(p, alpha=2.5):
            if p <= 0 or p >= 100: return p
            pr = p / 100.0
            ex = (pr ** alpha) / ((pr ** alpha) + ((1 - pr) ** alpha))
            return round(ex * 100)

        new_entry = {
            "prediction_id": new_pid,
            "title": data.get("title", ""),
            "ghost_url": ghost_article_url,
            "lang": lang,
            "status": "active",
            "our_pick": data.get("oracle_pick", "YES"),
            "our_pick_prob": extremize(raw_prob),
            "our_pick_prob_raw": raw_prob,
            "oracle_question": oracle_q,
            "oracle_deadline": data.get("oracle_deadline", ""),
            "oracle_criteria": "",
            "resolution_question": oracle_q,
            "triggers": [],
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "market_consensus": {},
            "article_type": "flash",
        }
        preds.append(new_entry)

        if isinstance(db, dict) and "stats" in db:
            db["stats"]["total"] = len(preds)
            db["stats"]["open"] = sum(1 for p in preds if p.get("status") in ("active", "open"))
            db["stats"]["last_updated"] = datetime.now().isoformat()

        db_path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"  prediction_db: {new_pid} added")
    except Exception as e:
        log(f"  prediction_db update failed: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log("=== breaking-news-watcher START ===")

    env = load_env()
    seen = load_seen()

    admin_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY") or env.get("GHOST_ADMIN_API_KEY", "")
    bearer_token = env.get("TWITTER_BEARER_TOKEN", "")
    bot_token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")

    processed = 0
    candidates = []

    # Step 1: Collect fresh high-score articles
    for feed in RSS_FEEDS:
        if processed >= MAX_PER_RUN:
            break
        items = fetch_rss(feed["url"])
        for item in items:
            url = item["link"]
            if url in seen:
                continue
            if not is_fresh(item["pub_date"]):
                continue
            score = score_article(item["title"], item["description"], feed["base_cat"])
            if score >= MIN_SCORE:
                candidates.append({
                    **item,
                    **feed,
                    "score": score,
                })

    # Sort by score desc, take top MAX_PER_RUN
    candidates.sort(key=lambda x: x["score"], reverse=True)
    candidates = candidates[:MAX_PER_RUN]

    if not candidates:
        log("No fresh high-score articles found. Exit.")
        save_seen(seen)
        return

    # Step 2: Process each candidate
    for cand in candidates:
        url = cand["link"]
        title = cand["title"]
        media = cand["media"]
        lang = cand["lang"]
        description = cand["description"]
        score = cand["score"]

        log(f"--- Processing [{score}/10] {title[:60]} ({media}) ---")
        mark_seen(seen, url)  # mark early to prevent parallel re-process

        source_truth_errors, _ = evaluate_article_truth(
            title=title,
            body_text=description,
            source_urls=[url],
            site_url=GHOST_URL,
            require_external_sources=True,
        )
        if source_truth_errors:
            log(f"  Truth guard blocked candidate: {source_truth_errors}")
            continue

        # Find source tweet
        source_tweet_url = find_source_tweet(url, media, bearer_token)
        log(f"  Source tweet: {source_tweet_url or 'not found'}")

        # Generate Flash article
        data = generate_flash_article(title, media, description, url, lang)
        if not data:
            log(f"  Flash generation failed, skip")
            continue

        factcheck = fact_check_and_revise_generated_article(
            data=data,
            source_urls=[url],
            lang=lang,
            mode="flash",
            site_url=GHOST_URL,
        )
        if not factcheck.get("ok"):
            log(f"  FACT-CHECK BLOCK: {factcheck.get('issues', [])}")
            if factcheck.get("summary"):
                log(f"  FACT-CHECK SUMMARY: {factcheck['summary']}")
            continue
        data = factcheck.get("data", data)
        if factcheck.get("summary"):
            log(f"  Post-gen fact-check: {factcheck['summary']}")

        article_title = data.get("title", title)
        log(f"  Generated: '{article_title}'")

        # Build HTML
        html = build_flash_html(data, url, media)

        article_truth_errors, _ = evaluate_article_truth(
            title=article_title,
            html=html,
            source_urls=[url],
            site_url=GHOST_URL,
            require_external_sources=True,
        )
        if article_truth_errors:
            log(f"  Truth guard blocked publish: {article_truth_errors}")
            continue

        # Parse tags
        genre_tags = [t.strip() for t in data.get("genre_tags", "geopolitics").split(",") if t.strip()]
        event_tags = [t.strip() for t in data.get("event_tags", "structural-shift").split(",") if t.strip()]
        dynamics_tags = [t.strip() for t in data.get("dynamics_tags", "platform-power").split(",") if t.strip()]

        release_block = evaluate_governed_release(
            title=article_title,
            html=html,
            source_urls=[url],
            tags=genre_tags + event_tags + dynamics_tags + [f"lang-{lang}"],
            site_url=GHOST_URL,
            status="published",
            channel="public",
            require_external_sources=True,
            check_source_fetchability=True,
        )
        blocking_errors = [
            err for err in release_block["errors"]
            if not err.startswith("HUMAN_APPROVAL_REQUIRED:")
        ]
        if blocking_errors:
            log(f"  Release blocker stopped publish: {blocking_errors}")
            continue
        publish_status = "published"
        if release_block["human_approval_required"] and not release_block["human_approval_present"]:
            publish_status = "draft"
            log(f"  High-risk flash article forced to DRAFT pending human approval: {release_block['risk_flags']}")

        # Publish to Ghost
        if not admin_key:
            log("  ERROR: GHOST_ADMIN_API_KEY not set, skip publish")
            continue

        ghost_result = publish_to_ghost(
            title=article_title,
            html=html,
            genre_tags=genre_tags,
            event_tags=event_tags,
            dynamics_tags=dynamics_tags,
            source_url=url,
            admin_api_key=admin_key,
            lang=lang,
            status=publish_status,
        )
        ghost_article_url = ghost_result.get("url", "")
        log(f"  Ghost: {ghost_article_url or 'FAILED'}")

        if not ghost_article_url:
            log("  Ghost publish failed, skip X post")
            continue

        if publish_status != "published":
            log("  Draft only; skip prediction_db + X distribution until human approval")
            continue

        # Update prediction_db
        update_prediction_db(data, ghost_article_url, lang)

        # Post to X (quote-repost source tweet or original tweet)
        x_text = data.get("x_post_text", "")
        if not x_text:
            x_text = f"【速報分析】{article_title}\n\n{data.get('fast_read','')[:200]}\n\n#Nowpattern #ニュース分析"

        # Ensure mandatory hashtags
        if "#Nowpattern" not in x_text:
            x_text += " #Nowpattern"
        if "#ニュース分析" not in x_text and lang == "ja":
            x_text += " #ニュース分析"
        if "#NewsAnalysis" not in x_text and lang == "en":
            x_text += " #NewsAnalysis"

        x_result = post_to_x_v2(
            text=x_text,
            quote_tweet_url=source_tweet_url or "",
            env=env,
        )

        # Reply with Ghost URL (X algorithm: link in reply not body)
        if x_result.get("tweet_id") and ghost_article_url:
            reply_text = f"📖 詳細分析 → {ghost_article_url}" if lang == "ja" else f"📖 Full analysis → {ghost_article_url}"
            post_reply_to_x(reply_text, x_result["tweet_id"], env)

        # Telegram notification
        tg_msg = (
            f"⚡ *[FLASH]* {article_title}\n"
            f"スコア: {score}/10 | ソース: {media}\n"
            f"Ghost: {ghost_article_url}\n"
            f"X: {x_result.get('url', 'なし')}"
        )
        notify_telegram(tg_msg, bot_token, chat_id)

        processed += 1
        log(f"  Done. processed={processed}/{MAX_PER_RUN}")

        # Rate limit pause
        if processed < len(candidates):
            time.sleep(30)

    save_seen(seen)
    log(f"=== breaking-news-watcher END (processed={processed}) ===")


if __name__ == "__main__":
    main()
