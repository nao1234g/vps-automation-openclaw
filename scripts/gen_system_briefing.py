#!/usr/bin/env python3
"""
System Briefing Generator — /opt/shared/SYSTEM_BRIEFING.md を自動生成する。

30分ごとにcronで実行し、Neo1/Neo2が「自分がオフラインの間に何が起きたか」を
セッション開始時に読み込めるようにする。

VPS上で実行: python3 /opt/shared/scripts/gen_system_briefing.py
出力先: /opt/shared/SYSTEM_BRIEFING.md
"""

import os
import sys
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
NOW = datetime.now(JST)
NOW_STR = NOW.strftime("%Y-%m-%d %H:%M JST")

TASK_LOG_DIR = Path("/opt/shared/task-log")
REPORTS_DIR  = Path("/opt/shared/reports")
OUTPUT_PATH  = Path("/opt/shared/SYSTEM_BRIEFING.md")

# ---------------------------------------------------------------------------

def _run(cmd: str, timeout: int = 5) -> str:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""


def _read_file(path: Path, max_chars: int = 3000) -> str:
    try:
        text = path.read_text(encoding="utf-8")
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n... (truncated, full file: {path})"
        return text
    except Exception:
        return f"(読み取り失敗: {path})"


def _recent_files(directory: Path, n: int = 5, glob: str = "*.md") -> list[Path]:
    """最近更新された n ファイルを返す"""
    try:
        files = sorted(directory.glob(glob), key=lambda p: p.stat().st_mtime, reverse=True)
        return files[:n]
    except Exception:
        return []


def _service_status(name: str) -> str:
    out = _run(f"systemctl is-active {name} 2>/dev/null")
    return "✅ 稼働中" if out == "active" else f"⚠️ {out or '不明'}"


# ---------------------------------------------------------------------------

