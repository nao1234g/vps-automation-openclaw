#!/usr/bin/env python3
"""
neo_queue_dispatcher.py — neo_task_queue.json のペンディングタスクをNEOへ送信

動作:
  1. /opt/shared/neo_task_queue.json を読む
  2. pending タスクを slug 単位でグループ化（同記事の複数issueを1プロンプトに統合）
  3. 優先度順に MAX_DISPATCH 件をNEO-ONE/NEO-TWO 交互に割り当て
  4. send-to-neo.py 経由で送信
  5. dispatched に更新

cron: */15 * * * *  (15分ごと)
ログ: /opt/shared/logs/neo_dispatcher.log
"""

import json
import os
import subprocess
import sys
import logging
from datetime import datetime, timezone
from collections import defaultdict

# ===== 設定 =====
QUEUE_FILE   = "/opt/shared/neo_task_queue.json"
SEND_SCRIPT  = "/opt/shared/scripts/send-to-neo.py"
LOG_FILE     = "/opt/shared/logs/neo_dispatcher.log"
MAX_DISPATCH = 5   # 1回あたり最大送信スラッグ数
BOT_CYCLE    = ["neo1", "neo2"]  # 交互割り当て
STATE_FILE   = "/opt/shared/logs/neo_dispatcher_state.json"

# ===== ログ =====
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return {"tasks": []}
    with open(QUEUE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_queue(q):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"bot_index": 0, "dispatched_total": 0}
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_state(s):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def build_merged_prompt(slug, title, lang, issues_data):
    """同一スラッグの複数issueを1つのプロンプトに統合"""
    issues_list = []
    task_ids = []
    for td in issues_data:
        issues_list.append(f"  - {td.get('issue', 'unknown')}")
        task_ids.append(td.get("task_id", ""))

    task_ids_str = "\n".join(f"  {tid}" for tid in task_ids)

    prompt = f"""【QA Sentinel 自動委譲タスク】
記事スラッグ: {slug}
タイトル: {title}
言語: {"日本語" if lang == "ja" else "英語"}
検出された問題（{len(issues_data)}件）:
{chr(10).join(issues_list)}

修正手順:
1. Ghost Admin API で記事取得: GET /ghost/api/admin/posts/?filter=slug:{slug}
2. 各問題に応じて修正（セクション追加/文字数補強/翻訳改善）
3. Ghost Admin API で更新: PUT /ghost/api/admin/posts/<post_id>/
4. 完了後、/opt/shared/neo_task_queue.json の以下タスクを status=done に変更:
{task_ids_str}

優先度: HIGH"""
    return prompt


def send_to_bot(bot_key, message):
    """send-to-neo.py 経由で送信"""
    # null byte / 制御文字を除去（subprocess引数に渡せない）
    message = message.replace(chr(0), '')
    result = subprocess.run(
        ["python3", SEND_SCRIPT, "--bot", bot_key, "--msg", message],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        return True, result.stdout.strip()
    else:
        return False, result.stderr.strip()


def main():
    now_str = datetime.now(timezone.utc).isoformat()
    logger.info(f"=== neo_queue_dispatcher START ({now_str}) ===")

    q = load_queue()
    tasks = q.get("tasks", [])
    state = load_state()

    # pending タスクを抽出
    pending = [t for t in tasks if t.get("status") == "pending"]
    logger.info(f"Pending tasks: {len(pending)}")

    if not pending:
        logger.info("Nothing to dispatch. Exit.")
        return

    # slug 単位でグループ化 (priority=最小値を代表値)
    slug_groups = defaultdict(list)
    for t in pending:
        slug = t.get("slug", "unknown")
        slug_groups[slug].append(t)

    # priority でソート（小さいほど高優先）→ MAX_DISPATCH スラッグ
    sorted_slugs = sorted(
        slug_groups.items(),
        key=lambda kv: min(t.get("priority", 99) for t in kv[1])
    )[:MAX_DISPATCH]

    logger.info(f"Dispatching {len(sorted_slugs)} slugs (of {len(slug_groups)} unique)")

    dispatched_count = 0
    bot_index = state.get("bot_index", 0)

    for slug, slug_tasks in sorted_slugs:
        # slug内の全issueをマージ
        title = slug_tasks[0].get("title", "")
        lang  = slug_tasks[0].get("lang", "ja")
        prompt = build_merged_prompt(slug, title, lang, slug_tasks)
        bot_key = BOT_CYCLE[bot_index % len(BOT_CYCLE)]

        logger.info(f"Sending slug={slug} ({len(slug_tasks)} issues) → {bot_key}")
        ok, msg = send_to_bot(bot_key, prompt)

        if ok:
            # 全タスクを dispatched に更新
            dispatched_at = datetime.now(timezone.utc).isoformat()
            for t in tasks:
                if t.get("slug") == slug and t.get("status") == "pending":
                    t["status"] = "dispatched"
                    t["dispatched_at"] = dispatched_at
                    t["dispatched_to"] = bot_key
            dispatched_count += 1
            bot_index += 1
            logger.info(f"  OK → {bot_key}: {msg[:80]}")
        else:
            logger.error(f"  FAIL → {bot_key}: {msg[:200]}")

    # キューを保存
    q["tasks"] = tasks
    q["last_dispatch"] = now_str
    save_queue(q)

    # 状態を保存
    state["bot_index"] = bot_index
    state["dispatched_total"] = state.get("dispatched_total", 0) + dispatched_count
    state["last_run"] = now_str
    save_state(state)

    # 残件数
    remaining = sum(1 for t in tasks if t.get("status") == "pending")
    logger.info(f"Done. Dispatched: {dispatched_count} slugs. Remaining pending: {remaining}")

    # Telegram通知（残件が多い時だけ）
    if remaining > 10:
        try:
            env = {}
            for line in open("/opt/cron-env.sh"):
                if line.startswith("export "):
                    k, _, v = line[7:].strip().partition("=")
                    env[k] = v.strip().strip('"').strip("'")
            import urllib.request
            data = json.dumps({
                "chat_id": env.get("TELEGRAM_CHAT_ID", ""),
                "text": f"📋 NEO Dispatcher: {dispatched_count}件送信。残り{remaining}件pending。",
                "parse_mode": "Markdown"
            }).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{env.get('TELEGRAM_BOT_TOKEN','')}/sendMessage",
                data=data, headers={"Content-Type": "application/json"}, method="POST"
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            logger.warning(f"Telegram notify failed: {e}")


if __name__ == "__main__":
    main()
