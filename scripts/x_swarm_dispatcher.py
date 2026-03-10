#!/usr/bin/env python3
"""
X Swarm Dispatcher — 100投稿/日を4フォーマットで分散投稿
======================================================
フォーマットを分散させてスパム判定を回避しつつ、Q（行動量）を維持する。

Content Portfolio:
  LINK     (20%): nowpattern.comリンク付き。予測にはPoll自動付与
  NATIVE   (30%): リンクなし長文/スレッド。滞在時間特化
  RED_TEAM (20%): 2視点の討論スレッド。会話スコア150倍ブースト
  REPLY    (30%): トレンドへの引用リポスト/分析リプライ

認証: OAuth1（X API v2 Pay-Per-Use）
cron: */5 * * * * source /opt/cron-env.sh && python3 /opt/shared/scripts/x_swarm_dispatcher.py

Usage:
  python3 x_swarm_dispatcher.py                  # 通常実行（1サイクル、4〜6件投稿）
  python3 x_swarm_dispatcher.py --dry-run        # 投稿せずに確認
  python3 x_swarm_dispatcher.py --retry-dlq      # DLQの失敗投稿を再試行
  python3 x_swarm_dispatcher.py --status         # 今日の投稿状況を表示
"""

import json
import os
import sys
import time
import random
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from requests_oauthlib import OAuth1

# ─────────── Config ───────────
SCRIPTS_DIR = Path("/opt/shared/scripts")
SWARM_STATE_FILE = SCRIPTS_DIR / "x_swarm_state.json"
DLQ_FILE = SCRIPTS_DIR / "x_dlq.json"
PREDICTION_DB = SCRIPTS_DIR / "prediction_db.json"
BREAKING_QUEUE = SCRIPTS_DIR / "breaking_queue.json"

X_API_URL = "https://api.twitter.com/2/tweets"
X_MAX_CHARS = 1400
JST = timezone(timedelta(hours=9))

MANDATORY_HASHTAGS = ["#Nowpattern", "#ニュース分析"]

# Content Portfolio: format → daily target percentage
PORTFOLIO = {
    "LINK":     0.20,  # 20件/日
    "NATIVE":   0.30,  # 30件/日
    "RED_TEAM": 0.20,  # 20件/日
    "REPLY":    0.30,  # 30件/日
}
DAILY_TARGET = 100

# ボット対策
POST_INTERVAL_MIN = 300   # 5分
POST_INTERVAL_MAX = 900   # 15分
QUIET_HOURS = (22, 8)     # 22:00-08:00 JST は投稿禁止
MAX_CONSECUTIVE_SAME = 2  # 同一フォーマット最大連続数
DLQ_MAX_RETRIES = 3
DLQ_COOLDOWN_429 = 1800   # 429エラー時30分クールダウン

# Per-cycle batch (5分cron → 1日288サイクル, 100投稿/288 ≈ 0.35件/サイクル → 余裕を持って4-6件)
CYCLE_BATCH_SIZE = 5


# ─────────── Auth ───────────

def get_auth():
    """OAuth1認証オブジェクトを取得"""
    keys = ["TWITTER_API_KEY", "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"]
    vals = [os.environ.get(k, "") for k in keys]
    if not all(vals):
        print("ERROR: Twitter認証情報が不足: " + ", ".join(
            k for k, v in zip(keys, vals) if not v))
        sys.exit(1)
    return OAuth1(*vals)


# ─────────── State Management ───────────

def load_state():
    """今日の投稿状態を読み込み"""
    today = datetime.now(JST).strftime("%Y-%m-%d")
    if SWARM_STATE_FILE.exists():
        state = json.loads(SWARM_STATE_FILE.read_text(encoding="utf-8"))
        if state.get("date") == today:
            return state
    return {
        "date": today,
        "posted": {"LINK": 0, "NATIVE": 0, "RED_TEAM": 0, "REPLY": 0},
        "total": 0,
        "last_format": "",
        "consecutive_same": 0,
        "last_post_time": "",
        "history": [],
    }


def save_state(state):
    SWARM_STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_dlq():
    if DLQ_FILE.exists():
        return json.loads(DLQ_FILE.read_text(encoding="utf-8"))
    return []