def generate() -> str:
    lines = []
    lines.append(f"# システム現状ブリーフィング")
    lines.append(f"> 自動生成: {NOW_STR}  |  **このファイルはセッション開始時に必ず最初に読むこと**")
    lines.append("")

    # ── 1. サービス稼働状態 ─────────────────────────────────────────────
    lines.append("## 1. サービス稼働状態")
    services = [
        ("neo-telegram",       "NEO-ONE (Claude Code Telegram)"),
        ("neo2-telegram",      "NEO-TWO (Claude Code Telegram)"),
        ("ghost-nowpattern",   "Ghost CMS (nowpattern.com)"),
        ("caddy",              "Caddy (リバースプロキシ)"),
        ("cron",               "Cron (定期実行)"),
    ]
    for svc, label in services:
        lines.append(f"- **{label}**: {_service_status(svc)}")

    # Docker コンテナ
    docker_out = _run("docker ps --format '{{.Names}}: {{.Status}}' 2>/dev/null | head -10")
    if docker_out:
        lines.append("")
        lines.append("**Dockerコンテナ:**")
        for row in docker_out.splitlines():
            lines.append(f"- {row}")
    lines.append("")

    # ── 2. 記事レジストリ（最重要: 重複防止）───────────────────────────
    lines.append("## 2. 記事レジストリ（重複防止 — 記事を書く前に必ず確認）")
    registry_path = Path("/opt/shared/article_registry.json")
    if registry_path.exists():
        try:
            import json as _json
            reg = _json.loads(registry_path.read_text(encoding="utf-8"))
            articles = reg.get("articles", [])
            in_progress = [a for a in articles if a["status"] == "in_progress"]
            completed = [a for a in articles if a["status"] == "completed"]

            if in_progress:
                lines.append("### ⚠️ 現在執筆中（このトピックと被る記事は書かないこと）")
                for a in in_progress:
                    lines.append(f"- **[{a['agent'].upper()}]** {a['topic']} `{a['type']}` — {a['claimed_at']}")
            else:
                lines.append("### ✅ 現在執筆中の記事: なし")

            lines.append("")
            recent_done = completed[-8:]
            if recent_done:
                lines.append("### 完了済み（最新8件）— 同じトピックを書かないこと")
                for a in recent_done:
                    url = a.get("url", "")
                    lines.append(f"- [{a['agent'].upper()}] {a['topic']} — {a.get('completed_at', '')} {url}")
        except Exception as e:
            lines.append(f"（レジストリ読み取りエラー: {e}）")
    else:
        lines.append("（レジストリ未作成）")

    lines.append("")
    lines.append("> **記事を書く手順**: 1) `article_registry.py claim` で予約 → 2) 記事執筆 → 3) `article_registry.py complete` で完了登録")
    lines.append("")

    # ── 3. 直近のタスクログ ───────────────────────────────────────────
    lines.append("## 3. 直近のタスクログ（最新5件）")
    task_files = _recent_files(TASK_LOG_DIR, n=5)
    if task_files:
        for tf in task_files:
            mtime = datetime.fromtimestamp(tf.stat().st_mtime, tz=JST).strftime("%m/%d %H:%M")
            lines.append(f"\n### [{mtime}] {tf.name}")
            lines.append(_read_file(tf, max_chars=1200))
    else:
        lines.append("（タスクログなし）")
    lines.append("")

    # ── 4. 直近のレポート ─────────────────────────────────────────────
    lines.append("## 4. 直近のレポート（最新3件）")
    report_files = _recent_files(REPORTS_DIR, n=3)
    if report_files:
        for rf in report_files:
            mtime = datetime.fromtimestamp(rf.stat().st_mtime, tz=JST).strftime("%m/%d %H:%M")
            lines.append(f"\n### [{mtime}] {rf.name}")
            lines.append(_read_file(rf, max_chars=1500))
    else:
        lines.append("（レポートなし）")
    lines.append("")

    # ── 5. cron 最終実行ログ（直近5行）──────────────────────────────────
    lines.append("## 5. cronジョブ最終実行（直近）")
    cron_log = _run("grep -i 'python3\\|bash' /var/log/syslog 2>/dev/null | tail -8")
    if not cron_log:
        cron_log = _run("journalctl -u cron --no-pager -n 8 2>/dev/null")
    if cron_log:
        lines.append("```")
        lines.append(cron_log[-2000:])
        lines.append("```")
    else:
        lines.append("（ログ取得不可）")
    lines.append("")

    # ── 5. Ghost 最新投稿 ────────────────────────────────────────────
    lines.append("## 6. Ghost最新投稿（nowpattern.com）")
    ghost_posts = _run(
        "sqlite3 /var/www/nowpattern/content/data/ghost.db "
        "\"SELECT title, status, published_at FROM posts ORDER BY published_at DESC LIMIT 5;\" "
        "2>/dev/null"
    )
    if ghost_posts:
        lines.append("```")
        lines.append(ghost_posts)
        lines.append("```")
    else:
        lines.append("（取得不可）")
    lines.append("")

    # ── 6. VPS ディスク・メモリ ──────────────────────────────────────
    lines.append("## 7. リソース状態")
    disk = _run("df -h / 2>/dev/null | tail -1")
    mem  = _run("free -h 2>/dev/null | grep Mem")
    if disk:
        lines.append(f"- **ディスク**: {disk}")
    if mem:
        lines.append(f"- **メモリ**: {mem}")
    lines.append("")

    # ── 7. AGENT_WISDOM 最終更新 ─────────────────────────────────────
    wisdom_path = Path("/opt/shared/AGENT_WISDOM.md")
    if wisdom_path.exists():
        mtime = datetime.fromtimestamp(wisdom_path.stat().st_mtime, tz=JST).strftime("%Y-%m-%d %H:%M JST")
        lines.append(f"## 8. AGENT_WISDOM.md 最終更新: {mtime}")
        # 先頭500字だけ
        lines.append(_read_file(wisdom_path, max_chars=500))
        lines.append(f"\n（続きは `/opt/shared/AGENT_WISDOM.md` を直接読むこと）")
    lines.append("")

    lines.append("---")
    lines.append(f"*自動生成 by gen_system_briefing.py — {NOW_STR}*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    print(f"Generating system briefing... ({NOW_STR})")
    content = generate()
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"OK: {OUTPUT_PATH} ({len(content)} chars)")
