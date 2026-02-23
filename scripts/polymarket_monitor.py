#!/usr/bin/env python3
"""
Polymarket Monitor v1.0 — Nowpattern予測市場インテリジェンス

Polymarket（予測市場）のリアルタイムオッズを監視し、
Nowpatternの記事執筆・予測追跡・分析強化に活用する。

3つの統合モード:
  1. TRIGGER: オッズが±10%以上動いたら記事トリガーアラート生成
  2. EMBED:   現在のオッズを記事テンプレート用JSONで出力
  3. BRIER:   Nowpatternの予測精度 vs 市場コンセンサスを比較

使い方:
  python3 polymarket_monitor.py                # スナップショット取得 + アラート
  python3 polymarket_monitor.py --mode trigger # アラートのみ
  python3 polymarket_monitor.py --mode embed   # 記事埋め込み用JSON出力
  python3 polymarket_monitor.py --mode brier   # Brier Score比較
  python3 polymarket_monitor.py --telegram     # Telegramにアラート送信

API: https://gamma-api.polymarket.com (公開、認証不要、無料)
法的: データ読み取りのみ（取引なし）。日本からの利用も問題なし。

連携先:
  - daily-learning.py: Phase 1のデータソースとして呼び出し
  - nowpattern_article_builder.py: embed JSONを記事に注入
  - /predictions/ ページ: Brier比較をトラッカーに表示
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# =============================================================================
# Config
# =============================================================================

BASE_URL = "https://gamma-api.polymarket.com"
DATA_DIR = "/opt/shared/polymarket"
SNAPSHOT_FILE = os.path.join(DATA_DIR, "latest_snapshot.json")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")
EMBED_FILE = os.path.join(DATA_DIR, "embed_data.json")

JST = timezone(timedelta(hours=9))

# Movement threshold for article trigger (10% = 0.10)
MOVEMENT_THRESHOLD = 0.10

# Minimum volume (USD) for a market to be interesting
MIN_VOLUME = 500_000

# Maximum events to fetch per scan
MAX_EVENTS = 50

# =============================================================================
# Genre-keyword mapping (Nowpattern taxonomy → Polymarket keywords)
# =============================================================================

GENRE_KEYWORDS = {
    "geopolitics": {
        "slug": "geopolitics",
        "name_ja": "地政学",
        "name_en": "Geopolitics",
        "keywords": [
            "war", "conflict", "diplomacy", "sanctions", "territory",
            "ceasefire", "nato", "russia", "ukraine", "china", "taiwan",
            "iran", "israel", "korea", "cuba", "venezuela", "greenland",
            "border", "invasion", "occupation", "troops",
        ],
    },
    "economic-policy": {
        "slug": "economic-policy",
        "name_ja": "経済政策",
        "name_en": "Economic Policy",
        "keywords": [
            "fed", "federal reserve", "interest rate", "inflation",
            "tariff", "fiscal", "monetary", "gdp", "recession",
            "unemployment", "stimulus", "debt ceiling", "treasury",
            "fomc", "rate cut", "rate hike", "powell",
        ],
    },
    "financial-markets": {
        "slug": "financial-markets",
        "name_ja": "金融市場",
        "name_en": "Financial Markets",
        "keywords": [
            "stock", "s&p", "dow", "nasdaq", "bond", "yield",
            "market crash", "ipo", "wall street", "berkshire",
            "gold", "silver", "commodity",
        ],
    },
    "technology": {
        "slug": "technology",
        "name_ja": "テクノロジー",
        "name_en": "Technology",
        "keywords": [
            "ai ", "artificial intelligence", "model", "chip",
            "semiconductor", "quantum", "computing", "openai",
            "anthropic", "claude", "gpt", "gemini", "deepseek",
            "apple", "google", "microsoft", "nvidia", "meta",
            "robot", "agi", "llm",
        ],
    },
    "crypto": {
        "slug": "crypto",
        "name_ja": "暗号資産",
        "name_en": "Crypto",
        "keywords": [
            "bitcoin", "btc", "ethereum", "eth", "crypto",
            "blockchain", "defi", "stablecoin", "solana",
            "token", "nft", "binance", "coinbase", "microstrategy",
        ],
    },
    "corporate-strategy": {
        "slug": "corporate-strategy",
        "name_ja": "企業戦略",
        "name_en": "Corporate Strategy",
        "keywords": [
            "acquisition", "merger", "acqui", "buyout",
            "ceo", "company", "corporation", "tiktok",
            "layoff", "restructur", "spinoff",
        ],
    },
    "regulation": {
        "slug": "regulation",
        "name_ja": "規制・法律",
        "name_en": "Regulation & Law",
        "keywords": [
            "regulation", "law", "court", "ruling", "antitrust",
            "ban", "compliance", "supreme court", "doj", "sec",
            "indictment", "trial", "conviction", "impeach",
        ],
    },
    "energy": {
        "slug": "energy",
        "name_ja": "エネルギー",
        "name_en": "Energy",
        "keywords": [
            "oil", "gas", "energy", "renewable", "nuclear",
            "opec", "solar", "wind", "battery", "ev ",
        ],
    },
    "climate": {
        "slug": "climate",
        "name_ja": "気候変動",
        "name_en": "Climate",
        "keywords": [
            "climate", "weather", "temperature", "emissions",
            "carbon", "hurricane", "wildfire", "drought", "flood",
        ],
    },
    "society": {
        "slug": "society",
        "name_ja": "社会・文化",
        "name_en": "Society & Culture",
        "keywords": [
            "election", "vote", "referendum", "president",
            "governor", "senate", "congress", "democrat",
            "republican", "trump", "biden", "populat",
        ],
    },
    "security": {
        "slug": "security",
        "name_ja": "安全保障",
        "name_en": "Security",
        "keywords": [
            "military", "defense", "nuclear weapon", "missile",
            "cyber", "attack", "strike", "bomb", "drone",
        ],
    },
    "science-health": {
        "slug": "science-health",
        "name_ja": "科学・医療",
        "name_en": "Science & Health",
        "keywords": [
            "vaccine", "health", "pandemic", "fda", "drug",
            "medical", "disease", "virus", "cancer", "trial",
            "who ", "bird flu", "h5n1",
        ],
    },
    "space": {
        "slug": "space",
        "name_ja": "宇宙",
        "name_en": "Space",
        "keywords": [
            "space", "nasa", "spacex", "satellite", "mars",
            "moon", "orbit", "rocket", "launch", "starship",
        ],
    },
}


# =============================================================================
# API Functions
# =============================================================================

def api_get(endpoint, params=None):
    """GET request to Polymarket Gamma API."""
    url = f"{BASE_URL}{endpoint}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"

    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "NowpatternMonitor/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"  API error ({endpoint}): {e}")
        return None
    except Exception as e:
        print(f"  Unexpected error ({endpoint}): {e}")
        return None


def fetch_active_events(limit=MAX_EVENTS):
    """Fetch top active events by volume."""
    data = api_get("/events", {
        "limit": str(limit),
        "active": "true",
        "closed": "false",
        "order": "volume",
        "ascending": "false",
    })
    if not data:
        return []
    return data if isinstance(data, list) else []


def parse_market_prices(market):
    """Parse outcome prices from a market object.

    Polymarket returns outcomePrices as either a JSON array or a JSON-encoded
    string (e.g., '["0.5","0.5"]'). This handles both.
    """
    prices = market.get("outcomePrices", [])
    outcomes = market.get("outcomes", [])

    # Handle JSON-encoded strings
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except (json.JSONDecodeError, ValueError):
            prices = []
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except (json.JSONDecodeError, ValueError):
            outcomes = []

    # Convert to float
    parsed = {}
    for outcome, price in zip(outcomes, prices):
        try:
            parsed[outcome] = float(price)
        except (ValueError, TypeError):
            continue
    return parsed


# =============================================================================
# Classification
# =============================================================================

def classify_event(event):
    """Classify a Polymarket event into Nowpattern genres.

    Returns list of matched genre slugs (can be multi-genre).
    """
    # Build searchable text from event
    title = (event.get("title") or "").lower()
    desc = (event.get("description") or "").lower()

    # Include sub-market questions
    market_texts = []
    for m in event.get("markets", []):
        q = (m.get("question") or "").lower()
        market_texts.append(q)

    # Include Polymarket's own tags
    poly_tags = []
    for t in event.get("tags", []):
        label = (t.get("label") or t.get("name") or "").lower()
        poly_tags.append(label)

    search_text = f"{title} {desc} {' '.join(market_texts)} {' '.join(poly_tags)}"

    matched = []
    for genre_key, genre_info in GENRE_KEYWORDS.items():
        score = 0
        for kw in genre_info["keywords"]:
            if kw in search_text:
                score += 1
        if score >= 2:  # Need at least 2 keyword matches
            matched.append({
                "slug": genre_info["slug"],
                "name_ja": genre_info["name_ja"],
                "name_en": genre_info["name_en"],
                "score": score,
            })

    # Sort by match score
    matched.sort(key=lambda x: x["score"], reverse=True)
    return matched[:3]  # Max 3 genres


# =============================================================================
# Snapshot Management
# =============================================================================

def load_snapshot():
    """Load previous snapshot for comparison."""
    if not os.path.exists(SNAPSHOT_FILE):
        return {}
    try:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_snapshot(snapshot):
    """Save current snapshot."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)


