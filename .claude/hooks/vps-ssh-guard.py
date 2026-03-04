#!/usr/bin/env python3
"""
VPS SSH Guard — PreToolUse Hook for Bash
==========================================
SSH/SCP経由のVPS操作を事前にインターセプト。

- 破壊的操作（rm -rf, DROP TABLE, data wipe）→ exit 2 でブロック
- 書き込み操作 → ログ記録してallow（exit 0）
- 全VPS操作を audit log に記録（事後監査用）

audit log: .claude/hooks/state/vps-ops.log
"""
import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
AUDIT_LOG = STATE_DIR / "vps-ops.log"
VPS_IP = "163.44.124.123"

# ── 破壊的パターン（exit 2 でブロック） ──────────────────────────────────
# 「元に戻せない」操作のみブロック。書き込みはブロックしない。
DESTRUCTIVE_PATTERNS = [
    (r"rm\s+-rf?\s+/opt",              "rm -rf /opt（本番ファイル全消去）"),
    (r"rm\s+-rf?\s+/var",              "rm -rf /var（ログ・DB全消去）"),
    (r"rm\s+-rf?\s+/etc",              "rm -rf /etc（設定ファイル全消去）"),
    (r">\s*/var/www/nowpattern",        "/var/www/nowpattern への上書き（Ghost本番）"),
    (r"DROP\s+TABLE",                  "SQL DROP TABLE"),
    (r"TRUNCATE\s+TABLE",              "SQL TRUNCATE TABLE"),
    (r"DROP\s+DATABASE",               "SQL DROP DATABASE"),
    (r"DELETE\s+FROM\s+posts",         "Ghost記事の全削除"),
    (r"ghost\s+db\s+import.*--force",  "Ghost DB強制インポート"),
]

# ── 書き込みパターン（ログ記録のみ、ブロックしない） ─────────────────────
WRITE_PATTERNS = [
    r"cat\s*>",
    r"tee\s+",
    r"echo\s.*>",
    r"\bcp\s+",
    r"\bmv\s+",
    r"systemctl\s+(start|stop|restart|reload|enable|disable)",
    r"docker\s+(restart|start|stop|exec)",
    r">\s*/opt",
    r">>\s*/opt",
    r"python3?\s+/opt.*\.py",
    r"bash\s+/opt",
    r"chmod\s+",
    r"chown\s+",
    r"pip3?\s+install",
    r"apt(-get)?\s+(install|remove|purge)",
    r"sed\s+-i",
    r"crontab\s+-",
    r"systemctl\s+daemon-reload",
]


def main():
    try:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
    except Exception:
        sys.exit(0)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    # VPS操作かチェック
    is_vps = (
        (f"root@{VPS_IP}" in command and "ssh" in command)
        or (f"root@{VPS_IP}" in command and "scp" in command)
        or f"@163.44.124.123" in command
    )
    if not is_vps:
        sys.exit(0)

    # Audit log（全VPS操作を記録）
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {command[:300]}\n")

    # ── 破壊的操作チェック → ブロック ───────────────────────────────────
    for pattern, description in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(
                f"\n{'━'*52}\n"
                f"🚨 [VPS-SSH-GUARD] 破壊的操作をブロックしました\n"
                f"{'━'*52}\n"
                f"  検出パターン: {description}\n"
                f"  コマンド: {command[:200]}\n\n"
                f"  このコマンドを実行するには:\n"
                f"  1. リスクと影響範囲をユーザーに説明する\n"
                f"  2. ユーザーの明示的承認を得る\n"
                f"  3. バックアップが存在することを確認する\n"
                f"{'━'*52}\n"
            )
            sys.exit(2)  # ブロック

    # ── 書き込み操作チェック → ログのみ ─────────────────────────────────
    for pattern in WRITE_PATTERNS:
        if re.search(pattern, command):
            print(f"📝 [VPS-SSH-GUARD] VPS書き込み操作 → audit log記録済み")
            break

    sys.exit(0)


if __name__ == "__main__":
    main()
