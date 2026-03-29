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
# 条件: エラーあり / リサーチなし開始 / 完了タスクあり — 成功セッションも記録対象
def _get_completed_tasks_today(project_dir: Path, today: str) -> list:
    """タスク台帳から今日完了したタスクIDリストを返す"""
    ledger_file = project_dir / ".claude" / "state" / "task_ledger.json"
    if not ledger_file.exists():
        return []
    try:
        ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
        tasks = ledger.get("tasks", [])
        return [
            t.get("task_id", t.get("id", "?"))
            for t in tasks
            if t.get("status") == "done"
            and (
                (t.get("completed_at") or "").startswith(today)
                or (t.get("created_at") or "").startswith(today)
            )
        ]
    except Exception:
        return []

completed_today = _get_completed_tasks_today(PROJECT_DIR, date_header)
has_completed_tasks = len(completed_today) > 0

should_write_wisdom = (error_count > 0 or started_without or has_completed_tasks)

if should_write_wisdom and AGENT_WISDOM.exists():
    # date_short（HH:MM付き）をヘッダーに使うことで、同日複数セッションも個別記録される
    wisdom_entry = "\n### %s セッションサマリー（自動記録）\n" % date_short
    wisdom_entry += "- searches: %d, errors: %d, research_first: %s\n" % (search_count, error_count, research_done)
    if errors:
        wisdom_entry += "- エラー発生ツール: %s\n" % ", ".join(set(e.get("tool", "?") for e in errors[:5]))
    if started_without:
        wisdom_entry += "- ⚠️ リサーチなしで実装開始（次回は先にWebSearchすること）\n"
    if has_completed_tasks:
        wisdom_entry += "- ✅ 完了タスク: %s\n" % ", ".join(completed_today)

    # 重複チェック: date_short（HH:MM粒度）単位で同一エントリを防ぐ
    # date_short = "2026-03-29 14:30" — 同分以内の重複書き込みのみ防止
    # ★ 旧ロジック（date_headerのみ）は1日1エントリ制限になっていたので修正
    existing = AGENT_WISDOM.read_text(encoding="utf-8")
    check_key = date_short + " セッションサマリー（自動記録）"
    if check_key not in existing:
        with open(AGENT_WISDOM, "a", encoding="utf-8") as f:
            f.write(wisdom_entry)
        print("📚 AGENT_WISDOM.md にセッションサマリーを記録しました。")

# 3. 長期記憶システムに自動保存（ChromaDB + Markdown）
try:
    sys.path.insert(0, str(SCRIPTS_DIR))
    from memory_extract import (
        extract_from_session,
        extract_from_task_ledger,
        extract_from_failure_memory,
    )
    from memory_system import MemorySystem

    memories = extract_from_session(PROJECT_DIR)
    memories.extend(extract_from_task_ledger(PROJECT_DIR))
    memories.extend(extract_from_failure_memory(PROJECT_DIR))
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

# 5. mistake_patterns.json → VPS同期（proactive_scannerが最新パターンを使えるように）
# auto-codifier.py が新パターンを登録したら、VPSスキャナーにも即反映する。
PATTERNS_FILE = STATE_DIR / "mistake_patterns.json"
if PATTERNS_FILE.exists():
    try:
        subprocess.run(
            ["scp", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
             str(PATTERNS_FILE), "%s:/opt/shared/state/mistake_patterns.json" % VPS],
            timeout=8, capture_output=True
        )
        # パターン数を読んで表示
        try:
            patterns = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
            print("🛡️ mistake_patterns.json (%d件) → VPSに同期しました。" % len(patterns))
        except Exception:
            print("🛡️ mistake_patterns.json → VPSに同期しました。")
    except Exception:
        pass  # VPS不達でもローカルのパターンは有効

# H1: VPSスナップショット保存（次セッション差分比較用）
try:
    result = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
         "-o", "BatchMode=yes", VPS, "cat /opt/shared/SHARED_STATE.md"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0:
        snapshot = {"timestamp": datetime.now().isoformat(), "content": result.stdout}
        snap_file = STATE_DIR / "last_vps_snapshot.json"
        with open(snap_file, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print("📸 VPSスナップショット保存（H1: 次セッション差分比較用）")
except Exception:
    pass  # VPS不達でも続行

# H3: セッション引き継ぎデータ保存（次セッション用ハンドオフ）
try:
    current_state_path = Path.home() / ".claude" / "tasks" / "current_state.json"
    handoff_file = STATE_DIR / "handoff.json"
    if current_state_path.exists():
        cs = json.loads(current_state_path.read_text(encoding="utf-8"))
        in_progress = cs.get("in_progress", [])
        pending = cs.get("pending", [])
        handoff = {
            "timestamp": datetime.now().isoformat(),
            "in_progress": in_progress[:5],
            "pending": pending[:5],
        }
        with open(handoff_file, "w", encoding="utf-8") as f:
            json.dump(handoff, f, ensure_ascii=False, indent=2)
        ip_count = len(in_progress)
        if ip_count > 0:
            print("🤝 H3: 引き継ぎデータ保存（進行中: %d件）" % ip_count)
except Exception:
    pass  # ハンドオフが保存できなくても続行

# 6. VPS→ローカル 双方向フィードバック（週1回: 新パターン候補をTelegramへ）
try:
    feedback_script = SCRIPTS_DIR / "vps_feedback_sync.py"
    if feedback_script.exists():
        subprocess.run(
            [sys.executable, str(feedback_script)],
            timeout=30, capture_output=True
        )
        # vps_feedback_sync.py 内でweekly制御済み（毎回呼んでOK）
except Exception:
    pass  # VPS不達でも続行

# 7. Coordination タスク完了（セッション終了時）
try:
    coord_state_file = PROJECT_DIR / ".claude" / "hooks" / "state" / "coord_session_task.json"
    if coord_state_file.exists():
        coord_state = json.loads(coord_state_file.read_text(encoding="utf-8"))
        task_id = coord_state.get("task_id", "")
        files_edited = coord_state.get("files_edited", [])
        if task_id and task_id != "FAILED":
            files_json = json.dumps(files_edited[:20]).replace('"', '\\"')
            py_cmd = (
                'import sys; sys.path.insert(0, "/opt/shared/scripts"); '
                'from coordination_workflow import CoordWorkflow, WorkflowContext; '
                'import time; '
                f'wf = CoordWorkflow("local-claude"); '
                f'ctx = WorkflowContext("local-claude", "{task_id}", []); '
                f'wf.done(ctx, evidence=["session:completed", "files:{n}"], '
                f'summary="Session ended, {n} files edited")'
            ).format(n=len(files_edited))
            result = subprocess.run(
                ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
                 '-o', 'StrictHostKeyChecking=no', 'root@163.44.124.123',
                 f'python3 -c \'{py_cmd}\''],
                capture_output=True, timeout=12
            )
            if result.returncode == 0:
                print(f"🤝 Coordination task {task_id[:12]}... → completed ({len(files_edited)} files)")
            coord_state_file.unlink(missing_ok=True)
except Exception:
    pass  # coordination failure must never crash session-end

sys.exit(0)
