"""
scripts/guard/task_close_memory_check.py
PostToolUse(Edit|Write) フック — タスク完了時の completion_notes 強制

動作:
  1. task_ledger.json を読む
  2. 以下を全て満たすタスクを探す:
       - status == "done"
       - created_at >= "2026-03-15"（新規タスクのみ。T001-T010 はグランドファーザー）
       - completion_notes が存在しない or 空文字 or 必須スキーマ不足
  3. 該当タスクがあれば exit 2（PostToolUse ブロック）
  4. 該当タスクがなければ exit 0（サイレント）

completion_notes スキーマ検証（2026-03-15 T013追加）:
  completion_notes が dict の場合: 以下の3キーが必須
    - what_changed  : 何を変えたか（技術的説明）
    - root_cause    : なぜ変更が必要だったか（根本原因）
    - tests_run     : 検証コマンドと結果
  completion_notes が string の場合: 50文字以上が必要（WARN のみ、exit 0）

目的:
  「記録なしでタスクが閉じる」問題を根絶する。
  「記録がある」だけでなく「意味のある記録が正しい形で存在する」を強制する。

使い方（settings.local.json PostToolUse Edit|Write）:
  python "$CLAUDE_PROJECT_DIR/scripts/guard/task_close_memory_check.py"

終了コード:
  0 = 問題なし（警告のみのケースも 0）
  2 = completion_notes なし or 必須キー欠如で done になっているタスクがある（ブロック）

Geneen原則: 「数字は言語。タスクが完了したなら、何が変わったかを数字と言葉で記録せよ」
T013原則:   「記録がある ≠ 意味ある記録が正しい層に存在する」
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


# completion_notes のスキーマ検証に必要な3キー（T013: Obj3）
_REQUIRED_DICT_KEYS = ["what_changed", "root_cause", "tests_run"]
# string 形式の場合の最小文字数
_MIN_STRING_LEN = 50

# プレースホルダー文字列（T014: Obj5 — これらが必須フィールドにあるとブロック）
_PLACEHOLDER_PATTERNS = [
    "[未記入]",
    "[自動記録]",
    "[未入力]",
    "[記入してください]",
    "TODO",
    "FIXME",
    "[要記入]",
]


def _has_placeholder(value: str) -> bool:
    """値にプレースホルダーが含まれているか確認する"""
    val_lower = value.lower()
    for pat in _PLACEHOLDER_PATTERNS:
        if pat.lower() in val_lower:
            return True
    return False


def _validate_completion_notes(task: dict) -> tuple:
    """
    completion_notes を検証する。
    Returns: (ok: bool, warn: bool, reason: str)
      ok=True, warn=False → 問題なし
      ok=False, warn=False → ブロック（exit 2）
      ok=True,  warn=True  → 警告のみ（exit 0 で続行）

    T014 Obj5 追加:
      - プレースホルダー文字列を含む必須フィールド → ブロック
      - memory_updates キーの欠如 → 警告
    """
    notes = task.get("completion_notes")

    # 存在しない or None
    if notes is None or notes == "" or notes == []:
        return False, False, "completion_notes が存在しません"

    # dict 形式: 必須キーを検証
    if isinstance(notes, dict):
        # 必須キーの存在確認
        missing = [k for k in _REQUIRED_DICT_KEYS if not notes.get(k)]
        if missing:
            return False, False, f"completion_notes dict に必須キーが不足: {missing}"

        # プレースホルダーチェック（T014 Obj5）
        for key in _REQUIRED_DICT_KEYS:
            val = notes.get(key, "")
            if isinstance(val, str) and _has_placeholder(val):
                return False, False, (
                    f"'{key}' にプレースホルダーが含まれています: '{val[:80]}'\n"
                    f"  実際の内容を記入してください。"
                )

        # memory_updates キーの確認（T014 Obj5 — WARN のみ）
        if "memory_updates" not in notes:
            return True, True, (
                "completion_notes dict に 'memory_updates' キーがありません。"
                " 変更ファイル一覧を追加することを推奨します。"
            )

        return True, False, ""

    # string 形式: 最小長チェック（WARN のみ）
    if isinstance(notes, str):
        stripped = notes.strip()
        if not stripped:
            return False, False, "completion_notes が空文字です"
        # プレースホルダーチェック（T014 Obj5）
        if _has_placeholder(stripped):
            return False, False, (
                f"completion_notes にプレースホルダーが含まれています: '{stripped[:80]}'"
            )
        if len(stripped) < _MIN_STRING_LEN:
            return True, True, (
                f"completion_notes が短すぎます ({len(stripped)} 文字 < {_MIN_STRING_LEN} 文字)。"
                f"dict 形式（what_changed/root_cause/tests_run）への移行を推奨します。"
            )
        return True, False, ""

    # list や他の型: 警告のみ
    return True, True, f"completion_notes の型が想定外: {type(notes).__name__}（dict 推奨）"


def main():
    # night_mode.flag があれば即スキップ
    if _is_night_mode():
        sys.exit(0)

    tasks = _load_tasks()
    if not tasks:
        sys.exit(0)

    blockers = []   # exit 2 対象
    warnings = []   # WARN のみ

    for t in tasks:
        if t.get("status") != "done":
            continue
        if not _is_new_task(t):
            continue
        ok, warn, reason = _validate_completion_notes(t)
        if not ok:
            blockers.append((t, reason))
        elif warn:
            warnings.append((t, reason))

    # 警告を先に出す（続行可能）
    if warnings:
        for t, reason in warnings:
            tid = t.get("id", "?")
            title = t.get("title", "")[:60]
            print(
                f"[TASK CLOSE] ⚠️ WARN [{tid}] {title}\n"
                f"  {reason}",
                file=sys.stderr
            )

    if not blockers:
        sys.exit(0)

    # ブロック: completion_notes なし or 必須キー欠如
    print(
        f"\n⛔ TASK CLOSE MEMORY CHECK — completion_notes が不十分な done タスクがあります\n"
        f"  タスクを 'done' にする前に completion_notes を正しい形式で記入してください。\n"
        f"  推奨フォーマット（dict）:\n"
        f"    \"completion_notes\": {{\n"
        f"      \"what_changed\": \"何を変えたか\",\n"
        f"      \"root_cause\": \"なぜ変更が必要だったか\",\n"
        f"      \"memory_updates\": [\"変更ファイル一覧\"],\n"
        f"      \"tests_run\": \"python scripts/doctor.py → X/X PASS\",\n"
        f"      \"remaining_risks\": \"残課題\"\n"
        f"    }}\n",
        file=sys.stderr
    )
    for t, reason in blockers:
        tid = t.get("id", "?")
        title = t.get("title", "")[:60]
        print(f"  [{tid}] {title}", file=sys.stderr)
        print(f"       理由: {reason}", file=sys.stderr)
    print(file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
