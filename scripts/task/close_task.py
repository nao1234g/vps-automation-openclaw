"""
scripts/task/close_task.py
タスクを正式に閉じるCLIスクリプト

目的:
  task_ledger.json を直接 Python で編集してタスクを閉じる行為を防止する。
  completion_notes の検証を通過したタスクのみ "done" に移行できる。

使い方:
  python scripts/task/close_task.py T014
  python scripts/task/close_task.py T014 --dry-run
  python scripts/task/close_task.py T014 --notes-file /tmp/notes.json

--notes-file: JSON ファイルから completion_notes を読み込む
              指定しない場合は標準入力からJSON を読み込む
              (Windowsでは stdin を使うかファイル指定を推奨)

completion_notes フォーマット（dict 形式、推奨）:
  {
    "what_changed": "何を変えたか（技術的説明）",
    "root_cause":   "なぜ変更が必要だったか（根本原因）",
    "memory_updates": ["変更ファイル1", "変更ファイル2"],
    "tests_run":    "python scripts/doctor.py → 93/93 PASS",
    "remaining_risks": "残課題（なければ '無し'）"
  }

終了コード:
  0 = 成功
  1 = バリデーションエラー（タスク不在 / completion_notes 不足）
  2 = completion_notes にプレースホルダーが含まれる
"""

import sys
import os
import json
import argparse
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
_TASK_LEDGER_PATH = os.path.join(_PROJECT_ROOT, ".claude", "state", "task_ledger.json")
_ACTIVE_ID_PATH = os.path.join(_PROJECT_ROOT, ".claude", "hooks", "state", "active_task_id.txt")

# ── バリデーション定数 ─────────────────────────────────────────────────
_REQUIRED_DICT_KEYS = ["what_changed", "root_cause", "tests_run"]
_MIN_STRING_LEN = 50

# プレースホルダー文字列（これらが必須フィールドに含まれているとブロック）
_PLACEHOLDER_PATTERNS = [
    "[未記入]",
    "[自動記録]",
    "[未入力]",
    "[記入してください]",
    "TODO",
    "FIXME",
    "[要記入]",
]


# ── ユーティリティ ────────────────────────────────────────────────────

def _load_ledger() -> dict:
    if not os.path.exists(_TASK_LEDGER_PATH):
        return {"tasks": []}
    try:
        return json.load(open(_TASK_LEDGER_PATH, encoding="utf-8"))
    except Exception as e:
        print(f"[CLOSE TASK] ❌ task_ledger.json 読み込みエラー: {e}", file=sys.stderr)
        return {"tasks": []}


