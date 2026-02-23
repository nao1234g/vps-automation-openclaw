#!/usr/bin/env python3
"""
MEMORY EXTRACT — セッションの会話から重要な事実を自動抽出して保存
================================================================
session-end.py から呼ばれる。セッション状態ファイルを読み、
エラー・学習・決定事項を記憶システムに保存する。

使い方:
  python3 memory_extract.py /path/to/project
  python3 memory_extract.py /path/to/project --dry-run
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from memory_system import MemorySystem


def extract_from_session(project_dir: Path, dry_run: bool = False) -> list:
    """セッション状態から記憶を抽出"""
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

    # 1. エラーから学習事項を抽出
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

    # 2. リサーチなしで実装開始した場合の警告記録
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

    # 3. セッションサマリー（常に記録）
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


def extract_from_known_mistakes(project_dir: Path) -> list:
    """KNOWN_MISTAKES.mdから新しいエントリを抽出"""
    km_file = project_dir / "docs" / "KNOWN_MISTAKES.md"
    memories = []

    if not km_file.exists():
        return memories

    try:
        content = km_file.read_text(encoding="utf-8")
    except Exception:
        return memories

    # 各ミスエントリを抽出
    entries = content.split("### ")
    for entry in entries[1:]:  # 最初の空要素をスキップ
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


def main():
    parser = argparse.ArgumentParser(description="Extract memories from session state")
    parser.add_argument("project_dir", nargs="?", default=".",
                        help="Project directory path")
    parser.add_argument("--base-dir", default="/opt/shared/memory",
                        help="Memory storage base directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be stored without storing")
    parser.add_argument("--import-mistakes", action="store_true",
                        help="Import all entries from KNOWN_MISTAKES.md")

    args = parser.parse_args()
    project_dir = Path(args.project_dir)

    # セッション状態から抽出
    memories = extract_from_session(project_dir)

    # KNOWN_MISTAKES インポート
    if args.import_mistakes:
        memories.extend(extract_from_known_mistakes(project_dir))

    if not memories:
        print("抽出する記憶がありませんでした。")
        return

    if args.dry_run:
        print(f"=== Dry Run: {len(memories)}件の記憶を抽出 ===\n")
        for m in memories:
            print(f"[{m['category']}] {m['content'][:100]}...")
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
