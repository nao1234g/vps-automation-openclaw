#!/usr/bin/env python3
"""
SESSION END HOOK (v3) - Score + AGENT_WISDOM + Long-Term Memory
1. Summarize session performance and update cumulative score
2. Append session insights to local docs/AGENT_WISDOM.md
3. Auto-extract memories to ChromaDB long-term memory system
4. If VPS reachable, sync AGENT_WISDOM + memories to VPS
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
SCRIPTS_DIR = PROJECT_DIR / "scripts"
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
STATE_FILE = STATE_DIR / "session.json"
SCORECARD = PROJECT_DIR / ".claude" / "SCORECARD.md"
AGENT_WISDOM = PROJECT_DIR / "docs" / "AGENT_WISDOM.md"
VPS = "root@163.44.124.123"

if not STATE_FILE.exists():
    sys.exit(0)

# Load state
try:
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
except Exception:
    sys.exit(0)

search_count = state.get("search_count", 0)
error_count = len(state.get("errors", []))
research_done = state.get("research_done", False)
started_without = state.get("started_without_research", False)
errors = state.get("errors", [])

date_short = datetime.now().strftime("%Y-%m-%d %H:%M")
date_header = datetime.now().strftime("%Y-%m-%d")
summary = "Session: searches=%d, errors=%d, researched_first=%s" % (search_count, error_count, research_done)

# 1. Write session summary to scorecard
if SCORECARD.exists():
    if search_count >= 3 and error_count == 0:
        with open(SCORECARD, "a", encoding="utf-8") as f:
            f.write("| %s | +3 | Thorough research, zero errors | %s |\n" % (date_short, summary))
    elif search_count >= 1 and error_count <= 1:
        with open(SCORECARD, "a", encoding="utf-8") as f:
            f.write("| %s | +1 | Researched with minimal errors | %s |\n" % (date_short, summary))
    elif started_without and error_count >= 2:
        with open(SCORECARD, "a", encoding="utf-8") as f:
            f.write("| %s | -2 | No research, multiple errors | %s |\n" % (date_short, summary))

    # Update cumulative score in header
    try:
        content = SCORECARD.read_text(encoding="utf-8")
        scores = re.findall(r'\|\s*([+-]\d+)\s*\|', content)
        total = sum(int(s) for s in scores)
        content = re.sub(
            r'^## Cumulative Score: .*$',
            '## Cumulative Score: %d' % total,
            content,
            flags=re.MULTILINE
        )
        SCORECARD.write_text(content, encoding="utf-8")
    except Exception:
        pass

# 2. AGENT_WISDOM 自動更新（セッションで学んだことを記録）
# エラーが1件以上あった場合、またはリサーチなしで開始した場合は記録
if (error_count > 0 or started_without) and AGENT_WISDOM.exists():
    wisdom_entry = "\n### %s セッションサマリー（自動記録）\n" % date_header
    wisdom_entry += "- searches: %d, errors: %d, research_first: %s\n" % (search_count, error_count, research_done)
    if errors:
        wisdom_entry += "- エラー発生ツール: %s\n" % ", ".join(set(e.get("tool", "?") for e in errors[:5]))
    if started_without:
        wisdom_entry += "- ⚠️ リサーチなしで実装開始（次回は先にWebSearchすること）\n"

    # 既存の自動記録エントリと重複しないよう確認
    marker = "セッションサマリー（自動記録）"
    existing = AGENT_WISDOM.read_text(encoding="utf-8")
    if date_header not in existing or marker not in existing:
        with open(AGENT_WISDOM, "a", encoding="utf-8") as f:
            f.write(wisdom_entry)
        print("📚 AGENT_WISDOM.md にセッションサマリーを記録しました。")

# 3. 長期記憶システムに自動保存（ChromaDB + Markdown）
try:
    sys.path.insert(0, str(SCRIPTS_DIR))
    from memory_extract import extract_from_session
    from memory_system import MemorySystem

    memories = extract_from_session(PROJECT_DIR)
    if memories:
        # ローカル保存先（VPS不達時のフォールバック）
        local_memory_dir = PROJECT_DIR / ".claude" / "memory"
        mem = MemorySystem(str(local_memory_dir))
        count = 0
        for m in memories:
            mem.store(m["category"], m["content"], m.get("metadata", {}))
            count += 1
        if count > 0:
            print("🧠 長期記憶に%d件保存しました。" % count)

        # VPSのChromaDBにも保存を試みる
        try:
            subprocess.run(
                ["scp", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", "-r",
                 str(local_memory_dir / "entries"), "%s:/opt/shared/memory/" % VPS],
                timeout=10, capture_output=True
            )
        except Exception:
            pass
except Exception as e:
    print("⚠️ 長期記憶保存スキップ: %s" % e)

# 4. VPSのAGENT_WISDOMに同期（バックグラウンド、失敗しても続行）
if AGENT_WISDOM.exists():
    try:
        subprocess.run(
            ["scp", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
             str(AGENT_WISDOM), "%s:/opt/shared/AGENT_WISDOM.md" % VPS],
            timeout=8, capture_output=True
        )
        print("🔄 AGENT_WISDOM.md → VPSに同期しました。")
    except Exception:
        pass  # VPS不達でもローカル更新は完了している

sys.exit(0)
