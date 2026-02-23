#!/usr/bin/env python3
"""
task-tracker.py — TodoWrite完了タスクを自動追跡・通知
PostToolUse hook (TodoWrite) として動作

動作:
  - TodoWriteが実行されるたびに実行される
  - completed になったタスクを ~\.claude\tasks\history.jsonl に記録
  - Windowsポップアップ通知 (MessageBox)
  - セッションログを更新 (session-end.pyがTelegram通知に使う)
"""
import json
import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path


def _generate_dashboard(history_dir: Path, state: dict):
    """タスクボードHTMLを生成 (ブラウザで開いて自動リフレッシュ)"""
    # 全履歴ロード (直近30件)
    all_history = []
    history_file = history_dir / "history.jsonl"
    if history_file.exists():
        for line in history_file.read_text(encoding="utf-8").splitlines()[-30:]:
            try:
                all_history.append(json.loads(line))
            except Exception:
                pass
    all_history.reverse()  # 新しい順

    # HTML生成
    today = datetime.now().strftime("%Y-%m-%d")
    today_done = [h for h in all_history if h.get("date") == today]
    older_done = [h for h in all_history if h.get("date") != today]

    def rows(items, color="#1a5c30"):
        r = ""
        for it in items:
            ts = it.get("ts", "")
            proj = it.get("project", "")
            content = it.get("content", "")
            r += f'<tr><td style="color:#888;font-size:.8em;white-space:nowrap">{ts}</td><td style="color:#555;font-size:.8em">[{proj}]</td><td style="color:{color}">{content}</td></tr>\n'
        return r or '<tr><td colspan="3" style="color:#aaa;text-align:center;padding:12px">なし</td></tr>'

    ip_items = state.get("in_progress", [])
    pd_items = state.get("pending", [])

    ip_html = "".join(f'<li style="color:#c9a84c;margin:4px 0">⚙ {x}</li>' for x in ip_items) or '<li style="color:#aaa">なし</li>'
    pd_html = "".join(f'<li style="color:#555;margin:4px 0">○ {x}</li>' for x in pd_items) or '<li style="color:#aaa">なし</li>'

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="10">
<title>Claude Code タスクボード</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f0;margin:0;padding:20px}}
  h1{{color:#121e30;font-size:1.3em;margin:0 0 4px}}
  .ts{{color:#888;font-size:.8em;margin:0 0 20px}}
  .card{{background:#fff;border-radius:8px;padding:16px 20px;margin:12px 0;border:1px solid #e0dcd4}}
  .card h2{{font-size:.95em;color:#121e30;margin:0 0 10px;letter-spacing:.05em;text-transform:uppercase}}
  table{{width:100%;border-collapse:collapse}}
  td{{padding:6px 8px;border-bottom:1px solid #f0ede8;vertical-align:top}}
  li{{list-style:none}}
</style>
</head>
<body>
<h1>Claude Code タスクボード</h1>
<p class="ts">最終更新: {state.get("ts","?")} | プロジェクト: {state.get("project","?")} | 10秒ごと自動更新</p>

<div class="card">
  <h2>実行中</h2>
  <ul>{ip_html}</ul>
</div>

<div class="card">
  <h2>未着手</h2>
  <ul>{pd_html}</ul>
</div>

<div class="card">
  <h2>本日完了 ({len(today_done)}件)</h2>
  <table><tbody>{rows(today_done)}</tbody></table>
</div>

<div class="card" style="opacity:.7">
  <h2>過去の完了タスク</h2>
  <table><tbody>{rows(older_done, "#555")}</tbody></table>
</div>

</body>
</html>"""

    dashboard_file = history_dir / "dashboard.html"
    dashboard_file.write_text(html, encoding="utf-8")


# ── stdin から hook input を読む ──────────────────────────────────
try:
    raw = sys.stdin.read().strip()
    if not raw:
        sys.exit(0)
    data = json.loads(raw)
except Exception:
    sys.exit(0)

# ── tool_input から todos を取得 ─────────────────────────────────
tool_input = (
    data.get("tool_input")
    or data.get("input")
    or (data.get("parameters") or {})
    or {}
)
todos = tool_input.get("todos", [])
if not todos:
    sys.exit(0)

completed = [t for t in todos if t.get("status") == "completed"]
in_progress = [t for t in todos if t.get("status") == "in_progress"]
pending = [t for t in todos if t.get("status") == "pending"]

if not completed and not in_progress:
    sys.exit(0)

# ── タスク履歴ファイルに記録 ─────────────────────────────────────
history_dir = Path.home() / ".claude" / "tasks"
history_dir.mkdir(parents=True, exist_ok=True)

history_file = history_dir / "history.jsonl"
state_file = history_dir / "current_state.json"

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
project = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
project_name = Path(project).name

# 完了タスクを履歴に追記（重複防止: content+dateで判断）
existing_entries = set()
if history_file.exists():
    for line in history_file.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            existing_entries.add(e.get("content", ""))
        except Exception:
            pass

new_completions = []
for task in completed:
    content = task.get("content", "")
    if content and content not in existing_entries:
        entry = {
            "ts": timestamp,
            "content": content,
            "project": project_name,
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        new_completions.append(content)

# 現在の状態を保存（session-end.pyが使う）
state = {
    "ts": timestamp,
    "project": project_name,
    "completed": [t.get("content", "") for t in completed],
    "in_progress": [t.get("content", "") for t in in_progress],
    "pending": [t.get("content", "") for t in pending],
}
state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

# ── Windows ポップアップ通知（新しく完了したタスクのみ）─────────
if new_completions:
    latest = new_completions[-1][:80].replace('"', "'").replace('\n', ' ')
    try:
        ps_cmd = (
            'Add-Type -AssemblyName System.Windows.Forms; '
            f'[System.Windows.Forms.MessageBox]::Show("{latest}", '
            '"Claude Code タスク完了", '
            '"OK", "Information") | Out-Null'
        )
        subprocess.Popen(
            ["powershell.exe", "-WindowStyle", "Hidden", "-Command", ps_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

# ── HTML ダッシュボードを再生成 ──────────────────────────────────
try:
    _generate_dashboard(history_dir, state)
except Exception:
    pass

sys.exit(0)
