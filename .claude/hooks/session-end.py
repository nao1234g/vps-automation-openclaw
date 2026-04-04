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

# 7. claude-to-codex.md 自動更新（双方向エージェント通信）
# 毎セッション終了時にClaudeが何をしたかをCodexに報告する
try:
    mailbox_dir = PROJECT_DIR / ".agent-mailbox"
    mailbox_dir.mkdir(parents=True, exist_ok=True)
    claude_to_codex = mailbox_dir / "claude-to-codex.md"

    # 自動収集できるメタデータ
    branch = ""
    commit_sha = ""
    try:
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=str(PROJECT_DIR)
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
        sha_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=str(PROJECT_DIR)
        )
        commit_sha = sha_result.stdout.strip() if sha_result.returncode == 0 else ""
    except Exception:
        pass

    changed_files = ""
    try:
        diff_result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            capture_output=True, text=True, timeout=5, cwd=str(PROJECT_DIR)
        )
        if diff_result.returncode == 0:
            files = diff_result.stdout.strip().split("\n")[:15]
            changed_files = "\n".join(f"- {f}" for f in files if f)
    except Exception:
        pass

    active_task = ""
    try:
        ledger_path = PROJECT_DIR / ".claude" / "state" / "task_ledger.json"
        if ledger_path.exists():
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            active_tasks = [
                t for t in ledger.get("tasks", [])
                if t.get("status") in ("active", "in_progress")
            ]
            if active_tasks:
                active_task = active_tasks[0].get("task_id", active_tasks[0].get("id", ""))
    except Exception:
        pass

    completed_str = ", ".join(completed_today) if completed_today else "(none)"

    # テンプレートを生成（自動フィールド + 手動フィールドのプレースホルダー）
    handoff_content = f"""# Claude → Codex Message ({date_header})

## Auto-generated Session Report

### Metadata (auto-filled)
- **timestamp**: {datetime.now().isoformat()}
- **branch**: {branch}
- **commit**: {commit_sha}
- **active_task_id**: {active_task}
- **completed_tasks**: {completed_str}
- **searches**: {search_count}, **errors**: {error_count}

### Changed Files
{changed_files if changed_files else "(no file changes detected)"}

### What Changed (session-end auto-summary)
- Session with {search_count} searches, {error_count} errors
- Completed tasks: {completed_str}

### Unfinished Items
(To be filled by Claude during session or by next session-start review)

### Next Steps for Codex
(To be filled by Claude when delegating work to Codex)
"""

    # 品質ゲート: 既存の手動メッセージがある場合は上書きしない
    # 同日の自動レポートのみ上書き（手動メッセージは保護）
    should_write = True
    if claude_to_codex.exists():
        existing = claude_to_codex.read_text(encoding="utf-8")
        # 手動メッセージ（"Auto-generated Session Report"を含まない）は保護
        if "Auto-generated Session Report" not in existing:
            # 手動メッセージが今日より新しい場合は上書きしない
            if date_header in existing.split("\n")[0]:
                should_write = False  # 同日の手動メッセージを保護
            else:
                # 古い手動メッセージは保持しつつ、新しいセッションレポートを追記
                handoff_content = existing + "\n---\n\n" + handoff_content
                should_write = True

    if should_write:
        claude_to_codex.write_text(handoff_content, encoding="utf-8")
        print("📬 claude-to-codex.md を更新しました（Codexへのセッションレポート）")
        # SCP push to VPS → Codex dispatcher will pick it up
        try:
            scp_result = subprocess.run(
                ['scp', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
                 '-o', 'StrictHostKeyChecking=no',
                 str(claude_to_codex),
                 'root@163.44.124.123:/opt/shared/agent-mailbox/claude-to-codex.md'],
                capture_output=True, timeout=15
            )
            if scp_result.returncode == 0:
                print("📤 claude-to-codex.md → VPS にプッシュ完了")
            else:
                print(f"⚠️ VPS push失敗: {scp_result.stderr.decode()[:100]}")
        except Exception as scp_e:
            print(f"⚠️ VPS push スキップ: {scp_e}")

except Exception as e:
    print(f"⚠️ claude-to-codex.md 更新スキップ: {e}")

# 8. resume_prompt.txt をCodex推奨スキーマで更新
try:
    resume_dir = PROJECT_DIR / "reports" / "claude_sidecar"
    resume_dir.mkdir(parents=True, exist_ok=True)
    resume_file = resume_dir / "resume_prompt.txt"

    # sidecar session_status.json からアクティブタスク情報を取得
    sidecar_status = ""
    sidecar_task = ""
    sidecar_next = ""
    sidecar_blocker = ""
    session_status_file = resume_dir / "session_status.json"
    if session_status_file.exists():
        try:
            ss = json.loads(session_status_file.read_text(encoding="utf-8"))
            sidecar_status = ss.get("status", "")
            sidecar_task = ss.get("task_id", "")
            sidecar_next = ss.get("next_exact_step", "")
            sidecar_blocker = ss.get("blocking_reason", "")
        except Exception:
            pass

    # 完了タスクがある場合はそのサマリーをTASKに
    task_line = sidecar_task or active_task or "(no active task)"
    now_doing = f"Session ended. Status: {sidecar_status}" if sidecar_status else "Session ended normally"
    blocker = sidecar_blocker or "none"
    next_step = sidecar_next or "Review session report in claude-to-codex.md"

    # ファイルリスト（変更があったファイル上位5件）
    files_list = ""
    if changed_files:
        top_files = [f.strip("- ") for f in changed_files.split("\n") if f.strip("- ")][:5]
        files_list = ", ".join(top_files)
    else:
        files_list = "(none)"

    resume_content = f"""TASK: {task_line}
NOW DOING: {now_doing}
LAST VERIFIED FACT: Session ended at {date_short} with {search_count} searches, {error_count} errors. Completed: {completed_str}
BLOCKER: {blocker}
NEXT EXACT STEP: {next_step}
NEXT EXACT COMMAND: cat .agent-mailbox/codex-to-claude.md
FILES TO OPEN FIRST: {files_list}
"""

    # sidecarがin_progressの場合はresume_prompt.txtを上書きしない（sidecar自身が管理）
    if sidecar_status not in ("in_progress",):
        resume_file.write_text(resume_content, encoding="utf-8")
        print("📝 resume_prompt.txt を標準スキーマで更新しました")

except Exception as e:
    print(f"⚠️ resume_prompt.txt 更新スキップ: {e}")

# 9. Coordination タスク完了（セッション終了時）
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
