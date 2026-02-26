#!/usr/bin/env python3
"""
prediction_resolver.py — Nowpattern 予測解決エンジン

market_history.db の確率データを使って:
1. 各予測記事の market を確認 (nowpattern_links テーブル)
2. 最新確率に基づいて自動/半自動で判定
3. prediction_db.json を更新 (Brier Score 計算)
4. 必要な場合は Telegram 通知

解決ロジック:
  確率 ≥95% or ≤5%      → 自動判定
  確率 70〜94% or 6〜29% → Gemini 確認後に自動
  確率 30〜70% (期日到来) → Telegram 手動ボタン通知
  確率 35〜65% (期日到来) → 基本シナリオ（不確定）
  リンクなし            → スキップ（A3 後に新記事から適用）

使用方法:
  python3 prediction_resolver.py           # 通常実行
  python3 prediction_resolver.py --dry-run # 変更なしで確認のみ
  python3 prediction_resolver.py --status  # DB・JSON 統計表示
  python3 prediction_resolver.py --link    # nowpattern_links の一覧表示

cron: 0 1 * * * source /opt/cron-env.sh && python3 /opt/shared/scripts/prediction_resolver.py
  (market_history_crawler.py が 00:00 に実行した後の 01:00 UTC = 10:00 JST)
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime, date, timezone

import requests

# ── 設定 ────────────────────────────────────────────────────────────
DB_PATH = "/opt/shared/market_history/market_history.db"
PREDICTION_DB = "/opt/shared/scripts/prediction_db.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# 判定閾値
THRESHOLD_AUTO_HIGH = 0.95   # ≥ この確率 → YES 自動判定
THRESHOLD_AUTO_LOW = 0.05    # ≤ この確率 → NO 自動判定
THRESHOLD_GEMINI_HIGH = 0.70  # 70〜94% → Gemini 確認
THRESHOLD_GEMINI_LOW = 0.30   # 6〜29% → Gemini 確認
THRESHOLD_AMBIGUOUS_HIGH = 0.65  # 35〜65% 期日到来 → 基本シナリオ
THRESHOLD_AMBIGUOUS_LOW = 0.35

# ── DB ヘルパー ──────────────────────────────────────────────────────

def get_db():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"market_history.db が見つかりません: {DB_PATH}")
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def get_latest_probability(db, market_id: int):
    """最新の確率スナップショットを取得"""
    cur = db.cursor()
    cur.execute("""
        SELECT yes_prob, no_prob, snapshot_date
        FROM probability_snapshots
        WHERE market_id = ?
        ORDER BY snapshot_date DESC
        LIMIT 1
    """, (market_id,))
    return cur.fetchone()


def get_market(db, market_id: int):
    """market 情報を取得"""
    cur = db.cursor()
    cur.execute("SELECT * FROM markets WHERE id = ?", (market_id,))
    return cur.fetchone()


def get_links_for_prediction(db, prediction_id: str):
    """prediction_id に対応する nowpattern_links を取得"""
    cur = db.cursor()
    cur.execute("""
        SELECT nl.*, m.question, m.close_date, m.resolved, m.resolution,
               m.source, m.external_id, m.event_title
        FROM nowpattern_links nl
        JOIN markets m ON nl.market_id = m.id
        WHERE nl.prediction_id = ?
    """, (prediction_id,))
    return cur.fetchall()


def get_all_links(db):
    """全ての nowpattern_links を取得"""
    cur = db.cursor()
    cur.execute("""
        SELECT nl.*, m.question, m.close_date, m.resolved, m.resolution,
               m.source, m.external_id, m.event_title
        FROM nowpattern_links nl
        JOIN markets m ON nl.market_id = m.id
        ORDER BY nl.prediction_id
    """)
    return cur.fetchall()


# ── Brier Score 計算 ─────────────────────────────────────────────────

def calc_brier_score(scenarios: list, outcome_label: str) -> float:
    """
    Brier Score を計算する。
    - scenarios: [{"label": "楽観シナリオ", "probability": 0.3, ...}, ...]
    - outcome_label: 実際に起きたシナリオのラベル
    - returns: Brier Score (0が完璧、0.25=ランダム)
    """
    if not scenarios:
        return None
    total = 0.0
    for s in scenarios:
        predicted_prob = s.get("probability", 0)
        actual = 1.0 if s["label"] == outcome_label else 0.0
        total += (predicted_prob - actual) ** 2
    return round(total / len(scenarios), 4)


# ── 判定ロジック ─────────────────────────────────────────────────────

def determine_outcome(resolution_direction: str, market_resolution: str) -> str:
    """
    market の YES/NO 解決結果 → シナリオラベルを返す

    resolution_direction:
      "pessimistic": YES→悲観, NO→楽観
      "optimistic":  YES→楽観, NO→悲観

    returns: "楽観シナリオ" or "悲観シナリオ" or "基本シナリオ"
    """
    if market_resolution == "YES":
        if resolution_direction == "pessimistic":
            return "悲観シナリオ"
        elif resolution_direction == "optimistic":
            return "楽観シナリオ"
    elif market_resolution == "NO":
        if resolution_direction == "pessimistic":
            return "楽観シナリオ"
        elif resolution_direction == "optimistic":
            return "悲観シナリオ"
    return "基本シナリオ"


def deadline_passed(close_date_str: str) -> bool:
    """close_date が今日以前かどうか"""
    if not close_date_str:
        return False
    try:
        # ISO形式 or YYYY-MM-DD
        if "T" in close_date_str:
            dt = datetime.fromisoformat(close_date_str.replace("Z", "+00:00"))
            close_date = dt.date()
        else:
            close_date = date.fromisoformat(close_date_str[:10])
        return close_date <= date.today()
    except (ValueError, AttributeError):
        return False


# ── Gemini 確認 ──────────────────────────────────────────────────────

def gemini_confirm_resolution(question: str, yes_prob: float, resolution_direction: str) -> dict:
    """
    Gemini に確率と方向性を渡して、判定を確認してもらう。
    returns: {"resolved": bool, "outcome": "YES"/"NO"/None, "reason": str}
    """
    if not GOOGLE_API_KEY:
        return {"resolved": False, "outcome": None, "reason": "GOOGLE_API_KEY なし"}

    direction_desc = "YES=悲観シナリオ、NO=楽観シナリオ" if resolution_direction == "pessimistic" \
        else "YES=楽観シナリオ、NO=悲観シナリオ"

    prompt = f"""以下の予測市場の状況を評価し、判定してください。