def save_history(snapshot, date_str):
    """Save daily history for Brier score tracking."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    path = os.path.join(HISTORY_DIR, f"{date_str}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)


# =============================================================================
# Movement Detection (Idea 2: Article Triggers)
# =============================================================================

def detect_movements(prev_snapshot, current_snapshot):
    """Detect significant odds movements (±10%+ in 24h).

    Returns list of alerts with market details and genre classification.
    """
    alerts = []

    for event_id, current in current_snapshot.items():
        if event_id not in prev_snapshot:
            # New event — check if it's high volume (debut alert)
            vol = current.get("volume", 0)
            if vol >= 5_000_000:  # New event with $5M+ volume
                alerts.append({
                    "type": "new_event",
                    "event_id": event_id,
                    "title": current.get("title", "?"),
                    "volume": vol,
                    "genres": current.get("genres", []),
                    "top_market": _get_top_market(current),
                    "severity": "medium",
                })
            continue

        prev = prev_snapshot[event_id]

        # Compare each sub-market's prices
        for market_id, curr_prices in current.get("markets", {}).items():
            prev_prices = prev.get("markets", {}).get(market_id, {})
            if not prev_prices:
                continue

            for outcome, curr_prob in curr_prices.get("prices", {}).items():
                prev_prob = prev_prices.get("prices", {}).get(outcome, curr_prob)
                delta = curr_prob - prev_prob

                if abs(delta) >= MOVEMENT_THRESHOLD:
                    direction = "UP" if delta > 0 else "DOWN"
                    alerts.append({
                        "type": "movement",
                        "event_id": event_id,
                        "market_id": market_id,
                        "title": current.get("title", "?"),
                        "question": curr_prices.get("question", "?"),
                        "outcome": outcome,
                        "prev_prob": prev_prob,
                        "curr_prob": curr_prob,
                        "delta": delta,
                        "direction": direction,
                        "volume": current.get("volume", 0),
                        "genres": current.get("genres", []),
                        "severity": "high" if abs(delta) >= 0.20 else "medium",
                    })

    # Sort by severity then delta
    alerts.sort(key=lambda a: (
        0 if a["severity"] == "high" else 1,
        -abs(a.get("delta", 0)),
    ))
    return alerts


def _get_top_market(event_data):
    """Get the most interesting sub-market from an event."""
    markets = event_data.get("markets", {})
    if not markets:
        return None
    # Return first market (already ordered by volume from API)
    market_id = next(iter(markets))
    m = markets[market_id]
    return {
        "question": m.get("question", "?"),
        "prices": m.get("prices", {}),
    }


# =============================================================================
# Embed Data (Idea 1: Article Integration)
# =============================================================================

def generate_embed_data(snapshot, max_per_event=3, max_total=50):
    """Generate JSON for article template integration.

    Output format matches what nowpattern_article_builder.py expects
    for the What's Next / Prediction Tracker sections.

    Filters:
    - Only Nowpattern-relevant events (with genre classification)
    - Top 3 sub-markets per event (by highest Yes probability or most interesting)
    - Max 50 total items (sorted by volume)
    """
    embeds = []

    for event_id, event_data in snapshot.items():
        genres = event_data.get("genres", [])
        if not genres:
            continue  # Skip events that don't match any Nowpattern genre

        # Collect all sub-markets with parsed prices
        event_markets = []
        for market_id, market_data in event_data.get("markets", {}).items():
            prices = market_data.get("prices", {})
            if not prices:
                continue

            # Get the "Yes" probability (most common binary market)
            yes_prob = prices.get("Yes", prices.get("yes", None))
            if yes_prob is None:
                # For non-binary, take the highest probability outcome
                if prices:
                    top_outcome = max(prices, key=prices.get)
                    yes_prob = prices[top_outcome]
                else:
                    continue

            event_markets.append({
                "market_id": market_id,
                "question": market_data.get("question", "?"),
                "probability": round(yes_prob * 100, 1),
                "outcomes": {k: round(v * 100, 1) for k, v in prices.items()},
                "yes_prob": yes_prob,
            })

        # Sort by probability descending (most likely outcomes first)
        # then take top N per event
        event_markets.sort(key=lambda m: m["yes_prob"], reverse=True)
        for m in event_markets[:max_per_event]:
            embeds.append({
                "source": "polymarket",
                "event_id": event_id,
                "market_id": m["market_id"],
                "title": event_data.get("title", "?"),
                "question": m["question"],
                "probability": m["probability"],
                "volume_usd": event_data.get("volume", 0),
                "genres": [g["slug"] for g in genres],
                "genres_ja": [g["name_ja"] for g in genres],
                "outcomes": m["outcomes"],
                "updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
            })

    # Sort by volume (most liquid first) and cap at max_total
    embeds.sort(key=lambda e: e["volume_usd"], reverse=True)
    return embeds[:max_total]


# =============================================================================
# Brier Score Comparison (Idea 3)
# =============================================================================

def compute_brier_scores(history_dir=HISTORY_DIR):
    """Compare Nowpattern predictions vs Polymarket consensus.

    Brier Score = mean of (forecast - actual)^2
    Lower = better. 0 = perfect. 0.25 = coin flip.

    Requires:
    - Resolved markets in history (actual outcomes)
    - Nowpattern predictions (from /predictions/ page data)
    """
    # TODO: Implement when we have enough resolved markets + predictions
    # For now, return placeholder explaining the concept
    return {
        "status": "accumulating_data",
        "message": (
            "Brier Score comparison requires resolved markets. "
            "Polymarket data is being collected daily. "
            "First comparison available after ~30 days of data."
        ),
        "polymarket_markets_tracked": _count_history_files(history_dir),
    }


def _count_history_files(history_dir):
    """Count days of historical data."""
    if not os.path.exists(history_dir):
        return 0
    return len([f for f in os.listdir(history_dir) if f.endswith(".json")])


# =============================================================================
# Alert Formatting
# =============================================================================

def format_alerts_telegram(alerts):
    """Format alerts for Telegram message."""
    if not alerts:
        return None

    lines = ["[Polymarket] Odds Movement Alerts\n"]

    for a in alerts[:10]:  # Max 10 alerts
        if a["type"] == "movement":
            emoji = "🔺" if a["direction"] == "UP" else "🔻"
            genre_str = ", ".join(g["name_ja"] for g in a.get("genres", []))
            lines.append(
                f"{emoji} {a['title'][:50]}\n"
                f"  {a['question'][:60]}\n"
                f"  {a['outcome']}: {a['prev_prob']*100:.1f}% -> "
                f"{a['curr_prob']*100:.1f}% ({a['delta']*100:+.1f}%)\n"
                f"  Vol: ${a['volume']:,.0f} | {genre_str}\n"
            )
        elif a["type"] == "new_event":
            genre_str = ", ".join(g["name_ja"] for g in a.get("genres", []))
            top = a.get("top_market")
            lines.append(
                f"🆕 {a['title'][:50]}\n"
                f"  Vol: ${a['volume']:,.0f} | {genre_str}\n"
            )
            if top:
                lines.append(
                    f"  {top['question'][:60]}\n"
                    f"  {', '.join(f'{k}={v*100:.0f}%' for k,v in top['prices'].items())}\n"
                )

    return "\n".join(lines)


def format_alerts_for_daily_learning(alerts, snapshot):
    """Format for daily-learning.py integration.

    Returns a string that can be appended to the raw_data section.
    """
    lines = [
        "### Polymarket Prediction Markets",
        f"Active markets tracked: {len(snapshot)}",
        "",
    ]

    if alerts:
        lines.append(f"Significant movements (±{MOVEMENT_THRESHOLD*100:.0f}%+): {len(alerts)}")
        for a in alerts[:5]:
            if a["type"] == "movement":
                lines.append(
                    f"  - {a['question'][:60]}: "
                    f"{a['outcome']} {a['prev_prob']*100:.0f}%→{a['curr_prob']*100:.0f}% "
                    f"({a['delta']*100:+.1f}%) [Vol: ${a['volume']:,.0f}]"
                )
        lines.append("")

    # Top 10 highest-volume markets with current odds
    lines.append("Top markets by volume:")
    items = sorted(snapshot.values(), key=lambda x: x.get("volume", 0), reverse=True)
    for item in items[:10]:
        title = item.get("title", "?")[:55]
        vol = item.get("volume", 0)
        genres = ", ".join(g["name_en"] for g in item.get("genres", []))

        # Show top sub-market odds
        markets = item.get("markets", {})
        if markets:
            first_m = next(iter(markets.values()))
            prices = first_m.get("prices", {})
            odds_str = " | ".join(
                f"{k}={v*100:.0f}%" for k, v in list(prices.items())[:3]
            )
        else:
            odds_str = ""

        lines.append(f"  ${vol/1e6:.1f}M | {title}")
        if odds_str:
            lines.append(f"         {odds_str}")
        if genres:
            lines.append(f"         [{genres}]")

    return "\n".join(lines)


# =============================================================================
# Main Scan Logic
# =============================================================================

def scan_and_snapshot():
    """Main scan: fetch events, classify, snapshot, detect movements."""
    now = datetime.now(JST)
    date_str = now.strftime("%Y-%m-%d")

    print(f"[Polymarket Monitor] {now.strftime('%Y-%m-%d %H:%M JST')}")

    # 1. Fetch active events
    print(f"  Fetching top {MAX_EVENTS} active events by volume...")
    events = fetch_active_events(MAX_EVENTS)
    if not events:
        print("  ERROR: No events fetched")
        return {}, []
    print(f"  Got {len(events)} events")

    # 2. Build current snapshot
    current_snapshot = {}
    relevant_count = 0

    for event in events:
        event_id = str(event.get("id", ""))
        title = event.get("title", "?")
        volume = float(event.get("volume", 0) or 0)

        # Skip low-volume markets
        if volume < MIN_VOLUME:
            continue

        # Classify into Nowpattern genres
        genres = classify_event(event)

        # Parse sub-markets
        markets_data = {}
        for m in event.get("markets", []):
            mid = str(m.get("id", ""))
            prices = parse_market_prices(m)
            if prices:
                markets_data[mid] = {
                    "question": m.get("question", "?"),
                    "prices": prices,
                }

        entry = {
            "title": title,
            "volume": volume,
            "genres": genres,
            "markets": markets_data,
            "poly_tags": [
                t.get("label", "") for t in event.get("tags", [])
            ],
        }
        current_snapshot[event_id] = entry

        if genres:
            relevant_count += 1

    print(f"  Snapshot: {len(current_snapshot)} events (vol>=${MIN_VOLUME/1e6:.1f}M)")
    print(f"  Nowpattern-relevant: {relevant_count} events")

    # 3. Load previous snapshot for comparison
    prev_snapshot = load_snapshot()
    prev_count = len(prev_snapshot)

    # 4. Detect movements
    alerts = []
    if prev_snapshot:
        alerts = detect_movements(prev_snapshot, current_snapshot)
        print(f"  Movements detected: {len(alerts)} (threshold: ±{MOVEMENT_THRESHOLD*100:.0f}%)")
    else:
        print("  First scan — no previous data to compare")

    # 5. Save snapshots
    save_snapshot(current_snapshot)
    save_history(current_snapshot, date_str)
    print(f"  Snapshot saved: {SNAPSHOT_FILE}")
    print(f"  History saved: {HISTORY_DIR}/{date_str}.json")

    # 6. Save alerts
    if alerts:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=2, ensure_ascii=False)

    return current_snapshot, alerts


# =============================================================================
# CLI Entry Point
# =============================================================================

def parse_args():
    """Parse CLI arguments."""
    mode = "full"  # full, trigger, embed, brier
    telegram = False

    for arg in sys.argv[1:]:
        if arg == "--mode":
            pass  # next arg will be the mode
        elif arg in ("trigger", "embed", "brier", "full"):
            mode = arg
        elif arg == "--telegram":
            telegram = True

    # Check for --mode <value> pattern
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--mode" and i < len(sys.argv) - 1:
            mode = sys.argv[i + 1]

    return mode, telegram


def send_telegram(message):
    """Send alert to Telegram. Uses same env vars as daily-learning.py."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        # Try cron-env.sh
        env_file = "/opt/cron-env.sh"
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("export TELEGRAM_BOT_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip("'\"")
                    elif line.startswith("export TELEGRAM_CHAT_ID="):
                        chat_id = line.split("=", 1)[1].strip().strip("'\"")

    if not token or not chat_id:
        print("  WARNING: Telegram config not found")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Strip markdown formatting
    clean = message.replace("**", "").replace("*", "").replace("_", "")

    payload = json.dumps({
        "chat_id": chat_id,
        "text": clean[:4000],
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("ok"):
                print("  Telegram alert sent")
                return True
    except Exception as e:
        print(f"  Telegram error: {e}")
    return False


def main():
    mode, telegram = parse_args()

    print("=== Polymarket Monitor v1.0 ===")
    print(f"Mode: {mode} | Telegram: {telegram}")
    print()

    if mode == "brier":
        result = compute_brier_scores()
        print(json.dumps(result, indent=2))
        return

    # Run scan
    snapshot, alerts = scan_and_snapshot()

    if not snapshot:
        print("ERROR: No data collected")
        sys.exit(1)

    if mode in ("full", "trigger"):
        # Print alerts
        if alerts:
            print(f"\n=== Alerts ({len(alerts)}) ===")
            for a in alerts[:10]:
                if a["type"] == "movement":
                    emoji = "▲" if a["direction"] == "UP" else "▼"
                    print(
                        f"  {emoji} {a['question'][:60]}\n"
                        f"    {a['outcome']}: "
                        f"{a['prev_prob']*100:.1f}% -> {a['curr_prob']*100:.1f}% "
                        f"({a['delta']*100:+.1f}%)"
                    )
                elif a["type"] == "new_event":
                    print(f"  NEW: {a['title'][:60]} (${a['volume']:,.0f})")

            # Telegram
            if telegram:
                tg_msg = format_alerts_telegram(alerts)
                if tg_msg:
                    send_telegram(tg_msg)
        else:
            print("\n  No significant movements detected")

    if mode in ("full", "embed"):
        # Generate embed data
        embed_data = generate_embed_data(snapshot)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(EMBED_FILE, "w", encoding="utf-8") as f:
            json.dump(embed_data, f, indent=2, ensure_ascii=False)
        print(f"\n  Embed data: {EMBED_FILE} ({len(embed_data)} markets)")

    # Print daily-learning integration text
    if mode == "full":
        dl_text = format_alerts_for_daily_learning(alerts, snapshot)
        print(f"\n=== daily-learning.py integration ===\n{dl_text}")

    # Summary
    genre_counts = {}
    for ev in snapshot.values():
        for g in ev.get("genres", []):
            slug = g["slug"]
            genre_counts[slug] = genre_counts.get(slug, 0) + 1

    print(f"\n=== Summary ===")
    print(f"  Events tracked: {len(snapshot)}")
    print(f"  Genre distribution:")
    for slug, count in sorted(genre_counts.items(), key=lambda x: -x[1]):
        name = GENRE_KEYWORDS.get(slug, {}).get("name_ja", slug)
        print(f"    {name}: {count}")
    if alerts:
        print(f"  Alerts generated: {len(alerts)}")
    print(f"  Data dir: {DATA_DIR}")


if __name__ == "__main__":
    main()
