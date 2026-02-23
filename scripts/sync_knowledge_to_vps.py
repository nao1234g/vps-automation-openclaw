#!/usr/bin/env python3
"""
ローカルClaude CodeからVPSのAGENT_KNOWLEDGE.mdに事実を追加するラッパー。
使い方: python sync_knowledge_to_vps.py --key KEY --value VALUE [--silent]

Claudeが新しい事実をユーザーから聞いたとき、このスクリプトをSSH経由で呼び出す。
全エージェント（NEO-ONE/TWO/GPT）が次タスク時に自動で読み込む。
"""
import subprocess
import argparse
import sys

VPS = "root@163.44.124.123"
REMOTE_SCRIPT = "/opt/shared/scripts/add_knowledge.py"


def sync(key: str, value: str, silent: bool = False):
    silent_flag = "--silent" if silent else ""
    cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
        "-o", "BatchMode=yes", VPS,
        f'python3 {REMOTE_SCRIPT} --key "{key}" --value "{value}" --agent local-claude {silent_flag}'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode == 0:
        print(f"[OK] VPS AGENT_KNOWLEDGE.md updated: {key} = {value}")
        return True
    else:
        print(f"[FAIL] SSH error: {result.stderr}")
        return False


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--key", required=True, help="事実のキー（例: Xアカウント）")
    p.add_argument("--value", required=True, help="事実の内容（例: @nowpattern で投稿可能）")
    p.add_argument("--silent", action="store_true", help="Telegram通知を送らない")
    args = p.parse_args()
    ok = sync(args.key, args.value, args.silent)
    sys.exit(0 if ok else 1)
