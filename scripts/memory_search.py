#!/usr/bin/env python3
"""
MEMORY SEARCH CLI — 長期記憶を検索する
========================================
使い方:
  python3 memory_search.py "Ghost API認証"
  python3 memory_search.py "Docker設定" --category docker --limit 10
  python3 memory_search.py --recent 20
  python3 memory_search.py --stats
  python3 memory_search.py --export > all_memories.md
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from memory_system import MemorySystem


def main():
    parser = argparse.ArgumentParser(description="Search the long-term memory system")
    parser.add_argument("query", nargs="?", help="Search query (natural language)")
    parser.add_argument("--base-dir", default="/opt/shared/memory",
                        help="Memory storage base directory")
    parser.add_argument("--category", "-c", help="Filter by category")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Number of results")
    parser.add_argument("--recent", "-r", type=int, help="Show N most recent memories")
    parser.add_argument("--stats", action="store_true", help="Show memory system stats")
    parser.add_argument("--export", action="store_true", help="Export all memories as markdown")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    mem = MemorySystem(args.base_dir)

    # 統計表示
    if args.stats:
        stats = mem.get_stats()
        if args.json:
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        else:
            print("=== Memory System Stats ===")
            print(f"ChromaDB: {'[OK] Available' if stats['chromadb_available'] else '[NG] Not available'}")
            print(f"Gemini Embedding: {'[OK] Available' if stats['gemini_available'] else '[NG] Fallback mode'}")
            print(f"Total memories (ChromaDB): {stats['total_memories']}")
            print(f"Markdown files: {stats['markdown_files']}")
            if stats['categories']:
                print("\nCategories:")
                for cat, count in sorted(stats['categories'].items()):
                    print(f"  {cat}: {count}")
        return

    # エクスポート
    if args.export:
        print(mem.export_all())
        return

    # 最近の記憶
    if args.recent:
        entries = mem.get_recent(args.recent)
        if args.json:
            print(json.dumps(entries, ensure_ascii=False, indent=2))
        else:
            print(f"=== Recent {len(entries)} Memories ===\n")
            for e in reversed(entries):
                print(f"[{e.get('created_at', '?')}] {e.get('category', '?')}: {e.get('summary', '?')}")
        return

    # 検索
    if not args.query:
        parser.error("Search query is required (or use --recent / --stats / --export)")

    results = mem.search(args.query, n_results=args.limit, category=args.category)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        if not results:
            print("記憶が見つかりませんでした。")
            return

        print(f"=== {len(results)} Results for: \"{args.query}\" ===\n")
        for i, r in enumerate(results, 1):
            distance = r.get("distance")
            score = f" (relevance: {1.0 - distance:.0%})" if distance is not None else ""
            print(f"--- [{i}] {r['category']}{score} ---")
            print(f"Date: {r.get('created_at', '?')} | Agent: {r.get('agent', '?')}")
            # 長いコンテンツは切り詰め
            content = r.get("content", "")
            if len(content) > 500:
                content = content[:500] + "..."
            print(content)
            print()


if __name__ == "__main__":
    main()
