#!/usr/bin/env python3
"""
VPSのSHARED_STATE.mdからMEMORY.mdのLIVE STATEセクションを自動更新するスクリプト。
session-start.sh から呼び出す、またはWindowsタスクスケジューラで定期実行する。
"""
import subprocess
import re
from pathlib import Path
from datetime import datetime

MEMORY_PATH = Path(r"C:\Users\user\.claude\projects\c--Users-user-OneDrive--------vps-automation-openclaw\memory\MEMORY.md")
VPS = "root@163.44.124.123"


def get_vps_state() -> dict:
    """SSH経由でVPSの現状を取得"""
    result = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
         "-o", "BatchMode=yes", VPS,
         "python3 -c \""
         "import sqlite3, subprocess, os;"
         "db = sqlite3.connect('/var/www/nowpattern/content/data/ghost.db');"
         "c = db.cursor();"
         "c.execute(\\\"SELECT COUNT(*) FROM posts WHERE status='published' AND type='post'\\\");"
         "articles = c.fetchone()[0];"
         "c.execute(\\\"SELECT COUNT(*) FROM posts WHERE status='published' AND type='post' AND slug LIKE '%-en'\\\");"
         "en = c.fetchone()[0];"
         "db.close();"
         "print(f'articles={articles},en={en}');"
         "\""
        ],
        capture_output=True, text=True, timeout=15
    )

    state = {
        "articles": "unknown",
        "en_articles": "unknown",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M JST"),
        "connected": False
    }

    if result.returncode == 0:
        state["connected"] = True
        for line in result.stdout.strip().split('\n'):
            for key in ["articles", "en"]:
                match = re.search(rf'{key}=(\d+)', line)
                if match:
                    if key == "en":
                        state["en_articles"] = match.group(1)
                    else:
                        state[key] = match.group(1)

    return state


def update_memory(state: dict):
    """MEMORY.mdのLIVE STATEセクションを更新（冪等: 既存のステータス行を置換）"""
    content = MEMORY_PATH.read_text(encoding="utf-8")

    if not state["connected"]:
        status_line = "> ⚠️ VPS接続失敗 — 手動確認が必要"
    else:
        ja = int(state.get("articles", 0)) - int(state.get("en_articles", 0))
        status_line = (
            f"> 自動更新: {state['timestamp']} | "
            f"記事数: {state['articles']} (JA:{ja}, EN:{state['en_articles']})"
        )

    # Step1: 既存の「> 自動更新:」行を削除（冪等性確保）
    content = re.sub(r'\n> 自動更新:[^\n]*', '', content)
    content = re.sub(r'\n> ⚠️ VPS接続失敗[^\n]*', '', content)

    # Step2: 「このセクションは定期更新...」行の後にステータス行を挿入
    new_content = re.sub(
        r'(> このセクションは定期更新されるが[^\n]*)',
        rf'\1\n{status_line}',
        content
    )

    if new_content != content:
        MEMORY_PATH.write_text(new_content, encoding="utf-8")
        print(f"[OK] MEMORY.md updated: {state['timestamp']}")
    else:
        print("[WARN] MEMORY.md pattern not found — manual check needed")


if __name__ == "__main__":
    state = get_vps_state()
    update_memory(state)
    if state["connected"]:
        print(f"  Articles: {state['articles']} (EN: {state['en_articles']})")
    else:
        print("  [WARN] VPS unreachable")