def save_dlq(dlq):
    DLQ_FILE.write_text(
        json.dumps(dlq, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────── Format Selection ───────────

def select_next_format(state):
    """最適な次のフォーマットを選択（比率バランス + 連続回避）"""
    posted = state["posted"]
    total = max(state["total"], 1)

    # 各フォーマットの「不足度」を計算（ターゲット比率 - 実績比率）
    deficits = {}
    for fmt, target_pct in PORTFOLIO.items():
        actual_pct = posted.get(fmt, 0) / total
        deficits[fmt] = target_pct - actual_pct

    # 連続回避: 同一フォーマットがMAX_CONSECUTIVE_SAME回連続なら除外
    last_fmt = state.get("last_format", "")
    consecutive = state.get("consecutive_same", 0)
    if consecutive >= MAX_CONSECUTIVE_SAME and last_fmt in deficits:
        deficits.pop(last_fmt)

    if not deficits:
        deficits = {k: v for k, v in PORTFOLIO.items() if k != last_fmt}

    # 不足度が最大のフォーマットを選択（同率ならランダム）
    max_deficit = max(deficits.values())
    candidates = [f for f, d in deficits.items() if d >= max_deficit - 0.02]
    return random.choice(candidates)


# ─────────── Hashtag Enforcement ───────────

def enforce_hashtags(text):
    """必須ハッシュタグが欠けていれば末尾に追加"""
    missing = [tag for tag in MANDATORY_HASHTAGS if tag not in text]
    if missing:
        text = text.rstrip() + "\n\n" + " ".join(missing)
    return text


# ─────────── X API Posting ───────────

def post_tweet(auth, text, poll=None, quote_tweet_id=None,
               reply_to_id=None):
    """X API v2で投稿。poll/quote/replyに対応。"""
    text = enforce_hashtags(text)
    if len(text) > X_MAX_CHARS:
        text = text[:X_MAX_CHARS - 3] + "..."

    payload = {"text": text}

    if poll:
        # Poll: options (2-4, max 25 chars each), duration_minutes (5-10080)
        payload["poll"] = {
            "options": [opt[:25] for opt in poll["options"][:4]],
            "duration_minutes": poll.get("duration_minutes", 1440),
        }

    if quote_tweet_id:
        payload["quote_tweet_id"] = str(quote_tweet_id)

    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": str(reply_to_id)}

    resp = requests.post(X_API_URL, auth=auth, json=payload, timeout=30)
    return resp


def post_thread(auth, texts):
    """スレッドを投稿（最初のツイート → 自分にリプライの連鎖）"""
    results = []
    parent_id = None
    for i, text in enumerate(texts):
        text = enforce_hashtags(text) if i == 0 else text  # ハッシュタグは1つ目のみ
        payload = {"text": text[:X_MAX_CHARS]}
        if parent_id:
            payload["reply"] = {"in_reply_to_tweet_id": parent_id}

        resp = requests.post(X_API_URL, auth=auth, json=payload, timeout=30)
        if resp.status_code == 201:
            data = resp.json().get("data", {})
            parent_id = data.get("id")
            results.append({"id": parent_id, "text": text[:80]})
        else:
            results.append({"error": resp.status_code, "text": text[:80]})
            break
        if i < len(texts) - 1:
            time.sleep(random.randint(3, 8))  # スレッド内も短い間隔

    return results


# ─────────── Content Generators ───────────

def load_breaking_queue():
    """breaking_queue.jsonから投稿待ちアイテムを取得"""
    if BREAKING_QUEUE.exists():
        items = json.loads(BREAKING_QUEUE.read_text(encoding="utf-8"))
        return [i for i in items if i.get("status") == "article_ready"]
    return []


def load_predictions():
    """prediction_db.jsonからactive予測を取得"""
    if PREDICTION_DB.exists():
        db = json.loads(PREDICTION_DB.read_text(encoding="utf-8"))
        return [p for p in db.get("predictions", []) if p.get("status") == "active"]
    return []


def generate_link_content(item):
    """LINK型: 記事リンク + フック + Poll（予測あり時）"""
    ghost_url = item.get("ghost_url", "")
    title = item.get("article_title", item.get("text", ""))[:100]
    cat = item.get("cat", "")

    text = f"📊 {title}\n\n📖 深層分析:\n{ghost_url}"

    # 予測がある場合はPollを生成
    poll = None
    prediction = item.get("prediction")
    if prediction:
        prob = prediction.get("our_pick_prob", 50)
        question = prediction.get("resolution_question", "")[:60]
        poll = {
            "options": [
                f"YES ({prob}%でAI予測)",
                "NO",
                "まだ分からない",
                "記事で確認する",
            ],
            "duration_minutes": 1440,  # 24時間
        }
        text = f"🎯 AIは{prob}%と予測\n{question}\n\n📖 {ghost_url}"

    return {"text": text, "poll": poll, "cat": cat}


def generate_native_content(item):
    """NATIVE型: リンクなし長文/スレッド。力学分析を直接展開"""
    title = item.get("article_title", "")[:60]
    text_body = item.get("text", item.get("x_comment", ""))

    # スレッド化（300字超の場合）
    if len(text_body) > 300:
        # 3分割してスレッドに
        chunk_size = len(text_body) // 3
        tweets = [
            f"🧵 {title}\n\n{text_body[:chunk_size]}",
            text_body[chunk_size:chunk_size*2],
            text_body[chunk_size*2:] + "\n\n💡 力学分析の全文はプロフィールのリンクから",
        ]
        return {"thread": tweets, "cat": item.get("cat", "")}
    else:
        text = f"💡 {title}\n\n{text_body}"
        return {"text": text, "cat": item.get("cat", "")}


def generate_redteam_content(item):
    """RED-TEAM型: 2視点の討論スレッド + Poll"""
    title = item.get("article_title", "")[:50]
    scenarios = item.get("scenarios", {})
    optimistic = scenarios.get("optimistic", {})
    pessimistic = scenarios.get("pessimistic", {})

    opt_text = optimistic.get("description", "楽観シナリオ")[:200]
    pes_text = pessimistic.get("description", "悲観シナリオ")[:200]
    opt_prob = optimistic.get("probability", "?")
    pes_prob = pessimistic.get("probability", "?")

    tweets = [
        f"⚡ {title}\n\n2つのシナリオで考える 🧵",
        f"📈 楽観シナリオ（{opt_prob}%）:\n{opt_text}",
        f"📉 悲観シナリオ（{pes_prob}%）:\n{pes_text}",
    ]

    poll = {
        "options": [
            f"楽観 ({opt_prob}%)",
            f"悲観 ({pes_prob}%)",
            "どちらでもない",
            "分析を読む",
        ],
        "duration_minutes": 1440,
    }

    return {"thread": tweets, "poll_on_last": poll, "cat": item.get("cat", "")}


def generate_reply_content(item):
    """REPLY/QRT型: トレンドニュースへの引用リポスト"""
    tweet_url = item.get("tweet_url", "")
    comment = item.get("x_comment", "")
    ghost_url = item.get("ghost_url", "")

    if not comment:
        text_preview = item.get("text", "")[:150]
        comment = f"📊 力学分析: {text_preview}"

    if ghost_url:
        comment = comment.rstrip() + f"\n\n📖 {ghost_url}"

    import re
    tweet_id = None
    m = re.search(r'/status/(\d+)', tweet_url)
    if m:
        tweet_id = m.group(1)

    return {"text": comment, "quote_tweet_id": tweet_id, "cat": item.get("cat", "")}


# ─────────── Dispatch Engine ───────────

def is_quiet_hours():
    """深夜投稿禁止時間帯かチェック"""
    now_jst = datetime.now(JST)
    hour = now_jst.hour
    start, end = QUIET_HOURS
    if start > end:  # 22:00-08:00のように日跨ぎ
        return hour >= start or hour < end
    return start <= hour < end


def dispatch_one(auth, fmt, queue_items, predictions, state, dry_run=False):
    """1件のフォーマット投稿を実行"""
    item = queue_items[0] if queue_items else {}

    # 予測情報を付与
    if predictions and not item.get("prediction"):
        for p in predictions:
            if p.get("article_id") == item.get("article_id"):
                item["prediction"] = p
                break

    content = None
    if fmt == "LINK":
        if not item.get("ghost_url"):
            return None  # リンクなしではLINK型不可
        content = generate_link_content(item)
    elif fmt == "NATIVE":
        content = generate_native_content(item)
    elif fmt == "RED_TEAM":
        content = generate_redteam_content(item)
    elif fmt == "REPLY":
        content = generate_reply_content(item)

    if not content:
        return None

    if dry_run:
        if "thread" in content:
            print(f"  [DRY-RUN] {fmt} thread ({len(content['thread'])} tweets)")
            for i, t in enumerate(content["thread"]):
                print(f"    [{i+1}] {t[:80]}...")
        else:
            print(f"  [DRY-RUN] {fmt}: {content.get('text', '')[:100]}...")
        if content.get("poll"):
            print(f"    Poll: {content['poll']['options']}")
        return {"format": fmt, "dry_run": True}

    # 実投稿
    result = None

    if "thread" in content:
        # スレッド投稿
        thread_results = post_thread(auth, content["thread"])

        # RED-TEAM: 最後のツイートにPollを付ける場合
        if content.get("poll_on_last") and thread_results:
            last = thread_results[-1]
            if last.get("id"):
                poll_text = "あなたはどちらのシナリオ？"
                poll_resp = post_tweet(
                    auth, poll_text,
                    poll=content["poll_on_last"],
                    reply_to_id=last["id"])
                if poll_resp.status_code == 201:
                    thread_results.append({"poll": True})

        if thread_results and thread_results[0].get("id"):
            result = {
                "format": fmt,
                "tweet_id": thread_results[0]["id"],
                "thread_length": len(thread_results),
            }
        else:
            return {"error": True, "format": fmt, "content": content}

    else:
        # 単発投稿
        resp = post_tweet(
            auth, content["text"],
            poll=content.get("poll"),
            quote_tweet_id=content.get("quote_tweet_id"))

        if resp.status_code == 201:
            data = resp.json().get("data", {})
            result = {
                "format": fmt,
                "tweet_id": data.get("id", ""),
                "url": f"https://x.com/nowpattern/status/{data.get('id', '')}",
            }
        elif resp.status_code == 429:
            return {"error": 429, "format": fmt, "content": content}
        else:
            return {
                "error": resp.status_code,
                "format": fmt,
                "detail": resp.text[:200],
                "content": content,
            }

    return result


def run_cycle(auth, dry_run=False):
    """1サイクル（5分間隔）の投稿を実行"""
    if is_quiet_hours():
        print("🌙 深夜投稿禁止時間帯（22:00-08:00 JST）。スキップ。")
        return

    state = load_state()

    if state["total"] >= DAILY_TARGET:
        print(f"📊 本日の目標 {DAILY_TARGET} 件達成済み（{state['total']}件投稿済み）")
        return

    queue_items = load_breaking_queue()
    predictions = load_predictions()

    print(f"📋 キュー: {len(queue_items)}件 | 予測: {len(predictions)}件 | 本日: {state['total']}/{DAILY_TARGET}")

    posted_this_cycle = 0

    for _ in range(CYCLE_BATCH_SIZE):
        if state["total"] >= DAILY_TARGET:
            break
        if not queue_items and state["total"] > 0:
            print("  キューが空です。次のサイクルで待機。")
            break

        fmt = select_next_format(state)
        print(f"\n▶ フォーマット: {fmt} (LINK:{state['posted']['LINK']} "
              f"NATIVE:{state['posted']['NATIVE']} "
              f"RED_TEAM:{state['posted']['RED_TEAM']} "
              f"REPLY:{state['posted']['REPLY']})")

        result = dispatch_one(auth, fmt, queue_items, predictions, state, dry_run)

        if result is None:
            # このフォーマットに適したコンテンツがない → 別のフォーマットを試す
            alt_fmts = [f for f in PORTFOLIO if f != fmt]
            for alt in alt_fmts:
                result = dispatch_one(auth, alt, queue_items, predictions, state, dry_run)
                if result is not None:
                    fmt = alt
                    break

        if result is None:
            print("  すべてのフォーマットで投稿可能なコンテンツがありません。")
            break

        if result.get("error"):
            error_code = result["error"]
            if error_code == 429:
                print(f"  ⚠️ Rate Limit (429). DLQに退避。{DLQ_COOLDOWN_429//60}分後に再試行。")
                dlq = load_dlq()
                dlq.append({
                    "format": fmt,
                    "content": result.get("content", {}),
                    "retries": 0,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                    "error": 429,
                })
                save_dlq(dlq)
                break  # 429はサイクル終了
            else:
                print(f"  ❌ 投稿失敗 (HTTP {error_code}): {result.get('detail', '')[:100]}")
                dlq = load_dlq()
                dlq.append({
                    "format": fmt,
                    "content": result.get("content", {}),
                    "retries": 0,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                    "error": error_code,
                })
                save_dlq(dlq)
                continue

        # 成功
        if not dry_run:
            state["posted"][fmt] = state["posted"].get(fmt, 0) + 1
            state["total"] += 1
            state["last_post_time"] = datetime.now(timezone.utc).isoformat()

            if fmt == state.get("last_format"):
                state["consecutive_same"] = state.get("consecutive_same", 0) + 1
            else:
                state["consecutive_same"] = 1
            state["last_format"] = fmt

            state["history"].append({
                "format": fmt,
                "tweet_id": result.get("tweet_id", ""),
                "time": state["last_post_time"],
            })

            # キューから消費
            if queue_items:
                consumed = queue_items.pop(0)
                consumed["status"] = "posted"

            save_state(state)

        posted_this_cycle += 1

        if result.get("tweet_id"):
            print(f"  ✅ {fmt} posted: https://x.com/nowpattern/status/{result['tweet_id']}")
        elif result.get("dry_run"):
            print(f"  ✅ [DRY-RUN] {fmt} would be posted")

        # 次の投稿まで待機
        if posted_this_cycle < CYCLE_BATCH_SIZE:
            delay = random.randint(POST_INTERVAL_MIN, POST_INTERVAL_MAX)
            if not dry_run:
                print(f"  ⏳ 次の投稿まで {delay//60}分{delay%60}秒待機")
                time.sleep(delay)

    # キューを保存
    if not dry_run and BREAKING_QUEUE.exists():
        all_items = json.loads(BREAKING_QUEUE.read_text(encoding="utf-8"))
        remaining = [i for i in all_items if i.get("status") != "posted"]
        BREAKING_QUEUE.write_text(
            json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== サイクル完了: {posted_this_cycle}件投稿 | 本日合計: {state['total']}/{DAILY_TARGET} ===")


def retry_dlq(auth, dry_run=False):
    """DLQ（Dead Letter Queue）の失敗投稿を再試行"""
    dlq = load_dlq()
    if not dlq:
        print("DLQは空です。")
        return

    print(f"📋 DLQ: {len(dlq)}件の失敗投稿")
    remaining = []

    for item in dlq:
        retries = item.get("retries", 0)
        if retries >= DLQ_MAX_RETRIES:
            print(f"  ❌ {item['format']}: {DLQ_MAX_RETRIES}回失敗。スキップ（Telegram通知推奨）。")
            continue

        # 429エラーのクールダウンチェック
        if item.get("error") == 429:
            added = datetime.fromisoformat(item["added_at"])
            elapsed = (datetime.now(timezone.utc) - added).total_seconds()
            if elapsed < DLQ_COOLDOWN_429:
                remaining.append(item)
                print(f"  ⏳ {item['format']}: 429クールダウン中（残り{int(DLQ_COOLDOWN_429-elapsed)}秒）")
                continue

        content = item.get("content", {})
        text = content.get("text", "DLQ retry")

        if dry_run:
            print(f"  [DRY-RUN] {item['format']}: {text[:80]}...")
            continue

        resp = post_tweet(auth, text, poll=content.get("poll"),
                          quote_tweet_id=content.get("quote_tweet_id"))

        if resp.status_code == 201:
            print(f"  ✅ DLQ再試行成功: {item['format']}")
        else:
            item["retries"] = retries + 1
            item["last_retry"] = datetime.now(timezone.utc).isoformat()
            remaining.append(item)
            print(f"  ❌ DLQ再試行失敗 (HTTP {resp.status_code}): {item['format']} (retry {item['retries']}/{DLQ_MAX_RETRIES})")

    save_dlq(remaining)
    print(f"DLQ残り: {len(remaining)}件")


def show_status():
    """今日の投稿状況を表示"""
    state = load_state()
    dlq = load_dlq()

    print(f"📊 X Swarm Status — {state['date']}")
    print(f"   合計: {state['total']}/{DAILY_TARGET}")
    print()

    for fmt, target_pct in PORTFOLIO.items():
        actual = state["posted"].get(fmt, 0)
        target = int(DAILY_TARGET * target_pct)
        pct = (actual / target * 100) if target > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"   {fmt:10s}: {actual:3d}/{target:3d} ({pct:5.1f}%) {bar}")

    print()
    if dlq:
        print(f"   ⚠️  DLQ: {len(dlq)}件の失敗投稿あり")
    else:
        print(f"   ✅ DLQ: 空（失敗投稿なし）")

    now_jst = datetime.now(JST)
    if is_quiet_hours():
        print(f"   🌙 現在: 深夜投稿禁止時間帯 ({now_jst.strftime('%H:%M')} JST)")
    else:
        print(f"   🟢 現在: 投稿可能 ({now_jst.strftime('%H:%M')} JST)")


# ─────────── Main ───────────

def main():
    parser = argparse.ArgumentParser(description="X Swarm Dispatcher — 4フォーマット分散投稿")
    parser.add_argument("--dry-run", action="store_true", help="投稿せずに確認")
    parser.add_argument("--retry-dlq", action="store_true", help="DLQ再試行")
    parser.add_argument("--status", action="store_true", help="投稿状況表示")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    auth = get_auth()

    if args.retry_dlq:
        retry_dlq(auth, dry_run=args.dry_run)
        return

    run_cycle(auth, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