def _save_ledger(data: dict) -> bool:
    try:
        with open(_TASK_LEDGER_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[CLOSE TASK] ❌ task_ledger.json 書き込みエラー: {e}", file=sys.stderr)
        return False


def _read_active_id() -> str:
    if not os.path.exists(_ACTIVE_ID_PATH):
        return ""
    try:
        return open(_ACTIVE_ID_PATH, encoding="utf-8").read().strip()
    except Exception:
        return ""


def _clear_active_id():
    try:
        with open(_ACTIVE_ID_PATH, "w", encoding="utf-8") as f:
            f.write("")
    except Exception as e:
        print(f"[CLOSE TASK] ⚠️ active_task_id.txt クリア失敗: {e}", file=sys.stderr)


def _has_placeholder(value: str) -> bool:
    """値にプレースホルダーが含まれているか確認する"""
    val_lower = value.lower()
    for pat in _PLACEHOLDER_PATTERNS:
        if pat.lower() in val_lower:
            return True
    return False


# ── completion_notes バリデーション ────────────────────────────────────

def validate_completion_notes(notes) -> tuple:
    """
    completion_notes を検証する。
    Returns: (ok: bool, error_message: str)
      ok=True  → 問題なし
      ok=False → error_message にエラー内容
    """
    # 存在しない or None or 空
    if notes is None or notes == "" or notes == []:
        return False, "completion_notes が存在しません。必ず記入してください。"

    # dict 形式（推奨）
    if isinstance(notes, dict):
        # 必須キーの存在確認
        missing = [k for k in _REQUIRED_DICT_KEYS if not notes.get(k)]
        if missing:
            return False, f"必須キーが不足しています: {missing}"

        # プレースホルダーチェック
        for key in _REQUIRED_DICT_KEYS:
            val = notes.get(key, "")
            if isinstance(val, str) and _has_placeholder(val):
                return False, (
                    f"'{key}' にプレースホルダーが含まれています: {val[:80]}\n"
                    f"  実際の内容を記入してください。"
                )
            # 極端に短い値チェック
            if isinstance(val, str) and len(val.strip()) < 10:
                return False, (
                    f"'{key}' の値が短すぎます ({len(val.strip())} 文字)。"
                    f"具体的な内容を記入してください。"
                )

        # tests_run が空でないか確認
        tests_run = notes.get("tests_run", "")
        if isinstance(tests_run, str) and not tests_run.strip():
            return False, "'tests_run' が空です。実行した検証コマンドと結果を記入してください。"

        return True, ""

    # string 形式（後方互換）
    if isinstance(notes, str):
        stripped = notes.strip()
        if not stripped:
            return False, "completion_notes が空文字です"
        if _has_placeholder(stripped):
            return False, f"completion_notes にプレースホルダーが含まれています: {stripped[:80]}"
        if len(stripped) < _MIN_STRING_LEN:
            return False, (
                f"completion_notes が短すぎます ({len(stripped)} 文字 < {_MIN_STRING_LEN} 文字)。"
                f" dict 形式での記入を推奨します。"
            )
        return True, ""

    return False, f"completion_notes の型が想定外: {type(notes).__name__}（dict 推奨）"


# ── メイン ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="タスクを正式に閉じる（completion_notes 検証付き）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("task_id", help="閉じるタスクのID（例: T014）")
    parser.add_argument(
        "--notes-file",
        help="completion_notes を読み込む JSON ファイルパス",
        default=None
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際には変更せず、検証のみ実行する"
    )
    parser.add_argument(
        "--no-clear-active",
        action="store_true",
        help="active_task_id.txt をクリアしない"
    )
    args = parser.parse_args()

    task_id = args.task_id.strip()

    # ── タスク台帳を読み込む ──────────────────────────────────────────
    ledger = _load_ledger()
    tasks = ledger.get("tasks", [])
    task = None
    task_idx = None
    for i, t in enumerate(tasks):
        if t.get("id") == task_id:
            task = t
            task_idx = i
            break

    if task is None:
        print(f"[CLOSE TASK] ❌ タスクID '{task_id}' が台帳に見つかりません", file=sys.stderr)
        print(f"  利用可能なID: {[t.get('id') for t in tasks]}", file=sys.stderr)
        sys.exit(1)

    # すでに done/archived
    current_status = task.get("status", "")
    if current_status in ("done", "archived"):
        print(
            f"[CLOSE TASK] ⚠️ タスク '{task_id}' はすでに {current_status} です。"
            f" 操作をスキップします。",
            file=sys.stderr
        )
        sys.exit(0)

    # ── completion_notes の読み込み ────────────────────────────────────
    notes = task.get("completion_notes")

    if args.notes_file:
        try:
            notes = json.load(open(args.notes_file, encoding="utf-8"))
            print(f"[CLOSE TASK] ℹ️ completion_notes を '{args.notes_file}' から読み込みました")
        except Exception as e:
            print(f"[CLOSE TASK] ❌ notes_file 読み込みエラー: {e}", file=sys.stderr)
            sys.exit(1)
    elif notes is None:
        # stdin から読み込み（非対話モードの場合は失敗する）
        print("[CLOSE TASK] ℹ️ completion_notes をJSONとして stdin から読み込みます...")
        print("  (JSON入力後に Ctrl+Z [Windows] または Ctrl+D [Unix] で終了)")
        try:
            notes = json.load(sys.stdin)
            print(f"[CLOSE TASK] ℹ️ stdin から completion_notes を読み込みました")
        except Exception:
            print(
                "[CLOSE TASK] ❌ completion_notes の読み込みに失敗しました\n"
                "  --notes-file オプションを使ってJSONファイルを指定してください。\n"
                "  例: python scripts/task/close_task.py T014 --notes-file /tmp/notes.json",
                file=sys.stderr
            )
            sys.exit(1)

    # ── バリデーション ────────────────────────────────────────────────
    ok, error_msg = validate_completion_notes(notes)

    if not ok:
        print(
            f"\n⛔ CLOSE TASK — completion_notes が不十分です\n"
            f"  タスク: [{task_id}] {task.get('title', '')[:70]}\n"
            f"  エラー: {error_msg}\n\n"
            f"  推奨フォーマット（dict）:\n"
            f"  {{\n"
            f"    \"what_changed\": \"何を変えたか（技術的説明）\",\n"
            f"    \"root_cause\":   \"なぜ変更が必要だったか\",\n"
            f"    \"memory_updates\": [\"変更ファイルパス\"],\n"
            f"    \"tests_run\":    \"python scripts/doctor.py → 93/93 PASS\",\n"
            f"    \"remaining_risks\": \"残課題（なければ '無し'）\"\n"
            f"  }}\n",
            file=sys.stderr
        )
        sys.exit(1)

    # ── dry-run ───────────────────────────────────────────────────────
    if args.dry_run:
        print(
            f"[CLOSE TASK] ✅ DRY-RUN — バリデーション通過\n"
            f"  タスク: [{task_id}] {task.get('title', '')[:70]}\n"
            f"  completion_notes: OK\n"
            f"  （実際の変更は行いません）"
        )
        sys.exit(0)

    # ── タスクを done に更新 ──────────────────────────────────────────
    now_iso = datetime.now(timezone.utc).isoformat()
    tasks[task_idx]["status"] = "done"
    tasks[task_idx]["completed_at"] = now_iso
    tasks[task_idx]["completion_notes"] = notes
    ledger["tasks"] = tasks

    if not _save_ledger(ledger):
        sys.exit(1)

    # active_task_id をクリア
    active_id = _read_active_id()
    if not args.no_clear_active:
        if active_id == task_id:
            _clear_active_id()
            print(f"[CLOSE TASK] ✅ active_task_id.txt をクリアしました")
        else:
            print(
                f"[CLOSE TASK] ℹ️ active_task_id.txt は '{active_id}' です（'{task_id}' ではない）。"
                f" クリアしませんでした。"
            )

    print(
        f"[CLOSE TASK] ✅ タスク '{task_id}' を done に移行しました\n"
        f"  タイトル: {task.get('title', '')[:70]}\n"
        f"  完了時刻: {now_iso}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
