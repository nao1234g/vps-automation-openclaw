#!/usr/bin/env python3
"""
market_history_crawler.py — Nowpattern 予測市場データ収集クローラー

毎日 09:00 JST に実行:
  cron: 0 0 * * * python3 /opt/shared/scripts/market_history_crawler.py

機能:
  - Polymarket Gamma API からトップ市場の確率スナップショットを取得
  - Manifold Markets API からスナップショットを取得
  - SQLite market_history.db に保存（4テーブル構成）

DB: /opt/shared/market_history/market_history.db

使用方法:
  python3 market_history_crawler.py           # 通常実行
  python3 market_history_crawler.py --init     # DBスキーマ初期化のみ
  python3 market_history_crawler.py --import-json  # 既存JSON履歴をDBに取り込む
  python3 market_history_crawler.py --status   # DB統計を表示
"""

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime, date, timezone

import requests

# ── 設定 ────────────────────────────────────────────────────────────
DB_DIR = "/opt/shared/market_history"
DB_PATH = os.path.join(DB_DIR, "market_history.db")
POLY_HISTORY_DIR = "/opt/shared/polymarket/history"

POLYMARKET_GAMMA = "https://gamma-api.polymarket.com"
MANIFOLD_API = "https://api.manifold.markets/v0"

# Polymarket: 1回あたり最大取得件数
POLY_MAX_EVENTS = 100
# Manifold: 1回あたり最大取得件数
MANIFOLD_MAX = 100

