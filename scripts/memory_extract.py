#!/usr/bin/env python3
"""
MEMORY EXTRACT v2 — セッション・タスク台帳・失敗メモリから実知識を抽出して保存
================================================================
session-end.py から呼ばれる。以下3つのソースから記憶を抽出する:
  1. session.json  — エラーパターン、リサーチ先行チェック
  2. task_ledger.json  — 完了タスクの root_cause / what_changed（実知識）
  3. failure_memory.json — 未解決 / 直近解決された失敗パターン（防止ルール）

使い方:
  python memory_extract.py /path/to/project
  python memory_extract.py /path/to/project --dry-run
  python memory_extract.py /path/to/project --import-mistakes
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from memory_system import MemorySystem


# ─────────────────────────────────────────────
# Source 1: session.json（セッション状態）
# ─────────────────────────────────────────────

def extract_from_session(project_dir: Path) -> list:
    """セッション状態ファイルから記憶を抽出"""
    state_file = project_dir / ".claude" / "hooks" / "state" / "session.json"
    memories = []

    if not state_file.exists():
        return memories

    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return memories

    errors = state.get("errors", [])
    search_count = state.get("search_count", 0)
    research_done = state.get("research_done", False)
    date_str = datetime.now().strftime("%Y-%m-%d")

    # 1a. エラーから学習事項を抽出
    for err in errors:
        tool = err.get("tool", "unknown")
        error_msg = err.get("error", "")
        if error_msg and len(error_msg) > 10:
            memories.append({
                "category": "error_pattern",
                "content": f"[{date_str}] ツール '{tool}' でエラー発生: {error_msg[:300]}",
                "metadata": {
                    "agent": "local-claude",
                    "importance": "high",
                    "source": "auto_extract",
                }
            })

    # 1b. リサーチなしで実装開始した場合の警告記録
    if state.get("started_without_research"):
        memories.append({
            "category": "behavior_pattern",
            "content": f"[{date_str}] リサーチなしで実装を開始した。次回は必ずWebSearch/WebFetchを先に行うこと。",
            "metadata": {
                "agent": "local-claude",
                "importance": "high",
                "source": "auto_extract",
            }
        })

    # 1c. セッションサマリー（search_count > 0 または errors > 0 の場合のみ記録）
    # 「検索0回, エラー0件」のゴミエントリを抑制する
    if search_count > 0 or errors:
        memories.append({
            "category": "session_summary",
            "content": (
                f"[{date_str}] セッションサマリー: "
                f"検索{search_count}回, エラー{len(errors)}件, "
                f"リサーチ先行={'yes' if research_done else 'no'}"
            ),
            "metadata": {
                "agent": "local-claude",
                "importance": "low",
                "source": "auto_extract",
            }
        })

    return memories


# ─────────────────────────────────────────────
# Source 2: task_ledger.json（タスク台帳）
# ─────────────────────────────────────────────

def extract_from_task_ledger(project_dir: Path) -> list:
    """task_ledger.json の直近完了タスクから実知識を抽出

    セッション終了時に呼ばれ、今セッションで完了したタスク（completed_at が今日）
    の root_cause / what_changed / memory_updates を記憶として保存する。
    """
    ledger_file = project_dir / ".claude" / "state" / "task_ledger.json"
    memories = []

    if not ledger_file.exists():
        return memories

    try:
        ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
    except Exception:
        return memories

    today = datetime.now().strftime("%Y-%m-%d")
    tasks = ledger.get("tasks", [])

    for task in tasks:
        status = task.get("status", "")
        # 今日完了したタスク、または直近 completed_at がある done タスク
        completed_at = task.get("completed_at", "") or ""
        if status != "done":
            continue
        # completed_at が今日のもの、またはフォールバックとして created_at が今日のもの
        created_at = task.get("created_at", "") or ""
        if not (completed_at.startswith(today) or created_at.startswith(today)):
            continue

        task_id = task.get("id", "?")
        title = task.get("title", "")
        resolution = task.get("resolution", task.get("completion_notes", {}))
        if not resolution:
            continue

        what_changed = resolution.get("what_changed", "")
        root_cause = resolution.get("root_cause", "")
        memory_updates = resolution.get("memory_updates", [])

        # root_cause が充実している場合は知識として保存
        if root_cause and len(root_cause) > 20:
            memories.append({
                "category": "task_lesson",
                "content": (
                    f"[{today}] タスク {task_id}: {title}\n"
                    f"根本原因: {root_cause[:400]}\n"
                    f"変更内容: {what_changed[:300]}"
                ),
                "metadata": {
                    "agent": "local-claude",
                    "importance": "high",
                    "source": "task_ledger",
                    "task_id": task_id,
                }
            })
        elif what_changed and len(what_changed) > 20:
            memories.append({
                "category": "task_lesson",
                "content": (
                    f"[{today}] タスク {task_id}: {title}\n"
                    f"変更内容: {what_changed[:400]}"
                ),
                "metadata": {
                    "agent": "local-claude",
                    "importance": "medium",
                    "source": "task_ledger",
                    "task_id": task_id,
                }
            })

        # memory_updates に実ファイルが記載されている場合も記録
        if memory_updates:
            memories.append({
                "category": "task_lesson",
                "content": (
                    f"[{today}] タスク {task_id} 記憶更新ファイル: "
                    f"{', '.join(str(m) for m in memory_updates[:5])}"
                ),
                "metadata": {
                    "agent": "local-claude",
                    "importance": "low",
                    "source": "task_ledger",
                    "task_id": task_id,
                }
            })

    return memories


# ─────────────────────────────────────────────
# Source 3: failure_memory.json（失敗メモリ）
# ─────────────────────────────────────────────

def extract_from_failure_memory(project_dir: Path) -> list:
    """failure_memory.json から未解決・直近解決された失敗の防止ルールを抽出

    - resolved_status == "open": 未解決 → critical として保存
    - resolved_status == "fixed" かつ prevention_rule が充実: 防止知識として保存
    - プレースホルダー("[未記入]" 等) は除外
    """
    fm_file = project_dir / ".claude" / "state" / "failure_memory.json"
    memories = []

    if not fm_file.exists():
        return memories

    try:
        fm = json.loads(fm_file.read_text(encoding="utf-8"))
    except Exception:
        return memories

    today = datetime.now().strftime("%Y-%m-%d")
    failures = fm.get("failures", [])

    for f in failures:
        fid = f.get("failure_id", "?")
        root_cause = f.get("root_cause", "")
        symptom = f.get("symptom", "")
        prevention_rule = f.get("prevention_rule", "")
        resolved_status = f.get("resolved_status", "open")
        severity = f.get("severity", "medium")

        # プレースホルダーチェック
        placeholder_markers = ["[自動記録]", "[未記入]", "手動で記入"]
        is_placeholder = any(m in root_cause for m in placeholder_markers)

        if resolved_status == "open" and not is_placeholder:
            # 未解決: critical として記録（次セッションで必ず認識させる）
            memories.append({
                "category": "open_failure",
                "content": (
                    f"[{today}] 未解決失敗 {fid} (severity={severity}): {symptom[:200]}\n"
                    f"根本原因: {root_cause[:300]}\n"
                    f"防止ルール: {prevention_rule[:200] if prevention_rule else '未記入'}"
                ),
                "metadata": {
                    "agent": "local-claude",
                    "importance": "critical",
                    "source": "failure_memory",
                    "failure_id": fid,
                    "resolved_status": resolved_status,
                }
            })
        elif resolved_status == "fixed" and prevention_rule:
            # プレースホルダーでない充実した防止ルール → 防止知識として保存
            is_pr_placeholder = any(m in prevention_rule for m in placeholder_markers)
            if not is_pr_placeholder and len(prevention_rule) > 20:
                memories.append({
                    "category": "prevention_rule",
                    "content": (
                        f"[{today}] 防止ルール {fid}: {prevention_rule[:400]}\n"
                        f"（症状: {symptom[:150]}）"
                    ),
                    "metadata": {
                        "agent": "local-claude",
                        "importance": "high",
                        "source": "failure_memory",
                        "failure_id": fid,
                        "resolved_status": resolved_status,
                    }
                })

    return memories


# ─────────────────────────────────────────────
# Source 4: KNOWN_MISTAKES.md（既知ミス、オプション）
# ─────────────────────────────────────────────

def extract_from_known_mistakes(project_dir: Path) -> list:
    """KNOWN_MISTAKES.mdから新しいエントリを抽出（--import-mistakes フラグで使用）"""
    km_file = project_dir / "docs" / "KNOWN_MISTAKES.md"
    memories = []

    if not km_file.exists():
        return memories

    try:
        content = km_file.read_text(encoding="utf-8")
    except Exception:
        return memories

    entries = content.split("### ")
    for entry in entries[1:]:
        lines = entry.strip().split("\n")
        title = lines[0].strip() if lines else ""
        body = "\n".join(lines[1:]).strip()

        if title and body:
            memories.append({
                "category": "known_mistake",
                "content": f"### {title}\n{body}",
                "metadata": {
                    "agent": "local-claude",
                    "importance": "critical",
                    "source": "known_mistakes",
                }
            })

    return memories


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract memories from session state and task data")
    parser.add_argument("project_dir", nargs="?", default=".",
                        help="Project directory path")
    parser.add_argument("--base-dir", default="/opt/shared/memory",
                        help="Memory storage base directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be stored without storing")
    parser.add_argument("--import-mistakes", action="store_true",
                        help="Import all entries from KNOWN_MISTAKES.md")
    parser.add_argument("--include-task-ledger", action="store_true",
                        help="Include knowledge from task_ledger.json (today's completed tasks)")
    parser.add_argument("--include-failure-memory", action="store_true",
                        help="Include prevention rules from failure_memory.json")

    args = parser.parse_args()
    project_dir = Path(args.project_dir)

    # Source 1: セッション状態
    memories = extract_from_session(project_dir)

    # Source 2: タスク台帳（フラグあり or session-end.py から呼ばれる場合）
    if args.include_task_ledger:
        memories.extend(extract_from_task_ledger(project_dir))

    # Source 3: 失敗メモリ（フラグあり or session-end.py から呼ばれる場合）
    if args.include_failure_memory:
        memories.extend(extract_from_failure_memory(project_dir))

    # Source 4: KNOWN_MISTAKES（オプション）
    if args.import_mistakes:
        memories.extend(extract_from_known_mistakes(project_dir))

    if not memories:
        print("抽出する記憶がありませんでした。")
        return

    if args.dry_run:
        print(f"=== Dry Run: {len(memories)}件の記憶を抽出 ===\n")
        for m in memories:
            print(f"[{m['category']}] {m['content'][:120]}")
            print()
        return

    # 保存
    mem = MemorySystem(args.base_dir)
    count = 0
    for m in memories:
        mem.store(m["category"], m["content"], m.get("metadata", {}))
        count += 1

    print(f"[OK] {count}件の記憶を保存しました。")
    stats = mem.get_stats()
    print(f"   Total memories: {stats['total_memories']}")


if __name__ == "__main__":
    main()
