#!/usr/bin/env python3
"""
MEMORY STORE CLI — 記憶を長期記憶システムに保存する
====================================================
使い方:
  python3 memory_store.py --category "ghost_api" --content "Ghost APIはverify=Falseが必要"
  python3 memory_store.py --category "pipeline" --content "Grokは4.1-fastが最適" --agent "neo-one"
  python3 memory_store.py --category "mistake" --content "CLIフラグではなくopenclaw.jsonで設定" --importance "high"
  python3 memory_store.py --batch /path/to/memories.json
"""
import argparse
import json
import sys
from pathlib import Path

# memory_system.pyと同じディレクトリにある前提
sys.path.insert(0, str(Path(__file__).parent))
from memory_system import MemorySystem


def main():
    parser = argparse.ArgumentParser(description="Store a memory in the long-term memory system")
    parser.add_argument("--base-dir", default="/opt/shared/memory",
                        help="Memory storage base directory")
    parser.add_argument("--category", "-c", help="Memory category (e.g., ghost_api, docker, pipeline)")
    parser.add_argument("--content", "-t", help="Memory content text")
    parser.add_argument("--agent", "-a", default="local-claude", help="Agent name")
    parser.add_argument("--importance", "-i", default="normal",
                        choices=["low", "normal", "high", "critical"],
                        help="Importance level")
    parser.add_argument("--source", "-s", default="manual", help="Source of the memory")
    parser.add_argument("--batch", "-b", help="Batch import from JSON file")
    parser.add_argument("--stdin", action="store_true", help="Read content from stdin")

    args = parser.parse_args()
    mem = MemorySystem(args.base_dir)

    # バッチインポート
    if args.batch:
        batch_file = Path(args.batch)
        if not batch_file.exists():
            print(f"ERROR: {args.batch} not found", file=sys.stderr)
            sys.exit(1)

        entries = json.loads(batch_file.read_text(encoding="utf-8"))
        count = 0
        for entry in entries:
            mid = mem.store(
                category=entry.get("category", "imported"),
                content=entry["content"],
                metadata={
                    "agent": entry.get("agent", args.agent),
                    "importance": entry.get("importance", "normal"),
                    "source": entry.get("source", "batch_import"),
                }
            )
            count += 1
            print(f"  stored: {mid} ({entry.get('category', 'imported')})")

        print(f"\n[OK] {count}件の記憶をインポートしました。")
        return

    # stdin入力
    if args.stdin:
        content = sys.stdin.read().strip()
        if not content:
            print("ERROR: stdin is empty", file=sys.stderr)
            sys.exit(1)
        category = args.category or "stdin"
    else:
        if not args.category or not args.content:
            parser.error("--category and --content are required (or use --batch / --stdin)")
        content = args.content
        category = args.category

    # 保存
    memory_id = mem.store(
        category=category,
        content=content,
        metadata={
            "agent": args.agent,
            "importance": args.importance,
            "source": args.source,
        }
    )

    print(f"[OK] 記憶を保存しました。")
    print(f"   ID: {memory_id}")
    print(f"   Category: {category}")
    print(f"   Agent: {args.agent}")

    # 統計表示
    stats = mem.get_stats()
    print(f"   Total memories: {stats['total_memories']}")


if __name__ == "__main__":
    main()
