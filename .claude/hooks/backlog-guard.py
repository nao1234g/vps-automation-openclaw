#!/usr/bin/env python3
"""
BACKLOG GUARD — UserPromptSubmit Hook
=======================================
ユーザーが新しいタスク指示を出したとき、それをBACKLOG.mdに追加する前に
作業を始めないようリマインドする。

「やる」「して」「しろ」「実装」「修正」「確認」「追加」などのキーワードを検出。

動作:
1. ユーザーメッセージにタスク指示キーワードが含まれる
2. BACKLOG.md の未完了タスク数を表示
3. 「このタスクをBACKLOG.mdに追加してから作業を開始してください」と注入
"""
import json
import sys
import os
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
BACKLOG_FILE = PROJECT_DIR / "docs" / "BACKLOG.md"

# タスク指示を示すキーワード（日本語）
TASK_KEYWORDS = [
    r"して$", r"してくれ", r"しろ", r"しろよ",
    r"実装して", r"修正して", r"確認して", r"追加して",
    r"やって", r"やれ", r"やろう",
    r"作って", r"直して", r"調べて", r"見て",
    r"設定して", r"デプロイ", r"移行して",
    r"スクリプト", r"自動化",
]

# 除外パターン（質問・感謝・短い返事）
EXCLUDE_PATTERNS = [
    r"^(はい|いいえ|ok|OK|了解|ありがとう|なるほど|そうか|わかった)$",
    r"^\?",    # 質問のみ
    r"^どう",  # 「どうやって？」等
    r"^何",    # 「何が？」等
]


def count_pending(backlog_path: Path) -> int:
    """BACKLOG.mdの未完了タスク数を数える"""
    if not backlog_path.exists():
        return 0
    content = backlog_path.read_text(encoding="utf-8")
    return len(re.findall(r"^- \[ \]", content, re.MULTILINE))


def is_task_instruction(message: str) -> bool:
    """ユーザーメッセージがタスク指示かどうかを判定"""
    if len(message.strip()) < 5:
        return False

    # 除外パターンに一致したら False
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, message.strip(), re.IGNORECASE):
            return False

    # タスクキーワードに一致したら True
    for pat in TASK_KEYWORDS:
        if re.search(pat, message, re.IGNORECASE):
            return True

    return False


def main():
    try:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
    except Exception:
        sys.exit(0)

    message = data.get("prompt", "")
    if not message:
        sys.exit(0)

    if not is_task_instruction(message):
        sys.exit(0)

    # 未完了タスク数
    pending = count_pending(BACKLOG_FILE)

    # バックログリマインダーを注入
    print(
        f"\n📋 [BACKLOG-GUARD] 新しいタスク指示を検出\n"
        f"  現在の未完了バックログ: {pending}件\n"
        f"  ファイル: docs/BACKLOG.md\n\n"
        f"  ✅ 作業前に必ずやること:\n"
        f"  1. このタスクを BACKLOG.md の「未完了」に追加する\n"
        f"  2. 追加後に作業を開始する\n"
        f"  （完了したら [ ] を [x] に変える）\n"
    )
    sys.exit(0)  # ブロックせず、リマインドのみ


if __name__ == "__main__":
    main()