質問: {question}
現在の YES 確率: {yes_prob*100:.1f}%
方向性マッピング: {direction_desc}

判定基準:
- YES確率 ≥ 70% → YES として判定
- YES確率 ≤ 30% → NO として判定

必ず以下のJSON形式で回答してください（それ以外の文字を含めないこと）:
{{"outcome": "YES" または "NO", "reason": "判定理由（1文）"}}"""

    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GOOGLE_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        # JSON抽出
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
        return {"resolved": True, "outcome": result.get("outcome"), "reason": result.get("reason", "")}
    except Exception as e:
        return {"resolved": False, "outcome": None, "reason": f"Gemini エラー: {e}"}


# ── Telegram 通知 ─────────────────────────────────────────────────────

def send_telegram(message: str):
    """Telegram にメッセージを送信"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [WARN] TELEGRAM_BOT_TOKEN/CHAT_ID が設定されていません")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=15
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"  [WARN] Telegram 送信失敗: {e}")
        return False


def notify_manual_review(prediction_id: str, article_title: str, question: str,
                          yes_prob: float, resolution_direction: str, close_date: str):
    """手動判定が必要な予測を Telegram で通知"""
    direction_desc = "YES=悲観/NO=楽観" if resolution_direction == "pessimistic" \
        else "YES=楽観/NO=悲観"
    msg = (
        f"🔔 <b>手動判定リクエスト</b>\n\n"
        f"記事: {article_title}\n"
        f"ID: {prediction_id}\n\n"
        f"📊 市場: {question}\n"
        f"現在確率: YES {yes_prob*100:.1f}%\n"
        f"方向性: {direction_desc}\n"
        f"期日: {close_date or '不明'}\n\n"
        f"👉 prediction_db.json の outcome と resolved_at を手動更新してください:\n"
        f"outcome: 楽観シナリオ / 基本シナリオ / 悲観シナリオ"
    )
    return send_telegram(msg)


