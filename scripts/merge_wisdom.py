#!/usr/bin/env python3
"""
Hive Mind v2.0 — VPS ↔ Local 双方向知識マージ
実行: python scripts/merge_wisdom.py [--dry-run]

1. VPS KNOWN_MISTAKES_VPS.md → Local docs/KNOWN_MISTAKES.md に新規セクション追加
2. VPS AGENT_WISDOM.md → Local docs/AGENT_WISDOM.md に新規エントリ追加
3. Local docs/KNOWN_MISTAKES.md → VPS /opt/shared/KNOWN_MISTAKES.md に同期
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

VPS = "root@163.44.124.123"
DRY_RUN = "--dry-run" in sys.argv

PROJECT_DIR = Path(__file__).parent.parent
LOCAL_MISTAKES = PROJECT_DIR / "docs" / "KNOWN_MISTAKES.md"
LOCAL_WISDOM   = PROJECT_DIR / "docs" / "AGENT_WISDOM.md"

def ssh(cmd, timeout=15):
    r = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
         "-o", "BatchMode=yes", VPS, cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
    )
    return r.stdout if r.returncode == 0 else ""

def scp_from(remote_path, local_path, timeout=15):
    r = subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
         "-o", "BatchMode=yes", f"{VPS}:{remote_path}", str(local_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
    )
    return r.returncode == 0

def scp_to(local_path, remote_path, timeout=15):
    r = subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
         "-o", "BatchMode=yes", str(local_path), f"{VPS}:{remote_path}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
    )
    return r.returncode == 0


# ─────────────────────────────────────────────────────
# Step 1: VPS KNOWN_MISTAKES_VPS.md → local KNOWN_MISTAKES.md
# ─────────────────────────────────────────────────────
def merge_mistakes():
    vps_content = ssh("cat /opt/shared/KNOWN_MISTAKES_VPS.md 2>/dev/null")
    if not vps_content:
        print("  [SKIP] KNOWN_MISTAKES_VPS.md not reachable")
        return 0

    # Parse sections: ### YYYY-MM-DD: ... entries
    vps_sections = {}
    current_key = None
    current_lines = []
    for line in vps_content.splitlines():
        if line.startswith("### "):
            if current_key:
                vps_sections[current_key] = "\n".join(current_lines)
            current_key = line.strip()
            current_lines = [line]
        elif current_key:
            current_lines.append(line)
    if current_key:
        vps_sections[current_key] = "\n".join(current_lines)

    if not LOCAL_MISTAKES.exists():
        print("  [SKIP] Local KNOWN_MISTAKES.md not found")
        return 0

    local_content = LOCAL_MISTAKES.read_text(encoding="utf-8")

    new_sections = []
    for key, section in vps_sections.items():
        if key not in local_content:
            new_sections.append(section)

    if not new_sections:
        print("  [OK] KNOWN_MISTAKES: VPSに新規セクションなし")
        return 0

    print(f"  [NEW] KNOWN_MISTAKES: VPSから{len(new_sections)}件の新規エラーを発見")
    for s in new_sections:
        print(f"    + {s.splitlines()[0]}")

    if DRY_RUN:
        print("  [DRY-RUN] 書き込みスキップ")
        return len(new_sections)

    # Append new sections after the last ### heading
    append_text = "\n\n---\n## VPS Auto-Collected Errors (from KNOWN_MISTAKES_VPS.md)\n\n"
    marker = "## VPS Auto-Collected Errors"
    if marker not in local_content:
        with open(LOCAL_MISTAKES, "a", encoding="utf-8") as f:
            f.write(append_text)
            f.write("\n\n".join(new_sections))
            f.write("\n")
    else:
        # Append after the VPS section header
        existing_keys = set()
        for line in local_content.splitlines():
            if line.startswith("### "):
                existing_keys.add(line.strip())
        new_only = [s for s in new_sections if s.splitlines()[0].strip() not in existing_keys]
        if new_only:
            with open(LOCAL_MISTAKES, "a", encoding="utf-8") as f:
                f.write("\n\n")
                f.write("\n\n".join(new_only))
                f.write("\n")

    print(f"  [DONE] {len(new_sections)}件を docs/KNOWN_MISTAKES.md に追記しました")
    return len(new_sections)


# ─────────────────────────────────────────────────────
# Step 2: VPS AGENT_WISDOM.md → local docs/AGENT_WISDOM.md
# ─────────────────────────────────────────────────────
def merge_agent_wisdom():
    vps_content = ssh("cat /opt/shared/AGENT_WISDOM.md 2>/dev/null")
    if not vps_content:
        print("  [SKIP] VPS AGENT_WISDOM.md not reachable")
        return 0

    # Extract "## 学習ログ" entries from VPS
    learning_entries = []
    in_learning = False
    for line in vps_content.splitlines():
        if line.startswith("## 学習ログ"):
            in_learning = True
            continue
        if in_learning and line.startswith("## "):
            in_learning = False
            continue
        if in_learning and line.startswith("- ") and len(line) > 20:
            learning_entries.append(line.strip())

    if not learning_entries:
        print("  [OK] AGENT_WISDOM: VPS学習ログに新規エントリなし")
        return 0

    if not LOCAL_WISDOM.exists():
        print("  [SKIP] Local AGENT_WISDOM.md not found")
        return 0

    local_content = LOCAL_WISDOM.read_text(encoding="utf-8")

    new_entries = [e for e in learning_entries if e[:50] not in local_content]

    if not new_entries:
        print("  [OK] AGENT_WISDOM: 全エントリ既存")
        return 0

    print(f"  [NEW] AGENT_WISDOM: VPSから{len(new_entries)}件の新規エントリ")
    for e in new_entries:
        print(f"    + {e[:80]}")

    if DRY_RUN:
        print("  [DRY-RUN] 書き込みスキップ")
        return len(new_entries)

    # Append to local AGENT_WISDOM.md under a VPS section
    marker = "## VPS Agent Learnings"
    if marker not in local_content:
        with open(LOCAL_WISDOM, "a", encoding="utf-8") as f:
            f.write(f"\n\n---\n{marker}\n> VPSエージェントが学んだ知識（自動同期）\n\n")
            for e in new_entries:
                f.write(f"{e}\n")
    else:
        with open(LOCAL_WISDOM, "a", encoding="utf-8") as f:
            f.write("\n")
            for e in new_entries:
                f.write(f"{e}\n")

    print(f"  [DONE] {len(new_entries)}件を docs/AGENT_WISDOM.md に追記しました")
    return len(new_entries)


# ─────────────────────────────────────────────────────
# Step 3: Local KNOWN_MISTAKES.md → VPS /opt/shared/KNOWN_MISTAKES.md
# ─────────────────────────────────────────────────────
def push_mistakes_to_vps():
    if not LOCAL_MISTAKES.exists():
        return
    if DRY_RUN:
        print("  [DRY-RUN] VPS push スキップ")
        return
    ok = scp_to(LOCAL_MISTAKES, "/opt/shared/KNOWN_MISTAKES.md")
    if ok:
        print("  [DONE] docs/KNOWN_MISTAKES.md → VPS /opt/shared/KNOWN_MISTAKES.md 同期完了")
    else:
        print("  [WARN] VPS push失敗（VPS不達の可能性）")


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[Hive Mind v2.0] 双方向知識マージ開始 {'(DRY-RUN)' if DRY_RUN else ''}")
    print(f"  時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    m1 = merge_mistakes()
    m2 = merge_agent_wisdom()
    push_mistakes_to_vps()

    total = m1 + m2
    if total > 0:
        print(f"\n[完了] 合計{total}件の新規知識をローカルにマージしました")
    else:
        print("\n[完了] 新規知識なし（同期済み）")
