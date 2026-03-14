"""
scripts/guard/pre_edit_task_guard.py
PreToolUse hook — Edit|Write の前にタスク台帳への登録を要求する

設計原則:
  「修正する前に、何を直すか必ず台帳へ記述する」
  タスクIDなしの編集はブロックする。Night Mode中はバイパス。

動作:
  1. .claude/hooks/state/night_mode.flag があればバイパス（exit 0）
  2. .claude/hooks/state/active_task_id.txt を読む
  3. IDが空/なければ exit 2（ブロック）
  4. .claude/state/task_ledger.json でIDを検証
  5. ステータスが in_progress でなければ警告（exit 0 — ソフトブロック）

Claude Codeの設定:
  settings.local.json の PreToolUse "Edit|Write" に追加する

終了コード:
  0 = 許可
  2 = ブロック（Claude Code がツール実行を中断する）
"""

import sys
import os
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── パス定義 ──────────────────────────────────────────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.environ.get(
    "CLAUDE_PROJECT_DIR",
    os.path.abspath(os.path.join(_HERE, "..", ".."))
)
_STATE_DIR = os.path.join(_PROJECT_ROOT, ".claude", "hooks", "state")
_LEDGER_PATH = os.path.join(_PROJECT_ROOT, ".claude", "state", "task_ledger.json")
_ACTIVE_ID_PATH = os.path.join(_STATE_DIR, "active_task_id.txt")
_NIGHT_MODE_PATH = os.path.join(_STATE_DIR, "night_mode.flag")

# ── バイパス条件 ──────────────────────────────────────────────────────

def _is_night_mode() -> bool:
    return os.path.exists(_NIGHT_MODE_PATH)

def _is_system_file(tool_input: dict) -> bool:
    """task_ledger.json 自体やフックの更新はブロックしない"""
    path = tool_input.get("file_path", "") or tool_input.get("path", "")
    bypass_patterns = [
        "task_ledger.json",
        "active_task_id.txt",
        ".claude/hooks/state/",
        ".claude/state/",
        "scripts/guard/pre_edit_task_guard.py",
        "settings.local.json",
    ]
    return any(pat in path for pat in bypass_patterns)

# ── タスク検証 ────────────────────────────────────────────────────────

def _read_active_id() -> str:
    if not os.path.exists(_ACTIVE_ID_PATH):
        return ""
    try:
        return open(_ACTIVE_ID_PATH, encoding="utf-8").read().strip()
    except Exception:
        return ""

def _find_task(task_id: str) -> dict:
    if not os.path.exists(_LEDGER_PATH):
        return {}
    try:
        data = json.load(open(_LEDGER_PATH, encoding="utf-8"))
        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                return t
    except Exception:
        pass
    return {}

# ── メイン ────────────────────────────────────────────────────────────

def main():
    # Night Mode — 自律運転中はブロックしない
    if _is_night_mode():
        sys.exit(0)

    # stdin から hook_data を読む（Claude Code が JSON で渡す）
    try:
        hook_data = json.load(sys.stdin)
    except Exception:
        hook_data = {}

    tool_input = hook_data.get("tool_input", {})

    # システムファイル自体の編集は許可
    if _is_system_file(tool_input):
        sys.exit(0)

    # active_task_id を確認
    task_id = _read_active_id()
    if not task_id:
        print(
            "[TASK GUARD] ❌ タスク未登録\n"
            "  Edit/Write の前に必ず台帳にタスクを登録してください。\n"
            "  1. .claude/state/task_ledger.json に新しいタスクを追加する\n"
            "  2. .claude/hooks/state/active_task_id.txt にそのIDを書く\n"
            "  例: echo -n 'T007' > .claude/hooks/state/active_task_id.txt",
            file=sys.stderr
        )
        sys.exit(2)

    # 台帳でIDを検証
    task = _find_task(task_id)
    if not task:
        print(
            f"[TASK GUARD] ❌ タスクID '{task_id}' が台帳に見つかりません\n"
            f"  .claude/state/task_ledger.json を確認してください。",
            file=sys.stderr
        )
        sys.exit(2)

    status = task.get("status", "")

    # archived/done のタスクで作業しようとしている場合は警告（ソフトブロック）
    if status in ("archived", "done"):
        print(
            f"[TASK GUARD] ⚠️ タスク '{task_id}' はすでに {status} です。\n"
            f"  タスク: {task.get('title', '')}\n"
            f"  新しい変更なら新タスクを台帳に追加し、active_task_id.txt を更新してください。",
            file=sys.stderr
        )
        # ソフトブロック: 警告のみで続行を許可
        sys.exit(0)

    # in_progress 以外（open/blocked）の場合も警告のみ
    if status not in ("in_progress",):
        print(
            f"[TASK GUARD] ℹ️ タスク '{task_id}' のステータスは '{status}' です。\n"
            f"  タスク: {task.get('title', '')}\n"
            f"  作業開始前に status を 'in_progress' に更新することを推奨します。",
            file=sys.stderr
        )

    # OK — タスクあり、作業続行
    sys.exit(0)


if __name__ == "__main__":
    main()