def notify_auto_resolved(prediction_id: str, article_title: str, outcome: str,
                          brier_score: float, reason: str = ""):
    """自動判定完了を Telegram で通知"""
    msg = (
        f"✅ <b>予測自動判定完了</b>\n\n"
        f"記事: {article_title}\n"
        f"ID: {prediction_id}\n"
        f"結果: <b>{outcome}</b>\n"
        f"Brier Score: {brier_score}\n"
    )
    if reason:
        msg += f"根拠: {reason}"
    return send_telegram(msg)


# ── メイン処理 ────────────────────────────────────────────────────────

def load_prediction_db():
    with open(PREDICTION_DB, "r", encoding="utf-8") as f:
        return json.load(f)


def save_prediction_db(data: dict):
    with open(PREDICTION_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def process_prediction(pred: dict, links: list, db, dry_run: bool) -> dict:
    """
    1つの予測エントリを処理し、更新があれば dict を返す。
    変更なしの場合は None を返す。
    """
    prediction_id = pred["prediction_id"]
    article_title = pred.get("article_title", "")
    current_status = pred.get("status", "open")

    # 既に解決済みならスキップ
    if current_status == "resolved":
        return None

    if not links:
        # nowpattern_links が未設定 → スキップ
        return None

    # 最初のリンク（1記事:1市場を想定）
    link = links[0]
    market_id = link["market_id"]
    resolution_direction = link["resolution_direction"]
    question = link["question"]
    close_date = link["close_date"]
    market_resolved = link["resolved"]
    market_resolution = link["resolution"]  # 'YES', 'NO', or None

    # 最新確率を取得
    snap = get_latest_probability(db, market_id)
    if not snap:
        print(f"  [SKIP] {prediction_id}: スナップショットなし")
        return None

    yes_prob = snap["yes_prob"]
    snapshot_date = snap["snapshot_date"]
    print(f"  [{prediction_id}] {article_title[:40]}... YES={yes_prob*100:.1f}% ({snapshot_date})")

    now_str = datetime.now(timezone.utc).isoformat()
    updates = {}

    # ── ケース 1: market が既に解決済み ──────────────────────────────
    if market_resolved and market_resolution in ("YES", "NO"):
        outcome = determine_outcome(resolution_direction, market_resolution)
        scenarios = pred.get("scenarios", [])
        brier = calc_brier_score(scenarios, outcome)
        print(f"    → 市場解決済み: {market_resolution} → {outcome} (Brier: {brier})")
        updates = {
            "status": "resolved",
            "outcome": outcome,
            "resolved_at": now_str,
            "brier_score": brier,
            "resolution_note": f"市場解決: {market_resolution} (market_id={market_id})"
        }
        if not dry_run:
            notify_auto_resolved(prediction_id, article_title, outcome, brier)
        return updates

    # ── ケース 2: 確率 ≥ 95% → YES 自動判定 ──────────────────────────
    if yes_prob >= THRESHOLD_AUTO_HIGH:
        outcome = determine_outcome(resolution_direction, "YES")
        scenarios = pred.get("scenarios", [])
        brier = calc_brier_score(scenarios, outcome)
        print(f"    → 自動判定 YES ({yes_prob*100:.1f}%) → {outcome} (Brier: {brier})")
        updates = {
            "status": "resolved",
            "outcome": outcome,
            "resolved_at": now_str,
            "brier_score": brier,
            "resolution_note": f"自動判定: YES確率={yes_prob*100:.1f}% ≥95%"
        }
        if not dry_run:
            notify_auto_resolved(prediction_id, article_title, outcome, brier,
                                  f"YES確率={yes_prob*100:.1f}%")
        return updates

    # ── ケース 3: 確率 ≤ 5% → NO 自動判定 ───────────────────────────
    if yes_prob <= THRESHOLD_AUTO_LOW:
        outcome = determine_outcome(resolution_direction, "NO")
        scenarios = pred.get("scenarios", [])
        brier = calc_brier_score(scenarios, outcome)
        print(f"    → 自動判定 NO ({yes_prob*100:.1f}%) → {outcome} (Brier: {brier})")
        updates = {
            "status": "resolved",
            "outcome": outcome,
            "resolved_at": now_str,
            "brier_score": brier,
            "resolution_note": f"自動判定: YES確率={yes_prob*100:.1f}% ≤5%"
        }
        if not dry_run:
            notify_auto_resolved(prediction_id, article_title, outcome, brier,
                                  f"YES確率={yes_prob*100:.1f}%")
        return updates

    # ── ケース 4: 確率 70〜94% → Gemini 確認後に自動 ────────────────
    if yes_prob >= THRESHOLD_GEMINI_HIGH:
        print(f"    → Gemini 確認: YES確率={yes_prob*100:.1f}%")
        if not dry_run:
            result = gemini_confirm_resolution(question, yes_prob, resolution_direction)
            if result["resolved"] and result["outcome"] in ("YES", "NO"):
                outcome = determine_outcome(resolution_direction, result["outcome"])
                scenarios = pred.get("scenarios", [])
                brier = calc_brier_score(scenarios, outcome)
                print(f"    → Gemini 判定: {result['outcome']} → {outcome} (Brier: {brier})")
                updates = {
                    "status": "resolved",
                    "outcome": outcome,
                    "resolved_at": now_str,
                    "brier_score": brier,
                    "resolution_note": f"Gemini判定: {result['outcome']} ({result['reason']})"
                }
                notify_auto_resolved(prediction_id, article_title, outcome, brier,
                                      f"Gemini: {result['reason']}")
                return updates
            else:
                print(f"    [WARN] Gemini 判定失敗: {result['reason']}")
        return None

    # ── ケース 5: 確率 6〜29% → Gemini 確認後に自動 (NO 側) ─────────
    if yes_prob <= THRESHOLD_GEMINI_LOW:
        print(f"    → Gemini 確認: YES確率={yes_prob*100:.1f}% (NO寄り)")
        if not dry_run:
            result = gemini_confirm_resolution(question, yes_prob, resolution_direction)
            if result["resolved"] and result["outcome"] in ("YES", "NO"):
                outcome = determine_outcome(resolution_direction, result["outcome"])
                scenarios = pred.get("scenarios", [])
                brier = calc_brier_score(scenarios, outcome)
                print(f"    → Gemini 判定: {result['outcome']} → {outcome} (Brier: {brier})")
                updates = {
                    "status": "resolved",
                    "outcome": outcome,
                    "resolved_at": now_str,
                    "brier_score": brier,
                    "resolution_note": f"Gemini判定: {result['outcome']} ({result['reason']})"
                }
                notify_auto_resolved(prediction_id, article_title, outcome, brier,
                                      f"Gemini: {result['reason']}")
                return updates
            else:
                print(f"    [WARN] Gemini 判定失敗: {result['reason']}")
        return None

    # ── ケース 6: 30〜70% の曖昧ゾーン ──────────────────────────────
    is_deadline = deadline_passed(close_date)
    if is_deadline:
        # 35〜65% の場合: 基本シナリオ（不確定）
        if THRESHOLD_AMBIGUOUS_LOW <= yes_prob <= THRESHOLD_AMBIGUOUS_HIGH:
            outcome = "基本シナリオ"
            scenarios = pred.get("scenarios", [])
            brier = calc_brier_score(scenarios, outcome)
            print(f"    → 基本シナリオ (期日到来、確率={yes_prob*100:.1f}%, Brier: {brier})")
            updates = {
                "status": "resolved",
                "outcome": outcome,
                "resolved_at": now_str,
                "brier_score": brier,
                "resolution_note": f"期日到来・不確定: YES確率={yes_prob*100:.1f}% (基本シナリオ適用)"
            }
            if not dry_run:
                notify_auto_resolved(prediction_id, article_title, outcome, brier,
                                      f"期日到来・不確定 ({yes_prob*100:.1f}%)")
            return updates
        else:
            # 30〜35% or 65〜70% かつ期日到来: 手動通知
            print(f"    → 手動判定通知 (期日到来、確率={yes_prob*100:.1f}%)")
            if not dry_run:
                notify_manual_review(prediction_id, article_title, question,
                                      yes_prob, resolution_direction, close_date)
    else:
        # 期日未到来: 監視継続（何もしない）
        days_info = f"(close_date: {close_date or '不明'})"
        print(f"    → 監視継続 {days_info}")

    return None


def run_resolver(dry_run: bool = False):
    """メイン処理"""
    print(f"=== prediction_resolver.py {'[DRY RUN]' if dry_run else ''} ===")
    print(f"時刻: {datetime.now().strftime('%Y-%m-%d %H:%M JST')}")
    print()

    db = get_db()
    data = load_prediction_db()
    predictions = data.get("predictions", [])

    resolved_count = 0
    skipped_count = 0
    manual_count = 0

    for pred in predictions:
        prediction_id = pred["prediction_id"]
        links = get_links_for_prediction(db, prediction_id)

        if not links:
            print(f"  [SKIP] {prediction_id}: nowpattern_links 未設定")
            skipped_count += 1
            continue

        updates = process_prediction(pred, list(links), db, dry_run)

        if updates:
            if not dry_run:
                pred.update(updates)
            resolved_count += 1
        elif pred.get("status") != "resolved":
            manual_count += 1

    db.close()

    # prediction_db.json を保存
    if not dry_run and resolved_count > 0:
        save_prediction_db(data)
        print(f"\n✅ prediction_db.json 更新: {resolved_count} 件")

    print(f"\n=== 集計 ===")
    print(f"解決済み: {resolved_count} 件")
    print(f"スキップ (リンクなし): {skipped_count} 件")
    print(f"手動/継続監視: {manual_count} 件")

    return resolved_count


def show_status():
    """統計表示"""
    db = get_db()
    cur = db.cursor()

    print("=== market_history.db ===")
    cur.execute("SELECT COUNT(*) FROM markets")
    print(f"  markets: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM probability_snapshots")
    print(f"  snapshots: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM nowpattern_links")
    links_count = cur.fetchone()[0]
    print(f"  nowpattern_links: {links_count}")

    if links_count > 0:
        print("\n  Links:")
        cur.execute("""
            SELECT nl.prediction_id, nl.resolution_direction, m.question,
                   m.close_date, m.resolved
            FROM nowpattern_links nl
            JOIN markets m ON nl.market_id = m.id
        """)
        for row in cur.fetchall():
            print(f"    [{row['prediction_id']}] {row['question'][:50]}...")
            print(f"      direction={row['resolution_direction']}, "
                  f"close={row['close_date']}, resolved={row['resolved']}")

    db.close()

    print("\n=== prediction_db.json ===")
    data = load_prediction_db()
    predictions = data.get("predictions", [])
    stats = data.get("stats", {})
    print(f"  predictions: {len(predictions)}")
    for pred in predictions:
        has_link = "✅" if any(True for _ in []) else "❌"
        print(f"  [{pred['prediction_id']}] {pred.get('article_title', '')[:40]}...")
        print(f"    status={pred.get('status', 'open')}, "
              f"brier={pred.get('brier_score')}, "
              f"outcome={pred.get('outcome')}")
        print(f"    resolution_question: {'あり' if pred.get('resolution_question') else '★なし'}")
        print(f"    resolution_direction: {'あり' if pred.get('resolution_direction') else '★なし'}")


def show_links():
    """nowpattern_links の一覧表示"""
    db = get_db()
    links = get_all_links(db)
    db.close()

    if not links:
        print("nowpattern_links は空です。")
        print("\n追加方法:")
        print("  python3 prediction_resolver.py --add-link \\")
        print("    --prediction-id NP-2026-XXXX \\")
        print("    --market-id <market_history.db の markets.id> \\")
        print("    --direction pessimistic/optimistic")
        return

    print(f"=== nowpattern_links ({len(links)} 件) ===")
    for link in links:
        print(f"\n[{link['prediction_id']}]")
        print(f"  market: {link['question']}")
        print(f"  source: {link['source']} / {link['external_id']}")
        print(f"  direction: {link['resolution_direction']}")
        print(f"  close_date: {link['close_date']}")
        print(f"  resolved: {link['resolved']} ({link['resolution']})")


def add_link(prediction_id: str, market_id: int, direction: str, notes: str = ""):
    """
    nowpattern_links にエントリを追加する。
    使用例:
      python3 prediction_resolver.py --add-link --prediction-id NP-2026-0001 --market-id 42 --direction pessimistic
    """
    db = get_db()
    cur = db.cursor()

    # market が存在するか確認
    cur.execute("SELECT id, source, external_id, question FROM markets WHERE id = ?", (market_id,))
    market = cur.fetchone()
    if not market:
        print(f"[ERROR] market_id={market_id} が存在しません")
        db.close()
        return False

    # prediction が prediction_db.json に存在するか確認
    data = load_prediction_db()
    pred_ids = [p["prediction_id"] for p in data.get("predictions", [])]
    if prediction_id not in pred_ids:
        print(f"[ERROR] prediction_id={prediction_id} が prediction_db.json に存在しません")
        db.close()
        return False

    now_str = datetime.now(timezone.utc).isoformat()
    try:
        cur.execute("""
            INSERT OR REPLACE INTO nowpattern_links
            (prediction_id, market_id, source, external_market_id, resolution_direction, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (prediction_id, market_id, market["source"], market["external_id"],
              direction, notes, now_str))
        db.commit()
        print(f"✅ リンク追加: {prediction_id} → market_id={market_id}")
        print(f"  market: {market['question']}")
        print(f"  direction: {direction}")
        db.close()
        return True
    except Exception as e:
        print(f"[ERROR] リンク追加失敗: {e}")
        db.close()
        return False


def search_markets(keyword: str, limit: int = 20):
    """
    キーワードで market を検索する (link 設定時に使う)
    使用例:
      python3 prediction_resolver.py --search "Fed rate" --limit 10
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT m.id, m.source, m.external_id, m.question, m.event_title,
               m.close_date, m.resolved,
               ps.yes_prob, ps.snapshot_date
        FROM markets m
        LEFT JOIN (
            SELECT market_id, yes_prob, snapshot_date
            FROM probability_snapshots
            WHERE (market_id, snapshot_date) IN (
                SELECT market_id, MAX(snapshot_date) FROM probability_snapshots GROUP BY market_id
            )
        ) ps ON m.id = ps.market_id
        WHERE m.question LIKE ? OR m.event_title LIKE ?
        ORDER BY ps.yes_prob DESC
        LIMIT ?
    """, (f"%{keyword}%", f"%{keyword}%", limit))

    rows = cur.fetchall()
    db.close()

    if not rows:
        print(f"「{keyword}」にマッチする market が見つかりません")
        return

    print(f"=== 検索結果: 「{keyword}」({len(rows)} 件) ===\n")
    for row in rows:
        yes_p = f"{row['yes_prob']*100:.1f}%" if row['yes_prob'] is not None else "N/A"
        print(f"  ID={row['id']} [{row['source']}]")
        print(f"  Q: {row['question']}")
        print(f"  Event: {row['event_title'] or 'N/A'}")
        print(f"  YES確率: {yes_p} ({row['snapshot_date'] or 'N/A'})")
        print(f"  close_date: {row['close_date'] or '不明'}")
        print()


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nowpattern 予測解決エンジン")
    parser.add_argument("--dry-run", action="store_true", help="変更なしで確認のみ")
    parser.add_argument("--status", action="store_true", help="DB・JSON 統計表示")
    parser.add_argument("--link", action="store_true", help="nowpattern_links 一覧表示")
    parser.add_argument("--add-link", action="store_true", help="nowpattern_links にエントリ追加")
    parser.add_argument("--prediction-id", help="予測 ID (例: NP-2026-0001)")
    parser.add_argument("--market-id", type=int, help="market_history.db の markets.id")
    parser.add_argument("--direction", choices=["pessimistic", "optimistic"],
                        help="resolution_direction")
    parser.add_argument("--notes", default="", help="メモ")
    parser.add_argument("--search", help="キーワードで market を検索")
    parser.add_argument("--limit", type=int, default=20, help="検索結果の最大件数")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.link:
        show_links()
    elif args.add_link:
        if not args.prediction_id or not args.market_id or not args.direction:
            parser.error("--add-link には --prediction-id / --market-id / --direction が必要です")
        add_link(args.prediction_id, args.market_id, args.direction, args.notes)
    elif args.search:
        search_markets(args.search, args.limit)
    else:
        run_resolver(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
