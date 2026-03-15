"""
scripts/guard/task_state_integrity_check.py
PostToolUse(Edit|Write) フック — active_task_id.txt の整合性強制

動作:
  1. active_task_id.txt を読む
  2. task_ledger.json を読む
  3. active_task_id が指しているタスクの status を確認する
  4. status が "done" または "archived" の場合 → exit 2（ブロック）
  5. active_task_id が空または存在しないタスクを指している場合 → exit 1（WARN）
  6. 正常の場合 → exit 0

目的:
  完了済み（done/archived）タスクが active_task_id に残留している場合、
  次のタスク作業の完了記録が誤ったタスクに紐付く危険がある。
  これを「次の Edit/Write 前に」物理的にブロックする。

ブロックメッセージ:
  active_task_id.txt の中身を正しいタスクID（in_progress のもの）に更新するか、
  空にしてから作業を再開してください。

  更新コマンド例:
    echo T014 > .claude/hooks/state/active_task_id.txt
    echo "" > .claude/hooks/state/active_task_id.txt

使い方（settings.local.json PostToolUse Edit|Write に追加）:
  python "$CLAUDE_PROJECT_DIR/scripts/guard/task_state_integrity_check.py"

終了コード:
  0 = 問題なし
  1 = active_task_id が空、またはタスクが台帳に見つからない（WARN — ブロックしない）
  2 = active_task_id が done/archived タスクを指している（BLOCK）
"""

import sys
import os
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── パス定義 ──────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.environ.get(
    "CLAUDE_PROJECT_DIR",
    os.path.abspath(os.path.join(_HERE, "..", ".."))
)
_ACTIVE_ID_PATH = os.path.join(
    _PROJECT_ROOT, ".claude", "hooks", "state", "active_task_id.txt"
)
_TASK_LEDGER_PATH = os.path.join(
    _PROJECT_ROOT, ".claude", "state", "task_ledger.json"
)
_NIGHT_MODE_FLAG = os.path.join(
    _PROJECT_ROOT, ".claude", "hooks", "state", "night_mode.flag"
)

# ブロック対象のステータス
_TERMINAL_STATUSES = {"done", "archived"}


def _is_night_mode() -> bool:
    return os.path.exists(_NIGHT_MODE_FLAG)


def _read_active_id() -> str:
    if not os.path.exists(_ACTIVE_ID_PATH):
        return ""
    try:
        return open(_ACTIVE_ID_PATH, encoding="utf-8").read().strip()
    except Exception:
        return ""


def _load_tasks() -> list:
    if not os.path.exists(_TASK_LEDGER_PATH):
        return []
    try:
        data = json.load(open(_TASK_LEDGER_PATH, encoding="utf-8"))
        return data.get("tasks", [])
    except Exception:
        return []


def main():
    # night_mode 中はスキップ
    if _is_night_mode():
        sys.exit(0)

    active_id = _read_active_id()

    # active_task_id が空 → WARN のみ（未設定は許容する）
    if not active_id:
        print(
            "[TASK INTEGRITY] ℹ️ active_task_id.txt が空です（タスク未設定）。"
            "作業前に echo <TaskID> > .claude/hooks/state/active_task_id.txt を実行してください。",
            file=sys.stderr
        )
        sys.exit(1)

    tasks = _load_tasks()
    task_map = {t.get("id"): t for t in tasks}

    task = task_map.get(active_id)

    # 台帳に存在しないIDを指している → WARN
    if task is None:
        print(
            f"[TASK INTEGRITY] ⚠️ WARN active_task_id='{active_id}' は台帳に存在しません。"
            f"正しいタスクIDに更新してください。",
            file=sys.stderr
        )
        sys.exit(1)

    status = task.get("status", "")

    # done/archived を指している → BLOCK
    if status in _TERMINAL_STATUSES:
        print(
            f"\n⛔ TASK STATE INTEGRITY — active_task_id が完了済みタスクを指しています\n"
            f"  タスク: [{active_id}] {task.get('title', '')[:70]}\n"
            f"  ステータス: {status}\n\n"
            f"  修正方法:\n"
            f"    1. 次のタスクIDを active_task_id.txt に設定する:\n"
            f"       echo T0XX > .claude/hooks/state/active_task_id.txt\n"
            f"    2. またはタスクなしで作業する場合は空にする:\n"
            f"       echo. > .claude/hooks/state/active_task_id.txt\n",
            file=sys.stderr
        )
        sys.exit(2)

    # in_progress / pending → 正常
    sys.exit(0)


if __name__ == "__main__":
    main()
