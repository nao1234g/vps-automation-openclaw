"""
scripts/guard/post_edit_task_reconcile.py
PostToolUse hook — Edit|Write 後にタスク台帳との整合を取る

動作:
  1. stdin から Claude Code が渡す hook_data を読む
     {tool_name, tool_input, tool_response}
  2. .claude/hooks/state/active_task_id.txt から現在のタスクIDを取得
  3. 編集ファイルが task_ledger.json の target_files に含まれているか確認
  4. タスクの status が "open" なら "in_progress" に自動更新
  5. タスクの target_files に含まれていない場合は警告をログに記録
  6. exit 0 — 常に成功（整合チェックが作業を止めないように）

設計原則:
  「完了後に報告できるか？（Accountability Test）」
  編集が台帳に紐付かないことを可視化し、未追跡の作業を明らかにする。

Claude Code設定:
  settings.local.json の PostToolUse "Edit|Write" に追加:
  {
    "type": "command",
    "command": "python \"$CLAUDE_PROJECT_DIR/scripts/guard/post_edit_task_reconcile.py\"",
    "timeout": 5
  }
"""

import sys
import os
import json
from datetime import datetime, timezone

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
_RECONCILE_LOG_PATH = os.path.join(_STATE_DIR, "reconcile.log")

# システムファイル（台帳登録不要）
_SYSTEM_PATTERNS = [
    "task_ledger.json",
    "active_task_id.txt",
    ".claude/hooks/state/",
    ".claude/state/",
    ".claude/rules/",
    "settings.local.json",
    "CLAUDE.md",
    "MEMORY.md",
    "KNOWN_MISTAKES.md",
    "failure_memory.json",
    "BACKLOG.md",
]


# ── ユーティリティ ────────────────────────────────────────────────────

def _read_active_id() -> str:
    if not os.path.exists(_ACTIVE_ID_PATH):
        return ""
    try:
        return open(_ACTIVE_ID_PATH, encoding="utf-8").read().strip()
    except Exception:
        return ""


def _load_ledger() -> dict:
    if not os.path.exists(_LEDGER_PATH):
        return {"tasks": []}
    try:
        return json.load(open(_LEDGER_PATH, encoding="utf-8"))
    except Exception:
        return {"tasks": []}


def _save_ledger(ledger: dict):
    try:
        with open(_LEDGER_PATH, "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[RECONCILE] 台帳保存エラー: {e}", file=sys.stderr)


def _find_task(ledger: dict, task_id: str) -> dict:
    for t in ledger.get("tasks", []):
        if t.get("id") == task_id:
            return t
    return {}


def _is_system_file(file_path: str) -> bool:
    """システムファイル自体の編集は整合チェック不要"""
    for pat in _SYSTEM_PATTERNS:
        if pat in file_path:
            return True
    return False


def _normalize_path(path: str) -> str:
    """パスを正規化して比較しやすくする"""
    # バックスラッシュをスラッシュに統一
    return path.replace("\\", "/").replace(_PROJECT_ROOT.replace("\\", "/") + "/", "")


def _log_reconcile(message: str):
    """整合ログに追記する"""
    try:
        os.makedirs(os.path.dirname(_RECONCILE_LOG_PATH), exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        with open(_RECONCILE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} {message}\n")
        # ログが大きくなりすぎたらローテーション（500行上限）
        with open(_RECONCILE_LOG_PATH, encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 500:
            with open(_RECONCILE_LOG_PATH, "w", encoding="utf-8") as f:
                f.writelines(lines[-400:])
    except Exception:
        pass


# ── メイン ────────────────────────────────────────────────────────────

def main():
    # stdin からフックデータを読む
    try:
        hook_data = json.load(sys.stdin)
    except Exception:
        hook_data = {}

    tool_name = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})

    # Edit/Write 以外は処理しない
    if tool_name not in ("Edit", "Write"):
        sys.exit(0)

    # 編集されたファイルパスを取得
    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
    if not file_path:
        sys.exit(0)

    # システムファイル自体はスキップ
    if _is_system_file(file_path):
        sys.exit(0)

    # アクティブタスクIDを確認
    task_id = _read_active_id()
    if not task_id:
        # タスクなしの編集 — pre_edit_task_guard.py がブロックするはず
        # ここでは警告ログのみ
        _log_reconcile(f"WARN no_task_id file={_normalize_path(file_path)}")
        sys.exit(0)

    # 台帳を読む
    ledger = _load_ledger()
    task = _find_task(ledger, task_id)

    if not task:
        _log_reconcile(f"WARN task_not_found task_id={task_id} file={_normalize_path(file_path)}")
        sys.exit(0)

    # ── タスクステータスを open → in_progress に自動更新 ──────────────
    updated = False
    if task.get("status") == "open":
        task["status"] = "in_progress"
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_ledger(ledger)
        updated = True
        print(f"[RECONCILE] ✅ タスク {task_id} を in_progress に更新", file=sys.stderr)
        _log_reconcile(f"INFO auto_progress task_id={task_id}")

    # ── target_files との整合チェック ────────────────────────────────
    normalized_edited = _normalize_path(file_path)
    target_files = task.get("target_files", [])
    normalized_targets = [_normalize_path(t) for t in target_files]

    # ファイル名のみでも一致を許す（パスが違っても同名ファイルは警告しない）
    edited_basename = os.path.basename(normalized_edited)
    target_basenames = [os.path.basename(t) for t in normalized_targets]

    in_targets = (
        normalized_edited in normalized_targets
        or any(normalized_edited.endswith(t) for t in normalized_targets)
        or edited_basename in target_basenames
    )

    if not in_targets and target_files:
        # 台帳に登録されていないファイルを編集している
        print(
            f"[RECONCILE] ℹ️ タスク {task_id} の target_files 外のファイルを編集:\n"
            f"  ファイル: {normalized_edited}\n"
            f"  登録済みターゲット: {', '.join(target_files[:3])}...\n"
            f"  必要なら task_ledger.json の target_files に追加してください。",
            file=sys.stderr
        )
        _log_reconcile(
            f"WARN off_target task_id={task_id} file={normalized_edited}"
        )
    else:
        _log_reconcile(
            f"INFO ok task_id={task_id} file={normalized_edited} status={task.get('status')}"
        )

    sys.exit(0)  # 常に exit 0 — 整合チェックが作業を止めない


if __name__ == "__main__":
    main()
