"""
scripts/guard/failure_capture.py
PostToolUseFailure hook — ツール失敗を failure_memory.json に自動記録する

動作:
  1. stdin から Claude Code が渡す hook_data を読む
     {tool_name, tool_input, error}
  2. .claude/hooks/state/active_task_id.txt から現在のタスクIDを取得
  3. .claude/state/failure_memory.json に新しい failure エントリを追記
     (failure_id は F{3桁連番}, resolved_status="open")
  4. exit 0 — 常に成功（失敗記録がツール実行を再ブロックしないように）

使い方:
  settings.local.json の PostToolUseFailure に登録する:
  {
    "type": "command",
    "command": "python \"$CLAUDE_PROJECT_DIR/scripts/guard/failure_capture.py\"",
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
_FAILURE_MEMORY_PATH = os.path.join(_PROJECT_ROOT, ".claude", "state", "failure_memory.json")
_CONSTITUTION_CANDIDATES_PATH = os.path.join(_PROJECT_ROOT, ".claude", "state", "constitution_candidates.json")
_ACTIVE_ID_PATH = os.path.join(_STATE_DIR, "active_task_id.txt")

# constitution_candidates 昇格条件
_ESCALATION_RECURRENCE_THRESHOLD = 3
_ESCALATION_SEVERITIES = {"critical", "high"}
_ESCALATION_STATUSES = {"open", "regressed"}

# ── ユーティリティ ────────────────────────────────────────────────────

def _read_active_id() -> str:
    if not os.path.exists(_ACTIVE_ID_PATH):
        return ""
    try:
        return open(_ACTIVE_ID_PATH, encoding="utf-8").read().strip()
    except Exception:
        return ""

def _load_failure_memory() -> dict:
    if not os.path.exists(_FAILURE_MEMORY_PATH):
        return {
            "_schema_version": "1.0",
            "_description": "AI Civilization OS 失敗メモリ",
            "failures": []
        }
    try:
        return json.load(open(_FAILURE_MEMORY_PATH, encoding="utf-8"))
    except Exception:
        return {"_schema_version": "1.0", "failures": []}

def _load_constitution_candidates() -> dict:
    if not os.path.exists(_CONSTITUTION_CANDIDATES_PATH):
        return {
            "_schema_version": "1.0",
            "_description": "failure_memory.json から自動昇格された constitution 候補",
            "candidates": []
        }
    try:
        return json.load(open(_CONSTITUTION_CANDIDATES_PATH, encoding="utf-8"))
    except Exception:
        return {"_schema_version": "1.0", "candidates": []}


def _escalate_to_constitution(failure: dict):
    """recurrence >= 3 かつ severity high/critical の失敗を constitution_candidates に昇格する"""
    doc = _load_constitution_candidates()
    candidates = doc.get("candidates", [])

    # 重複チェック（同一 failure_id はスキップ）
    existing_ids = {c.get("source_failure_id") for c in candidates}
    fid = failure.get("failure_id", "")
    if fid in existing_ids:
        return  # すでに昇格済み

    now_iso = datetime.now(timezone.utc).isoformat()
    candidate = {
        "candidate_id": f"CC{len(candidates) + 1:03d}",
        "source_failure_id": fid,
        "title": f"[自動昇格] {failure.get('category', 'unknown')} — {failure.get('symptom', '')[:80]}",
        "severity": failure.get("severity", ""),
        "recurrence_count": failure.get("recurrence_count", 0),
        "resolved_status": failure.get("resolved_status", ""),
        "escalated_at": now_iso,
        "status": "open",
        "proposed_rule": f"[未記入] failure_id={fid} の根本原因に基づきルールを追記する",
        "naoto_approval": "pending"
    }
    candidates.append(candidate)
    doc["candidates"] = candidates

    os.makedirs(os.path.dirname(_CONSTITUTION_CANDIDATES_PATH), exist_ok=True)
    try:
        with open(_CONSTITUTION_CANDIDATES_PATH, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print(
            f"[FAILURE CAPTURE] 🔺 Constitution昇格: {candidate['candidate_id']} "
            f"← {fid} (recurrence={failure.get('recurrence_count')}, "
            f"severity={failure.get('severity')})",
            file=sys.stderr
        )
    except Exception as e:
        print(f"[FAILURE CAPTURE] constitution_candidates 保存エラー: {e}", file=sys.stderr)


def _check_and_escalate(failure: dict):
    """昇格条件を満たすか判定して constitution_candidates に追加する"""
    if (failure.get("recurrence_count", 0) >= _ESCALATION_RECURRENCE_THRESHOLD
            and failure.get("severity", "") in _ESCALATION_SEVERITIES
            and failure.get("resolved_status", "") in _ESCALATION_STATUSES):
        _escalate_to_constitution(failure)


def _next_failure_id(failures: list) -> str:
    """既存の最大IDの次のIDを生成する"""
    max_num = 0
    for f in failures:
        fid = f.get("failure_id", "F000")
        try:
            num = int(fid[1:])
            max_num = max(max_num, num)
        except ValueError:
            pass
    return f"F{max_num + 1:03d}"

def _categorize_error(tool_name: str, error: str) -> str:
    """エラーメッセージからカテゴリを推定する"""
    error_lower = error.lower()
    if "attributeerror" in error_lower or "no attribute" in error_lower:
        return "api_mismatch"
    if "typeerror" in error_lower and "argument" in error_lower:
        return "api_mismatch"
    if "filenotfounderror" in error_lower or "no such file" in error_lower:
        return "path_mismatch"
    if "permissionerror" in error_lower:
        return "config_error"
    if "connectionerror" in error_lower or "timeout" in error_lower:
        return "integration_error"
    if "keyerror" in error_lower or "indexerror" in error_lower:
        return "logic_error"
    return "runtime_error"

# ── メイン ────────────────────────────────────────────────────────────

def main():
    # stdin からフックデータを読む
    try:
        hook_data = json.load(sys.stdin)
    except Exception:
        hook_data = {}

    tool_name = hook_data.get("tool_name", "unknown")
    tool_input = hook_data.get("tool_input", {})
    error = hook_data.get("error", "unknown error")

    # エラーが空 or 軽微な場合はスキップ
    if not error or error == "unknown error":
        sys.exit(0)

    # 現在のタスクIDを取得
    task_id = _read_active_id()

    # 失敗メモリを読み込む
    memory = _load_failure_memory()
    failures = memory.get("failures", [])

    # 同じ症状がすでに記録されているか確認（recurrence_count をインクリメント）
    now_iso = datetime.now(timezone.utc).isoformat()
    error_short = str(error)[:200]

    for existing in failures:
        if existing.get("symptom", "")[:50] == error_short[:50]:
            existing["recurrence_count"] = existing.get("recurrence_count", 0) + 1
            existing["last_seen"] = now_iso
            if existing.get("resolved_status") == "fixed":
                existing["resolved_status"] = "regressed"
                print(f"[FAILURE CAPTURE] ⚠️ 再発検知: {existing['failure_id']} — {error_short[:80]}", file=sys.stderr)
            _save_memory(memory)
            # 昇格条件チェック（recurrence更新後に評価）
            _check_and_escalate(existing)
            sys.exit(0)

    # 新規エントリを追加
    failure_id = _next_failure_id(failures)
    category = _categorize_error(tool_name, error)

    # affected_files を tool_input から推定
    affected_files = []
    if "file_path" in tool_input:
        affected_files.append(tool_input["file_path"])
    if "command" in tool_input:
        cmd = str(tool_input["command"])
        if ".py" in cmd:
            for part in cmd.split():
                if part.endswith(".py"):
                    affected_files.append(part)

    new_failure = {
        "failure_id": failure_id,
        "category": category,
        "root_cause": f"[自動記録] {tool_name} ツールが失敗 — 詳細は手動で記入してください",
        "symptom": error_short,
        "trigger": f"{tool_name} ツールの実行中 (task: {task_id or 'なし'})",
        "affected_files": affected_files,
        "prevention_rule": "[未記入 — 根本原因を調査後に追記]",
        "required_test": "[未記入 — 防止テストを追加]",
        "first_seen": now_iso,
        "last_seen": now_iso,
        "recurrence_count": 0,
        "severity": "medium",
        "resolved_status": "open",
        "related_task_id": task_id
    }

    failures.append(new_failure)
    memory["failures"] = failures

    _save_memory(memory)
    print(f"[FAILURE CAPTURE] 記録: {failure_id} — {error_short[:80]}", file=sys.stderr)

    sys.exit(0)  # 常に exit 0 — 記録失敗でClaude Codeを止めない


def _save_memory(memory: dict):
    os.makedirs(os.path.dirname(_FAILURE_MEMORY_PATH), exist_ok=True)
    try:
        with open(_FAILURE_MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[FAILURE CAPTURE] 保存エラー: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
