#!/usr/bin/env python3
"""
rules-sync.py — PostToolUse Hook: Rule File Auto-Sync to VPS
=============================================================
ローカルでルールファイルを編集した瞬間にVPSへ即時同期。
「脳の分裂」を防ぐ。Single Source of Truth の実現。

対象ファイル:
  docs/KNOWN_MISTAKES.md      -> /opt/shared/docs/KNOWN_MISTAKES.md
  docs/AGENT_WISDOM.md        -> /opt/shared/AGENT_WISDOM.md
  .claude/rules/*.md          -> /opt/shared/rules/*.md (any rules file)
  .claude/memory/MEMORY.md    -> /opt/shared/MEMORY.md
  ※ .claude/CLAUDE.md -> /opt/CLAUDE.md は 2026-03-14 退役済み（tombstone のみ残存）

動作: 非同期SCP（2秒タイムアウト）。失敗しても処理を止めない。
"""
import json
import subprocess
import sys
import time
from pathlib import Path

VPS = "root@163.44.124.123"
TIMEOUT = 6  # seconds

# ルールファイルのマッピング: local -> vps_path
# NOTE: ".claude/CLAUDE.md" -> "/opt/CLAUDE.md" は 2026-03-14 に退役済み。
#       /opt/CLAUDE.md は tombstone として存在。新規同期は不要。
#       NEO の実効プロンプトは sdk_integration.py:neo_system_prompt で注入される。
RULE_FILES = {
    "docs/KNOWN_MISTAKES.md": "/opt/shared/docs/KNOWN_MISTAKES.md",
    "docs/AGENT_WISDOM.md": "/opt/shared/AGENT_WISDOM.md",
    ".claude/memory/MEMORY.md": "/opt/shared/MEMORY.md",
}

# rules/ ディレクトリ内の*.mdは全てVPSへ
RULES_DIR_LOCAL = ".claude/rules"
RULES_DIR_VPS = "/opt/shared/rules"

try:
    # Hook入力を読み込む
    hook_input = json.loads(sys.stdin.read())
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Edit/Write以外はスキップ
    if tool_name not in ("Edit", "Write"):
        sys.exit(0)

    # 編集されたファイルパス
    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    # プロジェクトルートを特定
    project_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    abs_path = Path(file_path).resolve()

    # プロジェクトルートからの相対パス
    try:
        rel_path = abs_path.relative_to(project_dir.resolve())
        rel_str = str(rel_path).replace("\\", "/")
    except ValueError:
        sys.exit(0)

    # 同期対象かチェック
    vps_dest = None

    # 固定マッピング
    for local_rel, vps_path in RULE_FILES.items():
        if rel_str == local_rel or rel_str.endswith(local_rel.lstrip(".")):
            vps_dest = vps_path
            break

    # rules/ ディレクトリ内のmdファイル
    if vps_dest is None and (RULES_DIR_LOCAL in rel_str) and rel_str.endswith(".md"):
        filename = Path(rel_str).name
        vps_dest = f"{RULES_DIR_VPS}/{filename}"

    if vps_dest is None:
        sys.exit(0)  # 対象外のファイル

    # ファイルが存在するか確認
    if not abs_path.exists():
        sys.exit(0)

    # VPSへSCP（非同期、2秒タイムアウト）
    start = time.time()
    result = subprocess.run(
        [
            "scp",
            "-o", "ConnectTimeout=3",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            str(abs_path),
            f"{VPS}:{vps_dest}",
        ],
        timeout=TIMEOUT,
        capture_output=True,
    )

    elapsed = time.time() - start
    if result.returncode == 0:
        print(f"[rules-sync] {rel_str} -> VPS:{vps_dest} ({elapsed:.1f}s)")
    else:
        # 失敗してもブロックしない（VPS不達は許容）
        err = result.stderr.decode(errors="replace").strip()
        print(f"[rules-sync] SKIP (VPS unreachable): {rel_str}", file=sys.stderr)

except Exception as e:
    # フック失敗はサイレントに（メイン処理をブロックしない）
    print(f"[rules-sync] ERROR: {e}", file=sys.stderr)

sys.exit(0)
