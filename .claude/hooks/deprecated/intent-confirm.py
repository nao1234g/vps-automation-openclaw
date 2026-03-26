#!/usr/bin/env python3
"""
INTENT CONFIRM — PreToolUse Hook
==================================
ユーザーの指示 → Claudeが「こういう理解でいいですか？」と確認 → ユーザーOK → 実装

動作:
1. Edit/Write ツールの前に実行
2. intent_needs_confirmation.flag が存在 かつ intent_confirmed.flag が存在しない → exit 2 でブロック
3. feedback-trap.py がユーザーの承認を検知 → intent_confirmed.flag を作成 → ブロック解除

フラグ管理 (feedback-trap.py と連携):
  intent_needs_confirmation.flag → 新しい指示が来たときに作成（feedback-trap.py）
  intent_confirmed.flag          → ユーザーが承認したときに作成（feedback-trap.py）
"""
import json
import sys
import os
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
INTENT_CONFIRMED_FLAG = STATE_DIR / "intent_confirmed.flag"
INTENT_NEEDS_CONFIRMATION_FLAG = STATE_DIR / "intent_needs_confirmation.flag"

# ── stdin を読む ─────────────────────────────────────────────────────────
try:
    raw = sys.stdin.read().strip()
    data = json.loads(raw) if raw else {}
except Exception:
    sys.exit(0)

tool_name = data.get("tool_name", "")

# Edit / Write のみ対象（Read, Bash, WebSearch は対象外）
if tool_name not in ("Edit", "Write"):
    sys.exit(0)

# ── フラグチェック ───────────────────────────────────────────────────────
needs_confirmation = INTENT_NEEDS_CONFIRMATION_FLAG.exists()
is_confirmed = INTENT_CONFIRMED_FLAG.exists()

if needs_confirmation and not is_confirmed:
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", tool_input.get("path", "（不明）"))

    print(
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚫 [意図確認ゲート] 実装の前に理解を確認してください\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  対象ファイル: {file_path}\n"
        "\n"
        "  ユーザーから新しい指示を受けましたが、まだ確認が取れていません。\n"
        "\n"
        "  ✅ 次にすること:\n"
        "     1. 「こういう理解でいいですか？」と理解を確認する\n"
        "     2. ユーザーが承認したら intent_confirmed.flag が作成される\n"
        "     3. その後に Edit/Write を実行できる\n"
        "\n"
        "  このブロックは feedback-trap.py が承認を検知すると自動解除されます。\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    sys.exit(2)

sys.exit(0)
