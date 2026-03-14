"""
scripts/guard/task_close_memory_check.py
PostToolUse(Edit|Write) フック — タスク完了時の completion_notes 強制

動作:
  1. task_ledger.json を読む
  2. 以下を全て満たすタスクを探す:
       - status == "done"
       - created_at >= "2026-03-15"（新規タスクのみ。T001-T010 はグランドファーザー）
       - completion_notes が存在しない or 空文字
  3. 該当タスクがあれば exit 2（PostToolUse ブロック）
  4. 該当タスクがなければ exit 0（サイレント）

目的:
  「記録なしでタスクが閉じる」問題を根絶する。
  タスクを done にするなら何を学んだか必ず書け。

使い方（settings.local.json PostToolUse Edit|Write）:
  python "$CLAUDE_PROJECT_DIR/scripts/guard/task_close_memory_check.py"

終了コード:
  0 = 問題なし
  2 = completion_notes なしで done になっているタスクがある（ブロック）

Geneen原則: 「数字は言語。タスクが完了したなら、何が変わったかを数字と言葉で記録せよ」
"""

import sys
import os
import json
from datetime import datetime

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
_TASK_LEDGER_PATH = os.path.join(
    _PROJECT_ROOT, ".claude", "state", "task_ledger.json"
)
_NIGHT_MODE_FLAG = os.path.join(
    _PROJECT_ROOT, ".claude", "hooks", "state", "night_mode.flag"
)

# 2026-03-15 以降に作成されたタスクのみチェック（T001-T010 グランドファーザー）
_CUTOFF_DATE = "2026-03-15"


def _is_night_mode() -> bool:
    return os.path.exists(_NIGHT_MODE_FLAG)


def _load_tasks() -> list:
    if not os.path.exists(_TASK_LEDGER_PATH):
        return []
    try:
        data = json.load(open(_TASK_LEDGER_PATH, encoding="utf-8"))
        return data.get("tasks", [])
    except Exception:
        return []


def _is_new_task(task: dict) -> bool:
    """created_at >= _CUTOFF_DATE かどうか判定"""
    created = task.get("created_at", "")
    if not created:
        return False
    # ISO 8601 の先頭 10 文字（YYYY-MM-DD）で比較
    return created[:10] >= _CUTOFF_DATE


def _has_completion_notes(task: dict) -> bool:
    notes = task.get("completion_notes", "")
    return bool(notes and notes.strip())


def main():
    # night_mode.flag があれば即スキップ
    if _is_night_mode():
        sys.exit(0)

    tasks = _load_tasks()
    if not tasks:
        sys.exit(0)

    # done かつ新規タスク（>= cutoff）かつ completion_notes なし を抽出
    offenders = [
        t for t in tasks
        if t.get("status") == "done"
        and _is_new_task(t)
        and not _has_completion_notes(t)
    ]

    if not offenders:
        sys.exit(0)

    # ブロック: completion_notes がないタスクを報告
    print(
        f"\n⛔ TASK CLOSE MEMORY CHECK — completion_notes なしで done になっています\n"
        f"  タスクを 'done' にする前に completion_notes フィールドを必ず記入してください。\n"
        f"  何を学んだか、何が変わったかを記録することがこのOSの核心です。\n"
    )
    for t in offenders:
        tid = t.get("id", "?")
        title = t.get("title", "")[:60]
        print(f"  [{tid}] {title}")
    print(
        f"\n  修正方法: task_ledger.json の該当タスクに completion_notes を追加してください。\n"
        f"  例: \"completion_notes\": \"XXXを修正。根本原因はYYY。回帰テストZZZ/ZZZ PASS。\"\n"
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
