#!/usr/bin/env python3
"""
rules-sync.py — PostToolUse Hook: Rule File Auto-Sync to VPS
=============================================================
ローカルでルールファイルを編集した瞬間にVPSへ即時同期。
「脳の分裂」を防ぐ。Single Source of Truth の実現。

対象ファイル:
  .claude/CLAUDE.md           -> /opt/CLAUDE.md
  docs/KNOWN_MISTAKES.md      -> /opt/shared/docs/KNOWN_MISTAKES.md
  docs/AGENT_WISDOM.md        -> /opt/shared/AGENT_WISDOM.md
  .claude/rules/*.md          -> /opt/shared/rules/*.md (any rules file)
  .claude/memory/MEMORY.md    -> /opt/shared/MEMORY.md

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
RULE_FILES = {
    ".claude/CLAUDE.md": "/opt/CLAUDE.md",
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

        # CLAUDE.md を同期した場合、Oracle Mandate をVPS上で再注入
        if vps_dest == "/opt/CLAUDE.md":
            mandate_script = (
                "python3 -c \""
                "f=open('/opt/CLAUDE.md','r');c=f.read();f.close();"
                "m='# ⚡ ORACLE MANDATE（最優先）— タスク前に必ず読め';"
                "print('[rules-sync] Oracle Mandate: already present') if m in c else "
                "[open('/tmp/fix_oracle_mandate.py','r') and None]"
                "\""
            )
            # fix_oracle_mandate.py が存在すれば再実行
            ssh_result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=3", "-o", "BatchMode=yes",
                 "-o", "StrictHostKeyChecking=no", VPS,
                 "if grep -q 'ORACLE MANDATE' /opt/CLAUDE.md; then "
                 "echo '[rules-sync] Oracle Mandate already present'; "
                 "elif [ -f /tmp/fix_oracle_mandate.py ]; then "
                 "python3 /tmp/fix_oracle_mandate.py && echo '[rules-sync] Oracle Mandate re-injected'; "
                 "else echo '[rules-sync] WARN: fix_oracle_mandate.py not found'; fi"],
                timeout=10,
                capture_output=True,
            )
            if ssh_result.returncode == 0:
                out = ssh_result.stdout.decode(errors="replace").strip()
                sys.stdout.buffer.write(f"[rules-sync] {out}\n".encode("utf-8", errors="replace"))
    else:
        # 失敗してもブロックしない（VPS不達は許容）
        err = result.stderr.decode(errors="replace").strip()
        print(f"[rules-sync] SKIP (VPS unreachable): {rel_str}", file=sys.stderr)

except Exception as e:
    # フック失敗はサイレントに（メイン処理をブロックしない）
    print(f"[rules-sync] ERROR: {e}", file=sys.stderr)

sys.exit(0)