# ── DB 初期化 ─────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS markets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,   -- 'polymarket', 'manifold', 'metaculus'
    external_id     TEXT NOT NULL,   -- source の市場ID
    event_id        TEXT,            -- polymarket: event_id
    question        TEXT NOT NULL,
    event_title     TEXT,
    market_slug     TEXT,
    event_slug      TEXT,
    genres          TEXT,            -- JSON array of genre slugs
    close_date      TEXT,            -- ISO 8601 date
    resolved        INTEGER DEFAULT 0,  -- 0=open, 1=resolved
    resolution      TEXT,            -- 'YES', 'NO', null
    first_seen      TEXT NOT NULL,
    last_updated    TEXT NOT NULL,
    UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS probability_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id       INTEGER NOT NULL REFERENCES markets(id),
    snapshot_date   TEXT NOT NULL,   -- YYYY-MM-DD
    yes_prob        REAL,            -- 0.0〜1.0
    no_prob         REAL,
    volume          REAL,
    recorded_at     TEXT NOT NULL,
    UNIQUE(market_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS nowpattern_links (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id        TEXT NOT NULL,  -- prediction_db.json の prediction_id
    market_id            INTEGER REFERENCES markets(id),
    source               TEXT,           -- 'polymarket', 'manifold'
    external_market_id   TEXT,           -- markets.external_id のコピー（利便性）
    resolution_direction TEXT NOT NULL,  -- 'pessimistic' or 'optimistic'
    notes                TEXT,
    created_at           TEXT NOT NULL,
    UNIQUE(prediction_id, external_market_id)
);

CREATE TABLE IF NOT EXISTS news_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id       INTEGER NOT NULL REFERENCES markets(id),
    event_date      TEXT NOT NULL,   -- YYYY-MM-DD
    prev_prob       REAL,
    curr_prob       REAL,
    change_pct      REAL,            -- (curr - prev) * 100
    headline        TEXT,
    recorded_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_market   ON probability_snapshots(market_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_date     ON probability_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_links_prediction   ON nowpattern_links(prediction_id);
CREATE INDEX IF NOT EXISTS idx_news_market        ON news_events(market_id);
"""


def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(DDL)
    conn.commit()
    conn.close()
    print(f"DB initialized: {DB_PATH}")


# ── Polymarket 取得 ───────────────────────────────────────────────

def fetch_polymarket_events(limit: int = POLY_MAX_EVENTS) -> list[dict]:
    """Gamma API からアクティブなイベントを取得する。"""
    try:
        r = requests.get(
            f"{POLYMARKET_GAMMA}/events",
            params={"limit": limit, "active": "true", "closed": "false"},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[WARN] Polymarket events fetch failed: {e}")
        return []


def fetch_polymarket_markets(limit: int = POLY_MAX_EVENTS) -> list[dict]:
    """Gamma API からアクティブな市場を取得する（events APIが使えない場合のフォールバック）。"""
    try:
        r = requests.get(
            f"{POLYMARKET_GAMMA}/markets",
            params={"limit": limit, "active": "true", "closed": "false"},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[WARN] Polymarket markets fetch failed: {e}")
        return []


def upsert_polymarket(conn: sqlite3.Connection, event: dict, today_str: str):
    """1イベントをDBに挿入/更新し、スナップショットを記録する。"""
    event_id = str(event.get("id", ""))
    event_title = event.get("title", "")
    event_slug = event.get("slug", "")
    end_date = event.get("endDate", "")[:10] if event.get("endDate") else None

    genres_raw = event.get("tags", [])
    genres = json.dumps([g.get("slug", g) if isinstance(g, dict) else g for g in genres_raw])

    markets = event.get("markets", [])
    if not markets:
        return 0

    now_str = datetime.now(timezone.utc).isoformat()
    saved = 0

    for m in markets:
        market_id_ext = str(m.get("id", ""))
        question = m.get("question", "")
        market_slug = m.get("slug", "")

        # outcomePrices は "[\"0.72\", \"0.28\"]" のような文字列
        outcome_prices_raw = m.get("outcomePrices", "")
        outcomes_raw = m.get("outcomes", "")
        yes_prob = no_prob = None

        try:
            prices = json.loads(outcome_prices_raw) if isinstance(outcome_prices_raw, str) else outcome_prices_raw
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
            if prices and outcomes:
                for i, outcome in enumerate(outcomes):
                    if outcome.lower() in ("yes", "はい"):
                        yes_prob = float(prices[i])
                    elif outcome.lower() in ("no", "いいえ"):
                        no_prob = float(prices[i])
        except (json.JSONDecodeError, IndexError, ValueError):
            pass

        if yes_prob is None and no_prob is None:
            continue

        volume = float(m.get("volumeNum", 0) or 0)

        # markets テーブル upsert
        conn.execute("""
            INSERT INTO markets
                (source, external_id, event_id, question, event_title,
                 market_slug, event_slug, genres, close_date, first_seen, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, external_id) DO UPDATE SET
                last_updated = excluded.last_updated,
                event_title  = excluded.event_title,
                genres       = excluded.genres
        """, ("polymarket", market_id_ext, event_id, question, event_title,
              market_slug, event_slug, genres, end_date, now_str, now_str))

        row = conn.execute(
            "SELECT id FROM markets WHERE source=? AND external_id=?",
            ("polymarket", market_id_ext)
        ).fetchone()
        if not row:
            continue
        db_id = row["id"]

        # probability_snapshots upsert
        conn.execute("""
            INSERT INTO probability_snapshots
                (market_id, snapshot_date, yes_prob, no_prob, volume, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(market_id, snapshot_date) DO UPDATE SET
                yes_prob    = excluded.yes_prob,
                no_prob     = excluded.no_prob,
                volume      = excluded.volume,
                recorded_at = excluded.recorded_at
        """, (db_id, today_str, yes_prob, no_prob, volume, now_str))

        # 前日比 ≥15% でnews_eventsフラグ
        prev = conn.execute("""
            SELECT yes_prob FROM probability_snapshots
            WHERE market_id=? AND snapshot_date < ?
            ORDER BY snapshot_date DESC LIMIT 1
        """, (db_id, today_str)).fetchone()
        if prev and prev["yes_prob"] is not None and yes_prob is not None:
            change = (yes_prob - prev["yes_prob"]) * 100
            if abs(change) >= 15:
                conn.execute("""
                    INSERT OR IGNORE INTO news_events
                        (market_id, event_date, prev_prob, curr_prob, change_pct, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (db_id, today_str, prev["yes_prob"], yes_prob, round(change, 1), now_str))

        saved += 1

    return saved


# ── Manifold 取得 ─────────────────────────────────────────────────

def fetch_manifold_markets(limit: int = MANIFOLD_MAX) -> list[dict]:
    """Manifold Markets から注目市場を取得する（BINARY型のみ）。"""
    try:
        r = requests.get(
            f"{MANIFOLD_API}/markets",
            params={"limit": limit, "sort": "last-bet-time"},
            timeout=30,
        )
        r.raise_for_status()
        markets = r.json()
        # BINARY型のみ（probability フィールドあり）
        return [m for m in markets if m.get("outcomeType") == "BINARY" and m.get("probability") is not None]
    except Exception as e:
        print(f"[WARN] Manifold fetch failed: {e}")
        return []


def upsert_manifold(conn: sqlite3.Connection, m: dict, today_str: str):
    """1 Manifold 市場をDBに挿入/更新する。"""
    market_id_ext = str(m.get("id", ""))
    question = m.get("question", "")
    market_slug = m.get("slug", "")
    close_ts = m.get("closeTime", 0)
    close_date = datetime.fromtimestamp(close_ts / 1000).strftime("%Y-%m-%d") if close_ts else None

    # probability: BINARY markets have probability field directly
    prob = m.get("probability")
    if prob is None:
        return 0
    yes_prob = float(prob)
    no_prob = 1.0 - yes_prob
    volume = float(m.get("volume", 0) or 0)

    # Manifold にはタグがある
    tags = m.get("tags", [])
    genres = json.dumps(tags)

    now_str = datetime.now(timezone.utc).isoformat()

    conn.execute("""
        INSERT INTO markets
            (source, external_id, event_id, question, event_title,
             market_slug, event_slug, genres, close_date, first_seen, last_updated)
        VALUES (?, ?, NULL, ?, ?, ?, NULL, ?, ?, ?, ?)
        ON CONFLICT(source, external_id) DO UPDATE SET
            last_updated = excluded.last_updated
    """, ("manifold", market_id_ext, question, question,
          market_slug, genres, close_date, now_str, now_str))

    row = conn.execute(
        "SELECT id FROM markets WHERE source=? AND external_id=?",
        ("manifold", market_id_ext)
    ).fetchone()
    if not row:
        return 0
    db_id = row["id"]

    conn.execute("""
        INSERT INTO probability_snapshots
            (market_id, snapshot_date, yes_prob, no_prob, volume, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(market_id, snapshot_date) DO UPDATE SET
            yes_prob    = excluded.yes_prob,
            no_prob     = excluded.no_prob,
            volume      = excluded.volume,
            recorded_at = excluded.recorded_at
    """, (db_id, today_str, yes_prob, no_prob, volume, now_str))

    return 1


# ── 既存JSON履歴の取り込み ─────────────────────────────────────────

def import_json_history(conn: sqlite3.Connection):
    """
    /opt/shared/polymarket/history/YYYY-MM-DD.json を
    SQLiteに一括取り込みする。
    形式: {event_id: {title, markets: {market_id: {question, prices: {Yes, No}, slug}}}}
    """
    if not os.path.isdir(POLY_HISTORY_DIR):
        print(f"[WARN] History dir not found: {POLY_HISTORY_DIR}")
        return

    files = sorted(f for f in os.listdir(POLY_HISTORY_DIR) if re.match(r"\d{4}-\d{2}-\d{2}\.json", f))
    print(f"Importing {len(files)} JSON history files...")

    now_str = datetime.now(timezone.utc).isoformat()
    total_snapshots = 0

    for fname in files:
        date_str = fname[:10]
        fpath = os.path.join(POLY_HISTORY_DIR, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [SKIP] {fname}: {e}")
            continue

        for event_id, event_data in data.items():
            event_title = event_data.get("title", "")
            event_slug = event_data.get("slug", "")
            genres_raw = event_data.get("genres", [])
            genres = json.dumps([g.get("slug", g) if isinstance(g, dict) else g for g in genres_raw])

            for market_id_ext, mkt in event_data.get("markets", {}).items():
                question = mkt.get("question", "")
                market_slug = mkt.get("slug", "")
                prices = mkt.get("prices", {})
                yes_prob = prices.get("Yes") or prices.get("yes")
                no_prob = prices.get("No") or prices.get("no")

                if yes_prob is None:
                    continue

                conn.execute("""
                    INSERT INTO markets
                        (source, external_id, event_id, question, event_title,
                         market_slug, event_slug, genres, first_seen, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source, external_id) DO UPDATE SET
                        last_updated = excluded.last_updated
                """, ("polymarket", market_id_ext, event_id, question, event_title,
                      market_slug, event_slug, genres, now_str, now_str))

                row = conn.execute(
                    "SELECT id FROM markets WHERE source=? AND external_id=?",
                    ("polymarket", market_id_ext)
                ).fetchone()
                if not row:
                    continue
                db_id = row["id"]

                conn.execute("""
                    INSERT INTO probability_snapshots
                        (market_id, snapshot_date, yes_prob, no_prob, volume, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(market_id, snapshot_date) DO NOTHING
                """, (db_id, date_str, float(yes_prob), float(no_prob) if no_prob else None,
                      0, now_str))
                total_snapshots += 1

        conn.commit()

    print(f"Imported: {total_snapshots} snapshots from JSON history")


# ── メイン実行 ────────────────────────────────────────────────────

def print_status(conn: sqlite3.Connection):
    """DB統計を表示する。"""
    n_markets = conn.execute("SELECT COUNT(*) FROM markets").fetchone()[0]
    n_poly = conn.execute("SELECT COUNT(*) FROM markets WHERE source='polymarket'").fetchone()[0]
    n_manifold = conn.execute("SELECT COUNT(*) FROM markets WHERE source='manifold'").fetchone()[0]
    n_snaps = conn.execute("SELECT COUNT(*) FROM probability_snapshots").fetchone()[0]
    n_links = conn.execute("SELECT COUNT(*) FROM nowpattern_links").fetchone()[0]
    n_news = conn.execute("SELECT COUNT(*) FROM news_events").fetchone()[0]
    min_date = conn.execute("SELECT MIN(snapshot_date) FROM probability_snapshots").fetchone()[0]
    max_date = conn.execute("SELECT MAX(snapshot_date) FROM probability_snapshots").fetchone()[0]

    print(f"""
=== market_history.db ===
Markets:      {n_markets} (Polymarket: {n_poly}, Manifold: {n_manifold})
Snapshots:    {n_snaps} ({min_date} → {max_date})
Links:        {n_links} (nowpattern articles ↔ markets)
News events:  {n_news} (≥15% probability changes)
""")


def run_crawler():
    """通常実行: Polymarket + Manifold から今日のスナップショットを取得。"""
    today_str = date.today().isoformat()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting crawl for {today_str}")

    conn = get_db()

    # --- Polymarket ---
    print("Fetching Polymarket events...")
    events = fetch_polymarket_events()
    print(f"  Got {len(events)} events")

    poly_saved = 0
    for event in events:
        poly_saved += upsert_polymarket(conn, event, today_str)
    conn.commit()
    print(f"  Saved {poly_saved} Polymarket market snapshots")

    # --- Manifold ---
    print("Fetching Manifold markets...")
    manifold_markets = fetch_manifold_markets()
    print(f"  Got {len(manifold_markets)} markets")

    mf_saved = 0
    for m in manifold_markets:
        mf_saved += upsert_manifold(conn, m, today_str)
    conn.commit()
    print(f"  Saved {mf_saved} Manifold market snapshots")

    print_status(conn)
    conn.close()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Crawl complete")


def main():
    parser = argparse.ArgumentParser(description="Nowpattern 予測市場クローラー")
    parser.add_argument("--init", action="store_true", help="DBスキーマ初期化のみ")
    parser.add_argument("--import-json", action="store_true", help="既存JSON履歴をDBに取り込む")
    parser.add_argument("--status", action="store_true", help="DB統計を表示")
    args = parser.parse_args()

    init_db()

    if args.init:
        print("DB initialized. Done.")
        return

    if args.import_json:
        conn = get_db()
        import_json_history(conn)
        conn.close()
        return

    if args.status:
        conn = get_db()
        print_status(conn)
        conn.close()
        return

    run_crawler()


if __name__ == "__main__":
    main()
