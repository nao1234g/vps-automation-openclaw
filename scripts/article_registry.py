#!/usr/bin/env python3
"""
Article Registry — 記事の重複防止システム

Neo1/Neo2が記事を書く前にここで「予約」し、書き終わったら「完了」にする。
同じトピックを2人が書かないようにするための共有レジストリ。

使い方（VPS上で実行）:
  # 記事を書き始める前に予約（必須）
  python3 /opt/shared/scripts/article_registry.py claim --agent neo1 --topic "ホルムズ海峡封鎖リスク" --type deep_pattern

  # 記事を書き終わったら完了にする（必須）
  python3 /opt/shared/scripts/article_registry.py complete --agent neo1 --topic "ホルムズ海峡封鎖リスク" --url "https://nowpattern.com/..."

  # 現在の状態を確認（記事を書く前に必ず確認）
  python3 /opt/shared/scripts/article_registry.py status

  # キャンセル（書くのをやめた場合）
  python3 /opt/shared/scripts/article_registry.py cancel --agent neo1 --topic "ホルムズ海峡封鎖リスク"
"""

import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=9))
REGISTRY_PATH = Path("/opt/shared/article_registry.json")


def _now_str() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


def _load() -> dict:
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"articles": [], "last_updated": _now_str()}


def _save(data: dict):
    data["last_updated"] = _now_str()
    REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_status(args):
    """現在の記事レジストリを表示"""
    data = _load()
    articles = data.get("articles", [])

    in_progress = [a for a in articles if a["status"] == "in_progress"]
    completed_recent = [a for a in articles if a["status"] == "completed"][-10:]

    print(f"=== 記事レジストリ ({_now_str()}) ===\n")

    if in_progress:
        print("【執筆中】")
        for a in in_progress:
            print(f"  [{a['agent'].upper()}] {a['topic']} ({a['type']}) — {a['claimed_at']}")
    else:
        print("【執筆中】なし")

    print()
    if completed_recent:
        print("【完了済み（最新10件）】")
        for a in completed_recent:
            url = a.get("url", "URL未設定")
            print(f"  [{a['agent'].upper()}] {a['topic']} — {a['completed_at']} | {url}")
    else:
        print("【完了済み】なし")

    print(f"\n最終更新: {data.get('last_updated', '?')}")


def cmd_claim(args):
    """記事トピックを予約する（書き始める前に必ず実行）"""
    data = _load()
    articles = data.get("articles", [])

    # 重複チェック
    topic_lower = args.topic.lower()
    for a in articles:
        if a["status"] == "in_progress":
            if args.topic.lower() in a["topic"].lower() or a["topic"].lower() in topic_lower:
                print(f"ERROR: 類似トピックが既に {a['agent'].upper()} によって執筆中です:")
                print(f"  [{a['agent'].upper()}] {a['topic']} ({a['claimed_at']})")
                print("重複記事になる可能性があります。別のトピックを選んでください。")
                sys.exit(1)

    # 予約登録
    article = {
        "agent": args.agent,
        "topic": args.topic,
        "type": getattr(args, "type", "deep_pattern"),
        "status": "in_progress",
        "claimed_at": _now_str(),
        "completed_at": None,
        "url": None,
    }
    articles.append(article)
    data["articles"] = articles
    _save(data)

    print(f"OK: [{args.agent.upper()}] '{args.topic}' を予約しました")
    print("記事を書き終わったら必ず `complete` コマンドで完了にしてください")


def cmd_complete(args):
    """記事完了を記録する"""
    data = _load()
    articles = data.get("articles", [])

    found = False
    for a in articles:
        if a["agent"] == args.agent and a["topic"] == args.topic and a["status"] == "in_progress":
            a["status"] = "completed"
            a["completed_at"] = _now_str()
            a["url"] = getattr(args, "url", None) or ""
            found = True
            break

    if not found:
        # Fuzzy search
        for a in articles:
            if a["agent"] == args.agent and args.topic.lower() in a["topic"].lower() and a["status"] == "in_progress":
                a["status"] = "completed"
                a["completed_at"] = _now_str()
                a["url"] = getattr(args, "url", None) or ""
                found = True
                print(f"OK: (fuzzy match) '{a['topic']}' を完了にしました")
                break

    if not found:
        print(f"WARN: in_progress の記事が見つかりません: agent={args.agent}, topic={args.topic}")
        print("現在の執筆中一覧:")
        for a in articles:
            if a["status"] == "in_progress":
                print(f"  [{a['agent']}] {a['topic']}")
        sys.exit(1)

    data["articles"] = articles
    _save(data)
    print(f"OK: [{args.agent.upper()}] '{args.topic}' を完了としました")


def cmd_cancel(args):
    """記事予約をキャンセルする"""
    data = _load()
    articles = data.get("articles", [])

    for a in articles:
        if a["agent"] == args.agent and a["status"] == "in_progress":
            if args.topic.lower() in a["topic"].lower():
                a["status"] = "cancelled"
                a["completed_at"] = _now_str()
                _save(data)
                print(f"OK: [{args.agent.upper()}] '{a['topic']}' をキャンセルしました")
                return

    print(f"WARN: キャンセル対象が見つかりません: {args.topic}")


def cmd_list_json(args):
    """JSON形式で出力（SYSTEM_BRIEFING.mdからの呼び出し用）"""
    data = _load()
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Nowpattern 記事レジストリ")
    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="現在の状態を確認")

    # claim
    p_claim = sub.add_parser("claim", help="記事を予約")
    p_claim.add_argument("--agent", required=True, choices=["neo1", "neo2"], help="実行エージェント")
    p_claim.add_argument("--topic", required=True, help="記事トピック（日本語OK）")
    p_claim.add_argument("--type", default="deep_pattern", choices=["deep_pattern", "speed_log"])

    # complete
    p_complete = sub.add_parser("complete", help="記事完了を記録")
    p_complete.add_argument("--agent", required=True, choices=["neo1", "neo2"])
    p_complete.add_argument("--topic", required=True)
    p_complete.add_argument("--url", default="", help="公開URL")

    # cancel
    p_cancel = sub.add_parser("cancel", help="記事予約をキャンセル")
    p_cancel.add_argument("--agent", required=True, choices=["neo1", "neo2"])
    p_cancel.add_argument("--topic", required=True)

    # json (internal)
    sub.add_parser("json", help="JSON形式で出力")

    args = parser.parse_args()

    commands = {
        "status": cmd_status,
        "claim": cmd_claim,
        "complete": cmd_complete,
        "cancel": cmd_cancel,
        "json": cmd_list_json,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
